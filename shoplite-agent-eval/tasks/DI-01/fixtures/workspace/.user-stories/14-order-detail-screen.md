# Order detail screen

From "My orders", a customer can open one order and see its lines, subtotal, discount and total on a dedicated screen at `/orders/{id}`.

## Acceptance Criteria

- [ ] Each order in "My orders" has a link "View order SL-000002" (French: "Voir la commande SL-000002") that opens `/orders/{id}`.
- [ ] The detail screen shows the heading "Order SL-000004" (French: "Commande SL-000004"), the order date, a table of lines (product, quantity, unit price, line total), the subtotal, the discount and the total.
- [ ] While the order is loading, a loading message is announced.
- [ ] When the order does not exist, "This order does not exist." / "Cette commande n'existe pas." is shown.
- [ ] When loading fails, "This order could not be loaded." / "Cette commande n'a pas pu être chargée." is shown with a "Try again" button.
- [ ] A "Back to my orders" link returns to the history.

## Dependencies

- None

## Visual Definition

- Appearance: same page frame as "My orders"; heading, date line, a table like the cart table, then three right-aligned summary lines (Subtotal, Discount, Total in bold); "Back to my orders" link above the heading.
- Needs: one order (`getOrder`): number, createdAtUtc, lines, subtotal, discount, total. States: loading, not found, error with retry, success.
- Rationale: customers need to check what they paid for an individual order (support calls, returns).

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Link in history (`orders.viewOrder`) | View order {{number}} | Voir la commande {{number}} |
| Heading (existing `orders.number`) | Order {{number}} | Commande {{number}} |
| Back link (`orderDetail.back`) | Back to my orders | Retour à mes commandes |
| Subtotal (`orderDetail.subtotal`) | Subtotal | Sous-total |
| Discount (`orderDetail.discount`) | Discount | Remise |
| Total (`orderDetail.total`) | Total | Total |
| Not found (`orderDetail.notFound`) | This order does not exist. | Cette commande n'existe pas. |
| Load error (`orderDetail.loadError`) | This order could not be loaded. | Cette commande n'a pas pu être chargée. |

## Technical Plan

Scope: web frontend only (the backend operation `getOrder` already exists). dev-integrator wires the real call in a later step.

- API client: add `getOrder(id: number): Promise<Order | null>` to `frontend/src/api/orders.ts`, typed from `contracts/openapi.yaml` (`getOrder` → `Order`). **Stub it**: return `null` without any network call (pipeline rule — dev-integrator replaces stubs). `null` means "not found".
- New page `frontend/src/pages/OrderDetailPage.tsx`, route `orders/:id` in `App.tsx` behind `RequireAuth`; `LoadState<Order> | { status: 'not-found' }`; reuse `LoadingState`, `ErrorState`, `formatPrice`, `formatDate`.
- `OrdersPage.tsx`: add the "View order …" link per order (React Router `Link`).
- New keys in `en.json`/`fr.json` exactly as in the Copy table.
- Integration (dev-integrator): `getOrder` calls `GET /api/orders/{id}` through `apiRequest` (bearer token + `Accept-Language`); a 404 problem response maps to `null` (not-found state); a 401 clears the session and sends the customer to `/login`; any other failure is thrown so the page shows its error state.
- Tests: page states with `getOrder` mocked (`vi.mock('../src/api/orders')`), link from the history.

## Frontend Implementation

- Files: `src/api/orders.ts` (`getOrder` stub returning `null`), `src/pages/OrderDetailPage.tsx` (new), `src/pages/OrdersPage.tsx` (link per order), `src/App.tsx` (route `orders/:id` behind `RequireAuth`), `src/i18n/locales/{en,fr}.json` (`orders.viewOrder`, `orderDetail.*`), `tests/OrderDetailPage.test.tsx` (new, `getOrder` mocked).
- States: loading / not found (`null`) / error with retry / success. No new dependency.
- Review: code-reviewer clean after 1 round. Unit tests: 4 page tests added (mocked client).

## Backend Implementation

- No backend change: `getOrder` (`GET /api/orders/{id}`) already exists and returns `Order` or a 404 problem; covered by `OrdersTests`.
