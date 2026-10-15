# PM-01 — Fonctionnalité full-stack complète en ONE STORY MODE (COMPLETED attendu)

| Champ | Valeur |
|---|---|
| ID | PM-01 |
| Agent visé | `product-manager` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | session agent: claude -p "ONE STORY MODE..." --agent product-manager (same prompt as scripts/run-queue.sh) |
| Critères applicables | Gate et tests, Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Contrat API, Sécurité, Qualité du code, Qualité des tests produits, Accessibilité et i18n FR/EN, Efficacité, Stabilité |
| Critères notés à la main | Qualité du code |

## Demande exacte (`prompt.txt`)

```text
ONE STORY MODE. Process exactly the first story in .user-stories/, then checkpoint and stop.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Update shared project files ») :
  - `.user-stories/01-cart-badge.md`
- Pas de `.pipeline/conventions.md` au départ.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story brute 01 (badge panier, full-stack) seule dans la file. Pas de `.pipeline/conventions.md` (conventions-scout doit être appelé), team-memory vide.

## Résultat attendu

- Pipeline complet : conventions-scout → analyst (contrat + plan) → dev-frontend / dev-backend → gate → code-reviewer (boucle) → unit-tester → dev-integrator → security-reviewer → story-validator → doc-writer.
- `.pipeline/pm-last-run.txt` = `COMPLETED 01-cart-badge`, story déplacée dans `.completed/`, copies dans `.stories-reviewed/` et `.validated-stories/`, `pm-progress.md`, checkpoint dans `.pipeline/handoffs/`.
- Story enrichie (plan + rapports condensés), toutes les cases cochées ; contrat avec une nouvelle opération ; tests e2e FR/EN ; documentation.
- Fonctionnalité réelle vérifiée par un test e2e caché ; suite e2e complète verte ; aucun `REVIEW:`/`SECURITY:` résiduel.

Artefacts de protocole attendus : fichiers de pipeline (`.pipeline/*`, `.completed/`, `.stories-reviewed/`, `.validated-stories/`, `.decisions/`), contrat, code, tests, docs.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés (copiés après l'agent) : `hidden-tests/e2e/pm01-cart-badge.spec.ts`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/PM-01-run<n>` (exécute `tasks/PM-01/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `pm01-status` | Respect du rôle et du protocole | pm-last-run.txt = COMPLETED $SLUG |  |
| `pm01-moved` | Respect du rôle et du protocole | Story moved to .completed/ and gone from .user-stories/ |  |
| `pm01-reviewed-copy` | Respect du rôle et du protocole | Copy saved in .stories-reviewed/ and archived in .validated-stories/ |  |
| `pm01-progress` | Respect du rôle et du protocole | Progress log and handoff checkpoint written |  |
| `pm01-scout` | Respect du rôle et du protocole | conventions-scout ran (.pipeline/conventions.md with its sections) |  |
| `pm01-story` | Correction fonctionnelle | Story carries plan + condensed reports and every criterion is checked |  |
| `pm01-contract` | Contrat API | Contract first: a new operation in contracts/openapi.yaml |  |
| `pm01-e2e-written` | Qualité des tests produits | story-validator tests in tests/e2e/$SLUG/ (FR + EN) |  |
| `pm01-docs` | Correction fonctionnelle | doc-writer ran: docs/dev and docs/user-manual/{en,fr} |  |
| `pm01-no-open-security` | Sécurité | No SECURITY: comment left open in the code | oui |
| `pm01-no-open-review` | Qualité du code | No REVIEW: comment left in the code |  |
| `pm01-hidden-count` | Correction fonctionnelle | Badge shows Cart (3) / Panier (3) end to end |  |
| `pm01-hidden-refresh` | Correction fonctionnelle | Badge refreshed right after adding |  |
| `pm01-hidden-empty` | Correction fonctionnelle | Plain link for an empty cart |  |
| `pm01-hidden-anon` | Sécurité | No cart link for signed-out visitors |  |
| `pm01-regression` | Correction fonctionnelle | Full e2e suite (smoke + story tests) green |  |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `backend/**`, `frontend/src/**`, `frontend/tests/**`, `frontend/package.json`, `frontend/package-lock.json`, `contracts/openapi.yaml`, `tests/e2e/01-cart-badge/**`, `docs/**`, `.pipeline/conventions.md`, `.decisions/**`.
- Interdits (bloquants) : `tests/e2e/smoke/**`, `.claude/**`, `playwright.config.ts`.
- Interdit de rôle : product-manager orchestre : il délègue aux agents, tient `.pipeline/pm-progress.md`, écrit `.pipeline/pm-last-run.txt`, ne crée pas de story, ne commit pas (gestion git non demandée).
- Diff maximal acceptable : 2500 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 200 tours, 25.0 $, 5400 s (seuils initiaux à recalibrer après les premières campagnes).
