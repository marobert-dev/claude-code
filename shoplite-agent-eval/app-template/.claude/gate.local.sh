#!/usr/bin/env bash
# Workspace gate, run by .claude/hooks/gate.sh instead of its auto-detection.
# Why it exists: the auto-detection only recognises a .NET folder holding both a *.sln and a *.csproj,
# and backend/ holds only ShopLite.sln, so dotnet build/test would be skipped silently.
# Honours the same switches as gate.sh: GATE_SKIP_BUILD=1, GATE_SKIP_TESTS=1.
set -u
ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$ROOT" || exit 1

FAILED=0
run_step () {  # $1=label  $2=dir  $3...=command
  local label="$1" dir="$2"; shift 2
  local out rc
  out="$(cd "$dir" && "$@" 2>&1)"; rc=$?
  if [ $rc -ne 0 ]; then
    FAILED=1
    printf -- '--- %s (%s) FAILED ---\n%s\n' "$label" "$dir" "$(printf '%s' "$out" | tail -n 40)"
  else
    printf -- '--- %s (%s) ok\n' "$label" "$dir"
  fi
}

run_step "npm lint"      frontend npm run --silent lint
run_step "npm typecheck" frontend npm run --silent typecheck
[ -z "${GATE_SKIP_BUILD:-}" ] && run_step "npm build" frontend npm run --silent build
[ -z "${GATE_SKIP_TESTS:-}" ] && run_step "npm test"  frontend env CI=true npm test --silent

run_step "dotnet build" backend dotnet build ShopLite.sln --nologo -v q
[ -z "${GATE_SKIP_TESTS:-}" ] && run_step "dotnet test" backend dotnet test ShopLite.sln --nologo --no-build -v q

exit $FAILED
