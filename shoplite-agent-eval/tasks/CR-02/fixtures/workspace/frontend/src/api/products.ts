import { apiRequest } from './client';
import type { PagedResult, Product, ProductQuery, ProductSort, ProductSummary, ProductUpsertRequest } from './types';

export const DEFAULT_SORT: ProductSort = 'name';
export const PRODUCT_SORTS: readonly ProductSort[] = ['name', 'price-asc', 'price-desc'];

export function listProducts(query: ProductQuery): Promise<PagedResult<ProductSummary>> {
  const params = new URLSearchParams();
  if (query.search) params.set('search', query.search);
  if (query.category) params.set('category', query.category);
  if (query.page) params.set('page', String(query.page));
  if (query.pageSize) params.set('pageSize', String(query.pageSize));
  if (query.sort && query.sort !== DEFAULT_SORT) params.set('sort', query.sort);
  const suffix = params.size > 0 ? `?${params.toString()}` : '';
  return apiRequest<PagedResult<ProductSummary>>(`/api/products${suffix}`);
}

export function listCategories(): Promise<string[]> {
  return apiRequest<string[]>('/api/products/categories');
}

export function getProduct(id: number): Promise<Product> {
  return apiRequest<Product>(`/api/products/${id}`);
}

export function createProduct(request: ProductUpsertRequest): Promise<Product> {
  return apiRequest<Product>('/api/products', { method: 'POST', body: JSON.stringify(request) });
}

export function updateProduct(id: number, request: ProductUpsertRequest): Promise<Product> {
  return apiRequest<Product>(`/api/products/${id}`, { method: 'PUT', body: JSON.stringify(request) });
}
