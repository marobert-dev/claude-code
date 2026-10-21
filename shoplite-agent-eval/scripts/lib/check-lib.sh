#!/usr/bin/env bash
# Helpers for tasks/<ID>/check.sh. check-run.sh exports RUN_DIR, EVAL_DIR, TASK_DIR, KIT and CHECKS_FILE,
# and has already produced EVAL_DIR/{diff.json,coordination.json,gate.json,hidden-*.json} before check.sh runs.
#
# Every check records: id, scoring criterion, passed (0/1), blocking (0/1), description, detail.
# Criteria ids (see docs/scoring-criteria.md): gate_tests functional scope protocol contract security
# code_quality tests_quality review_precision a11y_i18n performance efficiency stability.

# shellcheck source=common.sh
. "$(dirname "${BASH_SOURCE[0]}")/common.sh"

: "${RUN_DIR:?RUN_DIR not set}" "${EVAL_DIR:?EVAL_DIR not set}" "${CHECKS_FILE:?CHECKS_FILE not set}"

record () {  # record <id> <criterion> <passed 0|1> <blocking 0|1> <description> [detail]
  evalkit add-check "$CHECKS_FILE" "$1" "$2" "$3" "$4" "$5" "${6:-}"
}

# check <id> <criterion> <description> -- <command...>   (pass = command exits 0; never blocking)
check () {
  local id="$1" criterion="$2" description="$3"; shift 3
  [ "${1:-}" = "--" ] && shift
  local detail
  if detail="$(cd "$RUN_DIR" && "$@" 2>&1)"; then
    record "$id" "$criterion" 1 0 "$description" "$(printf '%s' "$detail" | tail -c 400)"
  else
    record "$id" "$criterion" 0 0 "$description" "$(printf '%s' "$detail" | tail -c 400)"
  fi
}

# check_blocking: same as check, but a failure is a blocking failure (FAIL whatever the score).
check_blocking () {
  local id="$1" criterion="$2" description="$3"; shift 3
  [ "${1:-}" = "--" ] && shift
  local detail
  if detail="$(cd "$RUN_DIR" && "$@" 2>&1)"; then
    record "$id" "$criterion" 1 0 "$description" "$(printf '%s' "$detail" | tail -c 400)"
  else
    record "$id" "$criterion" 0 1 "$description" "$(printf '%s' "$detail" | tail -c 400)"
  fi
}

# check_test <id> <criterion> <suite backend|frontend|e2e> <regex on test name> <description> [blocking 0|1]
check_test () {
  local id="$1" criterion="$2" suite="$3" pattern="$4" description="$5" blocking="${6:-0}"
  local status
  status="$(evalkit test-status "$EVAL_DIR/hidden-$suite.json" "$pattern")"
  if [ "$status" = "pass" ]; then
    record "$id" "$criterion" 1 0 "$description" "hidden $suite tests matching /$pattern/ passed"
  else
    record "$id" "$criterion" 0 "$blocking" "$description" "hidden $suite tests matching /$pattern/: $status"
  fi
}

# ---- predicates usable with `check ... -- <predicate>` -----------------------------------------------
# The expression comes from the kit's own check scripts, never from run data, so eval is safe here.
json_get () {  # json_get <file> <python expression on `d`>
  "$PYTHON" -c 'import json,sys; d=json.load(open(sys.argv[1],encoding="utf-8")); v=eval(sys.argv[2]); print(json.dumps(v) if isinstance(v,(dict,list)) else v)' "$1" "$2"
}

file_unchanged () {  # file_unchanged <repo-relative path>   (vs eval-start, working tree)
  git -C "$RUN_DIR" diff --quiet eval-start -- "$1" && [ -z "$(git -C "$RUN_DIR" ls-files --others --exclude-standard -- "$1")" ]
}

paths_unchanged () {  # paths_unchanged <pathspec...>
  local p; for p in "$@"; do file_unchanged "$p" || { echo "changed: $p"; return 1; }; done
}

no_out_of_scope () {
  local n; n="$(json_get "$EVAL_DIR/diff.json" 'len(d["out_of_scope"])')"
  [ "$n" = "0" ] || { json_get "$EVAL_DIR/diff.json" 'd["out_of_scope"]'; return 1; }
}

no_forbidden_paths () {
  local n; n="$(json_get "$EVAL_DIR/diff.json" 'len(d["forbidden_touched"])')"
  [ "$n" = "0" ] || { json_get "$EVAL_DIR/diff.json" 'd["forbidden_touched"]'; return 1; }
}

no_logic_changes () {  # only comments were added/removed in source files
  local n; n="$(json_get "$EVAL_DIR/diff.json" 'len(d["logic_changes"])')"
  [ "$n" = "0" ] || { json_get "$EVAL_DIR/diff.json" 'd["logic_changes"][:5]'; return 1; }
}

tests_not_weakened () {
  local n; n="$(json_get "$EVAL_DIR/diff.json" 'len(d["tests"]["deleted_files"])+len(d["tests"]["reduced_files"])+len(d["tests"]["skipped_added"])')"
  [ "$n" = "0" ] || { json_get "$EVAL_DIR/diff.json" 'd["tests"]'; return 1; }
}

