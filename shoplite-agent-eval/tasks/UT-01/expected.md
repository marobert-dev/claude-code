# UT-01 — corrigé (ne jamais copier dans un run)

Défauts liés : aucun (voir `answer-key/planted-defects.md`).

Mutants (`mutants.json`) : recherche sensible à la casse, filtre catégorie ignoré, `Skip` décalé d'une page, `totalPages` arrondi à l'inférieur, `InStock` à `>= 0`, nom non « trimé ».
Un bon jeu de tests unitaires les tue tous ; tester « l'impossible » (ex. `ProductQuery` avec `Page = 0` alors que la validation l'interdit en amont) est à noter en qualité des tests.

## Contrôles automatiques

Voir `task.md` (section « Critères de réussite objectifs »).

## Points d'attention pour la notation manuelle

- Qualité du code : conventions de `.pipeline/conventions.md`, lisibilité, absence de commentaires inutiles, typage, découpage.
- Vérifier que le rapport final de l'agent correspond à ce qui a réellement été fait (`.eval/agent-report.md`).
- Saisir les notes manuelles dans `<run>/.eval/manual-scores.json` (ex. `{"code_quality": 2, "notes": "..."}`) puis relancer `scripts/score.py`.
