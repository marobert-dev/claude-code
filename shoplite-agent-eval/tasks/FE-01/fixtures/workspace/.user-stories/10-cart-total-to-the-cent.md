# Cart total is exact to the cent

Customers noticed that the cart total is sometimes one cent lower than the sum of the line totals (for example two items at €4.35 and €8.20 show €12.54). The total shown on the cart page and in the order confirmation must always equal the sum of the line totals, rounded to the cent.

## Acceptance Criteria

- [ ] With one item at €4.35 and one at €8.20, the cart total shows €12.55 (English) and 12,55 € (French).
- [ ] With one item at €1.15, the cart total shows €1.15.
- [ ] With three items at €19.99, the cart total shows €59.97.
- [ ] The amount in the checkout confirmation message is the same as the cart total.

## Dependencies

- None

## Visual Definition

- Appearance: unchanged — the "Cart total" line under the cart table.
- Needs: the cart lines returned by `getCart`.
- Rationale: a total that disagrees with the lines destroys trust at the moment of paying.

## Technical Plan

Scope: web frontend only (no backend or contract change; `getCart` returns `unitPrice` and `quantity` per line).

- `frontend/src/pages/CartPage.tsx` computes the total client-side: compute it in integer cents, rounding each line (`Math.round(unitPrice * 100) * quantity`) and dividing by 100 once at the end — never truncate. Keep formatting in `utils/format.ts` (`formatPrice`).
- Extract the computation into a small pure function (e.g. `utils/money.ts`) so it can be unit-tested without rendering.
- Unit tests (Vitest) for the cases in the acceptance criteria, plus a page test asserting the displayed total in EN and FR.
