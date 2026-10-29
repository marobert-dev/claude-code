#!/usr/bin/env bash
# Deterministic role guard for the pipeline agents, wired in their frontmatter hooks; no LLM involved.
#   PreToolUse (Edit|Write|NotebookEdit):   bash .claude/hooks/role-guard.sh <agent-name>
#     Blocks a file change outside the agent's role (exit 2: Claude Code cancels the call and feeds the reason back to
#     the agent): reviewers only add, update or remove their own single-line marker comments, analyst only TODO:
#     comments outside the story file and the contract, every other agent only its own paths, and no agent edits
#     .claude/ or a file outside the workspace.
#     Protected settings, which decide what the gate checks (so `"test": "exit 0"` or an ignore pattern would pass it):
#     the "scripts" and "jest" key of package.json, jest / vitest / playwright / eslint configs, tsconfig*.json (but
#     compilerOptions.paths and baseUrl), vite.config.* (but its "server" option, once it sets a vitest "test" option).
#     No agent changes them; an edit that undoes an earlier change is fine, and so are dependency edits and the rest of a
#     package.json. A new config in a package whose package.json is already committed is blocked too; in a package being
#     scaffolded it is fine.
#   Stop / SubagentStop:
#     bash .claude/hooks/role-guard.sh stop-plan            analyst: the plan it wrote has the fixed layout (pm-state.sh plan-check)
#     bash .claude/hooks/role-guard.sh stop-tests <agent>   the test files this agent changed gained no constant assertion,
#                                                           .only, or skip without an OBSOLETE-TEST: marker (story-validator:
#                                                           no fixed sleep either)
#     A Stop check blocks the same agent at most ROLE_GUARD_MAX_BLOCKS times (default 2), then lets it finish.
#   Called by the gate and pm-state.sh (no hook JSON; CLAUDE_PROJECT_DIR is the workspace):
#     bash .claude/hooks/role-guard.sh protected-diff       exit 2 and a report when a protected setting differs from the
#                                                           version the run started from, whatever tool changed it (Bash
#                                                           included). That version is the committed one (HEAD), or a copy
#                                                           kept in .pipeline/protected-baseline/ by protected-snapshot.
#     bash .claude/hooks/role-guard.sh protected-snapshot   copies the protected files already modified now, so a run is only
#                                                           held to its own changes; prints one PROTECTED line per file.
# Reads the hook JSON on stdin and needs jq or node to parse it; without either, or on input it cannot parse, it lets
# the call through: the prompts stay the first line of defence and this is the backstop. An agent that rewrites the hook
# scripts themselves with Bash is out of any in-workspace check's reach.

set -u
HOOKS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="${TMPDIR:-/tmp}/wta-role-guard"
mkdir -p "$STATE" 2>/dev/null || exit 0
W="$(mktemp -d "$STATE/in.XXXXXX" 2>/dev/null)" || exit 0
trap 'rm -rf "$W"' EXIT

MODE="${1:-}"; ROLE="${2:-}"
case "$MODE" in
  stop-plan)  ROLE="analyst" ;;
  stop-tests) ;;
  protected-diff|protected-snapshot) ROLE="gate" ;;
  '')         exit 0 ;;
  *)          ROLE="$MODE"; MODE="pre" ;;
esac

case "$MODE" in protected-*) INPUT="" ;; *) INPUT="$(cat 2>/dev/null || true)" ;; esac
FIELDS="tool_name tool_input.file_path tool_input.notebook_path tool_input.old_string tool_input.new_string tool_input.content tool_input.replace_all agent_id agent_type session_id cwd"

