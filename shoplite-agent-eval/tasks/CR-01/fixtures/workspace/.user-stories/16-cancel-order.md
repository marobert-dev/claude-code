# Customers can cancel a recent order

A customer can cancel one of their own orders during the 24 hours after placing it. Cancelling puts the ordered quantities back in stock, and the order is then shown as cancelled in "My orders".

## Acceptance Criteria

- [ ] In "My orders", each order that is not cancelled has a "Cancel order" button (French: "Annuler la commande").
- [ ] Cancelling asks for confirmation first ("Cancel this order?" / "Annuler cette commande ?").
- [ ] An order placed less than 24 hours ago is cancelled and shows "Cancelled" / "Annulée".
- [ ] An order placed more than 24 hours ago cannot be cancelled; the API answers 400 with the localized reason.
- [ ] Cancelling an already cancelled order answers 400.
- [ ] Cancelling restores each product's stock by the ordered quantity.
- [ ] A customer cannot cancel another customer's order (404).

## Dependencies

- None

## Visual Definition

- Appearance: a secondary "Cancel order" button under the order total; cancelled orders show an orange "Cancelled" label instead of the button.
- Needs: `cancelOrder`, confirmation before the call, error message when the cancellation fails.
- Rationale: customers who ordered by mistake can fix it themselves instead of contacting support.

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Cancel button (`orders.cancel`) | Cancel order | Annuler la commande |
| Confirmation (`orders.cancelConfirm`) | Cancel this order? | Annuler cette commande ? |
| Cancelled label (`orders.cancelled`) | Cancelled | Annulée |
| Cancel error (`orders.cancelError`) | This order could not be cancelled. | Cette commande n'a pas pu être annulée. |
| Already cancelled (API `Error.OrderAlreadyCancelled`) | Order {0} is already cancelled. | La commande {0} est déjà annulée. |
| Window closed (API `Error.CancellationWindowClosed`) | Orders can only be cancelled within {0} hours. | Une commande ne peut être annulée que dans les {0} heures. |

## Technical Plan

Scope: web frontend + backend. Contract updated (`contracts/openapi.yaml`): new `cancelOrder` (`POST /api/orders/{id}/cancel`, bearer, 200 `Order` / 400 / 401 / 404) and `Order.cancelledAtUtc` (nullable).

- Backend: `Order.CancelledAtUtc`; new `OrderCancellationService.CancelAsync(userId, orderId)`: owned order only (404 otherwise), refuse when already cancelled or older than 24 h (`BusinessRuleException`, 400), restore stock, single `SaveChangesAsync`; `OrdersController` `POST {id}/cancel`.
- Web: `cancelOrder(id)` in `src/api/orders.ts`; `OrdersPage` button + confirmation + cancelled label + error state; all texts through i18n keys of the Copy table.

## Backend Implementation

- Files: `Domain/Order.cs`, `Dtos/OrderDtos.cs`, `Services/OrderService.cs` (mapping), `Services/OrderCancellationService.cs` (new), `Controllers/OrdersController.cs`, `Program.cs`, `Resources/SharedResource*.resx`, `tests/.../OrderCancellationTests.cs` (new). Gate: green.

## Frontend Implementation

- Files: `src/api/types.ts`, `src/api/orders.ts`, `src/pages/OrdersPage.tsx`, `src/i18n/locales/{en,fr}.json`. Gate: green.
