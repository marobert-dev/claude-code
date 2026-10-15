#!/usr/bin/env bash
# FE-01 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

check_test fe01-totals functional frontend 'FE01 total equals the sum of the line totals' "Cart total exact to the cent (5 cases)"
check_test fe01-fr a11y_i18n frontend 'FE01 French total' "French total uses the French format"
check_test fe01-confirm functional frontend 'FE01 confirmation message' "Confirmation message shows the same total"
check fe01-contract-untouched contract "contracts/openapi.yaml unchanged" -- file_unchanged contracts/openapi.yaml
check fe01-no-floor code_quality "No truncation (Math.floor/trunc) left in the total computation" -- \
  grep_absent 'Math\.(floor|trunc)' frontend/src/pages/CartPage.tsx
check fe01-tests-added tests_quality "Unit tests added for the total" -- pattern_count_grew '(it|test)(\.each\([^)]*\))?\(' frontend/tests

finish
