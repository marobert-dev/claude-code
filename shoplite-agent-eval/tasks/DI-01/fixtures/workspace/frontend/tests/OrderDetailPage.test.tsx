import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as ordersApi from '../src/api/orders';
import { aliceOrders } from './fixtures';
import { jsonResponse, mockFetch, renderApp, signInAs } from './testUtils';

vi.mock('../src/api/orders', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../src/api/orders')>();
  return { ...actual, getOrder: vi.fn() };
});

const getOrder = vi.mocked(ordersApi.getOrder);

describe('OrderDetailPage', () => {
  beforeEach(() => {
    getOrder.mockReset();
    signInAs();
  });

  it('shows the order lines and totals', async () => {
    getOrder.mockResolvedValue(aliceOrders[0]);

    renderApp('/orders/2');

    expect(await screen.findByRole('heading', { level: 1, name: 'Order SL-000002' })).toBeInTheDocument();
    expect(screen.getByRole('rowheader', { name: 'Garden Hose' })).toBeInTheDocument();
    expect(getOrder).toHaveBeenCalledWith(2);
  });

  it('shows not found when the order does not exist', async () => {
    getOrder.mockResolvedValue(null);

    renderApp('/orders/999');

    expect(await screen.findByText('This order does not exist.')).toBeInTheDocument();
  });

  it('offers a retry when loading fails', async () => {
    getOrder.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(aliceOrders[0]);
    renderApp('/orders/2');

    await userEvent.click(await screen.findByRole('button', { name: 'Try again' }));

    expect(await screen.findByRole('heading', { level: 1, name: 'Order SL-000002' })).toBeInTheDocument();
  });

  it('is linked from the order history', async () => {
    mockFetch(() => jsonResponse(aliceOrders));

    renderApp('/orders');

    expect(await screen.findByRole('link', { name: 'View order SL-000002' })).toHaveAttribute('href', '/orders/2');
  });
});
