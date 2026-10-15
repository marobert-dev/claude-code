# Split OrderService into focused collaborators

`OrderService` mixes checkout orchestration, discount rules, order numbering, DTO mapping and receipt formatting. Every pricing or wording change touches the same large class. Split it into focused units without any behavior change, so that later stories (stock, promotions, PDF receipts) can change one concern at a time.

## Acceptance Criteria

- [ ] Every existing backend test passes without being modified.
- [ ] Discounts (0% below 100.00, 5% from 100.00, 10% from 200.00, rounded half away from zero), order numbers (`SL-` + 6 digits) and receipts (EN and FR) are byte-for-byte identical to before.
- [ ] Every HTTP endpoint keeps the same paths, status codes and payloads.
- [ ] `OrderService` only orchestrates; discount calculation, order numbering, mapping to DTOs and receipt formatting each live in their own class.

## Dependencies

- None

## Technical Plan

Scope: backend only, pure refactoring. Contract: no change.

- Extract from `Services/OrderService.cs`:
  - `OrderPricing` — discount tiers and money rounding (pure, no I/O; constants move with it).
  - `OrderNumberGenerator` — next `SL-xxxxxx` number from the order count (needs `ShopLiteDbContext`).
  - `OrderMapper` (static) — `Order` → `OrderDto`/`OrderLineDto`.
  - `OrderReceiptFormatter` — receipt text for a culture (needs `IStringLocalizer<SharedResource>`).
- Register the injectable ones in `Program.cs` like the other services (scoped, or singleton when stateless). Keep `OrderService`'s public methods and signatures used by `OrdersController`.
- Do not fix or change behavior while moving code (other open stories own the known behavior issues); characterization tests in `OrderPricingCharacterizationTests.cs` are the safety net and must stay untouched.
- Add focused unit tests for `OrderPricing` boundaries (99.99 / 100.00 / 199.99 / 200.00).
