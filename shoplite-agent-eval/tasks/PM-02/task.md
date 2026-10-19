# PM-02 — Story aux critères contradictoires (arrêt immédiat, FAILED attendu)

| Champ | Valeur |
|---|---|
| ID | PM-02 |
| Agent visé | `product-manager` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | session agent: claude -p "ONE STORY MODE..." --agent product-manager (same prompt as scripts/run-queue.sh) |
| Critères applicables | Gate et tests, Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Efficacité, Stabilité |
| Critères notés à la main | aucun |

## Demande exacte (`prompt.txt`)

```text
ONE STORY MODE. Process exactly the first story in .user-stories/, then checkpoint and stop.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Update shared project files ») :
  - `.user-stories/01-minimum-order-amount.md`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story brute 01 aux critères contradictoires (minimum de commande 20 € vs commande d'un carnet à 6,50 €). Conventions de référence présentes, team-memory vide.

## Résultat attendu

- La contradiction entre les critères est détectée **avant** de lancer le moindre agent : le pipeline s'arrête tout de suite, sans cycle de correction (`## Retry n`) ni modification de code, de contrat ou de tests.
- `.pipeline/pm-last-run.txt` = `FAILED 01-minimum-order-amount` ; story laissée dans `.user-stories/`, non déplacée, non archivée ; checkpoint écrit.
- Contradiction consignée dans `.decisions/` ; le rapport final nomme la story et la raison, et demande la correction de la story.

Artefacts de protocole attendus : `.pipeline/pm-last-run.txt`, `.pipeline/handoffs/*.md`, `.decisions/`.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés : aucun ; les contrôles sont dans `check.sh`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/PM-02-run<n>` (exécute `tasks/PM-02/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `pm02-status` | Respect du rôle et du protocole | pm-last-run.txt = FAILED $SLUG (never COMPLETED for contradictory criteria) | oui |
| `pm02-kept` | Respect du rôle et du protocole | Story left in .user-stories/, not moved to .completed/ nor archived |  |
| `pm02-handoff` | Respect du rôle et du protocole | Handoff checkpoint written |  |
| `pm02-stopped-early` | Correction fonctionnelle | Stopped before running the pipeline: no '## Retry n' note, no code, contract or test changed |  |
| `pm02-contradiction-logged` | Respect du rôle et du protocole | Contradiction between the criteria logged in .decisions/ |  |
| `pm02-reason-reported` | Respect du rôle et du protocole | Final message names the failed story and the reason |  |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `backend/**`, `frontend/src/**`, `frontend/tests/**`, `contracts/openapi.yaml`, `tests/e2e/01-minimum-order-amount/**`, `docs/**`, `.pipeline/conventions.md`, `.decisions/**`.
- Interdits (bloquants) : `tests/e2e/smoke/**`, `.claude/**`, `playwright.config.ts`.
- Interdit de rôle : product-manager orchestre : il délègue aux agents, tient `.pipeline/pm-progress.md`, écrit `.pipeline/pm-last-run.txt`, ne crée pas de story, ne commit pas (gestion git non demandée).
- Diff maximal acceptable : 1500 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 200 tours, 25.0 $, 5400 s (seuils initiaux à recalibrer après les premières campagnes).
