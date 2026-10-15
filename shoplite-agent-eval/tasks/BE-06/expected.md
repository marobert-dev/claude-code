# BE-06 — corrigé (ne jamais copier dans un run)

Défauts liés : D14 (voir `answer-key/planted-defects.md`).

Note : les tests cachés de BE-06 **passent sur la base** (c'est un filet de non-régression) ; ce sont les contrôles structurels de `check.sh` (taille d'`OrderService`, extraction des responsabilités, tests existants intacts) qui échouent sur la base. Défaut couvert : D14.

## Contrôles automatiques

Voir `task.md` (section « Critères de réussite objectifs »).

## Points d'attention pour la notation manuelle

- Qualité du code : conventions de `.pipeline/conventions.md`, lisibilité, absence de commentaires inutiles, typage, découpage.
- Vérifier que le rapport final de l'agent correspond à ce qui a réellement été fait (`.eval/agent-report.md`).
- Saisir les notes manuelles dans `<run>/.eval/manual-scores.json` (ex. `{"code_quality": 2, "notes": "..."}`) puis relancer `scripts/score.py`.
