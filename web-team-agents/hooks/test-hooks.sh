#!/usr/bin/env bash
# Tests for the deterministic hooks: role-guard.sh, pm-state.sh (plan-check, append, finish), secret-scan.sh, gate.sh
# (NOT CHECKED, scoped and full modes, loop guard, time limit, one gate at a time, colors).
# Usage (from the repo root): bash hooks/test-hooks.sh        Needs bash, git and jq; node too for the no-jq case.
set -u
HOOKS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v jq >/dev/null 2>&1 || { echo "jq is required to build the test inputs"; exit 1; }

WS="$(mktemp -d)"; export TMPDIR="$WS/.tmp"; mkdir -p "$TMPDIR"
trap 'rm -rf "$WS"' EXIT
cd "$WS" && git init -q && git config user.email t@t && git config user.name t
mkdir -p .claude/hooks src tests/e2e/01-x contracts .user-stories docs frontend/tests
cp "$HOOKS/role-guard.sh" "$HOOKS/pm-state.sh" .claude/hooks/
printf 'export const total = (a: number) => a;\n' > src/total.ts
printf '{\n  "nav": { "cart": "Cart" }\n}\n' > src/en.json
printf 'it("adds", () => {\n  expect(total(1)).toBe(1);\n});\n' > frontend/tests/total.test.ts
printf 'openapi: 3.1.0\n' > contracts/openapi.yaml
git add -A && git commit -qm base
export CLAUDE_PROJECT_DIR="$WS"

PASS=0; FAILED=0
check () {  # check <name> <expected exit> <actual exit>
  if [ "$2" = "$3" ]; then PASS=$((PASS + 1)); else FAILED=$((FAILED + 1)); echo "FAIL: $1 (expected exit $2, got $3)"; fi
}
# Values reach jq through the environment with MSYS_NO_PATHCONV: on Windows, MSYS rewrites arguments and environment
# values that look like paths (it turns "// REVIEW:" into "/ REVIEW:") before a native program such as jq sees them.
# Hooks themselves get their JSON on stdin, which MSYS leaves alone.
edit_json () {  # edit_json <rel path> <old> <new> [agent_id]
  MSYS_NO_PATHCONV=1 P="$WS/$1" O="$2" N="$3" A="${4:-agent-1}" jq -n \
    '{hook_event_name:"PreToolUse", tool_name:"Edit", agent_id:$ENV.A, session_id:"s1", cwd:"x",
      tool_input:{file_path:$ENV.P, old_string:$ENV.O, new_string:$ENV.N}}'
}
write_json () {  # write_json <path, relative or absolute> <content> [agent_id]
  local p="$1"; case "$p" in /*) ;; *) p="$WS/$p" ;; esac
  MSYS_NO_PATHCONV=1 P="$p" C="$2" A="${3:-agent-1}" jq -n \
    '{hook_event_name:"PreToolUse", tool_name:"Write", agent_id:$ENV.A, session_id:"s1", tool_input:{file_path:$ENV.P, content:$ENV.C}}'
}
guard () { bash .claude/hooks/role-guard.sh "$@" >/dev/null 2>&1; echo $?; }
stop_json () { jq -n --arg a "${1:-agent-1}" '{hook_event_name:"SubagentStop", agent_id:$a, session_id:"s1", stop_hook_active:false}'; }

# --- reviewers: marker comments only ----------------------------------------------------------------------------
code='export const total = (a: number) => a;'
check "reviewer adds a line comment"        0 "$(edit_json src/total.ts "$code" "// REVIEW: round to cents
$code" | guard code-reviewer)"
check "reviewer adds an inline comment"     0 "$(edit_json src/total.ts "$code" "$code // REVIEW: float money" | guard code-reviewer)"
check "reviewer removes a resolved comment" 0 "$(edit_json src/total.ts "// REVIEW: x
$code" "$code" | guard code-reviewer)"
check "reviewer adds a JSX comment"         0 "$(edit_json src/total.ts "  <a/>" "  {/* REVIEW: label */}
  <a/>" | guard code-reviewer)"
