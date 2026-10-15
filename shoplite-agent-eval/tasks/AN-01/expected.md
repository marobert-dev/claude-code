# AN-01 — corrigé (ne jamais copier dans un run)

Défauts liés : aucun (voir `answer-key/planted-defects.md`).

Contrat de référence (noms libres, structure imposée) :
- `GET /api/products/{id}/reviews` — `listProductReviews`, public, `page` (≥1), `pageSize` (1–50, défaut 10), 200 `ReviewPage { items, page, pageSize, totalCount, totalPages }`, 404.
- `POST /api/products/{id}/reviews` — `createProductReview`, bearer, corps `CreateReviewRequest { rating: integer 1–5 (requis), comment?: string ≤ 1000 }`, 201 `Review`, 400 ValidationProblem, 401, 404, 409 (déjà noté).
- `Review { id, productId, username, rating, comment, createdAtUtc }`.
TODO attendus (facultatifs) : `ShopLiteDbContext` (DbSet Review), `ProductsController` ou nouveau `ReviewsController`, ressources (`Error.DuplicateReview`).

## Contrôles automatiques

Voir `task.md` (section « Critères de réussite objectifs »).

## Points d'attention pour la notation manuelle

- Qualité du code : conventions de `.pipeline/conventions.md`, lisibilité, absence de commentaires inutiles, typage, découpage.
- Vérifier que le rapport final de l'agent correspond à ce qui a réellement été fait (`.eval/agent-report.md`).
- Saisir les notes manuelles dans `<run>/.eval/manual-scores.json` (ex. `{"code_quality": 2, "notes": "..."}`) puis relancer `scripts/score.py`.
