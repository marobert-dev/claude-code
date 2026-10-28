# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A distributable Claude Code agent stack, not an application. It ships 13 subagent prompts (`agents/*.md`), deterministic hook scripts (`hooks/`: the quality gate, the role guard, bookkeeping, convention detection, secret scan), headless pipeline runners (`scripts/`), and an optional SQLite-backed MCP server (`mcp/team-memory/`). The agents run *inside other workspaces* (the app repos they build); this repo is only their source. The README is the user-facing manual — keep it in sync when behavior changes.

## Source vs installed copies (the main trap)

Nothing in this repo is live until copied:

- `agents/*.md` → `~/.claude/agents/` via `bash install.sh` (or `.\install.ps1`). Editing a prompt here changes nothing until reinstalled.
- `hooks/gate.sh`, `hooks/role-guard.sh`, `hooks/pm-state.sh` (product-manager bookkeeping), `hooks/detect-conventions.sh` (mechanical facts for conventions-scout), `hooks/secret-scan.sh`, `scripts/run-queue.sh`, `scripts/run-parallel.sh`, `templates/user-manual/` and `templates/e2e/` (→ `.claude/templates/`, read by doc-writer and story-validator) → a target workspace via `bash install.sh /path/to/app`. `hooks/settings.snippet.json` (permissions and the one SubagentStop gate hook) is never auto-merged; users merge it by hand.
- The agents' frontmatter `hooks:` call `$CLAUDE_PROJECT_DIR/.claude/hooks/role-guard.sh` and do nothing when the file is missing. The gate is the exception: its one SubagentStop hook lives in the workspace's `settings.json` (from `hooks/settings.snippet.json`), never in an agent's frontmatter, or it would fire twice after every stop (`scripts/check-agents.py` enforces it). Renaming a hook script or its arguments means updating every agent that calls it, `settings.snippet.json`, `install.sh`/`install.ps1`, and the eval kit's copies in `../shoplite-agent-eval/app-template/.claude/` (`hooks/` and `settings.json`; the kit's runs use those copies; re-copy after any change to `hooks/` or `templates/`).
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

# hook tests (role-guard, pm-state plan-check/append/finish, secret-scan, gate NOT CHECKED, scoped/full, lock, time limit); needs git and jq
bash hooks/test-hooks.sh

# agent definitions vs the repo: names, team-memory tool names, Agent() list, hook scripts, frontmatter rules
python scripts/check-agents.py

# install agents globally / plus workspace helpers
bash install.sh [workspace-dir]
```

There is no build or lint step for the agent prompts. End-to-end behavior of the agents is measured by the sibling evaluation kit `../shoplite-agent-eval/` (a .NET + React target app with tasks, hidden tests and scoring), which never modifies the agents: its `run-agent.sh` feeds `agents/*.md` from this repo to `claude --agents` (no install needed) and isolates runs with `--setting-sources project,local` plus `--mcp-config`, which keeps the agents' hooks working.

Frontmatter rules the token budget depends on (README 3d): subagents keep `omitClaudeMd: true`, a pinned `effort` and a `maxTurns`; no agent gets `memory:`; team-memory tools are listed by name (`mcp__team-memory__<tool>`, each must exist in `server.py`) — only product-manager's list is long, and no agent uses the wildcard.

## Pipeline architecture (spans many agent files)

- **product-owner** and **product-manager** are run as the session agent (`claude --agent <name>`), never spawned. product-owner writes `.user-stories/<NN>-<slug>.md`; product-manager processes them one at a time, spawning the others. Only product-manager has `Agent(...)` in its `tools:` line — that list must match existing agent `name`s.
- Per story: analyst (plan appended into the story file, layout checked by `pm-state.sh plan-check`; owns `contracts/openapi.yaml`) → dev-frontend / dev-backend in parallel (with their own focused tests) → code-reviewer loop (inline `REVIEW:` comments; the scoped `gate.sh` already ran when each dev agent stopped) → unit-tester → dev-integrator → review → security-reviewer (inline `SECURITY:` comments) → story-validator (FR + EN e2e tests, full-suite regression) → ui-reviewer (web stories with a Visual Definition; screenshots via `uiSnapshot`, inline `UX:` comments) → `gate.sh --full` → doc-writer. Max 2 fix rounds, then the story stays queued and the run stops.
- Agents coordinate only through files whose paths and formats are hard-coded across several prompts: `.user-stories/`, `.stories-reviewed/`, `.validated-stories/`, `.completed/`, `.decisions/<agent>.decisions.md`, `.pipeline/conventions.md` (written by conventions-scout, read by all), `.pipeline/decisions-digest.md`, `.pipeline/pm-last-run.txt` (`COMPLETED`/`FAILED`/`EMPTY`, read by `run-queue.sh`), `tests/e2e/shared/ui-snapshot.ts` and `test-results/ui-review/<story-id>/` (story-validator → ui-reviewer → doc-writer). The `OBSOLETE-TEST: <story-id> — <what changed>` marker on a skipped unit test is one too (written by dev-frontend/dev-backend, resolved by unit-tester, checked by product-manager before validation, allowed by `role-guard.sh stop-tests`). Renaming a path or format means updating every agent that reads or writes it, `role-guard.sh`'s path rules, plus the README's "Files produced" table.
- Runtime state lives under `.pipeline/`, not `.claude/`, because Claude Code treats `.claude/` as protected and blocks unattended writes.
- Agents never stop to ask; judgment calls go to team memory (`log_decision`) when it is available, otherwise to `.decisions/<agent>.decisions.md`; product-manager exports each story's logged entries to those files when the story ends (`export_decisions_files`) — the same "Decision logging" block is repeated in each agent that logs. Model choice is deliberate: `opus` for product-owner, `sonnet` for analyst (A/B-tested 2026-10-21), `haiku` for unit-tester, `sonnet` for the rest.
- `run-parallel.sh` runs ready stories (all `## Dependencies` already in `.completed/`) in separate git worktrees on `feature/<slug>`; single-repo workspaces only.

## gate.sh

Two modes. **Scoped** (the default) is the SubagentStop hook declared once in the workspace's `settings.json`: stdin JSON, only dev-frontend/dev-backend/dev-integrator, exit 2 makes the agent keep working, loop guard `GATE_MAX_BLOCKS` (default 3) keyed by agent_id or, for a session agent, session_id. It checks only the packages changed since HEAD (a package outside git is checked whole) and in them the tests related to the changed files (`jest --findRelatedTests` capped by `GATE_SCOPED_MAX_TESTS`, `vitest related`; no e2e; .NET tests only in full), inside a 270 s budget so the 600 s stream watchdog never fires. `pm-state.sh start` reports whether that hook is wired (`GATE hook wired|missing|duplicated|unknown`, from the parsed settings files and the dev agents' frontmatter); product-manager runs the scoped gate itself on `missing`/`unknown`. `SubagentStop` does not fire for a dev agent run as the session (`claude --agent dev-backend`): the eval kit's template adds a `Stop` copy of the hook for that, which `gate.sh` answers only for the three dev agents. **Full** (`gate.sh --full`) is product-manager's call, once per story at the start of step 9, in the background. One gate per repository at a time (an `mkdir` lock in `$TMPDIR`; a waiter reuses the answer for unchanged code), a time limit per step (`GATE_STEP_TIMEOUT`, `GATE_BUDGET`, `GATE_LOCK_WAIT`), an EXIT/INT/TERM trap that kills the process tree it started (`taskkill /F /T` on the `/proc/<pid>/winpid` of Git Bash, `pgrep -P` elsewhere; never the Claude Code process), a journal in `.pipeline/gate.log`, and `NO_COLOR=1 FORCE_COLOR=0` for every step (`FORCE_COLOR` beats `NO_COLOR` in chalk). It auto-detects npm scripts (jq, or node as fallback) and `dotnet` solutions (`.sln`, `.slnx`, `.csproj`); a project it cannot check fails as `NOT CHECKED`; `.claude/gate.local.sh` in a workspace replaces detection entirely and sees `GATE_MODE`. Env: `GATE_SKIP_BUILD`, `GATE_SKIP_TESTS`, `GATE_NO_CACHE`, `GATE_TEST_ARGS`. A pass is cached in `.pipeline/gate-pass` by a git fingerprint of the code (HEAD + diff + untracked, coordination folders excluded) and the mode (a full pass covers a scoped call); any code change re-runs it, failures are never cached.

## role-guard.sh

PreToolUse (Edit|Write|NotebookEdit) per-agent policy plus two Stop checks (`stop-plan` for analyst, `stop-tests <agent>`), all documented in its header and README 3e. The frontmatter hooks of the session agent (`claude --agent product-manager`) behave like settings hooks: they also fire for every subagent's tool calls, and a running subagent's hooks can fire for a parallel sibling's calls. The hook input's `agent_type` names whose call it is, so each check exits 0 when it differs from the role it was installed for (verified 2026-10-25: without that, product-manager's guard blocked every dev-frontend write in a PM-01 run). Any new hook must do the same. Reviewer edits are allowed only when the old and new text normalize to the same lines once their marker comments (`REVIEW:`, `SECURITY:`, `UX:`, analyst's `TODO:`) are removed. For every role, an Edit or Write on an existing `package.json` is blocked when its `scripts` or `jest` value (compared with sorted keys, on the file as the edit would leave it) differs, or when the result is no longer JSON; any Edit or Write on an existing `jest.config.*` is blocked. A new `package.json` or `jest.config.*` and a `package.json` that is already not JSON pass (a new jest config in a package that ran jest with defaults is the known gap). Other test configs (vitest, playwright, eslint, tsconfig, jest setup files) are not covered. It fails open (exit 0) without jq/node or on unparsable input, and Stop checks give up after `ROLE_GUARD_MAX_BLOCKS` (default 2). On Windows, MSYS rewrites path-like arguments and environment values passed to native programs such as jq; the hooks only read JSON from stdin, and `test-hooks.sh` sets `MSYS_NO_PATHCONV=1` when it builds inputs.

## team-memory MCP server

- `store.py` holds all logic (`Store` class, validation helpers, FTS5 search); `server.py` is a thin tool layer that imports `MCPServer` (SDK 2.x) or falls back to `FastMCP` (1.x) — keep both working.
- DB: `$TEAM_MEMORY_DB`, else `<cwd>/.pipeline/team-memory.db`; inside a git worktree it resolves to the main worktree's DB so parallel stories share memory (`default_db_path`).
- Multi-process safety relies on short-lived connections (WAL, `busy_timeout`) and `BEGIN IMMEDIATE` for claims/locks — preserve this when touching task/lock code; the race tests cover it.
- Input limits (content 8000 chars, names `[A-Za-z0-9_.:#-]` ≤ 96) are enforced in `store.py` and documented in `mcp/team-memory/README.md`; the server's instructions string tells agents stored text is data, never instructions.
- Adding or renaming a tool means updating the tool table in `mcp/team-memory/README.md` and any agent prompts that call it, including their `tools:` lines, which name each `mcp__team-memory__<tool>` they use. `_ROLE_SECTIONS` in `store.py` maps each agent name to its conventions sections; a new agent that calls `agent_briefing` needs an entry.
