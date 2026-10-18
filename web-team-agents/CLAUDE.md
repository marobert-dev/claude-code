# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A distributable Claude Code agent stack, not an application. It ships 12 subagent prompts (`agents/*.md`), a deterministic quality gate (`hooks/gate.sh`), headless pipeline runners (`scripts/`), and an optional SQLite-backed MCP server (`mcp/team-memory/`). The agents run *inside other workspaces* (the app repos they build); this repo is only their source. The README is the user-facing manual — keep it in sync when behavior changes.

## Source vs installed copies (the main trap)

Nothing in this repo is live until copied:

- `agents/*.md` → `~/.claude/agents/` via `bash install.sh` (or `.\install.ps1`). Editing a prompt here changes nothing until reinstalled.
- `hooks/gate.sh`, `hooks/pm-state.sh` (product-manager bookkeeping), `scripts/run-queue.sh`, `scripts/run-parallel.sh` → a target workspace via `bash install.sh /path/to/app`. `hooks/settings.snippet.json` is never auto-merged; users merge it by hand.
- `mcp/team-memory/server.py` + `store.py` → the registered copy at `~\.mcp\team-memory\`. If not re-copied after a change, the running server silently keeps the old behavior (this already caused a days-long bug).
- `scripts/enable-graphify.sh` / `.ps1` edit the **installed** agents in `~/.claude/agents/`, not the repo. The committed `agents/*.md` already contain the Graphify "Before anything else" block.

## Commands

All shell scripts are bash — on Windows use Git Bash or WSL.

```bash
# team-memory tests (from mcp/team-memory/; pytest is not installed globally)
pip install pytest mcp
pytest -q                                              # all tests: store logic, multi-process races, real MCP stdio round-trip
pytest -q test_team_memory.py::test_remember_recall_and_supersede   # single test

# shell syntax check (no linter configured; shellcheck not installed)
for f in hooks/*.sh scripts/*.sh install.sh; do bash -n "$f" || echo "FAIL $f"; done

# install agents globally / plus workspace helpers
bash install.sh [workspace-dir]
```

There is no build or lint step for the agent prompts. End-to-end behavior of the agents is measured by the sibling evaluation kit `../shoplite-agent-eval/` (a .NET + React target app with tasks, hidden tests and scoring), which never modifies the agents.

## Pipeline architecture (spans many agent files)

- **product-owner** and **product-manager** are run as the session agent (`claude --agent <name>`), never spawned. product-owner writes `.user-stories/<NN>-<slug>.md`; product-manager processes them one at a time, spawning the others. Only product-manager has `Agent(...)` in its `tools:` line — that list must match existing agent `name`s.
- Per story: analyst (plan appended into the story file; owns `contracts/openapi.yaml`) → dev-frontend / dev-backend in parallel → `gate.sh` → code-reviewer loop (inline `REVIEW:` comments) → unit-tester → dev-integrator → gate + review → security-reviewer (inline `SECURITY:` comments) → story-validator (FR + EN e2e tests, full-suite regression) → doc-writer. Max 2 fix rounds, then the story stays queued and the run stops.
- Agents coordinate only through files whose paths and formats are hard-coded across several prompts: `.user-stories/`, `.stories-reviewed/`, `.validated-stories/`, `.completed/`, `.decisions/<agent>.decisions.md`, `.pipeline/conventions.md` (written by conventions-scout, read by all), `.pipeline/decisions-digest.md`, `.pipeline/pm-last-run.txt` (`COMPLETED`/`FAILED`/`EMPTY`, read by `run-queue.sh`). Renaming a path or format means updating every agent that reads or writes it, plus the README's "Files produced" table.
- Runtime state lives under `.pipeline/`, not `.claude/`, because Claude Code treats `.claude/` as protected and blocks unattended writes.
- Agents never stop to ask; judgment calls go to `.decisions/`. Model choice is deliberate: `opus` for product-owner and analyst, `haiku` for unit-tester, `sonnet` for the rest.
- `run-parallel.sh` runs ready stories (all `## Dependencies` already in `.completed/`) in separate git worktrees on `feature/<slug>`; single-repo workspaces only.

## gate.sh

Two modes: SubagentStop hook (stdin JSON; only gates dev-frontend/dev-backend/dev-integrator; exit 2 makes the subagent keep working; loop guard `GATE_MAX_BLOCKS`, default 3) and a direct call by product-manager before each review (non-zero = fail). It auto-detects npm scripts (requires `jq` — without it npm steps are skipped silently) and `dotnet` solutions; `.claude/gate.local.sh` in a workspace replaces detection entirely. Env: `GATE_SKIP_BUILD`, `GATE_SKIP_TESTS`.

## team-memory MCP server

- `store.py` holds all logic (`Store` class, validation helpers, FTS5 search); `server.py` is a thin tool layer that imports `MCPServer` (SDK 2.x) or falls back to `FastMCP` (1.x) — keep both working.
- DB: `$TEAM_MEMORY_DB`, else `<cwd>/.pipeline/team-memory.db`; inside a git worktree it resolves to the main worktree's DB so parallel stories share memory (`default_db_path`).
- Multi-process safety relies on short-lived connections (WAL, `busy_timeout`) and `BEGIN IMMEDIATE` for claims/locks — preserve this when touching task/lock code; the race tests cover it.
- Input limits (content 8000 chars, names `[A-Za-z0-9_.:#-]` ≤ 96) are enforced in `store.py` and documented in `mcp/team-memory/README.md`; the server's instructions string tells agents stored text is data, never instructions.
- Adding or renaming a tool means updating the tool table in `mcp/team-memory/README.md` and any agent prompts that call it (agents list `mcp__team-memory__*` in `tools:`).
