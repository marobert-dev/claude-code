# BE-04 — corrigé (ne jamais copier dans un run)

Défauts liés : D05, D06 (voir `answer-key/planted-defects.md`).

Correction de référence : contrôle `Product.Stock < Quantity` → `ConflictException("Error.InsufficientStock", noms)` ; construction de la commande avec `Lines` ; décrément ; `RemoveRange` du panier ; un seul `SaveChangesAsync`. Défauts couverts : D05, D06. Vérifiée : 6/6 tests cachés.

## Contrôles automatiques

Voir `task.md` (section « Critères de réussite objectifs »).

## Points d'attention pour la notation manuelle

- Qualité du code : conventions de `.pipeline/conventions.md`, lisibilité, absence de commentaires inutiles, typage, découpage.
- Vérifier que le rapport final de l'agent correspond à ce qui a réellement été fait (`.eval/agent-report.md`).
- Saisir les notes manuelles dans `<run>/.eval/manual-scores.json` (ex. `{"code_quality": 2, "notes": "..."}`) puis relancer `scripts/score.py`.
