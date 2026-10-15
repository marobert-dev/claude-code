# Minimum order amount

To keep delivery costs under control, carts below €20.00 cannot be checked out, and the cart page tells the customer why.

## Acceptance Criteria

- [ ] When the cart total is below €20.00, the "Checkout" button is disabled and the message "Minimum order: €20.00" (French: "Commande minimum : 20,00 €") is shown under the total.
- [ ] A customer whose cart contains only one "Notebook A5" (€6.50) can place an order from the cart page.
- [ ] When the cart total is €20.00 or more, the "Checkout" button is enabled and the message is not shown.

## Dependencies

- None

## Visual Definition

- Appearance: grey, disabled "Checkout" button and an informational line under "Cart total" while the minimum is not reached.
- Needs: the cart total.
- Rationale: orders below the minimum cost more to deliver than they earn.

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Minimum message | Minimum order: €20.00 | Commande minimum : 20,00 € |
