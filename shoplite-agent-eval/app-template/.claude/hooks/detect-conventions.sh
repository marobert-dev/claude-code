#!/usr/bin/env bash
# Mechanical half of conventions-scout: prints, as Markdown, the facts a script can establish for sure —
# repos and manifests, frameworks from declared dependencies, the exact commands the gate would run,
# locale/e2e locations and installed security tools. conventions-scout copies these and spends its reading
# on what needs judgment (layering, error handling, validation, auth, styling, naming).
# Usage: bash .claude/hooks/detect-conventions.sh   (from the workspace root; read-only, installs nothing)
set -u

# Same project dirs as gate.sh: the root plus its immediate subdirectories.
DIRS=". $(find . -mindepth 1 -maxdepth 1 -type d ! -name '.*' ! -name node_modules ! -name docs -printf '%f ' 2>/dev/null)"
HAS_JQ=""; command -v jq >/dev/null 2>&1 && HAS_JQ=1

# Dependency name -> what it tells about the project. Only names that settle a convention on their own.
NODE_MARKERS='react:React
react-native:React Native
expo:Expo
next:Next.js
vue:Vue
@angular/core:Angular
svelte:Svelte
vite:Vite
typescript:TypeScript
vitest:Vitest (unit)
jest:Jest (unit)
@testing-library/react:Testing Library (React)
@playwright/test:Playwright (e2e)
@axe-core/playwright:axe for Playwright (a11y checks in e2e)
jest-axe:jest-axe (a11y checks in unit tests)
vitest-axe:vitest-axe (a11y checks in unit tests)
msw:MSW (API mocking)
cypress:Cypress (e2e)
detox:Detox (e2e, mobile)
i18next:i18next
react-i18next:react-i18next
vue-i18n:vue-i18n
react-intl:react-intl
react-router-dom:React Router
react-router:React Router
@react-navigation/native:React Navigation
vue-router:Vue Router
@reduxjs/toolkit:Redux Toolkit
zustand:Zustand
pinia:Pinia
@tanstack/react-query:TanStack Query
axios:axios
tailwindcss:Tailwind CSS
styled-components:styled-components
@emotion/react:Emotion
sass:Sass
eslint:ESLint
prettier:Prettier
zod:zod
react-hook-form:React Hook Form
@sveltejs/kit:SvelteKit
nuxt:Nuxt
openapi-typescript:openapi-typescript (client types)
@hey-api/openapi-ts:hey-api (client generation)
orval:orval (client generation)
@redocly/cli:Redocly CLI (contract lint)
@stoplight/spectral-cli:Spectral (contract lint)'

DOTNET_MARKERS='Microsoft.EntityFrameworkCore.InMemory:EF Core InMemory provider (no real transactions)
Microsoft.EntityFrameworkCore.SqlServer:EF Core SQL Server
Npgsql.EntityFrameworkCore.PostgreSQL:EF Core PostgreSQL
Microsoft.EntityFrameworkCore.Sqlite:EF Core SQLite
Microsoft.EntityFrameworkCore:EF Core
Dapper:Dapper
FluentValidation:FluentValidation
FluentValidation.AspNetCore:FluentValidation
MediatR:MediatR
AutoMapper:AutoMapper
Serilog.AspNetCore:Serilog
Microsoft.AspNetCore.Authentication.JwtBearer:JWT bearer auth
Microsoft.AspNetCore.Identity.EntityFrameworkCore:ASP.NET Core Identity
Swashbuckle.AspNetCore:Swashbuckle (OpenAPI emitted by the backend)
NSwag.AspNetCore:NSwag (OpenAPI emitted by the backend)
Microsoft.AspNetCore.OpenApi:Microsoft.AspNetCore.OpenApi (OpenAPI emitted by the backend)
xunit:xUnit
NUnit:NUnit
MSTest.TestFramework:MSTest
Moq:Moq
NSubstitute:NSubstitute
FluentAssertions:FluentAssertions
Microsoft.AspNetCore.Mvc.Testing:WebApplicationFactory integration tests'

