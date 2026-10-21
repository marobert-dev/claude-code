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


def test_recall_defaults_are_compact_and_overridable(s):
    for n in range(9):
        s.remember("a", "fact", "alpha " + "z" * 900, key=f"k{n}")
    items = s.recall("alpha")
    assert len(items) == 6 and all(len(i["content"]) < 700 for i in items)
    wide = s.recall("alpha", limit=9, snippet=2000)
    assert len(wide) == 9 and all(len(i["content"]) > 900 for i in wide)


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


def test_export_decisions_files_appends_per_agent_once(s, tmp_path):
    s.log_decision("analyst", "01-a", "scope-gap", "AC2", "no limit given", "10|20", "20")
    s.log_decision("dev-backend", "01-a", "retry", "AC3", "timeout unclear", "5s|30s", "30s")
    s.log_decision("analyst", "02-b", "other", "r", "p", "c", "d")
    handwritten = tmp_path / ".decisions" / "analyst.decisions.md"
    handwritten.parent.mkdir()
    handwritten.write_text("Agent: analyst\nStory: 00 - setup\nDecision: written by hand", encoding="utf-8")

    first = s.export_decisions_files("01-a", tmp_path)
    again = s.export_decisions_files("01-a", tmp_path)

    assert first["written"] == {"analyst": 1, "dev-backend": 1}
    assert again["written"] == {}
    analyst = handwritten.read_text(encoding="utf-8")
    assert analyst.startswith("Agent: analyst\nStory: 00 - setup")
    assert "\n\nAgent: analyst\nStory: 01-a\n" in analyst
    assert analyst.count("Story: 01-a") == 1 and "02-b" not in analyst
    assert "Decision: 30s" in (tmp_path / ".decisions" / "dev-backend.decisions.md").read_text(encoding="utf-8")


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
                assert {"remember", "recall", "task_claim", "lock_acquire", "story_context", "agent_briefing", "export_decisions_files", "task_checkpoint", "contract_lookup", "conventions",
                        "similar_stories", "queue_status", "rules_briefing", "promote_rules", "flaky_report", "flaky_list",
                        "flaky_resolve", "usage_report"} <= names
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


# ---------------------------------------------------------------- token savers
OPENAPI = """\
openapi: 3.1.0
info:
  title: Demo
paths:
  /api/items:
    get:
      operationId: listItems
      summary: List the caller's items.
      tags: [items]
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ItemList'
        '401':
          $ref: '#/components/responses/Unauthenticated'
    post:
      operationId: createItem
      summary: Create an item.
      tags:
        - items
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateItem'
      responses:
        '201':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Item'
        '401':
          $ref: '#/components/responses/Unauthenticated'
  /api/items/{id}:
    parameters:
      - $ref: '#/components/parameters/ItemId'
    patch:
      operationId: updateItem
      summary: Update an item.
      responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Item'
        '401':
          $ref: '#/components/responses/Unauthenticated'
        '404':
          $ref: '#/components/responses/ItemNotFound'
    delete:
      operationId: deleteItem
      summary: Delete an item.
      responses:
        '204':
          description: gone
        '401':
          $ref: '#/components/responses/Unauthenticated'
  /api/health:
    get:
      operationId: getHealth
      summary: Liveness probe.
      responses:
        '200':
          description: ok
components:
  parameters:
    ItemId:
      name: id
      in: path
  responses:
    Unauthenticated:
      description: no token
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
    ItemNotFound:
      description: unknown item
  schemas:
    ErrorResponse:
      type: object
    Item:
      type: object
      properties:
        qty:
          $ref: '#/components/schemas/Quantity'
    Quantity:
      type: object
    CreateItem:
      type: object
    ItemList:
      type: array
"""


