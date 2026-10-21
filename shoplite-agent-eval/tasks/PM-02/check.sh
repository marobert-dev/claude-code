#!/usr/bin/env bash
# PM-02 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
# Expected: the contradiction is caught up front, so the pipeline stops before any agent runs.
. "$KIT/scripts/lib/check-lib.sh"

SLUG=01-minimum-order-amount
status_is () { local s; s="$(tr -d '\r' < "$RUN_DIR/.pipeline/pm-last-run.txt" 2>/dev/null)"; echo "pm-last-run: $s"; [ "$s" = "$1" ]; }
check_blocking pm02-status protocol "pm-last-run.txt = FAILED $SLUG (never COMPLETED for contradictory criteria)" -- status_is "FAILED $SLUG"
check pm02-kept protocol "Story left in .user-stories/, not moved to .completed/ nor archived" -- \
  bash -c "[ -f .user-stories/$SLUG.md ] && [ ! -e .completed/$SLUG.md ] && [ ! -e .validated-stories/$SLUG.md ]"
check pm02-handoff protocol "Handoff checkpoint written" -- \
  bash -c "compgen -G '.pipeline/handoffs/*.md' > /dev/null || compgen -G '.pipeline/handoffs/archive/*.md' > /dev/null"

stopped_before_pipeline () {
  "$PYTHON" - "$RUN_DIR/.user-stories/$SLUG.md" "$EVAL_DIR/diff.json" <<'PY'
import json, re, sys
from pathlib import Path
story = Path(sys.argv[1])
text = story.read_text(encoding="utf-8") if story.exists() else ""
retries = re.findall(r"^##\s*Retry\s*\d+", text, re.M | re.I)
diff = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
code = [f["path"] for f in diff["files"] if f["path"].startswith(("backend/", "frontend/", "contracts/", "tests/"))]
print({"retry_sections": len(retries), "code_changed": code[:5]})
sys.exit(0 if not retries and not code else 1)
PY
}
check pm02-stopped-early functional "Stopped before running the pipeline: no '## Retry n' note, no code, contract or test changed" -- stopped_before_pipeline
check pm02-contradiction-logged protocol "Contradiction between the criteria logged (team memory or .decisions/)" -- \
  decision_logged product-manager 'contradict|conflict|incompatible|mutually exclusive|cannot both|both cannot|cannot be both'
check pm02-reason-reported protocol "Final message names the failed story and the reason" -- report_mentions "$SLUG|minimum"

finish
