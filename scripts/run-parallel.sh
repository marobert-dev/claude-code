#!/usr/bin/env bash
# Runs up to N INDEPENDENT stories in parallel, each in its own git worktree + fresh headless
# product-manager session. Independence comes from the "## Dependencies" section product-owner
# writes in every story: a story is READY when every story file it lists is already in .completed/.
#
# Usage (from the workspace root, which must be a single git repo with a `dev` branch):
#     bash scripts/run-parallel.sh [N=2] [--dry-run]
#
# Limits (by design):
#   - Single-repo workspaces only (the root itself is the git repo).
#   - Each story ends on its own branch `feature/<slug>`. Merging into `dev` stays manual/PR-based,
#     because parallel stories can conflict. Cross-story regression checks happen on the next
#     sequential run (scripts/run-queue.sh) once the branches are merged.
#   - Coordination state (.completed, .validated-stories, ...) is copied back into the main
#     workspace when a session finishes.
# Env: CLAUDE_FLAGS (default "--permission-mode acceptEdits"), PM_EXTRA (extra prompt text).
set -u
N=2; DRY=0
for a in "$@"; do case "$a" in --dry-run) DRY=1 ;; ''|*[!0-9]*) ;; *) N="$a" ;; esac; done
FLAGS="${CLAUDE_FLAGS:---permission-mode acceptEdits}"
ROOT="$(pwd)"; REPO="$(basename "$ROOT")"
# All worktree sessions share the main workspace's team-memory database (the server also resolves this itself via git).
export TEAM_MEMORY_DB="${TEAM_MEMORY_DB:-$ROOT/.claude/team-memory.db}"

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { echo "Not a git repo (single-repo workspaces only)."; exit 1; }
[ -d .user-stories ] || { echo "No .user-stories/ folder."; exit 1; }
mkdir -p .completed .validated-stories .stories-reviewed .decisions .claude

deps_of () {  # prints story filenames listed under "## Dependencies"
  awk '/^## Dependencies/{f=1;next} /^## /{f=0} f' "$1" | grep -oE '[0-9]+-[A-Za-z0-9._-]+\.md' || true
}

READY=()
for f in $(ls .user-stories/*.md 2>/dev/null | sort); do
  ok=1
  for d in $(deps_of "$f"); do [ -f ".completed/$d" ] || { ok=0; break; }; done
  [ $ok -eq 1 ] && READY+=("$f")
  [ ${#READY[@]} -ge "$N" ] && break
done

if [ ${#READY[@]} -eq 0 ]; then echo "No ready stories (empty queue, or all blocked by dependencies)."; exit 0; fi
echo "Ready (${#READY[@]}): ${READY[*]}"
[ $DRY -eq 1 ] && exit 0

PIDS=(); WTS=()
for f in "${READY[@]}"; do
  base="$(basename "$f")"; slug="${base#*-}"; slug="${slug%.md}"
  wt="$ROOT/../${REPO}-wt-${slug}"
  if [ ! -d "$wt" ]; then
    git worktree add "$wt" -b "feature/${slug}" dev >/dev/null 2>&1 || git worktree add "$wt" "feature/${slug}" || { echo "worktree failed for $slug"; continue; }
  fi
  mkdir -p "$wt/.user-stories" "$wt/.claude" "$wt/.completed" "$wt/.validated-stories" "$wt/.stories-reviewed" "$wt/.decisions"
  cp "$f" "$wt/.user-stories/$base"
  cp -r .validated-stories/. "$wt/.validated-stories/" 2>/dev/null
  cp -r .completed/. "$wt/.completed/" 2>/dev/null
  [ -f .claude/conventions.md ] && cp .claude/conventions.md "$wt/.claude/"
  [ -f .claude/decisions-digest.md ] && cp .claude/decisions-digest.md "$wt/.claude/"
  [ -d .claude/hooks ] && { mkdir -p "$wt/.claude/hooks"; cp -r .claude/hooks/. "$wt/.claude/hooks/"; }
  [ -f .claude/settings.json ] && cp .claude/settings.json "$wt/.claude/"
  [ -d contracts ] && [ ! -d "$wt/contracts" ] && cp -r contracts "$wt/contracts"
  rm -f "$wt/.claude/pm-last-run.txt"
  echo "[parallel] starting $slug in $wt"
  # shellcheck disable=SC2086
  ( cd "$wt" && claude -p "ONE STORY MODE. WORKTREE MODE: branch feature/${slug} already exists and is checked out; skip branch creation. Git management: enabled. Process exactly this one story, then checkpoint and stop. ${PM_EXTRA:-}" --agent product-manager $FLAGS > ".claude/run.log" 2>&1 ) &
  PIDS+=($!); WTS+=("$wt|$base")
done

for p in "${PIDS[@]}"; do wait "$p"; done

for item in "${WTS[@]}"; do
  wt="${item%%|*}"; base="${item##*|}"
  st="$(cat "$wt/.claude/pm-last-run.txt" 2>/dev/null || echo UNKNOWN)"
  echo "[parallel] $base -> $st  (log: $wt/.claude/run.log)"
  # always bring back the reviewed copy and decision logs
  [ -f "$wt/.stories-reviewed/$base" ] && cp "$wt/.stories-reviewed/$base" ".stories-reviewed/$base"
  for d in "$wt"/.decisions/*.md; do [ -f "$d" ] && cat "$d" >> ".decisions/$(basename "$d")"; done
  case "$st" in
    COMPLETED*)
      [ -f "$wt/.completed/$base" ] && cp "$wt/.completed/$base" ".completed/$base"
      [ -f "$wt/.validated-stories/$base" ] && cp "$wt/.validated-stories/$base" ".validated-stories/$base"
      rm -f ".user-stories/$base" ;;
    *)
      [ -f "$wt/.user-stories/$base" ] && cp "$wt/.user-stories/$base" ".user-stories/$base" ;;
  esac
done
echo "[parallel] done. Merge the feature/<slug> branches into dev yourself, then re-run scripts/run-queue.sh for regression checks."
