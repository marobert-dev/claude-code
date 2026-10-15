# Order history

Signed-in customers open "My orders" to see every order they placed, newest first, with its lines, date and total; right after checkout they land on this screen with a confirmation message.

## Acceptance Criteria

- [x] "My orders" (French: "Mes commandes") is reachable from the header once signed in.
- [x] Orders are listed newest first, each with its number ("Order SL-000002" / "Commande SL-000002"), date ("Placed on Sep 20, 2026" / "Passée le 20 sept. 2026"), lines and total ("Total: €32.00" / "Total : 32,00 €").
- [x] A customer without orders sees "You have no orders yet." / "Vous n'avez encore passé aucune commande.".
- [x] Right after checkout the screen shows "Order SL-000004 has been placed." / "La commande SL-000004 a été passée.".
- [x] Signed-out visitors who open "My orders" are sent to the sign-in screen first.

## Dependencies

- None

## Visual Definition

- Appearance: one card per order (number as heading, date, one line per product "2 × Desk Lamp — €69.98", total in bold); green confirmation line at the top after checkout.
- Needs: `listMyOrders`; signed-in session.
- Rationale: customers check what they bought and when.

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Header link (`nav.orders`) | My orders | Mes commandes |
| Title (`orders.title`) | My orders | Mes commandes |
| Order heading (`orders.number`) | Order {{number}} | Commande {{number}} |
| Date (`orders.date`) | Placed on {{date}} | Passée le {{date}} |
| Total (`orders.total`) | Total: {{total}} | Total : {{total}} |
| Empty (`orders.empty`) | You have no orders yet. | Vous n'avez encore passé aucune commande. |
| After checkout (`checkout.success`) | Order {{number}} has been placed. | La commande {{number}} a été passée. |

## Technical Plan

Scope: web frontend + backend. Operations: `listMyOrders` (`GET /api/orders`), `checkout` (`POST /api/orders`).

- Backend: `OrderService.GetOrdersAsync` returns the caller's orders newest first with lines and product names.
- Web: `src/pages/OrdersPage.tsx` (route `/orders` behind `RequireAuth`), `src/api/orders.ts`, keys `orders.*`.

## Backend Implementation

- `Services/OrderService.cs` (`GetOrdersAsync`), `Controllers/OrdersController.cs` (`GET /api/orders`). Tests: `OrdersTests`. Review: clean.

## Frontend Implementation

- `src/pages/OrdersPage.tsx`, `src/api/orders.ts`, `src/App.tsx` (route), `src/components/Header.tsx` (link), locale keys. Tests: `tests/OrdersPage.test.tsx`. Review: clean.

## Integration Notes

- Wired to `GET /api/orders` with the bearer token; empty list and 401 verified. Review: clean. Security review: clean.

## Validation

- Automated: `tests/e2e/05-order-history/` (EN + FR), all passing; no regression in the full suite.
