#!/usr/bin/env bash
# PM-01 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

SLUG=01-cart-badge
status_is () { local s; s="$(tr -d '\r' < "$RUN_DIR/.pipeline/pm-last-run.txt" 2>/dev/null)"; echo "pm-last-run: $s"; [ "$s" = "$1" ]; }
check pm01-status protocol "pm-last-run.txt = COMPLETED $SLUG" -- status_is "COMPLETED $SLUG"
check pm01-moved protocol "Story moved to .completed/ and gone from .user-stories/" -- \
  bash -c "[ -f .completed/$SLUG.md ] && [ ! -e .user-stories/$SLUG.md ]"
check pm01-reviewed-copy protocol "Copy saved in .stories-reviewed/ and archived in .validated-stories/" -- \
  bash -c "[ -f .stories-reviewed/$SLUG.md ] && [ -f .validated-stories/$SLUG.md ]"
check pm01-progress protocol "Progress log and handoff checkpoint written" -- \
  bash -c "[ -f .pipeline/pm-progress.md ] && { compgen -G '.pipeline/handoffs/*.md' > /dev/null || compgen -G '.pipeline/handoffs/archive/*.md' > /dev/null; }"
check pm01-scout protocol "conventions-scout ran (.pipeline/conventions.md with its sections)" -- \
  bash -c "grep -q '^## Commands' .pipeline/conventions.md && grep -q '^## Change log' .pipeline/conventions.md"

story_sections () {
  "$PYTHON" - "$RUN_DIR/.completed/$SLUG.md" <<'PY'
import re, sys
from pathlib import Path
p = Path(sys.argv[1])
if not p.exists():
    print("story not in .completed/"); sys.exit(1)
text = p.read_text(encoding="utf-8")
need = ["## Technical Plan", "## Frontend Implementation", "## Backend Implementation", "## Integration Notes"]
missing = [n for n in need if n not in text]
unchecked = re.findall(r"^- \[ \]", text, re.M)
print({"missing": missing, "unchecked": len(unchecked)})
sys.exit(0 if not missing and not unchecked else 1)
PY
}
check pm01-story functional "Story carries plan + condensed reports and every criterion is checked" -- story_sections

contract_has_new_operation () {
  local before after
  before="$(git -C "$RUN_DIR" show eval-start:contracts/openapi.yaml | grep -c 'operationId:')"
  after="$(grep -c 'operationId:' "$RUN_DIR/contracts/openapi.yaml")"
  echo "operations: $before -> $after"; [ "$after" -gt "$before" ]
}
check pm01-contract contract "Contract first: a new operation in contracts/openapi.yaml" -- contract_has_new_operation
check pm01-e2e-written tests_quality "story-validator tests in tests/e2e/$SLUG/ (FR + EN)" -- \
  bash -c "grep -rq '\[$SLUG\]' tests/e2e/$SLUG && grep -rq 'Panier' tests/e2e/$SLUG"
check pm01-docs functional "doc-writer ran: docs/dev and docs/user-manual/{en,fr}" -- \
  bash -c "[ -d docs/dev ] && compgen -G 'docs/user-manual/en/*.html' > /dev/null && compgen -G 'docs/user-manual/fr/*.html' > /dev/null"
check_blocking pm01-no-open-security security "No SECURITY: comment left open in the code" -- grep_absent 'SECURITY:' backend/src frontend/src
check pm01-no-open-review code_quality "No REVIEW: comment left in the code" -- grep_absent 'REVIEW:' backend/src frontend/src
check_test pm01-hidden-count functional e2e 'PM01 shows the unit count' "Badge shows Cart (3) / Panier (3) end to end"
check_test pm01-hidden-refresh functional e2e 'PM01 updates the count' "Badge refreshed right after adding"
check_test pm01-hidden-empty functional e2e 'PM01 shows the plain link' "Plain link for an empty cart"
check_test pm01-hidden-anon security e2e 'PM01 hides the cart link' "No cart link for signed-out visitors"

full_suite_green () {
  (cd "$RUN_DIR" && PLAYWRIGHT_JSON_OUTPUT_FILE="$EVAL_DIR/pm01-suite.json" PLAYWRIGHT_JSON_OUTPUT_NAME="$EVAL_DIR/pm01-suite.json" \
     npx playwright test --grep-invert "PM01" --reporter=json > /dev/null 2>&1)
}
check pm01-regression functional "Full e2e suite (smoke + story tests) green" -- full_suite_green

finish