parse_input () {  # writes each field's raw text to $W/<last path segment>
  local f names i=0 val
  if command -v jq >/dev/null 2>&1; then
    # One jq call: the fields, NUL-separated, so multi-line strings survive intact.
    read -r -a names <<< "$FIELDS"
    printf '%s' "$INPUT" | jq -e . >/dev/null 2>&1 || return 1
    while IFS= read -r -d '' val; do
      printf '%s' "$val" > "$W/${names[i]##*.}"; i=$((i + 1))
    done < <(printf '%s' "$INPUT" | jq -j "[$(printf '.%s,' $FIELDS | sed 's/,$//')]
      | map(if . == null then \"\" elif type == \"string\" then . else tojson end) | map(. + \"\\u0000\") | add")
  elif command -v node >/dev/null 2>&1; then
    # shellcheck disable=SC2086
    printf '%s' "$INPUT" | GUARD_DIR="$W" node -e '
      const fs = require("fs"); let d = "";
      process.stdin.on("data", c => d += c).on("end", () => {
        let j; try { j = JSON.parse(d); } catch (e) { process.exit(1); }
        for (const p of process.argv.slice(1)) {
          const v = p.split(".").reduce((o, k) => (o == null ? o : o[k]), j);
          fs.writeFileSync(process.env.GUARD_DIR + "/" + p.split(".").pop(), v == null ? "" : (typeof v === "string" ? v : JSON.stringify(v)));
        }
      });' $FIELDS || return 1
  else
    return 1
  fi
}
field () { cat "$W/$1" 2>/dev/null; }

WIN=""; case "$(uname -s 2>/dev/null)" in MINGW*|MSYS*|CYGWIN*) WIN=1 ;; esac
norm () {  # forward slashes, no trailing slash; on Windows the c:/ form (MSYS mounts such as /tmp resolved), lower-case drive
  local p="${1//\\//}"
  if [ -n "$WIN" ]; then
    if command -v cygpath >/dev/null 2>&1; then p="$(cygpath -m -- "$p" 2>/dev/null || printf '%s' "$p")"
    else case "$p" in /[a-zA-Z]/*|/[a-zA-Z]) p="${p:1:1}:${p:2}" ;; esac; fi
    case "$p" in [A-Za-z]:*) p="$(printf '%s' "${p:0:1}" | tr 'A-Z' 'a-z')${p:1}" ;; esac
  fi
  printf '%s' "${p%/}"
}
lower () { if [ -n "$WIN" ]; then printf '%s' "$1" | tr 'A-Z' 'a-z'; else printf '%s' "$1"; fi; }

canon () {  # canon <absolute path>: "." and ".." segments resolved; fails when ".." climbs above the top
  local p="$1" lead="" seg parts out=()
  case "$p" in [a-z]:/*) lead="${p:0:2}"; p="${p:2}" ;; esac
  IFS=/ read -r -a parts <<< "$p"
  for seg in "${parts[@]}"; do
    case "$seg" in
      ''|.) ;;
      ..) [ "${#out[@]}" -gt 0 ] || return 1; out=("${out[@]:0:${#out[@]}-1}") ;;
      *) out+=("$seg") ;;
    esac
  done
  local IFS=/
  printf '%s/%s' "$lead" "${out[*]}"
}

physical () {  # physical <canonical path>: symlinks of its deepest existing directory resolved, the rest kept
  local p="$1" rest=""
  while [ -n "$p" ] && [ ! -d "$p" ]; do rest="/${p##*/}$rest"; p="${p%/*}"; done
  [ -n "$p" ] || { printf '%s' "$1"; return; }
  printf '%s%s' "$(norm "$(cd "$p" 2>/dev/null && pwd -P)")" "$rest"
}

block () { printf 'role-guard (%s): %s\n' "$ROLE" "$*" >&2; exit 2; }

# The hooks of the session agent (claude --agent product-manager) also fire for its subagents' tool calls, with the
# subagent's agent_type. A call that belongs to another agent is left to that agent's own guard.
not_mine () { local t; t="$(field agent_type)"; [ -n "$t" ] && [ "$t" != "$ROLE" ]; }

agent_key () { local id; id="$(field agent_id)"; [ -n "$id" ] || id="$(field session_id)"; printf '%s' "${id//[^A-Za-z0-9_-]/_}"; }

# Stop checks block the same agent only so often: after that it may finish and the next stage judges its work.
under_block_limit () {  # under_block_limit <check-name>
  local key; key="$(agent_key)"; [ -n "$key" ] || return 0
  COUNT_FILE="$STATE/$key.$1.count"
  [ "$(cat "$COUNT_FILE" 2>/dev/null || echo 0)" -lt "${ROLE_GUARD_MAX_BLOCKS:-2}" ]
}
stop_block () {  # stop_block <message...>: count the block, then exit 2
  [ -n "${COUNT_FILE:-}" ] && echo $(( $(cat "$COUNT_FILE" 2>/dev/null || echo 0) + 1 )) > "$COUNT_FILE"
  block "$@"
}

# --- comment-only edits ------------------------------------------------------------------------------------------
# Drops, on every line holding MARKER:, the comment that carries it: a block comment closed on the same line
# (/* */, <!-- -->, {/* */}, @* *@) is cut out and the rest of the line kept, any other comment runs to the end of the
# line. Then trailing blanks and blank lines go. Texts that normalize to the same lines differ only by MARKER: comments.
strip_marker_comments () {  # strip_marker_comments <MARKER> <file>
  awk -v m="$1:" '
    function lastpos(s, t,    p, q) { p = 0; while ((q = index(substr(s, p + 1), t)) > 0) p += q; return p }
    {
      line = $0; sub(/\r$/, "", line)
      i = index(line, m)
      if (i > 0) {
        pre = substr(line, 1, i - 1)
        if (pre ~ /^[ \t]*\*[ \t]*$/) line = ""          # " * REVIEW: ..." inside a block comment
        else {
          cut = 0; op = ""; jsx = 0
          n = split("// /* <!-- # -- @*", ops, " ")
          for (k = 1; k <= n; k++) { p = lastpos(pre, ops[k]); if (p > cut) { cut = p; op = ops[k] } }
          if (op == "--" && cut > 2 && substr(line, cut - 2, 2) == "<!") { cut -= 2; op = "<!--" }
          if (op == "/*" && cut > 1 && substr(line, cut - 1, 1) == "{") { cut -= 1; jsx = 1 }
          if (cut > 0) {
            head = substr(line, 1, cut - 1); tail = ""
            closer = (op == "/*") ? "*/" : (op == "<!--") ? "-->" : (op == "@*") ? "*@" : ""
            if (closer != "" && (j = index(substr(line, i), closer)) > 0) {
              tail = substr(line, i + j - 1 + length(closer))
              if (jsx) sub(/^[ \t]*}/, "", tail)
              if (head == "" || head ~ /[ \t]$/) sub(/^[ \t]+/, "", tail)
            }
            line = head tail
          }
        }
      }
      sub(/[ \t]+$/, "", line)
      if (line != "") print line
    }' "$2"
}

