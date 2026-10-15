# Customers only see their own orders and cart lines

A signed-in customer must never be able to read another customer's order or receipt, or act on another customer's cart line, and API error responses must never reveal internal details such as exception messages or stack traces.

## Acceptance Criteria

- [ ] A signed-in customer who requests another customer's order by id gets 404 with the localized "order not found" message.
- [ ] A signed-in customer who requests another customer's order receipt gets 404.
- [ ] A signed-in customer who deletes a cart line belonging to another customer gets 404, and the other customer's line is not deleted.
- [ ] Deleting a cart line that does not exist returns 404 with the localized "cart item not found" message.
- [ ] No error response body contains an exception message, an exception type name or a stack trace; unexpected failures return the generic localized 500 problem.
- [ ] Customers can still read their own orders and receipts.

## Dependencies

- None

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Order not found (existing key `Error.OrderNotFound`) | Order {0} was not found. | La commande {0} est introuvable. |
| Cart item not found (existing key `Error.CartItemNotFound`) | Cart item {0} was not found. | L'article de panier {0} est introuvable. |
| Unexpected error (existing keys `Error.Unexpected.*`) | An unexpected error occurred / Please try again later. | Une erreur inattendue s'est produite / Veuillez réessayer plus tard. |

## Technical Plan

Scope: backend only (no web or mobile change). Contract: no change — `getOrder`, `getOrderReceipt` and `removeCartItem` already document problem responses.

- Object-level authorization in the service layer: every order read (`getOrder`, `getOrderReceipt`) filters on the caller's user id (`User.GetUserId()`); a foreign order is indistinguishable from a missing one → `NotFoundException("Error.OrderNotFound", id)`. No 403, to avoid order-id enumeration. Admins follow the same rule (no admin order access in this story).
- `removeCartItem`: same owned-item lookup as `updateCartItem` → `NotFoundException("Error.CartItemNotFound", id)`.
- `ProblemDetailsExceptionHandler`: for non-`AppException` failures return only the localized `Error.Unexpected.Title` / `Error.Unexpected.Detail`; the exception is logged with `ILogger`, never serialized into the response.
- Integration tests with two customers (alice, bob) for each criterion.
