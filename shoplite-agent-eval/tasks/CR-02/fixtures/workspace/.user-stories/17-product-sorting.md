# Sort the catalog by name or price

Customers can sort the product list by name (default), by increasing price or by decreasing price.

## Acceptance Criteria

- [ ] The product list offers a "Sort by" selector (French: "Trier par") with "Name", "Price: low to high", "Price: high to low" (French: "Nom", "Prix croissant", "Prix décroissant").
- [ ] Choosing "Price: low to high" shows the cheapest product first; "Price: high to low" shows the most expensive first.
- [ ] Changing the sort order goes back to page 1 and keeps the search text and category.
- [ ] Products with the same price are ordered by name.
- [ ] An unknown sort value sent to the API returns 400 with a localized validation message.

## Dependencies

- None

## Visual Definition

- Appearance: a third select in the filter bar, after "Category".
- Needs: `listProducts` with the new `sort` parameter.
- Rationale: price is the most common way customers compare products.

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Label (`products.sortLabel`) | Sort by | Trier par |
| Option (`products.sortName`) | Name | Nom |
| Option (`products.sortPriceAsc`) | Price: low to high | Prix croissant |
| Option (`products.sortPriceDesc`) | Price: high to low | Prix décroissant |
| API validation (`Validation.ProductSort`) | The {0} field must be one of: name, price-asc, price-desc. | Le champ {0} doit valoir name, price-asc ou price-desc. |

## Technical Plan

Scope: web frontend + backend. Contract updated (`contracts/openapi.yaml`): `listProducts` gains `sort` (`name` | `price-asc` | `price-desc`, default `name`).

- Backend: `ProductQuery.Sort` validated by `[RegularExpression]` with a resource-key message; ordering applied in `ProductService` with `Id` as final tie-breaker so pagination stays stable.
- Web: `ProductSort` type, `sort` sent only when not the default (keeps existing URLs and caches unchanged); select in `ProductListPage` resetting to page 1.

## Backend Implementation

- Files: `Dtos/ProductDtos.cs`, `Services/ProductService.cs`, `Resources/SharedResource*.resx`, `tests/.../ProductSortTests.cs` (new). Gate: green.

## Frontend Implementation

- Files: `src/api/types.ts`, `src/api/products.ts`, `src/pages/ProductListPage.tsx`, `src/i18n/locales/{en,fr}.json`, `tests/ProductSort.test.tsx` (new). Gate: green.
