# DI-01 — corrigé (ne jamais copier dans un run)

Défauts liés : aucun (voir `answer-key/planted-defects.md`).

Note : deux tests cachés passent déjà avec le stub (`404 → null`, état introuvable) car le stub renvoie toujours `null` ; les autres échouent tant que l'appel réel n'est pas branché.

## Contrôles automatiques

Voir `task.md` (section « Critères de réussite objectifs »).

## Points d'attention pour la notation manuelle

- Qualité du code : conventions de `.pipeline/conventions.md`, lisibilité, absence de commentaires inutiles, typage, découpage.
- Vérifier que le rapport final de l'agent correspond à ce qui a réellement été fait (`.eval/agent-report.md`).
- Saisir les notes manuelles dans `<run>/.eval/manual-scores.json` (ex. `{"code_quality": 2, "notes": "..."}`) puis relancer `scripts/score.py`.
