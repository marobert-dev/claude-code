# BE-05 — Optimisation N+1 de l'historique des commandes

| Champ | Valeur |
|---|---|
| ID | BE-05 |
| Agent visé | `dev-backend` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent dev-backend |
| Critères applicables | Gate et tests, Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Contrat API, Performance, Qualité du code, Qualité des tests produits, Efficacité, Stabilité |
| Critères notés à la main | Qualité du code |

## Demande exacte (`prompt.txt`)

```text
Implement the backend scope of the story `.user-stories/08-order-history-performance.md`.

Read its description, Acceptance Criteria and Technical Plan, plus the operations it references in `contracts/openapi.yaml` (`listMyOrders`, `getOrder`). Project conventions are in `.pipeline/conventions.md`.

When you are done, report back: files created/modified, the final request/response contract of every changed endpoint, any dependency added, any deviation from the plan, open TODOs and convention gaps.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Plan story 08: order history loads in a constant number of queries ») :
  - `.user-stories/08-order-history-performance.md`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story analysée (historique des commandes en nombre de requêtes constant). Contrat inchangé.

## Résultat attendu

- `GET /api/orders` ≤ 2 commandes SQL quel que soit le nombre de commandes (mesuré par un intercepteur EF sur SQLite en mémoire dans le test caché).
- Réponse identique (ordre, lignes, noms, prix, totaux) sur SQLite et sur InMemory.
- Projection `AsNoTracking().Select(...)`, pas de boucle par ligne.

Artefacts de protocole attendus : rapport, ligne `Memory:`.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés (copiés après l'agent) : `hidden-tests/backend/BE05_OrderHistoryPerformanceTests.cs`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/BE-05-run<n>` (exécute `tasks/BE-05/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `be05-max-queries` | Performance | History issues <= 2 SQL commands (measured on SQLite) |  |
| `be05-constant` | Performance | Query count independent of the number of orders |  |
| `be05-shape` | Correction fonctionnelle | Response unchanged (relational provider) |  |
| `be05-inmemory` | Correction fonctionnelle | Response unchanged (InMemory provider) |  |
| `be05-single` | Correction fonctionnelle | Single order unchanged |  |
| `be05-contract-untouched` | Contrat API | contracts/openapi.yaml unchanged by dev-backend |  |
| `be05-projection` | Qualité du code | GetOrdersAsync projects with AsNoTracking, no per-row loop |  |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `backend/src/**`, `backend/tests/ShopLite.Api.Tests/**`, `.decisions/**`.
- Interdits (bloquants) : `contracts/openapi.yaml`, `frontend/**`, `tests/e2e/**`, `.pipeline/conventions.md`, `.claude/**`.
- Interdit de rôle : dev-backend ne modifie jamais `contracts/openapi.yaml` (l'analyst en est propriétaire) ; ne touche pas au front ni aux tests e2e ; ne supprime ni n'affaiblit aucun test.
- Diff maximal acceptable : 250 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 50 tours, 3.0 $, 1200 s (seuils initiaux à recalibrer après les premières campagnes).
