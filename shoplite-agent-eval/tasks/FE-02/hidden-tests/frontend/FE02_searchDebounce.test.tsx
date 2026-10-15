import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { json, renderAt, requestedUrls, setLanguage, stubFetch } from './hiddenUtils';

const lamp = { id: 6, name: 'Desk Lamp', category: 'Office', price: 34.99, inStock: true };
const knife = { id: 1, name: "Chef's Knife", category: 'Kitchen', price: 49.9, inStock: true };

function page(items: unknown[], pageNumber = 1, totalPages = 1) {
  return { items, page: pageNumber, pageSize: 12, totalCount: items.length, totalPages };
}

function productRequests(mock: ReturnType<typeof stubFetch>) {
  return requestedUrls(mock)
    .filter((url) => url.startsWith('/api/products') && !url.startsWith('/api/products/'))
    .map((url) => new URL(url, 'http://localhost').searchParams);
}

function searchTerms(mock: ReturnType<typeof stubFetch>) {
  return productRequests(mock).map((params) => params.get('search')).filter((term): term is string => !!term);
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

describe('FE02 search debounce', () => {
  it('FE02 sends one request for the full word once typing stops', async () => {
    const mock = stubFetch(({ path }) => (path === '/api/products/categories' ? json([]) : json(page([lamp, knife]))));
    renderAt('/');
    await screen.findByText('Desk Lamp');
    const user = userEvent.setup();

    await user.type(screen.getByLabelText('Search products'), 'lamp');
    expect(searchTerms(mock)).toEqual([]);
    await sleep(150);
    expect(searchTerms(mock)).toEqual([]);

    await waitFor(() => expect(searchTerms(mock)).toEqual(['lamp']), { timeout: 2000 });
    await sleep(400);
    expect(searchTerms(mock)).toEqual(['lamp']);
  });

  it('FE02 restarts from page 1 when the search changes', async () => {
    const mock = stubFetch(({ path, url }) => {
      if (path === '/api/products/categories') return json([]);
      return json(page([lamp], Number(url.searchParams.get('page') ?? 1), 3));
    });
    renderAt('/');
    await screen.findByText('Desk Lamp');
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Next' }));
    await waitFor(() => expect(productRequests(mock).some((p) => p.get('page') === '2')).toBe(true));

    await user.type(screen.getByLabelText('Search products'), 'desk');

    await waitFor(() => expect(searchTerms(mock)).toEqual(['desk']), { timeout: 2000 });
    const last = productRequests(mock).at(-1)!;
    expect(last.get('page')).toBe('1');
  });

  it('FE02 ignores the response of an older, slower search', async () => {
    let releaseSlow: (() => void) | undefined;
    stubFetch(({ path, url }) => {
      if (path === '/api/products/categories') return json([]);
      const term = url.searchParams.get('search');
      if (term === 'knife') {
        return new Promise<Response>((resolve) => {
          releaseSlow = () => resolve(json(page([knife])));
        });
      }
      return json(page(term === 'lamp' ? [lamp] : [lamp, knife]));
    });
    renderAt('/');
    await screen.findByText('Desk Lamp');
    const user = userEvent.setup();
    const input = screen.getByLabelText('Search products');

    await user.type(input, 'knife');
    await waitFor(() => expect(releaseSlow).toBeDefined(), { timeout: 2000 });
    await user.clear(input);
    await user.type(input, 'lamp');
    await sleep(700);
    releaseSlow?.();
    await sleep(100);

    expect(screen.getByText('Desk Lamp')).toBeInTheDocument();
    expect(screen.queryByText("Chef's Knife")).not.toBeInTheDocument();
  });

  it('FE02 category changes are not delayed', async () => {
    const mock = stubFetch(({ path }) => (path === '/api/products/categories' ? json(['Kitchen', 'Office']) : json(page([lamp]))));
    renderAt('/');
    await screen.findByText('Desk Lamp');
    const user = userEvent.setup();
    await waitFor(() => expect(screen.getByRole('option', { name: 'Office' })).toBeInTheDocument());

    await user.selectOptions(screen.getByLabelText('Category'), 'Office');

    await waitFor(() => expect(productRequests(mock).some((p) => p.get('category') === 'Office')).toBe(true), { timeout: 200 });
  });

  it('FE02 French label and placeholder unchanged', async () => {
    await setLanguage('fr');
    stubFetch(({ path }) => (path === '/api/products/categories' ? json([]) : json(page([lamp]))));
    renderAt('/');

    const input = await screen.findByLabelText('Rechercher des produits');

    expect(input).toHaveAttribute('placeholder', 'Rechercher par nom');
  });
});