check "reviewer adds an HTML comment"       0 "$(edit_json src/total.ts "<a/>" "<!-- REVIEW: label --><a/>" | guard code-reviewer)"
check "reviewer changes code"               2 "$(edit_json src/total.ts "$code" "export const total = (a: number) => Math.round(a);" | guard code-reviewer)"
check "reviewer adds a JSON key"            2 "$(edit_json src/en.json '  "nav": { "cart": "Cart" }' '  "REVIEW": "missing key",
  "nav": { "cart": "Cart" }' | guard code-reviewer)"
check "reviewer uses another marker"        2 "$(edit_json src/total.ts "$code" "// SECURITY: x
$code" | guard code-reviewer)"
check "security-reviewer adds its marker"   0 "$(edit_json src/total.ts "$code" "$code // SECURITY: high: x" | guard security-reviewer)"
check "ui-reviewer adds its marker"         0 "$(edit_json src/total.ts "$code" "/* UX: overflows at 360px */ $code" | guard ui-reviewer)"
check "reviewer creates a file"             2 "$(write_json src/new.ts "x" | guard code-reviewer)"
check "reviewer logs a decision to a file"  0 "$(write_json .decisions/security-reviewer.decisions.md "Agent: security-reviewer" | guard security-reviewer)"

# --- paths per role ---------------------------------------------------------------------------------------------
check "nobody edits .claude/"               2 "$(write_json .claude/hooks/role-guard.sh "exit 0" | guard dev-backend)"
check "nobody writes outside the workspace" 2 "$(write_json "$(dirname "$WS")/elsewhere.ts" "x" | guard dev-backend)"
check "dev edits application code"          0 "$(edit_json src/total.ts "$code" "export const total = (a: number) => a * 2;" | guard dev-frontend)"
check "dev edits the contract"              2 "$(edit_json contracts/openapi.yaml "openapi: 3.1.0" "openapi: 3.1.1" | guard dev-backend)"
check "dev edits an acceptance test"        2 "$(write_json tests/e2e/01-x/a.spec.ts "x" | guard dev-frontend)"
check "dev edits a story file"              2 "$(write_json .user-stories/01-x.md "x" | guard dev-integrator)"
check "analyst edits the story file"        0 "$(write_json .user-stories/01-x.md "# x" | guard analyst)"
check "analyst edits the contract"          0 "$(edit_json contracts/openapi.yaml "openapi: 3.1.0" "openapi: 3.1.0
info: {}" | guard analyst)"
check "analyst adds a TODO comment"         0 "$(edit_json src/total.ts "$code" "// TODO: round to cents
$code" | guard analyst)"
check "analyst implements code"             2 "$(edit_json src/total.ts "$code" "export const total = (a: number) => Math.round(a);" | guard analyst)"
check "validator writes an e2e test"        0 "$(write_json tests/e2e/01-x/a.spec.ts "x" | guard story-validator)"
check "validator writes a repo's e2e test"  0 "$(write_json server/tests/e2e/01-x/a.e2e.test.js "x" | guard story-validator)"
check "dev edits a repo's e2e test"         2 "$(write_json server/tests/e2e/01-x/a.e2e.test.js "x" | guard dev-backend)"
check "validator edits the e2e config"      2 "$(write_json playwright.config.ts "x" | guard story-validator)"
check "unit-tester writes a unit test"      0 "$(write_json frontend/tests/total.test.ts "x" | guard unit-tester)"
check "unit-tester writes a .NET test"      0 "$(write_json backend/tests/Api.Tests/CartTests.cs "x" | guard unit-tester)"
check "unit-tester edits application code"  2 "$(write_json src/total.ts "x" | guard unit-tester)"
check "unit-tester edits an e2e test"       2 "$(write_json tests/e2e/01-x/a.spec.ts "x" | guard unit-tester)"
check "doc-writer writes docs"              0 "$(write_json docs/dev/README.md "x" | guard doc-writer)"
check "doc-writer edits code"               2 "$(write_json src/total.ts "x" | guard doc-writer)"
check "scout writes conventions"            0 "$(write_json .pipeline/conventions.md "x" | guard conventions-scout)"
check "scout writes elsewhere"              2 "$(write_json .pipeline/other.md "x" | guard conventions-scout)"
check "product-manager appends to a story"  0 "$(edit_json .user-stories/01-x.md "# x" "# x
## Integration Notes" | guard product-manager)"
printf '# x\n' > .user-stories/01-x.md
check "product-manager creates a story"     2 "$(write_json .user-stories/02-new.md "# new" | guard product-manager)"
check "product-manager edits code"          2 "$(write_json src/total.ts "x" | guard product-manager)"
check "product-owner writes a story"        0 "$(write_json .user-stories/02-new.md "# new" | guard product-owner)"
check "unknown agent is not guarded"        0 "$(write_json src/total.ts "x" | guard some-other-agent)"
# The session agent's hook also fires for its subagents' calls; agent_type says whose call it is.
sub_write () { MSYS_NO_PATHCONV=1 P="$WS/$1" T="$2" jq -n \
  '{tool_name:"Write", agent_id:"sub-1", agent_type:$ENV.T, session_id:"s1", tool_input:{file_path:$ENV.P, content:"x"}}'; }
