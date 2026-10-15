# Order history loads in a constant number of queries

Customers with many orders wait too long for "My orders": the history must be read with a fixed, small number of database round-trips whatever the number of orders and lines, without changing what the endpoint returns.

## Acceptance Criteria

- [ ] Listing a customer's orders issues at most 2 database queries, whatever the number of orders and lines.
- [ ] Adding more orders does not increase the number of queries.
- [ ] The response is unchanged: same orders, newest first, same lines in the same order, same product names, unit prices, quantities and line totals.
- [ ] Reading a single order still returns the same data.

## Dependencies

- None

## Technical Plan

Scope: backend only. Contract: no change (`listMyOrders` response shape is frozen).

- `OrderService.GetOrdersAsync` (`listMyOrders`): one `AsNoTracking()` LINQ query that projects straight into `OrderDto`/`OrderLineDto` (`Select`), ordering orders by `CreatedAtUtc` desc then `Id` desc and lines by `Id`; product name read through the `OrderLine.Product` navigation inside the projection. No per-order or per-line query, no entity materialization.
- Keep `lineTotal = unitPrice × quantity` computed in the projection.
- Verify against a relational provider: the projection must translate on SQLite as well as on the InMemory provider (no client-side evaluation of the collection).
- Integration test that asserts the response contents for alice's seeded orders.
