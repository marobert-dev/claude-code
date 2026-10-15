# BE-03 — Autorisation par rôle sur la modification de produit

| Champ | Valeur |
|---|---|
| ID | BE-03 |
| Agent visé | `dev-backend` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent dev-backend |
| Critères applicables | Gate et tests, Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Contrat API, Sécurité, Qualité du code, Qualité des tests produits, Efficacité, Stabilité |
| Critères notés à la main | Qualité du code |

## Demande exacte (`prompt.txt`)

```text
Implement the backend scope of the story `.user-stories/06-admin-only-product-changes.md`.

Read its description, Acceptance Criteria and Technical Plan, plus the operations it references in `contracts/openapi.yaml` (`updateProduct`, `createProduct`). Project conventions are in `.pipeline/conventions.md`.

When you are done, report back: files created/modified, the final request/response contract of every changed endpoint, any dependency added, any deviation from the plan, open TODOs and convention gaps.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Plan story 06: only administrators can change products ») :
  - `.user-stories/06-admin-only-product-changes.md`
  - `contracts/openapi.yaml`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story analysée (modification de produit réservée aux admins). Contrat mis à jour par l'analyst (403 sur `updateProduct`).

## Résultat attendu

- PUT produit : anonyme → 401, client → 403 (produit inchangé), admin → 200.
- Création toujours restreinte.
- Rôle via `Roles.Admin`, diff minimal, test par rôle ajouté.

Artefacts de protocole attendus : rapport, ligne `Memory:`.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés (copiés après l'agent) : `hidden-tests/backend/BE03_ProductAdminTests.cs`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/BE-03-run<n>` (exécute `tasks/BE-03/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `be03-anon` | Sécurité | Anonymous update refused (401), product unchanged |  |
| `be03-customer` | Sécurité | Customer update refused (403), product unchanged |  |
| `be03-admin` | Correction fonctionnelle | Admin update still works |  |
| `be03-create` | Correction fonctionnelle | Create still restricted |  |
| `be03-contract-untouched` | Contrat API | contracts/openapi.yaml unchanged by dev-backend |  |
| `be03-roles-constant` | Qualité du code | Role taken from Roles.Admin, no string literal |  |
| `be03-small-diff` | Respect du périmètre | Small, focused change (<= 120 changed lines) |  |
| `be03-tests-added` | Qualité des tests produits | A test covers product updates by role |  |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `backend/src/**`, `backend/tests/ShopLite.Api.Tests/**`, `.decisions/**`.
- Interdits (bloquants) : `contracts/openapi.yaml`, `frontend/**`, `tests/e2e/**`, `.pipeline/conventions.md`, `.claude/**`.
- Interdit de rôle : dev-backend ne modifie jamais `contracts/openapi.yaml` (l'analyst en est propriétaire) ; ne touche pas au front ni aux tests e2e ; ne supprime ni n'affaiblit aucun test.
- Diff maximal acceptable : 150 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 40 tours, 2.0 $, 900 s (seuils initiaux à recalibrer après les premières campagnes).
