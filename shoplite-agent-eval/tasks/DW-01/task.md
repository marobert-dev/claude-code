# DW-01 — Documentation d'une story validée (dev EN + manuel FR/EN)

| Champ | Valeur |
|---|---|
| ID | DW-01 |
| Agent visé | `doc-writer` |
| Modèle attendu (frontmatter) | `sonnet` |
| Mode d'invocation | direct: claude -p --agent doc-writer |
| Critères applicables | Gate et tests, Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Accessibilité et i18n FR/EN, Qualité du code, Efficacité, Stabilité |
| Critères notés à la main | Qualité du code |

## Demande exacte (`prompt.txt`)

```text
story-validator confirmed every acceptance criterion of the story `.user-stories/05-order-history.md` (no regression). Document it.

Read its description, Acceptance Criteria, Copy (FR/EN) and the condensed implementation summaries. Return a one-line summary: which documentation sets you updated and which you skipped.
```

## Fixtures et état de départ

- Étape 1 — `fixtures/workspace/` copié dans le run puis commité (« Update shared project files ») :
  - `.user-stories/05-order-history.md`
- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Story 05 « historique des commandes » validée (toutes cases cochées) ; aucune documentation existante.

## Résultat attendu

- `docs/dev/README.md` (+ pages) en anglais, liant `contracts/openapi.yaml`.
- `docs/user-manual/en/` et `fr/` : sites HTML autonomes (sans CDN), navigation miroir de l'app, recherche côté client, lien EN↔FR sur chaque page.
- Langage « grand-mère » : aucun jargon (component, endpoint, API, database… / composant, base de données…), instructions pas à pas, textes affichés cités exactement (Copy FR/EN).
- Rien en dehors de `docs/` ; story inchangée.

Artefacts de protocole attendus : `docs/dev/`, `docs/user-manual/{en,fr}/`, résumé d'une ligne.

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés : aucun ; les contrôles sont dans `check.sh`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/DW-01-run<n>` (exécute `tasks/DW-01/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `dw01-exists` | Correction fonctionnelle | docs/dev/README.md and docs/user-manual/{en,fr}/index.html exist |  |
| `dw01-dev-en` | Correction fonctionnelle | Developer docs in English and linking contracts/openapi.yaml |  |
| `dw01-cross-links` | Accessibilité et i18n FR/EN | Every manual page links to its other-language counterpart |  |
| `dw01-search` | Correction fonctionnelle | Each language site has a working search box (input + script) |  |
| `dw01-no-cdn` | Qualité du code | No external/CDN dependency in the manual |  |
| `dw01-no-jargon` | Accessibilité et i18n FR/EN | No technical jargon in the beginner manual (EN and FR) |  |
| `dw01-copy` | Accessibilité et i18n FR/EN | Exact on-screen copy quoted in each language |  |
| `dw01-french` | Accessibilité et i18n FR/EN | French manual is written in French |  |
| `dw01-story-untouched` | Respect du rôle et du protocole | Story file not modified by doc-writer |  |
| `dw01-summary` | Respect du rôle et du protocole | One-line summary names the documentation sets |  |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `docs/**`, `.decisions/**`.
- Interdits (bloquants) : `backend/**`, `frontend/**`, `contracts/openapi.yaml`, `tests/**`, `playwright.config.ts`, `package.json`, `.pipeline/conventions.md`, `.claude/**`.
- Interdit de rôle : doc-writer n'écrit que sous `docs/` (bloquant) ; ne modifie ni le code ni la story.
- Diff maximal acceptable : 3000 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 50 tours, 3.0 $, 1500 s (seuils initiaux à recalibrer après les premières campagnes).
