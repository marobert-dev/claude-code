# UT-01 — Couverture unitaire d'un service existant (ProductService)

| Champ | Valeur |
|---|---|
| ID | UT-01 |
| Agent visé | `unit-tester` |
| Modèle attendu (frontmatter) | `haiku` |
| Mode d'invocation | direct: claude -p --agent unit-tester |
| Critères applicables | Gate et tests, Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Qualité des tests produits, Qualité du code, Efficacité, Stabilité |
| Critères notés à la main | Qualité du code |

## Demande exacte (`prompt.txt`)

```text
code-reviewer signed off with zero remaining comments on the backend of the story `.user-stories/03-catalog-search.md`.

Write unit tests for the service `backend/src/ShopLite.Api/Services/ProductService.cs`, covering the requirements in the story's Acceptance Criteria and Technical Plan. Test the service directly (not through HTTP; the existing `ProductsTests.cs` integration tests already do that).

Report back what you covered and the result.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Update shared project files ») :
  - `.user-stories/03-catalog-search.md`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story 03 validée ; `ProductService` n'est couvert que par des tests HTTP. Conventions de référence.

## Résultat attendu

- Nouvelles classes de tests unitaires qui instancient `ProductService` directement (DbContext InMemory dédié).
- Tests verts, déterministes (3 exécutions), sans sommeil, horloge ni hasard.
- Tests qui détectent de vrais défauts : score de mutation mesuré par `check.sh` sur 6 mutants (≥ 5/6 visé).
- Aucune modification du code de production.

Artefacts de protocole attendus : fichiers de tests, rapport, ligne `Memory:`.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés : aucun ; les contrôles sont dans `check.sh`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/UT-01-run<n>` (exécute `tasks/UT-01/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `ut01-new-tests` | Correction fonctionnelle | New unit-test classes added |  |
| `ut01-direct` | Qualité des tests produits | Tests exercise ProductService directly (not only HTTP) |  |
| `ut01-deterministic` | Qualité des tests produits | New tests pass 3 runs in a row |  |
| `ut01-no-time-or-random` | Qualité des tests produits | No sleeps, wall clock or randomness in new tests |  |
| `ut01-src-untouched` | Respect du rôle et du protocole | Production code untouched (tests only) |  |
| `ut01-mutation-high` | Qualité des tests produits | Mutation score: at least 5 of 6 mutants killed |  |
| `ut01-mutation-medium` | Qualité des tests produits | Mutation score: at least 3 of 6 mutants killed |  |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `backend/tests/ShopLite.Api.Tests/**`, `.decisions/**`.
- Interdits (bloquants) : `backend/src/**`, `frontend/**`, `contracts/openapi.yaml`, `tests/e2e/**`, `.pipeline/conventions.md`, `.claude/**`.
- Interdit de rôle : unit-tester n'écrit que des tests (services, handlers, repositories, composants) — aucun code de production (bloquant).
- Diff maximal acceptable : 500 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 40 tours, 1.0 $, 900 s (seuils initiaux à recalibrer après les premières campagnes).
