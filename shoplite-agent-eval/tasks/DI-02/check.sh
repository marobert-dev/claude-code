#!/usr/bin/env bash
# DI-02 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

check_test di02-empty-200 contract backend 'DI02_EmptyCart_Returns200WithZeros' "Empty cart -> 200 with zeros (contract), not 204"
check_test di02-field contract backend 'DI02_Summary_UsesContractFieldNames' "Backend uses the contract field name itemCount"
check_test di02-auth security backend 'DI02_Summary_RequiresAuthentication' "Summary still requires authentication"
check_test di02-spec contract backend 'DI02_EmittedSpec_Documents200Only' "Emitted spec matches the contract (no 204)"
check_test di02-client functional frontend 'DI02 getCartSummary calls' "Real call with bearer token"
check_test di02-badge functional frontend 'DI02 header shows the unit count from the API' "Badge shows the count"
check_test di02-badge-fr a11y_i18n frontend 'DI02 header shows the French unit count' "French badge"
check_test di02-empty functional frontend 'DI02 header shows the plain link for an empty cart' "Plain label for an empty cart"
check_test di02-failure functional frontend 'DI02 header survives a failing summary request' "Failure keeps the plain label"
check_test di02-anonymous functional frontend 'DI02 anonymous visitors never request' "No request for anonymous visitors"
check_blocking di02-contract-untouched contract "contracts/openapi.yaml unchanged (contract wins, code is fixed)" -- file_unchanged contracts/openapi.yaml

mismatch_reported () {
  grep -Eiq 'itemCount|count|204|mismatch|contract' "$EVAL_DIR/agent-report.md"
}
check di02-reported protocol "Final report names the contract mismatch and its resolution" -- mismatch_reported

finish
