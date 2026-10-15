# BE-06 — Refactoring sans régression d'OrderService

| Champ | Valeur |
|---|---|
| ID | BE-06 |
| Agent visé | `dev-backend` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent dev-backend |
| Critères applicables | Gate et tests, Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Contrat API, Qualité du code, Qualité des tests produits, Efficacité, Stabilité |
| Critères notés à la main | Qualité du code |

## Demande exacte (`prompt.txt`)

```text
Implement the backend scope of the story `.user-stories/09-split-order-service.md`.

Read its description, Acceptance Criteria and Technical Plan. Project conventions are in `.pipeline/conventions.md`; the API contract is `contracts/openapi.yaml`.

When you are done, report back: files created/modified, confirmation that no endpoint contract changed, any dependency added, any deviation from the plan, open TODOs and convention gaps.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Plan story 09: split OrderService into focused collaborators ») :
  - `.user-stories/09-split-order-service.md`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story analysée (refactoring sans changement de comportement). Filet de sécurité : `OrderPricingCharacterizationTests.cs` (HTTP).

## Résultat attendu

- Comportement identique (remises aux bornes 100/200, numérotation, reçus EN/FR, opérations et codes du spec émis).
- `OrderService` ≥ 30 % plus court, remises / numérotation / formatage du reçu extraits dans leurs propres classes.
- Tests existants **non modifiés** (bloquant), tests unitaires ajoutés pour la tarification.

Artefacts de protocole attendus : rapport, ligne `Memory:`.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés (copiés après l'agent) : `hidden-tests/backend/BE06_RefactoringSafetyNetTests.cs`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/BE-06-run<n>` (exécute `tasks/BE-06/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `be06-discounts` | Correction fonctionnelle | Discount tiers and rounding unchanged |  |
| `be06-numbers` | Correction fonctionnelle | Order numbering unchanged |  |
| `be06-receipts` | Correction fonctionnelle | Receipts (EN/FR) unchanged |  |
| `be06-spec` | Contrat API | Emitted spec: same operations and status codes |  |
| `be06-contract-untouched` | Contrat API | contracts/openapi.yaml unchanged |  |
| `be06-tests-untouched` | Respect du rôle et du protocole | Existing backend tests not modified (refactoring safety net) | oui |
| `be06-shrunk` | Qualité du code | OrderService.cs at least 30% shorter |  |
| `be06-extracted` | Qualité du code | Discounts, numbering and receipt formatting moved out of OrderService |  |
| `be06-pricing-tests` | Qualité des tests produits | Unit tests added for the extracted pricing |  |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `backend/src/**`, `backend/tests/ShopLite.Api.Tests/**`, `.decisions/**`.
- Interdits (bloquants) : `contracts/openapi.yaml`, `frontend/**`, `tests/e2e/**`, `.pipeline/conventions.md`, `.claude/**`.
- Interdit de rôle : dev-backend ne modifie jamais `contracts/openapi.yaml` (l'analyst en est propriétaire) ; ne touche pas au front ni aux tests e2e ; ne supprime ni n'affaiblit aucun test.
- Diff maximal acceptable : 700 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 80 tours, 5.0 $, 1800 s (seuils initiaux à recalibrer après les premières campagnes).
