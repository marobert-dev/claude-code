import { apiRequest } from './client';
import type { Order } from './types';

export function checkout(): Promise<Order> {
  return apiRequest<Order>('/api/orders', { method: 'POST' });
}

export function listMyOrders(): Promise<Order[]> {
  return apiRequest<Order[]>('/api/orders');
}
