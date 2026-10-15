# SV-01 — Story dont un critère échoue réellement

| Champ | Valeur |
|---|---|
| ID | SV-01 |
| Agent visé | `story-validator` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent story-validator |
| Critères applicables | Gate et tests, Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Qualité des tests produits, Accessibilité et i18n FR/EN, Efficacité, Stabilité |
| Critères notés à la main | aucun |

## Demande exacte (`prompt.txt`)

```text
Validate the story `.user-stories/19-cart-page.md`. dev-integrator marked it integrated and security-reviewer is clean; the integration report is in its `## Integration Notes` section.

Read its Acceptance Criteria, Copy (FR/EN) and Integration Notes. Return the story file path with your one-line summary.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Update shared project files ») :
  - `.user-stories/19-cart-page.md`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story 19 « page panier » intégrée, revue sécurité propre ; à valider de bout en bout. L'application réelle tourne via le `webServer` Playwright.

## Résultat attendu

- Un test e2e Playwright par critère, en FR **et** EN, sous `tests/e2e/19-cart-page/`, titres `[19-cart-page] …`, sans `waitForTimeout`.
- Cases cochées si et seulement si le test passe dans toutes les langues ; note précise sous chaque case non cochée (ce qui échoue, langue, fichier).
- Aucun test affaibli : les tests doivent échouer sur le défaut réel et passer une fois le défaut corrigé (vérifié par `check.sh` avec une correction de référence).
- Story non archivée dans `.validated-stories/` en cas d'échec ; suite complète exécutée (régression).

Artefacts de protocole attendus : `tests/e2e/19-cart-page/`, cases + notes dans la story, rapport d'une ligne, ligne `Memory:`.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés : aucun test copié ; `check.sh` compare le résultat au corrigé (`expected.md`, fichiers de spécification de la tâche).
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/SV-01-run<n>` (exécute `tasks/SV-01/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

- Correction fonctionnelle : 4 contrôle(s) — détail dans `check.sh` / `expected.md`.
- Respect du rôle et du protocole : 6 contrôle(s) dont bloquant(s) — détail dans `check.sh` / `expected.md`.
- Accessibilité et i18n FR/EN : 1 contrôle(s) — détail dans `check.sh` / `expected.md`.
- Qualité des tests produits : 3 contrôle(s) dont bloquant(s) — détail dans `check.sh` / `expected.md`.

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `tests/e2e/19-cart-page/**`, `.user-stories/19-cart-page.md`, `.validated-stories/**`, `.decisions/**`, `test-results/**`, `playwright-report/**`.
- Interdits (bloquants) : `backend/**`, `frontend/**`, `contracts/openapi.yaml`, `playwright.config.ts`, `package.json`, `tests/e2e/smoke/**`, `.pipeline/conventions.md`, `.claude/**`.
- Interdit de rôle : story-validator n'écrit que sous `tests/e2e/<story-id>/`, dans le fichier de story (cases + notes) et dans `.validated-stories/` ; ne touche jamais au code applicatif ni aux tests d'autres stories (bloquant).
- Diff maximal acceptable : 400 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 60 tours, 3.0 $, 1800 s (seuils initiaux à recalibrer après les premières campagnes).
