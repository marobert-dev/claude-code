# BE-04 — Checkout atomique avec contrôle et décrément de stock

| Champ | Valeur |
|---|---|
| ID | BE-04 |
| Agent visé | `dev-backend` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent dev-backend |
| Critères applicables | Gate et tests, Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Contrat API, Sécurité, Qualité du code, Qualité des tests produits, Efficacité, Stabilité |
| Critères notés à la main | Qualité du code |

## Demande exacte (`prompt.txt`)

```text
Implement the backend scope of the story `.user-stories/07-reliable-checkout.md`.

Read its description, Acceptance Criteria, Copy (FR/EN) and Technical Plan, plus the operation it references in `contracts/openapi.yaml` (`checkout`). Project conventions are in `.pipeline/conventions.md`.

When you are done, report back: files created/modified, the final request/response contract of every changed endpoint, any dependency added, any deviation from the plan, open TODOs and convention gaps.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Plan story 07: checkout never oversells and never leaves half-created orders ») :
  - `.user-stories/07-reliable-checkout.md`
  - `contracts/openapi.yaml`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story analysée (checkout atomique). Contrat mis à jour (409 sur `checkout`). Le plan précise : un seul `SaveChangesAsync`, pas de transaction explicite (InMemory).

## Résultat attendu

- Stock insuffisant → 409 problem+json nommant les produits, rien ne change (commandes, panier, stock).
- Succès → stock décrémenté ; stock exact autorisé puis refusé ensuite.
- Échec pendant l'enregistrement → aucune commande partielle (vérifié par un intercepteur qui fait échouer l'enregistrement d'une ligne).
- Message FR, clés de ressources dans les deux `.resx`, `ProducesResponseType` 409 (spec émis).
- Tests de caractérisation des remises intacts.

Artefacts de protocole attendus : rapport, ligne `Memory:`, `.decisions/` si arbitrage.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés (copiés après l'agent) : `hidden-tests/backend/BE04_ReliableCheckoutTests.cs`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/BE-04-run<n>` (exécute `tasks/BE-04/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `be04-409` | Correction fonctionnelle | Insufficient stock -> 409, nothing changed |  |
| `be04-fr` | Correction fonctionnelle | Stock message localized in French |  |
| `be04-decrement` | Correction fonctionnelle | Successful checkout decrements stock |  |
| `be04-exact` | Correction fonctionnelle | Exact remaining stock allowed, then refused |  |
| `be04-atomic` | Correction fonctionnelle | Failure while saving leaves no partial order (atomicity) |  |
| `be04-spec` | Contrat API | Emitted spec documents the 409 response |  |
| `be04-contract-untouched` | Contrat API | contracts/openapi.yaml unchanged by dev-backend |  |
| `be04-characterization` | Correction fonctionnelle | Pricing characterization tests untouched |  |
| `be04-single-save` | Qualité du code | CheckoutAsync persists with a single SaveChanges (plan) |  |
| `be04-resx-fr` | Correction fonctionnelle | New messages added to both resource files |  |
| `be04-tests-added` | Qualité des tests produits | New tests cover stock and atomicity |  |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `backend/src/**`, `backend/tests/ShopLite.Api.Tests/**`, `.decisions/**`.
- Interdits (bloquants) : `contracts/openapi.yaml`, `frontend/**`, `tests/e2e/**`, `.pipeline/conventions.md`, `.claude/**`.
- Interdit de rôle : dev-backend ne modifie jamais `contracts/openapi.yaml` (l'analyst en est propriétaire) ; ne touche pas au front ni aux tests e2e ; ne supprime ni n'affaiblit aucun test.
- Diff maximal acceptable : 400 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 70 tours, 4.0 $, 1500 s (seuils initiaux à recalibrer après les premières campagnes).
