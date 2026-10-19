#!/usr/bin/env bash
# Score inputs for one finished run: scripts/check-run.sh <run-dir>
#
# Order matters: everything about the agent's own work is measured BEFORE hidden tests are copied in.
#   1. diff since eval-start (agent's changes) and since eval-base, coordination files, .decisions entries, markers
#   2. the deterministic gate (bash .claude/hooks/gate.sh)
#   3. hidden tests copied in and run (backend xUnit project, frontend Vitest, Playwright), one run per suite
#   4. standard checks (gate, role prohibitions, scope, tests not weakened, diff size, Memory: line)
#   5. tasks/<TASK-ID>/check.sh adds task-specific checks
#   6. <run-dir>/.eval/result.json
# Env: EVAL_SKIP_GATE=1 skips step 2 (the gate check is then recorded as failed).
set -uo pipefail
# shellcheck source=lib/common.sh
. "$(dirname "$0")/lib/common.sh"

RUN="${1:-}"
[ -d "$RUN/.git" ] || die "usage: check-run.sh <run-dir>"
RUN="$(cd "$RUN" && pwd)"
META="$(meta_dir_of "$RUN")"
TASK="$(evalkit task-field "$META/run.json" task)"
[ -n "$TASK" ] || die "no run metadata in $META"
TASK_DIR="$KIT/tasks/$TASK"
TASK_JSON="$TASK_DIR/task.json"
EVAL="$RUN/.eval"
if [ "$(evalkit task-field "$EVAL/metrics.json" is_error)" = "true" ]; then
  rm -f "$EVAL/result.json"
  die "the agent call failed (see $EVAL/agent-report.md); rerun run-agent.sh before checking"
fi
mkdir -p "$EVAL"
rm -f "$EVAL/checks.jsonl" "$EVAL/checks.json" "$EVAL"/hidden-*.json
export RUN_DIR="$RUN" EVAL_DIR="$EVAL" TASK_DIR TASK_ID="$TASK" CHECKS_FILE="$EVAL/checks.jsonl" META_DIR="$META"

HIDDEN_BACKEND="$RUN/backend/tests/ShopLite.Api.HiddenTests"
HIDDEN_FRONTEND="$RUN/frontend/tests/hidden"
HIDDEN_E2E="$RUN/tests/e2e/hidden"
rm -rf "$HIDDEN_BACKEND" "$HIDDEN_FRONTEND" "$HIDDEN_E2E"

# ---- 1. what the agent changed ------------------------------------------------------------------------
info "measuring diff"
evalkit diff-metrics "$RUN" "$META" eval-start "$TASK_JSON" > "$EVAL/diff.json"
evalkit diff-metrics "$RUN" "$META" eval-base "$TASK_JSON" > "$EVAL/diff-base.json"
evalkit coord-diff "$RUN" "$META/coord-baseline.json" > "$EVAL/coordination.json"
evalkit decisions "$RUN" "$META/decisions-baseline.json" > "$EVAL/decisions.json"
[ -f "$EVAL/metrics.json" ] || printf '{}\n' > "$EVAL/metrics.json"

# ---- 2. gate -------------------------------------------------------------------------------------------
if [ -z "${EVAL_SKIP_GATE:-}" ]; then
  info "running the gate"
  ( cd "$RUN" && bash .claude/hooks/gate.sh < /dev/null ) > "$EVAL/gate.log" 2>&1
  GATE_RC=$?
else
  GATE_RC=99; echo "skipped (EVAL_SKIP_GATE)" > "$EVAL/gate.log"
fi
"$PYTHON" -c 'import json,sys; json.dump({"exit_code": int(sys.argv[1]), "passed": sys.argv[1] == "0"}, open(sys.argv[2], "w"))' "$GATE_RC" "$EVAL/gate.json"