@pytest.fixture()
def ws(tmp_path, monkeypatch):
    """A workspace with a contract, conventions and story folders; the cwd is the workspace."""
    (tmp_path / "contracts").mkdir()
    (tmp_path / "contracts" / "openapi.yaml").write_text(OPENAPI, encoding="utf-8")
    (tmp_path / ".pipeline").mkdir()
    (tmp_path / ".pipeline" / "conventions.md").write_text(
        "# Project conventions\n\n## Backend\nExpress routes live in src/routes. Zod validates bodies.\n\n"
        "## Frontend (web)\nVanilla JS controllers, i18n keys in locales/.\n\n"
        "## Tests\nJest with supertest; mongodb-memory-server for the database.\n\n"
        "## Change log\nstories 1-5 added things\n", encoding="utf-8")
    for d, names in ((".user-stories", ["03-b.md", "02-a.md"]), (".completed", ["01-items-post-endpoint.md", "00-items-get-endpoint.md"])):
        (tmp_path / d).mkdir()
        for n in names:
            (tmp_path / d / n).write_text("# story\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return Store(tmp_path / ".pipeline" / "team-memory.db", root=tmp_path)


def test_contract_lookup_outline_operation_path_component_and_fuzzy(ws):
    outline = ws.contract_lookup()
    assert len(outline["outline"]) == 5 and "PATCH /api/items/{id} updateItem - Update an item." in outline["outline"]
    assert outline["components"]["schemas"] == ["CreateItem", "ErrorResponse", "Item", "ItemList", "Quantity"]
    assert outline["returned_chars"] < outline["file_chars"]

    one = ws.contract_lookup("updateItem")
    assert [o["operationId"] for o in one["operations"]] == ["updateItem"]
    assert "ItemId" in one["operations"][0]["path_level_yaml"]
    assert set(one["components"]) == {"schemas/Item", "schemas/Quantity", "parameters/ItemId", "responses/ItemNotFound"}   # transitive, schemas first
    assert "createitem" not in json.dumps(one).lower()                       # nothing else leaks in
    assert one["common_components_omitted"] == ["schemas/ErrorResponse", "responses/Unauthenticated"]   # referenced by most operations
    assert "schemas/ErrorResponse" in ws.contract_lookup("updateItem", include_common=True)["components"]

    by_route = ws.contract_lookup("DELETE /api/items/{id}")
    assert [o["operationId"] for o in by_route["operations"]] == ["deleteItem"]
    both = ws.contract_lookup("/api/items/{id}")
    assert [o["operationId"] for o in both["operations"]] == ["updateItem", "deleteItem"]

    comp = ws.contract_lookup("schemas/Item")
    assert list(comp["components"]) == ["schemas/Item", "schemas/Quantity"]
    assert "operations" not in comp
    assert ws.contract_lookup("quantity")["components"].keys() == {"schemas/Quantity"}

    fuzzy = ws.contract_lookup("create item")
    assert [o["operationId"] for o in fuzzy["operations"]] == ["createItem"]
    several = ws.contract_lookup("items")
    assert len(several["matches"]) > 2 and "operations" not in several and "hint" in several
    assert "hint" in ws.contract_lookup("zzzz")


def test_contract_lookup_budget_and_path_safety(ws, tmp_path):
    small = ws.contract_lookup("/api/items/{id}", max_chars=2000)
    assert small["returned_chars"] < 6000
    tight = ws.contract_lookup("updateItem", max_chars=2000)                 # operation alone fits, extras are named not dropped silently
    assert "operations" in tight
    with pytest.raises(ValueError): ws.contract_lookup(file="../outside.yaml")
    with pytest.raises(ValueError): ws.contract_lookup(file="/etc/passwd.yaml")
    with pytest.raises(ValueError): ws.contract_lookup(file="contracts/openapi.json")
    with pytest.raises(ValueError): ws.contract_lookup(file="contracts/missing.yaml")
    (tmp_path / "contracts" / "openapi.yaml").write_text(OPENAPI.replace("listItems", "listAllItems"), encoding="utf-8")
    assert any("listAllItems" in line for line in ws.contract_lookup()["outline"])    # changed file is re-indexed


def test_conventions_by_role_topic_and_outline(ws):
    outline = ws.conventions()
    assert outline["sections"] == [] and {o["heading"] for o in outline["other_sections"]} >= {"Backend", "Tests", "Change log"}
    be = ws.conventions(role="dev-backend")
    heads = [s["heading"] for s in be["sections"]]
    assert heads[0] == "Backend" and "Tests" in heads and "Frontend (web)" not in heads and "Change log" not in heads
    assert sum(len(s["content"]) for s in be["sections"]) < be["file_chars"]
    fe = ws.conventions(role="dev-frontend", topic="i18n")
    assert [s["heading"] for s in fe["sections"]] == ["Frontend (web)"]
    assert [s["heading"] for s in ws.conventions(topic="supertest")["sections"]] == ["Tests"]
    with pytest.raises(ValueError): ws.conventions(file="../x.md")


def test_agent_briefing_bundles_story_context_and_role_conventions(ws):
    ws.remember("code-reviewer", "review-pattern", "Validate ids at the boundary", key="ids")
    ws.log_decision("analyst", "20-x", "id-format", "AC", "p", "c", "ids are uuids")
    ws.task_post("Obsolete test: a", story="20-x", role="unit-tester")
    ws.task_post("Wire x", story="20-x", role="dev-backend")
    b = ws.agent_briefing("20-x", "dev-backend")
    assert b["story"] == "20-x" and b["role"] == "dev-backend"
    assert [k["kind"] for k in b["knowledge"]] == ["review-pattern"]
    assert [d["story"] for d in b["decisions"]] == ["20-x"]
    assert [t["role"] for t in b["tasks"]] == ["dev-backend"]                                   # other roles' tasks stay out
    heads = [c["heading"] for c in b["conventions"]["sections"]]
    assert heads[0] == "Backend" and "Frontend (web)" not in heads
    tools = {t["tool"]: t for t in ws.usage_report()["by_tool"]}
    assert tools["agent_briefing"]["calls"] == 1 and "story_context" not in tools and "conventions" not in tools
    assert {a["agent"] for a in ws.usage_report()["by_agent"]} == {"dev-backend"}


def test_agent_briefing_without_conventions_file_and_capped(s, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for i in range(8):
        s.remember("analyst", "fact", f"fact {i} " + "x" * 700, story="21-y", key=f"k{i}")
    b = s.agent_briefing("21-y", "analyst", max_chars=4000)
    assert "missing" in b["conventions"] and b.get("truncated")
    assert len(json.dumps(b)) <= 4500
    with pytest.raises(ValueError): s.agent_briefing("21-y", "")


def test_rules_promote_automatically_and_reach_story_context(ws):
    r1 = ws.log_decision("analyst", "10-a", "list-shape", "AC", "p", "c", "q is the only list parameter")
    assert "rule_promoted" not in r1
    ws.log_decision("analyst", "10-a", "list-shape", "AC", "p", "c", "same story again")           # same story twice is not recurrence
    assert ws.rules_briefing()["count"] == 0
    r2 = ws.log_decision("analyst", "11-b", "list-shape", "AC", "p", "c", "q only, search is a 400")
    assert r2["rule_promoted"] == ["list-shape"]
    rules = ws.rules_briefing()["rules"]
    assert rules[0]["key"] == "topic:list-shape" and "search is a 400" in rules[0]["content"]
    assert ws.promote_rules()["promoted"] == []                                                       # idempotent
    ctx = ws.story_context("12-c")
    assert [r["key"] for r in ctx["rules"]] == ["topic:list-shape"]
    assert "rule" not in {k["kind"] for k in ctx["knowledge"]}
    ws.remember("product-manager", "rule", "Curated: q only; 400 otherwise.", key="topic:list-shape")   # curated text replaces the auto one
    assert ws.rules_briefing()["rules"][0]["content"].startswith("Curated")
    ws.retire_memory(ws.rules_briefing()["rules"][0]["id"], "product-manager")
    ws.log_decision("analyst", "13-d", "list-shape", "AC", "p", "c", "again")
    assert ws.rules_briefing()["count"] == 0                                                          # retired stays retired


def test_similar_stories_prefers_rare_words_and_points_to_story_files(ws):
    ws.remember("pm", "fact", "POST /api/items in routes/items.js", story="01-items-post-endpoint", key="story:01-items-post-endpoint")
    ws.log_decision("analyst", "01-items-post-endpoint", "expiry-format", "AC", "p", "c", "YYYY-MM-DD only")
    ws.remember("pm", "fact", "GET /api/meals", story="05-meals-get-endpoint", key="story:05-meals-get-endpoint")
    ws.remember("pm", "fact", "GET /api/food-guide", story="06-food-guide-list-endpoint", key="story:06-food-guide-list-endpoint")
    res = ws.similar_stories("07-catalog-items-create-endpoint")                                      # create ~ post, items shared
    assert res["similar"][0]["story"] == "01-items-post-endpoint"
    top = res["similar"][0]
    assert top["story_file"] == ".completed/01-items-post-endpoint.md" and "routes/items.js" in top["built"]
    assert top["decisions"][0]["decision"] == "YYYY-MM-DD only"
    assert "00-items-get-endpoint" in {s["story"] for s in res["similar"]}                            # known from .completed/ alone
    assert all(s["story"] != "06-food-guide-list-endpoint" for s in res["similar"])                   # sharing only 'endpoint' is not similarity
    assert ws.similar_stories("99-zzz-thing")["similar"] == []


def test_queue_status_summarises_pipeline_state(ws):
    ws.remember("pm", "fact", "built items post", story="01-items-post-endpoint", key="story:01-items-post-endpoint")
    ws.remember("pm", "handoff", "stopped after dev", story="02-a", key="handoff")
    ws.task_checkpoint("02-a", "analyst", "done")
    ws.task_checkpoint("02-a", "dev-backend", "claimed")
    ws.task_post("Obsolete test: x", story="02-a", role="unit-tester")                                # side queue is not a pipeline stage
    q = ws.queue_status()
    assert q["completed_stories"] == 1 and q["recent_done"][0]["story"] == "01-items-post-endpoint"
    assert q["in_progress"] == {"story": "02-a", "stages": {"analyst": "done", "dev-backend": "claimed"}}
    assert q["last_handoff"]["content"] == "stopped after dev"
    assert q["queue"] == {"pending": 2, "next": ["02-a", "03-b"], "completed_files": 2}
    ws.remember("pm", "fact", "built a", story="02-a", key="story:02-a")
    assert ws.queue_status()["in_progress"] is None                                                   # a story with its completion fact is done


def test_flaky_registry(ws):
    assert ws.flaky_report("items.update.test.js", "story-validator", story="33-x", cause="port clash")["count"] == 1
    assert ws.flaky_report("items.update.test.js", "product-manager")["count"] == 2
    ws.flaky_report("other.test.js", "story-validator")
    lst = ws.flaky_list()
    assert [f["test"] for f in lst] == ["items.update.test.js", "other.test.js"] and lst[0]["cause"] == "port clash"
    assert [f["test"] for f in ws.flaky_list(min_count=2)] == ["items.update.test.js"]
    assert ws.flaky_resolve("items.update.test.js", "product-manager") == {"resolved": True}
    assert [f["test"] for f in ws.flaky_list()] == ["other.test.js"]
    assert ws.flaky_report("items.update.test.js", "story-validator")["count"] == 3 and len(ws.flaky_list()) == 2   # flakes again -> back on the list
    with pytest.raises(ValueError): ws.flaky_report("", "a")


def test_usage_report_and_story_context_cap(ws, monkeypatch):
    for i in range(6):
        ws.remember("analyst", "fact", f"fact {i} " + "x" * 700, story="s9", key=f"k{i}")
    full = ws.story_context("s9", agent="analyst")
    capped = ws.story_context("s9", agent="dev-backend", max_chars=2000)
    assert capped.get("truncated") and len(json.dumps(capped)) < len(json.dumps(full)) and len(json.dumps(capped)) <= 2000
    ws.recall("fact", agent="analyst")
    ws.contract_lookup(agent="analyst")
    forgotten = ws.remember("analyst", "note", "nobody ever reads this", story="s10")["id"]
    rep = ws.usage_report()
    tools = {t["tool"]: t for t in rep["by_tool"]}
    assert {"story_context", "recall", "contract_lookup"} <= set(tools) and tools["story_context"]["calls"] == 2
    assert {a["agent"] for a in rep["by_agent"]} == {"analyst", "dev-backend"}
    assert rep["est_tokens_returned"] == rep["chars_returned"] // 4 and rep["never_recalled"] == [] and rep["note"]
    # after two weeks of tracking, entries nobody ever recalled are listed as prune candidates
    real_time = time.time
    monkeypatch.setattr(time, "time", lambda: real_time() + 15 * 86400)
    assert {i["kind"] for i in ws.recall("fact", kind="fact", agent="analyst")} == {"fact"}            # the facts get recalled, the note never
    stale = ws.usage_report()["never_recalled"]
    assert [s["id"] for s in stale] == [forgotten]
