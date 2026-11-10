#!/usr/bin/env python3
"""learn.py - cross-session learnings store for Claude Code (stdlib only, Python 3.9+).

Hook entry points (never fail a session: always exit 0):
  load      SessionStart / SubagentStart: inject approved learnings (global + current project)
  capture   SessionEnd: queue the session and start a detached analysis
  sweep     background: analyse queued/failed sessions and transcripts that never fired SessionEnd

Analysis:
  analyze   analyse one queued session with a headless `claude -p` and store candidates as 'pending'
  digest    print the condensed digest of a transcript (diagnostic)

Review (used by /learn-review):
  report    pending learnings grouped by scope
  act       approve | reject | defer | forget | edit | scope | md | nomd
  add       store an explicit, already-approved learning
  list      browse stored learnings
  claude-md plan | apply   managed block in CLAUDE.md (project or ~/.claude)
  ui        read-only web view of the database (live server, or --out snapshot.html)
  export    write global.md + projects/<name>.md (+ INDEX.md) from the database
  import    restore those markdown files into a database (idempotent)

Setup:
  init | status | install-hooks | uninstall-hooks
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ANALYZER_ENV = "CLAUDE_LEARN_ANALYZER"
SKILL_DIR = Path(__file__).resolve().parent.parent
HOOK_MARK = "learning-memory/scripts/run.sh"
MD_START = "<!-- learnings:start (managed by /learn-review; lines are tracked by id) -->"
MD_END = "<!-- learnings:end -->"
MD_HEADING = "## Learned rules"

KINDS = ("rule", "decision", "pitfall", "preference")
SOURCES = ("correction", "question", "error", "decision", "manual")
CONFS = ("high", "medium", "low")
CONF_RANK = {"high": 3, "medium": 2, "low": 1}
KIND_RANK = {"pitfall": 3, "rule": 3, "preference": 2, "decision": 1}

DEFAULTS = {
    "model": "sonnet",
    "auto_analyze": True,
    "max_digest_chars": 60000,
    "analyzer_timeout": 300,
    "session_budget_items": 40,
    "session_budget_chars": 6000,
    "subagent_budget_items": 25,
    "subagent_budget_chars": 3500,
    "max_candidates": 12,
    "max_attempts": 3,
    "idle_seconds": 600,
    "claude_args": ["--no-session-persistence", "--tools", ""],
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS projects(
  id INTEGER PRIMARY KEY,
  key TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  root TEXT NOT NULL DEFAULT '',
  created_at REAL NOT NULL,
  last_seen REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS learnings(
  id INTEGER PRIMARY KEY,
  scope TEXT NOT NULL CHECK (scope IN ('global','project')),
  project_id INTEGER REFERENCES projects(id),
  kind TEXT NOT NULL CHECK (kind IN ('rule','decision','pitfall','preference')),
  text TEXT NOT NULL,
  rationale TEXT NOT NULL DEFAULT '',
  evidence TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT 'manual'
    CHECK (source IN ('correction','question','error','decision','manual')),
  confidence TEXT NOT NULL DEFAULT 'medium' CHECK (confidence IN ('high','medium','low')),
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','approved','rejected','deferred','superseded')),
  claude_md INTEGER NOT NULL DEFAULT 0,
  claude_md_applied INTEGER NOT NULL DEFAULT 0,
  applied_file TEXT NOT NULL DEFAULT '',
  supersedes_id INTEGER REFERENCES learnings(id),
  fingerprint TEXT NOT NULL,
  session_id TEXT NOT NULL DEFAULT '',
  created_at REAL NOT NULL,
  reviewed_at REAL,
  CHECK ((scope='global' AND project_id IS NULL) OR (scope='project' AND project_id IS NOT NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_learning ON learnings(scope, COALESCE(project_id,0), fingerprint);
CREATE INDEX IF NOT EXISTS ix_learning_status ON learnings(status, scope, project_id);
CREATE TABLE IF NOT EXISTS sessions(
  session_id TEXT PRIMARY KEY,
  project_id INTEGER REFERENCES projects(id),
  transcript_path TEXT NOT NULL DEFAULT '',
  cwd TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued','analyzing','done','failed','skipped')),
  attempts INTEGER NOT NULL DEFAULT 0,
  error TEXT NOT NULL DEFAULT '',
  analyzed_bytes INTEGER NOT NULL DEFAULT 0,
  candidates INTEGER NOT NULL DEFAULT 0,
  queued_at REAL NOT NULL,
  updated_at REAL NOT NULL
);
"""


# --------------------------------------------------------------------------- paths / config

def home_dir() -> Path:
    return Path(os.environ.get("LEARN_HOME") or (Path.home() / ".claude" / "learnings"))


def db_path() -> Path:
    return home_dir() / "learnings.db"


def global_md_path() -> Path:
    return Path(os.environ.get("LEARN_GLOBAL_MD") or (Path.home() / ".claude" / "CLAUDE.md"))


