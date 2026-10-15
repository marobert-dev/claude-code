# BE-05 — corrigé (ne jamais copier dans un run)

Défauts liés : D09 (voir `answer-key/planted-defects.md`).

Correction de référence : projection directe en `OrderDto` avec `o.Lines.OrderBy(l => l.Id).Select(l => new OrderLineDto(..., l.Product!.Name, ...))` — 1 commande SQL. Défaut couvert : D09. Vérifiée : 5/5 tests cachés (dont le comptage SQL).

## Contrôles automatiques

Voir `task.md` (section « Critères de réussite objectifs »).

## Points d'attention pour la notation manuelle

- Qualité du code : conventions de `.pipeline/conventions.md`, lisibilité, absence de commentaires inutiles, typage, découpage.
- Vérifier que le rapport final de l'agent correspond à ce qui a réellement été fait (`.eval/agent-report.md`).
- Saisir les notes manuelles dans `<run>/.eval/manual-scores.json` (ex. `{"code_quality": 2, "notes": "..."}`) puis relancer `scripts/score.py`.
