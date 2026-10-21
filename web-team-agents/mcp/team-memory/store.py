"""team-memory store — SQLite-backed shared memory, task board and file locks for a team of agents.

Pure standard library (no MCP dependency) so it can be unit-tested and reused. Every operation opens its
own short-lived connection (WAL + busy_timeout), so many processes — one MCP server per agent session,
parallel worktrees, scripts — can share one database file safely. Multi-step changes run inside
BEGIN IMMEDIATE transactions, which is what makes task claims and locks race-free.
"""
from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

KINDS = ("note", "decision", "convention", "gotcha", "contract", "review-pattern", "handoff", "fact", "rule")
TASK_FINAL = ("done", "failed")
MAX_CONTENT = 8000
SNIPPET = 2000          # get_memory / default row snippet
RECALL_SNIPPET = 600    # recall default: entries are ~400-700 chars; the head carries the point
RECALL_LIMIT = 6        # recall default: bm25-ranked, so the top few are what matters
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:#-]{0,95}$")
_TOPIC = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories(
  id INTEGER PRIMARY KEY,
  ts REAL NOT NULL,
  agent TEXT NOT NULL,
  story TEXT NOT NULL DEFAULT '',
  kind TEXT NOT NULL,
  key TEXT NOT NULL DEFAULT '',
  content TEXT NOT NULL,
  tags TEXT NOT NULL DEFAULT '',
  superseded_by INTEGER
);
CREATE INDEX IF NOT EXISTS memories_lookup ON memories(kind, story, superseded_by);
CREATE INDEX IF NOT EXISTS memories_key ON memories(kind, key, story);
CREATE TABLE IF NOT EXISTS tasks(
  id INTEGER PRIMARY KEY,
  ts REAL NOT NULL,
  updated REAL NOT NULL,
  story TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  role TEXT NOT NULL DEFAULT '',
  priority INTEGER NOT NULL DEFAULT 0,
  depends_on TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','claimed','done','failed')),
  claimed_by TEXT,
  lease_until REAL,
  result TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS tasks_pick ON tasks(status, story, priority);
CREATE TABLE IF NOT EXISTS locks(
  resource TEXT PRIMARY KEY,
  holder TEXT NOT NULL,
  story TEXT NOT NULL DEFAULT '',
  ts REAL NOT NULL,
  expires REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS flaky(
  test TEXT PRIMARY KEY,
  n INTEGER NOT NULL DEFAULT 1,
  first_ts REAL NOT NULL,
  last_ts REAL NOT NULL,
  last_story TEXT NOT NULL DEFAULT '',
  last_agent TEXT NOT NULL DEFAULT '',
  cause TEXT NOT NULL DEFAULT '',
  retired INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS usage(
  id INTEGER PRIMARY KEY,
  ts REAL NOT NULL,
  agent TEXT NOT NULL DEFAULT '',
  tool TEXT NOT NULL,
  story TEXT NOT NULL DEFAULT '',
  chars INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS usage_tool ON usage(tool, agent);
CREATE TABLE IF NOT EXISTS hits(
  memory_id INTEGER PRIMARY KEY,
  n INTEGER NOT NULL DEFAULT 0,
  last_ts REAL NOT NULL
);
"""

FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(key, content, tags, content='memories', content_rowid='id');
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
  INSERT INTO memories_fts(rowid, key, content, tags) VALUES (new.id, new.key, new.content, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
  INSERT INTO memories_fts(memories_fts, rowid, key, content, tags) VALUES ('delete', old.id, old.key, old.content, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE OF key, content, tags ON memories BEGIN
  INSERT INTO memories_fts(memories_fts, rowid, key, content, tags) VALUES ('delete', old.id, old.key, old.content, old.tags);
  INSERT INTO memories_fts(rowid, key, content, tags) VALUES (new.id, new.key, new.content, new.tags);
END;
"""


# ----------------------------------------------------------------------------- validation helpers
def _name(value: str, label: str, optional: bool = False) -> str:
    value = (value or "").strip()
    if not value:
        if optional:
            return ""
        raise ValueError(f"{label} is required")
    if not _NAME.match(value):
        raise ValueError(f"{label} must match [A-Za-z0-9][A-Za-z0-9_.:#-]* and be at most 96 chars (got {value[:40]!r})")
    return value


def _text(value: str, label: str, limit: int, required: bool = False) -> str:
    value = (value or "").replace("\x00", "").strip()
    if required and not value:
        raise ValueError(f"{label} is required")
    if len(value) > limit:
        raise ValueError(f"{label} is too long ({len(value)} > {limit} chars); summarize it or store a file path instead")
    return value


def _resource(value: str) -> str:
    value = _text(value, "resource", 300, required=True).replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    return value


def _iso(ts: float | None) -> str | None:
    return None if ts is None else datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _snip(text: str, limit: int = SNIPPET) -> str:
    return text if len(text) <= limit else text[:limit] + f"…[truncated {len(text) - limit} chars; use get_memory(id)]"


def _cut(text: str, limit: int) -> str:
    """Hard cut with an ellipsis (no get_memory hint) — for compact briefings."""
    text = (text or "").strip()
    return text if len(text) <= limit else text[:max(0, limit - 1)].rstrip() + "…"


def _field(content: str, name: str) -> str:
    """Value of a 'Name: value' line in a structured memory body (log_decision format)."""
    m = re.search(rf"^{re.escape(name)}:\s*(.*)$", content or "", re.MULTILINE)
    return m.group(1).strip() if m else ""


def _fts_query(query: str) -> str:
    tokens = re.findall(r"\w+", query or "", re.UNICODE)[:8]
    return " OR ".join(f'"{t}"*' for t in tokens)


# ----------------------------------------------------------------------------- store
def default_db_path() -> Path:
    """$TEAM_MEMORY_DB, else <workspace>/.pipeline/team-memory.db.
    Inside a git worktree, <workspace> is the MAIN worktree, so parallel worktree sessions share one database."""
    env = os.environ.get("TEAM_MEMORY_DB")
    if env:
        return Path(env)
    root = Path.cwd()
    try:
        r = subprocess.run(["git", "rev-parse", "--git-common-dir"], capture_output=True, text=True, timeout=5, cwd=root)
        if r.returncode == 0 and r.stdout.strip():
            common = Path(r.stdout.strip())
            common = (root / common).resolve() if not common.is_absolute() else common
            if common.name == ".git":
                root = common.parent
    except (OSError, subprocess.SubprocessError):
        pass
    return root / ".pipeline" / "team-memory.db"


class Store:
    def __init__(self, path: str | os.PathLike | None = None, root: str | os.PathLike | None = None) -> None:
        self.path = Path(path) if path else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if root:
            self.root = Path(root)
        elif self.path.parent.name == ".pipeline":
            self.root = self.path.parent.parent      # the workspace the database belongs to
        else:
            self.root = Path.cwd()
        self._contract_cache: dict = {}
        self.fts = True
        with self._tx() as c:
            for stmt in _split(SCHEMA):
                c.execute(stmt)
        try:
            with self._tx() as c:
                for stmt in _split(FTS_SCHEMA):
                    c.execute(stmt)
        except sqlite3.OperationalError:
            self.fts = False  # SQLite built without FTS5: recall falls back to LIKE

    # -- connections -------------------------------------------------------------------------
    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        c = sqlite3.connect(str(self.path), timeout=15, isolation_level=None)
        c.row_factory = sqlite3.Row
        try:
            c.execute("PRAGMA busy_timeout=15000")
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=NORMAL")
            yield c
        finally:
            c.close()

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        with self._connect() as c:
            c.execute("BEGIN IMMEDIATE")
            try:
                yield c
            except BaseException:
                try:
                    c.execute("ROLLBACK")
                except sqlite3.Error:
                    pass
                raise
            else:
                c.execute("COMMIT")

    # -- memories ----------------------------------------------------------------------------
    def remember(self, agent: str, kind: str, content: str, story: str = "", key: str = "", tags: str = "") -> dict:
        agent = _name(agent, "agent")
        story = _name(story, "story", optional=True)
        if kind not in KINDS:
            raise ValueError(f"kind must be one of {', '.join(KINDS)}")
        content = _text(content, "content", MAX_CONTENT, required=True)
        key = _text(key, "key", 120)
        tags = _text(tags, "tags", 200)
        with self._tx() as c:
            new_id = c.execute(
                "INSERT INTO memories(ts, agent, story, kind, key, content, tags) VALUES (?,?,?,?,?,?,?)",
                (time.time(), agent, story, kind, key, content, tags),
            ).lastrowid
            replaced: list[int] = []
            if key:  # same (kind, key, story) = a correction: keep history, hide the old one
                replaced = [r["id"] for r in c.execute(
                    "SELECT id FROM memories WHERE kind=? AND key=? AND story=? AND superseded_by IS NULL AND id<>?",
                    (kind, key, story, new_id))]
                if replaced:
                    c.execute(f"UPDATE memories SET superseded_by=? WHERE id IN ({','.join('?' * len(replaced))})",
                              (new_id, *replaced))
        return {"id": new_id, "replaced": replaced}

    def _row(self, r: sqlite3.Row, full: bool = False, snippet: int = SNIPPET) -> dict:
        d = {"id": r["id"], "ts": _iso(r["ts"]), "agent": r["agent"], "story": r["story"], "kind": r["kind"],
             "key": r["key"], "tags": r["tags"], "content": r["content"] if full else _snip(r["content"], snippet)}
        if r["superseded_by"] is not None:
            d["superseded_by"] = r["superseded_by"]
        return d

    def recall(self, query: str = "", story: str = "", kind: str = "", limit: int = RECALL_LIMIT,
               include_retired: bool = False, agent: str = "", snippet: int = RECALL_SNIPPET) -> list[dict]:
        story = _name(story, "story", optional=True)
        if kind and kind not in KINDS:
            raise ValueError(f"kind must be one of {', '.join(KINDS)}")
        limit = max(1, min(int(limit), 50))
        snippet = max(100, min(int(snippet), 8000))
        where, params = [], []
        if not include_retired:
            where.append("m.superseded_by IS NULL")
        if story:  # this story's memories plus global ones (story = '')
            where.append("(m.story=? OR m.story='')")
            params.append(story)
        if kind:
            where.append("m.kind=?")
            params.append(kind)
        with self._connect() as c:
            match = _fts_query(query) if query else ""
            if match and self.fts:
                sql = ("SELECT m.* FROM memories_fts JOIN memories m ON m.id = memories_fts.rowid "
                       "WHERE memories_fts MATCH ? " + "".join(f"AND {w} " for w in where) +
                       "ORDER BY bm25(memories_fts), m.id DESC LIMIT ?")
                rows = c.execute(sql, (match, *params, limit)).fetchall()
            elif query:
                toks = re.findall(r"\w+", query, re.UNICODE)[:8] or [query]
                like = " OR ".join("(m.content LIKE ? OR m.key LIKE ? OR m.tags LIKE ?)" for _ in toks)
                lp = [f"%{t}%" for t in toks for _ in range(3)]
                sql = f"SELECT m.* FROM memories m WHERE ({like}) " + "".join(f"AND {w} " for w in where) + "ORDER BY m.id DESC LIMIT ?"
                rows = c.execute(sql, (*lp, *params, limit)).fetchall()
            else:
                sql = "SELECT m.* FROM memories m " + ("WHERE " + " AND ".join(where) + " " if where else "") + "ORDER BY m.id DESC LIMIT ?"
                rows = c.execute(sql, (*params, limit)).fetchall()
        out = [self._row(r, snippet=snippet) for r in rows]
        return self._track("recall", out, agent, story, [d["id"] for d in out])

    def get_memory(self, memory_id: int) -> dict:
        with self._connect() as c:
            r = c.execute("SELECT * FROM memories WHERE id=?", (int(memory_id),)).fetchone()
        if not r:
            raise ValueError(f"no memory with id {memory_id}")
        return self._row(r, full=True)

    def retire_memory(self, memory_id: int, agent: str) -> dict:
        _name(agent, "agent")
        with self._tx() as c:
            n = c.execute("UPDATE memories SET superseded_by=0 WHERE id=? AND superseded_by IS NULL", (int(memory_id),)).rowcount
        return {"retired": bool(n)}

    # -- decisions ---------------------------------------------------------------------------
    def log_decision(self, agent: str, story: str, topic: str, ref: str, problem: str, choice: str, decision: str) -> dict:
        if not _TOPIC.match(topic or ""):
            raise ValueError("topic must be a short kebab-case slug, e.g. 'error-copy' or 'i18n-keys' (max 40 chars)")
        body = "\n".join([
            f"Ref: {_text(ref, 'ref', 500, True)}",
            f"Problem: {_text(problem, 'problem', 1000, True)}",
            f"Choice: {_text(choice, 'choice', 1000, True)}",
            f"Decision: {_text(decision, 'decision', 1000, True)}",
        ])
        res = self.remember(agent, "decision", body, story=story, tags=topic)
        try:  # a topic that now recurs across stories becomes a standing rule (best effort, never fails the log)
            promoted = self.promote_rules()["promoted"]
            if promoted:
                res["rule_promoted"] = promoted
        except Exception:
            pass
        return res

    def export_decisions_markdown(self, story: str = "", agent: str = "") -> dict:
        """Render logged decisions back into the same Agent/Story/Ref/Problem/Choice/Decision markdown
        format as the .decisions/*.decisions.md files, so a human-readable file can be regenerated from
        the database. story/agent filter when given ('' = no filter); results are chronological."""
        entries = [entry for _, entry in self._decision_entries(story, agent)]
        return {"markdown": "\n\n".join(entries), "count": len(entries)}

    def export_decisions_files(self, story: str, root: str | Path) -> dict:
        """Append one story's logged decisions to <root>/.decisions/<agent>.decisions.md, one file per agent.
        Entries already in a file are skipped, so calling it again for the same story writes nothing new and
        entries agents wrote to the files themselves (memory off or failing) are kept."""
        story = _name(story, "story")
        folder = Path(root) / ".decisions"
        written: dict[str, int] = {}
        for agent, entry in self._decision_entries(story, ""):
            path = folder / f"{agent}.decisions.md"
            existing = path.read_text(encoding="utf-8") if path.exists() else ""
            if entry in existing:
                continue
            folder.mkdir(parents=True, exist_ok=True)
            separator = "" if not existing.strip() else "\n" if existing.endswith("\n") else "\n\n"
            with path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(f"{separator}{entry}\n")
            written[agent] = written.get(agent, 0) + 1
        return {"story": story, "written": written, "files": sorted(f".decisions/{a}.decisions.md" for a in written)}

    def _decision_entries(self, story: str, agent: str) -> list[tuple[str, str]]:
        story = _name(story, "story", optional=True)
        agent = _name(agent, "agent", optional=True)
        where, params = ["kind='decision'", "superseded_by IS NULL"], []
        if story:
            where.append("story=?")
            params.append(story)
        if agent:
            where.append("agent=?")
            params.append(agent)
        with self._connect() as c:
            rows = c.execute(
                f"SELECT agent, story, content, ts FROM memories WHERE {' AND '.join(where)} ORDER BY ts",
                params).fetchall()
        return [(r["agent"], f"Agent: {r['agent']}\nStory: {r['story'] or '(project-wide)'}\n{r['content']}") for r in rows]

    def decisions_digest(self, min_count: int = 2) -> dict:
        min_count = max(1, int(min_count))
        with self._connect() as c:
            total = c.execute("SELECT COUNT(*) n FROM memories WHERE kind='decision' AND superseded_by IS NULL").fetchone()["n"]
            groups = c.execute(
                "SELECT tags topic, COUNT(*) n, COUNT(DISTINCT story) stories, COUNT(DISTINCT agent) agents, MAX(id) last_id "
                "FROM memories WHERE kind='decision' AND superseded_by IS NULL GROUP BY tags HAVING n>=? ORDER BY n DESC, last_id DESC",
                (min_count,)).fetchall()
            out = []
            for g in groups:
                last = c.execute("SELECT content FROM memories WHERE id=?", (g["last_id"],)).fetchone()["content"]
                out.append({"topic": g["topic"] or "(untagged)", "count": g["n"], "stories": g["stories"],
                            "agents": g["agents"], "latest": _snip(last, 500)})
        return {"total_decisions": total, "recurring": out}

    # -- tasks -------------------------------------------------------------------------------
    def task_post(self, title: str, story: str = "", detail: str = "", role: str = "", priority: int = 0,
                  depends_on: list[int] | None = None) -> dict:
        title = _text(title, "title", 200, True)
        story = _name(story, "story", optional=True)
        role = _name(role, "role", optional=True)
        detail = _text(detail, "detail", MAX_CONTENT)
        deps = sorted({int(d) for d in (depends_on or [])})
        now = time.time()
        with self._tx() as c:
            if deps:
                found = {r["id"] for r in c.execute(f"SELECT id FROM tasks WHERE id IN ({','.join('?' * len(deps))})", deps)}
                if found != set(deps):
                    raise ValueError(f"unknown dependency task ids: {sorted(set(deps) - found)}")
            tid = c.execute(
                "INSERT INTO tasks(ts, updated, story, title, detail, role, priority, depends_on) VALUES (?,?,?,?,?,?,?,?)",
                (now, now, story, title, detail, role, int(priority), json.dumps(deps))).lastrowid
        return {"id": tid}

    def task_checkpoint(self, story: str, role: str, status: str, title: str = "", detail: str = "", result: str = "") -> dict:
        """Single-call, idempotent status write for a story's own pipeline-step mirror: no claim/ownership
        dance, because there is exactly one writer (e.g. product-manager reporting its own progress on its
        own story). Upserts by (story, role): updates the existing row for that pair if one exists, else
        inserts a new one already in the given status. For a real pool of workers pulling from a shared
        queue (e.g. dev -> unit-tester obsolete-test handoff), use task_post/task_claim/task_finish instead."""
        story = _name(story, "story")
        role = _name(role, "role")
        if status not in ("open", "claimed", "done", "failed"):
            raise ValueError("status must be open, claimed, done or failed")
        title = _text(title, "title", 200) or role
        detail = _text(detail, "detail", MAX_CONTENT)
        result = _text(result, "result", 2000)
        now = time.time()
        with self._tx() as c:
            row = c.execute("SELECT id FROM tasks WHERE story=? AND role=? ORDER BY id DESC LIMIT 1", (story, role)).fetchone()
            if row:
                tid = row["id"]
                c.execute("UPDATE tasks SET status=?, result=?, claimed_by=?, lease_until=NULL, updated=? WHERE id=?",
                          (status, result, role, now, tid))
            else:
                tid = c.execute(
                    "INSERT INTO tasks(ts, updated, story, title, detail, role, priority, depends_on, status, claimed_by, result) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (now, now, story, title, detail, role, 0, "[]", status, role, result)).lastrowid
        return {"id": tid, "story": story, "role": role, "status": status}

    def _task(self, r: sqlite3.Row, blocked_by: list[int] | None = None) -> dict:
        d = {"id": r["id"], "story": r["story"], "title": r["title"], "detail": r["detail"], "role": r["role"],
             "priority": r["priority"], "status": r["status"], "claimed_by": r["claimed_by"],
             "depends_on": json.loads(r["depends_on"] or "[]"), "result": r["result"]}
        if r["lease_until"] is not None and r["status"] == "claimed":
            d["lease_expires_in"] = max(0, int(r["lease_until"] - time.time()))
        if blocked_by:
            d["blocked_by"] = blocked_by
        return d

    def task_claim(self, agent: str, story: str = "", role: str = "", lease_seconds: int = 900) -> dict | None:
        agent = _name(agent, "agent")
        story = _name(story, "story", optional=True)
        role = _name(role, "role", optional=True)
        lease = max(30, min(int(lease_seconds), 6 * 3600))
        now = time.time()
        with self._tx() as c:
            c.execute("UPDATE tasks SET status='open', claimed_by=NULL, lease_until=NULL, updated=? "
                      "WHERE status='claimed' AND lease_until < ?", (now, now))  # crashed agents release automatically
            where, params = ["status='open'"], []
            if story:
                where.append("story=?"); params.append(story)
            if role:
                where.append("(role=? OR role='')"); params.append(role)
            for r in c.execute(f"SELECT * FROM tasks WHERE {' AND '.join(where)} ORDER BY priority DESC, id ASC", params).fetchall():
                deps = json.loads(r["depends_on"] or "[]")
                if deps:
                    done = c.execute(f"SELECT COUNT(*) n FROM tasks WHERE status='done' AND id IN ({','.join('?' * len(deps))})", deps).fetchone()["n"]
                    if done != len(deps):
                        continue
                c.execute("UPDATE tasks SET status='claimed', claimed_by=?, lease_until=?, updated=? WHERE id=?",
                          (agent, now + lease, now, r["id"]))
                return self._task(c.execute("SELECT * FROM tasks WHERE id=?", (r["id"],)).fetchone())
        return None

    def _owned(self, c: sqlite3.Connection, task_id: int, agent: str) -> sqlite3.Row:
        r = c.execute("SELECT * FROM tasks WHERE id=?", (int(task_id),)).fetchone()
        if not r:
            raise ValueError(f"no task with id {task_id}")
        if r["status"] != "claimed" or r["claimed_by"] != agent:
            raise ValueError(f"task {task_id} is {r['status']}" + (f" and claimed by {r['claimed_by']}" if r["claimed_by"] else "") + f", not claimed by {agent}")
        return r

    def task_heartbeat(self, task_id: int, agent: str, lease_seconds: int = 900) -> dict:
        agent = _name(agent, "agent")
        lease = max(30, min(int(lease_seconds), 6 * 3600))
        with self._tx() as c:
            self._owned(c, task_id, agent)
            c.execute("UPDATE tasks SET lease_until=?, updated=? WHERE id=?", (time.time() + lease, time.time(), int(task_id)))
        return {"id": int(task_id), "lease_expires_in": lease}

    def task_release(self, task_id: int, agent: str) -> dict:
        agent = _name(agent, "agent")
        with self._tx() as c:
            self._owned(c, task_id, agent)
            c.execute("UPDATE tasks SET status='open', claimed_by=NULL, lease_until=NULL, updated=? WHERE id=?", (time.time(), int(task_id)))
        return {"id": int(task_id), "status": "open"}

    def task_finish(self, task_id: int, agent: str, status: str = "done", result: str = "") -> dict:
        agent = _name(agent, "agent")
        if status not in TASK_FINAL:
            raise ValueError("status must be 'done' or 'failed'")
        result = _text(result, "result", 2000)
        with self._tx() as c:
            self._owned(c, task_id, agent)
            c.execute("UPDATE tasks SET status=?, result=?, lease_until=NULL, updated=? WHERE id=?",
                      (status, result, time.time(), int(task_id)))
        return {"id": int(task_id), "status": status}

    def task_list(self, story: str = "", status: str = "", limit: int = 50) -> list[dict]:
        story = _name(story, "story", optional=True)
        limit = max(1, min(int(limit), 200))
        where, params = [], []
        if story:
            where.append("story=?"); params.append(story)
        if status:
            if status not in ("open", "claimed", "done", "failed"):
                raise ValueError("status must be open, claimed, done or failed")
            where.append("status=?"); params.append(status)
        with self._connect() as c:
            rows = c.execute("SELECT * FROM tasks " + ("WHERE " + " AND ".join(where) + " " if where else "") +
                             "ORDER BY id ASC LIMIT ?", (*params, limit)).fetchall()
            status_by_id = {r["id"]: r["status"] for r in c.execute("SELECT id, status FROM tasks")}
        out = []
        for r in rows:
            deps = json.loads(r["depends_on"] or "[]")
            pending = [d for d in deps if status_by_id.get(d) != "done"] if r["status"] == "open" else []
            out.append(self._task(r, pending))
        return out

    # -- locks -------------------------------------------------------------------------------
    def lock_acquire(self, resource: str, agent: str, story: str = "", ttl_seconds: int = 600) -> dict:
        resource = _resource(resource)
        agent = _name(agent, "agent")
        story = _name(story, "story", optional=True)
        ttl = max(30, min(int(ttl_seconds), 6 * 3600))
        now = time.time()
        with self._tx() as c:
            c.execute("DELETE FROM locks WHERE expires < ?", (now,))
            r = c.execute("SELECT * FROM locks WHERE resource=?", (resource,)).fetchone()
            if r and r["holder"] != agent:
                return {"acquired": False, "resource": resource, "holder": r["holder"], "expires_in": max(0, int(r["expires"] - now))}
            c.execute("INSERT INTO locks(resource, holder, story, ts, expires) VALUES (?,?,?,?,?) "
                      "ON CONFLICT(resource) DO UPDATE SET expires=excluded.expires, story=excluded.story",
                      (resource, agent, story, now, now + ttl))
        return {"acquired": True, "resource": resource, "holder": agent, "expires_in": ttl}

    def lock_release(self, resource: str, agent: str, force: bool = False) -> dict:
        resource = _resource(resource)
        agent = _name(agent, "agent")
        with self._tx() as c:
            if force:
                n = c.execute("DELETE FROM locks WHERE resource=?", (resource,)).rowcount
            else:
                n = c.execute("DELETE FROM locks WHERE resource=? AND holder=?", (resource, agent)).rowcount
        return {"released": bool(n)}

    def lock_list(self) -> list[dict]:
        now = time.time()
        with self._connect() as c:
            rows = c.execute("SELECT * FROM locks WHERE expires >= ? ORDER BY resource", (now,)).fetchall()
        return [{"resource": r["resource"], "holder": r["holder"], "story": r["story"], "expires_in": int(r["expires"] - now)} for r in rows]

    # -- token savers: telemetry ---------------------------------------------------------------
    def _track(self, tool: str, result: Any, agent: str = "", story: str = "", ids: Any = ()) -> Any:
        """Record how much a read tool returned (usage telemetry) and which memories it surfaced (recall hits).
        Best effort: telemetry must never break a read."""
        try:
            chars = len(json.dumps(result, ensure_ascii=False, default=str))
            agent = agent if _NAME.match(agent or "") else ""
            story = story if _NAME.match(story or "") else ""
            now = time.time()
            with self._tx() as c:
                c.execute("INSERT INTO usage(ts, agent, tool, story, chars) VALUES (?,?,?,?,?)", (now, agent, tool, story, chars))
                for mid in {int(x) for x in (ids or ())}:
                    c.execute("INSERT INTO hits(memory_id, n, last_ts) VALUES (?,1,?) "
                              "ON CONFLICT(memory_id) DO UPDATE SET n=n+1, last_ts=excluded.last_ts", (mid, now))
        except Exception:
            pass
        return result

    def usage_report(self, days: int = 0, limit: int = 8, stale_days: int = 14) -> dict:
        """What the memory tools cost in returned text (chars / ~4 = tokens), per tool and per agent, the heaviest
        single calls, and active memories nobody has ever recalled (prune candidates for retire_memory)."""
        days, limit, stale_days = max(0, int(days)), max(1, min(int(limit), 30)), max(1, int(stale_days))
        now = time.time()
        since = now - days * 86400 if days else 0.0
        with self._connect() as c:
            tot = c.execute("SELECT COUNT(*) n, COALESCE(SUM(chars),0) s FROM usage WHERE ts>=?", (since,)).fetchone()

            def agg(col: str) -> list[dict]:
                rows = c.execute(f"SELECT {col} k, COUNT(*) n, SUM(chars) s, AVG(chars) a, MAX(chars) m FROM usage "
                                 f"WHERE ts>=? GROUP BY {col} ORDER BY s DESC LIMIT ?", (since, limit)).fetchall()
                return [{col: r["k"] or "(unknown)", "calls": r["n"], "chars": r["s"], "est_tokens": r["s"] // 4,
                         "avg_chars": int(r["a"]), "max_chars": r["m"]} for r in rows]

            by_tool, by_agent = agg("tool"), agg("agent")
            heavy = [{"when": _iso(r["ts"]), "agent": r["agent"] or "(unknown)", "tool": r["tool"], "story": r["story"],
                      "chars": r["chars"]} for r in c.execute(
                "SELECT ts, agent, tool, story, chars FROM usage WHERE ts>=? ORDER BY chars DESC LIMIT ?", (since, limit))]
            first = c.execute("SELECT MIN(ts) t FROM usage").fetchone()["t"]
            stale: list[dict] = []
            note = ""
            if first is None or now - first < stale_days * 86400:
                note = f"recall tracking has run for less than {stale_days} days; stale list withheld (entries recalled before tracking started would look unused)"
            else:
                stale = [{"id": r["id"], "kind": r["kind"], "key": r["key"], "agent": r["agent"], "story": r["story"], "chars": r["chars"]}
                         for r in c.execute(
                    "SELECT m.id, m.kind, m.key, m.agent, m.story, length(m.content) chars FROM memories m "
                    "LEFT JOIN hits h ON h.memory_id=m.id WHERE m.superseded_by IS NULL AND h.memory_id IS NULL AND m.ts<? "
                    "AND m.kind NOT IN ('handoff','rule') ORDER BY chars DESC LIMIT ?", (now - stale_days * 86400, limit))]
        return {"tracking_since": _iso(first), "calls": tot["n"], "chars_returned": tot["s"], "est_tokens_returned": tot["s"] // 4,
                "by_tool": by_tool, "by_agent": by_agent, "heaviest_calls": heavy,
                "never_recalled": stale, "note": note}

    # -- token savers: standing rules ----------------------------------------------------------
    def _rules(self, limit: int = 15, snip: int = 400) -> list[dict]:
        with self._connect() as c:
            rows = c.execute("SELECT id, key, tags, content FROM memories WHERE kind='rule' AND superseded_by IS NULL "
                             "ORDER BY id DESC LIMIT ?", (max(1, min(int(limit), 50)),)).fetchall()
        return [{"id": r["id"], "key": r["key"], "topic": r["tags"], "content": _cut(r["content"], snip)} for r in rows]

    def rules_briefing(self, limit: int = 15, agent: str = "") -> dict:
        """Standing rules (kind='rule'): decisions that recurred and must not be re-decided. story_context includes them too."""
        rules = self._rules(limit, 400)
        return self._track("rules_briefing", {"count": len(rules), "rules": rules}, agent, "", [r["id"] for r in rules])

    def promote_rules(self, min_stories: int = 2) -> dict:
        """Promote decision topics that recur across >= min_stories distinct stories into a standing `rule`
        (key 'topic:<slug>', project-wide). Idempotent; a rule that was retired stays retired, and a curated
        rule saved with remember(kind='rule', key='topic:<slug>') replaces the auto-generated text."""
        min_stories = max(2, int(min_stories))
        promoted: list[str] = []
        with self._tx() as c:
            groups = c.execute(
                "SELECT tags topic, COUNT(*) n, COUNT(DISTINCT story) stories, MAX(id) last_id FROM memories "
                "WHERE kind='decision' AND superseded_by IS NULL AND tags<>'' GROUP BY tags "
                "HAVING COUNT(DISTINCT story)>=?", (min_stories,)).fetchall()
            now = time.time()
            for g in groups:
                key = f"topic:{g['topic']}"
                if c.execute("SELECT 1 FROM memories WHERE kind='rule' AND key=? AND story='' "
                             "AND (superseded_by IS NULL OR superseded_by=0)", (key,)).fetchone():
                    continue  # already a rule, or deliberately retired
                last = c.execute("SELECT story, content FROM memories WHERE id=?", (g["last_id"],)).fetchone()
                decision = _field(last["content"], "Decision") or last["content"]
                content = (f"[auto-promoted: {g['n']} decisions across {g['stories']} stories, latest "
                           f"{last['story'] or 'project-wide'}] {_cut(decision, 600)} - apply without re-deciding unless the "
                           f"story contradicts it; curate with remember(kind='rule', key='{key}').")
                c.execute("INSERT INTO memories(ts, agent, story, kind, key, content, tags) VALUES (?,?,?,?,?,?,?)",
                          (now, "team-memory", "", "rule", key, content, g["topic"]))
                promoted.append(g["topic"])
        return {"promoted": promoted}

    # -- token savers: workspace files ---------------------------------------------------------
    def _workspace_file(self, rel: str, candidates: tuple[str, ...], suffixes: tuple[str, ...]) -> tuple[Path, str] | None:
        for r in ([rel] if rel else list(candidates)):
            r = r.replace("\\", "/").strip()
            if not r or r.startswith("/") or re.match(r"^[A-Za-z]:", r) or ".." in Path(r).parts:
                raise ValueError("file must be a relative path inside the workspace")
            if Path(r).suffix.lower() not in suffixes:
                raise ValueError(f"file must end with one of: {', '.join(suffixes)}")
            for base in (Path.cwd(), self.root):
                p = base / r
                try:
                    if p.is_file() and p.resolve().is_relative_to(base.resolve()):
                        return p, r
                except OSError:
                    continue
        return None

    def _workspace_dir(self, rel: str) -> Path | None:
        for base in (Path.cwd(), self.root):
            p = base / rel
            if p.is_dir():
                return p
        return None

    def contract_lookup(self, query: str = "", file: str = "", max_chars: int = 14000, agent: str = "", story: str = "",
                        include_common: bool = False) -> dict:
        """Return only the part of the OpenAPI file you need instead of reading all of it. query: '' = compact outline
        of every operation + component names; an operationId; 'METHOD /path'; '/path' (all its methods); a component
        name ('Meal' or 'schemas/Meal'); or free words. Operations come with the components they reference (schemas
        first), within max_chars. Boilerplate that most operations share (error envelope, 401/429/500 responses) is only
        listed by name, in common_components_omitted - look one up by name, or pass include_common=True."""
        max_chars = max(2000, min(int(max_chars), 60000))
        found = self._workspace_file(file, _CONTRACT_CANDIDATES, (".yaml", ".yml"))
        if not found:
            raise ValueError("no OpenAPI YAML file found (tried " + ", ".join(_CONTRACT_CANDIDATES) + "); pass file='relative/path.yaml'")
        p, rel = found
        st = p.stat()
        ck = (str(p), st.st_mtime_ns, st.st_size)
        idx = self._contract_cache.get(ck)
        if idx is None:
            idx = _index_openapi(p.read_text(encoding="utf-8", errors="replace"))
            self._contract_cache = {ck: idx}   # one entry: a changed file simply replaces it
        ops, comps = idx["ops"], idx["comps"]
        out: dict = {"file": rel, "file_chars": st.st_size, "operations_total": len(ops)}

        def finish(o: dict) -> dict:
            o["returned_chars"] = len(json.dumps(o, ensure_ascii=False, default=str))
            return self._track("contract_lookup", o, agent, story)

        q = (query or "").strip()
        if not q:
            out["outline"] = [f"{o['method']} {o['path']} {o['operationId']}" + (f" - {o['summary']}" if o["summary"] else "")
                              for o in ops]
            by_sec: dict[str, list[str]] = {}
            for sec, name in comps:
                by_sec.setdefault(sec, []).append(name)
            out["components"] = {k: sorted(v) for k, v in by_sec.items()}
            out["hint"] = "call contract_lookup('<operationId | METHOD /path | /path | ComponentName>') for one definition"
            return finish(out)

        ql = q.lower()
        selected: list[dict] = []
        comp_keys: list[tuple[str, str]] = []
        mm = re.match(r"^(get|put|post|delete|patch|head|options)\s+(/\S*)$", ql)
        if mm:
            selected = [o for o in ops if o["method"].lower() == mm.group(1) and o["path"].lower() == mm.group(2)]
        if not selected:
            selected = [o for o in ops if o["operationId"].lower() == ql]
        if not selected and ql.startswith("/"):
            selected = [o for o in ops if o["path"].lower() == ql]
        if not selected:
            head, _, tail = q.rpartition("/")
            comp_keys = [k for k in comps if k[1].lower() == (tail or q).lower()
                         and (not head or k[0].lower() == head.split("/")[-1].lower())]
        if not selected and not comp_keys:  # fuzzy: words against method / path / operationId / summary / tags
            words = re.findall(r"[a-z0-9]+", ql)
            scored = []
            for o in ops:
                hay = " ".join([o["method"], o["path"], o["operationId"], o["summary"], *o["tags"]]).lower()
                sc = sum(1 for w in words if w in hay)
                if sc:
                    scored.append((sc, o))
            matches = []
            if scored:
                best = max(sc for sc, _ in scored)
                matches = [o for sc, o in scored if sc == best][:15]
            out["matches"] = [f"{o['method']} {o['path']} {o['operationId']}" for o in matches]
            if not matches:
                out["hint"] = "no match; call contract_lookup() with no query for the outline"
                return finish(out)
            if len(matches) > 2:
                out["hint"] = "several matches; call again with an operationId or 'METHOD /path' for the full definition"
                return finish(out)
            selected = matches

        used, items = 0, []
        for o in selected[:4]:
            cost = len(o["text"]) + len(o["shared"])
            if items and used + cost > max_chars:
                out.setdefault("not_included_operations", []).append(f"{o['method']} {o['path']} {o['operationId']}")
                continue
            it = {"method": o["method"], "path": o["path"], "operationId": o["operationId"], "yaml": o["text"]}
            if o["shared"]:
                it["path_level_yaml"] = o["shared"]
            items.append(it)
            used += cost
        for o in selected[4:]:
            out.setdefault("not_included_operations", []).append(f"{o['method']} {o['path']} {o['operationId']}")
        if items:
            out["operations"] = items
        seeds = [i["yaml"] + i.get("path_level_yaml", "") for i in items] + [comps[k] for k in comp_keys[:3]]
        refs = _collect_refs(seeds, comps)
        common = idx["common"]
        if not include_common:   # components most operations reference (error envelope, 401/429/500...) are fetched by name when needed
            left_out = [f"{k[0]}/{k[1]}" for k in refs if k in common and k not in comp_keys]
            refs = [k for k in refs if k not in common or k in comp_keys]
            if left_out:
                out["common_components_omitted"] = left_out
        wanted = list(dict.fromkeys(comp_keys[:3] + refs))
        included: dict[str, str] = {}
        skipped: list[str] = []
        for k in wanted:
            t = comps[k]
            if used + len(t) > max_chars and (included or items):
                skipped.append(f"{k[0]}/{k[1]}")
                continue
            included[f"{k[0]}/{k[1]}"] = t
            used += len(t)
        if included:
            out["components"] = included
        if skipped:
            out["not_included_components"] = skipped
        return finish(out)

    def conventions(self, role: str = "", topic: str = "", file: str = "", max_chars: int = 9000,
                    agent: str = "", story: str = "") -> dict:
        return self._track("conventions", self._conventions(role, topic, file, max_chars), agent, story)

    def _conventions(self, role: str = "", topic: str = "", file: str = "", max_chars: int = 9000) -> dict:
        """Return only the sections of .pipeline/conventions.md that matter. role = your agent name (picks the sections
        relevant to that role); topic = keywords (matched against headings first, then bodies). With neither, only an
        outline (headings + sizes) comes back."""
        role = _name(role, "role", optional=True)
        topic = _text(topic, "topic", 120)
        max_chars = max(1000, min(int(max_chars), 40000))
        found = self._workspace_file(file, _CONVENTIONS_CANDIDATES, (".md",))
        if not found:
            raise ValueError("no conventions file found (.pipeline/conventions.md); pass file='relative/path.md'")
        p, rel = found
        text = p.read_text(encoding="utf-8", errors="replace")
        secs = _md_sections(text)
        out: dict = {"file": rel, "file_chars": len(text)}
        words = [w for w in re.findall(r"\w+", topic.lower()) if len(w) > 2]
        keys = _ROLE_SECTIONS.get(role, ())
        chosen: list[tuple[str, str]] = []
        if words:
            pools = ([s for s in secs if any(k in s[0].lower() for k in keys)], secs) if keys else (secs,)
            for pool in pools:
                scored = []
                for h, t in pool:
                    hl, tl = h.lower(), t.lower()
                    sc = sum(3 for w in words if w in hl) + sum(1 for w in words if w in tl)
                    if sc:
                        scored.append((sc, h, t))
                if scored:
                    chosen = [(h, t) for _, h, t in sorted(scored, key=lambda x: -x[0])[:4]]
                    break
        elif keys:
            def rank(h: str) -> int:
                return min((i for i, k in enumerate(keys) if k in h.lower()), default=99)
            chosen = sorted(((h, t) for h, t in secs if rank(h) < 99 and "change log" not in h.lower()), key=lambda x: rank(x[0]))
        used, sections, skipped = 0, [], []
        for h, t in chosen:
            if sections and used + len(t) > max_chars:
                skipped.append(h)
                continue
            sections.append({"heading": h, "content": t if len(t) <= max_chars else _cut(t, max_chars)})
            used += len(t)
        out["sections"] = sections
        if skipped:
            out["not_included"] = skipped
        shown = {s["heading"] for s in sections}
        rest = [{"heading": h, "chars": len(t)} for h, t in secs if h not in shown]
        if rest:
            out["other_sections"] = rest
        if not sections:
            out["hint"] = "pass role=<your agent name> and/or topic=<keywords> to get content"
        out["returned_chars"] = len(json.dumps(out, ensure_ascii=False, default=str))
        return out

    # -- token savers: reuse from earlier stories ----------------------------------------------
    def similar_stories(self, story: str, limit: int = 3, agent: str = "") -> dict:
        """Closest already-built stories to this one (by slug words: endpoint verb + resource, rare words weigh more),
        with what was built, the decisions taken and the gotchas/contracts recorded — start from that instead of
        re-exploring the codebase."""
        story = _name(story, "story")
        limit = max(1, min(int(limit), 5))
        with self._connect() as c:
            known = {r["story"] for r in c.execute(
                "SELECT DISTINCT story FROM memories WHERE kind IN ('fact','decision','contract','gotcha') "
                "AND superseded_by IS NULL AND story<>''")}
        files: dict[str, str] = {}   # finished stories keep their plan + implementation notes in .completed/<slug>.md
        for folder in (".completed", ".stories-reviewed"):
            d = self._workspace_dir(folder)
            if d is not None:
                for p in d.glob("*.md"):
                    files.setdefault(p.stem, f"{folder}/{p.name}")
        known |= {s for s in files if _NAME.match(s)}
        known.discard(story)
        toks = {s: _story_tokens(s) for s in known}
        mine = _story_tokens(story)
        res: dict = {"story": story, "similar": []}
        if not mine or not toks:
            return self._track("similar_stories", res, agent, story)
        n = len(toks) + 1
        df: dict[str, int] = {}
        for t in [*toks.values(), mine]:
            for w in t:
                df[w] = df.get(w, 0) + 1

        def weight(w: str) -> float:
            return math.log((n + 1) / (df.get(w, 0) + 1)) + 1.0

        scored = []
        for s, t in toks.items():
            shared = mine & t
            if not (shared - _STORY_GENERIC):
                continue  # sharing only words every story has ('endpoint') is not similarity
            score = sum(weight(w) for w in shared) / sum(weight(w) for w in (mine | t))
            if score >= 0.2:
                scored.append((score, s, shared))
        scored.sort(key=lambda x: (-x[0], x[1]))
        ids: list[int] = []
        with self._connect() as c:
            for score, s, shared in scored[:limit]:
                item: dict = {"story": s, "score": round(score, 2), "shared_words": sorted(shared)}
                if s in files:
                    item["story_file"] = files[s]
                f = c.execute("SELECT id, content FROM memories WHERE story=? AND kind='fact' AND superseded_by IS NULL "
                              "ORDER BY id DESC LIMIT 1", (s,)).fetchone()
                if f:
                    item["built"] = _cut(f["content"], 400)
                    ids.append(f["id"])
                decs = c.execute("SELECT id, tags, content FROM memories WHERE story=? AND kind='decision' AND superseded_by IS NULL "
                                 "ORDER BY id DESC LIMIT 3", (s,)).fetchall()
                if decs:
                    item["decisions"] = [{"topic": d["tags"], "decision": _cut(_field(d["content"], "Decision") or d["content"], 220)} for d in decs]
                    ids.extend(d["id"] for d in decs)
                gots = c.execute("SELECT id, kind, content FROM memories WHERE story=? AND kind IN ('gotcha','contract') "
                                 "AND superseded_by IS NULL ORDER BY id DESC LIMIT 3", (s,)).fetchall()
                if gots:
                    item["notes"] = [{"kind": g["kind"], "content": _cut(g["content"], 200)} for g in gots]
                    ids.extend(g["id"] for g in gots)
                res["similar"].append(item)
        if res["similar"]:
            res["hint"] = ("start from the closest story (its story_file holds the plan and implementation notes; read only the "
                           "section you need); verify against the code before copying")
        return self._track("similar_stories", res, agent, story, ids)

    # -- token savers: cheap session start -------------------------------------------------------
    def queue_status(self, recent: int = 3, agent: str = "") -> dict:
        """Compact pipeline state for a session start: stories completed, the last few (one line each), the story in
        progress with its stage statuses, the latest handoff, open task counts and the story files waiting
        in .user-stories/. Replaces re-reading the whole progress log."""
        recent = max(1, min(int(recent), 10))
        with self._connect() as c:
            done_rows = c.execute("SELECT id, story, content FROM memories WHERE kind='fact' AND key LIKE 'story:%' "
                                  "AND superseded_by IS NULL AND story<>'' ORDER BY id DESC").fetchall()
            h = c.execute("SELECT id, story, content FROM memories WHERE kind='handoff' AND superseded_by IS NULL "
                          "ORDER BY id DESC LIMIT 1").fetchone()
            last = c.execute("SELECT story FROM tasks WHERE story<>'' AND role<>'unit-tester' ORDER BY updated DESC, id DESC LIMIT 1").fetchone()
            tcounts = {r["status"]: r["n"] for r in c.execute(
                "SELECT status, COUNT(*) n FROM tasks WHERE status IN ('open','claimed') GROUP BY status")}
            stages: dict[str, str] = {}
            if last:
                for r in c.execute("SELECT role, status FROM tasks WHERE story=? AND role<>'unit-tester' ORDER BY id", (last["story"],)):
                    stages[r["role"] or "?"] = r["status"]
        done_set = {r["story"] for r in done_rows}
        queue: dict = {}
        d = self._workspace_dir(".user-stories")
        if d is not None:
            names = sorted(p.stem for p in d.glob("*.md"))
            queue["pending"] = len(names)
            queue["next"] = names[:3]
        d = self._workspace_dir(".completed")
        if d is not None:
            queue["completed_files"] = len(list(d.glob("*.md")))
        res = {
            "completed_stories": len(done_set),
            "recent_done": [{"story": r["story"], "built": _cut(r["content"], 240)} for r in done_rows[:recent]],
            "in_progress": {"story": last["story"], "stages": stages} if last and last["story"] not in done_set else None,
            "last_handoff": {"story": h["story"], "content": _cut(h["content"], 500)} if h else None,
            "open_tasks": tcounts,
            "queue": queue,
        }
        ids = [r["id"] for r in done_rows[:recent]] + ([h["id"]] if h else [])
        return self._track("queue_status", res, agent, "", ids)

    # -- token savers: known-flaky tests ---------------------------------------------------------
    def flaky_report(self, test: str, agent: str, story: str = "", cause: str = "") -> dict:
        """Register a test/suite that failed for a non-code reason (port clash, timing, network). Repeats raise its count."""
        test = _text(test, "test", 300, True)
        agent = _name(agent, "agent")
        story = _name(story, "story", optional=True)
        cause = _text(cause, "cause", 300)
        now = time.time()
        with self._tx() as c:
            c.execute("INSERT INTO flaky(test, n, first_ts, last_ts, last_story, last_agent, cause) VALUES (?,1,?,?,?,?,?) "
                      "ON CONFLICT(test) DO UPDATE SET n=n+1, last_ts=excluded.last_ts, last_story=excluded.last_story, "
                      "last_agent=excluded.last_agent, retired=0, "
                      "cause=CASE WHEN excluded.cause<>'' THEN excluded.cause ELSE flaky.cause END",
                      (test, now, now, story, agent, cause))
            n = c.execute("SELECT n FROM flaky WHERE test=?", (test,)).fetchone()["n"]
        return {"test": test, "count": n}

    def flaky_resolve(self, test: str, agent: str) -> dict:
        """Mark a flaky test as fixed (it comes back automatically if flaky_report sees it again)."""
        test = _text(test, "test", 300, True)
        _name(agent, "agent")
        with self._tx() as c:
            n = c.execute("UPDATE flaky SET retired=1 WHERE test=? AND retired=0", (test,)).rowcount
        return {"resolved": bool(n)}

    def flaky_list(self, min_count: int = 1, include_resolved: bool = False, limit: int = 30) -> list[dict]:
        limit = max(1, min(int(limit), 100))
        with self._connect() as c:
            rows = c.execute("SELECT * FROM flaky WHERE n>=? " + ("" if include_resolved else "AND retired=0 ") +
                             "ORDER BY n DESC, last_ts DESC LIMIT ?", (max(1, int(min_count)), limit)).fetchall()
        return [{"test": r["test"], "count": r["n"], "last_seen": _iso(r["last_ts"]), "last_story": r["last_story"],
                 "cause": r["cause"], **({"resolved": True} if r["retired"] else {})} for r in rows]

    # -- aggregates --------------------------------------------------------------------------
    def story_context(self, story: str, per_section: int = 6, agent: str = "", max_chars: int = 12000) -> dict:
        res, ids = self._story_context(story, per_section, max_chars)
        return self._track("story_context", res, agent, res["story"], ids)

    def _story_context(self, story: str, per_section: int = 6, max_chars: int = 12000) -> tuple[dict, list[int]]:
        story = _name(story, "story")
        n = max(1, min(int(per_section), 15))
        max_chars = max(2000, min(int(max_chars), 60000))

        def latest(kinds: tuple[str, ...], only_story: bool) -> list[dict]:
            with self._connect() as c:
                q = ("SELECT * FROM memories WHERE superseded_by IS NULL AND kind IN (" + ",".join("?" * len(kinds)) + ") AND " +
                     ("story=?" if only_story else "(story=? OR story='')") + " ORDER BY id DESC LIMIT ?")
                rows = c.execute(q, (*kinds, story, n)).fetchall()
            out = []
            for r in rows:
                d = self._row(r)
                d["content"] = _snip(r["content"], 600)
                out.append(d)
            return out

        with self._connect() as c:
            h = c.execute("SELECT * FROM memories WHERE superseded_by IS NULL AND kind='handoff' AND story=? ORDER BY id DESC LIMIT 1", (story,)).fetchone()
        res = {
            "story": story,
            "handoff": self._row(h) if h else None,
            "rules": self._rules(10, 300),
            "knowledge": latest(("convention", "contract", "gotcha", "review-pattern", "fact"), False),
            "decisions": latest(("decision",), True),
            "notes": latest(("note",), True),
            "tasks": [t for t in self.task_list(story=story, limit=40) if t["status"] in ("open", "claimed", "failed")],
            "locks": [l for l in self.lock_list() if l["story"] == story],
        }

        def size() -> int:
            return len(json.dumps(res, ensure_ascii=False, default=str))

        if size() > max_chars:  # cap the briefing: shrink entries first, then drop the least important ones
            res["truncated"] = True
            for limit in (300, 150, 80):
                for sec in ("rules", "knowledge", "decisions", "notes"):
                    for it in res[sec]:
                        it["content"] = _cut(it["content"], limit)
                if size() <= max_chars:
                    break
            if size() > max_chars:
                res["notes"] = []
                res["knowledge"], res["decisions"], res["rules"] = res["knowledge"][:4], res["decisions"][:4], res["rules"][:5]
                if res["handoff"]:
                    res["handoff"]["content"] = _cut(res["handoff"]["content"], 300)
        ids = [x["id"] for sec in ("rules", "knowledge", "decisions", "notes") for x in res[sec]]
        if res["handoff"]:
            ids.append(res["handoff"]["id"])
        return res, ids

    def agent_briefing(self, story: str, role: str, agent: str = "", max_chars: int = 12000) -> dict:
        """Everything an agent reads at the start of a story, in one call: the story_context sections (handoff,
        standing rules, knowledge incl. review patterns, this story's decisions, open tasks for this role, locks) plus
        the conventions sections for the role. Half the budget goes to each part; a missing conventions file is
        reported, not raised, so the briefing still works before conventions-scout has run."""
        role = _name(role, "role")
        max_chars = max(4000, min(int(max_chars), 60000))
        ctx, ids = self._story_context(story, 6, max_chars // 2)
        ctx["tasks"] = [t for t in ctx["tasks"] if t["role"] in ("", role)]
        try:
            conv = self._conventions(role=role, max_chars=max_chars // 2)
            ctx["conventions"] = {"file": conv["file"], "sections": conv["sections"]}
            if conv.get("not_included"):
                ctx["conventions"]["not_included"] = conv["not_included"]
        except ValueError as e:
            ctx["conventions"] = {"missing": str(e)}
        ctx["role"] = role
        return self._track("agent_briefing", ctx, agent or role, ctx["story"], ids)

    def stats(self) -> dict:
        with self._connect() as c:
            mem = {r["kind"]: r["n"] for r in c.execute("SELECT kind, COUNT(*) n FROM memories WHERE superseded_by IS NULL GROUP BY kind")}
            tasks = {r["status"]: r["n"] for r in c.execute("SELECT status, COUNT(*) n FROM tasks GROUP BY status")}
            locks = c.execute("SELECT COUNT(*) n FROM locks WHERE expires >= ?", (time.time(),)).fetchone()["n"]
        return {"db": str(self.path), "fts5": self.fts, "memories": mem, "tasks": tasks, "active_locks": locks}


# ----------------------------------------------------------------------------- token savers: pure helpers
_CONTRACT_CANDIDATES = ("contracts/openapi.yaml", "contracts/openapi.yml", "openapi.yaml", "openapi.yml",
                        "docs/openapi.yaml", "api/openapi.yaml")
_CONVENTIONS_CANDIDATES = (".pipeline/conventions.md",)
_REF_RE = re.compile(r"\$ref:\s*['\"]?#/components/([A-Za-z]+)/([A-Za-z0-9_.\-]+)")
_PATH_RE = re.compile(r"^  (/.*?):\s*$")
_METHOD_RE = re.compile(r"^    (get|put|post|delete|options|head|patch|trace):\s*$")
_SECTION_RANK = {"schemas": 0, "parameters": 1, "requestBodies": 2, "responses": 3}

# which `## ` sections of conventions.md matter to which agent (keywords matched against the heading)
_ROLE_SECTIONS = {   # keyword order = priority: the budget cuts the tail, never the section a role lives in
    "dev-backend": ("backend", "api", "test", "security", "command", "repositor", "git"),
    "dev-frontend": ("frontend", "mobile", "i18n", "api", "test", "command", "repositor", "git"),
    "dev-integrator": ("api", "backend", "frontend", "i18n", "command", "git", "repositor"),
    "code-reviewer": ("backend", "frontend", "mobile", "i18n", "api", "test", "security"),
    "security-reviewer": ("security", "api", "backend", "git"),
    "story-validator": ("test", "api", "command"),
    "unit-tester": ("test", "command", "backend", "frontend"),
    "analyst": ("api", "backend", "frontend", "mobile", "i18n", "repositor"),
    "doc-writer": ("repositor", "api", "command", "git"),
}
_STORY_GENERIC = {"endpoint", "api", "by", "for", "of", "to", "and", "the", "a"}   # shared alone, these say nothing
_STORY_SYNONYMS = {"update": "patch", "put": "patch", "create": "post", "list": "get", "fetch": "get",
                   "read": "get", "remove": "delete"}


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _block_end(lines: list[str], start: int, base: int, limit: int) -> int:
    """Index just past the block whose header is lines[start] (indent `base`): stops at the next non-blank
    line indented <= base. Trailing blank lines are excluded."""
    j = start + 1
    while j < limit:
        ln = lines[j]
        if ln.strip() and _indent(ln) <= base:
            break
        j += 1
    while j > start + 1 and not lines[j - 1].strip():
        j -= 1
    return j


def _index_openapi(text: str) -> dict:
    """Line-based index of an OpenAPI YAML file (standard library only — no YAML parser needed).
    Relies on the conventional 2-space layout: `paths:` -> `  /path:` -> `    method:` -> fields, and
    `components:` -> `  section:` -> `    Name:`. Returns {'ops': [...], 'comps': {(section, name): text}}."""
    lines = text.splitlines()
    tops = [(i, m.group(1)) for i, ln in enumerate(lines) if (m := re.match(r"^([A-Za-z][\w-]*):", ln))]
    bounds = {name: (i, tops[k + 1][0] if k + 1 < len(tops) else len(lines)) for k, (i, name) in enumerate(tops)}
    ops, comps = [], {}
    if "paths" in bounds:
        s, e = bounds["paths"]
        i = s + 1
        while i < e:
            m = _PATH_RE.match(lines[i])
            if not m:
                i += 1
                continue
            path = m.group(1).strip("'\"")
            pend = _block_end(lines, i, 2, e)
            methods = [(j, mm.group(1)) for j in range(i + 1, pend) if (mm := _METHOD_RE.match(lines[j]))]
            shared = "\n".join(lines[i + 1:methods[0][0]]).strip() if methods else ""
            for k, (j, method) in enumerate(methods):
                oend = methods[k + 1][0] if k + 1 < len(methods) else pend
                body = lines[j:oend]
                while body and not body[-1].strip():
                    body.pop()
                opid = summary = ""
                tags: list[str] = []
                for x, ln in enumerate(body):
                    if (mo := re.match(r"^      operationId:\s*(.+?)\s*$", ln)):
                        opid = mo.group(1).strip("'\"")
                    elif (ms := re.match(r"^      summary:\s*(.+?)\s*$", ln)):
                        summary = ms.group(1).strip("'\"")
                    elif (mt := re.match(r"^      tags:\s*\[(.*)\]\s*$", ln)):
                        tags = [t.strip().strip("'\"") for t in mt.group(1).split(",") if t.strip()]
                    elif re.match(r"^      tags:\s*$", ln):
                        for nxt in body[x + 1:x + 8]:
                            mi = re.match(r"^        - (.+?)\s*$", nxt)
                            if not mi:
                                break
                            tags.append(mi.group(1).strip("'\""))
                ops.append({"method": method.upper(), "path": path, "operationId": opid, "summary": summary,
                            "tags": tags, "text": "\n".join(body), "shared": shared})
            i = pend
    if "components" in bounds:
        s, e = bounds["components"]
        sec, i = "", s + 1
        while i < e:
            ln = lines[i]
            if (ms := re.match(r"^  ([A-Za-z]+):\s*$", ln)):
                sec = ms.group(1)
                i += 1
            elif sec and (mn := re.match(r"^    ([A-Za-z0-9_.\-]+):", ln)):
                end = _block_end(lines, i, 4, e)
                comps[(sec, mn.group(1))] = "\n".join(lines[i:end])
                i = end
            else:
                i += 1
    freq: dict[tuple[str, str], int] = {}
    for o in ops:
        for k in _collect_refs([o["text"] + o["shared"]], comps):
            freq[k] = freq.get(k, 0) + 1
    common = {k for k, v in freq.items() if len(ops) >= 4 and v >= 0.6 * len(ops)}
    return {"ops": ops, "comps": comps, "common": common}


def _collect_refs(texts: list[str], comps: dict, depth: int = 3) -> list[tuple[str, str]]:
    """Components referenced (transitively, up to `depth` levels) from the given YAML texts, schemas first."""
    seen: list[tuple[str, str]] = []
    frontier = texts
    for _ in range(depth):
        nxt = []
        for t in frontier:
            for sec, name in _REF_RE.findall(t):
                key = (sec, name)
                if key in comps and key not in seen:
                    seen.append(key)
                    nxt.append(comps[key])
        frontier = nxt
        if not frontier:
            break
    return sorted(seen, key=lambda k: _SECTION_RANK.get(k[0], 9))  # stable: keeps discovery order inside a rank


def _md_sections(text: str) -> list[tuple[str, str]]:
    """Split a markdown file into (heading, text-including-heading) pairs on `## ` lines."""
    secs: list[tuple[str, str]] = []
    cur, buf = None, []
    for ln in text.splitlines():
        if ln.startswith("## "):
            if cur is not None:
                secs.append((cur, "\n".join(buf).strip()))
            cur, buf = ln[3:].strip(), [ln]
        elif cur is not None:
            buf.append(ln)
    if cur is not None:
        secs.append((cur, "\n".join(buf).strip()))
    return secs


def _story_tokens(slug: str) -> set[str]:
    parts = re.split(r"[-_.:#]+", (slug or "").lower())
    return {_STORY_SYNONYMS.get(p, p) for p in parts if p and not p.isdigit()}


def _split(script: str) -> list[str]:
    """Split a schema script into single statements (triggers contain ';' inside BEGIN..END)."""
    out, buf, in_trigger = [], [], False
    for line in script.splitlines():
        buf.append(line)
        s = line.strip().upper()
        if s.startswith("CREATE TRIGGER"):
            in_trigger = True
        if in_trigger:
            if s == "END;":
                out.append("\n".join(buf)); buf, in_trigger = [], False
        elif s.endswith(";"):
            out.append("\n".join(buf)); buf = []
    tail = "\n".join(buf).strip()
    if tail:
        out.append(tail)
    return [x for x in out if x.strip()]
