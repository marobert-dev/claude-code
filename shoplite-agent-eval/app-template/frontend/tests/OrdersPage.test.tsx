import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { aliceOrders } from './fixtures';
import { jsonResponse, mockFetch, renderApp, signInAs } from './testUtils';

describe('OrdersPage', () => {
  it('lists past orders with their lines and totals', async () => {
    signInAs();
    mockFetch(() => jsonResponse(aliceOrders));

    renderApp('/orders');

    expect(await screen.findByRole('heading', { level: 2, name: 'Order SL-000002' })).toBeInTheDocument();
    expect(screen.getByText('Placed on Sep 20, 2026')).toBeInTheDocument();
    expect(screen.getByText('1 × Garden Hose — €32.00')).toBeInTheDocument();
    expect(screen.getByText('Total: €32.00')).toBeInTheDocument();
  });

  it('shows the empty state when there are no orders', async () => {
    signInAs();
    mockFetch(() => jsonResponse([]));

    renderApp('/orders');

    expect(await screen.findByText('You have no orders yet.')).toBeInTheDocument();
  });
});
