#!/usr/bin/env bash
# BE-04 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

check_test be04-409 functional backend 'BE04_InsufficientStock_Returns409AndChangesNothing' "Insufficient stock -> 409, nothing changed"
check_test be04-fr functional backend 'BE04_InsufficientStock_MessageLocalizedInFrench' "Stock message localized in French"
check_test be04-decrement functional backend 'BE04_Success_DecrementsStock' "Successful checkout decrements stock"
check_test be04-exact functional backend 'BE04_ExactRemainingStock_IsAllowedThenRefused' "Exact remaining stock allowed, then refused"
check_test be04-atomic functional backend 'BE04_FailureWhileSaving_LeavesNoPartialOrder' "Failure while saving leaves no partial order (atomicity)"
check_test be04-spec contract backend 'BE04_Contract_EmittedSpecDocuments409' "Emitted spec documents the 409 response"
check be04-contract-untouched contract "contracts/openapi.yaml unchanged by dev-backend" -- file_unchanged contracts/openapi.yaml
check be04-characterization functional "Pricing characterization tests untouched" -- \
  file_unchanged backend/tests/ShopLite.Api.Tests/OrderPricingCharacterizationTests.cs

single_save_in_checkout () {
  "$PYTHON" - "$RUN_DIR" <<'PY'
import re, sys, pathlib
root = pathlib.Path(sys.argv[1]) / "backend/src/ShopLite.Api"
text = "\n".join(p.read_text(encoding="utf-8") for p in root.rglob("*.cs") if "obj" not in p.parts)
m = re.search(r"\n    (public|internal|private)[^\n]*\bCheckoutAsync\s*\(.*?\n    }\n", text, re.S)
if not m:
    print("CheckoutAsync not found"); sys.exit(1)
saves = len(re.findall(r"SaveChanges(Async)?\s*\(", m.group(0)))
print(f"SaveChanges calls in CheckoutAsync: {saves}")
sys.exit(0 if saves == 1 else 1)
PY
}
check be04-single-save code_quality "CheckoutAsync persists with a single SaveChanges (plan)" -- single_save_in_checkout
check be04-resx-fr functional "New messages added to both resource files" -- bash -c \
  'grep -q "Error.InsufficientStock" backend/src/ShopLite.Api/Resources/SharedResource.resx && grep -q "Error.InsufficientStock" backend/src/ShopLite.Api/Resources/SharedResource.fr.resx'
check be04-tests-added tests_quality "New tests cover stock and atomicity" -- pattern_count_grew '\[(Fact|Theory)' backend/tests

finish
