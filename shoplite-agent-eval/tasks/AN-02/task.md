# AN-02 — Plan de checkout atomique : TODO aux bons emplacements, changement cassant identifié

| Champ | Valeur |
|---|---|
| ID | AN-02 |
| Agent visé | `analyst` |
| Modèle attendu (frontmatter) | `opus` |
| Mode d'invocation | direct: claude -p --agent analyst (prompt = story path, as product-manager passes it) |
| Critères applicables | Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Contrat API, Efficacité, Stabilité |
| Critères notés à la main | aucun |

## Demande exacte (`prompt.txt`)

```text
.user-stories/07-reliable-checkout.md
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Update shared project files ») :
  - `.user-stories/07-reliable-checkout.md`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story brute « checkout fiable » (format product-owner, sans plan). Le code actuel enregistre la commande en plusieurs `SaveChangesAsync` et ignore le stock (défauts D05, D06).

## Résultat attendu

- Commentaires `TODO:` aux bons emplacements : dans/au-dessus de `OrderService.CheckoutAsync`, côté web là où l'erreur de checkout est affichée (`CartPage.tsx` / `api/orders.ts`), et là où le nouveau message localisé est ajouté (ressources / `Errors/` / `OrdersController`).
- Contrat : `checkout` documente le refus (409 problem+json, ou 422 justifié).
- Le plan identifie explicitement le **changement cassant** (nouveau statut d'erreur sur `checkout` pour les clients) et sa mitigation.
- Le plan rend le checkout atomique (une seule unité de travail EF Core), contrôle et décrémente le stock, signale que le fournisseur InMemory ne supporte pas les transactions, couvre web + backend.
- Aucune implémentation (commentaires uniquement).

Artefacts de protocole attendus : `## Technical Plan`, `contracts/openapi.yaml`, `TODO:`, `.decisions/analyst.decisions.md`, ligne `Memory:`.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés : aucun ; les contrôles sont dans `check.sh`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/AN-02-run<n>` (exécute `tasks/AN-02/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `an02-todo-checkout` | Correction fonctionnelle | TODO: inside/above OrderService.CheckoutAsync (stock check + single save) |  |
| `an02-todo-web` | Correction fonctionnelle | TODO: on the web side where checkout errors are shown (409 handling) |  |
| `an02-todo-resources` | Correction fonctionnelle | TODO: where the new localized message goes (resources or Errors/) |  |
| `an02-contract` | Contrat API | checkout documents the new refusal (409/422 problem response) |  |
| `an02-plan-breaking` | Contrat API | Plan identifies the breaking change for clients (new refusal status on checkout) |  |
| `an02-plan-atomic` | Correction fonctionnelle | Plan makes the checkout atomic (single unit of work / transaction) |  |
| `an02-plan-stock` | Correction fonctionnelle | Plan checks and decrements stock |  |
| `an02-plan-inmemory` | Correction fonctionnelle | Plan notes the InMemory provider limitation on transactions |  |
| `an02-plan-scope-both` | Respect du rôle et du protocole | Plan states both scopes (backend + web) |  |
| `an02-no-code` | Respect du rôle et du protocole | Only TODO: comments in source files (no implementation by the analyst) | oui |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `contracts/openapi.yaml`, `backend/src/**`, `frontend/src/**`, `.decisions/**`.
- Interdits (bloquants) : `backend/tests/**`, `frontend/tests/**`, `tests/e2e/**`, `.pipeline/conventions.md`, `.claude/**`, `frontend/package.json`, `frontend/package-lock.json`.
- Interdit de rôle : analyst n'écrit que la section `## Technical Plan` de la story, `contracts/openapi.yaml` et des commentaires `TODO: <≤ 5 mots>` dans le code — aucune implémentation (bloquant).
- Diff maximal acceptable : 200 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 50 tours, 5.0 $, 1500 s (seuils initiaux à recalibrer après les premières campagnes).
