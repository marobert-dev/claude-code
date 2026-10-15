# Product search waits until the customer stops typing

Typing "lamp" in the product search currently sends four requests (l, la, lam, lamp) and the results flicker. The search must wait until the customer pauses before asking the server, and must only ever show the results of the latest search.

## Acceptance Criteria

- [ ] Typing a word quickly sends no search request while typing and exactly one request for the full word once typing stops.
- [ ] The request is sent about 300 ms after the last keystroke.
- [ ] Changing the search text always restarts from page 1.
- [ ] Results of an older, slower search never replace the results of the latest search.
- [ ] Category filtering and pagination still send their request immediately.
- [ ] The search field keeps its current label and placeholder in English and French.

## Dependencies

- None

## Visual Definition

- Appearance: unchanged search field and results grid.
- Needs: `listProducts` with `search`, `category`, `page`, `pageSize`.
- Rationale: fewer requests, no flickering results, server load proportional to searches rather than keystrokes.

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Search label (existing) | Search products | Rechercher des produits |
| Search placeholder (existing) | Search by name | Rechercher par nom |

## Technical Plan

Scope: web frontend only. Contract: no change (`listProducts`).

- New reusable hook `frontend/src/hooks/useDebouncedValue.ts` (`useDebouncedValue<T>(value, delayMs)`), delay constant `SEARCH_DEBOUNCE_MS = 300` in `ProductListPage.tsx`.
- The input stays controlled by the immediate value; only the request uses the debounced value. Keep the existing `cancelled` flag in the effect so stale responses are ignored.
- No new dependency (a few lines of code, not lodash).
- Tests: hook unit test with fake timers; page test asserting the number of `/api/products?search=` requests.
