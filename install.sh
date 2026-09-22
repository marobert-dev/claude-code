#!/usr/bin/env bash
# Installs the web-team-agents pipeline.
#   Global (always):   copies agents/*.md into ~/.claude/agents/
#   Workspace (opt-in): pass a target workspace directory to also install the
#                        per-project helpers (gate hook + scripts) there.
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

WORKSPACE="${1:-}"
if [ -n "$WORKSPACE" ]; then
  echo "==> Installing workspace helpers into $WORKSPACE"
  mkdir -p "$WORKSPACE/.claude/hooks" "$WORKSPACE/scripts"
  cp "$SCRIPT_DIR/hooks/gate.sh" "$WORKSPACE/.claude/hooks/gate.sh"
  cp "$SCRIPT_DIR/scripts/run-queue.sh" "$SCRIPT_DIR/scripts/run-parallel.sh" "$WORKSPACE/scripts/"
  chmod +x "$WORKSPACE/.claude/hooks/gate.sh" "$WORKSPACE/scripts/run-queue.sh" "$WORKSPACE/scripts/run-parallel.sh"
  echo "    Copied gate.sh, run-queue.sh, run-parallel.sh."
  echo "    NOT auto-merged: $SCRIPT_DIR/hooks/settings.snippet.json into $WORKSPACE/.claude/settings.json"
  echo "    Back up settings.json first, then merge that snippet by hand"
  echo "    (adds the gate hook + the team-memory MCP permission)."
else
  echo "==> No workspace directory given — skipping per-project helpers (hooks/, scripts/)."
  echo "    Re-run as: bash install.sh /path/to/your/app-repo"
fi

echo "==> Done. See README.md to queue stories (product-owner) and run the pipeline (product-manager)."
