import type { Cart, Order, PagedResult, ProductSummary } from '../src/api/types';

export const products: ProductSummary[] = [
  { id: 1, name: "Chef's Knife", category: 'Kitchen', price: 49.9, inStock: true },
  { id: 6, name: 'Desk Lamp', category: 'Office', price: 34.99, inStock: true },
  { id: 18, name: 'Bird Feeder', category: 'Garden', price: 18.6, inStock: false },
];

export function page(items: ProductSummary[], pageNumber = 1, totalPages = 1): PagedResult<ProductSummary> {
  return { items, page: pageNumber, pageSize: 12, totalCount: items.length, totalPages };
}

export const cartWithTwoItems: Cart = {
  items: [
    { id: 10, productId: 7, productName: 'Notebook A5', unitPrice: 6.5, quantity: 2 },
    { id: 11, productId: 17, productName: 'Garden Gloves', unitPrice: 10, quantity: 1 },
  ],
};

export const aliceOrders: Order[] = [
  {
    id: 2,
    number: 'SL-000002',
    createdAtUtc: '2026-09-20T16:40:00Z',
    subtotal: 32,
    discount: 0,
    total: 32,
    lines: [{ productId: 13, productName: 'Garden Hose', quantity: 1, unitPrice: 32, lineTotal: 32 }],
  },
];
