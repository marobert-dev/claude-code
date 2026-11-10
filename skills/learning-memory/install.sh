#!/usr/bin/env bash
# Installs the learning-memory system:
#   skill      -> ~/.claude/skills/learning-memory/
#   command    -> ~/.claude/commands/learn-review.md
#   database   -> ~/.claude/learnings/learnings.db (created empty)
#   hooks      -> SessionStart, SubagentStart, SessionEnd merged into ~/.claude/settings.json
#                 (idempotent, timestamped backup in ~/.claude/learnings/backups/)
#
# Usage: bash install.sh [--no-hooks] [--dry-run] [--uninstall]
#   --no-hooks   copy files and create the database, leave settings.json alone
#   --dry-run    print the hooks that would be registered, change nothing
#   --uninstall  remove the hooks, the command and the skill (the database is kept)
#
# Env: CLAUDE_SKILLS_DIR, CLAUDE_COMMANDS_DIR override the install dirs; LEARN_PYTHON picks the interpreter.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL_DST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/learning-memory"
CMD_DST="${CLAUDE_COMMANDS_DIR:-$HOME/.claude/commands}"
CMD_SRC="$REPO_ROOT/commands/learn-review.md"

HOOKS=1; DRY=0; UNINSTALL=0
for arg in "$@"; do
  case "$arg" in
    --no-hooks) HOOKS=0 ;;
    --dry-run) DRY=1 ;;
    --uninstall) UNINSTALL=1 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

RUN="$SKILL_DST/scripts/run.sh"
[ -f "$RUN" ] || RUN="$SCRIPT_DIR/scripts/run.sh"

if [ "$UNINSTALL" = 1 ]; then
  echo "==> Removing hooks"
  bash "$RUN" uninstall-hooks || true
  rm -f "$CMD_DST/learn-review.md"
  rm -rf "$SKILL_DST"
  echo "==> Removed skill and command. The database (~/.claude/learnings/) and its backups are kept."
  exit 0
fi

if [ "$DRY" = 1 ]; then
  echo "==> Dry run: hooks that would be registered"
  bash "$SCRIPT_DIR/scripts/run.sh" install-hooks --dry-run
  exit 0
fi

echo "==> Installing skill into $SKILL_DST"
if [ "$SCRIPT_DIR" != "$SKILL_DST" ]; then
  mkdir -p "$SKILL_DST"
  cp -R "$SCRIPT_DIR/." "$SKILL_DST/"
  rm -rf "$SKILL_DST/scripts/__pycache__"
fi
chmod +x "$SKILL_DST/scripts/run.sh"

echo "==> Installing /learn-review into $CMD_DST"
if [ -f "$CMD_SRC" ]; then
  mkdir -p "$CMD_DST"
  cp "$CMD_SRC" "$CMD_DST/learn-review.md"
else
  echo "    $CMD_SRC not found (installer run outside the repo); command not installed." >&2
fi

echo "==> Creating the database"
bash "$SKILL_DST/scripts/run.sh" init

if [ "$HOOKS" = 1 ]; then
  echo "==> Registering hooks in ~/.claude/settings.json"
  bash "$SKILL_DST/scripts/run.sh" install-hooks
else
  echo "==> Hooks NOT registered (--no-hooks). Register later with: bash $SKILL_DST/scripts/run.sh install-hooks"
fi

command -v claude >/dev/null 2>&1 || echo "WARNING: 'claude' is not on PATH; the background analysis needs it (or set LEARN_CLAUDE_BIN)." >&2

echo "==> Done. Restart Claude Code so the hooks and the command are picked up."
echo "    After a session ends, its learnings appear as 'pending'; review them with /learn-review."
echo "    Diagnostics: bash ~/.claude/skills/learning-memory/scripts/run.sh status"
