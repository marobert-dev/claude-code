#!/usr/bin/env bash
# Deterministic bookkeeping for product-manager, so it spends no tokens on file shuffling.
# Run from the workspace root:  bash .claude/hooks/pm-state.sh <command> [args]
#
#   start                          Archive and print the latest handoff, list the queue in processing order,
#                                  report whether conventions.md and gate.sh exist.
#                                  Empty queue: writes EMPTY to the status file and exits 3.
#   validated <story-file>         Save the story to .stories-reviewed/, report its acceptance-criteria boxes.
#                                  Exit 0 = every box checked, 1 = some unchecked (listed on stdout).
#   finish completed <story-file>  Move the story to .completed/ and write COMPLETED <slug> to the status file.
#   finish failed <story-file>     Leave the story queued and write FAILED <slug> to the status file.
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
  [ -f .pipeline/conventions.md ] && echo "CONVENTIONS present" || echo "CONVENTIONS missing"
  [ -f .claude/hooks/gate.sh ] && echo "GATE present" || echo "GATE missing"
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
  ':(exclude).claude/run.log'
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
  validated)  cmd_validated "${2:-}" ;;
  finish)     cmd_finish "${2:-}" "${3:-}" ;;
  git-branch) shift; cmd_git_branch "$@" ;;
  git-stage)  cmd_git_stage "${2:-}" ;;
  *) die "usage: pm-state.sh start | validated <story> | finish completed|failed <story> | git-branch <story> <repo>... | git-stage <repo>" ;;
esac
