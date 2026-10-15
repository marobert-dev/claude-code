import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { json, renderAt, sampleOrder, setLanguage, signIn, stubFetch } from './hiddenUtils';

describe('FE04 order history states', () => {
  it('FE04 announces loading while the history is pending', async () => {
    signIn();
    stubFetch(() => new Promise<Response>(() => undefined));

    renderAt('/orders');

    expect(await screen.findByRole('status')).toHaveTextContent('Loading…');
  });

  it('FE04 shows the empty message when there are no orders', async () => {
    signIn();
    stubFetch(() => json([]));

    renderAt('/orders');

    expect(await screen.findByText('You have no orders yet.')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('FE04 shows an error with retry on a server error, never the empty message', async () => {
    signIn();
    stubFetch(() => json({ status: 500, title: 'boom' }, 500));

    renderAt('/orders');

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('Your orders could not be loaded.');
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
    expect(screen.queryByText('You have no orders yet.')).not.toBeInTheDocument();
  });

  it('FE04 shows an error on a network failure', async () => {
    signIn();
    stubFetch(() => Promise.reject(new TypeError('Failed to fetch')));

    renderAt('/orders');

    expect(await screen.findByRole('alert')).toHaveTextContent('Your orders could not be loaded.');
    expect(screen.queryByText('You have no orders yet.')).not.toBeInTheDocument();
  });

  it('FE04 retry reloads and shows the orders', async () => {
    signIn();
    let failing = true;
    stubFetch(() => (failing ? json({ status: 500 }, 500) : json([sampleOrder])));
    renderAt('/orders');
    await screen.findByRole('alert');

    failing = false;
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByText(/SL-000004/)).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('FE04 French error and retry texts', async () => {
    await setLanguage('fr');
    signIn();
    stubFetch(() => json({ status: 500 }, 500));

    renderAt('/orders');

    expect(await screen.findByRole('alert')).toHaveTextContent("Vos commandes n'ont pas pu être chargées.");
    expect(screen.getByRole('button', { name: 'Réessayer' })).toBeInTheDocument();
  });
});
