import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { configureAxe } from 'jest-axe';
import { describe, expect, it } from 'vitest';
import { products, page } from './fixtures';
import { jsonResponse, mockFetch, renderApp, signInAs } from './testUtils';

const axe = configureAxe({ rules: { 'color-contrast': { enabled: false } } });

function mockCatalog() {
  mockFetch(({ path }) => (path === '/api/products/categories' ? jsonResponse(['Kitchen']) : jsonResponse(page(products))));
}

describe('Header', () => {
  it('shows only public links to anonymous visitors', async () => {
    mockCatalog();
    renderApp('/');

    const nav = await screen.findByRole('navigation', { name: 'Main navigation' });
    expect(nav).toHaveTextContent('Products');
    expect(nav).not.toHaveTextContent('Cart');
    expect(screen.getByRole('link', { name: 'Sign in' })).toBeInTheDocument();
  });

  it('shows the admin link to administrators only', async () => {
    mockCatalog();
    signInAs('admin');
    renderApp('/');

    expect(await screen.findByRole('link', { name: 'Admin' })).toBeInTheDocument();
    expect(screen.getByText('Signed in as admin')).toBeInTheDocument();
  });

  it('switches the interface to French', async () => {
    mockCatalog();
    renderApp('/');

    await userEvent.selectOptions(screen.getByLabelText('Language'), 'fr');

    expect(await screen.findByRole('heading', { level: 1, name: 'Produits' })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe('fr');
  });

  it('has no detectable accessibility violations on the catalog page', async () => {
    mockCatalog();
    const { container } = renderApp('/');
    await screen.findByText('Desk Lamp');

    const results = await axe(container);

    expect(results.violations).toEqual([]);
  });
});
