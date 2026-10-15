import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { getOrder } from '../../src/api/orders';
import { json, renderAt, requestedUrls, sampleOrder, signIn, stubFetch } from './hiddenUtils';

function ordersApi(detail: (id: string) => Response | Promise<Response>) {
  return stubFetch(({ path }) => {
    const match = /^\/api\/orders\/(\d+)$/.exec(path);
    if (match) return detail(match[1]);
    if (path === '/api/orders') return json([sampleOrder]);
    if (path === '/api/products/categories') return json([]);
    return json({ items: [], page: 1, pageSize: 12, totalCount: 0, totalPages: 0 });
  });
}

describe('DI01 order detail integration', () => {
  it('DI01 getOrder calls GET /api/orders/{id} with the bearer token', async () => {
    signIn();
    const mock = ordersApi((id) => json({ ...sampleOrder, id: Number(id) }));

    const order = await getOrder(4);

    expect(order?.number).toBe('SL-000004');
    expect(requestedUrls(mock)).toContain('/api/orders/4');
    const init = mock.mock.calls.find(([input]) => String(input) === '/api/orders/4')?.[1];
    expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer hidden-test-token');
    expect((init?.method ?? 'GET').toUpperCase()).toBe('GET');
  });

  it('DI01 getOrder maps 404 to null', async () => {
    signIn();
    ordersApi(() => json({ status: 404, title: 'Resource not found', detail: 'Order 9 was not found.' }, 404));

    await expect(getOrder(9)).resolves.toBeNull();
  });

  it('DI01 page shows the order returned by the API', async () => {
    signIn();
    ordersApi(() => json(sampleOrder));

    renderAt('/orders/4');

    expect(await screen.findByRole('heading', { level: 1, name: 'Order SL-000004' })).toBeInTheDocument();
    expect(screen.getByRole('table')).toHaveTextContent('Whiteboard');
  });

  it('DI01 page shows not found on 404', async () => {
    signIn();
    ordersApi(() => json({ status: 404 }, 404));

    renderAt('/orders/9');

    expect(await screen.findByText('This order does not exist.')).toBeInTheDocument();
  });

  it('DI01 page shows the error state with retry on 500', async () => {
    signIn();
    let failing = true;
    ordersApi(() => (failing ? json({ status: 500 }, 500) : json(sampleOrder)));
    renderAt('/orders/4');

    expect(await screen.findByRole('alert')).toHaveTextContent('This order could not be loaded.');
    failing = false;
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByRole('heading', { level: 1, name: 'Order SL-000004' })).toBeInTheDocument();
  });

  it('DI01 page shows the error state on a network failure', async () => {
    signIn();
    ordersApi(() => Promise.reject(new TypeError('Failed to fetch')));

    renderAt('/orders/4');

    expect(await screen.findByRole('alert')).toHaveTextContent('This order could not be loaded.');
  });

  it('DI01 page sends the customer to sign in on 401', async () => {
    signIn();
    ordersApi(() => json({ status: 401 }, 401));

    renderAt('/orders/4');

    expect(await screen.findByRole('heading', { level: 1, name: 'Sign in' })).toBeInTheDocument();
    expect(sessionStorage.getItem('shoplite.auth')).toBeNull();
  });
});
