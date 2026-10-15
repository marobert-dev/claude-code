#!/usr/bin/env bash
# Deterministic quality gate: lint + typecheck + build + unit tests, no LLM involved.
# Used two ways:
#   1. SubagentStop hook for dev-frontend / dev-backend / dev-integrator (stdin = hook JSON).
#      Exit 2 = the subagent is told to keep working (stderr is fed back to it).
#   2. Called by product-manager before every code-reviewer round:  bash .claude/hooks/gate.sh
#      Any non-zero exit = failure; stderr holds a short report to hand back to the dev agent.
# Override everything with a project script: .claude/gate.local.sh (run instead of auto-detection).
# Env: GATE_SKIP_BUILD=1 to skip builds, GATE_SKIP_TESTS=1 to skip tests, GATE_MAX_BLOCKS (default 3).

set -u
ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$ROOT" || exit 0

# --- hook mode: read stdin JSON if piped ---------------------------------------------------
AGENT_TYPE=""; AGENT_ID=""
if [ ! -t 0 ]; then
  INPUT="$(cat || true)"
  if [ -n "$INPUT" ] && command -v jq >/dev/null 2>&1; then
    AGENT_TYPE="$(printf '%s' "$INPUT" | jq -r '.agent_type // empty' 2>/dev/null)"
    AGENT_ID="$(printf '%s' "$INPUT" | jq -r '.agent_id // empty' 2>/dev/null)"
  fi
fi
if [ -n "$AGENT_TYPE" ]; then
  case "$AGENT_TYPE" in
    dev-frontend|dev-backend|dev-integrator) ;;
    *) exit 0 ;;   # only gate the implementers
  esac
fi

# --- loop guard: never block the same subagent more than N times ---------------------------
MAX="${GATE_MAX_BLOCKS:-3}"
COUNTER=""
if [ -n "$AGENT_ID" ]; then
  COUNTER="${TMPDIR:-/tmp}/gate-${AGENT_ID}.count"
  N=$(cat "$COUNTER" 2>/dev/null || echo 0)
  if [ "$N" -ge "$MAX" ]; then
    echo "gate: blocked $N times already for $AGENT_ID — letting it stop; product-manager gate will re-check." >&2
    exit 0
  fi
fi

# --- project override ---------------------------------------------------------------------
if [ -f .claude/gate.local.sh ]; then
  OUT="$(bash .claude/gate.local.sh 2>&1)"; RC=$?
  if [ $RC -ne 0 ]; then
    [ -n "$COUNTER" ] && echo $(( ${N:-0} + 1 )) > "$COUNTER"
    printf 'GATE FAILED (.claude/gate.local.sh):\n%s\n' "$(printf '%s' "$OUT" | tail -n 40)" >&2
    exit 2
  fi
  exit 0
fi

FAIL=""
run_step () {  # $1=label  $2=dir  $3...=command
  local label="$1" dir="$2"; shift 2
  local out rc
  out="$(cd "$dir" && "$@" 2>&1)"; rc=$?
  if [ $rc -ne 0 ]; then
    FAIL="${FAIL}--- ${label} (${dir}) FAILED ---
$(printf '%s' "$out" | tail -n 40)
"
  fi
}

# --- discover project dirs: root + immediate subdirs --------------------------------------
DIRS=". $(find . -mindepth 1 -maxdepth 1 -type d ! -name '.*' ! -name node_modules ! -name docs -printf '%f ' 2>/dev/null)"
for d in $DIRS; do
  # Node / React / React Native
  if [ -f "$d/package.json" ] && command -v npm >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
    has () { jq -e --arg s "$1" '.scripts[$s] // empty' "$d/package.json" >/dev/null 2>&1; }
    has lint      && run_step "npm lint"      "$d" npm run --silent lint
    if has typecheck; then run_step "npm typecheck" "$d" npm run --silent typecheck
    elif [ -f "$d/tsconfig.json" ] && [ -x "$d/node_modules/.bin/tsc" ]; then run_step "tsc --noEmit" "$d" ./node_modules/.bin/tsc --noEmit; fi
    [ -z "${GATE_SKIP_BUILD:-}" ] && has build && run_step "npm build" "$d" npm run --silent build
    [ -z "${GATE_SKIP_TESTS:-}" ] && has test  && run_step "npm test"  "$d" env CI=true npm test --silent
  fi
  # .NET
  if command -v dotnet >/dev/null 2>&1 && ls "$d"/*.sln "$d"/*.csproj >/dev/null 2>&1; then
    run_step "dotnet build" "$d" dotnet build --nologo -v q
    [ -z "${GATE_SKIP_TESTS:-}" ] && run_step "dotnet test" "$d" dotnet test --nologo --no-build -v q
  fi
done

if [ -n "$FAIL" ]; then
  [ -n "$COUNTER" ] && echo $(( ${N:-0} + 1 )) > "$COUNTER"
  printf 'GATE FAILED — fix these before finishing:\n%s' "$FAIL" >&2
  exit 2
fi
[ -n "$COUNTER" ] && rm -f "$COUNTER"
echo "gate: OK"
exit 0
