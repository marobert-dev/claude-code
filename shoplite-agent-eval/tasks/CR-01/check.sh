#!/usr/bin/env bash
# CR-01 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

check_blocking cr01-comments-only protocol "Reviewer only added/removed comments (no logic change)" -- no_logic_changes
review_score "$TASK_DIR/review-spec.json"
check cr01-recall review_precision "Recall: at least 3 of the 4 planted defects have a REVIEW: comment nearby" -- review_recall_at_least 3
check cr01-precision review_precision "Precision: at most 1 REVIEW: comment not attached to a planted defect" -- review_fp_at_most 1
check cr01-ownership functional "REVIEW: on the missing ownership check" -- review_flagged CR1-ownership
check cr01-window functional "REVIEW: on the inverted 24 h window" -- review_flagged CR2-window-inverted
check cr01-save functional "REVIEW: on the un-awaited SaveChangesAsync" -- review_flagged CR3-unawaited-save
check cr01-copy functional "REVIEW: on the hard-coded (non-i18n) texts" -- review_flagged CR4-hardcoded-copy
check cr01-no-security-markers protocol "Uses the REVIEW: prefix only (SECURITY: belongs to security-reviewer)" -- \
  bash -c '[ "$(git diff eval-start | grep -c "^+.*SECURITY:")" = 0 ]'
check cr01-report protocol "Report states the comment count and locations" -- report_mentions '[0-9]+ .*(comment|REVIEW)|(comment|REVIEW).*[0-9]+'

finish
