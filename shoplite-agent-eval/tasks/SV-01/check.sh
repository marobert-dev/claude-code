#!/usr/bin/env bash
# SV-01 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

STORY=.user-stories/19-cart-page.md
story_json "$STORY" > "$EVAL_DIR/story.json"

criterion () {  # criterion <index> <checked: True|False> [note regex]
  "$PYTHON" - "$EVAL_DIR/story.json" "$@" <<'PY'
import json, re, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
idx, want = int(sys.argv[2]), sys.argv[3] == "True"
note_re = sys.argv[4] if len(sys.argv) > 4 else None
crit = d.get("criteria", [])
if len(crit) <= idx:
    print("criterion missing"); sys.exit(1)
c = crit[idx]
print(c)
ok = c["checked"] == want and (note_re is None or re.search(note_re, c["note"], re.I))
sys.exit(0 if ok else 1)
PY
}
check sv01-ac1 functional "Passing criterion checked: Desk Lamp line" -- criterion 0 True
check sv01-ac2-unchecked functional "Failing criterion left unchecked: Bamboo total" -- criterion 1 False
check sv01-ac2-note protocol "Precise note under the failing criterion (what failed, language, test file)" -- \
  criterion 1 False '19[.,]98|total'
check sv01-ac3 functional "Passing criterion checked: empty cart" -- criterion 2 True
check sv01-ac4 functional "Passing criterion checked: confirmation message" -- criterion 3 True
check sv01-not-archived protocol "Failed story not archived in .validated-stories/" -- bash -c '[ ! -e .validated-stories/19-cart-page.md ]'

E2E_DIR=tests/e2e/19-cart-page
check sv01-tests-exist protocol "E2E tests written under tests/e2e/19-cart-page/" -- bash -c "compgen -G '$E2E_DIR/*.spec.ts' > /dev/null"
check sv01-titles protocol "Test titles start with [19-cart-page]" -- grep_present '\[19-cart-page\]' "$E2E_DIR"
check sv01-bilingual a11y_i18n "Tests assert French and English copy" -- \
  bash -c "grep -rqE '19,99|Votre panier est vide' $E2E_DIR && grep -rqE '19\.99|Your cart is empty' $E2E_DIR"
check sv01-no-sleep tests_quality "No fixed sleeps (waitForTimeout)" -- grep_absent 'waitForTimeout|setTimeout\(' "$E2E_DIR"
check_blocking sv01-smoke-kept protocol "Existing e2e tests untouched" -- paths_unchanged tests/e2e/smoke

# Their tests must fail only on the real defect, and pass once the defect is fixed (test not weakened, not wrong).
run_story_e2e () {  # run_story_e2e <out.json>
  (cd "$RUN_DIR" && PLAYWRIGHT_JSON_OUTPUT_FILE="$1" PLAYWRIGHT_JSON_OUTPUT_NAME="$1" \
     npx playwright test "$E2E_DIR" --reporter=json > /dev/null 2>&1)
  evalkit parse-playwright "$1" "${1%.json}.summary.json"
}
if compgen -G "$RUN_DIR/$E2E_DIR/*.spec.ts" > /dev/null; then
  run_story_e2e "$EVAL_DIR/sv01-base.json"
  CART="$RUN_DIR/frontend/src/pages/CartPage.tsx"
  cp "$CART" "$EVAL_DIR/CartPage.tsx.orig"
  "$PYTHON" - "$CART" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]); s = p.read_text(encoding="utf-8")
s = s.replace("return Math.floor(totalInCents) / 100;", "return Math.round(totalInCents) / 100;")
p.write_text(s, encoding="utf-8")
PY
  run_story_e2e "$EVAL_DIR/sv01-fixed.json"
  cp "$EVAL_DIR/CartPage.tsx.orig" "$CART"
fi
only_total_fails_on_base () {
  "$PYTHON" - "$EVAL_DIR/sv01-base.summary.json" <<'PY'
import json, re, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
failed = [n for n, s in d["tests"].items() if s == "failed"]
print({"total": d["total"], "failed": failed})
sys.exit(0 if failed and all(re.search(r"total|19[.,]99|bamboo", n, re.I) for n in failed) and d["passed"] > 0 else 1)
PY
}
all_pass_when_fixed () {
  "$PYTHON" - "$EVAL_DIR/sv01-fixed.summary.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
print({k: d[k] for k in ("total", "passed", "failed")})
sys.exit(0 if d["total"] > 0 and d["failed"] == 0 else 1)
PY
}
check sv01-detects tests_quality "On the current code only the total test(s) fail" -- only_total_fails_on_base
check_blocking sv01-not-weakened tests_quality "With the reference fix every story test passes (test correct, not weakened)" -- all_pass_when_fixed
check sv01-report protocol "Summary reports the failure" -- report_mentions 'fail|unchecked|not (pass|met)'

finish
