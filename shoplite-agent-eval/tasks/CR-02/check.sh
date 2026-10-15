#!/usr/bin/env bash
# CR-02 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

check_blocking cr02-comments-only protocol "Reviewer only added/removed comments (no logic change)" -- no_logic_changes
review_score "$TASK_DIR/review-spec.json"
check cr02-zero review_precision "Clean diff: zero REVIEW: comment outside known pre-existing issues" -- review_fp_at_most 0
check cr02-at-most-one review_precision "Clean diff: at most one REVIEW: comment outside known pre-existing issues" -- review_fp_at_most 1
check cr02-report protocol "Report says pass (zero comments)" -- report_mentions 'pass|zero|no (REVIEW )?comments|0 comments|clean'

finish
