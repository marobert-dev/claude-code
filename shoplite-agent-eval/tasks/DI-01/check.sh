#!/usr/bin/env bash
# DI-01 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

check_test di01-call contract frontend 'DI01 getOrder calls GET' "Real GET /api/orders/{id} with bearer token"
check_test di01-404 contract frontend 'DI01 getOrder maps 404 to null' "404 problem -> null (contract + plan)"
check_test di01-success functional frontend 'DI01 page shows the order returned by the API' "Page renders the real response"
check_test di01-page-404 functional frontend 'DI01 page shows not found on 404' "Not-found state wired to 404"
check_test di01-500 functional frontend 'DI01 page shows the error state with retry on 500' "Error state + retry wired to 500"
check_test di01-network functional frontend 'DI01 page shows the error state on a network failure' "Error state on network failure"
check_test di01-401 security frontend 'DI01 page sends the customer to sign in on 401' "401 clears the session and redirects to sign-in"
check di01-contract-untouched contract "contracts/openapi.yaml unchanged" -- file_unchanged contracts/openapi.yaml
check di01-uses-api-request code_quality "Real call goes through apiRequest (token, language, problem parsing)" -- \
  bash -c "grep -A8 'function getOrder' frontend/src/api/orders.ts | grep -q 'apiRequest'"
check di01-no-hardcoded-url code_quality "No hard-coded host in the client" -- grep_absent 'https?://localhost' frontend/src
check di01-visible-tests-kept protocol "dev-frontend's tests kept" -- bash -c '[ -f frontend/tests/OrderDetailPage.test.tsx ]'

finish
