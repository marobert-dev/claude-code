#!/usr/bin/env bash
# Shared setup for the kit scripts. Source it; do not execute it.

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export KIT
export EVAL_RUNS_DIR="${EVAL_RUNS_DIR:-$HOME/shoplite-runs}"
export WEB_TEAM_AGENTS_DIR="${WEB_TEAM_AGENTS_DIR:-$KIT/../web-team-agents}"
export TEAM_MEMORY_SRC="${TEAM_MEMORY_SRC:-$HOME/.mcp/team-memory}"

# A user-local .NET SDK (dotnet-install script) wins over a machine-wide host without SDK.
if [ -x "$HOME/.dotnet/dotnet" ] || [ -x "$HOME/.dotnet/dotnet.exe" ]; then
  export DOTNET_ROOT="$HOME/.dotnet"
  export PATH="$HOME/.dotnet:$PATH"
fi
export DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1

if command -v python3 >/dev/null 2>&1 && python3 -c "import sys" >/dev/null 2>&1; then
  PYTHON=python3
else
  PYTHON=python
fi
export PYTHON
# Windows consoles default to cp1252: printing non-ASCII (→, accents) from a check would crash it.
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8

# Exit code of run-agent.sh when Claude answered with an error (usage limit, auth…) instead of doing the task.
export EX_AGENT_CALL_FAILED=75

die () { printf 'error: %s\n' "$*" >&2; exit 1; }
info () { printf '==> %s\n' "$*" >&2; }

evalkit () { "$PYTHON" "$KIT/scripts/lib/evalkit.py" "$@"; }

run_name_of () { basename "$1"; }
meta_dir_of () { printf '%s/.meta/%s' "$(dirname "$1")" "$(basename "$1")"; }

task_field () {  # $1=task id  $2=json path (dot separated)
  evalkit task-field "$KIT/tasks/$1/task.json" "$2"
}