check "PM's hook lets a subagent's call pass" 0 "$(sub_write src/total.ts dev-frontend | guard product-manager)"
check "the subagent's own hook still guards"  2 "$(sub_write contracts/openapi.yaml dev-frontend | guard dev-frontend)"
check "PM's hook guards the PM's own calls"   2 "$(sub_write src/total.ts product-manager | guard product-manager)"
check "unparsable input lets the call pass" 0 "$(echo 'not json' | guard code-reviewer)"
check "'..' cannot reach .claude/"          2 "$(write_json "src/../.claude/hooks/gate.sh" "exit 0" | guard dev-backend)"
check "'..' cannot leave the e2e folder"    2 "$(write_json "tests/e2e/../../src/total.ts" "x" | guard story-validator)"
check "'..' cannot leave the workspace"     2 "$(write_json "src/../../outside.ts" "x" | guard dev-frontend)"
check "a harmless '..' is still allowed"    0 "$(write_json "tests/e2e/01-x/../01-x/a.spec.ts" "x" | guard story-validator)"
mkdir -p "$WS.outside" && ln -s "$WS.outside" linked 2>/dev/null
if [ -L linked ]; then   # real symlinks (Git Bash without winsymlinks copies instead; the check is skipped there)
  check "a symlinked folder is judged by its target" 2 "$(write_json linked/x.ts "x" | guard dev-frontend)"
fi
rm -rf linked "$WS.outside"
check "Windows-style path is understood"    2 "$(P="$(cygpath -w "$WS/contracts/openapi.yaml" 2>/dev/null || echo "$WS/contracts/openapi.yaml")" \
  jq -n '{tool_name:"Write", agent_id:"w", tool_input:{file_path:$ENV.P, content:"x"}}' | guard dev-backend)"

# --- Stop: test smells in the files the agent touched ------------------------------------------------------------
smell () {  # smell <agent> <agent_id> <test file content> [path]: the agent writes the test file, then stops
  local f="${4:-frontend/tests/smell.test.ts}"
  mkdir -p "$(dirname "$f")"; printf '%s\n' "$3" > "$f"
  write_json "$f" "$3" "$2" | bash .claude/hooks/role-guard.sh "$1" >/dev/null 2>&1
  stop_json "$2" | guard stop-tests "$1"
}
check "constant assertion blocks"           2 "$(smell unit-tester a1 'it("x", () => { expect(true).toBe(true); });')"
check "focused test blocks"                 2 "$(smell dev-frontend a2 'it.only("x", () => { expect(total(2)).toBe(2); });')"
check "unmarked skip blocks a dev agent"    2 "$(smell dev-backend a3 'it.skip("old total", () => {});')"
check "marked skip is fine for a dev agent" 0 "$(smell dev-backend a4 '// OBSOLETE-TEST: 01-x — total now rounds
it.skip("old total", () => {});')"
check "marked skip still blocks unit-tester" 2 "$(smell unit-tester a5 '// OBSOLETE-TEST: 01-x — x
it.skip("old total", () => {});')"
check "fixed sleep blocks story-validator"  2 "$(smell story-validator a6 'await page.waitForTimeout(500);' tests/e2e/01-x/smell.spec.ts)"
check "real assertions pass"                0 "$(smell unit-tester a7 'it("x", () => { expect(total(2)).toBe(2); });')"
smell unit-tester a8 'expect(1).toBe(1);' >/dev/null; smell unit-tester a8 'expect(1).toBe(1);' >/dev/null
check "a Stop check gives up after 2 blocks" 0 "$(stop_json a8 | guard stop-tests unit-tester)"
git checkout -q -- frontend/tests; rm -f frontend/tests/smell.test.ts tests/e2e/01-x/smell.spec.ts

