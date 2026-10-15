# BE-01 — Validation d'entrée (quantités, prix client, taille de page)

| Champ | Valeur |
|---|---|
| ID | BE-01 |
| Agent visé | `dev-backend` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent dev-backend |
| Critères applicables | Gate et tests, Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Contrat API, Sécurité, Qualité du code, Qualité des tests produits, Efficacité, Stabilité |
| Critères notés à la main | Qualité du code |

## Demande exacte (`prompt.txt`)

```text
Implement the backend scope of the story `.user-stories/04-cart-input-validation.md`.

Read its description, Acceptance Criteria, Copy (FR/EN) and Technical Plan, plus the operations it references in `contracts/openapi.yaml` (`addCartItem`, `updateCartItem`, `listProducts`). Project conventions are in `.pipeline/conventions.md`.

When you are done, report back: files created/modified, the final request/response contract of every changed endpoint, any dependency added, any deviation from the plan, open TODOs and convention gaps.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Plan story 04: reject invalid cart quantities, client prices and oversized pages ») :
  - `.user-stories/04-cart-input-validation.md`
  - `contracts/openapi.yaml`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story déjà analysée (gabarit product-owner + `## Technical Plan`) ; le contrat a déjà été mis à jour par l'analyst (commit de fixture). Conventions de référence fournies. team-memory vide.

## Résultat attendu

- Quantités hors 1–99 refusées (400 localisé) à l'ajout et à la modification ; 1 et 99 acceptés.
- Le prix unitaire vient toujours du catalogue (champ client ignoré ou refusé).
- `pageSize` borné à 1–50 (400 en dehors).
- Messages de validation localisés FR (Accept-Language).
- Spec émis `/openapi/v1.json` cohérent avec le contrat (min/max, plus de `unitPrice`).
- Tests d'intégration ajoutés ; validation déclarative (DataAnnotations + clés de ressources).

Artefacts de protocole attendus : rapport (fichiers, contrat final, écarts, TODO, convention gaps), ligne `Memory:`, `.decisions/dev-backend.decisions.md` si arbitrage.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés (copiés après l'agent) : `hidden-tests/backend/BE01_InputValidationTests.cs`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/BE-01-run<n>` (exécute `tasks/BE-01/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `be01-qty-add` | Correction fonctionnelle | Out-of-range quantities rejected on add (0, -3, 100) |  |
| `be01-qty-bounds` | Correction fonctionnelle | Quantities 1 and 99 still accepted |  |
| `be01-qty-update` | Correction fonctionnelle | Out-of-range quantities rejected on update, line unchanged |  |
| `be01-page-size` | Correction fonctionnelle | pageSize limited to 1-50 (400 outside) |  |
| `be01-i18n` | Correction fonctionnelle | Validation messages localized in French |  |
| `be01-price` | Sécurité | Client-supplied unit price ignored or rejected (mass assignment closed) |  |
| `be01-spec` | Contrat API | Emitted /openapi/v1.json matches the contract constraints |  |
| `be01-contract-untouched` | Contrat API | contracts/openapi.yaml unchanged by dev-backend |  |
| `be01-tests-added` | Qualité des tests produits | New backend tests cover the story |  |
| `be01-range-attrs` | Qualité du code | Validation declared with DataAnnotations + Validation.Range key (project convention) |  |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `backend/src/**`, `backend/tests/ShopLite.Api.Tests/**`, `.decisions/**`.
- Interdits (bloquants) : `contracts/openapi.yaml`, `frontend/**`, `tests/e2e/**`, `.pipeline/conventions.md`, `.claude/**`.
- Interdit de rôle : dev-backend ne modifie jamais `contracts/openapi.yaml` (l'analyst en est propriétaire) ; ne touche pas au front ni aux tests e2e ; ne supprime ni n'affaiblit aucun test.
- Diff maximal acceptable : 350 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 60 tours, 3.0 $, 1200 s (seuils initiaux à recalibrer après les premières campagnes).
