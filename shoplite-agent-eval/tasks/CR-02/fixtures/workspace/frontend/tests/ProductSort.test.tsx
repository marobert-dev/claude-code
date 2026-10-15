import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { page, products } from './fixtures';
import { jsonResponse, mockFetch, renderApp } from './testUtils';

describe('Product sorting', () => {
  it('sends the chosen sort order and restarts from page 1', async () => {
    const fetchMock = mockFetch(({ path }) => (path === '/api/products/categories' ? jsonResponse([]) : jsonResponse(page(products))));
    renderApp('/');
    await screen.findByText('Desk Lamp');

    await userEvent.selectOptions(screen.getByLabelText('Sort by'), 'price-desc');

    await waitFor(() => {
      const urls = fetchMock.mock.calls.map(([input]) => String(input));
      expect(urls).toContain('/api/products?page=1&pageSize=12&sort=price-desc');
    });
  });

  it('does not send the default sort order', async () => {
    const fetchMock = mockFetch(({ path }) => (path === '/api/products/categories' ? jsonResponse([]) : jsonResponse(page(products))));

    renderApp('/');
    await screen.findByText('Desk Lamp');

    const urls = fetchMock.mock.calls.map(([input]) => String(input));
    expect(urls).toContain('/api/products?page=1&pageSize=12');
  });

  it('offers the sort options in French', async () => {
    mockFetch(({ path }) => (path === '/api/products/categories' ? jsonResponse([]) : jsonResponse(page(products))));
    renderApp('/');
    await userEvent.selectOptions(screen.getByLabelText('Language'), 'fr');

    expect(await screen.findByRole('option', { name: 'Prix décroissant' })).toBeInTheDocument();
  });
});
