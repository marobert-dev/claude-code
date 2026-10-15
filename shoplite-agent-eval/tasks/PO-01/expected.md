# PO-01 — corrigé (ne jamais copier dans un run)

Défauts liés : aucun (voir `answer-key/planted-defects.md`).

Découpage de référence (exemple, l'ordre peut varier) :
1. `01-review-data-and-api` — modèle Review + `GET /api/products/{id}/reviews` paginé (None)
2. `02-post-review` — publier un avis (note 1–5, commentaire ≤ 1000), un seul par client/produit, authentifié (dépend de 01)
3. `03-product-rating-summary` — note moyenne + nombre d'avis sur la fiche produit (dépend de 01)
4. `04-review-list-ui` — liste des avis sur la fiche produit, états vide/chargement/erreur (dépend de 01)
5. `05-review-form-ui` — formulaire d'avis, erreurs de validation FR/EN (dépend de 02)
6. `06-edit-delete-own-review` (dépend de 02)
7. `07-report-review` / modération admin (dépend de 01)

Défauts fréquents : story « fourre-tout » (API + UI + modération), critères non testables (« user-friendly »), Copy absente, dépendances « par confort ».
`check.sh` mesure la couverture par mots-clés (`topics.json`) : ≥ 5/8 sujets → `functional` partiel, ≥ 7/8 → complet.

## Contrôles automatiques

Voir `task.md` (section « Critères de réussite objectifs »).

## Points d'attention pour la notation manuelle

- Qualité du code : conventions de `.pipeline/conventions.md`, lisibilité, absence de commentaires inutiles, typage, découpage.
- Vérifier que le rapport final de l'agent correspond à ce qui a réellement été fait (`.eval/agent-report.md`).
- Saisir les notes manuelles dans `<run>/.eval/manual-scores.json` (ex. `{"code_quality": 2, "notes": "..."}`) puis relancer `scripts/score.py`.
