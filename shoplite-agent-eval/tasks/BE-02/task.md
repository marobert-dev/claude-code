# BE-02 — Correction IDOR et fuite d'informations dans les erreurs

| Champ | Valeur |
|---|---|
| ID | BE-02 |
| Agent visé | `dev-backend` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent dev-backend |
| Critères applicables | Gate et tests, Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Contrat API, Sécurité, Qualité du code, Qualité des tests produits, Efficacité, Stabilité |
| Critères notés à la main | Qualité du code |

## Demande exacte (`prompt.txt`)

```text
Implement the backend scope of the story `.user-stories/05-customer-data-isolation.md`.

Read its description, Acceptance Criteria, Copy (FR/EN) and Technical Plan, plus the operations it references in `contracts/openapi.yaml` (`getOrder`, `getOrderReceipt`, `removeCartItem`). Project conventions are in `.pipeline/conventions.md`.

When you are done, report back: files created/modified, the final request/response contract of every changed endpoint, any dependency added, any deviation from the plan, open TODOs and convention gaps.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Plan story 05: customers only see their own orders and cart lines ») :
  - `.user-stories/05-customer-data-isolation.md`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story analysée (isolation des données clients). Contrat inchangé. Conventions de référence, team-memory vide.

## Résultat attendu

- `GET /api/orders/{id}` et `/receipt` d'une commande d'autrui → 404 localisé (pas 403).
- `DELETE /api/cart/items/{id}` d'une ligne d'autrui ou inconnue → 404 localisé, ligne d'autrui intacte.
- Aucune réponse d'erreur ne contient message d'exception, type ou trace ; 500 générique localisé.
- Ses propres commandes restent lisibles ; tests à deux clients ajoutés.

Artefacts de protocole attendus : rapport, ligne `Memory:`, `.decisions/` si arbitrage.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés (copiés après l'agent) : `hidden-tests/backend/BE02_DataIsolationTests.cs`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/BE-02-run<n>` (exécute `tasks/BE-02/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `be02-idor-order` | Sécurité | Foreign order -> 404 with localized message (IDOR closed) |  |
| `be02-idor-receipt` | Sécurité | Foreign receipt -> 404 (IDOR closed on receipt too) |  |
| `be02-own` | Correction fonctionnelle | Own orders and receipts still readable |  |
| `be02-cart-foreign` | Sécurité | Foreign cart line delete -> 404, line kept |  |
| `be02-cart-unknown` | Correction fonctionnelle | Unknown cart line delete -> localized 404 |  |
| `be02-no-trace` | Sécurité | Unexpected errors return the generic problem, no internals |  |
| `be02-contract-untouched` | Contrat API | contracts/openapi.yaml unchanged by dev-backend |  |
| `be02-no-403` | Qualité du code | Foreign orders answered with 404, not 403 (plan: no enumeration) |  |
| `be02-tests-added` | Qualité des tests produits | Tests with a second customer (bob) added |  |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `backend/src/**`, `backend/tests/ShopLite.Api.Tests/**`, `.decisions/**`.
- Interdits (bloquants) : `contracts/openapi.yaml`, `frontend/**`, `tests/e2e/**`, `.pipeline/conventions.md`, `.claude/**`.
- Interdit de rôle : dev-backend ne modifie jamais `contracts/openapi.yaml` (l'analyst en est propriétaire) ; ne touche pas au front ni aux tests e2e ; ne supprime ni n'affaiblit aucun test.
- Diff maximal acceptable : 300 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 60 tours, 3.0 $, 1200 s (seuils initiaux à recalibrer après les premières campagnes).
