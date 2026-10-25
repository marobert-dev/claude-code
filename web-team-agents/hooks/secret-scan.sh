#!/usr/bin/env bash
# Deterministic secret scan for security-reviewer; no LLM involved. Prints "file:line: rule: masked match" for every
# likely secret in the given files, or, with no argument, in every changed or untracked file of the workspace's git
# repositories (the root and its immediate subdirectories). Exit 1 when it finds something, 0 otherwise.
#   bash .claude/hooks/secret-scan.sh [file...]
# Covers well-known key formats (a fallback when gitleaks is not installed) plus one rule gitleaks does not apply:
# a secret-looking name behind a client-exposed prefix (VITE_, NEXT_PUBLIC_, REACT_APP_, EXPO_PUBLIC_, NUXT_PUBLIC_,
# GATSBY_, PUBLIC_), because build tools ship those values to every browser. Hits are leads to judge, not verdicts:
# demo passwords in seed data or fake keys in test fixtures match too.
set -u

# rule|grep flags|pattern  (the pattern may itself contain "|")
RULES='private-key||-----BEGIN ([A-Z]+ )?PRIVATE KEY-----
stripe-secret-key||(sk|rk)_(live|test)_[0-9A-Za-z]{10,}
aws-access-key||(AKIA|ASIA)[0-9A-Z]{16}
github-token||(gh[pousr]_[0-9A-Za-z]{30,}|github_pat_[0-9A-Za-z_]{40,})
slack-token||xox[abprs]-[0-9A-Za-z-]{10,}
google-api-key||AIza[0-9A-Za-z_-]{35}
jwt||eyJ[0-9A-Za-z_-]{10,}\.eyJ[0-9A-Za-z_-]{10,}\.[0-9A-Za-z_-]{10,}
client-exposed-secret||(VITE|NEXT_PUBLIC|REACT_APP|EXPO_PUBLIC|NUXT_PUBLIC|GATSBY|PUBLIC)_[A-Z0-9_]*(SECRET|PRIVATE|PASSWORD|PASSWD|TOKEN|API_?KEY|CLIENT_KEY)[A-Z0-9_]*
hardcoded-credential|-i|(password|passwd|pwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret)["'"'"']?[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"'[:space:]]{8,}["'"'"']
connection-string-password|-i|(password|pwd)=[^;"'"'"'[:space:]]{4,}'

changed_files () {
  local d top f
  for d in . $(find . -mindepth 1 -maxdepth 1 -type d ! -name '.*' ! -name node_modules -printf '%f ' 2>/dev/null); do
    git -C "$d" rev-parse --show-toplevel 2>/dev/null
  done | sort -u | while IFS= read -r top; do
    { git -C "$top" diff --name-only HEAD 2>/dev/null; git -C "$top" ls-files --others --exclude-standard 2>/dev/null; } \
      | while IFS= read -r f; do [ -f "$top/$f" ] && printf '%s\n' "$top/$f"; done
  done
}

scannable () {  # text files people write; lockfiles, build output and dependencies are skipped
  case "$1" in
    *node_modules/*|*/dist/*|*/build/*|*/bin/*|*/obj/*|*/coverage/*|*.min.js|*.map|*.lock|*-lock.json|*.lockb) return 1 ;;
    *.png|*.jpg|*.jpeg|*.gif|*.webp|*.ico|*.pdf|*.zip|*.gz|*.woff|*.woff2|*.ttf|*.dll|*.exe|*.db|*.db-*) return 1 ;;
  esac
  [ -f "$1" ] && grep -Iq . "$1" 2>/dev/null
}

scan () {  # scan <file>
  local rule flags pattern hit line match
  while IFS='|' read -r rule flags pattern; do
    # shellcheck disable=SC2086
    grep -nEo $flags -- "$pattern" "$1" 2>/dev/null | head -n 5 | while IFS= read -r hit; do
      line="${hit%%:*}"; match="${hit#*:}"
      # Never echo a whole secret back into a transcript: keep the first 6 and the last 2 characters.
      [ "${#match}" -gt 12 ] && match="${match:0:6}…${match: -2}"
      printf '%s:%s: %s: %s\n' "$1" "$line" "$rule" "$match"
    done
  done <<< "$RULES"
}

if [ $# -gt 0 ]; then FILES="$(printf '%s\n' "$@")"; else FILES="$(changed_files)"; fi
OUT="$(while IFS= read -r file; do
  [ -n "$file" ] && scannable "$file" && scan "$file"
done <<< "$FILES" | sort -u)"
[ -n "$OUT" ] || { echo "secret-scan: nothing found"; exit 0; }
printf '%s\n' "$OUT"
exit 1
