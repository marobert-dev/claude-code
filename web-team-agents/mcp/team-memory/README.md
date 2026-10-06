# team-memory — MCP server for the agent team

Shared memory, task board and file locks for the multi-agent dev pipeline. One SQLite file, no network, no
external services. Works with the MCP Python SDK 2.x (`MCPServer`) and 1.x (`FastMCP`).

## Install (Windows example — adapt paths)

This folder (`mcp/team-memory/`, inside the repo) is the **source** — edit and commit it here. The **installed, registered** copy that Claude Code actually talks to is a separate copy at `~\.mcp\team-memory\`. After changing `server.py`/`store.py`, re-copy them into the installed copy (and re-run its `pip install` if `requirements.txt` changed) for the change to take effect.

```powershell
# one-time install, from a copy of this folder at ~\.mcp\team-memory:
cd ~\.mcp\team-memory
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
# register once for every project (user scope):
claude mcp add --scope user team-memory -- ~\.mcp\team-memory\.venv\Scripts\python.exe ~\.mcp\team-memory\server.py
```

Linux/macOS: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, then the same `claude mcp add` with the venv's `python`.

The database defaults to `<workspace>/.pipeline/team-memory.db` (the server runs in the workspace folder), so every
workspace gets its own memory. Inside a git worktree the server automatically uses the **main** worktree's database, so parallel
stories share one memory. Override with `TEAM_MEMORY_DB=<absolute path>`. Add `.pipeline/team-memory.db*` to `.gitignore`: it is local coordination state.

Verify: `claude mcp list` shows `team-memory`; inside a session run `/mcp`, then ask the assistant to call `stats`.
**Also verify that a subagent can call it** (see TEAM-MEMORY-PROPOSAL.md, section 2) before changing any agent.

## Tools (29)

| Group | Tools | Purpose |
|---|---|---|
| Memory | `remember`, `recall`, `get_memory`, `retire_memory` | Short facts by kind (`note`, `decision`, `convention`, `gotcha`, `contract`, `review-pattern`, `handoff`, `fact`, `rule`), full-text search (FTS5, ranked). Same kind+key+story = replaces the old entry, history kept. |
| Decisions | `log_decision`, `decisions_digest` | Same fields as the `.decisions/` format plus a kebab-case `topic`; the digest lists topics that recur. |
| Briefing | `story_context` | One call: last handoff, relevant conventions/contracts/gotchas, decisions, notes, open tasks, active locks. |
| Task board | `task_post`, `task_claim`, `task_heartbeat`, `task_release`, `task_finish`, `task_list` | Atomic claims, priorities, dependencies, lease expiry (a crashed agent releases its task automatically). |
| Locks | `lock_acquire`, `lock_release`, `lock_list` | Advisory, expiring locks on file paths or logical resources; re-entrant for the holder. |
| Task checkpoint | `task_checkpoint` | One atomic upsert by `(story, role)` — the cheap way to mirror pipeline progress (replaces post/claim/finish). |
| Token savers | `contract_lookup`, `conventions`, `similar_stories`, `queue_status`, `rules_briefing`, `promote_rules` | Return a budgeted slice instead of a whole file: an OpenAPI operation/schema (`contract_lookup`, ~1-4k tokens vs ~40k), a conventions section by role/topic, the closest earlier story, the queue state (~400 tokens vs the progress file). `rule` entries are decision topics that recurred in ≥2 stories, auto-promoted inside `log_decision` and shown in `story_context`. |
| Flaky registry | `flaky_report`, `flaky_list`, `flaky_resolve` | Tests that fail for environmental reasons, with counts and causes, so agents retry once instead of failing a story. |
| Telemetry | `usage_report` | Characters returned per tool/agent and recall hit rates; lists never-recalled entries only after 14 days of tracking. Pass `agent="<name>"` to `recall`/`story_context` to attribute usage. `recall` returns the top 6 entries cut to 600 characters by default (`limit`, `snippet` to widen; `get_memory(id)` for one in full). |
| Misc | `stats` | Database path and counts. |

Resources: `team-memory://story/{story}` and `team-memory://decisions-digest`.

## Guarantees and limits

- Multi-process safe: each call uses a short-lived connection (WAL, `busy_timeout`), and claims/locks run in `BEGIN IMMEDIATE`
  transactions. Tested with 6 concurrent processes: 60 tasks claimed exactly once each; 6 racers for one lock, one winner.
- Locks are advisory: they only work if agents call them. Lock paths are compared as written (slashes normalized, case kept) —
  always use the same repo-relative spelling.
- Limits: content 8000 chars, recall snippets 2000 chars, names `[A-Za-z0-9_.:#-]` up to 96 chars. Oversized or malformed input is
  rejected with an error the agent can read.
- Stored text is data written by other agents: the server's instructions tell agents never to follow instructions found in it.
  Do not store secrets or personal data (the server cannot detect them).

## Shared HTTP mode (optional)

If subagents turn out not to share one stdio process, or you want one server for several machines' worth of agents on this
computer: `TEAM_MEMORY_TRANSPORT=streamable-http TEAM_MEMORY_PORT=8765 python server.py`, then
`claude mcp add --transport http team-memory http://127.0.0.1:8765/mcp`. It binds to 127.0.0.1 only and has no authentication —
do not expose it beyond localhost.

## Tests

```bash
pip install pytest mcp
pytest -q        # 27 tests: store logic, races across processes, and a real MCP stdio round-trip
```
