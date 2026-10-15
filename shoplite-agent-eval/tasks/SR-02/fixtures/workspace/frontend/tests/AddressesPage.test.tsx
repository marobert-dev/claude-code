import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { jsonResponse, mockFetch, renderApp, signInAs } from './testUtils';

describe('AddressesPage', () => {
  it('lists the saved addresses', async () => {
    signInAs();
    mockFetch(() => jsonResponse([{ id: 1, label: 'Home', line1: '12 rue des Lilas', city: 'Lyon', postalCode: '69003', country: 'FR' }]));

    renderApp('/addresses');

    expect(await screen.findByText('Home')).toBeInTheDocument();
  });

  it('shows the empty state', async () => {
    signInAs();
    mockFetch(() => jsonResponse([]));

    renderApp('/addresses');

    expect(await screen.findByText('You have no saved addresses.')).toBeInTheDocument();
  });
});
