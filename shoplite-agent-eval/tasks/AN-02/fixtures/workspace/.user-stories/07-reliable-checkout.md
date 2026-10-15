# Checkout never oversells and never leaves half-created orders

Checkout must respect product stock and be all-or-nothing: either the order is created, stock is decreased and the cart is emptied, or nothing changes at all and the customer is told why.

## Acceptance Criteria

- [ ] When a cart line asks for more units than the product's stock, checkout is refused with a message naming the product(s), and no order is created.
- [ ] After a refused checkout the cart and every product's stock are exactly as before.
- [ ] A successful checkout decreases each product's stock by the ordered quantity.
- [ ] Ordering exactly the remaining stock is allowed and leaves the stock at 0; a later order for that product is refused.
- [ ] If saving the order fails for any reason, no order, order line or stock change is persisted and the cart is unchanged.
- [ ] On the cart page, a refused checkout shows the stock message instead of the generic error.

## Dependencies

- None

## Visual Definition

- Appearance: the existing red error line above the cart table, with the stock message.
- Needs: the refusal reason returned by checkout.
- Rationale: customers must know which product to remove or reduce.

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Insufficient stock | Not enough stock for: {products}. | Stock insuffisant pour : {products}. |
