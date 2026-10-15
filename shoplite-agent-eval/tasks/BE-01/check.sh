#!/usr/bin/env bash
# BE-01 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

check_test be01-qty-add functional backend 'BE01_AddItem_RejectsQuantityOutOfRange' "Out-of-range quantities rejected on add (0, -3, 100)"
check_test be01-qty-bounds functional backend 'BE01_AddItem_AcceptsBoundaryQuantities' "Quantities 1 and 99 still accepted"
check_test be01-qty-update functional backend 'BE01_UpdateItem_RejectsQuantityOutOfRange' "Out-of-range quantities rejected on update, line unchanged"
check_test be01-page-size functional backend 'BE01_ListProducts_(RejectsPageSizeOutOfRange|AcceptsMaximumPageSize)' "pageSize limited to 1-50 (400 outside)"
check_test be01-i18n functional backend 'BE01_ValidationMessage_IsLocalizedInFrench' "Validation messages localized in French"
check_test be01-price security backend 'BE01_ClientCannotChooseUnitPrice' "Client-supplied unit price ignored or rejected (mass assignment closed)"
check_test be01-spec contract backend 'BE01_Contract_EmittedSpecMatchesConstraints' "Emitted /openapi/v1.json matches the contract constraints"
check be01-contract-untouched contract "contracts/openapi.yaml unchanged by dev-backend" -- file_unchanged contracts/openapi.yaml

check be01-tests-added tests_quality "New backend tests cover the story" --   pattern_count_grew '\[(Fact|Theory)' backend/tests
check be01-range-attrs code_quality "Validation declared with DataAnnotations + Validation.Range key (project convention)" -- \
  grep_present 'Range\(.*Validation\.Range' backend/src/ShopLite.Api/Dtos

finish
