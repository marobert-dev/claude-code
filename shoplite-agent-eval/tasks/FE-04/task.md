# FE-04 — États loading / vide / erreur de l'historique des commandes

| Champ | Valeur |
|---|---|
| ID | FE-04 |
| Agent visé | `dev-frontend` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent dev-frontend |
| Critères applicables | Gate et tests, Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Contrat API, Qualité du code, Qualité des tests produits, Accessibilité et i18n FR/EN, Efficacité, Stabilité |
| Critères notés à la main | Qualité du code |

## Demande exacte (`prompt.txt`)

```text
Implement the web frontend scope of the story `.user-stories/13-order-history-states.md`.

Read its description, Acceptance Criteria, Visual Definition, Copy (FR/EN) and Technical Plan, plus the operation it references in `contracts/openapi.yaml` (`listMyOrders`). Project conventions are in `.pipeline/conventions.md`.

When you are done, report back: files created/modified, platform(s) touched, any dependency added, any deviation from the plan, open TODOs and convention gaps.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Plan story 13: order history shows loading, empty and error states ») :
  - `.user-stories/13-order-history-states.md`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story analysée (états de l'historique des commandes). La clé `orders.loadError` doit être (re)créée.

## Résultat attendu

- Chargement annoncé (`role=status`), vide uniquement si vide, erreur (`role=alert`) + « Réessayer » sur 500 et sur panne réseau, jamais le message vide en cas d'erreur.
- Clé `orders.loadError` FR/EN, jeux de clés FR/EN identiques, réutilisation d'`ErrorState`.

Artefacts de protocole attendus : rapport, ligne `Memory:`.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés (copiés après l'agent) : `hidden-tests/frontend/FE04_orderHistoryStates.test.tsx`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/FE-04-run<n>` (exécute `tasks/FE-04/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `fe04-loading` | Accessibilité et i18n FR/EN | Loading announced (role=status) |  |
| `fe04-empty` | Correction fonctionnelle | Empty state only for an empty history |  |
| `fe04-error` | Correction fonctionnelle | Server error -> alert + retry, no empty message |  |
| `fe04-network` | Correction fonctionnelle | Network failure -> alert |  |
| `fe04-retry` | Correction fonctionnelle | Retry reloads the history |  |
| `fe04-fr` | Accessibilité et i18n FR/EN | French texts |  |
| `fe04-contract-untouched` | Contrat API | contracts/openapi.yaml unchanged |  |
| `fe04-locales` | Accessibilité et i18n FR/EN | orders.loadError present and en/fr key sets identical |  |
| `fe04-reuse-states` | Qualité du code | Reuses the shared ErrorState component |  |
| `fe04-tests-added` | Qualité des tests produits | Tests added for the history states |  |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `frontend/src/**`, `frontend/tests/**/*.ts`, `frontend/tests/**/*.tsx`, `.decisions/**`.
- Interdits (bloquants) : `contracts/openapi.yaml`, `backend/**`, `tests/e2e/**`, `.pipeline/conventions.md`, `.claude/**`.
- Interdit de rôle : dev-frontend ne modifie jamais `contracts/openapi.yaml` ; ne touche pas au back ni aux tests e2e ; toute **nouvelle** opération API est **stubbée** (retourne `null`/liste vide, aucun appel réseau) ; ne supprime ni n'affaiblit aucun test.
- Diff maximal acceptable : 200 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 35 tours, 2.0 $, 800 s (seuils initiaux à recalibrer après les premières campagnes).
