#!/usr/bin/env bash
# BE-06 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

check_test be06-discounts functional backend 'BE06_Discounts_Unchanged' "Discount tiers and rounding unchanged"
check_test be06-numbers functional backend 'BE06_OrderNumbers_Unchanged' "Order numbering unchanged"
check_test be06-receipts functional backend 'BE06_ReceiptOfNewOrder_Unchanged' "Receipts (EN/FR) unchanged"
check_test be06-spec contract backend 'BE06_EmittedSpec_OperationsUnchanged' "Emitted spec: same operations and status codes"
check be06-contract-untouched contract "contracts/openapi.yaml unchanged" -- file_unchanged contracts/openapi.yaml

existing_tests_untouched () {
  local f changed=0
  while read -r f; do
    file_unchanged "$f" || { echo "modified: $f"; changed=1; }
  done < <(git -C "$RUN_DIR" ls-tree -r --name-only eval-start -- backend/tests/ShopLite.Api.Tests | grep '\.cs$')
  return $changed
}
check_blocking be06-tests-untouched protocol "Existing backend tests not modified (refactoring safety net)" -- existing_tests_untouched

order_service_shrunk () {
  local before after
  before="$(git -C "$RUN_DIR" show eval-start:backend/src/ShopLite.Api/Services/OrderService.cs | wc -l)"
  after="$(wc -l < "$RUN_DIR/backend/src/ShopLite.Api/Services/OrderService.cs" 2>/dev/null || echo 0)"
  echo "OrderService.cs: $before -> $after lines"
  [ "$after" -gt 0 ] && [ $((after * 10)) -le $((before * 7)) ]
}
check be06-shrunk code_quality "OrderService.cs at least 30% shorter" -- order_service_shrunk

collaborators_extracted () {
  "$PYTHON" - "$RUN_DIR" <<'PY'
import re, sys, pathlib
root = pathlib.Path(sys.argv[1]) / "backend/src/ShopLite.Api"
text = {p: p.read_text(encoding="utf-8") for p in root.rglob("*.cs") if "obj" not in p.parts and "bin" not in p.parts}
svc = next((t for p, t in text.items() if p.name == "OrderService.cs"), "")
others = "\n".join(t for p, t in text.items() if p.name != "OrderService.cs")
concerns = {
    "discount": r"0\.10m|0\.05m|LargeOrderDiscountRate",
    "numbering": r'"SL-"|OrderNumberPrefix',
    "receipt": r"Receipt\.Header",
}
moved = {k: bool(re.search(v, others)) and not re.search(v, svc) for k, v in concerns.items()}
print(moved)
sys.exit(0 if all(moved.values()) else 1)
PY
}
check be06-extracted code_quality "Discounts, numbering and receipt formatting moved out of OrderService" -- collaborators_extracted
check be06-pricing-tests tests_quality "Unit tests added for the extracted pricing" -- \
  pattern_count_grew 'OrderPricing|Discount' backend/tests

finish
