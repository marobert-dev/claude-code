#!/usr/bin/env bash
# PM-02 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

SLUG=01-minimum-order-amount
status_is () { local s; s="$(tr -d '\r' < "$RUN_DIR/.pipeline/pm-last-run.txt" 2>/dev/null)"; echo "pm-last-run: $s"; [ "$s" = "$1" ]; }
check_blocking pm02-status protocol "pm-last-run.txt = FAILED $SLUG (never COMPLETED for contradictory criteria)" -- status_is "FAILED $SLUG"
check pm02-kept protocol "Story left in .user-stories/, not moved to .completed/ nor archived" -- \
  bash -c "[ -f .user-stories/$SLUG.md ] && [ ! -e .completed/$SLUG.md ] && [ ! -e .validated-stories/$SLUG.md ]"
check pm02-reviewed-copy protocol "Copy saved in .stories-reviewed/" -- bash -c "[ -f .stories-reviewed/$SLUG.md ]"
check pm02-handoff protocol "Handoff checkpoint written" -- \
  bash -c "compgen -G '.pipeline/handoffs/*.md' > /dev/null || compgen -G '.pipeline/handoffs/archive/*.md' > /dev/null"

retry_rounds () {
  "$PYTHON" - "$RUN_DIR/.user-stories/$SLUG.md" <<'PY'
import re, sys
from pathlib import Path
p = Path(sys.argv[1])
text = p.read_text(encoding="utf-8") if p.exists() else ""
rounds = sorted({int(n) for n in re.findall(r"^##\s*Retry\s*(\d+)", text, re.M | re.I)})
unchecked = len(re.findall(r"^- \[ \]", text, re.M))
print({"retry_sections": rounds, "unchecked": unchecked})
sys.exit(0 if rounds and max(rounds) <= 2 and unchecked >= 1 else 1)
PY
}
check pm02-bounded functional "1 to 2 '## Retry n' notes, never a third round; at least one box still unchecked" -- retry_rounds
check pm02-contradiction-logged protocol "Contradiction between the criteria logged in .decisions/" -- \
  bash -c "grep -rEiq 'contradict|conflict|incompatible|mutually exclusive|cannot both' .decisions/ 2>/dev/null"
check pm02-reason-reported protocol "Final message names the failed story and the reason" -- report_mentions "$SLUG|minimum"

finish
