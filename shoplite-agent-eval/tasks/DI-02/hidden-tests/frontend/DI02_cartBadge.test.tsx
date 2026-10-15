import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { getCartSummary } from '../../src/api/cart';
import { json, renderAt, requestedUrls, setLanguage, signIn, stubFetch } from './hiddenUtils';

const emptyCatalog = { items: [], page: 1, pageSize: 12, totalCount: 0, totalPages: 0 };

function api(summary: () => Response | Promise<Response>) {
  return stubFetch(({ path }) => {
    if (path === '/api/cart/summary') return summary();
    if (path === '/api/products/categories') return json([]);
    return json(emptyCatalog);
  });
}

describe('DI02 cart badge integration', () => {
  it('DI02 getCartSummary calls GET /api/cart/summary with the bearer token', async () => {
    signIn();
    const mock = api(() => json({ itemCount: 3, total: 76.48 }));

    const summary = await getCartSummary();

    expect(summary).toEqual({ itemCount: 3, total: 76.48 });
    const init = mock.mock.calls.find(([input]) => String(input) === '/api/cart/summary')?.[1];
    expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer hidden-test-token');
  });

  it('DI02 header shows the unit count from the API', async () => {
    signIn();
    api(() => json({ itemCount: 3, total: 76.48 }));

    renderAt('/');

    expect(await screen.findByRole('link', { name: 'Cart (3)' })).toHaveAttribute('href', '/cart');
  });

  it('DI02 header shows the French unit count', async () => {
    await setLanguage('fr');
    signIn();
    api(() => json({ itemCount: 3, total: 76.48 }));

    renderAt('/');

    expect(await screen.findByRole('link', { name: 'Panier (3)' })).toBeInTheDocument();
  });

  it('DI02 header shows the plain link for an empty cart', async () => {
    signIn();
    const mock = api(() => json({ itemCount: 0, total: 0 }));

    renderAt('/');

    await waitFor(() => expect(requestedUrls(mock)).toContain('/api/cart/summary'));
    expect(await screen.findByRole('link', { name: 'Cart' })).toBeInTheDocument();
  });

  it('DI02 header survives a failing summary request', async () => {
    signIn();
    const mock = api(() => json({ status: 500 }, 500));

    renderAt('/');

    await waitFor(() => expect(requestedUrls(mock)).toContain('/api/cart/summary'));
    expect(await screen.findByRole('link', { name: 'Cart' })).toBeInTheDocument();
  });

  it('DI02 anonymous visitors never request the summary', async () => {
    const mock = api(() => json({ itemCount: 1, total: 1 }));

    renderAt('/');

    await screen.findByRole('link', { name: 'Sign in' });
    expect(requestedUrls(mock)).not.toContain('/api/cart/summary');
  });
});
