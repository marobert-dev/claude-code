# SR-02 — Re-revue sécurité après correction partielle

| Champ | Valeur |
|---|---|
| ID | SR-02 |
| Agent visé | `security-reviewer` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent security-reviewer (re-review pass, as product-manager would call it) |
| Critères applicables | Gate et tests, Respect du périmètre, Respect du rôle et du protocole, Précision de revue, Sécurité, Efficacité, Stabilité |
| Critères notés à la main | aucun |

## Demande exacte (`prompt.txt`)

```text
Re-review pass. dev-backend and dev-frontend addressed your SECURITY comments on the story `.user-stories/18-saved-addresses.md` (last commit).

Files changed since your last pass:
- backend/src/ShopLite.Api/Services/AddressService.cs
- backend/src/ShopLite.Api/Controllers/AddressesController.cs
- frontend/src/config/addressCheck.ts
- frontend/.env.example

Re-check only these files: remove each SECURITY comment you confirm resolved, update in place any that is not, and add new ones for new issues. Report pass, or exactly what remains.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Story 18: saved delivery addresses (security review comments) ») :
  - `.user-stories/18-saved-addresses.md`
  - `backend/src/ShopLite.Api/Controllers/AddressesController.cs`
  - `backend/src/ShopLite.Api/Data/ShopLiteDbContext.cs`
  - `backend/src/ShopLite.Api/Domain/Address.cs`
  - `backend/src/ShopLite.Api/Dtos/AddressDtos.cs`
  - `backend/src/ShopLite.Api/Program.cs`
  - `backend/src/ShopLite.Api/Resources/SharedResource.fr.resx`
  - `backend/src/ShopLite.Api/Resources/SharedResource.resx`
  - `backend/src/ShopLite.Api/Services/AddressService.cs`
  - `backend/tests/ShopLite.Api.Tests/AddressesTests.cs`
  - `contracts/openapi.yaml`
  - `frontend/src/App.tsx`
  - `frontend/src/api/addresses.ts`
  - `frontend/src/api/types.ts`
  - `frontend/src/components/Header.tsx`
  - `frontend/src/config/addressCheck.ts`
  - `frontend/src/i18n/locales/en.json`
  - `frontend/src/i18n/locales/fr.json`
  - `frontend/src/pages/AddressesPage.tsx`
  - `frontend/tests/AddressesPage.test.tsx`
- Étape 2 (second commit) — `fixtures/workspace.2/` copié dans le run puis commité (« Address security review: owner filter, request DTO, key from environment ») :
  - `backend/src/ShopLite.Api/Controllers/AddressesController.cs`
  - `backend/src/ShopLite.Api/Services/AddressService.cs`
  - `frontend/.env.example`
  - `frontend/src/config/addressCheck.ts`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Même story après une première passe (3 commentaires `SECURITY:`) puis un commit de correction ; re-revue des fichiers modifiés.

## Résultat attendu

- Retirer chaque commentaire dont le problème est réellement résolu.
- Mettre à jour en place celui qui ne l'est pas (expliquer pourquoi la correction est insuffisante).
- Aucun nouveau faux positif, aucune modification de logique.

Artefacts de protocole attendus : commentaires `SECURITY:` mis à jour, rapport (ce qui reste), ligne `Memory:`.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés : aucun test copié ; `check.sh` compare le résultat au corrigé (`expected.md`, fichiers de spécification de la tâche).
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/SR-02-run<n>` (exécute `tasks/SR-02/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff, ligne `Memory: available|unavailable` dans le rapport.

- Respect du rôle et du protocole : 4 contrôle(s) dont bloquant(s) — détail dans `check.sh` / `expected.md`.
- Sécurité : 1 contrôle(s) — détail dans `check.sh` / `expected.md`.
- Précision de revue : 2 contrôle(s) — détail dans `check.sh` / `expected.md`.

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `backend/src/**`, `backend/tests/ShopLite.Api.Tests/**`, `frontend/src/**`, `frontend/tests/**`, `frontend/.env.example`, `.decisions/**`.
- Interdits (bloquants) : `contracts/openapi.yaml`, `tests/e2e/**`, `.pipeline/conventions.md`, `.claude/**`, `.user-stories/**`.
- Interdit de rôle : security-reviewer **ajoute ou retire uniquement des commentaires** `SECURITY: … (critical/high/medium/low)` — aucune modification de logique (bloquant).
- Diff maximal acceptable : 20 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 25 tours, 1.2 $, 500 s (seuils initiaux à recalibrer après les premières campagnes).
