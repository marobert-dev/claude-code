"""Tests for learn.py. Run: python -m unittest -v test_learn  (from this folder; stdlib only)."""
import contextlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("learn", HERE / "learn.py")
learn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(learn)

POSIX = os.name != "nt"


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.env_backup = dict(os.environ)
        os.environ["LEARN_HOME"] = str(t / "learnings")
        os.environ["LEARN_GLOBAL_MD"] = str(t / "global" / "CLAUDE.md")
        os.environ["LEARN_SETTINGS"] = str(t / "settings.json")
        os.environ.pop(learn.ANALYZER_ENV, None)
        os.environ["LEARN_AUTO_ANALYZE"] = "0"
        self.t = t
        self.repo = t / "repo-a"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "remote", "add", "origin", "git@github.com:Owner/Repo-A.git")
        self.repo_b = t / "repo-b"
        self.repo_b.mkdir()
        git(self.repo_b, "init", "-q")
        git(self.repo_b, "remote", "add", "origin", "https://user:pw@github.com/Owner/Repo-B.git")

    def tearDown(self):
        learn.close_all()
        os.environ.clear()
        os.environ.update(self.env_backup)
        self.tmp.cleanup()

    def run_cli(self, *argv, stdin=None):
        out = io.StringIO()
        old_stdin = sys.stdin
        sys.stdin = io.StringIO(stdin if stdin is not None else "")
        try:
            with contextlib.redirect_stdout(out):
                rc = learn.main(list(argv))
        finally:
            sys.stdin = old_stdin
        return rc, out.getvalue()

    def project_id(self, repo):
        conn = learn.connect()
        return learn.upsert_project(conn, learn.resolve_project(str(repo))), conn

    def add(self, text, scope="project", repo=None, status="approved", **kw):
        pid, conn = self.project_id(repo or self.repo)
        lid, _ = learn.add_learning(conn, scope=scope, pid=pid, kind=kw.pop("kind", "rule"), text=text,
                                    status=status, **kw)
        return lid, conn


class TestIdentity(Base):
    def test_normalize_remote(self):
        n = learn.normalize_remote
        self.assertEqual(n("git@github.com:Owner/Repo.git"), "github.com/owner/repo")
        self.assertEqual(n("https://user:tok@GitHub.com/Owner/Repo.git"), "github.com/owner/repo")
        self.assertEqual(n("ssh://git@host.example:2222/a/b.git"), "host.example/a/b")
        self.assertIsNone(n(""))
        self.assertIsNone(n("not a url"))

    def test_project_key_from_remote_and_path_fallback(self):
        p = learn.resolve_project(str(self.repo))
        self.assertEqual((p["key"], p["name"], p["via"]), ("github.com/owner/repo-a", "repo-a", "remote"))
        plain = self.t / "plain"
        plain.mkdir()
        q = learn.resolve_project(str(plain))
        self.assertEqual(q["via"], "path")
        self.assertTrue(q["key"].startswith("path:"))

    def test_same_remote_two_clones_same_project(self):
        clone = self.t / "clone"
        clone.mkdir()
        git(clone, "init", "-q")
        git(clone, "remote", "add", "origin", "https://github.com/owner/repo-a")
        self.assertEqual(learn.resolve_project(str(clone))["key"], learn.resolve_project(str(self.repo))["key"])


class TestStore(Base):
    def test_dedupe_including_rejected_and_cross_scope(self):
        lid, conn = self.add("Always run the gate before commit.", status="pending")
        _, new = learn.add_learning(conn, scope="project", pid=self.project_id(self.repo)[0], kind="rule",
                                    text="always run the gate before commit")
        self.assertFalse(new)
        conn.execute("UPDATE learnings SET status='rejected' WHERE id=?", (lid,))
        conn.commit()
        _, new = learn.add_learning(conn, scope="project", pid=self.project_id(self.repo)[0], kind="rule",
                                    text="Always run the gate before commit!")
        self.assertFalse(new, "a rejected learning must not come back")
        # same text in another project is allowed
        pid_b = self.project_id(self.repo_b)[0]
        _, new = learn.add_learning(conn, scope="project", pid=pid_b, kind="rule",
                                    text="Always run the gate before commit.")
        self.assertTrue(new)

    def test_project_duplicate_of_global_is_skipped(self):
        self.add("Never run python - on Windows.", scope="global")
        pid = self.project_id(self.repo)[0]
        conn = learn.connect()
        _, new = learn.add_learning(conn, scope="project", pid=pid, kind="pitfall",
                                    text="never run python - on windows")
        self.assertFalse(new)

    def test_global_must_have_no_project(self):
        conn = learn.connect()
        with self.assertRaises(Exception):
            conn.execute("INSERT INTO learnings(scope,project_id,kind,text,fingerprint,created_at) "
                         "VALUES('global',1,'rule','x','f',0)")

    def test_coerce_candidate_defaults_and_rejects(self):
        self.assertIsNone(learn.coerce_candidate({"text": "short"}))
        self.assertIsNone(learn.coerce_candidate("nope"))
        c = learn.coerce_candidate({"text": "A sufficiently long rule", "scope": "weird", "kind": "x",
                                    "confidence": "??", "supersedes": True})
        self.assertEqual((c["scope"], c["kind"], c["confidence"], c["supersedes"]), ("project", "rule", "medium", None))