comments_only () {  # comments_only <MARKER>: the change may only add, update or remove MARKER: comments
  local marker="$1" tool; tool="$(field tool_name)"
  local hint="Your edits may only add, update or remove single-line \`$marker:\` comments; never change code, data or whitespace. A file with no comment syntax (JSON, such as locale files) gets no comment: put it where the code uses that file."
  case "$tool" in
    Edit)
      strip_marker_comments "$marker" "$W/old_string" > "$W/a"
      strip_marker_comments "$marker" "$W/new_string" > "$W/b" ;;
    Write)
      [ -f "$ABS" ] || block "you never create files. $hint"
      strip_marker_comments "$marker" "$ABS" > "$W/a"
      strip_marker_comments "$marker" "$W/content" > "$W/b" ;;
    *) block "you never edit notebooks or other files with $tool. $hint" ;;
  esac
  cmp -s "$W/a" "$W/b" || block "this change touches more than \`$marker:\` comments in $REL. $hint"
}

in_paths () { local p; for p in "$@"; do case "$REL" in $p) return 0 ;; esac; done; return 1; }
# e2e suites live in tests/e2e/ at the workspace root, or inside one repository of a multi-repo workspace
in_e2e () { in_paths 'tests/e2e/*' '*/tests/e2e/*' 'e2e/*' '*/e2e/*'; }

is_test_file () {  # unit or e2e test file or test setup file, by folder or file-name convention
  printf '%s' "$1" | grep -Eiq '(^|/)(tests?|__tests__|specs?|e2e)/|\.(test|spec)\.[cm]?[jt]sx?$|tests?\.cs$|(^|/)[^/]*\.tests?/|(^|/)(jest|vitest)\.setup\.[^/]*$|(^|/)setup-?tests?\.[^/]*$'
}

remember_touched () {  # the test check at Stop looks only at files this agent changed (only these roles run it)
  case "$ROLE" in dev-frontend|dev-backend|dev-integrator|unit-tester|story-validator) ;; *) return 0 ;; esac
  local key; key="$(agent_key)"
  [ -n "$key" ] && printf '%s\n' "$REL" >> "$STATE/$key.touched"
}