# --- Stop: plan layout (analyst) and pm-state plan-check --------------------------------------------------------
story=.user-stories/03-cart-badge.md
printf '# Cart badge\n\n## Acceptance Criteria\n\n- [ ] Shows Cart (3)\n\n## Visual Definition\n\n- Appearance: x\n\n## Technical Plan\nScope: web, backend\n### Shared\n- reuse getCart\n### Web\n- header\n' > "$story"
check "valid plan passes plan-check"        0 "$(bash .claude/hooks/pm-state.sh plan-check "$story" >/dev/null 2>&1; echo $?)"
check "plan-check reports scope and visual" "PLAN ok scope=backend,web visual=yes" "$(bash .claude/hooks/pm-state.sh plan-check "$story")"
check "analyst may finish with a valid plan" 0 "$(stop_json p1 | guard stop-plan)"
printf '\n### Tests\n- add tests/e2e/cart-badge.spec.ts\n' >> "$story"
check "extra subsection and e2e file fail"  2 "$(bash .claude/hooks/pm-state.sh plan-check "$story" >/dev/null 2>&1; echo $?)"
check "analyst may not finish then"         2 "$(stop_json p2 | guard stop-plan)"
mkdir -p tests/e2e/01-older-story
printf '# x\n\n## Technical Plan\nScope: web\n### Existing code to change\n- tests/e2e/01-older-story/ asserts the old copy\n- tests/e2e/03-cart-badge/badge.spec.ts\n' > "$story"
check "existing e2e folders and the story's own may be named" 0 "$(bash .claude/hooks/pm-state.sh plan-check "$story" >/dev/null 2>&1; echo $?)"
printf '# x\n\n## Technical Plan\n### Scope\n- web\n' > "$story"
check "missing Scope: line fails"           2 "$(bash .claude/hooks/pm-state.sh plan-check "$story" >/dev/null 2>&1; echo $?)"
check "criteria prints only the criteria"   "- [ ] Shows Cart (3)" "$(printf '# a\n\n## Acceptance Criteria\n\n- [ ] Shows Cart (3)\n\n## Copy\nx\n' > "$story"; bash .claude/hooks/pm-state.sh criteria "$story" | grep .)"

# --- pm-state start: conventions state ---------------------------------------------------------------------------
mkdir -p .pipeline; printf '# Project conventions\n\n## Backend\nx\n' > .pipeline/conventions.md
check "conventions without Project rules are outdated" 1 "$(bash .claude/hooks/pm-state.sh start 2>/dev/null | grep -c '^CONVENTIONS outdated')"
printf '# Project conventions\n\n## Project rules\nnot present\n' > .pipeline/conventions.md
check "conventions with Project rules are present"     1 "$(bash .claude/hooks/pm-state.sh start 2>/dev/null | grep -c '^CONVENTIONS present')"

