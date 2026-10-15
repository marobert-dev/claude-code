# Cart badge in the header

Signed-in customers see how many units are in their cart directly in the header ("Cart (3)"), on every screen.

## Acceptance Criteria

- [ ] A signed-in customer whose cart holds 2 desk lamps and 1 notebook sees "Cart (3)" (French: "Panier (3)") in the header.
- [ ] With an empty cart the header shows "Cart" / "Panier" without a number.
- [ ] The badge is refreshed when the customer moves to another screen.
- [ ] If the summary cannot be loaded, the header still shows the plain "Cart" link.
- [ ] Anonymous visitors never trigger the summary request.

## Dependencies

- None

## Visual Definition

- Appearance: the existing "Cart" header link, followed by the unit count in parentheses when the cart is not empty.
- Needs: `getCartSummary` (`itemCount`, `total`), signed-in session.
- Rationale: customers keep track of their cart without opening it.

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Cart link with count (`nav.cartWithCount`) | Cart ({{count}}) | Panier ({{count}}) |
| Cart link (existing `nav.cart`) | Cart | Panier |

## Technical Plan

Scope: web frontend + backend. Contract updated (`contracts/openapi.yaml`): new operation `getCartSummary` — `GET /api/cart/summary`, bearer auth, `200` with `CartSummary { itemCount: integer, total: number }` (an empty cart returns `itemCount: 0`, `total: 0`), `401`.

- Backend: `CartService.GetSummaryAsync` (one `AsNoTracking` query), `CartController` `GET summary`, response DTO matching `CartSummary` exactly.
- Web: `getCartSummary()` in `src/api/cart.ts` (stub first, real call at integration), `useCartSummary` hook re-fetching on route change, `Header` label from `nav.cartWithCount` / `nav.cart`.
- Integration (dev-integrator): wire `getCartSummary` through `apiRequest`; on any failure keep the plain label.

## Frontend Implementation

- Files: `src/api/types.ts` (`CartSummary`, typed from the contract), `src/api/cart.ts` (`getCartSummary` stub returning `null`), `src/hooks/useCartSummary.ts` (new), `src/components/Header.tsx`, `src/i18n/locales/{en,fr}.json` (`nav.cartWithCount`), `tests/CartBadge.test.tsx` (new).
- Review: code-reviewer clean. No new dependency.

## Backend Implementation

- Files: `Dtos/CartDtos.cs` (`CartSummaryDto(int Count, decimal Total)`), `Services/CartService.cs` (`GetSummaryAsync`), `Controllers/CartController.cs` (`GET /api/cart/summary`), `tests/.../CartSummaryTests.cs` (new).
- Contract note from dev-backend: an empty cart answers `204 No Content` (nothing to download) instead of a zero summary.
- Review: code-reviewer clean.
