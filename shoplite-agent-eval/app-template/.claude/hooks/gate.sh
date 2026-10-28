#!/usr/bin/env bash
# Deterministic quality gate: lint + typecheck + build + unit tests, no LLM involved.
# Used two ways:
#   1. SubagentStop hook for dev-frontend / dev-backend / dev-integrator, declared once in the project's
#      .claude/settings.json (hooks/settings.snippet.json; stdin = hook JSON). SCOPED: only the packages with changes
#      since HEAD (a package outside git is checked whole), and in them only the tests related to the changed files
#      (no e2e, no full suite), so it ends well before the 600 s stream watchdog.
#      Exit 2 = the subagent is told to keep working (stderr is fed back to it).
#   2. Called by product-manager once per story, before the commit:  bash .claude/hooks/gate.sh --full < /dev/null
#      FULL: every package, lint + typecheck + build + the project's whole test script (`npm test`, `dotnet test`).
#      Can take many minutes: run it in the background. Any non-zero exit = failure; stderr holds a short report.
#      A package that defines both `test:unit` and `test:e2e` scripts and whose `test` is a single command (the two
#      scripts are taken to partition it) gets them as two separate steps, each with its own time limit and failure
#      label; any other package runs `npm test` whole, so nothing a chained `test` declares is dropped.
# One gate at a time per repository: a second call waits for the running one and reuses its answer when the code is
# unchanged. Every step has a time limit, and whenever the gate exits it kills the process tree it started.
# Override everything with a project script: .claude/gate.local.sh (run instead of auto-detection; GATE_MODE says which).
# A project the gate cannot check (package.json without npm, or without jq/node to read it; a .NET solution without
# dotnet) fails as NOT CHECKED instead of passing silently.
# A pass is remembered in .pipeline/gate-pass by a fingerprint of the code (every covered git repo: HEAD, uncommitted
# diff, untracked files) and the mode; the next call on unchanged code passes without re-running (a full pass also
# covers a scoped call). Failures are never remembered.
# Env: GATE_SKIP_BUILD=1 to skip builds, GATE_SKIP_TESTS=1 to skip tests, GATE_MAX_BLOCKS (default 3),
#      GATE_NO_CACHE=1 to always re-run (no remembered pass, no reuse of another gate's answer),
#      GATE_STEP_TIMEOUT / GATE_BUDGET / GATE_LOCK_WAIT in seconds (scoped 200 / 270 / 180, full 1800 / 3600 / 3600),
#      GATE_TEST_ARGS = extra arguments for the scoped jest / vitest run,
#      GATE_SCOPED_MAX_TESTS (default 10) = most jest test files the scoped gate runs for the files that changed; a change
#      reaching more of them (a widely imported file) runs only the test files that changed themselves, and the rest is
#      left to the --full gate instead of running past the time budget. Unit tests of .NET projects run in --full only.
# Journal: .pipeline/gate.log, one line per start / wait / reuse / cached / end, with the process id.

set -u
ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$ROOT" || exit 0

MODE=scoped
for arg in "$@"; do [ "$arg" = "--full" ] && MODE=full; done
export GATE_MODE="$MODE"
if [ "$MODE" = full ]; then
  STEP_TIMEOUT="${GATE_STEP_TIMEOUT:-1800}"; BUDGET="${GATE_BUDGET:-3600}"; LOCK_WAIT="${GATE_LOCK_WAIT:-3600}"
else
  STEP_TIMEOUT="${GATE_STEP_TIMEOUT:-200}";  BUDGET="${GATE_BUDGET:-270}";  LOCK_WAIT="${GATE_LOCK_WAIT:-180}"
fi
# The reports go back to a model: ANSI colors only cost tokens. FORCE_COLOR wins over NO_COLOR in chalk-based tools.
export NO_COLOR=1 FORCE_COLOR=0

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
    echo "gate: blocked $N times already for $GUARD_ID — letting it stop; the --full gate before the commit will re-check." >&2
    exit 0
  fi
