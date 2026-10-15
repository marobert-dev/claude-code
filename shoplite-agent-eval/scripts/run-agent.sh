#!/usr/bin/env bash
# Run one agent headless inside a run: scripts/run-agent.sh <run-dir> [agent] [--dry-run]
#
# The agent defaults to task.json "agent". The prompt is tasks/<TASK-ID>/prompt.txt, sent verbatim.
# Raw output goes to $EVAL_RUNS_DIR/.meta/<run>/claude-output.json while the agent works (outside its workspace);
# metrics are written to <run-dir>/.eval/metrics.json and the final report to <run-dir>/.eval/agent-report.md.
#
# Env: EVAL_ALLOWED_TOOLS (space-separated, overrides the default list), EVAL_CLAUDE_FLAGS (extra flags,
#      e.g. "--model sonnet"), EVAL_TIMEOUT (seconds, default 5400).
# Tested with Claude Code 2.1.299 (`claude --help`: -p/--print, --agent, --output-format json,
# --permission-mode acceptEdits, --allowedTools, --no-session-persistence).
set -euo pipefail
# shellcheck source=lib/common.sh
. "$(dirname "$0")/lib/common.sh"

RUN="${1:-}"
[ -d "$RUN/.git" ] || die "usage: run-agent.sh <run-dir> [agent] [--dry-run]"
RUN="$(cd "$RUN" && pwd)"
shift
AGENT=""; DRY=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    -*) die "unknown option $arg" ;;
    *) AGENT="$arg" ;;
  esac
done

META="$(meta_dir_of "$RUN")"
TASK="$(evalkit task-field "$META/run.json" task)"
[ -n "$TASK" ] || die "no run metadata in $META (create runs with new-run.sh)"
TASK_DIR="$KIT/tasks/$TASK"
[ -n "$AGENT" ] || AGENT="$(task_field "$TASK" agent)"
PROMPT_FILE="$TASK_DIR/prompt.txt"
[ -f "$PROMPT_FILE" ] || die "missing $PROMPT_FILE"

DEFAULT_TOOLS="Read Edit Write Glob Grep TodoWrite Agent WebSearch WebFetch mcp__team-memory \
Bash(dotnet:*) Bash(npm:*) Bash(npx:*) Bash(node:*) Bash(git:*) Bash(bash:*) Bash(ls:*) Bash(cat:*) \
Bash(head:*) Bash(tail:*) Bash(find:*) Bash(grep:*) Bash(mkdir:*) Bash(cp:*) Bash(mv:*) Bash(rm:*) Bash(which:*) \
Bash(command:*) Bash(test:*) Bash(wc:*) Bash(sort:*) Bash(diff:*) Bash(date:*) Bash(echo:*) Bash(curl:*) \
Bash(gitleaks:*) Bash(semgrep:*) Bash(schemathesis:*) Bash(oasdiff:*) Bash(osv-scanner:*)"
read -r -a TOOLS <<< "${EVAL_ALLOWED_TOOLS:-$DEFAULT_TOOLS}"
read -r -a EXTRA <<< "${EVAL_CLAUDE_FLAGS:-}"

CLAUDE_VERSION="$(claude --version 2>/dev/null | head -n1 || echo unknown)"
AGENTS_SHA="$(git -C "$WEB_TEAM_AGENTS_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
AGENT_FILE="$HOME/.claude/agents/$AGENT.md"
AGENT_FILE_SHA="$( [ -f "$AGENT_FILE" ] && sha256sum "$AGENT_FILE" | cut -c1-12 || echo missing)"
[ -f "$RUN/.claude/agents/$AGENT.md" ] && die "$RUN/.claude/agents/$AGENT.md would shadow the global agent under test"

CMD=(claude -p "$(cat "$PROMPT_FILE")" --agent "$AGENT" --output-format json --permission-mode acceptEdits
     --no-session-persistence "${EXTRA[@]}" --allowedTools "${TOOLS[@]}")

if [ "$DRY" = 1 ]; then
  printf 'cd %q\n' "$RUN"
  printf '%q ' "${CMD[@]}"; printf '\n'
  exit 0
fi

info "running $AGENT on $TASK ($(basename "$RUN")), Claude Code $CLAUDE_VERSION, agents $AGENTS_SHA"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
START=$(date +%s)
set +e
( cd "$RUN" && timeout "${EVAL_TIMEOUT:-5400}" "${CMD[@]}" ) > "$META/claude-output.json" 2> "$META/claude-stderr.log"
EXIT=$?
set -e
END=$(date +%s)

mkdir -p "$RUN/.eval"
evalkit metrics "$META/claude-output.json" "$RUN/.eval/metrics.json" "$RUN/.eval/agent-report.md" \
  "$AGENT" "$EXIT" "$((END - START))" "$CLAUDE_VERSION" "$AGENTS_SHA" "$AGENT_FILE_SHA" "$STARTED_AT"
cp "$META/claude-output.json" "$RUN/.eval/claude-output.json"
cp "$META/claude-stderr.log" "$RUN/.eval/claude-stderr.log"

info "agent exited with $EXIT; metrics in $RUN/.eval/metrics.json"
[ "$EXIT" = 0 ] || exit "$EXIT"
