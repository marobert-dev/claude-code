#!/usr/bin/env bash
# Runs product-manager as a FRESH headless session per story, so context never accumulates.
# Usage (from the workspace root):  bash scripts/run-queue.sh [max-stories]
# Env:  CLAUDE_FLAGS  extra flags, e.g. "--permission-mode acceptEdits" (set what YOUR setup needs;
#                     unattended runs cannot answer permission prompts, so pre-approve tools via
#                     .claude/settings.json permissions and/or --permission-mode).
#       PM_EXTRA      extra instruction appended to the prompt, e.g. "Git management: enabled."
# product-manager writes one line to .claude/pm-last-run.txt after each run:
#       COMPLETED <slug> | FAILED <slug> | EMPTY
set -u
MAX="${1:-1000}"
FLAGS="${CLAUDE_FLAGS:---permission-mode acceptEdits}"
STATUS=".claude/pm-last-run.txt"
mkdir -p .claude
i=0
while [ "$i" -lt "$MAX" ]; do
  rm -f "$STATUS"
  echo "[run-queue] session $((i+1))..."
  # shellcheck disable=SC2086
  claude -p "ONE STORY MODE. Process exactly the first story in .user-stories/, then checkpoint and stop. ${PM_EXTRA:-}" \
    --agent product-manager $FLAGS
  RC=$?
  LAST="$(cat "$STATUS" 2>/dev/null || echo 'UNKNOWN')"
  echo "[run-queue] claude exit=$RC status='$LAST'"
  case "$LAST" in
    COMPLETED*) i=$((i+1)) ;;
    EMPTY*)     echo "[run-queue] queue empty."; exit 0 ;;
    *)          echo "[run-queue] stopping (failure or unknown status). See .claude/handoffs/ and .claude/pm-progress.md"; exit 1 ;;
  esac
done
echo "[run-queue] reached max stories ($MAX)."
