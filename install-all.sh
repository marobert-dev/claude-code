#!/usr/bin/env bash
# Complete installer: web-team-agents, skills and rules into ~/.claude/
# Usage: bash install-all.sh [workspace-root]

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_SRC="$REPO_ROOT/web-team-agents/agents"
SKILLS_SRC="$REPO_ROOT/skills"
RULES_SRC="$REPO_ROOT/rules"
AGENTS_DST="$HOME/.claude/agents"
SKILLS_DST="$HOME/.claude/skills"
RULES_DST="$HOME/.claude/rules"
WORKSPACE="${1:-.}"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Claude Code Agents & Skills Installer ===${NC}\n"

# Check sources exist
if [ ! -d "$AGENTS_SRC" ]; then
  echo -e "${YELLOW}Error: $AGENTS_SRC not found${NC}"
  exit 1
fi

if [ ! -d "$SKILLS_SRC" ]; then
  echo -e "${YELLOW}Error: $SKILLS_SRC not found${NC}"
  exit 1
fi

# Create directories
mkdir -p "$AGENTS_DST"
mkdir -p "$SKILLS_DST"
mkdir -p "$RULES_DST"

echo -e "${BLUE}Installing agents...${NC}"
cp "$AGENTS_SRC"/*.md "$AGENTS_DST/"
AGENT_COUNT=$(ls -1 "$AGENTS_DST"/*.md 2>/dev/null | wc -l)
echo -e "${GREEN}✓ Installed $AGENT_COUNT agents${NC}\n"

echo -e "${BLUE}Installing skills...${NC}"
SKILL_COUNT=0
for skill_dir in "$SKILLS_SRC"/*/; do
  [ -f "$skill_dir/SKILL.md" ] || continue
  skill_name="$(basename "$skill_dir")"
  mkdir -p "$SKILLS_DST/$skill_name"
  cp -R "$skill_dir." "$SKILLS_DST/$skill_name/"
  echo -e "  - $skill_name"
  SKILL_COUNT=$((SKILL_COUNT + 1))
done
echo -e "${GREEN}✓ Installed $SKILL_COUNT skills${NC}\n"

echo -e "${BLUE}Installing rules...${NC}"
if [ -d "$RULES_SRC" ] && [ -n "$(find "$RULES_SRC" -name '*.md' -type f 2>/dev/null)" ]; then
  cp -R "$RULES_SRC/." "$RULES_DST/"
  RULE_COUNT=$(find "$RULES_SRC" -name '*.md' -type f | wc -l | tr -d ' ')
  echo -e "${GREEN}✓ Installed $RULE_COUNT rules${NC}\n"
else
  echo -e "${YELLOW}No rules found in $RULES_SRC - skipped${NC}\n"
fi

# Optional: install workspace helpers
if [ "$WORKSPACE" != "." ]; then
  echo -e "${BLUE}Installing workspace helpers into $WORKSPACE...${NC}"
  mkdir -p "$WORKSPACE/.claude/hooks" "$WORKSPACE/scripts"

  if [ -f "$REPO_ROOT/web-team-agents/hooks/gate.sh" ]; then
    cp "$REPO_ROOT/web-team-agents/hooks/gate.sh" "$WORKSPACE/.claude/hooks/"
    echo -e "${GREEN}✓ Copied gate.sh${NC}"
  fi

  if [ -f "$REPO_ROOT/web-team-agents/scripts/run-queue.sh" ]; then
    cp "$REPO_ROOT/web-team-agents/scripts/run-queue.sh" "$WORKSPACE/scripts/"
    echo -e "${GREEN}✓ Copied run-queue.sh${NC}"
  fi

  if [ -f "$REPO_ROOT/web-team-agents/scripts/run-parallel.sh" ]; then
    cp "$REPO_ROOT/web-team-agents/scripts/run-parallel.sh" "$WORKSPACE/scripts/"
    echo -e "${GREEN}✓ Copied run-parallel.sh${NC}"
  fi

  if [ -f "$REPO_ROOT/web-team-agents/scripts/enable-graphify.sh" ]; then
    cp "$REPO_ROOT/web-team-agents/scripts/enable-graphify.sh" "$WORKSPACE/scripts/"
    chmod +x "$WORKSPACE/scripts/enable-graphify.sh"
    echo -e "${GREEN}✓ Copied enable-graphify.sh${NC}"
  fi

  echo ""
fi

echo -e "${BLUE}=== Installation Complete ===${NC}\n"
echo -e "Location of installed components:"
echo -e "  Agents:     ${GREEN}$AGENTS_DST${NC}"
echo -e "  Skills:     ${GREEN}$SKILLS_DST${NC}"
echo -e "  Rules:      ${GREEN}$RULES_DST${NC}"

if [ "$WORKSPACE" != "." ]; then
  echo -e "  Workspace:  ${GREEN}$WORKSPACE${NC}"
fi

echo ""
echo -e "Next steps:"
echo -e "  1. ${YELLOW}Restart Claude Code${NC} if ~/.claude/agents/, skills/ or rules/ was newly created"
echo -e "  2. ${YELLOW}Queue stories${NC}: ${BLUE}claude --agent product-owner${NC}"
echo -e "  3. ${YELLOW}Process queue${NC}: ${BLUE}claude --agent product-manager${NC}"
echo -e "  4. ${YELLOW}(Optional) Enable Graphify${NC}: ${BLUE}bash scripts/enable-graphify.sh --backup${NC}"
echo ""
echo -e "For SSH setup, see: https://claude.ai/artifact/Y2ncJTckHk8Bdpt2FuoPgv"
echo ""
