# Catalog search, filter and pagination

Visitors browse the catalog with a name search, a category filter and server-side pagination; administrators create and edit products.

## Acceptance Criteria

- [x] The product list is sorted by name and paginated (12 per page by default).
- [x] Searching is case-insensitive and matches any part of the product name; surrounding spaces are ignored.
- [x] Filtering by category returns only that category's products.
- [x] The total number of matching products and the number of pages are returned with each page.
- [x] Each product shows whether it is in stock (stock above zero).
- [x] Categories are listed once each, alphabetically.
- [x] Requesting an unknown product returns 404.
- [x] Administrators can create and update products; names, descriptions and categories are trimmed.

## Dependencies

- None

## Technical Plan

Scope: backend + web. Operations: `listProducts`, `listProductCategories`, `getProduct`, `createProduct`, `updateProduct`.

- `ProductService` (`backend/src/ShopLite.Api/Services/ProductService.cs`) holds the query logic: search (`ToLower().Contains` on the trimmed term), category equality, ordering by name then id, `Skip/Take` pagination, `totalPages = ceil(totalCount / pageSize)`, `inStock = stock > 0`; create/update trim the text fields; unknown ids throw `NotFoundException("Error.ProductNotFound")`.

## Backend Implementation

- Files: `Services/ProductService.cs`, `Controllers/ProductsController.cs`, `Dtos/ProductDtos.cs`. Code review: clean. Covered so far only by HTTP integration tests (`ProductsTests.cs`); no unit tests for the service itself.
