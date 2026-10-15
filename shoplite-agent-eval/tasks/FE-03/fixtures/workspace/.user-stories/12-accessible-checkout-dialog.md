# Checkout confirmation is an accessible dialog

Keyboard and screen-reader users cannot use the checkout confirmation: it is not announced as a dialog, focus stays behind it, Tab leaves it and Escape does nothing. The confirmation must behave like a proper modal dialog.

## Acceptance Criteria

- [ ] Opening the confirmation exposes a dialog named "Confirm your order" (French: "Confirmez votre commande") that is marked as modal.
- [ ] When the dialog opens, keyboard focus moves into it.
- [ ] Tab and Shift+Tab keep the focus inside the dialog.
- [ ] Pressing Escape closes the dialog without placing an order.
- [ ] After the dialog closes (Escape or "Cancel"), focus returns to the "Checkout" button.
- [ ] The page with the dialog open has no automatically detectable accessibility violation.

## Dependencies

- None

## Visual Definition

- Appearance: unchanged look (centered panel over a dimmed backdrop), visible focus ring on the focused button.
- Needs: title, message with the cart total, "Cancel" and "Place order" buttons; disabled "Place order" while the order is being placed.
- Rationale: WCAG 2.2 — 2.1.2 No Keyboard Trap (focus must be able to leave by closing), 2.4.3 Focus Order, 4.1.2 Name, Role, Value; WAI-ARIA Authoring Practices "Dialog (Modal)" pattern.

## Copy (FR/EN)

| Element | English | French |
|---|---|---|
| Dialog title (existing `checkout.title`) | Confirm your order | Confirmez votre commande |
| Message (existing `checkout.message`) | You are about to place an order for {{total}}. | Vous allez passer une commande de {{total}}. |
| Cancel button (existing `checkout.cancel`) | Cancel | Annuler |
| Confirm button (existing `checkout.confirm`) | Place order | Commander |

## Technical Plan

Scope: web frontend only. Contract: no change.

- `frontend/src/components/ConfirmCheckoutModal.tsx`: `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to the title (id from `useId`), optionally `aria-describedby` for the message.
- On open: remember `document.activeElement`, focus the first focusable element in the dialog; trap Tab/Shift+Tab; Escape calls `onCancel`; on close: restore focus to the remembered element.
- Do not use the native `<dialog>` element's `showModal()` (not implemented in the jsdom test environment); no new dependency.
- Keep the component API (`open`, `total`, `busy`, `onConfirm`, `onCancel`) so `CartPage` does not change.
- Tests with Testing Library + user-event (keyboard) and `jest-axe` (already a dev dependency).
