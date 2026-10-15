#!/usr/bin/env bash
# BE-05 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

check_test be05-max-queries performance backend 'BE05_History_UsesAtMostTwoQueries' "History issues <= 2 SQL commands (measured on SQLite)"
check_test be05-constant performance backend 'BE05_History_QueryCountDoesNotGrowWithOrders' "Query count independent of the number of orders"
check_test be05-shape functional backend 'BE05_History_ResponseUnchanged' "Response unchanged (relational provider)"
check_test be05-inmemory functional backend 'BE05_History_InMemoryProviderStillWorks' "Response unchanged (InMemory provider)"
check_test be05-single functional backend 'BE05_SingleOrder_Unchanged' "Single order unchanged"
check be05-contract-untouched contract "contracts/openapi.yaml unchanged by dev-backend" -- file_unchanged contracts/openapi.yaml

projection_used () {
  "$PYTHON" - "$RUN_DIR" <<'PY'
import re, sys, pathlib
root = pathlib.Path(sys.argv[1]) / "backend/src/ShopLite.Api"
text = "\n".join(p.read_text(encoding="utf-8") for p in root.rglob("*.cs") if "obj" not in p.parts)
m = re.search(r"\n    (public|internal|private)[^\n]*\bGetOrdersAsync\s*\(.*?(?=\n    (public|private|internal|protected) |\n}\n)", text, re.S)
body = m.group(0) if m else ""
ok = "Select(" in body and "foreach" not in body and "AsNoTracking" in body
print("projection + AsNoTracking, no loop" if ok else "GetOrdersAsync still loops or does not project")
sys.exit(0 if ok else 1)
PY
}
check be05-projection code_quality "GetOrdersAsync projects with AsNoTracking, no per-row loop" -- projection_used

finish
