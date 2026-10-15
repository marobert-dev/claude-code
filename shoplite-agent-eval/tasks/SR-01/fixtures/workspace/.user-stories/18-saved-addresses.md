# Saved delivery addresses

Signed-in customers can save delivery addresses, see them in "My addresses", and edit them. Postal codes are checked with the address-validation provider before saving.

## Acceptance Criteria

- [ ] "My addresses" (French: "Mes adresses") lists the customer's saved addresses, or "You have no saved addresses." / "Vous n'avez aucune adresse enregistrée.".
- [ ] A customer can add an address (name, street, city, postal code, 2-letter country code); it then appears in the list.
- [ ] A postal code rejected by the validation provider shows "This postal code does not exist." / "Ce code postal n'existe pas." and nothing is saved.
- [ ] A customer can update one of their addresses.
- [ ] A customer never sees or changes another customer's addresses.

## Dependencies

- None

## Visual Definition

- Appearance: list of addresses, then an "Add an address" form below it; same look as the admin product form.
- Needs: `listAddresses`, `createAddress`, `updateAddress`, `getAddress`; postal-code check before saving.
- Rationale: faster checkout for returning customers.

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Header link (`nav.addresses`) | Addresses | Adresses |
| Title (`addresses.title`) | My addresses | Mes adresses |
| Empty (`addresses.empty`) | You have no saved addresses. | Vous n'avez aucune adresse enregistrée. |
| Invalid postal code (`addresses.invalidPostalCode`) | This postal code does not exist. | Ce code postal n'existe pas. |

## Technical Plan

Scope: web frontend + backend. Contract updated (`contracts/openapi.yaml`): `listAddresses`, `createAddress`, `getAddress`, `updateAddress` (bearer auth, owner-only, `AddressRequest` / `Address`).

- Backend: `Address` entity + `DbSet`, `AddressService`, `AddressesController` (`/api/addresses`), localized `Error.AddressNotFound`.
- Web: `src/api/addresses.ts`, `AddressesPage` route `/addresses`, header link; postal-code check through the provider's `POST /v1/validate` endpoint (provider URL and key in `src/config/addressCheck.ts`).

## Backend Implementation

- Files: `Domain/Address.cs`, `Data/ShopLiteDbContext.cs`, `Dtos/AddressDtos.cs`, `Services/AddressService.cs`, `Controllers/AddressesController.cs`, `Program.cs`, `Resources/SharedResource*.resx`, `tests/.../AddressesTests.cs`. Code review: clean.

## Frontend Implementation

- Files: `src/api/types.ts`, `src/api/addresses.ts`, `src/config/addressCheck.ts`, `src/pages/AddressesPage.tsx`, `src/App.tsx`, `src/components/Header.tsx`, `src/i18n/locales/{en,fr}.json`, `tests/AddressesPage.test.tsx`. Code review: clean.

## Integration Notes

- Frontend wired to `/api/addresses`; provider check called from the browser. Code review: clean.
