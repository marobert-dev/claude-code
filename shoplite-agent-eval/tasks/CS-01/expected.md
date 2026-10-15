# CS-01 — corrigé (ne jamais copier dans un run)

Défauts liés : aucun (voir `answer-key/planted-defects.md`).

Comparer section par section avec `fixtures/conventions.golden.md`.

Points que la plupart des scouts ratent (à noter dans la fiche) :
- `.claude/gate.local.sh` remplace la détection automatique du gate (le backend n'a qu'un `.sln` à la racine de `backend/`).
- Les commandes de build/test existent **à la fois** côté `frontend/` (npm) et `backend/` (dotnet) ; un tableau qui n'en cite qu'une est incomplet.
- `start app (for e2e)` : c'est `playwright.config.ts` (`webServer`) qui démarre `dotnet run --project backend/src/ShopLite.Api --no-launch-profile --urls http://localhost:5080` et `npm --prefix frontend run dev`.
- `Migrations tool: not present` (InMemory + `EnsureCreated`), `Client-generation tool: not present` (types écrits à la main), spec émis par `Microsoft.AspNetCore.OpenApi` (`/openapi/v1.json` en Development).
- `## Security tooling present` doit refléter la machine (vérifications `which`) : sur la machine de génération seuls `npm audit` et `dotnet list package --vulnerable` existaient.

Notation : `functional` = proportion des faits/commandes trouvés ; `protocol` = sections exactes, longueur, change log, résumé.

## Contrôles automatiques (détail)

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `cs01-sections` | Respect du rôle et du protocole | All imposed sections present (exact headings) |  |
| `cs01-length` | Respect du rôle et du protocole | Under ~150 lines |  |
| `cs01-changelog` | Respect du rôle et du protocole | Change log has the bootstrap entry |  |
| `cs01-mobile` | Correction fonctionnelle | Mobile section: 'not present' everywhere |  |
| `cs01-repos` | Correction fonctionnelle | Repositories: backend/ and frontend/ |  |
| `cs01-backend` | Correction fonctionnelle | Backend facts (layering, ProblemDetails, validation, JWT, secret, migrations) |  |
| `cs01-frontend` | Correction fonctionnelle | Frontend facts (React, TypeScript, Router, Vite) |  |
| `cs01-i18n` | Correction fonctionnelle | i18n facts (react-i18next files + API resx/Accept-Language) |  |
| `cs01-contract` | Correction fonctionnelle | API contract facts (location, no client generator, spec emitter) |  |
| `cs01-tests` | Correction fonctionnelle | Tests facts (xUnit, Vitest, Playwright, tests/e2e) |  |
| `cs01-cmd-lint` | Correction fonctionnelle | Command: lint |  |
| `cs01-cmd-typecheck` | Correction fonctionnelle | Command: typecheck |  |
| `cs01-cmd-build` | Correction fonctionnelle | Command: build (npm + dotnet) |  |
| `cs01-cmd-test` | Correction fonctionnelle | Command: unit test (npm + dotnet) |  |
| `cs01-cmd-e2e` | Correction fonctionnelle | Command: e2e |  |
| `cs01-cmd-grep` | Correction fonctionnelle | Command: e2e by tag/grep |  |
| `cs01-cmd-start` | Correction fonctionnelle | Command: start app for e2e |  |
| `cs01-security` | Respect du rôle et du protocole | Security tooling section from real checks |  |
| `cs01-summary` | Respect du rôle et du protocole | One-line summary with mode and path |  |

## Points d'attention pour la notation manuelle

- Qualité du code : conventions de `.pipeline/conventions.md`, lisibilité, absence de commentaires inutiles, typage, découpage.
- Vérifier que le rapport final de l'agent correspond à ce qui a réellement été fait (`.eval/agent-report.md`).
- Saisir les notes manuelles dans `<run>/.eval/manual-scores.json` (ex. `{"code_quality": 2, "notes": "..."}`) puis relancer `scripts/score.py`.
