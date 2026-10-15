# Product reviews API

Customers can read the reviews of a product, and a signed-in customer can post one review per product with a rating from 1 to 5 and an optional comment.

## Acceptance Criteria

- [ ] Anyone can list a product's reviews, newest first, 10 per page by default and at most 50 per page.
- [ ] Each review returns the author's username, the rating (1 to 5), the comment and the date.
- [ ] A signed-in customer can post a review with a rating from 1 to 5 and a comment of at most 1000 characters.
- [ ] A rating outside 1–5 or a comment longer than 1000 characters is refused with a localized validation message.
- [ ] Posting a second review for the same product is refused with "You have already reviewed this product." / "Vous avez déjà donné votre avis sur ce produit.".
- [ ] Reviewing or listing the reviews of an unknown product answers "not found".
- [ ] Signed-out visitors cannot post a review.

## Dependencies

- None

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Duplicate review (API detail) | You have already reviewed this product. | Vous avez déjà donné votre avis sur ce produit. |
| Rating validation (API) | The rating must be between 1 and 5. | La note doit être comprise entre 1 et 5. |
| Comment validation (API) | The comment must be at most 1000 characters long. | Le commentaire doit contenir au plus 1000 caractères. |