def settings_path() -> Path:
    return Path(os.environ.get("LEARN_SETTINGS") or (Path.home() / ".claude" / "settings.json"))


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    p = home_dir() / "config.json"
    try:
        cfg.update(json.loads(p.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    if os.environ.get("LEARN_MODEL"):
        cfg["model"] = os.environ["LEARN_MODEL"]
    if os.environ.get("LEARN_AUTO_ANALYZE") == "0":
        cfg["auto_analyze"] = False
    return cfg


def log(msg: str) -> None:
    try:
        home_dir().mkdir(parents=True, exist_ok=True)
        with open(home_dir() / "analyzer.log", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")
    except OSError:
        pass


def now() -> float:
    return time.time()


def fmt_ts(t: float | None) -> str:
    return datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M") if t else "-"


def clip(s: str, n: int) -> str:
    s = s or ""
    return s if len(s) <= n else s[: n - 1] + "…"


def one_line(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


# --------------------------------------------------------------------------- subprocess helpers

NT = os.name == "nt"
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_BREAKAWAY_FROM_JOB = 0x01000000


def run_quiet(argv: list[str], **kw):
    if NT:
        kw.setdefault("creationflags", CREATE_NO_WINDOW)
    return subprocess.run(argv, **kw)


def spawn_detached(argv: list[str]) -> None:
    """Start a process that outlives the hook that started it."""
    home_dir().mkdir(parents=True, exist_ok=True)
    out = open(home_dir() / "analyzer.log", "a", encoding="utf-8")
    kw = dict(stdin=subprocess.DEVNULL, stdout=out, stderr=out, close_fds=True)
    if NT:
        base = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        try:
            subprocess.Popen(argv, creationflags=base | CREATE_BREAKAWAY_FROM_JOB, **kw)
        except OSError:
            subprocess.Popen(argv, creationflags=base, **kw)
    else:
        subprocess.Popen(argv, start_new_session=True, **kw)


# --------------------------------------------------------------------------- database

_CONNS: list = []


def close_all(since: int = 0) -> None:
    while len(_CONNS) > since:
        try:
            _CONNS.pop().close()
        except sqlite3.Error:
            pass


def connect(create: bool = True, query_only: bool = False):
    p = db_path()
    if not p.exists():
        if not create:
            return None
        p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), timeout=10)
    _CONNS.append(conn)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=8000")
    if query_only:
        conn.execute("PRAGMA query_only=ON")
        return conn
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.DatabaseError:
        pass
    conn.execute("INSERT OR IGNORE INTO meta(key,value) VALUES('installed_at',?)", (str(now()),))
    conn.commit()
    return conn


def installed_at(conn) -> float:
    try:
        row = conn.execute("SELECT value FROM meta WHERE key='installed_at'").fetchone()
        return float(row["value"]) if row else 0.0
    except (sqlite3.Error, ValueError):
        return 0.0


# --------------------------------------------------------------------------- project identity

def _git(cwd: str, *args: str) -> str:
    try:
        r = run_quiet(["git", "-C", cwd, *args], capture_output=True, text=True,
                      encoding="utf-8", timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def normalize_remote(url: str) -> str | None:
    url = (url or "").strip()
    if not url:
        return None
    m = re.match(r"^(?:[\w.\-]+@)([^:/]+):(.+)$", url)  # scp-like: git@host:owner/repo.git
    if not m:
        m = re.match(r"^[A-Za-z][A-Za-z0-9+.\-]*://(?:[^@/]+@)?([^/:]+)(?::\d+)?/(.+)$", url)
    if not m:
        return None
    host, path = m.groups()
    path = re.sub(r"\.git/?$", "", path).strip("/")
    return f"{host.lower()}/{path.lower()}" if path else None


def resolve_project(cwd: str) -> dict:
    cwd = cwd or os.getcwd()
    top = _git(cwd, "rev-parse", "--show-toplevel")
    root = top or cwd
    root_norm = os.path.normcase(os.path.realpath(root)).replace("\\", "/")
    remote = normalize_remote(_git(cwd, "remote", "get-url", "origin")) if top else None
    if remote:
        key, name, via = remote, remote.rsplit("/", 1)[-1], "remote"
    else:
        key, name, via = "path:" + root_norm, Path(root).name or root_norm, "path"
    return {"key": key, "name": name, "root": root.replace("\\", "/"), "via": via}


def upsert_project(conn, proj: dict) -> int:
    t = now()
    conn.execute(
        "INSERT INTO projects(key,name,root,created_at,last_seen) VALUES(?,?,?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET name=excluded.name, root=excluded.root, last_seen=excluded.last_seen",
        (proj["key"], proj["name"], proj["root"], t, t))
    conn.commit()
    return conn.execute("SELECT id FROM projects WHERE key=?", (proj["key"],)).fetchone()["id"]


def find_project_id(conn, proj: dict):
    row = conn.execute("SELECT id FROM projects WHERE key=?", (proj["key"],)).fetchone()
    return row["id"] if row else None


# --------------------------------------------------------------------------- learnings CRUD

def fingerprint(text: str) -> str:
    norm = re.sub(r"[^\w]+", " ", (text or "").lower()).strip()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:16]


def find_dup(conn, scope: str, pid, fp: str):
    """A learning already stored (any status) in the same scope, or globally."""
    row = conn.execute(
        "SELECT * FROM learnings WHERE fingerprint=? AND "
        "(scope='global' OR (scope='project' AND project_id IS ?))", (fp, pid)).fetchone()
    return row


def add_learning(conn, *, scope, pid, kind, text, rationale="", evidence="", source="manual",
                 confidence="medium", status="pending", claude_md=False, session_id="",
                 supersedes_id=None):
    """Returns (id, created). Duplicates (same normalised text, any status) are not re-inserted."""
    text = one_line(text)
    if not text:
        raise ValueError("empty text")
    if scope == "global":
        pid = None
    fp = fingerprint(text)
    dup = find_dup(conn, scope, pid, fp)
    if dup:
        return dup["id"], False
    cur = conn.execute(
        "INSERT INTO learnings(scope,project_id,kind,text,rationale,evidence,source,confidence,status,"
        "claude_md,supersedes_id,fingerprint,session_id,created_at,reviewed_at) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (scope, pid, kind, clip(text, 400), clip(one_line(rationale), 400), clip(one_line(evidence), 400),
         source, confidence, status, 1 if claude_md else 0, supersedes_id, fp, session_id, now(),
         now() if status == "approved" else None))
    conn.commit()
    return cur.lastrowid, True


def coerce_candidate(c: dict):
    if not isinstance(c, dict):
        return None
    text = one_line(str(c.get("text", "")))
    if len(text) < 8:
        return None
    scope = c.get("scope") if c.get("scope") in ("global", "project") else "project"
    kind = c.get("kind") if c.get("kind") in KINDS else "rule"
    source = c.get("source") if c.get("source") in SOURCES[:-1] else "correction"
    conf = c.get("confidence") if c.get("confidence") in CONFS else "medium"
    sup = c.get("supersedes")
    sup = sup if isinstance(sup, int) and not isinstance(sup, bool) else None
    return dict(scope=scope, kind=kind, text=text, rationale=str(c.get("rationale", "")),
                evidence=str(c.get("evidence", "")), source=source, confidence=conf,
                claude_md=bool(c.get("claude_md")), supersedes=sup)


def insert_candidates(conn, cands: list, pid: int, sid: str, limit: int) -> int:
    created = 0
    for raw in cands:
        c = coerce_candidate(raw)
        if not c:
            continue
        sup = None
        if c["supersedes"]:
            old = conn.execute(
                "SELECT id FROM learnings WHERE id=? AND status IN ('approved','pending','deferred') "
                "AND (scope='global' OR project_id=?)", (c["supersedes"], pid)).fetchone()
            sup = old["id"] if old else None
        try:
            _, new = add_learning(conn, scope=c["scope"], pid=pid, kind=c["kind"], text=c["text"],
                                  rationale=c["rationale"], evidence=c["evidence"], source=c["source"],
                                  confidence=c["confidence"], status="pending", claude_md=c["claude_md"],
                                  session_id=sid, supersedes_id=sup)
        except (ValueError, sqlite3.Error) as e:
            log(f"insert skipped: {e}")
            continue
        created += 1 if new else 0
        if created >= limit:
            break
    return created


# --------------------------------------------------------------------------- stdin / output helpers

def read_stdin_json() -> dict:
    try:
        if sys.stdin is None or sys.stdin.isatty():
            return {}
        data = sys.stdin.read()
        return json.loads(data) if data.strip() else {}
    except (OSError, ValueError):
        return {}


def emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


# --------------------------------------------------------------------------- hook: load

def select_for_load(conn, pid, *, include_applied: bool, max_items: int, max_chars: int) -> list:
    sql = ("SELECT * FROM learnings WHERE status='approved' AND (scope='global' OR project_id IS ?)")
    if not include_applied:
        sql += " AND claude_md_applied=0"
    rows = conn.execute(sql, (pid,)).fetchall()
    rows.sort(key=lambda r: (-CONF_RANK.get(r["confidence"], 2), 0 if r["scope"] == "project" else 1,
                             -KIND_RANK.get(r["kind"], 1), -r["created_at"]))
    out, used = [], 0
    for r in rows:
        line = f"- [{r['kind']}] {r['text']} (#{r['id']})"
        if len(out) >= max_items or used + len(line) > max_chars:
            continue
        out.append(r)
        used += len(line) + 1
    return out


def format_context(rows: list, project_name: str) -> str:
    glob = [r for r in rows if r["scope"] == "global"]
    proj = [r for r in rows if r["scope"] == "project"]
    parts = ["## Learned context",
             "Approved learnings from past sessions. Apply them without mentioning this block "
             "unless asked. Manage them with /learn-review."]
    for title, items in (("Global", glob), (f"Project: {project_name}", proj)):
        if items:
            parts.append(f"### {title}")
            parts += [f"- [{r['kind']}] {r['text']} (#{r['id']})" for r in items]
    return "\n".join(parts)


def needs_sweep(conn, tdir: str, current: str, cfg: dict) -> bool:
    t = now()
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM sessions WHERE session_id<>? AND "
        "(status='queued' OR (status='failed' AND attempts<?) OR (status='analyzing' AND updated_at<?))",
        (current, cfg["max_attempts"], t - 1800)).fetchone()
    if row["n"]:
        return True
    return bool(find_unseen(conn, tdir, current, cfg, limit=1))


def find_unseen(conn, tdir: str, current: str, cfg: dict, limit: int = 3) -> list:
    """Transcripts of sessions that never fired SessionEnd (crash, closed terminal)."""
    if not tdir or not os.path.isdir(tdir):
        return []
    known = {r["session_id"] for r in conn.execute("SELECT session_id FROM sessions")}
    floor, ceil = installed_at(conn), now() - cfg["idle_seconds"]
    found = []
    try:
        for name in os.listdir(tdir):
            if not name.endswith(".jsonl"):
                continue
            sid = name[:-6]
            full = os.path.join(tdir, name)
            try:
                mt = os.path.getmtime(full)
            except OSError:
                continue
            if sid != current and sid not in known and floor <= mt <= ceil:
                found.append((mt, sid, full))
    except OSError:
        return []
    found.sort(reverse=True)
    return found[:limit]


