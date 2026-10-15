import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as ordersApi from '../../src/api/orders';
import { json, renderAt, sampleOrder, setLanguage, signIn, stubFetch } from './hiddenUtils';

vi.mock('../../src/api/orders', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../src/api/orders')>();
  return { ...actual, getOrder: vi.fn(actual.getOrder) };
});

const getOrder = vi.mocked(ordersApi.getOrder);

describe('FE05 order detail', () => {
  beforeEach(() => {
    getOrder.mockReset();
    signIn();
  });

  it('FE05 getOrder is a stub that never calls the network', async () => {
    const actual = await vi.importActual<typeof import('../../src/api/orders')>('../../src/api/orders');
    const fetchMock = stubFetch(() => json(sampleOrder));

    const result = await actual.getOrder(4);

    expect(result).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('FE05 shows the order with lines and totals', async () => {
    getOrder.mockResolvedValue(sampleOrder);
    stubFetch(() => json([]));

    renderAt('/orders/4');

    expect(await screen.findByRole('heading', { level: 1, name: 'Order SL-000004' })).toBeInTheDocument();
    expect(screen.getByRole('table')).toHaveTextContent('Whiteboard');
    expect(screen.getAllByText('€128.00').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/€6\.40/)).toBeInTheDocument();
    expect(screen.getByText(/€121\.60/)).toBeInTheDocument();
    expect(getOrder).toHaveBeenCalledWith(4);
    expect(screen.getByRole('link', { name: 'Back to my orders' })).toHaveAttribute('href', '/orders');
  });

  it('FE05 announces loading', async () => {
    getOrder.mockReturnValue(new Promise(() => undefined));

    renderAt('/orders/4');

    expect(await screen.findByRole('status')).toHaveTextContent('Loading…');
  });

  it('FE05 shows not found when the client returns null', async () => {
    getOrder.mockResolvedValue(null);

    renderAt('/orders/999');

    expect(await screen.findByText('This order does not exist.')).toBeInTheDocument();
  });

  it('FE05 shows an error with retry', async () => {
    getOrder.mockRejectedValueOnce(new Error('boom')).mockResolvedValueOnce(sampleOrder);
    renderAt('/orders/4');

    expect(await screen.findByRole('alert')).toHaveTextContent('This order could not be loaded.');
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    expect(await screen.findByRole('heading', { level: 1, name: 'Order SL-000004' })).toBeInTheDocument();
  });

  it('FE05 history links to the detail screen', async () => {
    stubFetch(() => json([{ ...sampleOrder, id: 2, number: 'SL-000002' }]));

    renderAt('/orders');

    expect(await screen.findByRole('link', { name: 'View order SL-000002' })).toHaveAttribute('href', '/orders/2');
  });

  it('FE05 French texts', async () => {
    await setLanguage('fr');
    getOrder.mockResolvedValue(null);

    renderAt('/orders/999');

    expect(await screen.findByText("Cette commande n'existe pas.")).toBeInTheDocument();
  });
});
