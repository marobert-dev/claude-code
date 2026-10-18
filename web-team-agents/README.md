# Dev team subagents — install

## Layout

```
agents/    12 subagent definitions — installed into ~/.claude/agents/ (global, all projects)
hooks/     gate.sh (deterministic lint/typecheck/build/test gate), pm-state.sh (product-manager bookkeeping) + settings.snippet.json
scripts/   run-queue.sh, run-parallel.sh — pipeline runners
           enable-graphify.sh / enable-graphify.ps1 — optionally inject Graphify support
mcp/       team-memory/ — optional shared-memory MCP server (source; see its own README)
install.sh / install.ps1   installer — run one, see below
```

## 1. Install (global, all projects)

One command, from a clone of this repo:

```bash
bash install.sh                      # copies agents/*.md -> ~/.claude/agents/
```

```powershell
.\install.ps1                        # same, native PowerShell
```

Restart Claude Code if `~/.claude/agents/` didn't already exist before this copy — a running session only picks up a brand-new agents directory after a restart.

To also install the per-project helpers into a **workspace root** (the folder you run the agents from — this copies `hooks/gate.sh`, `hooks/pm-state.sh` and `scripts/run-queue.sh`/`run-parallel.sh` there), pass it as an argument:

```bash
bash install.sh /path/to/your/app-repo
```

```powershell
.\install.ps1 -Workspace C:\path\to\your\app-repo
```

Or do it by hand:

```bash
mkdir -p .claude/hooks scripts
cp hooks/gate.sh hooks/pm-state.sh .claude/hooks/
cp scripts/run-queue.sh scripts/run-parallel.sh scripts/
```

Optional but recommended — run the gate inside the dev agents too, so they fix failures before finishing. Back up `.claude/settings.json` first, then merge `hooks/settings.snippet.json` into it. The gate is also run by product-manager before every code review, so the pipeline stays safe even if the hook never fires (SubagentStop matcher/exit-code behavior is only partly documented — verify with a small run).

Scripts and `gate.sh` are bash: on Windows run them from Git Bash or WSL. Override the gate for a project with `.claude/gate.local.sh`.

**For another agent installing this on your behalf:** clone the repo, run `bash install.sh [workspace-dir]` (or `install.ps1` on native Windows PowerShell), then read section 2 onward below to queue and run the pipeline — no other setup is required except the optional tools in section 7.

## 2. Queue stories (product-owner, run on its own)

From your workspace root — the folder that either *is* the app repo, or contains each app repo as a subdirectory if the story spans more than one (e.g. separate frontend/backend repos):

```bash
claude --agent product-owner
```

Give it the request. It writes one Markdown file per story into `.user-stories/` in that same folder, named `<NN>-<story-slug>.md`, the number giving the processing order — and continues numbering after whatever's already queued if you run it again. product-owner and product-manager are fully independent — run product-owner as many times as you want to queue more stories before ever running product-manager.

## 3. Process the queue (product-manager, run independently)

```bash
claude --agent product-manager
```

- If `.user-stories/` is missing or empty, product-manager errors out immediately: no stories to process.
- On the first run it calls **conventions-scout** once to write `.pipeline/conventions.md` (stack, layering, i18n, test setup, exact lint/typecheck/build/test commands). Every other agent reads that file instead of re-detecting conventions.
- Otherwise it works through the queued files in filename order, one at a time:
  1. **analyst** appends a technical plan (incl. UI/UX for user-facing stories) directly into the story file. For any API change it also writes/updates `contracts/openapi.yaml` — the single contract dev-backend, dev-frontend and dev-integrator all build against.
  2. **dev-frontend** and/or **dev-backend** implement it (in parallel when both apply). After each, a deterministic **gate** (`.claude/hooks/gate.sh`: lint, typecheck, build, unit tests — no LLM) must pass before **code-reviewer** runs. They loop with code-reviewer until clean, then **unit-tester** adds coverage. product-manager logs condensed (≤15 lines) reports into the story file. Unresolved broken code stops the run.
  3. **dev-integrator** wires frontend to backend, verified by a contract check (Schemathesis against `contracts/openapi.yaml` when installed), then gate + code-reviewer loop. A blocked integration stops the run.
  4. **security-reviewer** reviews every changed file (secret/SAST/dependency scans if installed, authZ, validation, mobile risks). Findings loop back to the owning dev agent; critical/high must be fixed.
  5. **story-validator** turns each acceptance criterion into an automated e2e test (French and English) under `tests/e2e/<story-id>/`, checks the boxes that pass, then runs the **whole e2e suite** as the regression check. Only `(manual)` criteria of overlapping older stories are re-checked by hand.
  6. product-manager saves the returned file to `.stories-reviewed/<same-filename>` regardless of outcome.
  7. If a box is unchecked or a regression was found, product-manager runs up to **2 bounded fix rounds** (owning agent → gate → reviewers → story-validator again). If it still fails, the story **stays** in `.user-stories/`, the run stops, and product-manager writes a handoff checkpoint.
  8. If everything passes, story-validator archives the story into `.validated-stories/`, **doc-writer** runs, and the story file is **moved** from `.user-stories/` to `.completed/` — that queue only ever holds unfinished work.
