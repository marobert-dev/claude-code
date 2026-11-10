#!/usr/bin/env bash
# Runs learn.py with the first working Python >= 3.9 (Windows: skips the Microsoft Store stub).
# Override with LEARN_PYTHON. Always forces UTF-8.
set -u
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8

CHECK='import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'

try_python() {
  # $@ = interpreter command (may be two words: py -3)
  command -v "$1" >/dev/null 2>&1 || return 1
  "$@" -c "$CHECK" >/dev/null 2>&1 || return 1
  return 0
}

if [ -n "${LEARN_PYTHON:-}" ] && try_python "$LEARN_PYTHON"; then
  exec "$LEARN_PYTHON" "$DIR/learn.py" "$@"
fi
for cand in python3 python; do
  if try_python "$cand"; then exec "$cand" "$DIR/learn.py" "$@"; fi
done
if try_python py -3; then exec py -3 "$DIR/learn.py" "$@"; fi

echo "learning-memory: no Python >= 3.9 found (set LEARN_PYTHON)" >&2
# Never break a hook: exit 0 for hook subcommands, 1 for interactive ones.
case "${1:-}" in load|capture|sweep|analyze) exit 0 ;; *) exit 1 ;; esac
