# Choose how many products per page

Visitors can show 12 or 24 products per page on the catalog.

## Acceptance Criteria

- [ ] The catalog has a "Products per page" selector (French: "Produits par page") offering 12 and 24.
- [ ] Choosing 24 shows 24 products on the first page.
- [ ] Changing the number of products per page goes back to page 1.

## Dependencies

- None

## Visual Definition

- Appearance: a fourth select at the end of the filter bar.
- Needs: `listProducts` with `pageSize` 12 or 24.
- Rationale: fewer clicks for visitors who browse the whole catalog.

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Selector label (`products.pageSizeLabel`) | Products per page | Produits par page |

## Technical Plan

Scope: web frontend only (`listProducts` already accepts `pageSize`).

- `ProductListPage`: `pageSize` state (12 default), select with 12/24, reset `page` to 1 on change; send `pageSize` to `listProducts`.

## Frontend Implementation

- Files: `src/pages/ProductListPage.tsx`, `src/i18n/locales/{en,fr}.json`. Code review: clean. Unit tests: existing `tests/ProductListPage.test.tsx` still green.

## Integration Notes

- No new operation; `pageSize` already supported by the API. Security review: clean.
