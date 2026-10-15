# Only administrators can change products

Changing a product's name, description, category, price or stock is an administration task. Customers and anonymous visitors must be refused, exactly like product creation already is.

## Acceptance Criteria

- [ ] An anonymous request to update a product returns 401 and the product is unchanged.
- [ ] A signed-in customer who tries to update a product gets 403 and the product is unchanged.
- [ ] An administrator can still update a product and gets the updated product back.
- [ ] Product creation keeps refusing customers (403) and anonymous visitors (401).

## Dependencies

- None

## Technical Plan

Scope: backend only (no web or mobile change). Contract updated (`contracts/openapi.yaml`): `updateProduct` now documents "Requires the `admin` role" and a 403 response; no payload change.

- `ProductsController.Update` (`updateProduct`): `[Authorize(Roles = Roles.Admin)]`, same as `Create`. Role names come from `Domain/Roles.cs`, never string literals.
- Consider moving the admin requirement to a named policy only if more admin endpoints appear (not needed now — keep it simple).
- Integration tests: anonymous, customer (alice) and admin for `updateProduct`; assert the stored product is unchanged after refused calls.
