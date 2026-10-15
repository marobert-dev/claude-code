#!/usr/bin/env bash
# Create an isolated run of one task: scripts/new-run.sh <TASK-ID> <n> [--force] [--no-install]
#
#   1. copies app-template/ to $EVAL_RUNS_DIR/<TASK-ID>-run<n>/ (default ~/shoplite-runs, outside the kit)
#   2. git init + baseline commit, tag eval-base
#   3. installs tasks/<TASK-ID>/fixtures/workspace/ over the run (+ golden conventions when task.json asks for it)
#      and commits the tracked part as "fixtures" when task.json has fixtures_commit_message; tag eval-start
#   4. removes .pipeline/team-memory.db*, then seeds team memory from fixtures/team-memory-seed.json if present
#   5. installs dependencies (npm ci root + frontend, dotnet restore) unless --no-install
# Evaluation metadata (baselines, raw agent output) lives in $EVAL_RUNS_DIR/.meta/<run>/, never inside the run.
set -euo pipefail
# shellcheck source=lib/common.sh
. "$(dirname "$0")/lib/common.sh"

TASK="${1:-}"; N="${2:-}"
[ -n "$TASK" ] && [ -n "$N" ] || die "usage: new-run.sh <TASK-ID> <n> [--force] [--no-install]"
shift 2
FORCE=0; INSTALL=1
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    --no-install) INSTALL=0 ;;
    *) die "unknown option $arg" ;;
  esac
done

TASK_DIR="$KIT/tasks/$TASK"
[ -f "$TASK_DIR/task.json" ] || die "unknown task $TASK (no $TASK_DIR/task.json)"
RUN="$EVAL_RUNS_DIR/$TASK-run$N"
META="$EVAL_RUNS_DIR/.meta/$TASK-run$N"

if [ -e "$RUN" ]; then
  [ "$FORCE" = 1 ] || die "$RUN already exists (use --force to recreate it)"
  rm -rf "$RUN" "$META"
fi
mkdir -p "$RUN" "$META"

info "copying app-template -> $RUN"
tar -C "$KIT/app-template" \
  --exclude=node_modules --exclude=bin --exclude=obj --exclude=dist \
  --exclude=test-results --exclude=playwright-report --exclude=.pipeline \
  -cf - . | tar -C "$RUN" -xf -

cd "$RUN"
git init -q -b main
git config user.name "ShopLite Dev"
git config user.email "dev@shoplite.local"
git config core.autocrlf false
printf '.eval/\n' >> .git/info/exclude
git add -A
git commit -q -m "ShopLite baseline"
git tag eval-base

FIX="$TASK_DIR/fixtures"
if [ -d "$FIX/workspace" ]; then
  info "installing fixtures"
  cp -R "$FIX/workspace/." "$RUN/"
fi
if [ "$(task_field "$TASK" conventions)" = "true" ]; then
  mkdir -p "$RUN/.pipeline"
  cp "$KIT/fixtures/conventions.golden.md" "$RUN/.pipeline/conventions.md"
fi
for d in .user-stories .stories-reviewed .validated-stories .completed .decisions; do
  [ -d "$RUN/$d" ] && find "$RUN/$d" -name '.gitkeep' -delete
done

COMMIT_MSG="$(task_field "$TASK" fixtures_commit_message)"
if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -q -m "${COMMIT_MSG:-Update shared project files}"
fi
# Optional second stage (e.g. a fix on top of a reviewed change, for re-review tasks).
if [ -d "$FIX/workspace.2" ]; then
  cp -R "$FIX/workspace.2/." "$RUN/"
  git add -A
  git commit -q -m "$(task_field "$TASK" fixtures_commit_message_2)"
fi
git tag eval-start

rm -f "$RUN"/.pipeline/team-memory.db*
if [ -f "$FIX/team-memory-seed.json" ]; then
  [ -f "$TEAM_MEMORY_SRC/store.py" ] || die "team-memory seed requested but $TEAM_MEMORY_SRC/store.py is missing (set TEAM_MEMORY_SRC)"
  info "seeding team memory"
  evalkit seed-memory "$RUN" "$FIX/team-memory-seed.json" "$TEAM_MEMORY_SRC" >/dev/null
fi

evalkit snapshot-coord "$RUN" "$META/coord-baseline.json"
evalkit decisions "$RUN" /dev/null > "$META/decisions-baseline.json"

KIT_SHA="$(git -C "$KIT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
if [ -n "$(git -C "$KIT" status --porcelain -- . 2>/dev/null)" ]; then KIT_SHA="$KIT_SHA-dirty"; fi
AGENTS_SHA="$(git -C "$WEB_TEAM_AGENTS_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
CLAUDE_VERSION="$(claude --version 2>/dev/null | head -n1 || echo unknown)"
"$PYTHON" - "$META/run.json" "$TASK" "$N" "$KIT_SHA" "$AGENTS_SHA" "$CLAUDE_VERSION" <<'PY'
import datetime, json, sys
path, task, n, kit, agents, claude = sys.argv[1:]
json.dump({"task": task, "run": int(n), "kit_sha": kit, "agents_sha": agents, "claude_version": claude,
           "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")},
          open(path, "w", encoding="utf-8"), indent=2)
PY

if [ "$INSTALL" = 1 ]; then
  info "installing dependencies (npm ci, dotnet restore)"
  npm ci --no-audit --no-fund --loglevel=error >/dev/null
  npm --prefix frontend ci --no-audit --no-fund --loglevel=error >/dev/null
  dotnet restore backend/ShopLite.sln -v q >/dev/null
fi

info "run ready: $RUN"
echo "$RUN"