node_deps () {  # node_deps <package.json>: "name<TAB>declared version", one dependency per line
  if [ -n "$HAS_JQ" ]; then
    jq -r '[.dependencies, .devDependencies, .peerDependencies] | map(select(.) | to_entries[]) | .[] | "\(.key)\t\(.value)"' "$1" 2>/dev/null
  else
    # Without jq: any "name": "<version>" pair — a version starts with ^, ~, a digit, * or a known tag.
    grep -o '"[^"]*"[[:space:]]*:[[:space:]]*"\([~^0-9*]\|latest\|next\|workspace:\|file:\|npm:\)[^"]*"' "$1" \
      | sed 's/^"\([^"]*\)"[[:space:]]*:[[:space:]]*"\([^"]*\)"$/\1\t\2/'
  fi
}
with_versions () {  # with_versions <dir> <markers> < "name<TAB>declared": "Label <installed or declared version>" lines
  local dir="$1" markers="$2" name declared label installed
  while IFS="$(printf '\t')" read -r name declared; do
    label="$(printf '%s\n' "$markers" | awk -F: -v n="$name" '$1 == n { sub(/^[^:]*:/, ""); print; exit }')"
    [ -n "$label" ] || continue
    installed="$(grep -m1 -o '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "$dir/node_modules/$name/package.json" 2>/dev/null | cut -d'"' -f4)"
    echo "$label ${installed:-$declared}"
  done | awk '!seen[$0]++'
}
npm_script () {  # npm_script <package.json> <name>: the script's command, empty when absent
  if [ -n "$HAS_JQ" ]; then jq -r --arg s "$2" '.scripts[$s] // empty' "$1" 2>/dev/null
  else sed -n '/"scripts"[[:space:]]*:/,/}/p' "$1" | grep -m1 "\"$2\"[[:space:]]*:" | sed 's/^[^:]*:[[:space:]]*"\(.*\)",\{0,1\}[[:space:]]*$/\1/'; fi
}
rel () { local p="${1#./}"; echo "${p:-.}"; }

echo "# Detected facts (detect-conventions.sh — mechanical, verify only what looks odd)"
echo
echo "## Repositories"
for d in $DIRS; do
  manifests="$(cd "$d" && ls -1 package.json *.sln *.slnx *.csproj pubspec.yaml pyproject.toml go.mod pom.xml build.gradle Dockerfile 2>/dev/null | tr '\n' ' ')"
  top="$(git -C "$d" rev-parse --show-toplevel 2>/dev/null)"
  [ -n "$manifests" ] && echo "- \`$(rel "$d")\`: ${manifests% }${top:+ (git: $(basename "$top"))}"
done
find . -maxdepth 4 -name '*.csproj' -not -path '*/node_modules/*' -not -path '*/bin/*' -not -path '*/obj/*' 2>/dev/null \
  | sed 's|^\./||' | sed 's/^/- project: `/; s/$/`/'

echo
echo "## Frameworks and libraries (from declared dependencies, with the installed version when node_modules has it)"
for d in $DIRS; do
  [ -f "$d/package.json" ] || continue
  libs="$(node_deps "$d/package.json" | with_versions "$d" "$NODE_MARKERS" | paste -sd ',' - | sed 's/,/, /g')"
  echo "- \`$(rel "$d")/package.json\`: ${libs:-none of the known markers}"
