#!/usr/bin/env bash
# Deterministic quality gate: lint + typecheck + build + unit tests, no LLM involved.
# Used two ways:
#   1. Stop hook in the frontmatter of dev-frontend / dev-backend / dev-integrator (a SubagentStop hook when they run
#      as subagents; the same command also works from settings.json). stdin = hook JSON.
#      Exit 2 = the agent is told to keep working (stderr is fed back to it).
#   2. Called by product-manager before every code-reviewer round:  bash .claude/hooks/gate.sh < /dev/null
#      Any non-zero exit = failure; stderr holds a short report to hand back to the dev agent.
# Override everything with a project script: .claude/gate.local.sh (run instead of auto-detection).
# A project the gate cannot check (package.json without npm, or without jq/node to read it; a .NET solution without
# dotnet) fails as NOT CHECKED instead of passing silently.
# A pass is remembered in .pipeline/gate-pass by a fingerprint of the code (every covered git repo:
# HEAD, uncommitted diff, untracked files); the next call on unchanged code passes without re-running,
# since a dev agent, its Stop hook and product-manager otherwise gate the same tree back to back.
# Env: GATE_SKIP_BUILD=1 to skip builds, GATE_SKIP_TESTS=1 to skip tests, GATE_MAX_BLOCKS (default 3),
#      GATE_NO_CACHE=1 to always re-run.

set -u
ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$ROOT" || exit 0

# Reads one top-level string field of the hook JSON, with jq or, without it, node.
json_field () {
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$INPUT" | jq -r --arg k "$1" '.[$k] // empty' 2>/dev/null
  elif command -v node >/dev/null 2>&1; then
    printf '%s' "$INPUT" | node -e 'let d="";process.stdin.on("data",c=>d+=c).on("end",()=>{try{const v=JSON.parse(d)[process.argv[1]];if(v!=null)process.stdout.write(String(v))}catch(e){}})' "$1" 2>/dev/null
  fi
}

# --- hook mode: read stdin JSON if piped ---------------------------------------------------
AGENT_TYPE=""; GUARD_ID=""
if [ ! -t 0 ]; then
  INPUT="$(cat || true)"
  if [ -n "$INPUT" ]; then
    AGENT_TYPE="$(json_field agent_type)"
    # A subagent has an agent_id; an agent run as the session itself (claude --agent) only has its session_id.
    GUARD_ID="$(json_field agent_id)"; [ -n "$GUARD_ID" ] || GUARD_ID="$(json_field session_id)"
  fi
fi
if [ -n "$AGENT_TYPE" ]; then
  case "$AGENT_TYPE" in
    dev-frontend|dev-backend|dev-integrator) ;;
    *) exit 0 ;;   # only gate the implementers
  esac
fi

# --- loop guard: never block the same agent more than N times ------------------------------
MAX="${GATE_MAX_BLOCKS:-3}"
COUNTER=""
if [ -n "$GUARD_ID" ]; then
  COUNTER="${TMPDIR:-/tmp}/gate-${GUARD_ID//[^A-Za-z0-9_-]/_}.count"
  N=$(cat "$COUNTER" 2>/dev/null || echo 0)
  if [ "$N" -ge "$MAX" ]; then
    echo "gate: blocked $N times already for $GUARD_ID — letting it stop; product-manager gate will re-check." >&2
    exit 0
  fi
fi

# --- discover project dirs: root + immediate subdirs --------------------------------------
DIRS=". $(find . -mindepth 1 -maxdepth 1 -type d ! -name '.*' ! -name node_modules ! -name docs -printf '%f ' 2>/dev/null)"

# --- pass cache ---------------------------------------------------------------------------
CACHE=".pipeline/gate-pass"
# Coordination state changes between calls without changing the code (README "Files produced").
UNGATED=(':(exclude).pipeline' ':(exclude).user-stories' ':(exclude).stories-reviewed' ':(exclude).validated-stories'
         ':(exclude).completed' ':(exclude).decisions' ':(exclude).claude/run.log' ':(exclude)docs')

