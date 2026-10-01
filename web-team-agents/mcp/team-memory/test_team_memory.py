"""Run:  pip install pytest mcp  &&  pytest -q      (from this folder)"""
import asyncio
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from store import Store, default_db_path  # noqa: E402


@pytest.fixture()
def db(tmp_path):
    return tmp_path / "tm.db"


@pytest.fixture()
def s(db):
    return Store(db)


# ---------------------------------------------------------------- memories
def test_remember_recall_and_supersede(s):
    a = s.remember("analyst", "convention", "Use i18next; keys are dot.case", key="i18n")
    b = s.remember("analyst", "convention", "Use i18next; keys are camelCase", key="i18n")
    assert b["replaced"] == [a["id"]]
    hits = s.recall("i18next")
    assert [h["id"] for h in hits] == [b["id"]]                       # old one hidden
    assert any(h["id"] == a["id"] for h in s.recall("i18next", include_retired=True))


def test_recall_is_ranked_scoped_and_project_wide_included(s):
    s.remember("dev-backend", "gotcha", "EF migrations must be reversible", story="01-auth")
    s.remember("dev-backend", "gotcha", "Never trust client dates", story="02-orders")
    s.remember("analyst", "convention", "All endpoints return problem+json errors")   # project-wide
    got = s.recall("endpoints errors migrations dates", story="01-auth")
    texts = " ".join(h["content"] for h in got)
    assert "reversible" in texts and "problem+json" in texts and "client dates" not in texts
    assert s.recall(kind="convention")[0]["agent"] == "analyst"


def test_fts_query_is_injection_safe(s):
    s.remember("a", "note", "quote \" and star * and NEAR( inside")
    assert isinstance(s.recall('" OR * NEAR( AND'), list)              # must not raise
    assert isinstance(s.recall("'; DROP TABLE memories; --"), list)
    assert s.stats()["memories"]["note"] == 1


def test_validation(s):
    with pytest.raises(ValueError): s.remember("bad agent!", "note", "x")
    with pytest.raises(ValueError): s.remember("a", "nope", "x")
    with pytest.raises(ValueError): s.remember("a", "note", "x" * 9000)
    with pytest.raises(ValueError): s.remember("a", "note", "   ")
    with pytest.raises(ValueError): s.log_decision("a", "s1", "Bad Topic", "r", "p", "c", "d")


def test_retire_and_get(s):
    i = s.remember("a", "note", "wrong fact")["id"]
    assert s.retire_memory(i, "a") == {"retired": True}
    assert s.recall("wrong") == []
    assert s.get_memory(i)["content"] == "wrong fact"


def test_long_content_is_truncated_in_recall_but_full_in_get(s):
    i = s.remember("a", "note", "y" * 5000)["id"]
    assert "truncated" in s.recall()[0]["content"]
    assert len(s.get_memory(i)["content"]) == 5000


def test_decisions_digest_groups_recurring_topics(s):
    for story in ("01-a", "02-b", "03-c"):
        s.log_decision("dev-frontend", story, "error-copy", "AC 3", "no FR copy given", "invent|ask", "invented FR copy")
    s.log_decision("analyst", "01-a", "one-off", "r", "p", "c", "d")
    d = s.decisions_digest(2)
    assert d["total_decisions"] == 4
    assert [g["topic"] for g in d["recurring"]] == ["error-copy"] and d["recurring"][0]["stories"] == 3


def test_export_decisions_markdown_roundtrips_and_filters(s):
    s.log_decision("product-manager", "01-a", "scope-gap", "step 5", "no frontend scope", "skip|run anyway", "skip")
    s.log_decision("dev-backend", "02-b", "scope-gap", "step 5", "same tension again", "skip|run anyway", "skip")
    s.log_decision("product-manager", "01-a", "other-topic", "r2", "p2", "c2", "d2")

    everything = s.export_decisions_markdown()
    assert everything["count"] == 3
    assert "Agent: product-manager" in everything["markdown"]
    assert "Story: 01-a" in everything["markdown"]
    assert "Ref: step 5" in everything["markdown"]
    assert "Decision: skip" in everything["markdown"]

    by_story = s.export_decisions_markdown(story="01-a")
    assert by_story["count"] == 2
    assert "02-b" not in by_story["markdown"]

    by_agent = s.export_decisions_markdown(agent="dev-backend")
    assert by_agent["count"] == 1
    assert "same tension again" in by_agent["markdown"]

    none_found = s.export_decisions_markdown(story="no-such-story")
    assert none_found == {"markdown": "", "count": 0}


