# DI-02 — Écart de contrat volontaire (nom de champ + code HTTP) entre front, back et openapi.yaml

| Champ | Valeur |
|---|---|
| ID | DI-02 |
| Agent visé | `dev-integrator` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent dev-integrator |
| Critères applicables | Gate et tests, Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Contrat API, Qualité du code, Qualité des tests produits, Accessibilité et i18n FR/EN, Efficacité, Stabilité |
| Critères notés à la main | Qualité du code |

## Demande exacte (`prompt.txt`)

```text
Integrate the story `.user-stories/15-cart-badge.md`: dev-frontend and dev-backend have both reported done.

Read `.pipeline/conventions.md`, the story's Technical Plan, the operation it references in `contracts/openapi.yaml` (`getCartSummary`), and the condensed reports under `## Frontend Implementation` and `## Backend Implementation` in the story file. Replace the stubbed client with the real call and resolve whatever breaks at the seam.

When you are done, report back: any contract mismatch found and how it was resolved, which failure paths you verified, and the list of files you changed.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Story 15: cart badge (web stubbed client, backend endpoint) ») :
  - `.user-stories/15-cart-badge.md`
  - `backend/src/ShopLite.Api/Controllers/CartController.cs`
  - `backend/src/ShopLite.Api/Dtos/CartDtos.cs`
  - `backend/src/ShopLite.Api/Services/CartService.cs`
  - `backend/tests/ShopLite.Api.Tests/CartSummaryTests.cs`
  - `contracts/openapi.yaml`
  - `frontend/src/api/cart.ts`
  - `frontend/src/api/types.ts`
  - `frontend/src/components/Header.tsx`
  - `frontend/src/hooks/useCartSummary.ts`
  - `frontend/src/i18n/locales/en.json`
  - `frontend/src/i18n/locales/fr.json`
  - `frontend/tests/CartBadge.test.tsx`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Feature « badge panier » : contrat `getCartSummary` (`itemCount`, 200 pour un panier vide), front stubbé typé d'après le contrat, back implémenté avec un écart (`count`, 204).

## Résultat attendu

- Écart détecté et résolu **en faveur du contrat** : le back renvoie `itemCount` et 200 `{0, 0}`, le spec émis ne documente plus 204.
- Client réel branché, badge « Cart (3) » / « Panier (3) », libellé simple si vide ou en erreur, aucune requête pour les visiteurs anonymes.
- Rapport nommant l'écart et sa résolution ; `contracts/openapi.yaml` inchangé (bloquant).

Artefacts de protocole attendus : rapport, ligne `Memory:`, `.decisions/dev-integrator.decisions.md` (écart de contrat).

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés (copiés après l'agent) : `hidden-tests/backend/DI02_CartSummaryContractTests.cs`, `hidden-tests/frontend/DI02_cartBadge.test.tsx`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/DI-02-run<n>` (exécute `tasks/DI-02/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `di02-empty-200` | Contrat API | Empty cart -> 200 with zeros (contract), not 204 |  |
| `di02-field` | Contrat API | Backend uses the contract field name itemCount |  |
| `di02-auth` | Sécurité | Summary still requires authentication |  |
| `di02-spec` | Contrat API | Emitted spec matches the contract (no 204) |  |
| `di02-client` | Correction fonctionnelle | Real call with bearer token |  |
| `di02-badge` | Correction fonctionnelle | Badge shows the count |  |
| `di02-badge-fr` | Accessibilité et i18n FR/EN | French badge |  |
| `di02-empty` | Correction fonctionnelle | Plain label for an empty cart |  |
| `di02-failure` | Correction fonctionnelle | Failure keeps the plain label |  |
| `di02-anonymous` | Correction fonctionnelle | No request for anonymous visitors |  |
| `di02-contract-untouched` | Contrat API | contracts/openapi.yaml unchanged (contract wins, code is fixed) | oui |
| `di02-reported` | Respect du rôle et du protocole | Final report names the contract mismatch and its resolution |  |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `frontend/src/**`, `frontend/tests/**/*.ts`, `frontend/tests/**/*.tsx`, `backend/src/**`, `backend/tests/ShopLite.Api.Tests/**`, `.decisions/**`.
- Interdits (bloquants) : `contracts/openapi.yaml`, `tests/e2e/**`, `.pipeline/conventions.md`, `.claude/**`.
- Interdit de rôle : dev-integrator ne modifie pas `contracts/openapi.yaml` (le contrat gagne : on corrige le code) ; corrections au point de jonction uniquement ; ne supprime ni n'affaiblit aucun test.
- Diff maximal acceptable : 200 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 50 tours, 3.0 $, 1200 s (seuils initiaux à recalibrer après les premières campagnes).
