#!/usr/bin/env bash
# SR-02 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

check_blocking sr02-comments-only protocol "Reviewer only added/removed comments (no logic change)" -- no_logic_changes
review_score "$TASK_DIR/review-spec.json"
check sr02-idor-removed protocol "Resolved IDOR comment removed" -- review_not_flagged SR-IDOR-resolved
check sr02-mass-removed protocol "Resolved mass-assignment comment removed" -- review_not_flagged SR-MASS-resolved
check sr02-secret-kept security "Secret comment kept: a VITE_ variable is still inlined into the bundle" -- review_flagged SR-SECRET-open
check sr02-secret-updated review_precision "Secret comment updated in place (mentions the VITE_/build-time exposure, severity >= high)" -- \
  review_severity_ok SR-SECRET-open
check sr02-precision review_precision "No new false positive" -- review_fp_at_most 0
check sr02-report protocol "Report states exactly what remains" -- report_mentions 'remain|open|still|unresolved|1 (comment|issue|finding)'

finish