class TestLoad(Base):
    def load(self, repo, event="SessionStart", extra=None):
        payload = {"cwd": str(repo), "session_id": "cur", "hook_event_name": event, **(extra or {})}
        rc, out = self.run_cli("load", "--event", event, stdin=json.dumps(payload))
        self.assertEqual(rc, 0)
        return json.loads(out) if out.strip() else {}

    def test_isolation_and_status_filter(self):
        self.add("Use pnpm in repo A.", repo=self.repo)
        self.add("Use yarn in repo B.", repo=self.repo_b)
        self.add("Global: answer tersely.", scope="global")
        self.add("Pending thing not loaded.", status="pending")
        self.add("Rejected thing not loaded.", status="rejected")
        res = self.load(self.repo)
        ctx = res["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(res["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertIn("Use pnpm in repo A.", ctx)
        self.assertIn("Global: answer tersely.", ctx)
        self.assertNotIn("yarn", ctx)
        self.assertNotIn("Pending thing", ctx)
        self.assertNotIn("Rejected thing", ctx)
        self.assertIn("1 learning(s) pending review", res["systemMessage"])

    def test_unknown_project_still_gets_global(self):
        self.add("Global: answer tersely.", scope="global")
        other = self.t / "brand-new"
        other.mkdir()
        res = self.load(other)
        self.assertIn("answer tersely", res["hookSpecificOutput"]["additionalContext"])

    def test_applied_to_claude_md_not_duplicated_in_session_but_in_subagent(self):
        lid, conn = self.add("Run gate.sh before any commit.")
        conn.execute("UPDATE learnings SET claude_md=1, claude_md_applied=1 WHERE id=?", (lid,))
        conn.commit()
        self.assertEqual(self.load(self.repo), {})
        sub = self.load(self.repo, "SubagentStart")
        self.assertIn("gate.sh", sub["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(sub["hookSpecificOutput"]["hookEventName"], "SubagentStart")
        self.assertNotIn("systemMessage", sub)

    def test_budget_keeps_highest_confidence(self):
        for i in range(6):
            self.add(f"Low confidence note number {i} xx.", confidence="low")
        self.add("High confidence rule here.", confidence="high")
        (Path(os.environ["LEARN_HOME"]) / "config.json").write_text(json.dumps({"session_budget_items": 2}))
        ctx = self.load(self.repo)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("High confidence rule here.", ctx)
        self.assertEqual(ctx.count("\n- "), 2)

    def test_no_database_is_silent_and_does_not_create_it(self):
        rc, out = self.run_cli("load", "--event", "SessionStart",
                               stdin=json.dumps({"cwd": str(self.repo)}))
        self.assertEqual((rc, out), (0, ""))
        self.assertFalse(learn.db_path().exists())

    def test_analyzer_env_guard(self):
        self.add("Something approved here.")
        os.environ[learn.ANALYZER_ENV] = "1"
        self.assertEqual(self.load(self.repo), {})
        rc, _ = self.run_cli("capture", stdin=json.dumps({"session_id": "s", "cwd": str(self.repo)}))
        conn = learn.connect()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 0)

    def test_load_real_process_stdin(self):
        self.add("Real process rule works.")
        env = dict(os.environ, PYTHONUTF8="1")
        r = subprocess.run([sys.executable, str(HERE / "learn.py"), "load", "--event", "SessionStart"],
                           input=json.dumps({"cwd": str(self.repo)}), capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Real process rule works.", json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"])


def line(**kw):
    return json.dumps(kw)


def user(text, **kw):
    return line(type="user", message={"role": "user", "content": text}, **kw)


def assistant(blocks, **kw):
    return line(type="assistant", message={"role": "assistant", "content": blocks}, **kw)


def tool_result(tid, content, is_error=False):
    return line(type="user", message={"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tid, "content": content, "is_error": is_error}]})


def sample_transcript():
    return [
        user("Please add pagination to the list endpoint, and use vitest not jest. " * 3),
        user("<system-reminder>injected</system-reminder>"),
        user("meta noise", isMeta=True),
        user("sidechain prompt", isSidechain=True),
        assistant([{"type": "text", "text": "I'll start with jest."},
                   {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "npx jest"}}]),
        tool_result("t1", "The user doesn't want to proceed with this tool use.", True),
        user("No. We use vitest. Run gate.sh before any commit, you forgot again. token=abcd1234secret"),
        assistant([{"type": "tool_use", "id": "t2", "name": "AskUserQuestion", "input": {"questions": [
            {"question": "Which test runner?", "options": [{"label": "vitest"}, {"label": "jest"}]}]}}]),
        tool_result("t2", 'User has answered your questions: "Which test runner?"="vitest".'),
        assistant([{"type": "tool_use", "id": "t3", "name": "Bash", "input": {"command": "python - <<EOF"}}]),
        tool_result("t3", "Command hangs on stdin", True),
        user("sk-abcdefghijklmnopqrstuvwxyz0123 is my key, remember pnpm only."),
    ]


class TestDigest(Base):
    def write(self, lines, name="t.jsonl", tail=""):
        p = self.t / name
        p.write_text("\n".join(lines) + "\n" + tail, encoding="utf-8")
        return p

    def test_digest_content(self):
        p = self.write(sample_transcript())
        entries, end = learn.read_transcript(str(p))
        self.assertEqual(end, p.stat().st_size)
        text = learn.fit_digest(learn.digest_items(entries), 60000)
        self.assertIn("[USER] Please add pagination", text)
        self.assertNotIn("injected", text)
        self.assertNotIn("meta noise", text)
        self.assertNotIn("sidechain prompt", text)
        self.assertIn("[REJECTED] Bash npx jest", text)
        self.assertIn("[ASKED] Which test runner? [vitest, jest]", text)
        self.assertIn('[ANSWER] User has answered your questions: "Which test runner?"="vitest".', text)
        self.assertIn("[ERROR] Bash python - <<EOF: Command hangs on stdin", text)
        self.assertNotIn("abcd1234secret", text)
        self.assertNotIn("sk-abcdefghijklmnopqrstuvwxyz0123", text)

    def test_partial_last_line_is_left_for_next_time(self):
        p = self.write(sample_transcript()[:2], tail='{"type":"user","message":{"cont')
        entries, end = learn.read_transcript(str(p))
        self.assertEqual(len(entries), 2)
        self.assertLess(end, p.stat().st_size)
        with open(p, "ab") as f:
            f.write(b'ent":"later message"}}\n')
        entries2, end2 = learn.read_transcript(str(p), end)
        self.assertEqual(len(entries2), 1)
        self.assertEqual(end2, p.stat().st_size)

    def test_cap_drops_assistant_text_first(self):
        items = [("user", "u" * 50), ("claude", "c" * 500), ("user", "v" * 50)]
        out = learn.fit_digest(items, 200)
        self.assertIn("[USER]", out)
        self.assertNotIn("[CLAUDE]", out)

    def test_cli_digest(self):
        p = self.write(sample_transcript())
        rc, out = self.run_cli("digest", str(p))
        self.assertEqual(rc, 0)
        self.assertIn("[ANSWER]", out)


@unittest.skipUnless(POSIX, "fake claude binary is a shell script")
class TestAnalyze(Base):
    def setUp(self):
        super().setUp()
        self.reply = self.t / "reply.json"
        self.stdin_dump = self.t / "stdin.txt"
        fake = self.t / "fake-claude"
        fake.write_text('#!/bin/sh\ncat > "$FAKE_STDIN"\ncat "$FAKE_REPLY"\n')
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        os.environ.update(LEARN_CLAUDE_BIN=str(fake), FAKE_REPLY=str(self.reply), FAKE_STDIN=str(self.stdin_dump))
        self.transcript = self.t / "sess1.jsonl"
        self.transcript.write_text("\n".join(sample_transcript()) + "\n", encoding="utf-8")

    def queue(self, sid="sess1", path=None):
        rc, _ = self.run_cli("capture", stdin=json.dumps({
            "session_id": sid, "cwd": str(self.repo), "transcript_path": str(path or self.transcript)}))
        self.assertEqual(rc, 0)

    def test_end_to_end_pending_candidates(self):
        self.add("Use jest in tests.", status="approved")
        self.reply.write_text("Here you go:\n" + json.dumps({"learnings": [
            {"scope": "project", "kind": "rule", "text": "Run gate.sh before any commit.", "rationale": "Forgotten twice.",
             "evidence": "you forgot again", "source": "correction", "confidence": "high", "claude_md": True,
             "supersedes": None},
            {"scope": "global", "kind": "pitfall", "text": "Never run python - with a heredoc on Windows.",
             "evidence": "Command hangs on stdin", "source": "error", "confidence": "high", "claude_md": True},
            {"scope": "project", "kind": "decision", "text": "Use vitest, not jest, for tests.",
             "source": "question", "confidence": "medium", "supersedes": 1},
            {"text": "x"},
        ]}) + "\nbye")
        self.queue()
        rc, out = self.run_cli("analyze", "--session", "sess1", "--verbose")
        self.assertEqual(out.strip(), "done")
        prompt = self.stdin_dump.read_text(encoding="utf-8")
        self.assertIn("Use jest in tests.", prompt)  # existing learnings reach the analyzer
        self.assertIn("[ANSWER]", prompt)
        self.assertNotIn("abcd1234secret", prompt)
        self.assertNotIn("{{", prompt)
        conn = learn.connect()
        rows = conn.execute("SELECT * FROM learnings WHERE status='pending' ORDER BY id").fetchall()
        self.assertEqual([r["scope"] for r in rows], ["project", "global", "project"])
        self.assertEqual(rows[2]["supersedes_id"], 1)
        self.assertEqual(rows[1]["project_id"], None)
        sess = conn.execute("SELECT * FROM sessions WHERE session_id='sess1'").fetchone()
        self.assertEqual((sess["status"], sess["candidates"]), ("done", 3))
        self.assertEqual(sess["analyzed_bytes"], self.transcript.stat().st_size)

    def test_failure_is_recorded_and_retried_then_capped(self):
        self.reply.write_text("not json at all")
        self.queue()
        self.run_cli("analyze", "--session", "sess1")
        conn = learn.connect()
        s = conn.execute("SELECT * FROM sessions").fetchone()
        self.assertEqual(s["status"], "failed")
        self.assertIn("no JSON", s["error"])
        self.reply.write_text(json.dumps({"learnings": []}))
        self.run_cli("analyze", "--session", "sess1", "--verbose")
        self.assertEqual(conn.execute("SELECT status FROM sessions").fetchone()[0], "done")

    def test_cli_option_rejection_falls_back_to_fewer_flags(self):
        fake = self.t / "picky-claude"
        fake.write_text('#!/bin/sh\ncat > "$FAKE_STDIN"\ncase "$*" in *--tools*) echo "error: unknown option --tools" >&2; exit 1;; esac\ncat "$FAKE_REPLY"\n')
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        os.environ["LEARN_CLAUDE_BIN"] = str(fake)
        self.reply.write_text(json.dumps({"learnings": []}))
        self.queue()
        _, out = self.run_cli("analyze", "--session", "sess1", "--verbose")
        self.assertEqual(out.strip(), "done")

    def test_non_option_failure_is_not_retried(self):
        counter = self.t / "calls.txt"
        fake = self.t / "down-claude"
        fake.write_text(f'#!/bin/sh\ncat > /dev/null\necho x >> "{counter}"\necho "network down" >&2\nexit 1\n')
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        os.environ["LEARN_CLAUDE_BIN"] = str(fake)
        self.queue()
        self.run_cli("analyze", "--session", "sess1")
        self.assertEqual(len(counter.read_text().split()), 1)

    def test_claude_nonzero_exit_marks_failed(self):
        os.environ["LEARN_CLAUDE_BIN"] = "false"
        self.queue()
        self.run_cli("analyze", "--session", "sess1")
        s = learn.connect().execute("SELECT * FROM sessions").fetchone()
        self.assertEqual(s["status"], "failed")

    def test_trivial_session_skipped_without_calling_claude(self):
        tiny = self.t / "tiny.jsonl"
        tiny.write_text(user("hi") + "\n")
        os.environ["LEARN_CLAUDE_BIN"] = "false"
        self.queue("tiny", tiny)
        _, out = self.run_cli("analyze", "--session", "tiny", "--verbose")
        self.assertEqual(out.strip(), "skipped")

    def test_resumed_session_analyses_only_new_part(self):
        self.reply.write_text(json.dumps({"learnings": []}))
        self.queue()
        self.run_cli("analyze", "--session", "sess1")
        first = self.stdin_dump.read_text(encoding="utf-8")
        self.assertIn("Please add pagination", first)
        with open(self.transcript, "a", encoding="utf-8") as f:
            f.write(user("Second part: always answer in French, this is a long enough message. " * 3) + "\n")
            f.write(user("And another follow up message that is meaningful enough for analysis here.") + "\n")
        self.queue()  # SessionEnd fires again for the resumed session
        self.run_cli("analyze", "--session", "sess1")
        second = self.stdin_dump.read_text(encoding="utf-8")
        self.assertIn("Second part", second)
        self.assertNotIn("Please add pagination", second)

    def test_sweep_finds_orphan_transcripts_and_skips_current_and_recent(self):
        self.reply.write_text(json.dumps({"learnings": [
            {"scope": "project", "kind": "rule", "text": "Orphan session learning is stored.", "confidence": "high"}]}))
        tdir = self.t / "transcripts"
        tdir.mkdir()
        conn = learn.connect()
        orphan, recent, current = tdir / "orphan.jsonl", tdir / "recent.jsonl", tdir / "cur.jsonl"
        for p in (orphan, recent, current):
            p.write_text("\n".join(sample_transcript()) + "\n", encoding="utf-8")
        old = time.time() - 3600
        os.utime(orphan, (old, old))
        os.utime(current, (old, old))
        conn.execute("UPDATE meta SET value=? WHERE key='installed_at'", (str(old - 100),))
        conn.commit()
        self.run_cli("sweep", "--cwd", str(self.repo), "--transcripts-dir", str(tdir), "--current", "cur")
        ids = {r[0]: r[1] for r in conn.execute("SELECT session_id, status FROM sessions")}
        self.assertEqual(ids, {"orphan": "done"})
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM learnings WHERE status='pending'").fetchone()[0], 1)

    def test_sweep_ignores_transcripts_older_than_install(self):
        tdir = self.t / "transcripts"
        tdir.mkdir()
        p = tdir / "ancient.jsonl"
        p.write_text("\n".join(sample_transcript()) + "\n", encoding="utf-8")
        conn = learn.connect()
        old = time.time() - 86400 * 30
        os.utime(p, (old, old))
        self.assertEqual(learn.find_unseen(conn, str(tdir), "x", learn.load_config()), [])

    def test_prompt_includes_claude_md_files(self):
        (self.repo / "CLAUDE.md").write_text("PROJECT-MD-MARKER", encoding="utf-8")
        gp = Path(os.environ["LEARN_GLOBAL_MD"])
        gp.parent.mkdir(parents=True)
        gp.write_text("GLOBAL-MD-MARKER", encoding="utf-8")
        self.reply.write_text(json.dumps({"learnings": []}))
        self.queue()
        self.run_cli("analyze", "--session", "sess1")
        prompt = self.stdin_dump.read_text(encoding="utf-8")
        self.assertIn("PROJECT-MD-MARKER", prompt)
        self.assertIn("GLOBAL-MD-MARKER", prompt)


class TestReviewFlow(Base):
    def pending(self, text, **kw):
        lid, conn = self.add(text, status="pending", **kw)
        return lid

    def test_report_sections_and_conflicts(self):
        a = self.pending("Run gate.sh before any commit.", claude_md=True, confidence="high", source="correction",
                         evidence="you forgot", rationale="Forgotten twice.")
        g = self.pending("Never run python - on Windows.", scope="global", kind="pitfall")
        old, _ = self.add("Use jest.", status="approved")
        pid, conn = self.project_id(self.repo)
        new, _ = learn.add_learning(conn, scope="project", pid=pid, kind="decision", text="Use vitest.",
                                    supersedes_id=old)
        self.pending("Other project pending.", repo=self.repo_b)
        rc, out = self.run_cli("report", "--cwd", str(self.repo))
        self.assertIn("# Learning report - repo-a", out)
        self.assertIn("## PROJECT (1)", out)
        self.assertIn("## GLOBAL (1)", out)
        self.assertIn("## CONFLICTS / DUPLICATES (1)", out)
        self.assertIn(f"#{a} [rule] conf:high  src:correction", out)
        self.assertIn("-> CLAUDE.md (project) + DB", out)
        self.assertIn("Replaces #", out)
        self.assertNotIn("Other project pending.", out)
        self.assertIn("1 pending in other projects", out)
        self.assertIn("Actions: approve 1,2", out)
        rc, allout = self.run_cli("report", "--cwd", str(self.repo), "--all")
        self.assertIn("Other project pending.", allout)

    def test_report_without_db(self):
        rc, out = self.run_cli("report", "--cwd", str(self.repo))
        self.assertIn("No learnings database yet", out)

    def test_act_approve_supersede_reject_defer_scope_edit(self):
        old, _ = self.add("Use jest.", status="approved")
        pid, conn = self.project_id(self.repo)
        new, _ = learn.add_learning(conn, scope="project", pid=pid, kind="decision", text="Use vitest.",
                                    supersedes_id=old)
        a = self.pending("Alpha rule pending text.")
        b = self.pending("Beta rule pending text.")
        c = self.pending("Gamma rule pending text.")
        d = self.pending("Delta rule pending text.")
        cwd = str(self.repo)
        _, out = self.run_cli("act", "approve", f"{new},{a}", "--cwd", cwd)
        self.assertIn(f"#{new}: approved (replaces #{old})", out)
        st = {r["id"]: r["status"] for r in conn.execute("SELECT id,status FROM learnings")}
        self.assertEqual((st[old], st[new], st[a]), ("superseded", "approved", "approved"))
        self.run_cli("act", "reject", str(b), "--cwd", cwd)
        self.run_cli("act", "defer", str(c), "--cwd", cwd)
        self.run_cli("act", "scope", str(d), "--to", "global", "--cwd", cwd)
        self.run_cli("act", "edit", str(d), "--text", "Delta rule, reworded and clearer.", "--cwd", cwd)
        row = conn.execute("SELECT * FROM learnings WHERE id=?", (d,)).fetchone()
        self.assertEqual((row["scope"], row["project_id"], row["text"]), ("global", None, "Delta rule, reworded and clearer."))
        st = {r["id"]: r["status"] for r in conn.execute("SELECT id,status FROM learnings")}
        self.assertEqual((st[b], st[c]), ("rejected", "deferred"))
        # deferred items can still be approved later
        self.run_cli("act", "approve", str(c), "--cwd", cwd)
        self.assertEqual(conn.execute("SELECT status FROM learnings WHERE id=?", (c,)).fetchone()[0], "approved")
        # a rejected one is never offered again by "approve all"
        self.pending("Epsilon rule pending text.")
        self.run_cli("act", "approve", "all", "--cwd", cwd)
        self.assertEqual(conn.execute("SELECT status FROM learnings WHERE id=?", (b,)).fetchone()[0], "rejected")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM learnings WHERE status='pending'").fetchone()[0], 0)

    def test_act_errors(self):
        a = self.pending("Alpha rule pending text.")
        rc, out = self.run_cli("act", "approve", "999", "--cwd", str(self.repo))
        self.assertEqual(rc, 1)
        self.assertIn("not found", out)
        rc, out = self.run_cli("act", "forget", str(a), "--cwd", str(self.repo))
        self.assertIn("only approved", out)
        rc, out = self.run_cli("act", "approve", "x,y", "--cwd", str(self.repo))
        self.assertEqual(rc, 2)

    def test_scope_to_global_collision(self):
        self.add("Same text for scope collision.", scope="global")
        pid, conn = self.project_id(self.repo)
        conn.execute("INSERT INTO learnings(scope,project_id,kind,text,fingerprint,created_at) VALUES('project',?,'rule','Same text','zzz',0)", (pid,))
        conn.commit()
        lid = conn.execute("SELECT id FROM learnings WHERE fingerprint='zzz'").fetchone()[0]
        conn.execute("UPDATE learnings SET fingerprint=? WHERE id=?", (learn.fingerprint("Same text for scope collision."), lid))
        conn.commit()
        rc, out = self.run_cli("act", "scope", str(lid), "--to", "global", "--cwd", str(self.repo))
        self.assertEqual(rc, 1)
        self.assertIn("identical", out)

    def test_add_and_list(self):
        self.run_cli("add", "--scope", "global", "--text", "Answer in French in chat.", "--cwd", str(self.repo))
        self.run_cli("add", "--scope", "project", "--text", "Stories live in .user-stories.", "--cwd", str(self.repo))
        self.run_cli("add", "--scope", "project", "--text", "Other repo rule goes here.", "--cwd", str(self.repo_b))
        _, out = self.run_cli("list", "--cwd", str(self.repo))
        self.assertIn("Answer in French", out)
        self.assertIn("Stories live", out)
        self.assertNotIn("Other repo rule", out)
        self.assertIn("project:repo-a", out)
        _, out = self.run_cli("list", "--cwd", str(self.repo), "--all")
        self.assertIn("Other repo rule", out)


class TestClaudeMd(Base):
    def setup_two(self):
        a, conn = self.add("Run gate.sh before any commit.", claude_md=True)
        g, _ = self.add("Never run python - on Windows.", scope="global", claude_md=True)
        self.add("DB only learning stays out.", claude_md=False)
        return a, g, conn

    def test_plan_then_apply_then_idempotent(self):
        a, g, conn = self.setup_two()
        cwd = str(self.repo)
        _, plan = self.run_cli("claude-md", "plan", "--cwd", cwd)
        self.assertIn("+- Run gate.sh before any commit. <!-- L%d -->" % a, plan)
        self.assertIn("(new file)", plan)
        self.assertIn("Never run python - on Windows.", plan)
        self.assertNotIn("DB only", plan)
        self.assertFalse((self.repo / "CLAUDE.md").exists(), "plan must not write")
        _, out = self.run_cli("claude-md", "apply", "--cwd", cwd)
        proj_md = (self.repo / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn(learn.MD_START, proj_md)
        self.assertIn(f"- Run gate.sh before any commit. <!-- L{a} -->", proj_md)
        self.assertIn(f"- Never run python - on Windows. <!-- L{g} -->", Path(os.environ["LEARN_GLOBAL_MD"]).read_text(encoding="utf-8"))
        rows = {r["id"]: r for r in conn.execute("SELECT * FROM learnings")}
        self.assertEqual((rows[a]["claude_md_applied"], rows[a]["applied_file"]), (1, str(self.repo / "CLAUDE.md")))
        _, again = self.run_cli("claude-md", "plan", "--cwd", cwd)
        self.assertEqual(again.strip(), "NOTHING TO DO")

    def test_preserves_existing_content_crlf_and_makes_backup(self):
        md = self.repo / "CLAUDE.md"
        md.write_bytes(b"# Project\r\n\r\nExisting rules.\r\n")
        a, _ = self.add("Run gate.sh before any commit.", claude_md=True)
        self.run_cli("claude-md", "apply", "--cwd", str(self.repo))
        raw = md.read_bytes()
        self.assertTrue(raw.startswith(b"# Project\r\n\r\nExisting rules.\r\n"))
        self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))
        self.assertTrue(list((Path(os.environ["LEARN_HOME"]) / "backups").glob("*.bak")))

    def test_forget_removes_line_and_empty_block(self):
        md = self.repo / "CLAUDE.md"
        md.write_text("# Project\n\nExisting rules.\n", encoding="utf-8")
        a, conn = self.add("Run gate.sh before any commit.", claude_md=True)
        b, _ = self.add("Use vitest, not jest.", claude_md=True)
        cwd = str(self.repo)
        self.run_cli("claude-md", "apply", "--cwd", cwd)
        self.run_cli("act", "forget", str(a), "--cwd", cwd)
        _, plan = self.run_cli("claude-md", "plan", "--cwd", cwd)
        self.assertIn(f"-- Run gate.sh before any commit. <!-- L{a} -->".replace("--", "-", 1), plan)
        self.run_cli("claude-md", "apply", "--cwd", cwd)
        text = md.read_text(encoding="utf-8")
        self.assertNotIn("gate.sh", text)
        self.assertIn("Use vitest", text)
        self.run_cli("act", "forget", str(b), "--cwd", cwd)
        self.run_cli("claude-md", "apply", "--cwd", cwd)
        self.assertEqual(md.read_text(encoding="utf-8"), "# Project\n\nExisting rules.\n")
        row = conn.execute("SELECT claude_md_applied, applied_file FROM learnings WHERE id=?", (a,)).fetchone()
        self.assertEqual((row[0], row[1]), (0, ""))

    def test_hand_edited_line_text_survives_and_other_content_untouched(self):
        a, _ = self.add("Run gate.sh before any commit.", claude_md=True)
        cwd = str(self.repo)
        self.run_cli("claude-md", "apply", "--cwd", cwd)
        md = self.repo / "CLAUDE.md"
        md.write_text(md.read_text(encoding="utf-8").replace("Run gate.sh before any commit.", "ALWAYS run gate.sh (edited)."),
                      encoding="utf-8")
        b, _ = self.add("Use vitest, not jest.", claude_md=True)
        self.run_cli("claude-md", "apply", "--cwd", cwd)
        text = md.read_text(encoding="utf-8")
        self.assertIn("ALWAYS run gate.sh (edited).", text)
        self.assertIn("Use vitest", text)
        self.assertEqual(text.count("learnings:start"), 1)

    def test_scope_move_relocates_line(self):
        a, conn = self.add("Prefer small commits always.", claude_md=True)
        cwd = str(self.repo)
        self.run_cli("claude-md", "apply", "--cwd", cwd)
        self.run_cli("act", "scope", str(a), "--to", "global", "--cwd", cwd)
        self.run_cli("claude-md", "apply", "--cwd", cwd)
        self.assertNotIn("small commits", (self.repo / "CLAUDE.md").read_text(encoding="utf-8") if (self.repo / "CLAUDE.md").exists() else "")
        self.assertIn("small commits", Path(os.environ["LEARN_GLOBAL_MD"]).read_text(encoding="utf-8"))

    def test_other_project_pending_adds_not_applied(self):
        self.add("Repo B only rule applies.", repo=self.repo_b, claude_md=True)
        _, out = self.run_cli("claude-md", "plan", "--cwd", str(self.repo))
        self.assertEqual(out.strip(), "NOTHING TO DO")

    def test_rewrite_block_unit(self):
        s = learn.rewrite_block("", [(1, "A rule."), (2, "B\nrule.")], set())
        self.assertIn("- B rule. <!-- L2 -->", s)
        self.assertEqual(learn.rewrite_block(s, [(1, "A rule.")], set()), s)
        self.assertEqual(learn.rewrite_block(s, [], {1, 2}), "")


class TestExportImport(Base):
    def seed(self):
        g, conn = self.add("Never run python - heredocs on Windows.", scope="global", kind="pitfall",
                           rationale="Hangs on stdin.", evidence="Command hangs: on stdin", claude_md=True)
        a, _ = self.add("Use jest in tests.", status="superseded")
        b, _ = self.add("Use vitest, not jest: it is faster.", kind="decision", source="question",
                        rationale="User choice.", evidence="vitest")
        pid = self.project_id(self.repo)[0]
        conn.execute("UPDATE learnings SET supersedes_id=? WHERE id=?", (a, b))
        conn.commit()
        c, _ = self.add("Rejected idea stays rejected.", status="rejected")
        d, _ = self.add("Pending idea waits for review.", status="pending", confidence="low")
        e, _ = self.add("Repo B convention applies here.", repo=self.repo_b, claude_md=True)
        conn.execute("UPDATE learnings SET claude_md_applied=1, applied_file='/x/CLAUDE.md' WHERE id=?", (e,))
        conn.commit()
        return conn

    def rows(self, conn):
        out = []
        for r in conn.execute("SELECT l.*, p.key AS pkey, p.name AS pname FROM learnings l "
                              "LEFT JOIN projects p ON p.id=l.project_id ORDER BY l.id"):
            out.append({k: r[k] for k in ("id", "scope", "pkey", "kind", "text", "rationale", "evidence", "source",
                                          "confidence", "status", "claude_md", "supersedes_id", "session_id")})
        return out

    def test_export_layout_and_content(self):
        self.seed()
        out = self.t / "exp"
        rc, msg = self.run_cli("export", "--out", str(out))
        self.assertEqual(rc, 0)
        self.assertTrue((out / "INDEX.md").exists())
        names = sorted(p.name for p in (out / "projects").glob("*.md"))
        self.assertEqual(len(names), 2)
        self.assertTrue(names[0].startswith("repo-a-") and names[1].startswith("repo-b-"))
        g = (out / "global.md").read_text(encoding="utf-8")
        self.assertIn("scope: global", g)
        self.assertIn("- text: Never run python - heredocs on Windows.", g)
        self.assertNotIn("project_key", g)
        a = next((out / "projects").glob("repo-a-*.md")).read_text(encoding="utf-8")
        self.assertIn("project_key: github.com/owner/repo-a", a)
        self.assertLess(a.index("## Approved"), a.index("## Pending"))
        self.assertLess(a.index("## Pending"), a.index("## Rejected"))
        self.assertIn("- evidence: Command hangs: on stdin", g)
        self.assertNotIn("repo-b", a)
        idx = (out / "INDEX.md").read_text(encoding="utf-8")
        self.assertIn("global.md", idx)
        self.assertIn("run.sh import", idx)

    def test_export_is_deterministic_and_cleans_stale_files(self):
        self.seed()
        out = self.t / "exp"
        self.run_cli("export", "--out", str(out))
        first = {p.name: p.read_bytes() for p in out.rglob("*.md") if p.name != "INDEX.md"}
        self.run_cli("export", "--out", str(out))
        self.assertEqual(first, {p.name: p.read_bytes() for p in out.rglob("*.md") if p.name != "INDEX.md"})
        stale = out / "projects" / "gone-abc123.md"
        stale.write_text("---\nlearnings_export: 1\nscope: project\n---\n", encoding="utf-8")
        foreign = out / "projects" / "notes.md"
        foreign.write_text("my own notes", encoding="utf-8")
        self.run_cli("export", "--out", str(out))
        self.assertFalse(stale.exists())
        self.assertTrue(foreign.exists())

    def test_round_trip_into_empty_database(self):
        conn = self.seed()
        before = self.rows(conn)
        out = self.t / "exp"
        self.run_cli("export", "--out", str(out))
        learn.close_all()
        os.environ["LEARN_HOME"] = str(self.t / "fresh")
        rc, msg = self.run_cli("import", str(out))
        self.assertEqual(rc, 0, msg)
        self.assertIn("6 added", msg)
        conn2 = learn.connect()
        self.assertEqual(self.rows(conn2), before)
        row = conn2.execute("SELECT claude_md_applied, applied_file FROM learnings WHERE claude_md=1 AND scope='project'").fetchone()
        self.assertEqual((row[0], row[1]), (0, ""))
        # restored database behaves: approved project learning loads, rejected one does not
        proj = conn2.execute("SELECT name, root FROM projects ORDER BY id").fetchall()
        self.assertEqual({r["name"] for r in proj}, {"repo-a", "repo-b"})
        rc, out2 = self.run_cli("load", "--event", "SessionStart", stdin=json.dumps({"cwd": str(self.repo)}))
        ctx = json.loads(out2)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Use vitest, not jest: it is faster.", ctx)
        self.assertNotIn("Rejected idea", ctx)
        self.assertIn("python - heredocs", ctx)

    def test_import_is_idempotent_and_remaps_ids_on_collision(self):
        conn = self.seed()
        out = self.t / "exp"
        self.run_cli("export", "--out", str(out))
        _, msg = self.run_cli("import", str(out))
        self.assertIn("0 added, 6 already present", msg)
        # target database already holds an unrelated learning with id 1: ids must be remapped, links preserved
        learn.close_all()
        os.environ["LEARN_HOME"] = str(self.t / "other")
        pid, c2 = self.project_id(self.repo_b)
        learn.add_learning(c2, scope="project", pid=pid, kind="rule", text="Unrelated learning in target DB.",
                           status="approved")
        rc, msg = self.run_cli("import", str(out))
        self.assertEqual(rc, 0, msg)
        self.assertIn("6 added", msg)
        rows = {r["text"]: r for r in c2.execute("SELECT * FROM learnings")}
        sup = rows["Use vitest, not jest: it is faster."]["supersedes_id"]
        self.assertEqual(c2.execute("SELECT text FROM learnings WHERE id=?", (sup,)).fetchone()[0], "Use jest in tests.")
        self.assertEqual(len(rows), 7)

    def test_dry_run_changes_nothing_and_bad_entries_are_reported(self):
        self.seed()
        out = self.t / "exp"
        self.run_cli("export", "--out", str(out))
        f = out / "global.md"
        f.write_text(f.read_text(encoding="utf-8").replace("- kind: pitfall", "- kind: nonsense"), encoding="utf-8")
        learn.close_all()
        os.environ["LEARN_HOME"] = str(self.t / "fresh2")
        rc, msg = self.run_cli("import", str(out), "--dry-run")
        self.assertIn("would import: 5 added", msg)
        self.assertIn("bad kind 'nonsense'", msg)
        self.assertEqual(rc, 1)
        self.assertEqual(learn.connect().execute("SELECT COUNT(*) FROM learnings").fetchone()[0], 0)

    def test_import_single_file_ignores_foreign_markdown_and_errors_when_empty(self):
        self.seed()
        out = self.t / "exp"
        self.run_cli("export", "--out", str(out))
        (out / "README-notes.md").write_text("# just notes\n", encoding="utf-8")
        learn.close_all()
        os.environ["LEARN_HOME"] = str(self.t / "fresh3")
        rc, msg = self.run_cli("import", str(out / "global.md"))
        self.assertIn("1 added", msg)
        rc, msg = self.run_cli("import", str(out / "README-notes.md"))
        self.assertEqual(rc, 2)
        rc, msg = self.run_cli("import", str(self.t / "missing"))
        self.assertEqual(rc, 2)

    def test_keep_applied_flag_and_hand_edit_of_status(self):
        self.seed()
        out = self.t / "exp"
        self.run_cli("export", "--out", str(out))
        b = next((out / "projects").glob("repo-b-*.md"))
        learn.close_all()
        os.environ["LEARN_HOME"] = str(self.t / "fresh4")
        self.run_cli("import", str(b), "--keep-applied")
        row = learn.connect().execute("SELECT claude_md_applied FROM learnings").fetchone()
        self.assertEqual(row[0], 1)
        # a human or AI may edit status in the markdown before importing
        a = next((out / "projects").glob("repo-a-*.md"))
        a.write_text(a.read_text(encoding="utf-8").replace("- status: pending", "- status: approved"), encoding="utf-8")
        self.run_cli("import", str(a))
        st = learn.connect().execute("SELECT status FROM learnings WHERE text='Pending idea waits for review.'").fetchone()[0]
        self.assertEqual(st, "approved")

    def test_export_without_database(self):
        rc, msg = self.run_cli("export", "--out", str(self.t / "e"))
        self.assertEqual(rc, 1)
        self.assertFalse((self.t / "e").exists())


class TestUi(Base):
    def test_collect_without_database(self):
        d = learn.collect_ui_data()
        self.assertTrue(d["db_missing"])
        self.assertEqual((d["learnings"], d["projects"]), ([], []))
        self.assertFalse(learn.db_path().exists(), "reading must not create the database")

    def test_collect_with_data_and_snapshot_escaping(self):
        evil = "</script><img src=x onerror=alert(1)> Run gate.sh first"
        a, conn = self.add(evil, claude_md=True)
        self.add("Global note stays global.", scope="global")
        conn.execute("INSERT INTO sessions(session_id,project_id,status,candidates,queued_at,updated_at) VALUES('s1',1,'failed',0,0,5)")
        conn.commit()
        d = learn.collect_ui_data()
        self.assertFalse(d["db_missing"])
        self.assertEqual(len(d["learnings"]), 2)
        row = next(r for r in d["learnings"] if r["id"] == a)
        self.assertEqual((row["project"], row["project_key"], row["claude_md"], row["applied"]),
                         ("repo-a", "github.com/owner/repo-a", True, False))
        self.assertEqual(d["sessions"]["counts"], {"failed": 1})
        out = self.t / "snap.html"
        rc, msg = self.run_cli("ui", "--out", str(out))
        self.assertEqual(rc, 0)
        html = out.read_text(encoding="utf-8")
        self.assertEqual(html.count("</script>"), 2, "learning text must not be able to close the script tag")
        self.assertIn('"mode": "static"', html)
        self.assertIn("Run gate.sh first", html)
        for banned in ("http://", "https://", "cdn."):
            self.assertNotIn(banned, html, "the page must work offline with no external resource")

    def test_server_is_local_read_only_and_serves_live_data(self):
        import threading
        import urllib.error
        import urllib.request
        self.add("Served learning text here.")
        srv = learn.make_ui_server(0)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            base = f"http://127.0.0.1:{port}"
            page = urllib.request.urlopen(base + "/").read().decode("utf-8")
            self.assertIn('"mode": "live"', page)
            data = json.loads(urllib.request.urlopen(base + "/api/data").read())
            self.assertEqual(data["learnings"][0]["text"], "Served learning text here.")
            for method in ("POST", "PUT", "DELETE"):
                with self.assertRaises(urllib.error.HTTPError) as cm:
                    urllib.request.urlopen(urllib.request.Request(base + "/api/data", data=b"x", method=method))
                self.assertEqual(cm.exception.code, 405)
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(base + "/nope")
            self.assertEqual(cm.exception.code, 404)
            with self.assertRaises(urllib.error.HTTPError) as cm:  # DNS-rebinding style Host header
                urllib.request.urlopen(urllib.request.Request(base + "/api/data", headers={"Host": "evil.example"}))
            self.assertEqual(cm.exception.code, 403)
            self.assertEqual(srv.server_address[0], "127.0.0.1")
        finally:
            srv.shutdown()
            srv.server_close()

    def test_host_only(self):
        self.assertEqual(learn.host_only("localhost:8765"), "localhost")
        self.assertEqual(learn.host_only("127.0.0.1"), "127.0.0.1")
        self.assertEqual(learn.host_only("[::1]:8765"), "[::1]")
        self.assertEqual(learn.host_only("evil.example:80"), "evil.example")
        self.assertEqual(learn.host_only(None), "")


class TestHooksRegistration(Base):
    def test_merge_is_idempotent_and_preserves_foreign_hooks(self):
        foreign = {"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "echo hi"}]}],
                             "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "node x.cjs"}]}]},
                   "permissions": {"allow": ["Bash(ls:*)"]}}
        sp = Path(os.environ["LEARN_SETTINGS"])
        sp.write_text(json.dumps(foreign), encoding="utf-8")
        self.run_cli("install-hooks")
        once = json.loads(sp.read_text(encoding="utf-8"))
        self.run_cli("install-hooks")
        twice = json.loads(sp.read_text(encoding="utf-8"))
        self.assertEqual(once, twice)
        self.assertEqual(once["permissions"], foreign["permissions"])
        self.assertEqual(once["hooks"]["PreToolUse"], foreign["hooks"]["PreToolUse"])
        ss = once["hooks"]["SessionStart"]
        self.assertEqual(len(ss), 2)
        self.assertEqual(ss[0]["hooks"][0]["command"], "echo hi")
        self.assertIn("run.sh", ss[1]["hooks"][0]["command"])
        for ev in ("SubagentStart", "SessionEnd"):
            self.assertEqual(len(once["hooks"][ev]), 1)
        self.assertTrue(list((Path(os.environ["LEARN_HOME"]) / "backups").glob("settings.json.*.bak")))
        self.run_cli("uninstall-hooks")
        gone = json.loads(sp.read_text(encoding="utf-8"))
        self.assertEqual(gone["hooks"]["SessionStart"], foreign["hooks"]["SessionStart"])
        self.assertNotIn("SessionEnd", gone["hooks"])
        self.assertNotIn("SubagentStart", gone["hooks"])

    def test_fresh_settings_and_dry_run_and_invalid_json(self):
        sp = Path(os.environ["LEARN_SETTINGS"])
        _, out = self.run_cli("install-hooks", "--dry-run")
        self.assertIn("SessionEnd", out)
        self.assertFalse(sp.exists())
        self.run_cli("install-hooks")
        self.assertTrue(sp.exists())
        sp.write_text("{broken", encoding="utf-8")
        rc, out = self.run_cli("install-hooks")
        self.assertEqual(rc, 1)
        self.assertEqual(sp.read_text(encoding="utf-8"), "{broken")


class TestCaptureHook(Base):
    def test_capture_queues_and_requeues_resumed(self):
        payload = {"session_id": "abc", "cwd": str(self.repo), "transcript_path": "/x/abc.jsonl", "reason": "other"}
        rc, out = self.run_cli("capture", stdin=json.dumps(payload))
        self.assertEqual((rc, out), (0, ""))
        conn = learn.connect()
        r = conn.execute("SELECT * FROM sessions").fetchone()
        self.assertEqual((r["session_id"], r["status"]), ("abc", "queued"))
        conn.execute("UPDATE sessions SET status='done' WHERE session_id='abc'")
        conn.commit()
        self.run_cli("capture", stdin=json.dumps(payload))
        self.assertEqual(conn.execute("SELECT status FROM sessions").fetchone()[0], "queued")

    def test_capture_garbage_stdin_never_fails(self):
        rc, out = self.run_cli("capture", stdin="not json")
        self.assertEqual(rc, 0)
        rc, out = self.run_cli("load", "--event", "SessionStart", stdin="not json")
        self.assertEqual(rc, 0)


@unittest.skipUnless(POSIX, "run.sh needs bash")
class TestRunSh(Base):
    def test_run_sh_status(self):
        r = subprocess.run(["bash", str(HERE / "run.sh"), "status"], capture_output=True, text=True,
                           env=dict(os.environ))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("database:", r.stdout)

    def test_run_sh_hook_exits_zero_without_python(self):
        env = dict(os.environ, PATH="/nonexistent", LEARN_PYTHON="")
        r = subprocess.run(["/bin/bash", str(HERE / "run.sh"), "load"], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0)
        r = subprocess.run(["/bin/bash", str(HERE / "run.sh"), "report"], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
