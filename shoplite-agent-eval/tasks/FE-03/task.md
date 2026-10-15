# FE-03 — Modale de confirmation accessible (focus piégé, retour du focus, Escape, aria-modal)

| Champ | Valeur |
|---|---|
| ID | FE-03 |
| Agent visé | `dev-frontend` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent dev-frontend |
| Critères applicables | Gate et tests, Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Contrat API, Qualité du code, Qualité des tests produits, Accessibilité et i18n FR/EN, Efficacité, Stabilité |
| Critères notés à la main | Qualité du code |

## Demande exacte (`prompt.txt`)

```text
Implement the web frontend scope of the story `.user-stories/12-accessible-checkout-dialog.md`.

Read its description, Acceptance Criteria, Visual Definition, Copy (FR/EN) and Technical Plan. Project conventions are in `.pipeline/conventions.md`; the API contract is `contracts/openapi.yaml`.

When you are done, report back: files created/modified, platform(s) touched, any dependency added, any deviation from the plan, open TODOs and convention gaps.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Plan story 12: checkout confirmation is an accessible dialog ») :
  - `.user-stories/12-accessible-checkout-dialog.md`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story analysée (modale de confirmation accessible).

## Résultat attendu

- `role=dialog`, `aria-modal="true"`, nom accessible = titre (EN/FR).
- Focus déplacé dans la modale, Tab/Shift+Tab piégés, Escape ferme sans commander, focus rendu au bouton « Checkout ».
- jest-axe sans violation, API du composant conservée, pas de dépendance.

Artefacts de protocole attendus : rapport, ligne `Memory:`.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés (copiés après l'agent) : `hidden-tests/frontend/FE03_accessibleDialog.test.tsx`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/FE-03-run<n>` (exécute `tasks/FE-03/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `fe03-role` | Accessibilité et i18n FR/EN | role=dialog, accessible name, aria-modal |  |
| `fe03-focus-in` | Accessibilité et i18n FR/EN | Focus moves into the dialog |  |
| `fe03-trap` | Accessibilité et i18n FR/EN | Tab/Shift+Tab trapped |  |
| `fe03-escape` | Correction fonctionnelle | Escape closes without ordering, focus restored |  |
| `fe03-cancel` | Correction fonctionnelle | Cancel restores focus |  |
| `fe03-axe` | Accessibilité et i18n FR/EN | jest-axe clean with dialog open |  |
| `fe03-fr` | Accessibilité et i18n FR/EN | French dialog name |  |
| `fe03-contract-untouched` | Contrat API | contracts/openapi.yaml unchanged |  |
| `fe03-no-new-dependency` | Qualité du code | No dependency added (plan) |  |
| `fe03-props-kept` | Qualité du code | Component API kept (CartPage untouched or only trivially changed) |  |
| `fe03-tests-added` | Qualité des tests produits | Keyboard/a11y tests added |  |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `frontend/src/**`, `frontend/tests/**/*.ts`, `frontend/tests/**/*.tsx`, `.decisions/**`.
- Interdits (bloquants) : `contracts/openapi.yaml`, `backend/**`, `tests/e2e/**`, `.pipeline/conventions.md`, `.claude/**`, `frontend/package.json`, `frontend/package-lock.json`.
- Interdit de rôle : dev-frontend ne modifie jamais `contracts/openapi.yaml` ; ne touche pas au back ni aux tests e2e ; toute **nouvelle** opération API est **stubbée** (retourne `null`/liste vide, aucun appel réseau) ; ne supprime ni n'affaiblit aucun test.
- Diff maximal acceptable : 300 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 45 tours, 2.5 $, 1000 s (seuils initiaux à recalibrer après les premières campagnes).
