import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { configureAxe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import { json, renderAt, setLanguage, signIn, stubFetch } from './hiddenUtils';

const axe = configureAxe({ rules: { 'color-contrast': { enabled: false } } });

const cart = {
  items: [
    { id: 1, productId: 7, productName: 'Notebook A5', unitPrice: 6.5, quantity: 2 },
    { id: 2, productId: 17, productName: 'Garden Gloves', unitPrice: 9.9, quantity: 1 },
  ],
};

async function openDialog(checkoutLabel = 'Checkout') {
  signIn();
  const fetchMock = stubFetch(() => json(cart));
  const user = userEvent.setup();
  const view = renderAt('/cart');
  const trigger = await screen.findByRole('button', { name: checkoutLabel });
  await user.click(trigger);
  return { user, trigger, fetchMock, view };
}

function dialogContainsFocus(dialog: HTMLElement) {
  return dialog.contains(document.activeElement);
}

describe('FE03 checkout dialog', () => {
  it('FE03 exposes a modal dialog named after its title', async () => {
    await openDialog();

    const dialog = screen.getByRole('dialog', { name: 'Confirm your order' });

    expect(dialog).toHaveAttribute('aria-modal', 'true');
  });

  it('FE03 moves focus into the dialog when it opens', async () => {
    await openDialog();

    expect(dialogContainsFocus(screen.getByRole('dialog'))).toBe(true);
  });

  it('FE03 keeps Tab and Shift+Tab inside the dialog', async () => {
    const { user } = await openDialog();
    const dialog = screen.getByRole('dialog');

    for (let i = 0; i < 5; i += 1) {
      await user.tab();
      expect(dialogContainsFocus(dialog)).toBe(true);
    }
    for (let i = 0; i < 5; i += 1) {
      await user.tab({ shift: true });
      expect(dialogContainsFocus(dialog)).toBe(true);
    }
  });

  it('FE03 closes on Escape without ordering and returns focus to Checkout', async () => {
    const { user, trigger, fetchMock } = await openDialog();

    expect(screen.getByText('Confirm your order')).toBeInTheDocument();

    await user.keyboard('{Escape}');

    expect(screen.queryByText('Confirm your order')).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(false);
  });

  it('FE03 returns focus to Checkout after Cancel', async () => {
    const { user, trigger } = await openDialog();

    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(screen.queryByText('Confirm your order')).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it('FE03 has no detectable accessibility violation while open', async () => {
    const { view } = await openDialog();

    const results = await axe(view.container);

    expect(results.violations).toEqual([]);
  });

  it('FE03 French dialog name', async () => {
    await setLanguage('fr');
    await openDialog('Passer la commande');

    expect(screen.getByRole('dialog', { name: 'Confirmez votre commande' })).toHaveAttribute('aria-modal', 'true');
  });
});
