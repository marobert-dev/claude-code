# BE-01 — corrigé (ne jamais copier dans un run)

Défauts liés : D03, D07, D08 (voir `answer-key/planted-defects.md`).

Correction de référence : `[Range(1, 99, ErrorMessage = "Validation.Range")]` sur les deux `Quantity`, suppression de `UnitPrice` dans `AddCartItemRequest` et `UnitPrice = product.Price` dans `CartService`, `[Range(1, 50, …)]` sur `ProductQuery.PageSize`. Défauts couverts : D03, D07, D08.
Vérifiée : les 15 tests cachés passent sur la correction de référence (étape 3 de la génération).

## Contrôles automatiques

Voir `task.md` (section « Critères de réussite objectifs »).

## Points d'attention pour la notation manuelle

- Qualité du code : conventions de `.pipeline/conventions.md`, lisibilité, absence de commentaires inutiles, typage, découpage.
- Vérifier que le rapport final de l'agent correspond à ce qui a réellement été fait (`.eval/agent-report.md`).
- Saisir les notes manuelles dans `<run>/.eval/manual-scores.json` (ex. `{"code_quality": 2, "notes": "..."}`) puis relancer `scripts/score.py`.
