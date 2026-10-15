# CS-01 — Bootstrap des conventions comparé au fichier de référence

| Champ | Valeur |
|---|---|
| ID | CS-01 |
| Agent visé | `conventions-scout` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent conventions-scout (bootstrap, as product-manager calls it on a first run) |
| Critères applicables | Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Efficacité, Stabilité |
| Critères notés à la main | aucun |

## Demande exacte (`prompt.txt`)

```text
Bootstrap mode: `.pipeline/conventions.md` does not exist yet. Scan this workspace and write it.
```

## Fixtures et état de départ

- Pas de `.pipeline/conventions.md` au départ.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Workspace ShopLite vierge de tout artefact de pipeline : pas de `.pipeline/conventions.md`, pas de story. Stack réelle : .NET 10 / EF Core InMemory / JWT (backend), React 19 + Vite + react-i18next (frontend), Playwright à la racine, contrat `contracts/openapi.yaml`, gate `.claude/hooks/gate.sh` + `.claude/gate.local.sh`.

## Résultat attendu

- `.pipeline/conventions.md` créé avec exactement les sections imposées par `conventions-scout.md` (y compris `## Mobile (React Native)` rempli de `not present`).
- Commandes exactes et répertoires corrects pour lint, typecheck, build, unit test (npm **et** dotnet), e2e, e2e par grep et démarrage de l'app (webServer Playwright).
- Faits observés et non devinés : couches Controllers → Services → DbContext, ProblemDetails, DataAnnotations + clés de ressources, JWT + `SHOPLITE_JWT_KEY`, pas de migrations (InMemory), i18n web et API, outil d'émission du spec, absence de générateur de client.
- Fichier ≤ ~150 lignes, entrée `bootstrap` dans `## Change log`, résumé d'une ligne (mode, chemin, sections `not present` importantes).

Artefacts de protocole attendus : `.pipeline/conventions.md`, résumé d'une ligne.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés : aucun test copié ; `check.sh` compare le résultat au corrigé (`expected.md`, fichiers de spécification de la tâche).
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/CS-01-run<n>` (exécute `tasks/CS-01/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff.

- Respect du rôle et du protocole : 5 contrôle(s) — détail dans `check.sh` / `expected.md`.
- Correction fonctionnelle : 14 contrôle(s) — détail dans `check.sh` / `expected.md`.

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `.pipeline/conventions.md`, `.decisions/**`.
- Interdits (bloquants) : `backend/**`, `frontend/**`, `contracts/**`, `tests/**`, `.claude/**`, `package.json`, `playwright.config.ts`.
- Interdit de rôle : conventions-scout n'écrit que `.pipeline/conventions.md` ; n'installe rien.
- Diff maximal acceptable : 200 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 40 tours, 1.5 $, 900 s (seuils initiaux à recalibrer après les premières campagnes).