def cmd_load(args) -> int:
    if os.environ.get(ANALYZER_ENV):
        return 0
    payload = read_stdin_json()
    event = args.event or payload.get("hook_event_name") or "SessionStart"
    cwd = payload.get("cwd") or os.getcwd()
    conn = connect(create=False, query_only=True)
    if conn is None:
        return 0
    cfg = load_config()
    proj = resolve_project(cwd)
    pid = find_project_id(conn, proj)
    sub = event == "SubagentStart"
    rows = select_for_load(conn, pid, include_applied=sub,
                           max_items=cfg["subagent_budget_items" if sub else "session_budget_items"],
                           max_chars=cfg["subagent_budget_chars" if sub else "session_budget_chars"])
    out: dict = {}
    if rows:
        out["hookSpecificOutput"] = {"hookEventName": event,
                                     "additionalContext": format_context(rows, proj["name"])}
    if not sub:
        n = conn.execute("SELECT COUNT(*) AS n FROM learnings WHERE status='pending' AND "
                         "(scope='global' OR project_id IS ?)", (pid,)).fetchone()["n"]
        if n:
            out["systemMessage"] = f"{n} learning(s) pending review for {proj['name']}: run /learn-review"
    if out:
        emit(out)
    if not sub and cfg["auto_analyze"]:
        tdir = os.path.dirname(payload.get("transcript_path") or "")
        try:
            if needs_sweep(conn, tdir, payload.get("session_id") or "", cfg):
                spawn_detached([sys.executable, str(Path(__file__).resolve()), "sweep",
                                "--cwd", cwd, "--transcripts-dir", tdir,
                                "--current", payload.get("session_id") or ""])
        except (OSError, sqlite3.Error) as e:
            log(f"sweep spawn failed: {e}")
    return 0


# --------------------------------------------------------------------------- hook: capture / sweep

def queue_session(conn, sid: str, pid: int, tpath: str, cwd: str) -> None:
    t = now()
    conn.execute(
        "INSERT INTO sessions(session_id,project_id,transcript_path,cwd,status,queued_at,updated_at) "
        "VALUES(?,?,?,?, 'queued', ?, ?) ON CONFLICT(session_id) DO UPDATE SET "
        "transcript_path=excluded.transcript_path, cwd=excluded.cwd, updated_at=excluded.updated_at, "
        "attempts=0, status=CASE WHEN status='analyzing' THEN status ELSE 'queued' END",
        (sid, pid, tpath, cwd, t, t))
    conn.commit()


def cmd_capture(args) -> int:
    if os.environ.get(ANALYZER_ENV):
        return 0
    payload = read_stdin_json()
    sid = payload.get("session_id")
    if not sid:
        return 0
    cwd = payload.get("cwd") or os.getcwd()
    conn = connect()
    pid = upsert_project(conn, resolve_project(cwd))
    queue_session(conn, sid, pid, payload.get("transcript_path") or "", cwd)
    if load_config()["auto_analyze"]:
        spawn_detached([sys.executable, str(Path(__file__).resolve()), "analyze", "--session", sid])
    return 0


def cmd_sweep(args) -> int:
    if os.environ.get(ANALYZER_ENV):
        return 0
    cfg = load_config()
    conn = connect()
    proj_id = upsert_project(conn, resolve_project(args.cwd or os.getcwd()))
    for _, sid, full in find_unseen(conn, args.transcripts_dir, args.current, cfg):
        queue_session(conn, sid, proj_id, full, args.cwd or os.getcwd())
    t = now()
    rows = conn.execute(
        "SELECT session_id FROM sessions WHERE session_id<>? AND "
        "(status='queued' OR (status='failed' AND attempts<?) OR (status='analyzing' AND updated_at<?)) "
        "ORDER BY queued_at LIMIT 5", (args.current or "", cfg["max_attempts"], t - 1800)).fetchall()
    for r in rows:
        analyze_session(conn, r["session_id"], cfg)
    return 0


# --------------------------------------------------------------------------- transcript digest

SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_\-]{20,}"), "[REDACTED]"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"), "[REDACTED]"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED]"),
    (re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._\-]{20,}"), r"\1 [REDACTED]"),
    (re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key)\b(\s*[:=]\s*)\S+"), r"\1\2[REDACTED]"),
]
NOISE_PREFIXES = ("<system-reminder>", "<command-", "<local-command", "<user-prompt-submit-hook>",
                  "Caveat:", "This session is being continued")


def redact(s: str) -> str:
    for pat, rep in SECRET_PATTERNS:
        s = pat.sub(rep, s)
    return s


def read_transcript(path: str, start: int = 0):
    """Complete JSONL entries after byte offset `start`. Returns (entries, end_offset)."""
    with open(path, "rb") as f:
        f.seek(start)
        data = f.read()
    if data and not data.endswith(b"\n"):
        tail = data.rsplit(b"\n", 1)[-1]
        try:
            json.loads(tail.decode("utf-8", "replace"))
        except ValueError:
            data = data[: len(data) - len(tail)]
    entries = []
    for line in data.split(b"\n"):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line.decode("utf-8", "replace")))
        except ValueError:
            continue
    return entries, start + len(data)


