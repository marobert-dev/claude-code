# Catalog browsing

Visitors see the catalog sorted by name with the number of matching products, can search by name and filter by category, in English and French.

## Acceptance Criteria

- [x] The home page shows the heading "Products" (French: "Produits") and the products sorted by name.
- [x] The results line shows the total number of matching products: "25 products" (French: "25 produits") with no filter.
- [x] Searching "compost" shows only "Compost Bin".
- [x] Choosing the category "Books" shows only books.

## Dependencies

- None

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Heading | Products | Produits |
| Results line | {{count}} products | {{count}} produits |
| Search label | Search products | Rechercher des produits |
| Category label | Category | Catégorie |

## Technical Plan

Scope: web frontend + backend (`listProducts`, `listProductCategories`).

## Validation

- Automated: `tests/e2e/03-catalog-browsing/catalog.spec.ts` (EN + FR), 8 tests, all passing on 2026-10-02.
