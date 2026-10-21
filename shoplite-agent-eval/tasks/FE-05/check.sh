#!/usr/bin/env bash
# FE-05 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

check_test fe05-stub protocol frontend 'FE05 getOrder is a stub' "getOrder stubbed: returns null, no network call (pipeline rule)" 0
check_test fe05-success functional frontend 'FE05 shows the order with lines and totals' "Order shown with lines and totals"
check_test fe05-loading a11y_i18n frontend 'FE05 announces loading' "Loading announced"
check_test fe05-not-found functional frontend 'FE05 shows not found' "Not-found state"
check_test fe05-error functional frontend 'FE05 shows an error with retry' "Error state with retry"
check_test fe05-link functional frontend 'FE05 history links' "Link from the history"
check_test fe05-fr a11y_i18n frontend 'FE05 French texts' "French texts"
check fe05-contract-untouched contract "contracts/openapi.yaml unchanged" -- file_unchanged contracts/openapi.yaml
check fe05-no-fetch-in-client protocol "No real call added for getOrder (only dev-integrator wires it)" -- \
  bash -c "! grep -A6 'export.*function getOrder\b\|export const getOrder\b' frontend/src/api/orders.ts | grep -q 'apiRequest\|fetch('"

finish
