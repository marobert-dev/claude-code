#!/usr/bin/env bash
# Deterministic bookkeeping for product-manager, so it spends no tokens on file shuffling.
# Run from the workspace root:  bash .claude/hooks/pm-state.sh <command> [args]
#
#   start                          Archive and print the latest handoff, list the queue in processing order,
#                                  report whether conventions.md (present/outdated/missing) and gate.sh exist, and
#                                  whether the dev agents' stop is wired to it (GATE hook wired|missing|duplicated|unknown).
#                                  Empty queue: writes EMPTY to the status file and exits 3.
#   criteria <story-file>          Print only the story's acceptance criteria.
#   plan-check <story-file>|--latest
#                                  Check the analyst's Technical Plan layout (a Scope: line, only the fixed ### subsections,
#                                  no e2e test file outside tests/e2e/<slug>/). Prints "PLAN ok scope=<..> visual=<yes|no>",
#                                  or "PLAN invalid" and the problems with exit 2. --latest = the newest story file.
#   append <story-file> "<## Heading>"
#                                  Append a section (body on stdin) to the story file, so it never has to be read back.
#   validated <story-file>         Save the story to .stories-reviewed/, report its acceptance-criteria boxes.
#                                  Exit 0 = every box checked, 1 = some unchecked (listed on stdout).
#   finish completed <story-file>  Move the story to .completed/ and write COMPLETED <slug> to the status file.
#   finish failed <story-file>     Leave the story queued and write FAILED <slug> to the status file.
#                                  Both print the periodic duties now due ("DUE digest", "DUE refresh") from the number of
#                                  completed stories, so every session follows the same schedule.
#   git-branch <story-file> <repo>...
#                                  In each repo: checkout dev, pull, create feature/<NN>-<description> off dev.
#   git-stage <repo>               Stage every change in <repo> except coordination state, print what is staged.
#                                  Does not commit: product-manager checks the list, then commits.
# <slug> is the story filename without .md, e.g. 01-create-user-login.

set -u
STATUS=".pipeline/pm-last-run.txt"
HANDOFFS=".pipeline/handoffs"
EXIT_EMPTY_QUEUE=3

die () { echo "pm-state: $*" >&2; exit 2; }
slug_of () { basename "$1" .md; }
require_story () { [ -n "${1:-}" ] && [ -f "$1" ] || die "story file not found: ${1:-<missing>}"; }
write_status () { mkdir -p .pipeline; echo "$1" > "$STATUS"; }

# Does a dev agent's stop reach gate.sh exactly once? Counts the SubagentStop hooks calling it in the settings files
# Claude Code merges, plus a gate.sh call in the agent's own frontmatter (the old placement, a second trigger). The JSON
# is parsed because permissions name gate.sh too, and the agents' frontmatter is cut off because their bodies do as well.
# Prints wired, missing (some dev agent gets no gate), duplicated, or unknown (neither jq nor node to read the settings).
gate_hook_status () {
  local f n x file lo=99 hi=0 t declared=0 agents_dir="${CLAUDE_AGENTS_DIR:-$HOME/.claude/agents}"
  for f in .claude/settings.json .claude/settings.local.json "$HOME/.claude/settings.json"; do
    [ -f "$f" ] || continue
    if command -v jq >/dev/null 2>&1; then
      n="$(jq '[.hooks.SubagentStop[]?.hooks[]? | select((.command // "") | contains("gate.sh"))] | length' "$f" 2>/dev/null)"
    elif command -v node >/dev/null 2>&1; then
      n="$(node -e 'const h=(JSON.parse(require("fs").readFileSync(process.argv[1],"utf8")).hooks||{}).SubagentStop||[];console.log(h.flatMap(e=>e.hooks||[]).filter(x=>(x.command||"").includes("gate.sh")).length)' "$f" 2>/dev/null)"
    else
      echo unknown; return
    fi
    declared=$(( declared + ${n:-0} ))
  done
  for x in dev-frontend dev-backend dev-integrator; do
    file=".claude/agents/$x.md"; [ -f "$file" ] || file="$agents_dir/$x.md"
    t=$declared
    if [ -f "$file" ] && awk 'NR==1{if ($0 ~ /^---/) front=1; next} front && /^---/{exit} front' "$file" | grep -q 'hooks/gate.sh'; then t=$(( t + 1 )); fi
    [ "$t" -lt "$lo" ] && lo=$t
    [ "$t" -gt "$hi" ] && hi=$t
  done
  if [ "$lo" -eq 0 ]; then echo missing; elif [ "$hi" -gt 1 ]; then echo duplicated; else echo wired; fi
}