# --- pm-state append and finish schedule ------------------------------------------------------------------------
printf 'line one' > .user-stories/04-a.md
bash .claude/hooks/pm-state.sh append .user-stories/04-a.md "## Integration Notes" <<< "- wired" >/dev/null
check "append adds the section after a blank line" "line one||## Integration Notes||- wired" "$(paste -sd '|' .user-stories/04-a.md)"
rm -f .user-stories/*.md; mkdir -p .completed; touch .completed/01-a.md .completed/02-b.md .completed/03-c.md .completed/04-d.md .completed/05-e.md
printf '# f\n' > .user-stories/06-f.md; printf '# g\n' > .user-stories/07-g.md
out="$(bash .claude/hooks/pm-state.sh finish completed .user-stories/06-f.md)"
check "6th completed story: digest and refresh due" "DUE refresh" "$(printf '%s\n' "$out" | grep '^DUE refresh')"
check "6th completed story: digest due"            "DUE digest" "$(printf '%s\n' "$out" | grep '^DUE digest')"
out="$(bash .claude/hooks/pm-state.sh finish failed .user-stories/07-g.md)"
check "a failure makes the digest due"      "DUE digest" "$(printf '%s\n' "$out" | grep '^DUE')"

# --- secret-scan -------------------------------------------------------------------------------------------------
printf 'VITE_STRIPE_SECRET_KEY=sk_test_51HabcdefGHIJKLMNOP\n' > frontend/.env
printf 'const stripeKey = "sk_live_abcdefghijklmnop12";\n' > src/pay.ts
out="$(bash "$HOOKS/secret-scan.sh" frontend/.env src/pay.ts 2>&1)"; rc=$?
check "secret-scan exits 1 on findings"     1 "$rc"
check "secret-scan flags a client-exposed secret" 1 "$(printf '%s\n' "$out" | grep -c 'frontend/.env:1: client-exposed-secret')"
check "secret-scan masks the secret"        0 "$(printf '%s\n' "$out" | grep -c 'sk_live_abcdefghijklmnop12')"
check "secret-scan passes a clean file"     0 "$(bash "$HOOKS/secret-scan.sh" src/total.ts >/dev/null 2>&1; echo $?)"

# --- gate --------------------------------------------------------------------------------------------------------
check "gate ignores other agents' Stop"     0 "$(printf '{"agent_type":"code-reviewer","agent_id":"g1"}' | bash "$HOOKS/gate.sh" >/dev/null 2>&1; echo $?)"
mkdir -p "$WS/gate-ws/app" && printf '{"scripts":{"test":"exit 0"}}' > "$WS/gate-ws/app/package.json"
NO_NODE_PATH="$(printf '%s' "$PATH" | tr ':' '\n' | grep -v -i -e nodejs -e npm -e 'jq' | paste -sd ':' -)"
out="$(cd "$WS/gate-ws" && CLAUDE_PROJECT_DIR="$WS/gate-ws" PATH="$NO_NODE_PATH" GATE_NO_CACHE=1 bash "$HOOKS/gate.sh" < /dev/null 2>&1)"; rc=$?
check "gate fails NOT CHECKED without npm"  2 "$rc"
check "gate names what it could not check"  1 "$(printf '%s\n' "$out" | grep -c 'NOT CHECKED')"
if command -v node >/dev/null 2>&1; then
  NO_JQ_PATH="$(printf '%s' "$PATH" | tr ':' '\n' | grep -v -i 'jq' | paste -sd ':' -)"
  check "gate reads package.json with node when jq is missing" 0 \
    "$(cd "$WS/gate-ws" && CLAUDE_PROJECT_DIR="$WS/gate-ws" PATH="$NO_JQ_PATH" GATE_NO_CACHE=1 bash "$HOOKS/gate.sh" < /dev/null >/dev/null 2>&1; echo $?)"
  check "role-guard parses with node when jq is missing" 2 \
    "$(write_json contracts/openapi.yaml "x" | PATH="$NO_JQ_PATH" bash .claude/hooks/role-guard.sh dev-backend >/dev/null 2>&1; echo $?)"
fi

# --- gate: scoped and full modes, loop guard, time limit, one gate at a time, colors ---------------------------------
mkgw () {  # mkgw <dir> <package>...   a git workspace whose packages each hold a package.json and an a.js; the scripts follow
  local dir="$1"; shift
  mkdir -p "$dir/.pipeline"; printf '.pipeline/\n' > "$dir/.gitignore"
  for pkg in "$@"; do mkdir -p "$dir/$pkg"; echo x > "$dir/$pkg/a.js"; done
}
commit_gw () { ( cd "$1" && git init -q && git config user.email t@t && git config user.name t && git add -A && git commit -qm base ) >/dev/null 2>&1; }
gate_in () {  # gate_in <dir> [VAR=value ...] -- [gate.sh args]; prints the output, exit code in $?
  local dir="$1"; shift; local envs=()
  while [ "${1:-}" != "--" ]; do envs+=("$1"); shift; done; shift
  ( cd "$dir" && env CLAUDE_PROJECT_DIR="$dir" "${envs[@]}" bash "$HOOKS/gate.sh" "$@" ) < /dev/null 2>&1
}

GW="$WS/gate2"; mkgw "$GW" pkg-ok pkg-bad
printf '{"scripts":{"lint":"exit 0"}}' > "$GW/pkg-ok/package.json"
printf '{"scripts":{"lint":"exit 1"}}' > "$GW/pkg-bad/package.json"
commit_gw "$GW"
out="$(gate_in "$GW" GATE_NO_CACHE=1 --)"; rc=$?
check "scoped gate passes with nothing changed" 0 "$rc"
check "scoped gate says no package changed"     1 "$(printf '%s\n' "$out" | grep -c 'no changed package')"
echo y >> "$GW/pkg-ok/a.js"
gate_in "$GW" GATE_NO_CACHE=1 -- >/dev/null; check "scoped gate skips an untouched package that would fail" 0 "$?"
out="$(gate_in "$GW" GATE_NO_CACHE=1 -- --full)"; rc=$?
check "full gate checks every package"         2 "$rc"
check "full gate names the failing step"       1 "$(printf '%s\n' "$out" | grep -c 'npm lint (pkg-bad) FAILED')"
echo y >> "$GW/pkg-bad/a.js"
out="$(gate_in "$GW" GATE_NO_CACHE=1 --)"; rc=$?
check "scoped gate fails a changed package"    2 "$rc"
check "scoped gate names the failing step"     1 "$(printf '%s\n' "$out" | grep -c 'npm lint (pkg-bad) FAILED')"
check "gate output carries no color codes"     0 "$(printf '%s\n' "$out" | grep -c "$(printf '\033')")"
loop () { printf '{"agent_type":"dev-backend","agent_id":"loop-1"}' | ( cd "$GW" && CLAUDE_PROJECT_DIR="$GW" GATE_NO_CACHE=1 GATE_MAX_BLOCKS=1 bash "$HOOKS/gate.sh" ) >/dev/null 2>&1; echo $?; }
check "gate blocks a dev agent once"           2 "$(loop)"
check "gate then lets the loop guard release it" 0 "$(loop)"

NG="$(TMPDIR=/tmp mktemp -d)"; mkdir -p "$NG/pkg-bad"; printf '{"scripts":{"lint":"exit 1"}}' > "$NG/pkg-bad/package.json"
if ! git -C "$NG" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  gate_in "$NG" GATE_NO_CACHE=1 -- >/dev/null; check "scoped gate checks a package outside git whole" 2 "$?"
fi
rm -rf "$NG"

GW2="$WS/gate3"; mkgw "$GW2" pkg-slow pkg-env pkg-conc
cat > "$GW2/pkg-slow/package.json" <<'EOF'
{"scripts":{"lint":"node -e \"setInterval(() => {}, 1000)\""}}
EOF
cat > "$GW2/pkg-env/package.json" <<'EOF'
{"scripts":{"lint":"node -e \"require('fs').writeFileSync('../.pipeline/env.txt', process.env.NO_COLOR + process.env.FORCE_COLOR)\""}}
EOF
cat > "$GW2/pkg-conc/package.json" <<'EOF'
{"scripts":{"lint":"node -e \"require('fs').appendFileSync('../.pipeline/runs.txt', 'x'); setTimeout(() => {}, 4000)\""}}
EOF
commit_gw "$GW2"
echo y >> "$GW2/pkg-slow/a.js"; SECONDS=0
out="$(gate_in "$GW2" GATE_NO_CACHE=1 GATE_STEP_TIMEOUT=3 --)"; rc=$?
check "gate fails a step that outlasts its time limit" 2 "$rc"
check "gate reports the timed-out step"        1 "$(printf '%s\n' "$out" | grep -c 'TIMED OUT after 3s')"
check "gate returns soon after the time limit" 1 "$([ "$SECONDS" -lt 30 ] && echo 1 || echo 0)"
( cd "$GW2" && git checkout -q -- . )
echo y >> "$GW2/pkg-env/a.js"
gate_in "$GW2" GATE_NO_CACHE=1 FORCE_COLOR=1 -- >/dev/null
check "steps run with NO_COLOR=1 FORCE_COLOR=0 even if the caller forces colors" "10" "$(cat "$GW2/.pipeline/env.txt" 2>/dev/null)"
( cd "$GW2" && git checkout -q -- . )
echo y >> "$GW2/pkg-conc/a.js"; rm -f "$GW2/.pipeline/runs.txt" "$GW2/.pipeline/rc1"
( gate_in "$GW2" -- >/dev/null; echo $? > "$GW2/.pipeline/rc1" ) &
sleep 1
gate_in "$GW2" -- >/dev/null; rc2=$?
wait
check "two simultaneous gates both pass"       "00" "$(cat "$GW2/.pipeline/rc1")$rc2"
check "two simultaneous gates run the checks once" 1 "$(wc -c < "$GW2/.pipeline/runs.txt" | tr -d ' ')"

# --- pm-state start: is the dev agents' stop wired to the gate? --------------------------------------------------
WIRE="$WS/wire"; mkdir -p "$WIRE/.claude/hooks" "$WS/home/.claude/agents"
touch "$WIRE/.claude/hooks/gate.sh"
wire () {  # wire [VAR=value ...]   pm-state start in $WIRE with an empty home, so the real user settings and agents never count
  ( cd "$WIRE" && env HOME="$WS/home" CLAUDE_AGENTS_DIR="$WS/home/.claude/agents" "$@" bash "$HOOKS/pm-state.sh" start ) 2>/dev/null
}
GATE_HOOK='{"hooks":{"SubagentStop":[{"matcher":"dev-frontend|dev-backend|dev-integrator","hooks":[{"type":"command","command":"bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/gate.sh\""}]}]}}'
printf '{"permissions":{"allow":["Bash(bash .claude/hooks/gate.sh:*)"]}}' > "$WIRE/.claude/settings.json"
check "permissions naming gate.sh are not a hook"     1 "$(wire | grep -c '^GATE hook missing')"
printf '%s' "$GATE_HOOK" > "$WIRE/.claude/settings.json"
check "one SubagentStop gate hook is wired"           1 "$(wire | grep -c '^GATE hook wired')"
printf '%s' "$GATE_HOOK" > "$WIRE/.claude/settings.local.json"
check "the same hook in settings.local.json doubles it" 1 "$(wire | grep -c '^GATE hook duplicated')"
rm -f "$WIRE/.claude/settings.local.json"
printf -- '---\nname: dev-backend\nhooks:\n  Stop:\n    - hooks:\n        - type: command\n          command: role-guard.sh\n---\nDo not run `.claude/hooks/gate.sh` yourself.\n' > "$WS/home/.claude/agents/dev-backend.md"
check "gate.sh named in an agent's body is not a trigger" 1 "$(wire | grep -c '^GATE hook wired')"
printf -- '---\nname: dev-backend\nhooks:\n  Stop:\n    - hooks:\n        - type: command\n          command: bash "$CLAUDE_PROJECT_DIR/.claude/hooks/gate.sh"\n---\nbody\n' > "$WS/home/.claude/agents/dev-backend.md"
check "gate.sh in an agent's frontmatter doubles it"  1 "$(wire | grep -c '^GATE hook duplicated')"
rm -f "$WS/home/.claude/agents/dev-backend.md"
printf '{}' > "$WIRE/.claude/settings.json"
check "an agent with no gate trigger is reported"     1 "$(wire | grep -c '^GATE hook missing')"
printf '%s' "$GATE_HOOK" > "$WIRE/.claude/settings.json"
check "without jq and node the wiring is unknown"     1 "$(wire PATH="$NO_NODE_PATH" | grep -c '^GATE hook unknown')"
if command -v node >/dev/null 2>&1; then
  check "the wiring is read with node when jq is missing" 1 "$(wire PATH="$NO_JQ_PATH" | grep -c '^GATE hook wired')"
fi
rm -f "$WIRE/.claude/hooks/gate.sh"
check "no gate.sh: no hook line, only GATE missing"   "1 0" "$(wire | grep -c '^GATE missing') $(wire | grep -c '^GATE hook')"

echo "hooks tests: $PASS passed, $FAILED failed"
[ "$FAILED" -eq 0 ]
