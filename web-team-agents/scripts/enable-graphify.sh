#!/usr/bin/env bash
# Enable Graphify integration in all development agents
# Usage: bash scripts/enable-graphify.sh [--backup] [--remove]

set -u

BACKUP=${1:---backup}
AGENTS_DIR="${HOME}/.claude/agents"
BACKUP_DIR="${AGENTS_DIR}-graphify-backup-$(date +%s)"

# Graphify blocks to inject (templates). Only the planners and the scout read the full report;
# every other agent queries on demand, since it may be invoked many times per story.
READS_REPORT=" analyst product-owner conventions-scout "
read -r -d '' GRAPHIFY_BLOCK << 'EOF' || true

Before anything else, check whether `graphify-out/` exists in the workspace. If it does, read `graphify-out/GRAPH_REPORT.md` for a high-level architecture summary, and run `graphify query "<question>"` via Bash whenever you need to know what a file or symbol depends on, or is depended on by, before {{ACTION}}. If Graphify isn't set up for this project, skip this and proceed without it.
EOF
read -r -d '' GRAPHIFY_QUERY_BLOCK << 'EOF' || true
Before anything else, check whether `graphify-out/` exists in the workspace. If it does, run `graphify query "<question>"` via Bash whenever you need to know what a file or symbol depends on, or is depended on by, before {{ACTION}} — query only what you need; don't read `graphify-out/GRAPH_REPORT.md` in full. If Graphify isn't set up for this project, skip this and proceed without it.
EOF

# Agent-specific actions
declare -A ACTIONS=(
  [product-manager]="routing work"
  [analyst]="deciding on the plan"
  [code-reviewer]="judging the wider impact of a change"
  [conventions-scout]="writing conventions"
  [dev-backend]="changing it"
  [dev-frontend]="changing it"
  [dev-integrator]="wiring it"
  [security-reviewer]="assessing the risks"
  [story-validator]="validating the story"
  [unit-tester]="writing tests"
  [doc-writer]="writing docs"
  [product-owner]="writing stories"
)

if [ "$BACKUP" == "--remove" ]; then
  echo "Removing Graphify blocks from agents..."
  for agent in "${!ACTIONS[@]}"; do
    file="$AGENTS_DIR/${agent}.md"
    if [ -f "$file" ]; then
      # Remove Graphify block (lines starting from "Before anything else" to empty line after it)
      sed -i '/^Before anything else, check whether `graphify-out\/`/,/^$/d' "$file"
      echo "  ✓ Removed from $agent.md"
    fi
  done
  echo "Graphify blocks removed. Agents restored to minimal state."
  exit 0
fi

if [ ! -d "$AGENTS_DIR" ]; then
  echo "Error: $AGENTS_DIR does not exist. Install agents first: bash install.sh"
  exit 1
fi

if [ "$BACKUP" == "--backup" ]; then
  echo "Backing up agents to $BACKUP_DIR..."
  cp -r "$AGENTS_DIR" "$BACKUP_DIR"
  echo "  ✓ Backup saved"
fi

echo "Enabling Graphify integration in agents..."
for agent in "${!ACTIONS[@]}"; do
  file="$AGENTS_DIR/${agent}.md"
  if [ ! -f "$file" ]; then
    echo "  ⚠ Skipping $agent.md (not found)"
    continue
  fi

  # Check if Graphify block already exists
  if grep -q "Before anything else, check whether \`graphify-out/\`" "$file"; then
    echo "  ✓ $agent.md already has Graphify (skipped)"
    continue
  fi

  action="${ACTIONS[$agent]}"
  block="$GRAPHIFY_QUERY_BLOCK"
  [[ "$READS_REPORT" == *" $agent "* ]] && block="$GRAPHIFY_BLOCK"
  graphify_text=$(echo "$block" | sed "s|{{ACTION}}|$action|")

  # Insert block after frontmatter (after ---)
  # Find line number of second ---
  line=$(grep -n '^---$' "$file" | tail -1 | cut -d: -f1)
  if [ -z "$line" ]; then
    echo "  ✗ Could not find frontmatter end in $agent.md"
    continue
  fi

  # Insert the block
  sed -i "${line}a\\${graphify_text}" "$file"
  echo "  ✓ Injected into $agent.md"
done

echo "Done! All agents now support Graphify."
echo "When graphify-out/ exists in your workspace, agents will use it for architecture queries."
