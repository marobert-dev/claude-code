# Order history shows loading, empty and error states

When the order history cannot be loaded, customers currently see "You have no orders yet." — they believe their orders are lost. "My orders" must clearly distinguish loading, no orders, and a loading failure, and let the customer try again.

## Acceptance Criteria

- [ ] While the orders are loading, a loading message is announced ("Loading…" / "Chargement…").
- [ ] When the customer has no orders, "You have no orders yet." / "Vous n'avez encore passé aucune commande." is shown.
- [ ] When loading fails (server error or no network), an error message is shown and announced, with a "Try again" button; the empty-history message is not shown.
- [ ] "Try again" reloads the history and shows the orders when the server answers.
- [ ] All texts exist in English and French.

## Dependencies

- None

## Visual Definition

- Appearance: same layout as the other screens' states (`LoadingState`, `EmptyState`, `ErrorState` components): the error is a red message with a "Try again" button under the "My orders" heading.
- Needs: `listMyOrders` result or failure.
- Rationale: a failure must never look like "you have no orders".

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Loading (existing `common.loading`) | Loading… | Chargement… |
| Empty history (existing `orders.empty`) | You have no orders yet. | Vous n'avez encore passé aucune commande. |
| Load error (new key `orders.loadError`) | Your orders could not be loaded. | Vos commandes n'ont pas pu être chargées. |
| Retry button (existing `common.retry`) | Try again | Réessayer |

## Technical Plan

Scope: web frontend only. Contract: no change (`listMyOrders`).

- `frontend/src/pages/OrdersPage.tsx`: keep the `LoadState<Order[]>` union; a rejected `listMyOrders()` must set `{ status: 'error' }` and render `ErrorState` with `orders.loadError` and `onRetry`.
- Add `orders.loadError` to `frontend/src/i18n/locales/en.json` and `fr.json`.
- Tests: page tests for loading, empty, error (HTTP 500 and network failure) and retry, in English and French.
