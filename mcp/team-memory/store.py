"""team-memory store — SQLite-backed shared memory, task board and file locks for a team of agents.

Pure standard library (no MCP dependency) so it can be unit-tested and reused. Every operation opens its
own short-lived connection (WAL + busy_timeout), so many processes — one MCP server per agent session,
parallel worktrees, scripts — can share one database file safely. Multi-step changes run inside
BEGIN IMMEDIATE transactions, which is what makes task claims and locks race-free.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

KINDS = ("note", "decision", "convention", "gotcha", "contract", "review-pattern", "handoff", "fact")
TASK_FINAL = ("done", "failed")
MAX_CONTENT = 8000
SNIPPET = 2000
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


def _fts_query(query: str) -> str:
    tokens = re.findall(r"\w+", query or "", re.UNICODE)[:8]
    return " OR ".join(f'"{t}"*' for t in tokens)


# ----------------------------------------------------------------------------- store
def default_db_path() -> Path:
    """$TEAM_MEMORY_DB, else <workspace>/.claude/team-memory.db.
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
    return root / ".claude" / "team-memory.db"


class Store:
    def __init__(self, path: str | os.PathLike | None = None) -> None:
        self.path = Path(path) if path else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
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

    def _row(self, r: sqlite3.Row, full: bool = False) -> dict:
        d = {"id": r["id"], "ts": _iso(r["ts"]), "agent": r["agent"], "story": r["story"], "kind": r["kind"],
             "key": r["key"], "tags": r["tags"], "content": r["content"] if full else _snip(r["content"])}
        if r["superseded_by"] is not None:
            d["superseded_by"] = r["superseded_by"]
        return d

    def recall(self, query: str = "", story: str = "", kind: str = "", limit: int = 10,
               include_retired: bool = False) -> list[dict]:
        story = _name(story, "story", optional=True)
        if kind and kind not in KINDS:
            raise ValueError(f"kind must be one of {', '.join(KINDS)}")
        limit = max(1, min(int(limit), 50))
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
        return [self._row(r) for r in rows]

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
        return self.remember(agent, "decision", body, story=story, tags=topic)

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

    # -- aggregates --------------------------------------------------------------------------
    def story_context(self, story: str, per_section: int = 6) -> dict:
        story = _name(story, "story")
        n = max(1, min(int(per_section), 15))

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
        return {
            "story": story,
            "handoff": self._row(h) if h else None,
            "knowledge": latest(("convention", "contract", "gotcha", "review-pattern", "fact"), False),
            "decisions": latest(("decision",), True),
            "notes": latest(("note",), True),
            "tasks": [t for t in self.task_list(story=story, limit=40) if t["status"] in ("open", "claimed", "failed")],
            "locks": [l for l in self.lock_list() if l["story"] == story],
        }

    def stats(self) -> dict:
        with self._connect() as c:
            mem = {r["kind"]: r["n"] for r in c.execute("SELECT kind, COUNT(*) n FROM memories WHERE superseded_by IS NULL GROUP BY kind")}
            tasks = {r["status"]: r["n"] for r in c.execute("SELECT status, COUNT(*) n FROM tasks GROUP BY status")}
            locks = c.execute("SELECT COUNT(*) n FROM locks WHERE expires >= ?", (time.time(),)).fetchone()["n"]
        return {"db": str(self.path), "fts5": self.fts, "memories": mem, "tasks": tasks, "active_locks": locks}


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
