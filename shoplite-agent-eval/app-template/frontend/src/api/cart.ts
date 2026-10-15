import { apiRequest } from './client';
import type { AddCartItemRequest, Cart } from './types';

export function getCart(): Promise<Cart> {
  return apiRequest<Cart>('/api/cart');
}

export function addCartItem(request: AddCartItemRequest): Promise<Cart> {
  return apiRequest<Cart>('/api/cart/items', { method: 'POST', body: JSON.stringify(request) });
}

export function updateCartItem(itemId: number, quantity: number): Promise<Cart> {
  return apiRequest<Cart>(`/api/cart/items/${itemId}`, { method: 'PUT', body: JSON.stringify({ quantity }) });
}

export function removeCartItem(itemId: number): Promise<void> {
  return apiRequest<void>(`/api/cart/items/${itemId}`, { method: 'DELETE' });
}
