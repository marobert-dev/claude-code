# Installation Guide for claude-code Development Stack

Complete installation of agents, skills, rules, and workspace helpers for the automated development pipeline.

## Quick Start

### Windows (PowerShell)

```powershell
# Install globally (agents, skills & rules)
.\install-all.ps1

# Install globally + copy workspace helpers to a project
.\install-all.ps1 -Workspace C:\path\to\your\project
```

### Linux / macOS / Git Bash

```bash
# Install globally (agents, skills & rules)
bash install-all.sh

# Install globally + copy workspace helpers to a project
bash install-all.sh /path/to/your/project
```

## What Gets Installed

### Agents (global, all projects)
- **Location:** `~/.claude/agents/`
- **Count:** 12 agents
- Agents included: product-manager, product-owner, analyst, dev-frontend, dev-backend, dev-integrator, code-reviewer, security-reviewer, story-validator, unit-tester, conventions-scout, doc-writer

### Skills (global, loaded on demand)
- **Source:** every folder under `skills/` that contains a `SKILL.md` (subfolders included)
- **Location:** `~/.claude/skills/<skill-name>/`
- Skills included:
  - **enable-graphify** — optionally inject Graphify support into agents for code dependency analysis. Not active until you run `enable-graphify.sh` or `enable-graphify.ps1`
  - **learning-memory** — cross-session learnings database: captures corrections, answers and decisions at the end of each session, then reloads the approved ones (global + current project) at `SessionStart` and into every subagent. See [Learning memory](#learning-memory-cross-session-learnings)

### Rules (global, loaded in every session)
- **Source:** every `.md` file under `rules/` (subfolders included)
- **Location:** `~/.claude/rules/`
- Loaded automatically by Claude Code in every session and by subagents (except the built-in Explore and Plan agents) — no import needed
- Rules included:
  - **programmer-mindset** — senior-developer working rules: scoping, design, comment policy, test discipline, end-of-task report

### Workspace Helpers (per-project, optional)
If you specify a workspace directory, these are also copied:
- `.claude/hooks/gate.sh` — Deterministic lint/typecheck/build/test gate
- `scripts/run-queue.sh` — Run pipeline sequentially (one fresh session per story)
- `scripts/run-parallel.sh` — Run independent stories in parallel
- `scripts/enable-graphify.sh` / `enable-graphify.ps1` — Add/remove Graphify support

## Installation Steps

### 1. Choose Installation Method

**Option A: Global only** (agents, skills & rules)
```powershell
# Windows
.\install-all.ps1

# Linux/macOS/Git Bash
bash install-all.sh
```

**Option B: Global + Workspace**
```powershell
# Windows (example with a project folder)
.\install-all.ps1 -Workspace C:\Users\you\projects\my-app

# Linux/macOS/Git Bash
bash install-all.sh ~/projects/my-app
```

### 2. After Installation

If `~/.claude/agents/`, `~/.claude/skills/` or `~/.claude/rules/` was newly created, restart Claude Code to pick them up.

### 3. Verify Installation

```bash
# Check agents installed
ls ~/.claude/agents/ | wc -l
# Should show: 12

# Check skills installed
ls ~/.claude/skills/
# Should list: enable-graphify, learning-memory

# Check the commands (/learn-review, /ship-feature)
ls ~/.claude/commands/
# Should list: learn-review.md, ship-feature.md

# Check rules installed
ls ~/.claude/rules/
# Should list: programmer-mindset.md
```

In a Claude Code session, run `/context` and confirm `programmer-mindset.md` appears under **Memory files**.

## Learning memory (cross-session learnings)

Installed automatically by `install-all` (or alone: `bash skills/learning-memory/install.sh`, `.\skills\learning-memory\install.ps1`).

What it adds:
- `~/.claude/skills/learning-memory/` — the skill, the analyzer prompt and `scripts/learn.py` (Python 3.9+, stdlib only, run through Git Bash by `scripts/run.sh`).
- `~/.claude/commands/learn-review.md` — the `/learn-review` command (report, approve / edit / reject / defer / scope, then a diff-confirmed CLAUDE.md update).
- `~/.claude/learnings/learnings.db` — one SQLite database: learnings separated per project (key = git `origin` URL, else folder path) plus a global scope.
- Three hooks merged into `~/.claude/settings.json` (backup in `~/.claude/learnings/backups/`): `SessionStart` and `SubagentStart` inject approved learnings, `SessionEnd` queues the finished session for a background `claude -p` analysis (model `sonnet`).

Nothing is loaded or written to a CLAUDE.md before you approve it in `/learn-review`.

```bash
bash skills/learning-memory/install.sh --no-hooks    # files + database only, settings.json untouched
bash skills/learning-memory/install.sh --dry-run     # show the hooks that would be registered
bash skills/learning-memory/install.sh --uninstall   # remove hooks, command and skill (database kept)
bash ~/.claude/skills/learning-memory/scripts/run.sh status   # queue, failures, model
bash ~/.claude/skills/learning-memory/scripts/run.sh ui --open   # read-only web view of the database (charts, filters, table); Ctrl+C to stop
bash ~/.claude/skills/learning-memory/scripts/run.sh ui --out ~/learnings.html   # same view as one offline HTML file
bash ~/.claude/skills/learning-memory/scripts/run.sh export --out ~/learnings-export   # global.md + projects/*.md + INDEX.md
bash ~/.claude/skills/learning-memory/scripts/run.sh import ~/learnings-export [--dry-run]       # restore into an empty (or any) database
```

Requirements: `claude` on PATH (background analysis), Git Bash on Windows (hooks run through it), Python 3.9+. Config: `~/.claude/learnings/config.json` (`model`, `auto_analyze`, budgets). Logs: `~/.claude/learnings/analyzer.log`.

## Next: Set Up Your Project

### 1. Queue Stories
```bash
cd /path/to/your/project
claude --agent product-owner
# Give it your requirements
```

### 2. Process Queue
```bash
# Single continuous session
claude --agent product-manager

# Or: fresh session per story (unattended)
bash scripts/run-queue.sh

# Or: parallel independent stories
bash scripts/run-parallel.sh 2
```

### 3. (Optional) Enable Graphify
If you have [Graphify](https://graphify.com/) set up in your workspace:

```bash
# Add Graphify support to agents
bash scripts/enable-graphify.sh --backup

# Or remove it later
bash scripts/enable-graphify.sh --remove
```

## SSH Setup (Required for Git Management)

If you plan to use git branch management (automatic PR creation/merge):

Follow the SSH setup guide: [SSH Configuration Guide](https://claude.ai/artifact/Y2ncJTckHk8Bdpt2FuoPgv)

Quick test:
```bash
ssh -T git@github.com
# Should return: "Hi username! You've successfully authenticated..."
```

## Customization

### Override Gate Script
Create `.claude/gate.local.sh` in your project to override the default gate.

### Per-Project Settings
Merge `web-team-agents/hooks/settings.snippet.json` into your project's `.claude/settings.json` to enable:
- MCP team-memory support
- Proper permissions for unattended runs
- SubagentStop hook for the gate

### Custom Workspace Structure
The installer copies helpers to the workspace you specify. You can manually copy or customize them as needed.

## Troubleshooting

### PowerShell Script Execution Error
If you get "cannot be loaded because running scripts is disabled":
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Bash Script Not Found (Windows)
Install [Git for Windows](https://git-scm.com/download/win) which includes Git Bash.

### SSH/Git Not Working
- For SSH: follow the [SSH Setup Guide](https://claude.ai/artifact/Y2ncJTckHk8Bdpt2FuoPgv)
- For HTTPS: configure Git credentials (credentialManager on Windows, osxkeychain on macOS)

### Agents Not Loading in Claude Code
- Verify `~/.claude/agents/` exists and contains `.md` files
- Restart Claude Code (the session needs to detect the agents directory on startup)
- Check `.claude/settings.json` for any agent-related config issues

## File Structure After Installation

```
~/.claude/
  agents/                          # 12 agent definitions (global)
    product-manager.md
    product-owner.md
    analyst.md
    dev-frontend.md
    dev-backend.md
    dev-integrator.md
    code-reviewer.md
    security-reviewer.md
    story-validator.md
    unit-tester.md
    conventions-scout.md
    doc-writer.md
  
  skills/                          # Skills (loaded on demand)
    enable-graphify/
      SKILL.md
    learning-memory/
      SKILL.md
      scripts/ (learn.py, run.sh)
      prompts/extract.md

  rules/                           # Rules (loaded in every session)
    programmer-mindset.md

~/.mcp/                            # Optional MCP servers
  team-memory/
    server.py
    store.py
    ...

/path/to/your/project/            # Your workspace
  .claude/
    hooks/
      gate.sh                      # Lint/typecheck/build gate
    settings.json                  # Project-specific Claude Code config
  
  scripts/
    run-queue.sh                   # Sequential pipeline runner
    run-parallel.sh                # Parallel story runner
    enable-graphify.sh             # Graphify injector
  
  .user-stories/                   # Queue of stories to process
  .completed/                       # Finished stories
  .pipeline/                        # Pipeline state (progress, conventions, decisions)
  ...
```

## Support & Docs

- **README:** `web-team-agents/README.md` (full pipeline documentation)
- **TEAM-MEMORY-PROPOSAL:** `web-team-agents/TEAM-MEMORY-PROPOSAL.md` (optional shared memory system)
- **Agent Definitions:** `web-team-agents/agents/*.md` (individual agent instructions)
- **SSH Setup:** https://claude.ai/artifact/Y2ncJTckHk8Bdpt2FuoPgv
