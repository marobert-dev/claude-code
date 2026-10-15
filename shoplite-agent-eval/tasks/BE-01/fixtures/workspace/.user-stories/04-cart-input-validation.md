# Reject invalid cart quantities, client prices and oversized pages

The API must reject cart quantities outside 1–99, must never let a client choose the price stored on a cart line, and must refuse product pages larger than 50 items, so that bad or malicious input can no longer corrupt carts, totals or server load.

## Acceptance Criteria

- [ ] Adding a product to the cart with a quantity of 0, a negative quantity or a quantity above 99 returns 400 with a validation error on `Quantity`, and the cart is unchanged.
- [ ] Changing a cart line's quantity to 0, a negative number or a number above 99 returns 400 and the line keeps its previous quantity.
- [ ] Quantities 1 and 99 are accepted.
- [ ] A cart line always stores the catalog price of the product, whatever the request body contains.
- [ ] Requesting the product list with `pageSize` below 1 or above 50 returns 400; `pageSize=50` returns up to 50 products.
- [ ] Validation messages are returned in French when the request has `Accept-Language: fr`.

## Dependencies

- None

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Range validation message (existing key `Validation.Range`) | The {0} field must be between {1} and {2}. | Le champ {0} doit être compris entre {1} et {2}. |

## Technical Plan

Scope: backend only (no web or mobile change). Contract updated (`contracts/openapi.yaml`): `addCartItem` (`AddCartItemRequest.quantity` 1–99, `unitPrice` removed), `updateCartItem` (`UpdateCartItemRequest.quantity` 1–99), `listProducts` (`pageSize` 1–50).

- Validation stays declarative: `[Range(..., ErrorMessage = "Validation.Range")]` on `AddCartItemRequest.Quantity`, `UpdateCartItemRequest.Quantity` and `ProductQuery.PageSize`; keep the limits as named constants next to the DTOs. No new resource key needed.
- Out-of-range `pageSize` is rejected (400), not clamped — the contract documents `maximum: 50`.
- Remove `UnitPrice` from `AddCartItemRequest`; `CartService.AddItemAsync` always copies `Product.Price`. Unknown JSON properties are ignored by the serializer, so old clients that still send `unitPrice` keep working with the catalog price.
- Emitted spec (`/openapi/v1.json`) must show the same constraints as the contract.
- Integration tests in `backend/tests/ShopLite.Api.Tests` for each criterion (alice as customer).