def _flatten(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


def _brief(name: str, inp: dict) -> str:
    inp = inp if isinstance(inp, dict) else {}
    for k in ("command", "file_path", "path", "pattern", "url", "description"):
        if inp.get(k):
            return f"{name} {clip(one_line(str(inp[k])), 150)}"
    return name


def digest_items(entries: list) -> list:
    items, tools = [], {}
    for e in entries:
        if not isinstance(e, dict) or e.get("isSidechain") or e.get("isMeta"):
            continue
        t = e.get("type")
        content = (e.get("message") or {}).get("content")
        blocks = [{"type": "text", "text": content}] if isinstance(content, str) else (content or [])
        for b in blocks:
            if not isinstance(b, dict):
                continue
            bt = b.get("type")
            if t == "user" and bt == "text":
                txt = (b.get("text") or "").strip()
                if txt and not txt.startswith(NOISE_PREFIXES):
                    items.append(("user", clip(txt, 1500)))
            elif t == "user" and bt == "tool_result":
                body = _flatten(b.get("content"))
                name, brief = tools.get(b.get("tool_use_id"), ("", "?"))
                if name == "AskUserQuestion":
                    items.append(("answer", clip(one_line(body), 800)))
                elif b.get("is_error"):
                    low = body.lower()
                    kind = "rejected" if ("doesn't want to proceed" in low or "user rejected" in low) else "error"
                    items.append((kind, f"{brief}: {clip(one_line(body), 300)}"))
            elif t == "assistant" and bt == "text":
                txt = (b.get("text") or "").strip()
                if txt:
                    items.append(("claude", clip(one_line(txt), 500)))
            elif t == "assistant" and bt == "tool_use":
                name, inp = b.get("name", ""), b.get("input") or {}
                tools[b.get("id")] = (name, _brief(name, inp))
                if name == "AskUserQuestion":
                    qs = []
                    for q in inp.get("questions", []) if isinstance(inp, dict) else []:
                        opts = ", ".join(o.get("label", "") for o in q.get("options", []) if isinstance(o, dict))
                        qs.append(f"{q.get('question', '')} [{opts}]")
                    items.append(("asked", clip(" | ".join(qs), 800)))
    return items


def fit_digest(items: list, cap: int) -> str:
    lines = [f"[{k.upper()}] {redact(t)}" for k, t in items]
    total = sum(len(l) + 1 for l in lines)
    if total <= cap:
        return "\n".join(lines)
    keep = [True] * len(lines)
    for i, (k, _) in enumerate(items):
        if total <= cap:
            break
        if k == "claude":
            total -= len(lines[i]) + 1
            keep[i] = False
    s = "\n".join(l for l, k in zip(lines, keep) if k)
    if len(s) <= cap:
        return s
    head = cap // 4
    return s[:head] + "\n[... middle omitted ...]\n" + s[-(cap - head - 30):]


# --------------------------------------------------------------------------- analysis

def read_md(path: Path, limit: int = 4000) -> str:
    try:
        return clip(path.read_text(encoding="utf-8"), limit)
    except OSError:
        return "(none)"


def existing_block(conn, pid) -> str:
    rows = conn.execute("SELECT id,scope,kind,status,text FROM learnings "
                        "WHERE scope='global' OR project_id IS ? ORDER BY id DESC LIMIT 200", (pid,))
    lines = [f"#{r['id']} [{r['scope']}/{r['kind']}/{r['status']}] {clip(r['text'], 200)}" for r in rows]
    return "\n".join(lines) or "(none)"


def build_prompt(conn, proj: dict, pid, digest: str) -> str:
    tpl = (SKILL_DIR / "prompts" / "extract.md").read_text(encoding="utf-8")
    root = Path(proj["root"])
    subs = {"{{PROJECT}}": f"{proj['name']} ({proj['key']})",
            "{{EXISTING}}": existing_block(conn, pid),
            "{{CLAUDE_MD_PROJECT}}": read_md(root / "CLAUDE.md"),
            "{{CLAUDE_MD_GLOBAL}}": read_md(global_md_path()),
            "{{DIGEST}}": digest}
    for k, v in subs.items():
        tpl = tpl.replace(k, v)
    return tpl


OPTION_ERROR = re.compile(r"unknown|unrecognized|invalid|unexpected|usage|option|argument", re.I)


def run_claude(prompt: str, cfg: dict) -> str:
    """Headless analysis. Retries with fewer flags only when the CLI rejected an option."""
    binary = os.environ.get("LEARN_CLAUDE_BIN") or shutil.which("claude") or "claude"
    env = dict(os.environ, **{ANALYZER_ENV: "1"})
    home_dir().mkdir(parents=True, exist_ok=True)
    arg_sets = [list(cfg["claude_args"]), ["--no-session-persistence"], []]
    seen, err = [], ""
    for extra in arg_sets:
        if extra in seen:
            continue
        seen.append(extra)
        argv = [binary, "-p", "--model", cfg["model"], "--output-format", "text", *extra]
        r = run_quiet(argv, input=prompt, capture_output=True, text=True, encoding="utf-8",
                      timeout=cfg["analyzer_timeout"], env=env, cwd=str(home_dir()))
        if r.returncode == 0:
            return r.stdout
        err = f"claude exited {r.returncode}: {clip(one_line(r.stderr or r.stdout), 300)}"
        if not OPTION_ERROR.search(r.stderr or ""):
            break
    raise RuntimeError(err)


def parse_candidates(text: str) -> list:
    s = text.strip()
    a, b = s.find("{"), s.rfind("}")
    if a < 0 or b <= a:
        raise ValueError("no JSON object in analyzer output")
    data = json.loads(s[a:b + 1])
    items = data.get("learnings")
    if not isinstance(items, list):
        raise ValueError("missing 'learnings' list")
    return items


def set_session(conn, sid: str, **fields) -> None:
    fields["updated_at"] = now()
    cols = ", ".join(f"{k}=?" for k in fields)
    conn.execute(f"UPDATE sessions SET {cols} WHERE session_id=?", (*fields.values(), sid))
    conn.commit()


def claim_session(conn, sid: str) -> bool:
    t = now()
    cur = conn.execute(
        "UPDATE sessions SET status='analyzing', attempts=attempts+1, updated_at=? WHERE session_id=? "
        "AND (status IN ('queued','failed') OR (status='analyzing' AND updated_at<?))", (t, sid, t - 1800))
    conn.commit()
    return cur.rowcount == 1


def analyze_session(conn, sid: str, cfg: dict) -> str:
    if not claim_session(conn, sid):
        return "not-claimed"
    row = conn.execute("SELECT * FROM sessions WHERE session_id=?", (sid,)).fetchone()
    try:
        tpath = row["transcript_path"]
        if not tpath or not os.path.isfile(tpath):
            raise FileNotFoundError(f"transcript not found: {tpath!r}")
        entries, end = read_transcript(tpath, row["analyzed_bytes"])
        items = digest_items(entries)
        signals = sum(1 for k, _ in items if k in ("user", "answer", "rejected", "error"))
        if signals < 2:
            set_session(conn, sid, status="skipped", analyzed_bytes=end, error="")
            return "skipped"
        digest = fit_digest(items, cfg["max_digest_chars"])
        proj = resolve_project(row["cwd"] or os.getcwd())
        pid = row["project_id"]
        prompt = build_prompt(conn, proj, pid, digest)
        cands = parse_candidates(run_claude(prompt, cfg))
        n = insert_candidates(conn, cands, pid, sid, cfg["max_candidates"])
        set_session(conn, sid, status="done", analyzed_bytes=end, candidates=n, error="")
        log(f"session {sid}: {n} candidate(s)")
        return "done"
    except Exception as e:  # noqa: BLE001 - analysis must never raise into a hook
        set_session(conn, sid, status="failed", error=clip(f"{type(e).__name__}: {e}", 400))
        log(f"session {sid} failed: {e}")
        return "failed"


def cmd_analyze(args) -> int:
    if os.environ.get(ANALYZER_ENV):
        return 0
    conn = connect()
    status = analyze_session(conn, args.session, load_config())
    if args.verbose:
        print(status)
    return 0


def cmd_digest(args) -> int:
    entries, _ = read_transcript(args.transcript, 0)
    items = digest_items(entries)
    print(fit_digest(items, load_config()["max_digest_chars"]))
    return 0


# --------------------------------------------------------------------------- report

def scope_label(r) -> str:
    return "global" if r["scope"] == "global" else "project"


def route(r) -> str:
    if r["claude_md"]:
        return f"CLAUDE.md ({scope_label(r)}) + DB"
    return "DB only"


def render_item(r, old=None) -> list:
    out = [f"#{r['id']} [{r['kind']}] conf:{r['confidence']}  src:{r['source']}",
           f"   {r['text']}"]
    if r["rationale"]:
        out.append(f"   Why: {r['rationale']}")
    if r["evidence"]:
        out.append(f"   Evidence: \"{r['evidence']}\"")
    if old is not None:
        out.append(f"   Replaces #{old['id']} ({old['status']}): {clip(old['text'], 120)}")
    out.append(f"   -> {route(r)}")
    return out


def cmd_report(args) -> int:
    conn = connect(create=False)
    if conn is None:
        print("No learnings database yet. It is created after the first analysed session.")
        return 0
    proj = resolve_project(args.cwd)
    pid = find_project_id(conn, proj)
    if args.all:
        rows = conn.execute("SELECT l.*, p.name AS pname FROM learnings l LEFT JOIN projects p ON p.id=l.project_id "
                            "WHERE l.status='pending'").fetchall()
        title = "all projects"
    else:
        rows = conn.execute("SELECT l.*, p.name AS pname FROM learnings l LEFT JOIN projects p ON p.id=l.project_id "
                            "WHERE l.status='pending' AND (l.scope='global' OR l.project_id IS ?)", (pid,)).fetchall()
        title = proj["name"]
    rows.sort(key=lambda r: (-CONF_RANK.get(r["confidence"], 2), r["created_at"]))
    normal = [r for r in rows if not r["supersedes_id"]]
    conflicts = [r for r in rows if r["supersedes_id"]]
    n_proj = sum(1 for r in rows if r["scope"] == "project")
    n_glob = len(rows) - n_proj
    sess = conn.execute("SELECT status, COUNT(*) AS n FROM sessions GROUP BY status").fetchall()
    sc = {r["status"]: r["n"] for r in sess}
    print(f"# Learning report - {title} ({datetime.now().strftime('%Y-%m-%d')})")
    print(f"Summary: {len(rows)} pending ({n_proj} project, {n_glob} global) | "
          f"sessions: {sc.get('done', 0)} analysed, {sc.get('queued', 0) + sc.get('analyzing', 0)} in queue, "
          f"{sc.get('failed', 0)} failed")
    if not rows:
        print("\nNothing pending.")
    projects = sorted({r["pname"] for r in normal if r["scope"] == "project"}) if args.all else [None]
    for pname in projects:
        items = [r for r in normal if r["scope"] == "project" and (pname is None or r["pname"] == pname)]
        if items:
            print(f"\n## PROJECT{': ' + pname if pname else ''} ({len(items)})")
            for r in items:
                print("\n".join(render_item(r)))
    glob = [r for r in normal if r["scope"] == "global"]
    if glob:
        print(f"\n## GLOBAL ({len(glob)})")
        for r in glob:
            print("\n".join(render_item(r)))
    if conflicts:
        print(f"\n## CONFLICTS / DUPLICATES ({len(conflicts)})")
        for r in conflicts:
            old = conn.execute("SELECT * FROM learnings WHERE id=?", (r["supersedes_id"],)).fetchone()
            print("\n".join(render_item(r, old)))
    deferred = conn.execute("SELECT COUNT(*) AS n FROM learnings WHERE status='deferred' AND "
                            "(scope='global' OR project_id IS ?)", (pid,)).fetchone()["n"]
    other = 0
    if not args.all:
        other = conn.execute("SELECT COUNT(*) AS n FROM learnings WHERE status='pending' AND scope='project' "
                             "AND project_id IS NOT ?", (pid,)).fetchone()["n"]
    if deferred or other:
        print(f"\nAlso: {deferred} deferred here" + (f", {other} pending in other projects (/learn-review all)" if other else ""))
    if rows:
        print("\nActions: approve 1,2 | approve all | edit 6 \"new text\" | reject 3 | scope 4=global | "
              "defer 5 | md 4 | nomd 4")
    return 0


# --------------------------------------------------------------------------- act / add / list

def parse_ids(spec: str, conn, pid, all_projects: bool, statuses: tuple) -> list:
    if spec.strip().lower() == "all":
        q = f"SELECT id FROM learnings WHERE status IN ({','.join('?' * len(statuses))})"
        params = list(statuses)
        if not all_projects:
            q += " AND (scope='global' OR project_id IS ?)"
            params.append(pid)
        return [r["id"] for r in conn.execute(q, params)]
    ids = []
    for tok in re.split(r"[,\s]+", spec.strip()):
        if tok:
            ids.append(int(tok.lstrip("#")))
    return ids


def cmd_act(args) -> int:
    conn = connect()
    proj = resolve_project(args.cwd)
    pid = find_project_id(conn, proj)
    act = args.action
    try:
        ids = parse_ids(args.ids, conn, pid, args.all, ("pending", "deferred"))
    except ValueError:
        print(f"ERROR: bad id list {args.ids!r}")
        return 2
    rc = 0
    for lid in ids:
        r = conn.execute("SELECT * FROM learnings WHERE id=?", (lid,)).fetchone()
        if not r:
            print(f"#{lid}: not found")
            rc = 1
            continue
        if act in ("md", "nomd", "scope", "edit") and r["status"] not in ("pending", "deferred", "approved"):
            print(f"#{lid}: is {r['status']}, nothing to do")
            rc = 1
            continue
        if act in ("approve", "reject", "defer") and r["status"] not in ("pending", "deferred"):
            print(f"#{lid}: already {r['status']}")
            continue
        if act == "forget" and r["status"] != "approved":
            print(f"#{lid}: is {r['status']}, only approved learnings can be forgotten (use reject for pending)")
            rc = 1
            continue
        t = now()
        if act == "approve":
            conn.execute("UPDATE learnings SET status='approved', reviewed_at=? WHERE id=?", (t, lid))
            if r["supersedes_id"]:
                conn.execute("UPDATE learnings SET status='superseded', reviewed_at=? WHERE id=? "
                             "AND status IN ('approved','pending','deferred')", (t, r["supersedes_id"]))
            print(f"#{lid}: approved" + (f" (replaces #{r['supersedes_id']})" if r["supersedes_id"] else ""))
        elif act in ("reject", "forget"):
            conn.execute("UPDATE learnings SET status='rejected', reviewed_at=? WHERE id=?", (t, lid))
            print(f"#{lid}: {'rejected' if act == 'reject' else 'forgotten'}")
        elif act == "defer":
            conn.execute("UPDATE learnings SET status='deferred', reviewed_at=? WHERE id=?", (t, lid))
            print(f"#{lid}: deferred")
        elif act in ("md", "nomd"):
            conn.execute("UPDATE learnings SET claude_md=? WHERE id=?", (1 if act == "md" else 0, lid))
            print(f"#{lid}: {'will go to CLAUDE.md' if act == 'md' else 'DB only'}")
        elif act == "edit":
            if r["claude_md_applied"]:
                print(f"#{lid}: already written to CLAUDE.md; forget it and add a new one instead")
                rc = 1
                continue
            text = one_line(args.text or "")
            if len(text) < 8:
                print(f"#{lid}: --text required")
                rc = 1
                continue
            try:
                conn.execute("UPDATE learnings SET text=?, fingerprint=? WHERE id=?",
                             (clip(text, 400), fingerprint(text), lid))
                print(f"#{lid}: text updated")
            except sqlite3.IntegrityError:
                print(f"#{lid}: same text already stored in this scope")
                rc = 1
        elif act == "scope":
            to = args.to
            if to not in ("global", "project"):
                print(f"#{lid}: --to global|project required")
                rc = 1
                continue
            if to == r["scope"]:
                print(f"#{lid}: already {to}")
                continue
            new_pid = None if to == "global" else upsert_project(conn, proj)
            try:
                conn.execute("UPDATE learnings SET scope=?, project_id=? WHERE id=?", (to, new_pid, lid))
                print(f"#{lid}: scope -> {to}")
            except sqlite3.IntegrityError:
                print(f"#{lid}: an identical learning already exists in {to}")
                rc = 1
        conn.commit()
    return rc


def cmd_add(args) -> int:
    conn = connect()
    proj = resolve_project(args.cwd)
    pid = upsert_project(conn, proj) if args.scope == "project" else None
    lid, new = add_learning(conn, scope=args.scope, pid=pid, kind=args.kind, text=args.text,
                            rationale=args.rationale or "", source="manual", confidence="high",
                            status="approved", claude_md=args.md)
    print(f"#{lid}: {'stored (approved)' if new else 'already stored'}")
    return 0


def cmd_list(args) -> int:
    conn = connect(create=False)
    if conn is None:
        print("No learnings database yet.")
        return 0
    proj = resolve_project(args.cwd)
    pid = find_project_id(conn, proj)
    q = ("SELECT l.*, p.name AS pname FROM learnings l LEFT JOIN projects p ON p.id=l.project_id WHERE 1=1")
    params: list = []
    if args.status != "any":
        q += " AND l.status=?"
        params.append(args.status)
    if not args.all:
        q += " AND (l.scope='global' OR l.project_id IS ?)"
        params.append(pid)
    q += " ORDER BY l.scope DESC, l.id"
    rows = conn.execute(q, params).fetchall()
    for r in rows:
        where = "global" if r["scope"] == "global" else f"project:{r['pname']}"
        md = " [CLAUDE.md]" if r["claude_md_applied"] else ""
        print(f"#{r['id']} [{where}/{r['kind']}/{r['status']}]{md} {r['text']}")
    print(f"({len(rows)} {args.status} learning(s))")
    return 0


# --------------------------------------------------------------------------- CLAUDE.md managed block

BULLET_RE = re.compile(r"^- (.*?)\s*<!-- L(\d+) -->\s*$")
BLOCK_RE = re.compile(r"<!-- learnings:start[^\n]*-->\n(.*?)\n?<!-- learnings:end -->\n?", re.S)


def rewrite_block(content: str, add: list, remove: set) -> str:
    nl = "\r\n" if "\r\n" in content else "\n"
    text = content.replace("\r\n", "\n")
    m = BLOCK_RE.search(text)
    body = m.group(1).split("\n") if m else []
    kept, present = [], set()
    for ln in body:
        mm = BULLET_RE.match(ln)
        if mm:
            lid = int(mm.group(2))
            if lid in remove:
                continue
            present.add(lid)
        kept.append(ln)
    for lid, t in add:
        if lid not in present:
            kept.append(f"- {one_line(t)} <!-- L{lid} -->")
            present.add(lid)
    has_bullets = any(BULLET_RE.match(l) for l in kept)
    if has_bullets:
        if not any(l.strip() == MD_HEADING for l in kept):
            kept.insert(0, MD_HEADING)
        block = f"{MD_START}\n" + "\n".join(kept) + f"\n{MD_END}\n"
    else:
        block = ""
    if m:
        new = text[:m.start()] + block + text[m.end():]
        if not block:
            new = re.sub(r"\n{3,}", "\n\n", new).rstrip("\n") + ("\n" if new.strip() else "")
    elif block:
        new = (text.rstrip("\n") + "\n\n" + block) if text.strip() else block
    else:
        new = text
    return new.replace("\n", nl)


def file_for(r) -> str:
    if r["scope"] == "global":
        return str(global_md_path())
    root = r["root"] if "root" in r.keys() else ""
    return str(Path(root) / "CLAUDE.md") if root else ""


def compute_md_ops(conn, pid) -> dict:
    """{file: {'add': [(id,text)], 'remove': {id}}} for rows whose CLAUDE.md state is out of date."""
    rows = conn.execute(
        "SELECT l.*, p.root AS root FROM learnings l LEFT JOIN projects p ON p.id=l.project_id "
        "WHERE l.claude_md_applied=1 OR (l.status='approved' AND l.claude_md=1 AND "
        "(l.scope='global' OR l.project_id IS ?))", (pid,)).fetchall()
    ops: dict = {}

    def slot(f):
        return ops.setdefault(f, {"add": [], "remove": set()})
    for r in rows:
        active = r["status"] == "approved" and r["claude_md"] == 1
        want = file_for(r) if active else ""
        if r["claude_md_applied"] and (not active or want != r["applied_file"]):
            slot(r["applied_file"])["remove"].add(r["id"])
        if active and (not r["claude_md_applied"] or want != r["applied_file"]):
            if not want:
                print(f"WARNING: #{r['id']} has no known project root; skipped")
                continue
            if r["scope"] == "global" or r["project_id"] == pid:
                slot(want)["add"].append((r["id"], r["text"]))
    return {f: o for f, o in ops.items() if f and (o["add"] or o["remove"])}


def read_file(path: str) -> str:
    try:
        return Path(path).read_bytes().decode("utf-8")
    except OSError:
        return ""


def cmd_claude_md(args) -> int:
    conn = connect(create=False)
    if conn is None:
        print("NOTHING TO DO")
        return 0
    proj = resolve_project(args.cwd)
    pid = find_project_id(conn, proj)
    ops = compute_md_ops(conn, pid)
    if not ops:
        print("NOTHING TO DO")
        return 0
    for path, o in ops.items():
        old = read_file(path)
        new = rewrite_block(old, o["add"], o["remove"])
        if args.mode == "plan":
            label = path + ("" if Path(path).exists() else "  (new file)")
            diff = difflib.unified_diff(old.splitlines(), new.splitlines(), label, label, lineterm="", n=1)
            print("\n".join(diff) or f"(no textual change in {path})")
            print()
            continue
        if old == new:
            continue
        backups = home_dir() / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        if Path(path).exists():
            safe = re.sub(r"[^\w.\-]+", "_", path)[-80:]
            (backups / f"{safe}.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak").write_bytes(Path(path).read_bytes())
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(path + ".learn-tmp")
        tmp.write_bytes(new.encode("utf-8"))
        os.replace(tmp, path)
        for lid, _ in o["add"]:
            conn.execute("UPDATE learnings SET claude_md_applied=1, applied_file=? WHERE id=?", (path, lid))
        for lid in o["remove"]:
            conn.execute("UPDATE learnings SET claude_md_applied=0, applied_file='' WHERE id=?", (lid,))
        conn.commit()
        print(f"updated {path}: +{len(o['add'])} -{len(o['remove'])}")
    return 0


# --------------------------------------------------------------------------- export / import (markdown)

EXPORT_VERSION = 1
EXPORT_ORDER = ("approved", "pending", "deferred", "superseded", "rejected")
EXPORT_MARK = "learnings_export:"


def iso_utc(t) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if t else ""


def parse_iso(s: str):
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def slugify(name: str, key: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "project"
    return f"{base}-{hashlib.sha1(key.encode('utf-8')).hexdigest()[:6]}"


def render_export(scope: str, proj, rows: list) -> str:
    title = "global" if scope == "global" else proj["name"]
    head = ["---", f"learnings_export: {EXPORT_VERSION}", f"scope: {scope}"]
    if proj is not None:
        head += [f"project_key: {proj['key']}", f"project_name: {proj['name']}", f"project_root: {proj['root']}"]
    head += [f"count: {len(rows)}", "---", "",
             f"# Learnings - {title}", "",
             "Exported from the Claude Code learnings database. Each `### #<id>` block is one learning; "
             "the `- key: value` lines under it are its fields (one line each, English). "
             "Restore into a database with `bash ~/.claude/skills/learning-memory/scripts/run.sh import <this folder>`. "
             "Only `status: approved` entries are active in sessions."]
    out = list(head)
    for status in EXPORT_ORDER:
        group = [r for r in rows if r["status"] == status]
        if not group:
            continue
        out += ["", f"## {status.capitalize()} ({len(group)})"]
        for r in group:
            out += ["", f"### #{r['id']}",
                    f"- kind: {r['kind']}", f"- status: {r['status']}", f"- confidence: {r['confidence']}",
                    f"- source: {r['source']}", f"- claude_md: {'yes' if r['claude_md'] else 'no'}",
                    f"- applied: {'yes' if r['claude_md_applied'] else 'no'}",
                    f"- supersedes: {r['supersedes_id'] or ''}",
                    f"- created: {iso_utc(r['created_at'])}", f"- reviewed: {iso_utc(r['reviewed_at'])}",
                    f"- session: {r['session_id']}",
                    f"- text: {r['text']}", f"- rationale: {r['rationale']}", f"- evidence: {r['evidence']}"]
    return "\n".join(out) + "\n"


def cmd_export(args) -> int:
    conn = connect(create=False)
    out_dir = Path(args.out).expanduser() if args.out else home_dir() / "export"
    if conn is None:
        print(f"No learnings database at {db_path()}; nothing to export.")
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "projects").mkdir(exist_ok=True)
    written, index = set(), []

    def emit_file(rel: str, text: str, label: str, n: int):
        path = out_dir / rel
        if not path.exists() or path.read_bytes() != text.encode("utf-8"):
            path.write_bytes(text.encode("utf-8"))
        written.add(path.resolve())
        index.append((rel, label, n))

    rows = conn.execute("SELECT * FROM learnings WHERE scope='global' ORDER BY id").fetchall()
    emit_file("global.md", render_export("global", None, rows), "global", len(rows))
    for proj in conn.execute("SELECT * FROM projects ORDER BY name, key").fetchall():
        rows = conn.execute("SELECT * FROM learnings WHERE project_id=? ORDER BY id", (proj["id"],)).fetchall()
        if rows:
            emit_file(f"projects/{slugify(proj['name'], proj['key'])}.md", render_export("project", proj, rows),
                      f"project: {proj['name']} ({proj['key']})", len(rows))
    for old in (out_dir / "projects").glob("*.md"):  # stale exports of deleted projects
        if old.resolve() not in written and EXPORT_MARK in old.read_text(encoding="utf-8", errors="replace")[:200]:
            old.unlink()
    lines = ["# Learnings export", "",
             f"Exported {iso_utc(now())} from `{db_path()}`.", "",
             "| File | Content | Learnings |", "|---|---|---|"]
    lines += [f"| `{rel}` | {label} | {n} |" for rel, label, n in index]
    lines += ["", "## How to use", "",
              "- Read `global.md` (applies to every project) and the file of the project you work on.",
              "- Entries with `status: approved` are the active ones; `rejected` ones are kept so they are never proposed again.",
              "- Restore into an empty database: `bash ~/.claude/skills/learning-memory/scripts/run.sh import <this folder>` "
              "(`--dry-run` to check first). Re-importing is safe: identical learnings are skipped.",
              "- Do not edit ids; other entries reference them (`supersedes`). You may edit `text`, `status`, `claude_md`.", ""]
    (out_dir / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")
    total = sum(n for _, _, n in index)
    print(f"exported {total} learning(s) into {len(index)} file(s): {out_dir}")
    for rel, label, n in index:
        print(f"  {rel}  ({n})")
    return 0


def parse_export_file(path: Path):
    """Returns (meta, entries, errors). entries: list of dicts with '_line'."""
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, [], []
    meta, i = {}, 1
    while i < len(lines) and lines[i].strip() != "---":
        k, _, v = lines[i].partition(":")
        meta[k.strip()] = v.strip()
        i += 1
    if "learnings_export" not in meta:
        return None, [], []
    entries, errors, cur = [], [], None
    for n, ln in enumerate(lines[i + 1:], start=i + 2):
        m = re.match(r"^###\s+#(\d+)\s*$", ln)
        if m:
            cur = {"id": int(m.group(1)), "_line": n}
            entries.append(cur)
            continue
        if cur is not None and ln.startswith("- "):
            k, sep, v = ln[2:].partition(":")
            if sep:
                cur[k.strip()] = v.strip()
        elif ln.startswith("## ") or ln.startswith("# "):
            cur = None
    return meta, entries, errors


def validate_entry(e: dict, scope: str) -> str:
    for key, allowed in (("kind", KINDS), ("status", ("pending", "approved", "rejected", "deferred", "superseded")),
                         ("confidence", CONFS), ("source", SOURCES)):
        if e.get(key) not in allowed:
            return f"bad {key} {e.get(key)!r}"
    if len(one_line(e.get("text", ""))) < 2:
        return "missing text"
    if e.get("claude_md", "no") not in ("yes", "no"):
        return "claude_md must be yes|no"
    return ""


def cmd_import(args) -> int:
    src = Path(args.path).expanduser()
    files = [src] if src.is_file() else sorted(src.rglob("*.md")) if src.is_dir() else []
    if not files:
        print(f"ERROR: nothing to import at {src}")
        return 2
    conn = connect()
    t = now()
    stats = {"added": 0, "duplicate": 0, "invalid": 0}
    idmap: dict = {}          # exported id -> db id (global ids are unique across files)
    pending_sup: list = []    # (db id, exported superseded id)
    seen_files = 0
    try:
        for f in files:
            meta, entries, _ = parse_export_file(f)
            if meta is None:
                continue
            seen_files += 1
            scope = meta.get("scope", "")
            if scope not in ("global", "project"):
                print(f"{f.name}: bad scope {scope!r}; file skipped")
                stats["invalid"] += len(entries)
                continue
            pid = None
            if scope == "project":
                key = meta.get("project_key", "")
                if not key:
                    print(f"{f.name}: project_key missing; file skipped")
                    stats["invalid"] += len(entries)
                    continue
                conn.execute("INSERT INTO projects(key,name,root,created_at,last_seen) VALUES(?,?,?,?,?) "
                             "ON CONFLICT(key) DO UPDATE SET name=excluded.name, "
                             "root=CASE WHEN excluded.root<>'' THEN excluded.root ELSE projects.root END",
                             (key, meta.get("project_name") or key, meta.get("project_root", ""), t, t))
                pid = conn.execute("SELECT id FROM projects WHERE key=?", (key,)).fetchone()["id"]
            for e in entries:
                err = validate_entry(e, scope)
                if err:
                    print(f"{f.name}:{e['_line']}: #{e['id']} {err}; skipped")
                    stats["invalid"] += 1
                    continue
                text = one_line(e["text"])
                fp = fingerprint(text)
                dup = conn.execute("SELECT id FROM learnings WHERE scope=? AND project_id IS ? AND fingerprint=?",
                                   (scope, pid, fp)).fetchone()
                if dup:
                    idmap[e["id"]] = dup["id"]
                    stats["duplicate"] += 1
                    continue
                keep_applied = args.keep_applied and e.get("applied") == "yes"
                new_id = e["id"] if not conn.execute("SELECT 1 FROM learnings WHERE id=?", (e["id"],)).fetchone() else None
                cols = ["scope", "project_id", "kind", "text", "rationale", "evidence", "source", "confidence",
                        "status", "claude_md", "claude_md_applied", "fingerprint", "session_id", "created_at",
                        "reviewed_at"]
                vals = [scope, pid, e["kind"], clip(text, 400), clip(one_line(e.get("rationale", "")), 400),
                        clip(one_line(e.get("evidence", "")), 400), e["source"], e["confidence"], e["status"],
                        1 if e.get("claude_md") == "yes" else 0, 1 if keep_applied else 0, fp,
                        e.get("session", ""), parse_iso(e.get("created", "")) or t, parse_iso(e.get("reviewed", ""))]
                if new_id is not None:
                    cols.insert(0, "id")
                    vals.insert(0, new_id)
                cur = conn.execute(f"INSERT INTO learnings({','.join(cols)}) VALUES({','.join('?' * len(cols))})", vals)
                idmap[e["id"]] = cur.lastrowid
                if e.get("supersedes", "").isdigit():
                    pending_sup.append((cur.lastrowid, int(e["supersedes"])))
                stats["added"] += 1
        for new_id, old_exported in pending_sup:
            if old_exported in idmap:
                conn.execute("UPDATE learnings SET supersedes_id=? WHERE id=?", (idmap[old_exported], new_id))
        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    if not seen_files:
        print(f"ERROR: no learnings export files (front matter '{EXPORT_MARK}') found in {src}")
        return 2
    print(f"{'would import' if args.dry_run else 'imported'}: {stats['added']} added, "
          f"{stats['duplicate']} already present, {stats['invalid']} invalid, from {seen_files} file(s)")
    if stats["added"] and not args.dry_run and args.keep_applied is False:
        print("Note: CLAUDE.md state is not restored; run /learn-review (claude-md plan) to re-sync CLAUDE.md files.")
    return 1 if stats["invalid"] else 0


# --------------------------------------------------------------------------- web UI (read-only)

UI_FILE = SKILL_DIR / "web" / "index.html"
UI_BOOT = '<script id="boot" type="application/json">{"mode":"static","data":null}</script>'
LOCAL_HOSTS = ("127.0.0.1", "localhost", "[::1]")


def collect_ui_data() -> dict:
    """Everything the web UI shows, read-only. Works without a database."""
    data = {"db": str(db_path()), "generated_at": now(), "db_missing": False, "projects": [],
            "learnings": [], "sessions": {"counts": {}, "recent": []}}
    conn = connect(create=False, query_only=True)
    if conn is None:
        data["db_missing"] = True
        return data
    try:
        _fill_ui_data(conn, data)
    finally:  # a long-running server must not accumulate connections
        conn.close()
        if conn in _CONNS:
            _CONNS.remove(conn)
    return data


def _fill_ui_data(conn, data: dict) -> None:
    data["projects"] = [dict(id=r["id"], key=r["key"], name=r["name"], root=r["root"])
                        for r in conn.execute("SELECT * FROM projects ORDER BY name")]
    for r in conn.execute("SELECT l.*, p.name AS pname, p.key AS pkey FROM learnings l "
                          "LEFT JOIN projects p ON p.id=l.project_id ORDER BY l.id"):
        data["learnings"].append({
            "id": r["id"], "scope": r["scope"], "project": r["pname"], "project_key": r["pkey"],
            "kind": r["kind"], "status": r["status"], "confidence": r["confidence"], "source": r["source"],
            "text": r["text"], "rationale": r["rationale"], "evidence": r["evidence"],
            "claude_md": bool(r["claude_md"]), "applied": bool(r["claude_md_applied"]),
            "applied_file": r["applied_file"], "supersedes_id": r["supersedes_id"],
            "session_id": r["session_id"], "created_at": r["created_at"], "reviewed_at": r["reviewed_at"]})
    data["sessions"]["counts"] = {r["status"]: r["n"] for r in conn.execute(
        "SELECT status, COUNT(*) AS n FROM sessions GROUP BY status")}
    data["sessions"]["recent"] = [
        {"session_id": r["session_id"], "project": r["pname"], "status": r["status"], "attempts": r["attempts"],
         "candidates": r["candidates"], "error": r["error"], "updated_at": r["updated_at"]}
        for r in conn.execute("SELECT s.*, p.name AS pname FROM sessions s LEFT JOIN projects p ON p.id=s.project_id "
                              "ORDER BY s.updated_at DESC LIMIT 25")]


def _json_for_script(obj) -> str:
    return json.dumps(obj).replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def render_ui_html(mode: str, data=None) -> str:
    html = UI_FILE.read_text(encoding="utf-8")
    if UI_BOOT not in html:
        raise RuntimeError("web/index.html is missing its boot placeholder")
    boot = f'<script id="boot" type="application/json">{_json_for_script({"mode": mode, "data": data})}</script>'
    return html.replace(UI_BOOT, boot, 1)


def host_only(header) -> str:
    h = (header or "").strip()
    if h.startswith("["):
        return h.split("]")[0] + "]"
    return h.rsplit(":", 1)[0] if ":" in h else h


def make_ui_server(port: int):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        server_version = "learning-memory-ui"

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; "
                             "style-src 'unsafe-inline'; connect-src 'self'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):  # noqa: N802
            host = host_only(self.headers.get("Host"))
            if host not in LOCAL_HOSTS:  # blocks DNS-rebinding reads of local data
                return self._send(403, b"forbidden", "text/plain; charset=utf-8")
            path = self.path.split("?", 1)[0]
            if path == "/":
                return self._send(200, render_ui_html("live").encode("utf-8"), "text/html; charset=utf-8")
            if path == "/api/data":
                return self._send(200, json.dumps(collect_ui_data()).encode("utf-8"), "application/json")
            return self._send(404, b"not found", "text/plain; charset=utf-8")

        def _no(self):
            self._send(405, b"read-only", "text/plain; charset=utf-8")
        do_POST = do_PUT = do_DELETE = do_PATCH = _no

        def log_message(self, *a):  # keep the console quiet
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def cmd_ui(args) -> int:
    if args.out:
        out = Path(args.out).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_ui_html("static", collect_ui_data()), encoding="utf-8")
        print(f"snapshot written: {out}")
        return 0
    server = None
    for port in range(args.port, args.port + 20):
        try:
            server = make_ui_server(port)
            break
        except OSError:
            continue
    if server is None:
        print(f"ERROR: no free port in {args.port}-{args.port + 19}")
        return 1
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Learning memory UI (read-only): {url}   (Ctrl+C to stop)", flush=True)
    if args.open:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


# --------------------------------------------------------------------------- setup

def hook_specs() -> dict:
    base = 'bash "$HOME/.claude/skills/learning-memory/scripts/run.sh"'
    return {"SessionStart": (f"{base} load --event SessionStart", 15),
            "SubagentStart": (f"{base} load --event SubagentStart", 15),
            "SessionEnd": (f"{base} capture", 10)}


def merge_hooks(settings: dict, remove_only: bool = False) -> dict:
    hooks = settings.setdefault("hooks", {})
    for event, (cmd, timeout) in hook_specs().items():
        groups = hooks.get(event, [])
        cleaned = []
        for g in groups:
            inner = [h for h in g.get("hooks", []) if HOOK_MARK not in str(h.get("command", ""))]
            if inner:
                cleaned.append({**g, "hooks": inner})
        if not remove_only:
            cleaned.append({"hooks": [{"type": "command", "command": cmd, "timeout": timeout}]})
        if cleaned:
            hooks[event] = cleaned
        else:
            hooks.pop(event, None)
    if not hooks:
        settings.pop("hooks", None)
    return settings


def cmd_hooks(args) -> int:
    p = settings_path()
    try:
        raw = p.read_text(encoding="utf-8") if p.exists() else "{}"
        settings = json.loads(raw or "{}")
    except ValueError as e:
        print(f"ERROR: {p} is not valid JSON ({e}); nothing changed")
        return 1
    new = merge_hooks(json.loads(json.dumps(settings)), remove_only=args.remove)
    text = json.dumps(new, indent=2, ensure_ascii=False) + "\n"
    if args.dry_run:
        print(json.dumps(new.get("hooks", {}), indent=2))
        return 0
    if new == settings:
        print(f"hooks already {'absent' if args.remove else 'registered'} in {p}")
        return 0
    if p.exists():
        backups = home_dir() / "backups"
        backups.mkdir(parents=True, exist_ok=True)
        (backups / f"settings.json.{datetime.now().strftime('%Y%m%d-%H%M%S')}.bak").write_text(raw, encoding="utf-8")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    print(f"hooks {'removed from' if args.remove else 'registered in'} {p}")
    return 0


def cmd_init(args) -> int:
    connect()
    print(f"database ready: {db_path()}")
    return 0


def cmd_status(args) -> int:
    conn = connect(create=False)
    print(f"database: {db_path()} ({'present' if conn else 'missing'})")
    if conn is None:
        return 0
    for r in conn.execute("SELECT status, COUNT(*) AS n FROM learnings GROUP BY status"):
        print(f"  learnings {r['status']}: {r['n']}")
    for r in conn.execute("SELECT status, COUNT(*) AS n FROM sessions GROUP BY status"):
        print(f"  sessions {r['status']}: {r['n']}")
    for r in conn.execute("SELECT session_id, error FROM sessions WHERE status='failed' "
                          "ORDER BY updated_at DESC LIMIT 3"):
        print(f"  failed {r['session_id'][:8]}: {r['error']}")
    cfg = load_config()
    print(f"model: {cfg['model']} | auto_analyze: {cfg['auto_analyze']}")
    return 0


# --------------------------------------------------------------------------- main

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="learn.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    cwd = os.getcwd()

    p = sp.add_parser("load")
    p.add_argument("--event", choices=("SessionStart", "SubagentStart"))
    p.set_defaults(fn=cmd_load, hook=True)
    p = sp.add_parser("capture")
    p.set_defaults(fn=cmd_capture, hook=True)
    p = sp.add_parser("sweep")
    p.add_argument("--cwd", default=cwd)
    p.add_argument("--transcripts-dir", default="")
    p.add_argument("--current", default="")
    p.set_defaults(fn=cmd_sweep, hook=True)
    p = sp.add_parser("analyze")
    p.add_argument("--session", required=True)
    p.add_argument("--verbose", action="store_true")
    p.set_defaults(fn=cmd_analyze, hook=True)
    p = sp.add_parser("digest")
    p.add_argument("transcript")
    p.set_defaults(fn=cmd_digest)

    p = sp.add_parser("report")
    p.add_argument("--cwd", default=cwd)
    p.add_argument("--all", action="store_true")
    p.set_defaults(fn=cmd_report)
    p = sp.add_parser("act")
    p.add_argument("action", choices=("approve", "reject", "defer", "forget", "edit", "scope", "md", "nomd"))
    p.add_argument("ids")
    p.add_argument("--text")
    p.add_argument("--to")
    p.add_argument("--cwd", default=cwd)
    p.add_argument("--all", action="store_true")
    p.set_defaults(fn=cmd_act)
    p = sp.add_parser("add")
    p.add_argument("--scope", choices=("global", "project"), required=True)
    p.add_argument("--kind", choices=KINDS, default="rule")
    p.add_argument("--text", required=True)
    p.add_argument("--rationale")
    p.add_argument("--md", action="store_true")
    p.add_argument("--cwd", default=cwd)
    p.set_defaults(fn=cmd_add)
    p = sp.add_parser("list")
    p.add_argument("--status", default="approved",
                   choices=("approved", "pending", "deferred", "rejected", "superseded", "any"))
    p.add_argument("--all", action="store_true")
    p.add_argument("--cwd", default=cwd)
    p.set_defaults(fn=cmd_list)
    p = sp.add_parser("claude-md")
    p.add_argument("mode", choices=("plan", "apply"))
    p.add_argument("--cwd", default=cwd)
    p.set_defaults(fn=cmd_claude_md)

    p = sp.add_parser("export")
    p.add_argument("--out", help="output folder (default ~/.claude/learnings/export)")
    p.set_defaults(fn=cmd_export)
    p = sp.add_parser("import")
    p.add_argument("path", help="export folder or a single exported .md file")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--keep-applied", action="store_true",
                   help="keep 'applied to CLAUDE.md' flags (only when the CLAUDE.md files are restored too)")
    p.set_defaults(fn=cmd_import)

    p = sp.add_parser("ui")
    p.add_argument("--out", help="write a self-contained HTML snapshot instead of serving")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--open", action="store_true", help="open the browser")
    p.set_defaults(fn=cmd_ui)

    sp.add_parser("init").set_defaults(fn=cmd_init)
    sp.add_parser("status").set_defaults(fn=cmd_status)
    for name, rm in (("install-hooks", False), ("uninstall-hooks", True)):
        p = sp.add_parser(name)
        p.add_argument("--dry-run", action="store_true")
        p.set_defaults(fn=cmd_hooks, remove=rm)
    return ap


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    opened = len(_CONNS)
    try:
        if getattr(args, "hook", False):
            try:
                args.fn(args)
            except Exception as e:  # noqa: BLE001 - a hook must never break the session
                log(f"{args.cmd} crashed: {type(e).__name__}: {e}")
            return 0
        return args.fn(args)
    finally:
        close_all(opened)


if __name__ == "__main__":
    sys.exit(main())