def test_task_checkpoint_upserts_without_claim(s):
    r1 = s.task_checkpoint(story="s5", role="analyst", status="done", detail="plan written")
    assert r1["status"] == "done"
    tid = r1["id"]
    rows = s.task_list(story="s5")
    assert len(rows) == 1
    assert rows[0]["id"] == tid
    assert rows[0]["role"] == "analyst"
    assert rows[0]["status"] == "done"
    assert rows[0]["claimed_by"] == "analyst"

    # same (story, role) pair again -> updates the same row, no duplicate
    r2 = s.task_checkpoint(story="s5", role="analyst", status="failed", result="reverted")
    assert r2["id"] == tid
    rows = s.task_list(story="s5")
    assert len(rows) == 1
    assert rows[0]["status"] == "failed"
    assert rows[0]["result"] == "reverted"

    # a different role on the same story is a separate row
    s.task_checkpoint(story="s5", role="dev-backend", status="done")
    assert len(s.task_list(story="s5")) == 2

    with pytest.raises(ValueError):
        s.task_checkpoint(story="s5", role="analyst", status="bogus")


# ---------------------------------------------------------------- tasks
def test_task_flow_priority_dependencies_and_ownership(s):
    t1 = s.task_post("plan", story="s1", role="analyst", priority=5)["id"]
    t2 = s.task_post("code", story="s1", role="dev-backend", depends_on=[t1])["id"]
    assert s.task_claim("dev-backend", story="s1", role="dev-backend") is None       # blocked by t1
    assert s.task_list(story="s1")[1]["blocked_by"] == [t1]
    assert s.task_claim("dev-frontend", story="s1", role="dev-frontend") is None       # t1 is for analyst, t2 blocked
    c = s.task_claim("analyst", story="s1", role="analyst")
    assert c["id"] == t1 and c["claimed_by"] == "analyst"
    with pytest.raises(ValueError): s.task_finish(t1, "someone-else")
    s.task_finish(t1, "analyst", "done", "plan appended")
    c2 = s.task_claim("dev-backend", story="s1", role="dev-backend")
    assert c2["id"] == t2
    s.task_finish(t2, "dev-backend", "failed", "tests red")
    assert [t["status"] for t in s.task_list(story="s1")] == ["done", "failed"]


def test_expired_lease_is_reclaimed(s, monkeypatch):
    t = s.task_post("x")["id"]
    s.task_claim("a1", lease_seconds=30)
    real = time.time
    monkeypatch.setattr(time, "time", lambda: real() + 3600)
    again = s.task_claim("a2")
    assert again["id"] == t and again["claimed_by"] == "a2"


def _claimer(args):
    path, name = args
    got = []
    st = Store(path)
    while True:
        t = st.task_claim(name)
        if not t:
            return got
        got.append(t["id"])


def test_concurrent_claims_never_double_assign(db):
    st = Store(db)
    ids = {st.task_post(f"t{i}")["id"] for i in range(60)}
    with mp.get_context("spawn").Pool(6) as pool:
        results = pool.map(_claimer, [(str(db), f"agent{i}") for i in range(6)])
    flat = [i for r in results for i in r]
    assert sorted(flat) == sorted(ids) and len(flat) == len(set(flat))     # each task exactly once


# ---------------------------------------------------------------- locks
def test_locks_exclusive_reentrant_expiring(s, monkeypatch):
    assert s.lock_acquire("src/locales/en.json", "dev-frontend", ttl_seconds=60)["acquired"]
    r = s.lock_acquire(".\\src\\locales\\en.json".replace("\\", "/"), "dev-backend")
    assert r["acquired"] is False and r["holder"] == "dev-frontend"
    assert s.lock_acquire("src/locales/en.json", "dev-frontend")["acquired"]         # re-entrant
    assert s.lock_release("src/locales/en.json", "dev-backend") == {"released": False}
    assert len(s.lock_list()) == 1
    real = time.time
    monkeypatch.setattr(time, "time", lambda: real() + 7200)
    assert s.lock_acquire("src/locales/en.json", "dev-backend")["acquired"]          # old lock expired


def _locker(args):
    path, name = args
    return Store(path).lock_acquire("contracts/openapi.yaml", name)["acquired"]


