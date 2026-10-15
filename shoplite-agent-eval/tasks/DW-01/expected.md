# DW-01 — corrigé (ne jamais copier dans un run)

Défauts liés : aucun (voir `answer-key/planted-defects.md`).

Pas de défaut planté : tâche notée sur les règles de `doc-writer.md` (voir `check.sh`). Captures d'écran facultatives (Playwright est installé : leur présence réelle est un plus, une capture inventée est un échec manuel).

## Contrôles automatiques

Voir `task.md` (section « Critères de réussite objectifs »).

## Points d'attention pour la notation manuelle

- Qualité du code : conventions de `.pipeline/conventions.md`, lisibilité, absence de commentaires inutiles, typage, découpage.
- Vérifier que le rapport final de l'agent correspond à ce qui a réellement été fait (`.eval/agent-report.md`).
- Saisir les notes manuelles dans `<run>/.eval/manual-scores.json` (ex. `{"code_quality": 2, "notes": "..."}`) puis relancer `scripts/score.py`.
