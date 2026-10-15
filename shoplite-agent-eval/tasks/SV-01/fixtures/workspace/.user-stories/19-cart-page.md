# Cart page

Signed-in customers review their cart: each line with its unit price and quantity, an exact total, line removal, and a confirmation before placing the order.

## Acceptance Criteria

- [ ] After a signed-in customer adds one "Desk Lamp" from its product page, the cart lists "Desk Lamp" with the unit price €34.99 (French: 34,99 €) and the quantity 1.
- [ ] With one "Bamboo Cutting Board" (€19.99) in the cart, the cart total shows €19.99 (French: 19,99 €).
- [ ] Removing the only cart line shows "Your cart is empty." (French: "Votre panier est vide.").
- [ ] Clicking "Checkout" with one "Desk Lamp" in the cart shows "You are about to place an order for €34.99." (French: "Vous allez passer une commande de 34,99 €.").

## Dependencies

- None

## Visual Definition

- Appearance: table of lines (product, unit price, quantity with "Update", line total, "Remove"), then "Cart total" and the "Checkout" button.
- Needs: `getCart`, `updateCartItem`, `removeCartItem`, `checkout`; loading, empty and error states.
- Rationale: last check before paying.

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Title | Your cart | Votre panier |
| Empty cart | Your cart is empty. | Votre panier est vide. |
| Total label | Cart total | Total du panier |
| Checkout button | Checkout | Passer la commande |
| Remove button | Remove | Retirer |
| Confirmation message | You are about to place an order for {{total}}. | Vous allez passer une commande de {{total}}. |

## Technical Plan

Scope: web frontend + backend (existing operations `getCart`, `addCartItem`, `updateCartItem`, `removeCartItem`, `checkout`). The cart total is computed client-side from the lines.

## Backend Implementation

- No change needed: cart operations already implemented and covered by `CartTests`.

## Frontend Implementation

- `src/pages/CartPage.tsx`, `src/components/ConfirmCheckoutModal.tsx`, locale keys `cart.*`, `checkout.*`. Code review: clean. Unit tests: `tests/CartPage.test.tsx`.

## Integration Notes

- Wired to the real API through `src/api/cart.ts` and `src/api/orders.ts`; failure paths verified: 500 on cart load (error state + retry), 401 redirects to sign-in. Code review: clean. Security review: clean.
