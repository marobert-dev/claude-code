# AN-01 — Contrat d'abord pour une nouvelle API (avis produits)

| Champ | Valeur |
|---|---|
| ID | AN-01 |
| Agent visé | `analyst` |
| Modèle attendu (frontmatter) | `opus` |
| Mode d'invocation | direct: claude -p --agent analyst (prompt = story path, as product-manager passes it) |
| Critères applicables | Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Contrat API, Sécurité, Efficacité, Stabilité |
| Critères notés à la main | aucun |

## Demande exacte (`prompt.txt`)

```text
.user-stories/22-product-reviews-api.md
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Update shared project files ») :
  - `.user-stories/22-product-reviews-api.md`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story brute (format product-owner, sans plan) décrivant une API d'avis produits. Contrat existant : 14 opérations dans `contracts/openapi.yaml`. Aucun code d'avis n'existe.

## Résultat attendu

- `contracts/openapi.yaml` (OpenAPI 3.1) enrichi **avant** tout code : `GET` et `POST /api/products/{id}/reviews` avec `operationId`, schémas, `rating` 1–5 requis, `comment` ≤ 1000, `page`/`pageSize` (max 50), sécurité bearer sur POST seulement, réponses 201/400/401/404 + 409 (doublon) en `application/problem+json`, 404 sur GET.
- Aucune opération existante modifiée ou retirée (changement additif).
- Section `## Technical Plan` ajoutée à la fin de la story (texte d'origine intact), courte, référençant les `operationId`, indiquant le périmètre (backend).
- Seuls des commentaires `TODO: <≤ 5 mots>` éventuels dans le code, aucune implémentation.

Artefacts de protocole attendus : `## Technical Plan` dans la story, `contracts/openapi.yaml`, commentaires `TODO:`, `.decisions/analyst.decisions.md` pour les arbitrages, ligne `Memory:`.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés : aucun ; les contrôles sont dans `check.sh`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/AN-01-run<n>` (exécute `tasks/AN-01/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `an01-parses` | Contrat API | contracts/openapi.yaml still parses |  |
| `an01-paths` | Contrat API | GET and POST /api/products/{id}/reviews in the contract |  |
| `an01-opids` | Contrat API | Both operations have an operationId |  |
| `an01-auth` | Sécurité | POST requires bearer auth, GET is public |  |
| `an01-validation` | Contrat API | Request schema: rating 1-5 (required), comment maxLength 1000 |  |
| `an01-errors` | Contrat API | POST documents 201/400/401/404 + 409 duplicate, errors as problem+json; GET documents 404 |  |
| `an01-pagination` | Contrat API | GET paginated: page + pageSize (maximum 50) |  |
| `an01-non-breaking` | Contrat API | No existing operation changed or removed | oui |
| `an01-plan-appended` | Respect du rôle et du protocole | ## Technical Plan appended at the end, original story text untouched |  |
| `an01-plan-opids` | Respect du rôle et du protocole | Plan references the new operationIds instead of re-describing payloads |  |
| `an01-plan-scope` | Respect du rôle et du protocole | Plan states its scope (backend) |  |
| `an01-no-code` | Respect du rôle et du protocole | Only TODO: comments in source files (no implementation by the analyst) | oui |
| `an01-todo-format` | Respect du rôle et du protocole | Every TODO is 'TODO: <= 5 words' |  |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `contracts/openapi.yaml`, `backend/src/**`, `frontend/src/**`, `.decisions/**`.
- Interdits (bloquants) : `backend/tests/**`, `frontend/tests/**`, `tests/e2e/**`, `.pipeline/conventions.md`, `.claude/**`, `frontend/package.json`, `frontend/package-lock.json`.
- Interdit de rôle : analyst n'écrit que la section `## Technical Plan` de la story, `contracts/openapi.yaml` et des commentaires `TODO: <≤ 5 mots>` dans le code — aucune implémentation (bloquant).
- Diff maximal acceptable : 400 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 50 tours, 5.0 $, 1500 s (seuils initiaux à recalibrer après les premières campagnes).