def test_concurrent_lock_has_single_winner(db):
    Store(db)
    with mp.get_context("spawn").Pool(6) as pool:
        wins = pool.map(_locker, [(str(db), f"a{i}") for i in range(6)])
    assert sum(wins) == 1


# ---------------------------------------------------------------- story context
def test_story_context_bundles_everything(s):
    s.remember("analyst", "convention", "problem+json errors", key="errors")
    s.remember("dev-backend", "gotcha", "N+1 on orders list", story="s1")
    s.remember("product-manager", "handoff", "stopped after backend review", story="s1")
    s.log_decision("dev-frontend", "s1", "copy", "AC1", "p", "c", "d")
    t = s.task_post("wire", story="s1")["id"]
    s.lock_acquire("package.json", "dev-frontend", story="s1")
    ctx = s.story_context("s1")
    assert ctx["handoff"]["content"].startswith("stopped")
    assert {k["kind"] for k in ctx["knowledge"]} == {"convention", "gotcha"}
    assert len(ctx["decisions"]) == 1 and ctx["tasks"][0]["id"] == t and ctx["locks"][0]["resource"] == "package.json"


# ---------------------------------------------------------------- real MCP protocol over stdio
def _is_error(r):  # mcp 1.x: isError, mcp 2.x: is_error
    return bool(getattr(r, "is_error", getattr(r, "isError", False)))


def _payload(r):
    sc = getattr(r, "structured_content", None) or getattr(r, "structuredContent", None)
    return sc if sc else json.loads(r.content[0].text)


def test_mcp_stdio_roundtrip(tmp_path):
    pytest.importorskip("mcp")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def go():
        params = StdioServerParameters(command=sys.executable, args=[str(HERE / "server.py")],
                                       env={**os.environ, "TEAM_MEMORY_DB": str(tmp_path / "p.db")})
        async with stdio_client(params) as streams:
            async with ClientSession(streams[0], streams[1]) as sess:
                await sess.initialize()
                names = {t.name for t in (await sess.list_tools()).tools}
                assert {"remember", "recall", "task_claim", "lock_acquire", "story_context"} <= names
                r = await sess.call_tool("remember", {"agent": "analyst", "kind": "gotcha", "content": "use UTC everywhere", "story": "s1"})
                assert not _is_error(r)
                r = await sess.call_tool("recall", {"query": "UTC"})
                payload = _payload(r)
                assert payload["items"][0]["content"] == "use UTC everywhere"
                bad = await sess.call_tool("remember", {"agent": "bad agent", "kind": "note", "content": "x"})
                assert _is_error(bad)                                           # validation surfaces as a tool error
                res = await sess.read_resource("team-memory://story/s1")
                assert "use UTC everywhere" in res.contents[0].text

    asyncio.run(go())


# ---------------------------------------------------------------- default database location
def _git(cwd, *args):
    import subprocess
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=cwd, check=True, capture_output=True)


def test_default_db_shared_across_git_worktrees(tmp_path, monkeypatch):
    main = tmp_path / "repo"
    main.mkdir()
    _git(main, "init", "-q", "-b", "dev")
    (main / "f").write_text("x")
    _git(main, "add", "f")
    _git(main, "commit", "-qm", "init")
    wt = tmp_path / "repo-wt-a"
    _git(main, "worktree", "add", "-q", str(wt), "-b", "feature/a", "dev")
    monkeypatch.delenv("TEAM_MEMORY_DB", raising=False)
    expected = (main / ".pipeline" / "team-memory.db").resolve()
    monkeypatch.chdir(wt)
    assert default_db_path().resolve() == expected                 # worktree -> main workspace DB
    monkeypatch.chdir(main)
    assert default_db_path().resolve() == expected                 # main itself
    sub = main / "sub"; sub.mkdir(); monkeypatch.chdir(sub)
    assert default_db_path().resolve() == expected                 # subfolder of the repo


def test_default_db_fallback_and_env_override(tmp_path, monkeypatch):
    plain = tmp_path / "not-a-repo"; plain.mkdir()
    monkeypatch.delenv("TEAM_MEMORY_DB", raising=False)
    monkeypatch.chdir(plain)
    assert default_db_path().resolve() == (plain / ".pipeline" / "team-memory.db").resolve()
    monkeypatch.setenv("TEAM_MEMORY_DB", str(tmp_path / "custom.db"))
    assert default_db_path() == tmp_path / "custom.db"
