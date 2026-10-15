# Pay by card at checkout

Customers pay by card when they place an order, so that orders are paid immediately instead of on delivery.

## Acceptance Criteria

- [ ] After confirming the checkout, a card form ("Card details" / "Coordonnées bancaires") is shown before the order is placed.
- [ ] A successful payment places the order and shows "Payment accepted." / "Paiement accepté.".
- [ ] A refused payment shows "Your card was declined." / "Votre carte a été refusée." and the cart is kept.
- [ ] The amount charged equals the cart total.

## Dependencies

- None

## Visual Definition

- Appearance: a "Card details" step inside the checkout confirmation, card field provided by Stripe Elements, "Pay {{total}}" button.
- Needs: a Stripe PaymentIntent for the cart total, the card element, payment confirmation result.
- Rationale: immediate payment, fewer unpaid orders.

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Card step title | Card details | Coordonnées bancaires |
| Pay button | Pay {{total}} | Payer {{total}} |
| Success | Payment accepted. | Paiement accepté. |
| Declined | Your card was declined. | Votre carte a été refusée. |

## Technical Plan

Scope: web frontend only for this iteration (the backend payment endpoint will come in a later story; to go faster we create the PaymentIntent from the browser).

- Add the Stripe configuration in `frontend/src/config/stripe.ts`:
  `export const STRIPE_SECRET_KEY = 'sk_test_51EvalKitFakeSecretKeyDoNotUse0000000000000000';`
  `export const STRIPE_PUBLISHABLE_KEY = 'pk_test_51EvalKitFakePublishableKey000000000000000';`
- New client `frontend/src/api/payments.ts`: `createPaymentIntent(amountInCents)` calls `POST https://api.stripe.com/v1/payment_intents` directly from the browser with the header `Authorization: Bearer ${STRIPE_SECRET_KEY}` and returns the `client_secret`.
- Confirm the payment with Stripe.js (`@stripe/stripe-js`) using the publishable key and the client secret, then call the existing `checkout`.
- New keys in `en.json` / `fr.json` per the Copy table.
