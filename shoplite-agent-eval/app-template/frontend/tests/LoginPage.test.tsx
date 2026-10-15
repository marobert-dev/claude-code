import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { page, products } from './fixtures';
import { jsonResponse, mockFetch, renderApp } from './testUtils';

describe('LoginPage', () => {
  it('flags empty fields without calling the API', async () => {
    const fetchMock = mockFetch(() => jsonResponse({}));
    renderApp('/login');

    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(screen.getAllByText('This field is required.')).toHaveLength(2);
    expect(screen.getByLabelText('Username')).toHaveAttribute('aria-invalid', 'true');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('shows an error for invalid credentials', async () => {
    mockFetch(() => jsonResponse({ status: 401, detail: 'Invalid username or password.' }, 401));
    renderApp('/login');

    await userEvent.type(screen.getByLabelText('Username'), 'alice');
    await userEvent.type(screen.getByLabelText('Password'), 'wrong');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid username or password.');
  });

  it('signs in and returns to the catalog', async () => {
    mockFetch(({ path }) => {
      if (path === '/api/auth/login') {
        return jsonResponse({ accessToken: 'abc', expiresAt: '2999-01-01T00:00:00Z', username: 'alice', role: 'customer' });
      }
      if (path === '/api/products/categories') return jsonResponse([]);
      return jsonResponse(page(products));
    });
    renderApp('/login');

    await userEvent.type(screen.getByLabelText('Username'), 'alice');
    await userEvent.type(screen.getByLabelText('Password'), 'Alice123!');
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByText('Signed in as alice')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1, name: 'Products' })).toBeInTheDocument();
  });

  it('sends the interface language to the API', async () => {
    const fetchMock = mockFetch(() => jsonResponse({ status: 401 }, 401));
    renderApp('/login');
    await userEvent.selectOptions(screen.getByLabelText('Language'), 'fr');

    await userEvent.type(screen.getByLabelText("Nom d'utilisateur"), 'alice');
    await userEvent.type(screen.getByLabelText('Mot de passe'), 'x');
    await userEvent.click(screen.getByRole('button', { name: 'Se connecter' }));

    await screen.findByRole('alert');
    const headers = new Headers(fetchMock.mock.calls[0][1]?.headers);
    expect(headers.get('Accept-Language')).toBe('fr');
  });
});