fingerprint () {  # prints nothing when no covered dir is in a git repo: no cache then
  local tops top f
  tops="$(for d in $DIRS; do git -C "$d" rev-parse --show-toplevel 2>/dev/null; done | sort -u)"
  [ -n "$tops" ] || return 0
  {
    echo "skip-build=${GATE_SKIP_BUILD:-} skip-tests=${GATE_SKIP_TESTS:-}"
    [ -f .claude/gate.local.sh ] && git hash-object .claude/gate.local.sh
    printf '%s\n' "$tops" | while IFS= read -r top; do
      echo "repo $top $(git -C "$top" rev-parse HEAD 2>/dev/null)"
      git -C "$top" diff HEAD --binary -- . "${UNGATED[@]}" 2>/dev/null
      git -C "$top" ls-files --others --exclude-standard -- . "${UNGATED[@]}" 2>/dev/null | while IFS= read -r f; do
        echo "untracked $f $(git -C "$top" hash-object -- "$f" 2>/dev/null)"
      done
    done
  } | git hash-object --stdin
}

FINGERPRINT=""
[ -z "${GATE_NO_CACHE:-}" ] && FINGERPRINT="$(fingerprint)"
if [ -n "$FINGERPRINT" ] && [ "$(cat "$CACHE" 2>/dev/null)" = "$FINGERPRINT" ]; then
  [ -n "$COUNTER" ] && rm -f "$COUNTER"
  echo "gate: OK (unchanged since the last pass)"
  exit 0
fi

pass () {
  [ -n "$COUNTER" ] && rm -f "$COUNTER"
  # Only the workspace root has .pipeline/; a gate run from a subfolder must not leave a stray cache there.
  [ -n "$FINGERPRINT" ] && [ -d .pipeline ] && echo "$FINGERPRINT" > "$CACHE"
  echo "gate: OK"
  exit 0
}

# --- project override ---------------------------------------------------------------------
if [ -f .claude/gate.local.sh ]; then
  OUT="$(bash .claude/gate.local.sh 2>&1)"; RC=$?
  if [ $RC -ne 0 ]; then
    [ -n "$COUNTER" ] && echo $(( ${N:-0} + 1 )) > "$COUNTER"
    printf 'GATE FAILED (.claude/gate.local.sh):\n%s\n' "$(printf '%s' "$OUT" | tail -n 40)" >&2
    exit 2
  fi
  pass
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
not_checked () {  # $1=dir  $2=what is missing
  FAIL="${FAIL}--- ${1} NOT CHECKED: ${2} ---
"
}

for d in $DIRS; do
  # Node / React / React Native
  if [ -f "$d/package.json" ]; then
    if ! command -v npm >/dev/null 2>&1; then
      not_checked "$d" "npm is required to run its package.json scripts"
    elif ! command -v jq >/dev/null 2>&1 && ! command -v node >/dev/null 2>&1; then
      not_checked "$d" "jq or node is required to read its package.json scripts"
    else
      if command -v jq >/dev/null 2>&1; then
        has () { jq -e --arg s "$1" '.scripts[$s] // empty' "$d/package.json" >/dev/null 2>&1; }
      else
        has () { node -e 'const p=require(require("path").resolve(process.argv[1],"package.json"));process.exit(p.scripts&&p.scripts[process.argv[2]]?0:1)' "$d" "$1" >/dev/null 2>&1; }
      fi
      has lint      && run_step "npm lint"      "$d" npm run --silent lint
      if has typecheck; then run_step "npm typecheck" "$d" npm run --silent typecheck
      elif [ -f "$d/tsconfig.json" ] && [ -x "$d/node_modules/.bin/tsc" ]; then run_step "tsc --noEmit" "$d" ./node_modules/.bin/tsc --noEmit; fi
      [ -z "${GATE_SKIP_BUILD:-}" ] && has build && run_step "npm build" "$d" npm run --silent build
      [ -z "${GATE_SKIP_TESTS:-}" ] && has test  && run_step "npm test"  "$d" env CI=true npm test --silent
    fi
  fi
  # .NET (a folder may hold a .sln without any .csproj, or the reverse)
  if { compgen -G "$d/*.sln" || compgen -G "$d/*.slnx" || compgen -G "$d/*.csproj"; } >/dev/null; then
    if ! command -v dotnet >/dev/null 2>&1; then
      not_checked "$d" "dotnet is required to build and test it"
    else
      run_step "dotnet build" "$d" dotnet build --nologo -v q
      [ -z "${GATE_SKIP_TESTS:-}" ] && run_step "dotnet test" "$d" dotnet test --nologo --no-build -v q
    fi
  fi
done

if [ -n "$FAIL" ]; then
  [ -n "$COUNTER" ] && echo $(( ${N:-0} + 1 )) > "$COUNTER"
  printf 'GATE FAILED — fix these before finishing:\n%s' "$FAIL" >&2
  exit 2
fi
pass