- Every agent runs autonomously (no per-step approval) and logs any genuine judgment call — an ambiguous criterion, a contradiction, a gap, a question — to `.decisions/<agent-name>.decisions.md` rather than stopping to ask.
- product-manager writes a handoff checkpoint every 3 completed stories and once more when the queue is empty, refreshing `.pipeline/decisions-digest.md` each time. product-owner reads that digest, so recurring ambiguities get fixed at the source (sharper criteria) instead of being guessed again and again.
- With git management enabled, commits include this story's application changes — but never `.user-stories/`, `.stories-reviewed/`, `.validated-stories/`, `.completed/`, `.decisions/`, or `.pipeline/pm-progress.md`, which are local coordination state (also `.pipeline/pm-last-run.txt`, `.pipeline/decisions-digest.md` and `.pipeline/team-memory.db*`). Add those specific paths to `.gitignore` if you haven't already; the rest of `.claude/` (like `.claude/agents/`) should stay committed for the team. If the project uses Graphify, its `graphify-out/` folder is managed by Graphify's own git hook, independent of this pipeline's commits.

Don't set `product-manager` as a project-wide default agent in `.claude/settings.json` — that would force every session in that repo into pipeline mode, including plain ad-hoc coding sessions. Use `--agent` per run instead.

**Why launch with `product-manager`, not `product-owner`, to process the queue:** only the agent running as the actual Claude Code session has native access to your `/handoff` and `/resume` commands, and product-manager is the one that needs them (it pauses mid-pipeline on failure or every 5 stories). product-owner doesn't need this — it's a short, one-shot run, which is also why it's fine for it to be a fully separate invocation now.

## 3a. Graphify integration (optional, enables auto-update)

**By default, agents do NOT use Graphify** — the pipeline is entirely independent and has no external dependencies. This keeps the agent stack lean and publishable.