# --- protected settings: what the gate and the test runners read --------------------------------------------------
# An agent must not make the gate pass by changing what it checks: the package.json scripts and jest key, the test
# runner configs, the lint and type-check configs. Edit and Write are judged before they land (pre_tool); a change
# made any other way (Bash) is found afterwards by `protected-diff`, which the gate runs, against the version the run
# started from: the committed one, or a copy taken by `protected-snapshot` of a file that was already modified then.

protection_kind () {  # protection_kind <path>: package | tsconfig | vite | strict, or nothing for any other file
  case "$(printf '%s' "${1##*/}" | tr 'A-Z' 'a-z')" in
    package.json)                  echo package ;;
    tsconfig.json|tsconfig.*.json) echo tsconfig ;;
    vite.config.*)                 echo vite ;;
    jest.config.*|vitest.config.*|vitest.workspace.*|playwright.config.*|eslint.config.*|.eslintrc|.eslintrc.*|.eslintignore)
                                   echo strict ;;
  esac
}
protected_part () {  # protected_part <kind>: what may not change in a file of that kind
  case "$1" in
    package)  echo '"scripts" and the "jest" key' ;;
    tsconfig) echo 'everything but compilerOptions.paths and baseUrl' ;;
    vite)     echo 'everything but the "server" option' ;;
    *)        echo 'the whole file' ;;
  esac
}

plain_text () {  # plain_text <file>: without the BOM and the carriage returns, so a CRLF file still matches an edit
  LC_ALL=C sed $'1s/^\xEF\xBB\xBF//' "$1" | tr -d '\r'
}

# Comments and white space dropped, strings kept. With $1 the first option of that name ("server: {...}") is cut out; with
# $2 nothing is printed unless the code sets a "test" option (vitest's).
squash_code () {  # squash_code [dropped option] [1 = only when a test option is set]; reads stdin
  awk -v drop="${1:-}" -v needtest="${2:-}" '
    BEGIN { RS = "\001"; sq = "\047"; dq = "\042" }
    function ident(ch) { return ch ~ /[A-Za-z0-9_$.]/ }
    function quote(ch) { return ch == dq || ch == sq }
    function drop_option(t, key,    base, k, pos, before, e, start, depth, q, c, j) {
      base = 0
      while ((k = index(substr(t, base + 1), key)) > 0) {
        pos = base + k; base = pos
        before = (pos > 1) ? substr(t, pos - 1, 1) : ""
        if (before != "" && ident(before)) continue
        e = pos + length(key)
        if (quote(before) && quote(substr(t, e, 1))) e++
        if (substr(t, e, 2) != ":{") continue
        start = quote(before) ? pos - 1 : pos
        depth = 0; q = ""
        for (j = e + 1; j <= length(t); j++) {
          c = substr(t, j, 1)
          if (q != "") { if (c == "\\") j++; else if (c == q) q = ""; continue }
          if (c == dq || c == sq || c == "`") { q = c; continue }
          if (c == "{") depth++
          else if (c == "}" && --depth == 0) break
        }
        if (substr(t, j + 1, 1) == ",") j++
        return substr(t, 1, start - 1) substr(t, j + 1)
      }
      return t
    }
    {
      s = $0; n = length(s); out = ""; q = ""
      for (i = 1; i <= n; i++) {
        c = substr(s, i, 1); d = substr(s, i + 1, 1)
        if (q != "") { out = out c; if (c == "\\") { i++; out = out substr(s, i, 1) } else if (c == q) q = ""; continue }
        if (c == dq || c == sq || c == "`") { q = c; out = out c; continue }
        if (c == "/" && d == "/") { while (i <= n && substr(s, i, 1) != "\n") i++; continue }
        if (c == "/" && d == "*") { j = index(substr(s, i + 2), "*/"); i = (j ? i + j + 2 : n); continue }
        if (c !~ /[ \t\r\n]/) out = out c
      }
      if (needtest != "" && !match(out, "(^|[^A-Za-z0-9_$.])[" sq dq "]?test[" sq dq "]?:")) exit
      if (drop != "") out = drop_option(out, drop)
      print out
    }'
}