# ---- 3. hidden tests -----------------------------------------------------------------------------------
if compgen -G "$TASK_DIR/hidden-tests/backend/*.cs" > /dev/null; then
  info "running hidden backend tests"
  mkdir -p "$HIDDEN_BACKEND"
  cp -R "$KIT/tasks/_shared/hidden-backend/." "$HIDDEN_BACKEND/"
  cp "$TASK_DIR"/hidden-tests/backend/*.cs "$HIDDEN_BACKEND/"
  ( cd "$RUN" && dotnet test backend/tests/ShopLite.Api.HiddenTests --nologo -v q \
      --logger "trx;LogFileName=hidden-backend.trx" --results-directory "$EVAL/trx" ) > "$EVAL/hidden-backend.log" 2>&1
  evalkit parse-trx "$EVAL/hidden-backend.json" "$EVAL/trx/hidden-backend.trx"
fi

if compgen -G "$TASK_DIR/hidden-tests/frontend/*.test.ts*" > /dev/null; then
  info "running hidden frontend tests"
  mkdir -p "$HIDDEN_FRONTEND"
  cp -R "$KIT/tasks/_shared/hidden-frontend/." "$HIDDEN_FRONTEND/"
  cp "$TASK_DIR"/hidden-tests/frontend/*.test.ts* "$HIDDEN_FRONTEND/"
  ( cd "$RUN/frontend" && npx vitest run tests/hidden --reporter=json --outputFile="$EVAL/vitest-hidden.json" ) > "$EVAL/hidden-frontend.log" 2>&1
  evalkit parse-vitest "$EVAL/vitest-hidden.json" "$EVAL/hidden-frontend.json"
fi

if compgen -G "$TASK_DIR/hidden-tests/e2e/*.spec.ts" > /dev/null; then
  info "running hidden e2e tests"
  mkdir -p "$HIDDEN_E2E"
  cp "$TASK_DIR"/hidden-tests/e2e/*.spec.ts "$HIDDEN_E2E/"
  ( cd "$RUN" && PLAYWRIGHT_JSON_OUTPUT_FILE="$EVAL/playwright-hidden.json" PLAYWRIGHT_JSON_OUTPUT_NAME="$EVAL/playwright-hidden.json" \
      npx playwright test tests/e2e/hidden --reporter=json ) > "$EVAL/hidden-e2e.log" 2>&1
  evalkit parse-playwright "$EVAL/playwright-hidden.json" "$EVAL/hidden-e2e.json"
fi

# ---- 4. standard checks --------------------------------------------------------------------------------
# shellcheck source=lib/check-lib.sh
. "$KIT/scripts/lib/check-lib.sh"
check_blocking std-gate gate_tests "Gate green at the end of the run (bash .claude/hooks/gate.sh)" -- gate_green
check_blocking std-role protocol "No role prohibition violated (forbidden paths untouched)" -- no_forbidden_paths
check_blocking std-tests protocol "No test deleted, skipped or reduced" -- tests_not_weakened
check std-scope scope "Every changed file is inside the task's allowed paths" -- no_out_of_scope
MAX_DIFF="$(task_field "$TASK" scope.max_diff_lines)"
[ -n "$MAX_DIFF" ] && check std-diff-size scope "Diff size within the task maximum ($MAX_DIFF lines)" -- diff_within "$MAX_DIFF"
if [ "$(task_field "$TASK" memory_line_expected)" = "true" ]; then
  check std-memory-line protocol "Final report ends with 'Memory: available|unavailable'" -- memory_line_present
fi

# ---- 5. task checks ------------------------------------------------------------------------------------
if [ -f "$TASK_DIR/check.sh" ]; then
  info "running task checks"
  bash "$TASK_DIR/check.sh" "$RUN" > "$EVAL/check-sh.out" 2> "$EVAL/check-sh.log" || \
    record task-check-crashed functional 0 0 "tasks/$TASK/check.sh exited non-zero" "$(tail -c 400 "$EVAL/check-sh.log")"
fi
evalkit finish-checks "$CHECKS_FILE" > "$EVAL/checks.json"

# ---- 6. result -----------------------------------------------------------------------------------------
evalkit compose-result "$RUN" "$META" "$TASK_JSON"
