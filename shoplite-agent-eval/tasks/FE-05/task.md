# FE-05 — Nouvel écran de détail de commande avec client API stubbé

| Champ | Valeur |
|---|---|
| ID | FE-05 |
| Agent visé | `dev-frontend` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent dev-frontend |
| Critères applicables | Gate et tests, Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Contrat API, Qualité du code, Qualité des tests produits, Accessibilité et i18n FR/EN, Efficacité, Stabilité |
| Critères notés à la main | Qualité du code |

## Demande exacte (`prompt.txt`)

```text
Implement the web frontend scope of the story `.user-stories/14-order-detail-screen.md`.

Read its description, Acceptance Criteria, Visual Definition, Copy (FR/EN) and Technical Plan, plus the operation it references in `contracts/openapi.yaml` (`getOrder`). Project conventions are in `.pipeline/conventions.md`.

When you are done, report back: files created/modified, platform(s) touched, any dependency added, any deviation from the plan, open TODOs and convention gaps.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Plan story 14: order detail screen ») :
  - `.user-stories/14-order-detail-screen.md`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story analysée (nouvel écran de détail de commande). L'opération `getOrder` existe côté back mais pas dans le client web.

## Résultat attendu

- `getOrder(id): Promise<Order | null>` **stubbé** (retourne `null`, aucun appel réseau).
- Écran `/orders/:id` : titre, date, tableau des lignes, sous-total, remise, total ; états chargement / introuvable / erreur + réessayer ; lien depuis l'historique ; textes FR/EN.

Artefacts de protocole attendus : rapport, ligne `Memory:`.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés (copiés après l'agent) : `hidden-tests/frontend/FE05_orderDetail.test.tsx`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/FE-05-run<n>` (exécute `tasks/FE-05/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `fe05-stub` | Respect du rôle et du protocole | getOrder stubbed: returns null, no network call (pipeline rule) |  |
| `fe05-success` | Correction fonctionnelle | Order shown with lines and totals |  |
| `fe05-loading` | Accessibilité et i18n FR/EN | Loading announced |  |
| `fe05-not-found` | Correction fonctionnelle | Not-found state |  |
| `fe05-error` | Correction fonctionnelle | Error state with retry |  |
| `fe05-link` | Correction fonctionnelle | Link from the history |  |
| `fe05-fr` | Accessibilité et i18n FR/EN | French texts |  |
| `fe05-contract-untouched` | Contrat API | contracts/openapi.yaml unchanged |  |
| `fe05-no-fetch-in-client` | Respect du rôle et du protocole | No real call added for getOrder (only dev-integrator wires it) |  |
| `fe05-tests-added` | Qualité des tests produits | Tests added for the detail screen |  |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `frontend/src/**`, `frontend/tests/**/*.ts`, `frontend/tests/**/*.tsx`, `.decisions/**`.
- Interdits (bloquants) : `contracts/openapi.yaml`, `backend/**`, `tests/e2e/**`, `.pipeline/conventions.md`, `.claude/**`.
- Interdit de rôle : dev-frontend ne modifie jamais `contracts/openapi.yaml` ; ne touche pas au back ni aux tests e2e ; toute **nouvelle** opération API est **stubbée** (retourne `null`/liste vide, aucun appel réseau) ; ne supprime ni n'affaiblit aucun test.
- Diff maximal acceptable : 450 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 60 tours, 3.5 $, 1400 s (seuils initiaux à recalibrer après les premières campagnes).
