# FE-01 — Correction du total du panier (arrondi)

| Champ | Valeur |
|---|---|
| ID | FE-01 |
| Agent visé | `dev-frontend` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent dev-frontend |
| Critères applicables | Gate et tests, Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Contrat API, Qualité du code, Qualité des tests produits, Accessibilité et i18n FR/EN, Efficacité, Stabilité |
| Critères notés à la main | Qualité du code |

## Demande exacte (`prompt.txt`)

```text
Implement the web frontend scope of the story `.user-stories/10-cart-total-to-the-cent.md`.

Read its description, Acceptance Criteria, Visual Definition and Technical Plan, plus the operation it references in `contracts/openapi.yaml` (`getCart`). Project conventions are in `.pipeline/conventions.md`.

When you are done, report back: files created/modified, platform(s) touched, any dependency added, any deviation from the plan, open TODOs and convention gaps.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Plan story 10: cart total is exact to the cent ») :
  - `.user-stories/10-cart-total-to-the-cent.md`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story analysée (total du panier exact au centime). Front uniquement.

## Résultat attendu

- Total exact pour 4,35 + 8,20, 1,15, 3 × 19,99, etc. ; format FR `12,55 €`.
- Message de confirmation identique au total.
- Calcul en centimes arrondis, fonction pure testée.

Artefacts de protocole attendus : rapport, ligne `Memory:`.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés (copiés après l'agent) : `hidden-tests/frontend/FE01_cartTotal.test.tsx`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/FE-01-run<n>` (exécute `tasks/FE-01/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `fe01-totals` | Correction fonctionnelle | Cart total exact to the cent (5 cases) |  |
| `fe01-fr` | Accessibilité et i18n FR/EN | French total uses the French format |  |
| `fe01-confirm` | Correction fonctionnelle | Confirmation message shows the same total |  |
| `fe01-contract-untouched` | Contrat API | contracts/openapi.yaml unchanged |  |
| `fe01-no-floor` | Qualité du code | No truncation (Math.floor/trunc) left in the total computation |  |
| `fe01-tests-added` | Qualité des tests produits | Unit tests added for the total |  |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `frontend/src/**`, `frontend/tests/*.test.ts`, `frontend/tests/*.test.tsx`, `frontend/tests/**/*.ts`, `frontend/tests/**/*.tsx`, `.decisions/**`.
- Interdits (bloquants) : `contracts/openapi.yaml`, `backend/**`, `tests/e2e/**`, `.pipeline/conventions.md`, `.claude/**`.
- Interdit de rôle : dev-frontend ne modifie jamais `contracts/openapi.yaml` ; ne touche pas au back ni aux tests e2e ; toute **nouvelle** opération API est **stubbée** (retourne `null`/liste vide, aucun appel réseau) ; ne supprime ni n'affaiblit aucun test.
- Diff maximal acceptable : 200 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 40 tours, 2.0 $, 900 s (seuils initiaux à recalibrer après les premières campagnes).
