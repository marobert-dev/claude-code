import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { page, products } from './fixtures';
import { jsonResponse, mockFetch, renderApp } from './testUtils';

describe('ProductListPage', () => {
  it('lists products with price and availability', async () => {
    mockFetch(({ path }) => (path === '/api/products/categories' ? jsonResponse(['Kitchen', 'Office']) : jsonResponse(page(products))));

    renderApp('/');

    expect(await screen.findByRole('link', { name: 'Desk Lamp' })).toHaveAttribute('href', '/products/6');
    expect(screen.getByText('€34.99')).toBeInTheDocument();
    expect(screen.getByText('Out of stock')).toBeInTheDocument();
    expect(screen.getByText('3 products')).toBeInTheDocument();
  });

  it('shows the empty state when nothing matches', async () => {
    mockFetch(({ path }) => (path === '/api/products/categories' ? jsonResponse([]) : jsonResponse(page([]))));

    renderApp('/');

    expect(await screen.findByText('No products match your search.')).toBeInTheDocument();
  });

  it('shows an error with a retry button when the catalog cannot be loaded', async () => {
    let failing = true;
    mockFetch(({ path }) => {
      if (path === '/api/products/categories') return jsonResponse([]);
      return failing ? jsonResponse({ title: 'boom' }, 500) : jsonResponse(page(products));
    });

    renderApp('/');
    expect(await screen.findByRole('alert')).toHaveTextContent('Something went wrong. Please try again.');

    failing = false;
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByText('Desk Lamp')).toBeInTheDocument();
  });

  it('sends the selected category to the API', async () => {
    const fetchMock = mockFetch(({ path }) => (path === '/api/products/categories' ? jsonResponse(['Kitchen', 'Office']) : jsonResponse(page(products))));
    renderApp('/');
    await screen.findByText('Desk Lamp');

    await userEvent.selectOptions(screen.getByLabelText('Category'), 'Office');

    await screen.findByText('Desk Lamp');
    const urls = fetchMock.mock.calls.map(([input]) => String(input));
    expect(urls).toContain('/api/products?category=Office&page=1&pageSize=12');
  });

  it('eventually searches for the typed term', async () => {
    const fetchMock = mockFetch(({ path }) => (path === '/api/products/categories' ? jsonResponse([]) : jsonResponse(page(products))));
    renderApp('/');
    await screen.findByText('Desk Lamp');

    await userEvent.type(screen.getByLabelText('Search products'), 'lamp');

    await screen.findByText('Desk Lamp');
    await vi.waitFor(() => {
      const urls = fetchMock.mock.calls.map(([input]) => String(input));
      expect(urls).toContain('/api/products?search=lamp&page=1&pageSize=12');
    });
  });
});
