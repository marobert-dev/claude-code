import { apiRequest } from './client';
import type { Order } from './types';

export function checkout(): Promise<Order> {
  return apiRequest<Order>('/api/orders', { method: 'POST' });
}

export function listMyOrders(): Promise<Order[]> {
  return apiRequest<Order[]>('/api/orders');
}

// Stubbed per the pipeline: dev-integrator replaces it with the real GET /api/orders/{id} call (operation getOrder).
export function getOrder(id: number): Promise<Order | null> {
  void id;
  return Promise.resolve(null);
}
