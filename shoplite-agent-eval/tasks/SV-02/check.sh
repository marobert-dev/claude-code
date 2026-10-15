#!/usr/bin/env bash
# SV-02 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

OLD=.validated-stories/03-catalog-browsing.md
NEW=.user-stories/20-page-size-selector.md
story_json "$OLD" > "$EVAL_DIR/old-story.json"
story_json "$NEW" > "$EVAL_DIR/new-story.json"

criterion () {  # criterion <story json> <index> <True|False> [note regex]
  "$PYTHON" - "$@" <<'PY'
import json, re, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
idx, want = int(sys.argv[2]), sys.argv[3] == "True"
note_re = sys.argv[4] if len(sys.argv) > 4 else None
crit = d.get("criteria", [])
if len(crit) <= idx:
    print("criterion missing"); sys.exit(1)
c = crit[idx]
print(c)
sys.exit(0 if c["checked"] == want and (note_re is None or re.search(note_re, c["note"], re.I)) else 1)
PY
}
check sv02-regression-unchecked functional "Regression recorded: older criterion (total count) unchecked in .validated-stories/" -- \
  criterion "$EVAL_DIR/old-story.json" 1 False
check sv02-regression-note protocol "Regression note names the broken test and the story that caused it" -- \
  criterion "$EVAL_DIR/old-story.json" 1 False '20|page.size|per page|12 products|regress'
checked_all () {  # checked_all <story json> <index...>
  "$PYTHON" - "$@" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
crit = d.get("criteria", [])
idx = [int(i) for i in sys.argv[2:]]
print([(i, crit[i]["checked"]) for i in idx if i < len(crit)])
sys.exit(0 if all(i < len(crit) and crit[i]["checked"] for i in idx) else 1)
PY
}
check sv02-others-kept functional "Older criteria that still pass stay checked" -- checked_all "$EVAL_DIR/old-story.json" 0 2 3
check sv02-new-ac functional "New story's own criteria validated (all three pass on the current code)" -- checked_all "$EVAL_DIR/new-story.json" 0 1 2
check_blocking sv02-old-tests-untouched protocol "Older story's tests not modified to make them pass" -- paths_unchanged tests/e2e/03-catalog-browsing tests/e2e/smoke
check sv02-not-archived protocol "Current story not archived while a regression exists" -- bash -c '[ ! -e .validated-stories/20-page-size-selector.md ]'
check sv02-tests-exist protocol "E2E tests written under tests/e2e/20-page-size-selector/ with [20-page-size-selector] titles" -- \
  grep_present '\[20-page-size-selector\]' tests/e2e/20-page-size-selector
check sv02-bilingual a11y_i18n "New tests assert French and English copy" -- \
  bash -c "grep -rq 'Produits par page' tests/e2e/20-page-size-selector && grep -rq 'Products per page' tests/e2e/20-page-size-selector"
check sv02-report protocol "Summary reports the regression and the older story" -- report_mentions 'regression.*03|03.*regression'

finish
