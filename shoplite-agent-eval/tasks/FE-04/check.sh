#!/usr/bin/env bash
# FE-04 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

check_test fe04-loading a11y_i18n frontend 'FE04 announces loading' "Loading announced (role=status)"
check_test fe04-empty functional frontend 'FE04 shows the empty message' "Empty state only for an empty history"
check_test fe04-error functional frontend 'FE04 shows an error with retry on a server error' "Server error -> alert + retry, no empty message"
check_test fe04-network functional frontend 'FE04 shows an error on a network failure' "Network failure -> alert"
check_test fe04-retry functional frontend 'FE04 retry reloads' "Retry reloads the history"
check_test fe04-fr a11y_i18n frontend 'FE04 French error' "French texts"
check fe04-contract-untouched contract "contracts/openapi.yaml unchanged" -- file_unchanged contracts/openapi.yaml

keys_in_both_locales () {
  "$PYTHON" - "$RUN_DIR" <<'PY'
import json, sys, pathlib
base = pathlib.Path(sys.argv[1]) / "frontend/src/i18n/locales"
def keys(d, p=""):
    for k, v in d.items():
        yield from (keys(v, p + k + ".") if isinstance(v, dict) else [p + k])
en = set(keys(json.loads((base / "en.json").read_text(encoding="utf-8"))))
fr = set(keys(json.loads((base / "fr.json").read_text(encoding="utf-8"))))
print("missing in fr:", sorted(en - fr), "missing in en:", sorted(fr - en))
sys.exit(0 if en == fr and "orders.loadError" in en else 1)
PY
}
check fe04-locales a11y_i18n "orders.loadError present and en/fr key sets identical" -- keys_in_both_locales
check fe04-reuse-states code_quality "Reuses the shared ErrorState component" -- grep_present 'ErrorState' frontend/src/pages/OrdersPage.tsx
check fe04-tests-added tests_quality "Tests added for the history states" -- pattern_count_grew 'loadError|could not be loaded|Try again' frontend/tests

finish
