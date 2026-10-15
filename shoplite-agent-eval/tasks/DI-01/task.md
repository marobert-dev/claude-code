# DI-01 — Remplacer le client stubbé par le vrai appel (détail de commande)

| Champ | Valeur |
|---|---|
| ID | DI-01 |
| Agent visé | `dev-integrator` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent dev-integrator |
| Critères applicables | Gate et tests, Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Contrat API, Sécurité, Qualité du code, Qualité des tests produits, Efficacité, Stabilité |
| Critères notés à la main | Qualité du code |

## Demande exacte (`prompt.txt`)

```text
Integrate the story `.user-stories/14-order-detail-screen.md`: dev-frontend and dev-backend have both reported done.

Read `.pipeline/conventions.md`, the story's Technical Plan, the operation it references in `contracts/openapi.yaml` (`getOrder`), and the condensed reports under `## Frontend Implementation` and `## Backend Implementation` in the story file. Replace the stubbed client with the real call and resolve whatever breaks at the seam.

When you are done, report back: any contract mismatch found and how it was resolved, which failure paths you verified, and the list of files you changed.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Story 14: order detail screen (web, stubbed client) ») :
  - `.user-stories/14-order-detail-screen.md`
  - `frontend/src/App.tsx`
  - `frontend/src/api/orders.ts`
  - `frontend/src/i18n/locales/en.json`
  - `frontend/src/i18n/locales/fr.json`
  - `frontend/src/pages/OrderDetailPage.tsx`
  - `frontend/src/pages/OrdersPage.tsx`
  - `frontend/tests/OrderDetailPage.test.tsx`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

État de départ = sortie de référence de dev-frontend pour la story 14 (client `getOrder` stubbé, écran détail) + rapports condensés back/front dans la story.

## Résultat attendu

- `getOrder` appelle réellement `GET /api/orders/{id}` via `apiRequest` (jeton bearer, Accept-Language).
- 404 → `null` (état introuvable), 500/réseau → état erreur + réessayer, 401 → session effacée et redirection vers la connexion.
- Contrat inchangé, tests de dev-frontend conservés.

Artefacts de protocole attendus : rapport (écarts de contrat, chemins d'échec vérifiés, fichiers), ligne `Memory:`.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés (copiés après l'agent) : `hidden-tests/frontend/DI01_orderDetailIntegration.test.tsx`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/DI-01-run<n>` (exécute `tasks/DI-01/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `di01-call` | Contrat API | Real GET /api/orders/{id} with bearer token |  |
| `di01-404` | Contrat API | 404 problem -> null (contract + plan) |  |
| `di01-success` | Correction fonctionnelle | Page renders the real response |  |
| `di01-page-404` | Correction fonctionnelle | Not-found state wired to 404 |  |
| `di01-500` | Correction fonctionnelle | Error state + retry wired to 500 |  |
| `di01-network` | Correction fonctionnelle | Error state on network failure |  |
| `di01-401` | Sécurité | 401 clears the session and redirects to sign-in |  |
| `di01-contract-untouched` | Contrat API | contracts/openapi.yaml unchanged |  |
| `di01-uses-api-request` | Qualité du code | Real call goes through apiRequest (token, language, problem parsing) |  |
| `di01-no-hardcoded-url` | Qualité du code | No hard-coded host in the client |  |
| `di01-visible-tests-kept` | Respect du rôle et du protocole | dev-frontend's tests kept |  |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `frontend/src/**`, `frontend/tests/**/*.ts`, `frontend/tests/**/*.tsx`, `backend/src/**`, `backend/tests/ShopLite.Api.Tests/**`, `.decisions/**`.
- Interdits (bloquants) : `contracts/openapi.yaml`, `tests/e2e/**`, `.pipeline/conventions.md`, `.claude/**`.
- Interdit de rôle : dev-integrator ne modifie pas `contracts/openapi.yaml` (le contrat gagne : on corrige le code) ; corrections au point de jonction uniquement ; ne supprime ni n'affaiblit aucun test.
- Diff maximal acceptable : 250 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 50 tours, 3.0 $, 1200 s (seuils initiaux à recalibrer après les premières campagnes).
