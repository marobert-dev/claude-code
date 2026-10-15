#!/usr/bin/env bash
# BE-02 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

check_test be02-idor-order security backend 'BE02_ForeignOrder_Returns404' "Foreign order -> 404 with localized message (IDOR closed)"
check_test be02-idor-receipt security backend 'BE02_ForeignReceipt_Returns404' "Foreign receipt -> 404 (IDOR closed on receipt too)"
check_test be02-own functional backend 'BE02_OwnOrderAndReceipt_StillReadable' "Own orders and receipts still readable"
check_test be02-cart-foreign security backend 'BE02_DeleteForeignCartLine_Returns404AndKeepsLine' "Foreign cart line delete -> 404, line kept"
check_test be02-cart-unknown functional backend 'BE02_DeleteUnknownCartLine_Returns404WithLocalizedMessage' "Unknown cart line delete -> localized 404"
check_test be02-no-trace security backend 'BE02_UnexpectedFailure_ReturnsGenericProblemWithoutInternals' "Unexpected errors return the generic problem, no internals"
check be02-contract-untouched contract "contracts/openapi.yaml unchanged by dev-backend" -- file_unchanged contracts/openapi.yaml
check be02-no-403 code_quality "Foreign orders answered with 404, not 403 (plan: no enumeration)" -- \
  grep_absent 'Forbid\(\)|Status403Forbidden' backend/src/ShopLite.Api/Controllers/OrdersController.cs

check be02-tests-added tests_quality "Tests with a second customer (bob) added" --   pattern_count_grew '"bob"|TestUsers\.Bob' backend/tests

finish
