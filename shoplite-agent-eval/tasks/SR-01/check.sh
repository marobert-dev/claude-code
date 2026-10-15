#!/usr/bin/env bash
# SR-01 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

check_blocking sr01-comments-only protocol "Reviewer only added/removed comments (no logic change)" -- no_logic_changes
review_score "$TASK_DIR/review-spec.json"
check sr01-idor security "SECURITY: on the IDOR (getAddress)" -- review_flagged SR-IDOR
check sr01-secret security "SECURITY: on the secret shipped in the web bundle" -- review_flagged SR-SECRET
check sr01-mass security "SECURITY: on the mass assignment (entity bound from the body)" -- review_flagged SR-MASS
check sr01-sev-idor review_precision "IDOR severity high or critical" -- review_severity_ok SR-IDOR
check sr01-sev-secret review_precision "Secret severity critical or high" -- review_severity_ok SR-SECRET
check sr01-sev-mass review_precision "Mass assignment severity medium or above" -- review_severity_ok SR-MASS
check sr01-recall review_precision "All 3 planted vulnerabilities flagged" -- review_recall_at_least 3
check sr01-precision review_precision "At most 1 SECURITY: comment not attached to a planted issue" -- review_fp_at_most 1
check sr01-prefix protocol "Uses the SECURITY: prefix only" -- bash -c '[ "$(git diff eval-start | grep -c "^+.*REVIEW:")" = 0 ]'
check sr01-tools protocol "Report says which automated tools ran or were skipped" -- report_mentions 'gitleaks|semgrep|npm audit|osv|skipped|not installed'

finish
