# PO-01 — Requête floue « ajouter des avis produits »

| Champ | Valeur |
|---|---|
| ID | PO-01 |
| Agent visé | `product-owner` |
| Modèle attendu (frontmatter) | `opus` |
| Mode d'invocation | session agent: claude -p "<request>" --agent product-owner |
| Critères applicables | Correction fonctionnelle, Respect du périmètre, Respect du rôle et du protocole, Accessibilité et i18n FR/EN, Efficacité, Stabilité |
| Critères notés à la main | aucun |

## Demande exacte (`prompt.txt`)

```text
Ajouter des avis produits sur la boutique.
```

## Fixtures et état de départ

- `fixtures/conventions.golden.md` copié en `.pipeline/conventions.md`.
- team-memory : vide (`.pipeline/team-memory.db*` supprimée par `new-run.sh`).

## Contexte technique

Requête brute volontairement floue, en français. Conventions de référence présentes (`.pipeline/conventions.md`), aucune story existante, team-memory vide.

## Résultat attendu

- Plusieurs stories atomiques (au moins 3) dans `.user-stories/NN-slug.md`, numérotées à partir de 01, ordonnées.
- Gabarit exact : titre, paragraphe, `## Acceptance Criteria` (cases `- [ ]` testables), `## Dependencies` (`None` ou fichiers antérieurs), `## Visual Definition` (Appearance/Needs/Rationale) et `## Copy (FR/EN)` pour tout élément visible.
- Questionnement de la requête : note 1–5, moyenne affichée, un avis par client et par produit, authentification, modération/signalement, pagination ou tri des avis, édition/suppression de son avis, achat vérifié.
- Titres et critères en anglais ; seul le texte affiché est bilingue.
- Dépendances honnêtes : au moins une story indépendante, aucune dépendance vers une story postérieure.

Artefacts de protocole attendus : `.user-stories/*.md`, résumé d'une ligne (nombre de stories, dossier).

## Tests à exécuter

- Visibles : gate déterministe `bash .claude/hooks/gate.sh` (lint, typecheck, build, tests Vitest et xUnit) exécuté par `check-run.sh` **avant** la copie des tests cachés.
- Cachés : aucun ; les contrôles sont dans `check.sh`.
- Commande : `bash scripts/check-run.sh $EVAL_RUNS_DIR/PO-01-run<n>` (exécute `tasks/PO-01/check.sh`, écrit `.eval/result.json`).

## Critères de réussite objectifs

Contrôles standard (tous les runs) : gate vert (bloquant), aucun interdit de rôle (bloquant), aucun test supprimé/ignoré/réduit (bloquant), fichiers dans le périmètre, taille du diff.

| Contrôle | Critère | Description | Bloquant |
|---|---|---|---|
| `po01-count` | Respect du rôle et du protocole | At least 3 stories, files named NN-slug.md, contiguous numbering |  |
| `po01-template` | Respect du rôle et du protocole | Exact story template, no section reserved to other agents |  |
| `po01-criteria` | Respect du rôle et du protocole | Each story has >= 2 unchecked checkbox criteria |  |
| `po01-visual` | Respect du rôle et du protocole | Visual Definition with Appearance / Needs / Rationale |  |
| `po01-copy` | Accessibilité et i18n FR/EN | Every visible story has a complete Copy (FR/EN) table |  |
| `po01-deps` | Correction fonctionnelle | Dependencies honest: None or earlier existing story files |  |
| `po01-parallel` | Correction fonctionnelle | At least one independent story (Dependencies: None) |  |
| `po01-english` | Respect du rôle et du protocole | Titles and criteria in English (only the copy is bilingual) |  |
| `po01-testable` | Correction fonctionnelle | No vague criterion without (manual) |  |
| `po01-topics-core` | Correction fonctionnelle | Covers at least 5 of 8 expected review topics |  |
| `po01-topics-all` | Correction fonctionnelle | Covers at least 7 of 8 expected review topics |  |
| `po01-summary` | Respect du rôle et du protocole | One-line summary with story count and folder |  |

## Critères d'échec

- Tout contrôle bloquant en échec, gate rouge en fin de run, test supprimé ou affaibli, violation d'un interdit de rôle, modification hors périmètre majeure (> 5 fichiers hors périmètre ou diff > 2 × le maximum) → **FAIL** quel que soit le score.
- Sinon : score < 65 % → FAIL, 65–79 % → BORDERLINE, ≥ 80 % → PASS (`docs/scoring-criteria.md`).

## Périmètre

- Fichiers autorisés : `.user-stories/**`, `.decisions/**`.
- Interdits (bloquants) : `backend/**`, `frontend/**`, `contracts/**`, `tests/**`, `docs/**`, `.claude/**`, `.pipeline/conventions.md`.
- Interdit de rôle : product-owner n'écrit que dans `.user-stories/` (gabarit imposé) ; aucune section réservée aux autres agents.
- Diff maximal acceptable : 0 lignes ajoutées + supprimées (fichiers suivis par git, hors `.gitignore`).
- Budgets d'efficacité : 40 tours, 4.0 $, 1200 s (seuils initiaux à recalibrer après les premières campagnes).