done
find . -maxdepth 4 -name '*.csproj' -not -path '*/node_modules/*' -not -path '*/bin/*' -not -path '*/obj/*' 2>/dev/null | while IFS= read -r p; do
  sdk="$(grep -o 'Sdk="[^"]*"' "$p" | head -1 | cut -d'"' -f2)"
  tfm="$(grep -o '<TargetFrameworks\{0,1\}>[^<]*' "$p" | head -1 | cut -d'>' -f2)"
  libs="$(grep -o 'PackageReference Include="[^"]*"\( Version="[^"]*"\)\{0,1\}' "$p" \
    | sed 's/PackageReference Include="\([^"]*\)"\( Version="\([^"]*\)"\)\{0,1\}/\1\t\3/' | with_versions "$(dirname "$p")" "$DOTNET_MARKERS" \
    | sed 's/ $//' | paste -sd ',' - | sed 's/,/, /g')"
  echo "- \`${p#./}\`: ${sdk:-?} ${tfm:+($tfm)}; ${libs:-none of the known markers}"
done

echo
echo "## Commands (lint/typecheck/build/unit test = what .claude/hooks/gate.sh runs; e2e and start from package.json scripts)"
echo
# One row per step, as in conventions.md: every directory that has the step goes in the same row.
declare -A DIR_OF CMD_OF
add_cmd () {  # add_cmd <step> <dir> <command>
  DIR_OF[$1]="${DIR_OF[$1]:+${DIR_OF[$1]}; }$2"
  CMD_OF[$1]="${CMD_OF[$1]:+${CMD_OF[$1]}; }\`$3\` ($2)"
}
for d in $DIRS; do
  dir="$(rel "$d")"
  if [ -f "$d/package.json" ]; then
    pj="$d/package.json"
    for s in lint typecheck build; do
      [ -n "$(npm_script "$pj" "$s")" ] && add_cmd "$s" "$dir" "npm run $s"
    done
    [ -z "$(npm_script "$pj" typecheck)" ] && [ -f "$d/tsconfig.json" ] && add_cmd typecheck "$dir" "npx tsc --noEmit"
    [ -n "$(npm_script "$pj" test)" ] && add_cmd "unit test" "$dir" "npm test"
    for s in e2e test:e2e; do
      [ -n "$(npm_script "$pj" "$s")" ] && add_cmd "e2e test" "$dir" "npm run $s" && break
    done
    for s in dev start; do
      [ -n "$(npm_script "$pj" "$s")" ] && add_cmd "start app (for e2e)" "$dir" "npm run $s" && break
    done
  fi
  if compgen -G "$d/*.sln" >/dev/null || compgen -G "$d/*.slnx" >/dev/null || compgen -G "$d/*.csproj" >/dev/null; then
    add_cmd build "$dir" "dotnet build --nologo -v q"
    add_cmd "unit test" "$dir" "dotnet test --nologo --no-build -v q"
  fi
done
echo "| Step | Directory | Command |"
echo "|---|---|---|"
for s in lint typecheck build "unit test" "e2e test" "start app (for e2e)"; do
  echo "| $s | ${DIR_OF[$s]:-} | ${CMD_OF[$s]:-not detected} |"
done
[ -f .claude/gate.local.sh ] && echo "- \`.claude/gate.local.sh\` exists: the gate runs it instead of the detection above."
echo "- Not detected by this script: e2e by tag/grep, and how to start a backend that has no npm script — read the e2e config (e.g. \`webServer\`) and the backend's launch settings."

echo
echo "## Configuration keys read from the environment (names only, from source code)"
keys="$(grep -rhoE --include='*.cs' --include='*.ts' --include='*.tsx' --include='*.js' \
  --exclude-dir=node_modules --exclude-dir=bin --exclude-dir=obj --exclude-dir=dist --exclude-dir=tests --exclude-dir=test \
  '(GetEnvironmentVariable\(|process\.env\.|import\.meta\.env\.|")[A-Z][A-Z0-9]*_[A-Z0-9_]{2,}' . 2>/dev/null \
  | sed -E 's/^(GetEnvironmentVariable\(|process\.env\.|import\.meta\.env\.|")//' | sort -u | head -20 | paste -sd ' ' -)"
echo "- ${keys:-none found}"

echo
echo "## Locations"
cfg="$(find . -maxdepth 3 \( -name 'playwright.config.*' -o -name 'cypress.config.*' -o -name '.detoxrc*' -o -name 'vitest.config.*' -o -name 'jest.config.*' \) -not -path '*/node_modules/*' 2>/dev/null | sed 's|^\./||' | paste -sd ' ' -)"
echo "- Test configs: ${cfg:-not present}"
e2e="$(find . -maxdepth 4 -type d \( -name e2e -o -name 'e2e-tests' \) -not -path '*/node_modules/*' 2>/dev/null | sed 's|^\./||' | paste -sd ' ' -)"
echo "- e2e folders: ${e2e:-not present}"
loc="$(find . -maxdepth 6 \( -path '*/locales/*.json' -o -path '*/i18n/*.json' -o -path '*/lang/*.json' -o -name '*.resx' \) -not -path '*/node_modules/*' -not -path '*/bin/*' -not -path '*/obj/*' 2>/dev/null | sed 's|^\./||' | head -10 | paste -sd ' ' -)"
echo "- Locale files: ${loc:-not present}"
echo "- API contract: $( [ -f contracts/openapi.yaml ] && echo 'contracts/openapi.yaml' || echo 'not present')"
ci="$(ls -1 .github/workflows/*.yml .github/workflows/*.yaml .gitlab-ci.yml azure-pipelines.yml 2>/dev/null | paste -sd ' ' -)"
echo "- CI files: ${ci:-not present}"

echo
echo "## Agent instruction files (subagents do not load them: copy the rules that constrain code changes into conventions)"
inst="$(for d in $DIRS; do for f in CLAUDE.md AGENTS.md .github/copilot-instructions.md .cursorrules; do
  [ -f "$d/$f" ] && printf '%s\n' "$(rel "$d")/$f"; done; done | sed 's|^\./||' | paste -sd ' ' -)"
echo "- ${inst:-not present}"

echo
echo "## Security tooling present"
tools=""
for t in gitleaks semgrep osv-scanner schemathesis oasdiff; do command -v "$t" >/dev/null 2>&1 && tools="$tools $t"; done
command -v npm >/dev/null 2>&1 && [ -f package.json -o -n "$(find . -maxdepth 2 -name package.json -not -path '*/node_modules/*' 2>/dev/null | head -1)" ] && tools="$tools npm-audit"
command -v dotnet >/dev/null 2>&1 && tools="$tools dotnet-list-package"
[ -f .claude/hooks/secret-scan.sh ] && tools="$tools secret-scan.sh"
echo "-${tools:- none}"

echo
echo "## Developer tooling present"
dev=""
for t in typescript-language-server csharp-ls redocly spectral; do command -v "$t" >/dev/null 2>&1 && dev="$dev $t"; done
echo "-${dev:- none} (language servers give agents diagnostics after each edit when the matching Claude Code LSP plugin is installed)"
