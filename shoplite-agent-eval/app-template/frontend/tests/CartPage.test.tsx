import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { aliceOrders, cartWithTwoItems } from './fixtures';
import { jsonResponse, mockFetch, renderApp, signInAs } from './testUtils';

describe('CartPage', () => {
  it('redirects anonymous visitors to the sign-in page', async () => {
    mockFetch(() => jsonResponse({}));

    renderApp('/cart');

    expect(await screen.findByRole('heading', { level: 1, name: 'Sign in' })).toBeInTheDocument();
  });

  it('lists cart items with line totals and the cart total', async () => {
    signInAs();
    mockFetch(() => jsonResponse(cartWithTwoItems));

    renderApp('/cart');

    const notebookRow = (await screen.findByRole('rowheader', { name: 'Notebook A5' })).closest('tr')!;
    expect(within(notebookRow).getByText('€13.00')).toBeInTheDocument();
    expect(screen.getByTestId('cart-total')).toHaveTextContent('€23.00');
  });

  it('shows the empty state for an empty cart', async () => {
    signInAs();
    mockFetch(() => jsonResponse({ items: [] }));

    renderApp('/cart');

    expect(await screen.findByText('Your cart is empty.')).toBeInTheDocument();
  });

  it('updates a quantity through the API', async () => {
    signInAs();
    const fetchMock = mockFetch(({ method, body }) => {
      if (method === 'PUT') {
        const quantity = (body as { quantity: number }).quantity;
        return jsonResponse({ items: [{ ...cartWithTwoItems.items[0], quantity }, cartWithTwoItems.items[1]] });
      }
      return jsonResponse(cartWithTwoItems);
    });
    renderApp('/cart');

    const input = await screen.findByLabelText('Quantity for Notebook A5');
    await userEvent.clear(input);
    await userEvent.type(input, '3');
    await userEvent.click(within(input.closest('td')!).getByRole('button', { name: 'Update' }));

    expect(await screen.findByTestId('cart-total')).toHaveTextContent('€29.50');
    const put = fetchMock.mock.calls.find(([, init]) => init?.method === 'PUT');
    expect(String(put?.[0])).toBe('/api/cart/items/10');
  });

  it('places the order after confirmation and shows it in the order history', async () => {
    signInAs();
    mockFetch(({ method, path }) => {
      if (path === '/api/orders' && method === 'POST') return jsonResponse({ ...aliceOrders[0], number: 'SL-000004' }, 201);
      if (path === '/api/orders') return jsonResponse(aliceOrders);
      return jsonResponse(cartWithTwoItems);
    });
    renderApp('/cart');

    await userEvent.click(await screen.findByRole('button', { name: 'Checkout' }));
    expect(screen.getByText('You are about to place an order for €23.00.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Place order' }));

    expect(await screen.findByText('Order SL-000004 has been placed.')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: 'My orders' })).toBeInTheDocument();
  });

  it('closes the confirmation without ordering when cancelled', async () => {
    signInAs();
    const fetchMock = mockFetch(() => jsonResponse(cartWithTwoItems));
    renderApp('/cart');

    await userEvent.click(await screen.findByRole('button', { name: 'Checkout' }));
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(screen.queryByText('Confirm your order')).not.toBeInTheDocument();
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'POST')).toBe(false);
  });
});
