---
name: enable-graphify
description: Inject Graphify integration into all development agents for code dependency analysis. Creates versions of agents that check for graphify-out/ and use it for architecture queries.
---

# Enable Graphify in Agents

This skill adds Graphify support to all agents in the pipeline. It injects a "Before anything else" block into each agent that checks for `graphify-out/` and integrates it into the agent's workflow.

## What it does

1. **For each agent** (product-manager, analyst, dev-backend, dev-frontend, dev-integrator, code-reviewer, security-reviewer, story-validator, unit-tester, doc-writer, conventions-scout, product-owner):
   - Adds a block after the opening lines that checks whether `graphify-out/` exists
   - If it exists: agent reads `GRAPH_REPORT.md` and can run `graphify query "<question>"` for architecture analysis
   - If not: agent skips Graphify and proceeds normally (no error)

2. **Creates modified versions** in `.claude/agents-with-graphify/` (optional, for backup/review)

## How to use

### Option 1: Inject into existing agents (modifies in-place)

```bash
# In your project root:
claude --agent product-manager
> /enable-graphify
```

The skill will:
- Read all agents from `~/.claude/agents/`
- Add Graphify blocks if not already present
- Update files in-place
- Sync to your project's local `.claude/agents/` if it exists

### Option 2: Preview before applying

The skill asks for confirmation before modifying files, showing:
- Which agents will be modified
- Exact text being injected
- Backup location (if you want to keep originals)

## Graphify block (what gets injected)

Each agent receives this at the start of its body text (after the frontmatter):

```markdown
Before anything else, check whether `graphify-out/` exists in the workspace. If it does, read `graphify-out/GRAPH_REPORT.md` for a high-level architecture summary, and run `graphify query "<question>"` via Bash whenever you need to know what a file or symbol depends on, or is depended on by, before [role-specific action]. If Graphify isn't set up for this project, skip this and proceed without it.
```

The bracketed action varies by agent (e.g., "routing work" for product-manager, "changing it" for dev agents, etc.).

## Removing Graphify

To revert to the original agents without Graphify:

1. Restore from backup (if you made one): `cp .claude/agents-backup/* ~/.claude/agents/`
2. Or reinstall from the repo: `bash install.sh`
3. Or run `/enable-graphify` again and select "remove Graphify blocks"

## Prerequisites

- Agents are installed in `~/.claude/agents/`
- If you have a project copy in `.claude/agents/`, it will be synced after modification

## Notes

- This is fully reversible — you can always remove Graphify blocks later
- If an agent already has a Graphify block, the skill skips it (no duplication)
- Compatible with all other agent customizations
