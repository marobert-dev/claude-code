#!/usr/bin/env bash
# CS-01 — called by scripts/check-run.sh with RUN_DIR/EVAL_DIR/CHECKS_FILE exported.
# Section-by-section comparison with fixtures/conventions.golden.md (facts that must be found, not wording).
. "$KIT/scripts/lib/check-lib.sh"

FILE="$RUN_DIR/.pipeline/conventions.md"
conv () {  # conv <rule>
  "$PYTHON" - "$FILE" "$1" <<'PY'
import re, sys
from pathlib import Path
p = Path(sys.argv[1]); rule = sys.argv[2]
if not p.exists():
    print("missing .pipeline/conventions.md"); sys.exit(1)
text = p.read_text(encoding="utf-8")

def section(name):
    m = re.search(rf"^## {re.escape(name)}\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""

def row(step):
    m = re.search(rf"^\|\s*{re.escape(step)}\s*\|(.*)$", section("Commands"), re.M | re.I)
    return m.group(1) if m else ""

def need(cond, msg):
    if not cond:
        print(msg); sys.exit(1)

if rule == "sections":
    names = ["Repositories", "Backend", "Frontend (web)", "Mobile (React Native)", "i18n", "API contract", "Tests", "Commands", "Security tooling present", "Change log"]
    missing = [n for n in names if not re.search(rf"^## {re.escape(n)}\s*$", text, re.M)]
    need(not missing and text.startswith("# Project conventions"), f"missing sections: {missing}")
elif rule == "length":
    n = len(text.splitlines()); need(n <= 150, f"{n} lines (max ~150)")
elif rule == "mobile-not-present":
    s = section("Mobile (React Native)")
    need(len(re.findall(r"not present", s, re.I)) >= 3, f"mobile bullets must say 'not present': {s.strip()[:200]}")
elif rule == "repositories":
    s = section("Repositories"); need(re.search(r"backend", s, re.I) and re.search(r"frontend", s, re.I), "backend/ and frontend/ not both listed")
elif rule == "cmd-lint":
    r = row("lint"); need("npm run lint" in r and "frontend" in r, f"lint row: {r}")
elif rule == "cmd-typecheck":
    r = row("typecheck"); need("npm run typecheck" in r, f"typecheck row: {r}")
elif rule == "cmd-build":
    r = row("build"); need("npm run build" in r and "dotnet build" in r, f"build row: {r}")
elif rule == "cmd-test":
    r = row("unit test"); need(re.search(r"npm (run )?test|vitest run", r) and "dotnet test" in r, f"unit test row: {r}")
elif rule == "cmd-e2e":
    r = row("e2e test"); need(re.search(r"npx playwright test|npm run e2e", r), f"e2e row: {r}")
elif rule == "cmd-e2e-grep":
    r = row("e2e test by tag/grep"); need("--grep" in r or "-g " in r, f"e2e grep row: {r}")
elif rule == "cmd-start":
    r = row("start app (for e2e)"); need(re.search(r"dotnet run|webServer|playwright", r, re.I) and re.search(r"npm (--prefix frontend )?run dev|webServer|playwright", r, re.I), f"start row: {r}")
elif rule == "backend":
    s = section("Backend")
    for fact, rx in (("controllers/services layering", r"controller"), ("ProblemDetails errors", r"problem ?details"), ("DataAnnotations validation", r"data ?annotations|\[Range|\[Required"), ("JWT auth", r"jwt|bearer"), ("SHOPLITE_JWT_KEY secret", r"SHOPLITE_JWT_KEY"), ("no migrations (InMemory)", r"not present|in-?memory|EnsureCreated")):
        need(re.search(rx, s, re.I), f"backend section misses: {fact}")
elif rule == "frontend":
    s = section("Frontend (web)")
    for fact, rx in (("React + TypeScript", r"react"), ("TypeScript", r"typescript|\bTS\b"), ("React Router", r"router"), ("Vite", r"vite")):
        need(re.search(rx, s, re.I), f"frontend section misses: {fact}")
elif rule == "i18n":
    s = section("i18n")
    need(re.search(r"i18next", s, re.I) and re.search(r"fr\.json|locales", s, re.I) and re.search(r"resx|IStringLocalizer|Accept-Language", s, re.I), "i18n must cover react-i18next locale files and the API's resx/Accept-Language")
elif rule == "contract":
    s = section("API contract")
    need("contracts/openapi.yaml" in s, "contract location missing")
    need(re.search(r"client-generation[^\n]*not present|generation[^\n]*not present|hand-written", s, re.I), "client generation should be 'not present'")
    need(re.search(r"Microsoft\.AspNetCore\.OpenApi|openapi/v1\.json|AddOpenApi|MapOpenApi", s, re.I), "spec-emitting tool missing")
elif rule == "tests":
    s = section("Tests")
    need(re.search(r"xunit", s, re.I) and re.search(r"vitest", s, re.I) and re.search(r"playwright", s, re.I) and "tests/e2e" in s, "tests section incomplete (xUnit, Vitest, Playwright, tests/e2e)")
elif rule == "security":
    s = section("Security tooling present"); need(re.search(r"npm audit", s, re.I), "security tooling section must at least report npm audit")
elif rule == "changelog":
    need(re.search(r"bootstrap", section("Change log"), re.I), "change log without a bootstrap entry")
print("ok")
PY
}

check cs01-sections protocol "All imposed sections present (exact headings)" -- conv sections
check cs01-length protocol "Under ~150 lines" -- conv length
check cs01-changelog protocol "Change log has the bootstrap entry" -- conv changelog
check cs01-mobile functional "Mobile section: 'not present' everywhere" -- conv mobile-not-present
check cs01-repos functional "Repositories: backend/ and frontend/" -- conv repositories
check cs01-backend functional "Backend facts (layering, ProblemDetails, validation, JWT, secret, migrations)" -- conv backend
check cs01-frontend functional "Frontend facts (React, TypeScript, Router, Vite)" -- conv frontend
check cs01-i18n functional "i18n facts (react-i18next files + API resx/Accept-Language)" -- conv i18n
check cs01-contract functional "API contract facts (location, no client generator, spec emitter)" -- conv contract
check cs01-tests functional "Tests facts (xUnit, Vitest, Playwright, tests/e2e)" -- conv tests
check cs01-cmd-lint functional "Command: lint" -- conv cmd-lint
check cs01-cmd-typecheck functional "Command: typecheck" -- conv cmd-typecheck
check cs01-cmd-build functional "Command: build (npm + dotnet)" -- conv cmd-build
check cs01-cmd-test functional "Command: unit test (npm + dotnet)" -- conv cmd-test
check cs01-cmd-e2e functional "Command: e2e" -- conv cmd-e2e
check cs01-cmd-grep functional "Command: e2e by tag/grep" -- conv cmd-e2e-grep
check cs01-cmd-start functional "Command: start app for e2e" -- conv cmd-start
check cs01-security protocol "Security tooling section from real checks" -- conv security
check cs01-summary protocol "One-line summary with mode and path" -- report_mentions 'bootstrap.*conventions\.md|conventions\.md.*bootstrap'

finish