json_state () {  # json_state package|tsconfig: stdin JSON reduced to the settings the gate depends on, keys sorted; fails when it is not JSON
  if command -v jq >/dev/null 2>&1; then
    case "$1" in
      package) jq -S -c '{scripts: (.scripts // {}), jest: .jest}' 2>/dev/null ;;
      *)       jq -S -c 'del(.compilerOptions.paths, .compilerOptions.baseUrl)' 2>/dev/null ;;
    esac
  else
    node -e 'const sorted = v => Array.isArray(v) ? v.map(sorted) : v && typeof v === "object"
        ? Object.fromEntries(Object.keys(v).sort().map(k => [k, sorted(v[k])])) : v;
      let d = ""; process.stdin.on("data", c => d += c).on("end", () => {
        try {
          const j = JSON.parse(d); let o = j;
          if (process.argv[1] === "package") o = { scripts: j.scripts || {}, jest: j.jest === undefined ? null : j.jest };
          else if (j.compilerOptions && typeof j.compilerOptions === "object") { delete j.compilerOptions.paths; delete j.compilerOptions.baseUrl; }
          console.log(JSON.stringify(sorted(o)));
        } catch (e) { process.exit(1); }
      });' "$1" 2>/dev/null
  fi
}

protected_state () {  # protected_state <kind> <file>: canonical text of the part of <file> that must not change; fails when it cannot be read
  case "$1" in
    package)  plain_text "$2" | json_state package ;;
    tsconfig) plain_text "$2" | squash_code | sed 's/,\([]}]\)/\1/g' | json_state tsconfig ;;   # JSONC: no comments, no trailing commas
    vite)     plain_text "$2" | squash_code server 1 ;;
    *)        plain_text "$2" ;;
  esac
}

abs_key () { lower "$(physical "$(canon "$(norm "$1")")")" | cksum | cut -d' ' -f1; }

baseline_file () {  # baseline_file <abs path> <out file>: the file as the run started from it; fails when it did not exist then
  local abs="$1" key
  key="$(abs_key "$abs")"
  [ -e "$BASELINE_DIR/$key.deleted" ] && return 1
  if [ -f "$BASELINE_DIR/$key" ]; then cp "$BASELINE_DIR/$key" "$2"; return; fi
  git -C "$(dirname "$abs")" show "HEAD:./${abs##*/}" > "$2" 2>/dev/null
}

package_established () {  # package_established <abs path>: the nearest package.json above it is already committed (a new package is still being scaffolded)
  local dir prefix
  dir="$(dirname "$1")"
  while [ ! -d "$dir" ] && [ "$dir" != "$(dirname "$dir")" ]; do dir="$(dirname "$dir")"; done
  git -C "$dir" rev-parse --verify -q HEAD >/dev/null 2>&1 || return 1
  prefix="$(git -C "$dir" rev-parse --show-prefix 2>/dev/null)" || return 1
  while :; do
    if [ -f "$dir/package.json" ]; then git -C "$dir" cat-file -e "HEAD:${prefix}package.json" 2>/dev/null; return; fi
    [ -n "$prefix" ] || return 1
    prefix="${prefix%/}"; prefix="${prefix%"${prefix##*/}"}"
    dir="$(dirname "$dir")"
  done
}

after_edit () {  # after_edit <out file>: the existing $ABS as this Edit or Write would leave it; fails for any other tool
  shopt -u patsub_replacement 2>/dev/null
  local text old new
  case "$(field tool_name)" in
    Edit)
      text="$(plain_text "$ABS")"; old="$(plain_text "$W/old_string")"; new="$(plain_text "$W/new_string")"
      if [ "$(field replace_all)" = true ]; then text="${text//"$old"/"$new"}"; else text="${text/"$old"/"$new"}"; fi
      printf '%s\n' "$text" > "$1" ;;
    Write) plain_text "$W/content" > "$1" ;;
    *) return 1 ;;
  esac
}

protected_edit_check () {  # judge an Edit or Write on a protected file before it lands
  local kind before after
  kind="$(protection_kind "$REL")"; [ -n "$kind" ] || return 0
  if [ ! -f "$ABS" ]; then   # a new file: a new package.json, or config of a package still being scaffolded, is fine
    [ "$kind" = package ] || ! package_established "$ABS" \
      || block "$REL would be new $kind config in a package that is already committed, and config decides which checks and tests the gate runs; no agent adds it. Report the setting a story needs in your reply instead."
    return 0
  fi
  plain_text "$ABS" > "$W/cfg.before"
  before="$(protected_state "$kind" "$W/cfg.before")" || return 0   # already unreadable: nothing to compare with
  after_edit "$W/cfg.after" || return 0
  after="$(protected_state "$kind" "$W/cfg.after")" \
    || block "this change would leave $REL invalid JSON; make each edit keep it valid."
  [ "$after" = "$before" ] && return 0
  # Undoing an earlier change (back to the version the run started from) is always fine.
  if baseline_file "$ABS" "$W/cfg.base" && [ "$after" = "$(protected_state "$kind" "$W/cfg.base")" ]; then return 0; fi
  block "$REL: $(protected_part "$kind") may not change; it decides which checks and tests the gate runs. The rest of the file is fine to edit. Report the script or setting a story needs in your reply instead."
}