**To add Graphify support** (if you have [Graphify](https://githubify.com/) set up in your workspace and want agents to query it for architecture analysis):

```bash
# Bash / Linux / macOS:
bash scripts/enable-graphify.sh --backup

# Windows PowerShell:
.\scripts\enable-graphify.ps1 -Backup
```

This:
1. Backs up the current agents to `~/.claude/agents-graphify-backup-<timestamp>/`
2. Injects a "Before anything else" block into each agent that checks for `graphify-out/`
3. If Graphify exists, agents will read `GRAPH_REPORT.md` and can run `graphify query "<question>"` for dependency analysis
4. If Graphify doesn't exist, agents silently skip this and proceed normally

**To remove Graphify** (revert to the minimal agent definitions):

```bash
bash scripts/enable-graphify.sh --remove
# or
.\scripts\enable-graphify.ps1 -Remove
```

Agents are designed to work perfectly with or without Graphify — the integration is non-invasive and optional.

### 3b. Unattended and parallel runs

- **One fresh session per story** (context never accumulates): `bash scripts/run-queue.sh` from the workspace root. It runs `claude -p ... --agent product-manager` in ONE STORY MODE, reads `.pipeline/pm-last-run.txt` (`COMPLETED`, `FAILED`, or `EMPTY`), and stops on the first failure. Set `CLAUDE_FLAGS` (default `--permission-mode acceptEdits`) and pre-approve the tools your setup needs in `.claude/settings.json` — a headless run cannot answer permission prompts.
- **Independent stories in parallel**: `bash scripts/run-parallel.sh 2` (add `--dry-run` to only list what is ready). product-owner writes a `## Dependencies` section in every story; a story is ready when everything it lists is already in `.completed/`. Each ready story runs in its own git worktree on `feature/<slug>`. You merge the branches into `dev` yourself, then run `run-queue.sh` so regression checks run on the merged result. Single-repo workspaces only.

### 3c. Team memory (phase 1, optional)

Source lives in this repo, at `mcp/team-memory/` (see its `README.md`); the installed copy Claude Code actually runs is a separate copy at `~\.mcp\team-memory\`, registered globally (`--scope user`) so every project on this machine can use it — **re-copy `server.py`/`store.py` there after every source change, or the running server silently keeps the old behavior** (this bit us once: it kept defaulting to `.claude/team-memory.db` for days after the source was fixed to `.pipeline/team-memory.db`). Merge `hooks/settings.snippet.json` into each project's `.claude/settings.json` (it now also allows `mcp__team-memory`), and add `.pipeline/team-memory.db*` to that project's `.gitignore`. **Phase 1:** product-manager adds a short "Team memory briefing" to each agent prompt and writes a handoff entry at every checkpoint and a fact when a story completes. **Phase 2:** analyst, dev-frontend, dev-backend, dev-integrator, code-reviewer, security-reviewer, story-validator and unit-tester also have the tools (`tools:` line) and each has a "Team memory" section — `story_context`/`recall` before working, locks on shared files, at most 3 `remember` calls at the end, `log_decision` for judgment calls, and reviewers save recurring `review-pattern` rules that devs recall before coding. Every agent ends its report with `Memory: available|unavailable`, so the first story doubles as the smoke test that subagents can reach the server (product-manager records the result in `.pipeline/pm-progress.md`). If the server is missing, every agent skips its memory steps silently and the pipeline runs exactly as before. **Phase 3 (applied 2026-09-24, validated on 5 stories — review rounds dropped from ~1-2/story to 4/5 clean first-round; task board mirror redone 2026-09-30, see incident note below):** product-manager mirrors the pipeline's steps onto the task board with one `task_checkpoint(story, role, status)` call per stage (no separate `task_post`/`task_claim`/`task_finish`) for crash-recovery visibility; product-owner reads `recall(kind="fact")` and `decisions_digest()` before writing new stories to avoid re-queuing built capabilities; doc-writer optionally reads `recall(kind="fact", story=...)`; the server gained `export_decisions_markdown(story, agent)` so `.decisions/*.decisions.md` can eventually be regenerated from `log_decision` entries instead of hand-written in parallel (not yet switched over — both still run side by side). Details: `TEAM-MEMORY-PROPOSAL.md`.

## 4. Note on claude.ai / Cowork access

Kept as Claude Code subagents only — no companion claude.ai/Cowork Skill built. These files run in Claude Code exclusively; they won't appear as anything usable inside claude.ai chat. Say the word if you want that changed later.

## 5. Not yet smoke-tested

Whether `/handoff` and `/resume` behave the same when the session runs under `--agent product-manager` versus the default assistant persona. Worth a real run on a small queue before trusting it on a big one.

## 6. Set up Graphify (recommended, replaces the old hand-maintained architecture file)

Every agent in this set checks for `graphify-out/` and reads `graphify-out/GRAPH_REPORT.md` for architecture context, and can run `graphify query "<question>"` for targeted impact analysis, if [Graphify](https://graphify.com/) is set up in your workspace. It's optional — agents skip this gracefully if it isn't there — but it's a real upgrade over a doc-writer-maintained file: deterministic AST parsing (no hallucination risk), auto-refreshes on every commit, and merges graphs across multiple repos natively.

**⚠️ Before installing on any platform:** back up `~/.claude/settings.json` first. A reported bug has `graphify claude install --strict` overwrite that file entirely — no backup, existing MCP servers/hooks/plugins gone. Given the `~/.claude/agents/` setup here, don't use `--strict`, and keep a copy of `settings.json` regardless.

**Setup — Linux/macOS** (verify exact flags with `graphify --help` or the [official repo](https://github.com/Graphify-Labs/graphify) — commands below are assembled from its docs, not guaranteed 1:1 for every version):

1. Install the CLI: `uv tool install graphifyy` (the install command has a double "y" due to a PyPI name conflict; the CLI itself is invoked as `graphify`).
2. Register the skill: `graphify install`.
3. From your workspace root, build the initial graph — check `graphify --help` for the exact build/init subcommand for your version.
4. Enable auto-refresh on every commit: `graphify hook install`.
5. For a multi-repo setup (e.g. separate frontend/backend repos), combine their graphs: `graphify merge-graphs a.json b.json`.
6. Commit `graphify-out/` to git (excluding `cost.json`) so the whole team shares the graph without everyone rebuilding it — this is Graphify's own recommendation, and it plays well with this pipeline's own git-management step, which leaves `graphify-out/` alone.

**Setup — Windows:**

1. `uv tool install graphifyy` then `uv tool update-shell`, and open a **new** terminal — the PATH change doesn't apply to the current one. `pipx install graphifyy` works too; avoid plain `pip install` on Windows if you can, it's prone to PATH/environment mismatches (`ModuleNotFoundError` even after a "successful" install).
2. `graphify install` to register the skill.
3. PowerShell-specific bug: `/graphify .` fails ("path not recognized") because a leading `/` is parsed as a path separator. Use `graphify .` (no leading slash).
4. If install fails on Python 3.12+ with a `numpy`/`gensim` build error, that's a known transitive-dependency issue — install under Python 3.11 instead (e.g. via `pyenv install 3.11`, then `pipx install graphifyy --python <path-to-3.11>`).

**Docker:**

- To serve an already-built graph over HTTP from a container (the officially documented use case — for sharing a graph rather than building one inside your dev workflow):
  ```bash
  docker build -t graphify .
  docker run -p 8080:8080 -v "$(pwd)/graphify-out:/data" graphify \
    /data/graph.json --transport http --host 0.0.0.0 --api-key "$SECRET"
  ```
- To have Graphify available inside a devcontainer where Claude Code itself runs, add to that image's Dockerfile:
  ```dockerfile
  RUN pip install graphifyy --break-system-packages \
      && graphify install --platform claude-code
  ```
  (`--break-system-packages` is needed on recent Ubuntu/Debian base images that block a plain system-wide pip install; `uv tool install graphifyy` is a drop-in alternative if `uv` is already in the image.)

Runs 100% locally for code parsing (tree-sitter, no API key, no telemetry). Optional non-code parsing (docs, PDFs, schemas) can go through a local model like Ollama if you want to keep everything on-device.

## 7. Prerequisites — what to install yourself

No MCP server is required. Everything below is optional except where marked; every agent skips gracefully (and says so) when a tool is missing, and none installs anything on its own.

| Purpose | Tool | Install (check the tool's docs for your OS) |
|---|---|---|
| Gate script (**required** for gate.sh) | `jq`, bash (Git Bash or WSL on Windows) | package manager of your choice |
| Web e2e tests / regression suite | Playwright | `npm i -D @playwright/test` then `npx playwright install` |
| Mobile e2e tests | Maestro (needs Java 17+) | see maestro.mobile.dev |
| Typed API clients (frontend) | `openapi-typescript` or `orval` | `npm i -D openapi-typescript` |
| Emit the OpenAPI spec (C# backend) | Swashbuckle.AspNetCore (+ its CLI) or NSwag | NuGet |
| Contract test (integrator) | Schemathesis | `pipx install schemathesis` (or `uv tool install schemathesis`) |
| Breaking-change check (mobile compat) | oasdiff | release binary from github.com/oasdiff/oasdiff |
| Secret scan | gitleaks | release binary |
| Static analysis | semgrep | `pipx install semgrep` |
| Dependency vulnerabilities | `npm audit` and `dotnet list package --vulnerable` (built in), or osv-scanner | — |
| Code graph | Graphify (section 6) | see section 6 |

Optional MCP servers: Playwright MCP (`claude mcp add playwright -- npx -y @playwright/mcp@latest`) if you want agents to explore the running app interactively — the pipeline itself only needs the Playwright test runner. A shared team-memory MCP server is a separate, later addition.

## Files produced in the app repo

Every directory this pipeline creates and manages for itself is dot-prefixed (hidden); only genuine project deliverables are left visible.

| Path | Written/updated by | Contents | Commit to git? |
|---|---|---|---|
| `.user-stories/<NN>-<slug>.md` | product-owner (created), analyst/product-manager (appended to), product-manager (deleted once finished) | The live queue: one file per unfinished story | No — local coordination state |
| `.pipeline/pm-progress.md` | product-manager | Status per story (pending/in progress/done/failed) | No — local coordination state |
| `.stories-reviewed/<same-filename>` | product-manager | Permanent copy of every story file as returned by story-validator, pass or fail — the queue file itself gets moved, not deleted, once finished, but this copy stays put | No — local coordination state |
| `.validated-stories/<same-filename>` | story-validator | Copy of every story that has fully passed — the regression-testing baseline for every story validated afterward | No — local coordination state |
| `.completed/<same-filename>` | product-manager | Final resting place of every fully finished story file, moved here from `.user-stories/` instead of being deleted | No — local coordination state |
| `.decisions/<agent-name>.decisions.md` | every agent | One file per agent, logging every autonomous judgment call it made (ambiguity, contradiction, gap, question) and why | No — local coordination state |
| `.pipeline/conventions.md` | conventions-scout (bootstrap/refresh) | Stack, layering, i18n, test setup, exact lint/typecheck/build/test/e2e commands — read by every agent | Yes — shared knowledge |
| `.pipeline/decisions-digest.md` | product-manager | Recurring ambiguities and "needs human answer" items distilled from `.decisions/`; read by product-owner | No — local coordination state |
| `.pipeline/team-memory.db` | team-memory MCP server (source: `mcp/team-memory/`; installed at `~\.mcp\team-memory\`, registered globally) | Shared memory (handoffs, story facts, gotchas, review patterns, decisions, standing rules), task/lock tables, flaky-test registry, usage telemetry — optional | No — local coordination state |
| `.pipeline/pm-last-run.txt` | product-manager | One-line status (`COMPLETED`/`FAILED`/`EMPTY`) read by the scripts | No — local coordination state |
| `.claude/hooks/gate.sh` | you (copied from `hooks/`) | Deterministic lint/typecheck/build/unit-test gate | Yes |
| `.claude/hooks/pm-state.sh` | you (copied from `hooks/`) | product-manager's deterministic bookkeeping: handoff pickup, queue order, `.stories-reviewed/` copy + checkbox count, move to `.completed/`, `pm-last-run.txt`, feature branch, staging without coordination files | Yes |
| `contracts/openapi.yaml` | analyst (source of truth); nobody else edits it | API contract shared by backend, frontend, integrator | Yes — project deliverable |
| `tests/e2e/<story-id>/` | story-validator | Automated acceptance tests (FR + EN) — the regression suite | Yes — project deliverable |
| `graphify-out/` | Graphify (external tool, not one of these agents) | Deterministic code knowledge graph — `GRAPH_REPORT.md`, `graph.json`, `graph.html` — every agent reads it for impact analysis if present. See section 6 for setup. | Yes, per Graphify's own convention (except `cost.json`) |
| `docs/dev/` | doc-writer | Human developer documentation — English only, regardless of the app's own languages | Yes — project deliverable |
| `docs/user-manual/en/`, `docs/user-manual/fr/` | doc-writer | Two independent, cross-linked, searchable HTML sites mirroring the app's own navigation, written for a total beginner (no jargon, step-by-step) — the app supports French and English, so this does too | Yes — project deliverable |

## Agents

All 12 live in [`agents/`](agents/).

| File | Role |
|---|---|
| `agents/product-owner.md` | Critiques the request against market standards, creates and orders stories into `.user-stories/`. Runs independently. |
| `agents/product-manager.md` | Hub — processes `.user-stories/` one file at a time, tracks progress, pauses via `/handoff`. Runs independently. |
| `agents/analyst.md` | Appends the technical plan (incl. UI/UX) into each story file |
| `agents/dev-frontend.md` | Web and mobile (React Native) client implementation (stubbed API clients) |
| `agents/dev-backend.md` | Backend implementation |
| `agents/unit-tester.md` | Unit tests for services/handlers/repositories/components |
| `agents/dev-integrator.md` | Wires client (web/mobile) to real backend controllers, incl. offline/push/deep-link wiring on mobile |
| `agents/story-validator.md` | Turns criteria into automated e2e tests (FR + EN), checks off passing ones, runs the full e2e suite as regression, no app-code fixes |
| `agents/doc-writer.md` | Writes/updates dev docs and the beginner-level user manual after a story passes validation |
| `agents/code-reviewer.md` | Reviews dev-frontend/dev-backend/dev-integrator's changes with inline `REVIEW:` comments, loops with them until resolved |
| `agents/conventions-scout.md` | Writes/refreshes `.pipeline/conventions.md` (stack, conventions, exact commands) once instead of every agent re-detecting them |
| `agents/security-reviewer.md` | Reviews every changed file for security (authZ, validation, secrets, dependencies, mobile), inline `SECURITY:` comments, loops with the dev agents |

Models: `opus` for product-owner and analyst (planning errors are the most expensive downstream); `haiku` for unit-tester; `sonnet` for everything else — doc-writer stays on sonnet because the beginner-level French/English manual needs natural wording.

Each file ends with an HTML comment listing existing published alternatives found during research, for you to review — not applied automatically.

## TODO

- **Deployment/publication agent — not yet built.** Nothing in this stack currently ships anything: no web deploy/CI-CD step, no App Store/Play Store submission (signing, provisioning profiles, store metadata/screenshots, review-cycle-aware versioning). Every story currently ends at "committed to a feature branch." Add this when ready.