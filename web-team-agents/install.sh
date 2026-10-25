#!/usr/bin/env bash
# Installs the web-team-agents pipeline.
#   Global (always):   copies agents/*.md into ~/.claude/agents/
#   Workspace (opt-in): pass a target workspace directory to also install the
#                        per-project helpers (hook scripts, runners, templates) there.
#
# Usage:
#   bash install.sh                  # global agents only
#   bash install.sh /path/to/app     # global agents + workspace helpers in /path/to/app
#
# Env:
#   CLAUDE_AGENTS_DIR   override the global agents install dir (default: ~/.claude/agents)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="${CLAUDE_AGENTS_DIR:-$HOME/.claude/agents}"

echo "==> Installing agents into $AGENTS_DIR"
mkdir -p "$AGENTS_DIR"
cp "$SCRIPT_DIR"/agents/*.md "$AGENTS_DIR"/
echo "    $(ls "$SCRIPT_DIR"/agents/*.md | wc -l | tr -d ' ') agent files copied."
echo "    Restart Claude Code if $AGENTS_DIR didn't already exist before this copy —"
echo "    a running session only picks up a brand-new agents directory after a restart."

HOOK_SCRIPTS="gate.sh pm-state.sh detect-conventions.sh role-guard.sh secret-scan.sh"

WORKSPACE="${1:-}"
if [ -n "$WORKSPACE" ]; then
  echo "==> Installing workspace helpers into $WORKSPACE"
  mkdir -p "$WORKSPACE/.claude/hooks" "$WORKSPACE/scripts"
  for f in $HOOK_SCRIPTS; do cp "$SCRIPT_DIR/hooks/$f" "$WORKSPACE/.claude/hooks/"; chmod +x "$WORKSPACE/.claude/hooks/$f"; done
  cp "$SCRIPT_DIR/scripts/run-queue.sh" "$SCRIPT_DIR/scripts/run-parallel.sh" "$WORKSPACE/scripts/"
  chmod +x "$WORKSPACE/scripts/run-queue.sh" "$WORKSPACE/scripts/run-parallel.sh"
  echo "    Copied $HOOK_SCRIPTS to .claude/hooks/ (the agents' frontmatter hooks call gate.sh and role-guard.sh)."
  echo "    Copied run-queue.sh, run-parallel.sh to scripts/."
  mkdir -p "$WORKSPACE/.claude/templates"
  rm -rf "$WORKSPACE/.claude/templates/user-manual" "$WORKSPACE/.claude/templates/e2e"
  cp -R "$SCRIPT_DIR/templates/user-manual" "$SCRIPT_DIR/templates/e2e" "$WORKSPACE/.claude/templates/"
  echo "    Copied the user-manual template (doc-writer) and the e2e screenshot hook (story-validator) to .claude/templates/."
  echo "    NOT auto-merged: $SCRIPT_DIR/hooks/settings.snippet.json into $WORKSPACE/.claude/settings.json"
  echo "    Back up settings.json first, then merge that snippet by hand (team-memory and pipeline-script permissions)."
  echo "    If an older snippet added a SubagentStop gate hook there, remove it: the dev agents now run the gate themselves."
else
  echo "==> No workspace directory given — skipping per-project helpers (hooks/, scripts/)."
  echo "    Re-run as: bash install.sh /path/to/your/app-repo"
fi

echo "==> Done. See README.md to queue stories (product-owner) and run the pipeline (product-manager)."
