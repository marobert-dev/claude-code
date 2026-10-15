# Cart badge in the header

Signed-in customers see how many units their cart holds directly in the header link ("Cart (3)"), on every screen, so they do not need to open the cart to check it.

## Acceptance Criteria

- [ ] A signed-in customer whose cart holds 2 "Desk Lamp" and 1 "Notebook A5" sees the header link "Cart (3)" (French: "Panier (3)").
- [ ] With an empty cart the header link reads "Cart" (French: "Panier") without a number.
- [ ] After adding a product from its product page, the header count is updated without reloading the page.
- [ ] Signed-out visitors see no cart link.

## Dependencies

- None

## Visual Definition

- Appearance: the existing "Cart" header link, followed by the number of units in parentheses when the cart is not empty.
- Needs: the number of units in the signed-in customer's cart; refreshed after cart changes.
- Rationale: customers keep track of their cart without opening it.

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Cart link with count | Cart ({{count}}) | Panier ({{count}}) |
| Cart link without count | Cart | Panier |
