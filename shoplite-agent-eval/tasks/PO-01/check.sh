#!/usr/bin/env bash
# PO-01 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
. "$KIT/scripts/lib/check-lib.sh"

po () { "$PYTHON" "$KIT/tasks/_shared/po_checks.py" "$RUN_DIR" "$@"; }

check po01-count protocol "At least 3 stories, files named NN-slug.md, contiguous numbering" -- po count 3
check po01-template protocol "Exact story template, no section reserved to other agents" -- po template
check po01-criteria protocol "Each story has >= 2 unchecked checkbox criteria" -- po criteria
check po01-visual protocol "Visual Definition with Appearance / Needs / Rationale" -- po visual
check po01-copy a11y_i18n "Every visible story has a complete Copy (FR/EN) table" -- po copy
check po01-deps functional "Dependencies honest: None or earlier existing story files" -- po dependencies
check po01-parallel functional "At least one independent story (Dependencies: None)" -- po none-dependency
check po01-english protocol "Titles and criteria in English (only the copy is bilingual)" -- po english
check po01-testable functional "No vague criterion without (manual)" -- po testable
check po01-topics-core functional "Covers at least 5 of 8 expected review topics" -- po topics 5 "$TASK_DIR/topics.json"
check po01-topics-all functional "Covers at least 7 of 8 expected review topics" -- po topics 7 "$TASK_DIR/topics.json"
check po01-summary protocol "One-line summary with story count and folder" -- report_mentions '[0-9]+ .*stor|\.user-stories'

finish