# --- protected settings: changes made any other way -----------------------------------------------------------------
repo_tops () {  # the git repositories the gate covers: the workspace root and its folders
  local d
  for d in . $(find . -mindepth 1 -maxdepth 1 -type d ! -name '.*' ! -name node_modules ! -name docs -printf '%f ' 2>/dev/null); do
    git -C "$d" rev-parse --show-toplevel 2>/dev/null
  done | sort -u
}

protected_candidates () {  # protected_candidates <repo top>: protected files that differ from HEAD (modified, deleted or new)
  { git -C "$1" diff HEAD --name-only 2>/dev/null; git -C "$1" ls-files --others --exclude-standard 2>/dev/null; } | sort -u \
    | while IFS= read -r p; do
        case "$p" in node_modules/*|*/node_modules/*) continue ;; esac
        [ -n "$(protection_kind "$p")" ] && printf '%s\n' "$p"
      done
}

violation_of () {  # violation_of <abs path> <name to show>: how the file differs from where the run started, or nothing
  local abs="$1" shown="$2" kind state_base state_now
  kind="$(protection_kind "$abs")"
  if baseline_file "$abs" "$W/cfg.base"; then
    [ -f "$abs" ] || { echo "$shown: deleted"; return; }
    state_base="$(protected_state "$kind" "$W/cfg.base")" || return 0
    state_now="$(protected_state "$kind" "$abs")" || { echo "$shown: no longer valid JSON"; return; }
    [ "$state_now" = "$state_base" ] || echo "$shown: changed ($(protected_part "$kind"))"
  elif [ -f "$abs" ] && [ "$kind" != package ] && package_established "$abs"; then
    echo "$shown: new config in a package that is already committed"
  fi
}

for_each_candidate () {  # for_each_candidate <function>: calls it with <abs path> <path shown> for every protected file that differs from HEAD
  local top p
  while IFS= read -r top; do
    git -C "$top" rev-parse --verify -q HEAD >/dev/null 2>&1 || continue
    while IFS= read -r p; do "$1" "$top/$p" "$p"; done < <(protected_candidates "$top")
  done < <(repo_tops)
}

enter_workspace () {  # the workspace root is where .pipeline/ lives
  local root; root="$(norm "${CLAUDE_PROJECT_DIR:-$(pwd)}")"
  cd "$root" 2>/dev/null || exit 0
  BASELINE_DIR="$(physical "$(canon "$root")")/.pipeline/protected-baseline"
}

protected_diff () {  # exit 2 with a report when a protected file changed since the run started
  local report=""
  enter_workspace
  collect_violation () { report="$report$(violation_of "$1" "$2" | sed 's/^/  /')"$'\n'; }
  for_each_candidate collect_violation
  report="$(printf '%s' "$report" | grep .)" || exit 0
  printf 'protected settings changed since the run started; they decide which checks and tests the gate runs, so no agent changes them to make it pass:\n%s\nUndo these changes (only the protected part; keep other work) and report the script or setting a story needs in your reply instead.\n' "$report" >&2
  exit 2
}

protected_snapshot () {  # take the protected files that are already modified as the baseline, so the run is only held to its own changes
  enter_workspace
  rm -rf "$BASELINE_DIR"
  keep_dirty () {
    [ -n "$(violation_of "$1" "$2")" ] || return 0
    mkdir -p "$BASELINE_DIR"
    if [ -f "$1" ]; then cp "$1" "$BASELINE_DIR/$(abs_key "$1")"; else : > "$BASELINE_DIR/$(abs_key "$1").deleted"; fi
    echo "PROTECTED already modified: $2 (taken as the baseline for this run)"
  }
  for_each_candidate keep_dirty
}

pre_tool () {
  parse_input || exit 0
  not_mine && exit 0
  local raw root target
  raw="$(field file_path)"; [ -n "$raw" ] || raw="$(field notebook_path)"
  [ -n "$raw" ] || exit 0
  root="$(norm "${CLAUDE_PROJECT_DIR:-$(field cwd)}")"; [ -n "$root" ] || root="$(norm "$(pwd)")"
  target="$(norm "$raw")"
  case "$target" in /*|[a-z]:/*) ;; *) target="$root/$target" ;; esac
  # Compare real locations: "tests/e2e/../../src/x.ts" is src/x.ts, and a symlinked folder is where it points.
  root="$(physical "$(canon "$root")")"
  BASELINE_DIR="$root/.pipeline/protected-baseline"
  target="$(canon "$target")" || block "$raw climbs above the file system root."
  target="$(physical "$target")"
  ABS="$target"
  if [ "$(lower "$target")" = "$(lower "$root")" ] || [ "${#target}" -le "${#root}" ] \
     || [ "$(lower "${target:0:${#root}+1}")" != "$(lower "$root")/" ]; then
    block "$raw is outside the workspace ($root); agents only change files inside it."
  fi
  REL="${target:${#root}+1}"
  in_paths '.claude/*' && block ".claude/ holds the pipeline's own agents, hooks and settings; no agent edits it."
  protected_edit_check

  case "$ROLE" in
    # .decisions/ is where every agent logs its judgment calls when team memory is off.
    code-reviewer)     in_paths '.decisions/*' || comments_only REVIEW ;;
    security-reviewer) in_paths '.decisions/*' || comments_only SECURITY ;;
    ui-reviewer)       in_paths '.decisions/*' || comments_only UX ;;
    analyst)
      in_paths '.user-stories/*' 'contracts/*' '.decisions/*' || comments_only TODO ;;
    dev-frontend|dev-backend|dev-integrator)
      in_paths 'contracts/openapi.yaml' 'contracts/openapi.yml' && block "analyst owns the API contract; report a contract defect instead."
      in_e2e && block "story-validator owns the e2e suite; fix the application code, never the acceptance tests."
      in_paths '.user-stories/*' '.stories-reviewed/*' '.validated-stories/*' '.completed/*' '.pipeline/*' \
        && block "$REL is pipeline state; report to product-manager instead of editing it."
      in_paths 'docs/*' && block "doc-writer owns docs/; mention what changed in your report instead." ;;
    unit-tester)
      in_paths '.decisions/*' || { is_test_file "$REL" && ! in_e2e; } \
        || block "you only write unit test files ($REL is not one; the e2e suite belongs to story-validator). Report what the code under test needs instead." ;;
    story-validator)
      in_e2e || in_paths '.user-stories/*' '.validated-stories/*' '.decisions/*' \
        || block "you only write e2e tests in the e2e folder, check boxes and notes in story files, and archives in .validated-stories/; never configs or application code ($REL). Report what needs fixing instead." ;;
    doc-writer)
      in_paths 'docs/*' || block "you only write under docs/ ($REL is outside it); report anything else instead." ;;
    conventions-scout)
      in_paths '.pipeline/conventions.md' || block "you only write .pipeline/conventions.md." ;;
    product-owner)
      in_paths '.user-stories/*' '.decisions/*' || block "you only write story files in .user-stories/." ;;
    product-manager)
      in_paths '.user-stories/*' '.pipeline/*' '.decisions/*' '.stories-reviewed/*' '.validated-stories/*' '.completed/*' \
        || block "product-manager orchestrates; $REL is changed by the agent that owns it."
      [ "$(field tool_name)" = "Write" ] && in_paths '.user-stories/*' && [ ! -f "$ABS" ] \
        && block "product-manager never creates stories; product-owner does." ;;
    *) exit 0 ;;
  esac
  remember_touched
  exit 0
}

# --- Stop: the analyst's plan ------------------------------------------------------------------------------------
stop_plan () {
  parse_input || exit 0
  not_mine && exit 0
  under_block_limit plan || exit 0
  cd "$(norm "${CLAUDE_PROJECT_DIR:-$(field cwd)}")" 2>/dev/null || exit 0
  [ -f "$HOOKS/pm-state.sh" ] || exit 0
  local out
  out="$(bash "$HOOKS/pm-state.sh" plan-check --latest 2>&1)" && exit 0
  stop_block "the Technical Plan does not follow the fixed layout yet. Fix it in the story file, then finish:
$out"
}

# --- Stop: test smells in the files this agent changed -----------------------------------------------------------
added_lines () {  # added_lines <abs path>: "<line>\t<text>" for lines added since HEAD (every line of an untracked file)
  local abs="$1" dir; dir="$(dirname "$abs")"
  if git -C "$dir" ls-files --error-unmatch -- "$abs" >/dev/null 2>&1; then
    git -C "$dir" diff -U0 HEAD -- "$abs" 2>/dev/null \
      | awk '/^@@/ { split($3, a, ","); n = substr(a[1], 2) + 0; next } /^\+\+\+/ { next } /^\+/ { print n "\t" substr($0, 2); n++ }'
  else
    awk '{ print NR "\t" $0 }' "$abs"
  fi
}

stop_tests () {
  parse_input || exit 0
  not_mine && exit 0
  under_block_limit "tests-$ROLE" || exit 0
  local key root list rel abs findings="" n=0
  key="$(agent_key)"; list="$STATE/$key.touched"
  [ -n "$key" ] && [ -f "$list" ] || exit 0
  root="$(norm "${CLAUDE_PROJECT_DIR:-$(field cwd)}")"
  # Patterns go to awk through the environment: awk -v would eat their backslashes.
  export GUARD_PLACEHOLDER='expect\([[:space:]]*(true|false|null|undefined|[0-9]+)[[:space:]]*\)\.(toBe|toEqual|toStrictEqual|toBeTruthy|toBeFalsy|toBeDefined)\(|Assert\.(True|False)\([[:space:]]*(true|false)[[:space:]]*\)|Assert\.Pass\(|(true|false)\.Should\(\)'
  export GUARD_FOCUSED='(^|[^.[:alnum:]_])((it|test|describe)\.only|fit|fdescribe)\('
  export GUARD_SKIPPED='(^|[^.[:alnum:]_])((it|test|describe)\.(skip|todo|fixme)|x(it|test|describe))\(|Skip[[:space:]]*=[[:space:]]*"|\[Ignore'
  export GUARD_SLEEP='waitForTimeout\('
  export GUARD_SETUP='process\.exit[[:space:]]*\(|(global(This)?|window)\.expect[[:space:]]*=[^=]'
  while IFS= read -r rel; do
    [ -n "$rel" ] && is_test_file "$rel" || continue
    abs="$root/$rel"; [ -f "$abs" ] || continue
    findings="$findings$(added_lines "$abs" | awk -F'\t' -v f="$rel" -v role="$ROLE" '
      { t = $2; kind = "" }
      t ~ ENVIRON["GUARD_PLACEHOLDER"] { kind = "constant assertion (asserts nothing about the code)" }
      t ~ ENVIRON["GUARD_FOCUSED"] { kind = "focused test (.only runs this test alone)" }
      t ~ ENVIRON["GUARD_SKIPPED"] && t !~ /OBSOLETE-TEST:/ && prev !~ /OBSOLETE-TEST:/ { kind = "skipped test without an OBSOLETE-TEST: marker" }
      t ~ ENVIRON["GUARD_SKIPPED"] && (role == "unit-tester" || role == "story-validator") { kind = "skipped test (yours must run)" }
      role == "story-validator" && t ~ ENVIRON["GUARD_SLEEP"] { kind = "fixed sleep (use web-first assertions)" }
      t ~ ENVIRON["GUARD_SETUP"] { kind = "ends the test process or replaces expect (a setup file runs before every test)" }
      kind != "" { gsub(/^[ \t]+/, "", t); printf "%s:%s: %s: %s\n", f, $1, kind, substr(t, 1, 100) }
      { prev = t }')"
  done < <(sort -u "$list")
  if [ -z "$findings" ]; then rm -f "$list"; exit 0; fi
  n="$(printf '%s' "$findings" | grep -c .)"
  stop_block "$n line(s) in the tests you changed would weaken the suite. Every test must assert real behavior of the code under test, run in the full suite, and stay enabled (only dev agents park a test, with an OBSOLETE-TEST: marker). Fix them, then finish:
$(printf '%s' "$findings" | head -n 12)"
}

case "$MODE" in
  pre)        pre_tool ;;
  stop-plan)  stop_plan ;;
  stop-tests) stop_tests ;;
  protected-diff)     protected_diff ;;
  protected-snapshot) protected_snapshot ;;
esac
exit 0
