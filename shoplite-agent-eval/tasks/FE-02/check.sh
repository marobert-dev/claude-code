#!/usr/bin/env bash
# FE-02 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

check_test fe02-one-request performance frontend 'FE02 sends one request' "One request for the full word, none while typing"
check_test fe02-page-reset functional frontend 'FE02 restarts from page 1' "New search restarts from page 1"
check_test fe02-stale functional frontend 'FE02 ignores the response of an older' "Stale responses ignored"
check_test fe02-category functional frontend 'FE02 category changes are not delayed' "Category filter not debounced"
check_test fe02-fr a11y_i18n frontend 'FE02 French label' "FR label/placeholder unchanged"
check fe02-contract-untouched contract "contracts/openapi.yaml unchanged" -- file_unchanged contracts/openapi.yaml
check fe02-no-new-dependency code_quality "No dependency added for debouncing (plan)" -- \
  paths_unchanged frontend/package.json frontend/package-lock.json
check fe02-tests-added tests_quality "Tests added for the debounce" -- pattern_count_grew '(it|test)(\.each\([^)]*\))?\(' frontend/tests

finish
