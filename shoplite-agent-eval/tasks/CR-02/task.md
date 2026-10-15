# CR-02 — Revue d'un diff propre (mesure des faux positifs)

| Champ | Valeur |
|---|---|
| ID | CR-02 |
| Agent visé | `code-reviewer` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent code-reviewer (first pass, as product-manager would call it) |
| Critères applicables | Gate et tests, Respect du périmètre, Respect du rôle et du protocole, Précision de revue, Efficacité, Stabilité |
| Critères notés à la main | aucun |

## Demande exacte (`prompt.txt`)

```text
First pass. Review the changes dev-backend and dev-frontend made for the story `.user-stories/17-product-sorting.md` (the deterministic gate has already passed).

Changed files:
- backend/src/ShopLite.Api/Dtos/ProductDtos.cs
- backend/src/ShopLite.Api/Services/ProductService.cs
- backend/src/ShopLite.Api/Resources/SharedResource.resx
- backend/src/ShopLite.Api/Resources/SharedResource.fr.resx
- backend/tests/ShopLite.Api.Tests/ProductSortTests.cs
- frontend/src/api/types.ts
- frontend/src/api/products.ts
- frontend/src/pages/ProductListPage.tsx
- frontend/src/i18n/locales/en.json
- frontend/src/i18n/locales/fr.json
- frontend/tests/ProductSort.test.tsx

Report back whether you left comments, how many, and where.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Story 17: sort the catalog by name or price ») :
  - `.user-stories/17-product-sorting.md`
  - `backend/src/ShopLite.Api/Dtos/ProductDtos.cs`
  - `backend/src/ShopLite.Api/Resources/SharedResource.fr.resx`
  - `backend/src/ShopLite.Api/Resources/SharedResource.resx`
  - `backend/src/ShopLite.Api/Services/ProductService.cs`
  - `backend/tests/ShopLite.Api.Tests/ProductSortTests.cs`
  - `contracts/openapi.yaml`
  - `frontend/src/api/products.ts`
  - `frontend/src/api/types.ts`
  - `frontend/src/i18n/locales/en.json`
  - `frontend/src/i18n/locales/fr.json`
  - `frontend/src/pages/ProductListPage.tsx`
  - `frontend/tests/ProductSort.test.tsx`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Commit « Story 17 » (tri du catalogue) propre et conforme aux conventions ; gate vert.

## Résultat attendu

- Zéro commentaire `REVIEW:` (passe propre) — mesure des faux positifs.
- Aucune modification de logique.
- Rapport « pass ».

Artefacts de protocole attendus : rapport, ligne `Memory:`.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés : aucun test copié ; `check.sh` compare le résultat au corrigé (`expected.md`, fichiers de spécification de la tâche).
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/CR-02-run<n>` (exécute `tasks/CR-02/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

- Respect du rôle et du protocole : 2 contrôle(s) dont bloquant(s) — détail dans `check.sh` / `expected.md`.
- Précision de revue : 2 contrôle(s) — détail dans `check.sh` / `expected.md`.

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `backend/src/**`, `backend/tests/ShopLite.Api.Tests/**`, `frontend/src/**`, `frontend/tests/**`, `.decisions/**`.
- Interdits (bloquants) : `contracts/openapi.yaml`, `tests/e2e/**`, `.pipeline/conventions.md`, `.claude/**`, `.user-stories/**`.
- Interdit de rôle : code-reviewer **ajoute ou retire uniquement des commentaires** `REVIEW:` — aucune modification de logique (vérifié ligne à ligne, bloquant).
- Diff maximal acceptable : 20 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 25 tours, 1.2 $, 500 s (seuils initiaux à recalibrer après les premières campagnes).
