import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { page, products } from './fixtures';
import { jsonResponse, mockFetch, renderApp, signInAs } from './testUtils';

describe('Cart badge', () => {
  it('shows the plain cart link while no summary is available', async () => {
    signInAs();
    mockFetch(({ path }) => (path === '/api/products/categories' ? jsonResponse([]) : jsonResponse(page(products))));

    renderApp('/');

    expect(await screen.findByRole('link', { name: 'Cart' })).toHaveAttribute('href', '/cart');
  });
});
