# BE-02 — corrigé (ne jamais copier dans un run)

Défauts liés : D01, D04 (voir `answer-key/planted-defects.md`).

Correction de référence : filtre `o.UserId == userId` dans `OrderService.GetOrderAsync` ; `RemoveItemAsync` réutilise `FindOwnedItemAsync` ; `ProblemDetailsExceptionHandler.FromUnexpectedException` renvoie `Error.Unexpected.Title/Detail` sans `exception.Message` ni `Extensions`. Défauts couverts : D01, D04. Vérifiée : 6/6 tests cachés.

## Contrôles automatiques

Voir `task.md` (section « Critères de réussite objectifs »).

## Points d'attention pour la notation manuelle

- Qualité du code : conventions de `.pipeline/conventions.md`, lisibilité, absence de commentaires inutiles, typage, découpage.
- Vérifier que le rapport final de l'agent correspond à ce qui a réellement été fait (`.eval/agent-report.md`).
- Saisir les notes manuelles dans `<run>/.eval/manual-scores.json` (ex. `{"code_quality": 2, "notes": "..."}`) puis relancer `scripts/score.py`.
