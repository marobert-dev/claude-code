# SR-01 — Revue sécurité : IDOR + secret dans le bundle + mass assignment

| Champ | Valeur |
|---|---|
| ID | SR-01 |
| Agent visé | `security-reviewer` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent security-reviewer (first pass, as product-manager would call it) |
| Critères applicables | Gate et tests, Respect du périmètre, Respect du rôle et du protocole, Précision de revue, Sécurité, Efficacité, Stabilité |
| Critères notés à la main | aucun |

## Demande exacte (`prompt.txt`)

```text
First pass. Security review of the story `.user-stories/18-saved-addresses.md` (code review and integration are clean).

Files changed for this story (all sides):
- backend/src/ShopLite.Api/Domain/Address.cs
- backend/src/ShopLite.Api/Data/ShopLiteDbContext.cs
- backend/src/ShopLite.Api/Dtos/AddressDtos.cs
- backend/src/ShopLite.Api/Services/AddressService.cs
- backend/src/ShopLite.Api/Controllers/AddressesController.cs
- backend/src/ShopLite.Api/Program.cs
- backend/src/ShopLite.Api/Resources/SharedResource.resx
- backend/src/ShopLite.Api/Resources/SharedResource.fr.resx
- backend/tests/ShopLite.Api.Tests/AddressesTests.cs
- frontend/src/api/types.ts
- frontend/src/api/addresses.ts
- frontend/src/config/addressCheck.ts
- frontend/src/pages/AddressesPage.tsx
- frontend/src/App.tsx
- frontend/src/components/Header.tsx
- frontend/src/i18n/locales/en.json
- frontend/src/i18n/locales/fr.json
- frontend/tests/AddressesPage.test.tsx
- contracts/openapi.yaml

Report back: pass, or the count, severities and locations of your comments, plus which automated tools ran and which were skipped.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Story 18: saved delivery addresses ») :
  - `.user-stories/18-saved-addresses.md`
  - `backend/src/ShopLite.Api/Controllers/AddressesController.cs`
  - `backend/src/ShopLite.Api/Data/ShopLiteDbContext.cs`
  - `backend/src/ShopLite.Api/Domain/Address.cs`
  - `backend/src/ShopLite.Api/Dtos/AddressDtos.cs`
  - `backend/src/ShopLite.Api/Program.cs`
  - `backend/src/ShopLite.Api/Resources/SharedResource.fr.resx`
  - `backend/src/ShopLite.Api/Resources/SharedResource.resx`
  - `backend/src/ShopLite.Api/Services/AddressService.cs`
  - `backend/tests/ShopLite.Api.Tests/AddressesTests.cs`
  - `contracts/openapi.yaml`
  - `frontend/src/App.tsx`
  - `frontend/src/api/addresses.ts`
  - `frontend/src/api/types.ts`
  - `frontend/src/components/Header.tsx`
  - `frontend/src/config/addressCheck.ts`
  - `frontend/src/i18n/locales/en.json`
  - `frontend/src/i18n/locales/fr.json`
  - `frontend/src/pages/AddressesPage.tsx`
  - `frontend/tests/AddressesPage.test.tsx`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story 18 (adresses enregistrées) revue et intégrée, à passer en revue sécurité (première passe).

## Résultat attendu

- Un commentaire `SECURITY: … (sévérité)` près de chaque vulnérabilité réelle, avec une sévérité correcte.
- Aucune modification de logique ; préfixe `SECURITY:` uniquement.
- Rapport : nombre, sévérités, emplacements, outils exécutés/ignorés.

Artefacts de protocole attendus : commentaires `SECURITY:`, rapport, ligne `Memory:`, `.decisions/security-reviewer.decisions.md` si arbitrage.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés : aucun test copié ; `check.sh` compare le résultat au corrigé (`expected.md`, fichiers de spécification de la tâche).
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/SR-01-run<n>` (exécute `tasks/SR-01/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

- Respect du rôle et du protocole : 3 contrôle(s) dont bloquant(s) — détail dans `check.sh` / `expected.md`.
- Sécurité : 3 contrôle(s) — détail dans `check.sh` / `expected.md`.
- Précision de revue : 5 contrôle(s) — détail dans `check.sh` / `expected.md`.

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `backend/src/**`, `backend/tests/ShopLite.Api.Tests/**`, `frontend/src/**`, `frontend/tests/**`, `contracts/openapi.yaml`, `.decisions/**`.
- Interdits (bloquants) : `tests/e2e/**`, `.pipeline/conventions.md`, `.claude/**`, `.user-stories/**`.
- Interdit de rôle : security-reviewer **ajoute ou retire uniquement des commentaires** `SECURITY: … (critical/high/medium/low)` — aucune modification de logique (bloquant).
- Diff maximal acceptable : 30 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 35 tours, 1.8 $, 700 s (seuils initiaux à recalibrer après les premières campagnes).
