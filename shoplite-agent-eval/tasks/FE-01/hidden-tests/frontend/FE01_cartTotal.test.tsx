import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { json, renderAt, setLanguage, signIn, stubFetch } from './hiddenUtils';

type Line = { unitPrice: number; quantity: number };

function cartOf(lines: Line[]) {
  return {
    items: lines.map((line, index) => ({ id: index + 1, productId: 100 + index, productName: `Item ${index + 1}`, ...line })),
  };
}

async function totalLine(): Promise<HTMLElement> {
  return screen.findByText((_, element) => element?.tagName === 'P' && /^(Cart total|Total du panier)/.test(element.textContent ?? ''));
}

describe('FE01 cart total', () => {
  it.each([
    { lines: [{ unitPrice: 4.35, quantity: 1 }, { unitPrice: 8.2, quantity: 1 }], expected: '€12.55' },
    { lines: [{ unitPrice: 1.15, quantity: 1 }], expected: '€1.15' },
    { lines: [{ unitPrice: 19.99, quantity: 3 }], expected: '€59.97' },
    { lines: [{ unitPrice: 8.2, quantity: 1 }, { unitPrice: 1.15, quantity: 2 }], expected: '€10.50' },
    { lines: [{ unitPrice: 0.1, quantity: 3 }, { unitPrice: 0.2, quantity: 1 }], expected: '€0.50' },
  ])('FE01 total equals the sum of the line totals ($expected)', async ({ lines, expected }) => {
    signIn();
    stubFetch(() => json(cartOf(lines)));

    renderAt('/cart');

    expect(await totalLine()).toHaveTextContent(expected);
  });

  it('FE01 French total uses the French format', async () => {
    await setLanguage('fr');
    signIn();
    stubFetch(() => json(cartOf([{ unitPrice: 4.35, quantity: 1 }, { unitPrice: 8.2, quantity: 1 }])));

    renderAt('/cart');

    expect((await totalLine()).textContent).toMatch(/12,55\s€/u);
  });

  it('FE01 confirmation message shows the same total', async () => {
    signIn();
    stubFetch(() => json(cartOf([{ unitPrice: 4.35, quantity: 1 }, { unitPrice: 8.2, quantity: 1 }])));
    renderAt('/cart');

    await userEvent.click(await screen.findByRole('button', { name: 'Checkout' }));

    expect(screen.getByText(/You are about to place an order for €12\.55\./)).toBeInTheDocument();
  });
});