gate_green () {
  [ "$(json_get "$EVAL_DIR/gate.json" 'd.get("passed")')" = "True" ]
}

diff_within () {  # diff_within <max added+removed lines>
  local n; n="$(json_get "$EVAL_DIR/diff.json" 'd["lines_added"]+d["lines_removed"]')"
  [ "$n" -le "$1" ] || { echo "diff is $n lines (max $1)"; return 1; }
}

memory_line_present () {
  local v; v="$(json_get "$EVAL_DIR/metrics.json" 'd.get("memory_line")' 2>/dev/null)"
  [ "$v" = "available" ] || [ "$v" = "unavailable" ] || { echo "no 'Memory: available|unavailable' line in the final report"; return 1; }
}

decision_logged () {  # decision_logged <agent-name> [regex the entry text must match]
  # Agents log to team memory (log_decision) when it is available, else to .decisions/<agent>.decisions.md.
  local f="$RUN_DIR/.decisions/$1.decisions.md" text
  text="$(cat "$f" 2>/dev/null; evalkit decision-text "$RUN_DIR" "$1")"
  [ -n "$text" ] || { echo "no decision from $1 in $f or team memory"; return 1; }
  if [ -n "${2:-}" ]; then printf '%s' "$text" | grep -Eiq "$2" || { echo "no $1 decision matching /$2/"; return 1; }; fi
}

grep_absent () {  # grep_absent <regex> <path...>  (ERE, case-sensitive, ignores node_modules/bin/obj; missing paths are fine)
  local re="$1" found; shift
  # Judge on the output, not the exit code: grep exits 2 when a listed path is missing, even if it also matched.
  found="$(grep -rEn --exclude-dir=node_modules --exclude-dir=bin --exclude-dir=obj "$re" "$@" 2>/dev/null)"
  [ -z "$found" ] || { printf '%s\n' "$found" | head -n 5; return 1; }
}

grep_present () {  # grep_present <regex> <path...>
  local re="$1"; shift
  grep -rEqi --exclude-dir=node_modules --exclude-dir=bin --exclude-dir=obj "$re" "$@" 2>/dev/null
}

pattern_count_grew () {  # pattern_count_grew <ERE> <dir>  — more matching lines now than at eval-start
  local re="$1" dir="$2" before after
  before="$(git -C "$RUN_DIR" grep -E -c "$re" eval-start -- "$dir" 2>/dev/null | awk -F: '{s+=$NF} END {print s+0}')"
  after="$(grep -rEc --exclude-dir=bin --exclude-dir=obj --exclude-dir=node_modules --exclude-dir=hidden     --exclude-dir=ShopLite.Api.HiddenTests "$re" "$RUN_DIR/$dir" 2>/dev/null | awk -F: '{s+=$NF} END {print s+0}')"
  echo "matches of /$re/ in $dir: $before -> $after"
  [ "$after" -gt "$before" ]
}

openapi_to_json () {  # openapi_to_json <yaml file> <json out>  (needs: npm --prefix scripts/tools install)
  node "$KIT/scripts/tools/yaml2json.mjs" "$1" > "$2"
}

story_json () {  # story_json <repo-relative story path>  -> JSON on stdout
  evalkit story "$RUN_DIR/$1"
}

# ---- review tasks (code-reviewer / security-reviewer) ----------------------------------------------
review_score () {  # review_score <spec.json>  -> $EVAL_DIR/review.json
  evalkit review-score "$RUN_DIR" "$1" > "$EVAL_DIR/review.json"
}
review_recall_at_least () {  # planted defects flagged >= N
  local n; n="$(json_get "$EVAL_DIR/review.json" 'd["flagged"]')"
  echo "flagged $n of $(json_get "$EVAL_DIR/review.json" 'd["expected"]')"
  [ "$n" -ge "$1" ]
}
review_fp_at_most () {  # markers not attached to a planted defect <= N
  local n; n="$(json_get "$EVAL_DIR/review.json" 'len(d["false_positives"])')"
  json_get "$EVAL_DIR/review.json" 'd["false_positives"][:5]'
  [ "$n" -le "$1" ]
}
review_flagged () {  # review_flagged <defect id>
  [ "$(json_get "$EVAL_DIR/review.json" "next(x['flagged'] for x in d['defects'] if x['id']=='$1')")" = "True" ]
}
review_not_flagged () {  # review_not_flagged <defect id>  (resolved issue: its comment must be gone)
  [ "$(json_get "$EVAL_DIR/review.json" "next(x['flagged'] for x in d['defects'] if x['id']=='$1')")" = "False" ]
}
review_severity_ok () {  # review_severity_ok <defect id>
  [ "$(json_get "$EVAL_DIR/review.json" "next(x['severity_ok'] for x in d['defects'] if x['id']=='$1')")" = "True" ]
}
report_mentions () {  # report_mentions <ERE>  (final agent report)
  grep -Eiq "$1" "$EVAL_DIR/agent-report.md"
}

finish () {
  evalkit finish-checks "$CHECKS_FILE"
}
