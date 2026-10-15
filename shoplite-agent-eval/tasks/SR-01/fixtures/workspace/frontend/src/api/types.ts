export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  accessToken: string;
  expiresAt: string;
  username: string;
  role: 'customer' | 'admin';
}

export interface ProductSummary {
  id: number;
  name: string;
  category: string;
  price: number;
  inStock: boolean;
}

export interface Product {
  id: number;
  name: string;
  description: string;
  category: string;
  price: number;
  stock: number;
}

export interface ProductUpsertRequest {
  name: string;
  description: string;
  category: string;
  price: number;
  stock: number;
}

export interface PagedResult<T> {
  items: T[];
  page: number;
  pageSize: number;
  totalCount: number;
  totalPages: number;
}

export interface ProductQuery {
  search?: string;
  category?: string;
  page?: number;
  pageSize?: number;
}

export interface CartItem {
  id: number;
  productId: number;
  productName: string;
  unitPrice: number;
  quantity: number;
}

export interface Cart {
  items: CartItem[];
}

export interface AddCartItemRequest {
  productId: number;
  quantity: number;
}

export interface OrderLine {
  productId: number;
  productName: string;
  quantity: number;
  unitPrice: number;
  lineTotal: number;
}

export interface Order {
  id: number;
  number: string;
  createdAtUtc: string;
  subtotal: number;
  discount: number;
  total: number;
  lines: OrderLine[];
}

export interface ProblemDetails {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  errors?: Record<string, string[]>;
}

export interface AddressRequest {
  label: string;
  line1: string;
  city: string;
  postalCode: string;
  country: string;
}

export interface Address extends AddressRequest {
  id: number;
}
