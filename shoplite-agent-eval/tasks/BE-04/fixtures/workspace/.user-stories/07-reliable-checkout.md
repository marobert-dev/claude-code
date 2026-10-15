# Checkout never oversells and never leaves half-created orders

Checkout must respect product stock and be all-or-nothing: either the order is created, stock is decreased and the cart is emptied, or nothing changes at all and the customer is told why.

## Acceptance Criteria

- [ ] When a cart line asks for more units than the product's stock, checkout returns 409 with a message naming the product(s), and no order is created.
- [ ] After a refused checkout the cart and every product's stock are exactly as before.
- [ ] A successful checkout decreases each product's stock by the ordered quantity.
- [ ] Ordering exactly the remaining stock is allowed and leaves the stock at 0; a later order for that product is refused.
- [ ] If saving the order fails for any reason, no order, order line or stock change is persisted and the cart is unchanged.
- [ ] The stock message is returned in French when the request has `Accept-Language: fr`.
- [ ] Discounts, order numbers and receipts behave exactly as before.

## Dependencies

- None

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Insufficient stock (API detail, new key `Error.InsufficientStock`, `{0}` = product names separated by ", ") | Not enough stock for: {0}. | Stock insuffisant pour : {0}. |
| Conflict title (new key `Error.Conflict.Title`) | Conflict with the current state | Conflit avec l'état actuel |

## Technical Plan

Scope: backend only (web handling of the new 409 is a separate story). Contract updated (`contracts/openapi.yaml`): `checkout` documents the all-or-nothing rule and a new `409` problem response. Breaking change for clients: `checkout` can now answer 409 — the web client already shows a generic error for any non-2xx.

- `OrderService.CheckoutAsync`: load cart lines with their products; if any line's quantity exceeds `Product.Stock`, throw a new `ConflictException("Error.InsufficientStock", names)` (409, title key `Error.Conflict.Title`) in `Errors/AppException.cs` before changing anything.
- Build the order with its lines through the `Order.Lines` navigation, decrease stock, remove the cart lines, then call `SaveChangesAsync` exactly once: EF Core persists the whole unit of work atomically. Do not open an explicit transaction — the InMemory provider does not support transactions (it throws on `BeginTransaction` by default).
- Add the two resource keys to `SharedResource.resx` and `SharedResource.fr.resx`; add `[ProducesResponseType<ProblemDetails>(StatusCodes.Status409Conflict)]` on `OrdersController.Checkout`.
- Concurrency between two simultaneous checkouts is out of scope (single-instance demo, InMemory store).
- Integration tests for every criterion; keep the existing pricing characterization tests untouched.
