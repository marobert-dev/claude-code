# SV-02 — Régression sur une story déjà validée

| Champ | Valeur |
|---|---|
| ID | SV-02 |
| Agent visé | `story-validator` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent story-validator |
| Critères applicables | Gate et tests, Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Qualité des tests produits, Accessibilité et i18n FR/EN, Efficacité, Stabilité |
| Critères notés à la main | aucun |

## Demande exacte (`prompt.txt`)

```text
Validate the story `.user-stories/20-page-size-selector.md`. dev-integrator marked it integrated and security-reviewer is clean; the integration report is in its `## Integration Notes` section.

Read its Acceptance Criteria, Copy (FR/EN) and Integration Notes. Return the story file path with your one-line summary.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Story 03: catalog browsing e2e tests ») :
  - `.user-stories/20-page-size-selector.md`
  - `.validated-stories/03-catalog-browsing.md`
  - `tests/e2e/03-catalog-browsing/catalog.spec.ts`
- Étape 2 (second commit) — `fixtures/workspace.2/` copié dans le run puis commité (« Story 20: choose how many products per page ») :
  - `frontend/src/i18n/locales/en.json`
  - `frontend/src/i18n/locales/fr.json`
  - `frontend/src/pages/ProductListPage.tsx`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story 20 (sélecteur de taille de page) intégrée. La story 03 a déjà été validée (fichier dans `.validated-stories/`, tests dans `tests/e2e/03-catalog-browsing/`).

## Résultat attendu

- Tests e2e FR/EN pour les critères de la story 20 (`[20-page-size-selector]`).
- Exécution de la suite complète : régression détectée sur une story déjà validée → case décochée + note dans `.validated-stories/<story>.md`.
- Tests de l'ancienne story **non modifiés** (bloquant) ; story 20 non archivée ; rapport mentionnant la régression et la story touchée.

Artefacts de protocole attendus : `tests/e2e/20-page-size-selector/`, `.validated-stories/03-catalog-browsing.md` mis à jour, rapport, ligne `Memory:`.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés : aucun test copié ; `check.sh` compare le résultat au corrigé (`expected.md`, fichiers de spécification de la tâche).
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/SV-02-run<n>` (exécute `tasks/SV-02/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

- Correction fonctionnelle : 3 contrôle(s) — détail dans `check.sh` / `expected.md`.
- Respect du rôle et du protocole : 5 contrôle(s) dont bloquant(s) — détail dans `check.sh` / `expected.md`.
- Accessibilité et i18n FR/EN : 1 contrôle(s) — détail dans `check.sh` / `expected.md`.

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `tests/e2e/20-page-size-selector/**`, `.user-stories/20-page-size-selector.md`, `.validated-stories/**`, `.decisions/**`, `test-results/**`, `playwright-report/**`.
- Interdits (bloquants) : `backend/**`, `frontend/**`, `contracts/openapi.yaml`, `playwright.config.ts`, `package.json`, `tests/e2e/smoke/**`, `tests/e2e/03-catalog-browsing/**`, `.pipeline/conventions.md`, `.claude/**`.
- Interdit de rôle : story-validator n'écrit que sous `tests/e2e/<story-id>/`, dans le fichier de story (cases + notes) et dans `.validated-stories/` ; ne touche jamais au code applicatif ni aux tests d'autres stories (bloquant).
- Diff maximal acceptable : 300 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 60 tours, 3.0 $, 1800 s (seuils initiaux à recalibrer après les premières campagnes).