fi

# --- discover project dirs: root + immediate subdirs --------------------------------------
DIRS=". $(find . -mindepth 1 -maxdepth 1 -type d ! -name '.*' ! -name node_modules ! -name docs -printf '%f ' 2>/dev/null)"
is_node ()   { [ -f "$1/package.json" ]; }
is_dotnet () { { compgen -G "$1/*.sln" || compgen -G "$1/*.slnx" || compgen -G "$1/*.csproj"; } >/dev/null; }

# --- journal -------------------------------------------------------------------------------
log () {
  [ -d .pipeline ] || return 0
  printf '%s pid=%s winpid=%s mode=%s agent=%s %s\n' "$(date +%Y-%m-%dT%H:%M:%S)" "$$" \
    "$(cat /proc/$$/winpid 2>/dev/null || echo "$$")" "$MODE" "${AGENT_TYPE:-direct}" "$*" >> .pipeline/gate.log
}

# --- cleanup: runs on every exit, Ctrl-C and SIGTERM ----------------------------------------
# Kills one process the gate started and everything below it, never anything else (not the Claude Code process).
kill_tree () {
  local pid="$1" child
  [ -n "$pid" ] && [ "$pid" != "$$" ] || return 0
  if [ -r "/proc/$pid/winpid" ] && command -v taskkill >/dev/null 2>&1; then
    MSYS_NO_PATHCONV=1 taskkill /F /T /PID "$(cat "/proc/$pid/winpid")" >/dev/null 2>&1
  else
    for child in $(pgrep -P "$pid" 2>/dev/null); do kill_tree "$child"; done
    kill -KILL "$pid" 2>/dev/null
  fi
}
STEP_PID=""; STEP_OUT=""; LOCK_OWNED=0; STARTED_AT=""
cleanup () {
  local rc=$?
  [ -n "$STEP_PID" ] && kill -0 "$STEP_PID" 2>/dev/null && kill_tree "$STEP_PID"
  [ -n "$STEP_OUT" ] && rm -f "$STEP_OUT"
  [ -n "$STARTED_AT" ] && log "event=end rc=$rc dur=$(( $(date +%s) - STARTED_AT ))s"
  [ "$LOCK_OWNED" = 1 ] && rm -rf "$LOCK"
  return $rc
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# --- fingerprint of the code under test ------------------------------------------------------
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
refresh_fingerprint () { FINGERPRINT=""; [ -z "${GATE_NO_CACHE:-}" ] && FINGERPRINT="$(fingerprint)"; }

# The cache holds "<fingerprint> <mode>"; an entry without a mode comes from the single-mode gate, which ran everything.
cached_pass () {
  local fp mode
  [ -n "$FINGERPRINT" ] || return 1
  set -- $(cat "$CACHE" 2>/dev/null); fp="${1:-}"; mode="${2:-full}"
  [ "$fp" = "$FINGERPRINT" ] && { [ "$mode" = "$MODE" ] || [ "$mode" = full ]; }
}
answer_from_cache () {
  cached_pass || return 1
  [ -n "$COUNTER" ] && rm -f "$COUNTER"
  log "event=cached"
  echo "gate: OK (unchanged since the last pass)"
  exit 0
}

refresh_fingerprint
answer_from_cache

# --- one gate at a time per repository -------------------------------------------------------
TOP="$(git rev-parse --show-toplevel 2>/dev/null || pwd -P)"
STATE="${TMPDIR:-/tmp}/gate-repo-$(printf '%s' "$TOP" | cksum | cut -d' ' -f1)"
LOCK="$STATE.lock"; RESULT="$STATE.result"
WAITED=0; WAIT_STARTED=$(date +%s)

acquire_lock () {  # returns 1 when the running gate outlasts GATE_LOCK_WAIT
  local info pid mode
  until mkdir "$LOCK" 2>/dev/null; do
    info="$(cat "$LOCK/info" 2>/dev/null)"; set -- $info; pid="${1:-}"; mode="${2:-?}"
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then rm -rf "$LOCK"; continue; fi   # holder died
    if [ -z "$pid" ] && [ -n "$(find "$LOCK" -maxdepth 0 -mmin +1 2>/dev/null)" ]; then rm -rf "$LOCK"; continue; fi
    if [ "$WAITED" -eq 0 ]; then WAITED=1; log "event=wait holder=${pid:-?} holder_mode=$mode"; fi
    [ $(( $(date +%s) - WAIT_STARTED )) -ge "$LOCK_WAIT" ] && return 1
    sleep 2
  done
  echo "$$ $MODE $(date +%s)" > "$LOCK/info"
  LOCK_OWNED=1
}

# The gate we waited for answered for the same code: its answer is ours (a full pass also covers a scoped call).
reuse_result () {
  local line fp mode rc ended
  [ -f "$RESULT" ] || return 1
  line="$(head -n 1 "$RESULT")"; set -- $line; fp="${1:-}"; mode="${2:-}"; rc="${3:-}"; ended="${4:-0}"
  [ "$ended" -ge "$WAIT_STARTED" ] || return 1
  [ "$mode" = "$MODE" ] || { [ "$mode" = full ] && [ "$rc" = 0 ]; } || return 1
  [ -n "$fp" ] && [ "$fp" = "$FINGERPRINT" ] || return 1
  log "event=reuse of_mode=$mode rc=$rc"
  if [ "$rc" = 0 ]; then
    echo "gate: reused the result of the $mode gate that was running"
    echo "gate: OK"
    exit 0
  fi
  [ -n "$COUNTER" ] && echo $(( ${N:-0} + 1 )) > "$COUNTER"
  tail -n +2 "$RESULT" >&2
  exit 2
}

if ! acquire_lock; then
  echo "gate: another gate has been running for more than ${LOCK_WAIT}s ($(cat "$LOCK/info" 2>/dev/null)); not run for this stop — the --full gate before the commit covers it." >&2
  exit 0
fi
if [ "$WAITED" -eq 1 ]; then
  refresh_fingerprint   # the code may have changed while we waited
  answer_from_cache
  reuse_result
fi
STARTED_AT=$(date +%s)
DEADLINE=$(( STARTED_AT + BUDGET ))
log "event=start budget=${BUDGET}s step_timeout=${STEP_TIMEOUT}s"

# --- steps ------------------------------------------------------------------------------------
FAIL=""
run_step () {  # $1=label  $2=dir  $3...=command; at most STEP_TIMEOUT seconds, and no more than what is left of BUDGET
  local label="$1" dir="$2" limit waited=0 timed_out=0 rc
  shift 2
  limit=$(( DEADLINE - $(date +%s) )); [ "$limit" -gt "$STEP_TIMEOUT" ] && limit=$STEP_TIMEOUT
  if [ "$limit" -le 0 ]; then
    FAIL="${FAIL}--- ${label} (${dir}) NOT RUN: the ${BUDGET}s budget of the ${MODE} gate is used up ---
"
    return
  fi
  STEP_OUT="$(mktemp)"
  ( cd "$dir" && exec "$@" ) >"$STEP_OUT" 2>&1 </dev/null &
  STEP_PID=$!
  while kill -0 "$STEP_PID" 2>/dev/null; do
    if [ "$waited" -ge "$limit" ]; then timed_out=1; kill_tree "$STEP_PID"; break; fi
    sleep 1; waited=$(( waited + 1 ))
  done
  wait "$STEP_PID" 2>/dev/null; rc=$?
  if [ "$timed_out" -eq 1 ]; then
    FAIL="${FAIL}--- ${label} (${dir}) TIMED OUT after ${limit}s, its process tree was killed ---
$(grep -v "^npm notice" "$STEP_OUT" | tail -n 20)
"
  elif [ "$rc" -ne 0 ]; then
    FAIL="${FAIL}--- ${label} (${dir}) FAILED ---
$(grep -v "^npm notice" "$STEP_OUT" | tail -n 40)
"
  fi
  rm -f "$STEP_OUT"; STEP_OUT=""; STEP_PID=""
}
not_checked () {  # $1=dir  $2=what is missing
  FAIL="${FAIL}--- ${1} NOT CHECKED: ${2} ---
"
}

# Files of $1 that changed since HEAD (staged, unstaged, untracked), relative to it; docs-only changes do not count.
changed_in () {
  local d="$1" f
  { git -C "$d" diff --name-only --relative HEAD -- . 2>/dev/null || git -C "$d" diff --name-only --relative --cached -- . 2>/dev/null   # no commit yet
    git -C "$d" ls-files --others --exclude-standard -- . 2>/dev/null; } | sort -u | while IFS= read -r f; do
    [ -f "$d/$f" ] || continue
    case "$f" in node_modules/*|dist/*|build/*|coverage/*|*.md|*.txt) continue ;; esac
    [ "$d" = "." ] && is_node "${f%%/*}" && continue   # belongs to a package of its own
    echo "$f"
  done
}

finish () {  # $1 = exit code, $2 = report for stderr (empty when the gate passed)
  { echo "${FINGERPRINT:-none} $MODE $1 $(date +%s)"; printf '%s' "$2"; } > "$RESULT"
  if [ "$1" -ne 0 ]; then
    [ -n "$COUNTER" ] && echo $(( ${N:-0} + 1 )) > "$COUNTER"
    printf '%s' "$2" >&2
    exit "$1"
  fi
  [ -n "$COUNTER" ] && rm -f "$COUNTER"
  # Only the workspace root has .pipeline/; a gate run from a subfolder must not leave a stray cache there.
  # A scoped pass never replaces the full pass of the same code.
  if [ -n "$FINGERPRINT" ] && [ -d .pipeline ] && ! { [ "$MODE" = scoped ] && cached_pass; }; then
    echo "$FINGERPRINT $MODE" > "$CACHE"
  fi
  echo "gate: OK"
  exit 0
}

# --- project override ---------------------------------------------------------------------
if [ -f .claude/gate.local.sh ]; then
  run_step ".claude/gate.local.sh" . bash .claude/gate.local.sh
  [ -z "$FAIL" ] && finish 0 ""
  finish 2 "$(printf 'GATE FAILED — fix these before finishing:\n%s' "$FAIL")"
fi

SCOPE=""
for d in $DIRS; do
  is_node "$d" || is_dotnet "$d" || continue   # not a project
  CHANGED=""; SCOPED_DIR=0
  if [ "$MODE" = scoped ]; then
    # Outside a git repository nothing says what changed: the package is checked whole, as in the full gate.
    if git -C "$d" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      CHANGED="$(changed_in "$d")"
      [ -n "$CHANGED" ] || continue
      SCOPED_DIR=1
    fi
    SCOPE="$SCOPE $d"
  fi
  # Node / React / React Native
  # A project with package.json must never be skipped silently: without npm and a JSON reader
  # (jq, or node as fallback) the gate would print "OK" having run nothing.
  if is_node "$d" && { ! command -v npm >/dev/null 2>&1 || { ! command -v jq >/dev/null 2>&1 && ! command -v node >/dev/null 2>&1; }; }; then
    not_checked "$d" "npm and jq/node are required to run its scripts"
  elif is_node "$d"; then
    if command -v jq >/dev/null 2>&1; then
      script_of () { jq -r --arg s "$1" '.scripts[$s] // empty' "$d/package.json" 2>/dev/null; }
    else
      script_of () { node -e 'const p=require(require("path").resolve(process.argv[1],"package.json"));process.stdout.write((p.scripts&&p.scripts[process.argv[2]])||"")' "$d" "$1" 2>/dev/null; }
    fi
    has () { [ -n "$(script_of "$1")" ]; }
    has lint      && run_step "npm lint"      "$d" npm run --silent lint
    if has typecheck; then run_step "npm typecheck" "$d" npm run --silent typecheck
    elif [ -f "$d/tsconfig.json" ] && [ -x "$d/node_modules/.bin/tsc" ]; then run_step "tsc --noEmit" "$d" ./node_modules/.bin/tsc --noEmit; fi
    [ -z "${GATE_SKIP_BUILD:-}" ] && has build && run_step "npm build" "$d" npm run --silent build
    if [ -z "${GATE_SKIP_TESTS:-}" ] && has test; then
      if [ "$SCOPED_DIR" = 0 ]; then
        if has test:unit && has test:e2e && ! printf '%s' "$(script_of test)" | grep -qE '&&|[|;]'; then
          run_step "npm test:unit" "$d" env CI=true npm run --silent test:unit
          run_step "npm test:e2e"  "$d" env CI=true npm run --silent test:e2e
        else
          run_step "npm test" "$d" env CI=true npm test --silent
        fi
      else
        # Only the tests that import a changed file; e2e suites and the full run are left to the --full gate.
        RELATED="$(printf '%s\n' "$CHANGED" | grep -v '^tests/e2e/' || true)"
        if [ -z "$RELATED" ]; then
          echo "gate: $d tests skipped in the scoped gate (only e2e files changed); the --full gate runs them"
        else
          # shellcheck disable=SC2086
          case "$(script_of test)" in
            *vitest*) run_step "vitest related" "$d" env CI=true npx --no-install vitest related --run --passWithNoTests ${GATE_TEST_ARGS:-} $RELATED ;;
            *jest*)
              JEST_SCOPE="--passWithNoTests --testPathIgnorePatterns=node_modules --testPathIgnorePatterns=tests/e2e"
              COUNT="$(cd "$d" && npx --no-install jest --listTests $JEST_SCOPE --findRelatedTests $RELATED 2>/dev/null | grep -vc '^npm notice')"
              OWN_TESTS="$(printf '%s\n' "$RELATED" | grep -E '\.(test|spec)\.[cm]?[jt]sx?$' || true)"
              if [ "${COUNT:-0}" -le "${GATE_SCOPED_MAX_TESTS:-10}" ]; then
                run_step "jest related" "$d" env CI=true npx --no-install jest $JEST_SCOPE ${GATE_TEST_ARGS:-} --findRelatedTests $RELATED
              else
                echo "gate: $d: $COUNT test files reach the changed files (max ${GATE_SCOPED_MAX_TESTS:-10} in the scoped gate); the rest is left to the --full gate"
                [ -z "$OWN_TESTS" ] || run_step "jest changed tests" "$d" env CI=true npx --no-install jest $JEST_SCOPE ${GATE_TEST_ARGS:-} --runTestsByPath $OWN_TESTS
              fi ;;
            *) echo "gate: $d tests skipped in the scoped gate (unknown test runner); the --full gate runs them" ;;
          esac
        fi
      fi
    fi
  fi
  # .NET (a folder may hold a .sln without any .csproj, or the reverse)
  if is_dotnet "$d"; then
    if ! command -v dotnet >/dev/null 2>&1; then
      not_checked "$d" "dotnet is required to build and test it"
    else
      run_step "dotnet build" "$d" dotnet build --nologo -v q
      [ -z "${GATE_SKIP_TESTS:-}" ] && [ "$MODE" = full ] && run_step "dotnet test" "$d" dotnet test --nologo --no-build -v q
    fi
  fi
done

if [ "$MODE" = scoped ]; then
  if [ -n "$SCOPE" ]; then echo "gate: scoped to${SCOPE} (changes since HEAD; tests related to them, no e2e)"
  else echo "gate: no changed package to check"; fi
fi
[ -z "$FAIL" ] && finish 0 ""
finish 2 "$(printf 'GATE FAILED — fix these before finishing:\n%s' "$FAIL")"
