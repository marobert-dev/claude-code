#!/usr/bin/env bash
# BE-03 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

check_test be03-anon security backend 'BE03_Anonymous_Update_Returns401AndKeepsProduct' "Anonymous update refused (401), product unchanged"
check_test be03-customer security backend 'BE03_Customer_Update_Returns403AndKeepsProduct' "Customer update refused (403), product unchanged"
check_test be03-admin functional backend 'BE03_Admin_Update_Succeeds' "Admin update still works"
check_test be03-create functional backend 'BE03_Create_StillRestricted' "Create still restricted"
check be03-contract-untouched contract "contracts/openapi.yaml unchanged by dev-backend" -- file_unchanged contracts/openapi.yaml
check be03-roles-constant code_quality "Role taken from Roles.Admin, no string literal" -- \
  grep_absent 'Roles *= *"admin"' backend/src/ShopLite.Api/Controllers
check be03-small-diff scope "Small, focused change (<= 120 changed lines)" -- diff_within 120

check be03-tests-added tests_quality "A test covers product updates by role" --   pattern_count_grew 'PutAsJsonAsync\(.*/api/products' backend/tests

finish