cmd_start () {
  local latest
  latest="$(ls -t "$HANDOFFS"/*.md 2>/dev/null | head -n 1)"
  if [ -n "$latest" ]; then
    mkdir -p "$HANDOFFS/archive"
    echo "HANDOFF $latest (archived)"
    cat "$latest"
    echo "END HANDOFF"
    mv "$latest" "$HANDOFFS/archive/"
  else
    echo "HANDOFF none"
  fi

  local stories
  stories="$(ls .user-stories/*.md 2>/dev/null | sort)"
  if [ ! -f .pipeline/conventions.md ]; then echo "CONVENTIONS missing"
  # Written before conventions-scout copied the project's CLAUDE.md/AGENTS.md rules, which subagents no longer load.
  elif ! grep -q '^## Project rules' .pipeline/conventions.md; then echo "CONVENTIONS outdated"
  else echo "CONVENTIONS present"; fi
  if [ -f .claude/hooks/gate.sh ]; then echo "GATE present"; echo "GATE hook $(gate_hook_status)"; else echo "GATE missing"; fi
  # Test, lint and type-check settings already modified now become the baseline the gate compares against.
  [ -f .claude/hooks/role-guard.sh ] && { bash .claude/hooks/role-guard.sh protected-snapshot < /dev/null 2>/dev/null || true; }
  if [ -z "$stories" ]; then
    write_status "EMPTY"
    echo "QUEUE empty"
    exit "$EXIT_EMPTY_QUEUE"
  fi
  echo "QUEUE"
  echo "$stories"
}

acceptance_criteria () {
  awk '/^## Acceptance Criteria/{f=1;next} /^## /{f=0} f' "$1"
}

cmd_criteria () {
  require_story "${1:-}"
  acceptance_criteria "$1"
}

PLAN_SUBSECTIONS="shared|backend|web|mobile|existing code to change"

cmd_plan_check () {
  local story="${1:-}"
  if [ "$story" = "--latest" ]; then
    story="$(ls -t .user-stories/*.md 2>/dev/null | head -n 1)"
    [ -n "$story" ] || { echo "PLAN none (no story file)"; return 0; }
  fi
  require_story "$story"
  local slug plan scope_line scopes problems="" h p visual=no
  slug="$(slug_of "$story")"
  plan="$(awk '/^## Technical Plan[[:space:]]*$/{f=1;next} /^## /{f=0} f' "$story")"
  if [ -z "$(printf '%s' "$plan" | tr -d '[:space:]')" ]; then
    problems="- no '## Technical Plan' section with content"
  else
    scope_line="$(printf '%s\n' "$plan" | grep -m1 -v '^[[:space:]]*$')"
    scopes="$(printf '%s' "$scope_line" | sed -n 's/^Scope:[[:space:]]*//p' | tr 'A-Z' 'a-z' | tr -s ' ,/+&|' '\n' | grep -v '^and$' | grep -v '^$' | sort -u | paste -sd ',' -)"
    if [ -z "$scopes" ]; then
      problems="$problems
- the plan's first line must be 'Scope: <web | mobile | backend — one or more>', found: ${scope_line:0:80}"
    else
      for p in ${scopes//,/ }; do
        case "$p" in web|mobile|backend) ;; *) problems="$problems
- unknown scope '$p' (allowed: web, mobile, backend)" ;; esac
      done
    fi
    while IFS= read -r h; do
      printf '%s' "$h" | sed 's/^###[[:space:]]*//; s/[[:space:]]*$//' | tr 'A-Z' 'a-z' | grep -Eqx "$PLAN_SUBSECTIONS" \
        || problems="$problems
- subsection '$h' is not part of the layout (only ### Shared, ### Backend, ### Web, ### Mobile, ### Existing code to change)"
    done < <(printf '%s\n' "$plan" | grep '^###')
    # A path that already exists is a reference to an earlier story's tests; a new one outside this story's folder
    # is the analyst planning e2e files, which story-validator owns.
    while IFS= read -r p; do
      case "$p" in *"tests/e2e/$slug"|*"tests/e2e/$slug/"*) continue ;; esac
      [ -e "$p" ] && continue
      problems="$problems
- the plan names e2e test file '$p': story-validator owns tests/e2e/$slug/ and decides its files, titles and tags"
    done < <(printf '%s\n' "$plan" | grep -oE '([A-Za-z0-9._-]+/)*tests/e2e/[A-Za-z0-9._/-]*[A-Za-z0-9_/-]' | sort -u)
  fi
  grep -q '^## Visual Definition' "$story" && visual=yes
  if [ -n "$problems" ]; then
    printf 'PLAN invalid (%s)%s\n' "$story" "$problems"
    return 2
  fi
  echo "PLAN ok scope=$scopes visual=$visual"
}

cmd_append () {
  require_story "${1:-}"
  local heading="${2:-}"
  case "$heading" in "## "*) ;; *) die "append needs a '## ' heading, got: ${heading:-<missing>}" ;; esac
  local body; body="$(cat)"
  [ -n "$(printf '%s' "$body" | tr -d '[:space:]')" ] || die "append: empty body on stdin"
  # One blank line before the new section, whatever the file ended with.
  [ -n "$(tail -c 1 "$1")" ] && printf '\n' >> "$1"
  printf '\n%s\n\n%s\n' "$heading" "$body" >> "$1"
  echo "APPENDED $heading"
}

print_due () {  # print_due completed|failed: the periodic duties the schedule says are due now
  local n queued
  n="$(ls .completed/*.md 2>/dev/null | wc -l | tr -d ' ')"
  queued="$(ls .user-stories/*.md 2>/dev/null | wc -l | tr -d ' ')"
  echo "COMPLETED_TOTAL $n"
  if [ "$1" = failed ] || [ "$queued" -eq 0 ] || [ $((n % 3)) -eq 0 ]; then echo "DUE digest"; fi
  if [ "$1" = completed ] && [ "$n" -gt 0 ] && [ $((n % 6)) -eq 0 ]; then echo "DUE refresh"; fi
}

cmd_validated () {
  require_story "${1:-}"
  mkdir -p .stories-reviewed
  cp "$1" ".stories-reviewed/$(basename "$1")"
  local criteria checked unchecked
  criteria="$(acceptance_criteria "$1")"
  checked="$(printf '%s\n' "$criteria" | grep -cE '^[[:space:]]*- \[[xX]\]')"
  unchecked="$(printf '%s\n' "$criteria" | grep -cE '^[[:space:]]*- \[ \]')"
  echo "SAVED .stories-reviewed/$(basename "$1")"
  echo "CRITERIA checked=$checked unchecked=$unchecked"
  [ "$checked" -gt 0 ] || die "no acceptance-criteria checkboxes found in $1"
  [ "$unchecked" -eq 0 ] && return 0
  printf '%s\n' "$criteria" | grep -E '^[[:space:]]*- \[ \]'
  return 1
}

cmd_finish () {
  local outcome="${1:-}" story="${2:-}"
  require_story "$story"
  case "$outcome" in
    completed)
      mkdir -p .completed
      mv "$story" ".completed/$(basename "$story")"
      write_status "COMPLETED $(slug_of "$story")" ;;
    failed)
      write_status "FAILED $(slug_of "$story")" ;;
    *) die "finish expects completed|failed, got: ${outcome:-<missing>}" ;;
  esac
  echo "STATUS $(cat "$STATUS")"
  print_due "$outcome"
}

cmd_git_branch () {
  require_story "${1:-}"
  local branch="feature/$(slug_of "$1")"; shift
  [ $# -gt 0 ] || die "git-branch needs at least one repo"
  local repo
  for repo in "$@"; do
    git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not a git repo: $repo"
    git -C "$repo" checkout dev && git -C "$repo" pull && git -C "$repo" checkout -b "$branch" \
      || die "branch setup failed in $repo"
    echo "BRANCH $repo $branch"
  done
}

# Coordination state never committed (README "Files produced"); .claude/run.log is written by run-parallel.sh.
COORDINATION_EXCLUDES=(
  ':(exclude).user-stories' ':(exclude).stories-reviewed' ':(exclude).validated-stories'
  ':(exclude).completed' ':(exclude).decisions' ':(exclude).pipeline/pm-progress.md'
  ':(exclude).pipeline/pm-last-run.txt' ':(exclude).pipeline/decisions-digest.md'
  ':(exclude,glob).pipeline/team-memory.db*' ':(exclude).pipeline/handoffs' ':(exclude).pipeline/gate-pass'
  ':(exclude).pipeline/gate.log' ':(exclude).claude/run.log'
)

cmd_git_stage () {
  local repo="${1:-}"
  [ -n "$repo" ] || die "git-stage needs a repo"
  git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not a git repo: $repo"
  git -C "$repo" add -A -- . "${COORDINATION_EXCLUDES[@]}" || die "staging failed in $repo"
  echo "STAGED $repo"
  git -C "$repo" diff --cached --name-status
}

case "${1:-}" in
  start)      cmd_start ;;
  criteria)   cmd_criteria "${2:-}" ;;
  plan-check) cmd_plan_check "${2:-}" ;;
  append)     cmd_append "${2:-}" "${3:-}" ;;
  validated)  cmd_validated "${2:-}" ;;
  finish)     cmd_finish "${2:-}" "${3:-}" ;;
  git-branch) shift; cmd_git_branch "$@" ;;
  git-stage)  cmd_git_stage "${2:-}" ;;
  *) die "usage: pm-state.sh start | criteria <story> | plan-check <story>|--latest | append <story> '<## Heading>' | validated <story> | finish completed|failed <story> | git-branch <story> <repo>... | git-stage <repo>" ;;
esac
