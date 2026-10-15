import { ADDRESS_CHECK_SECRET_KEY, ADDRESS_CHECK_URL } from '../config/addressCheck';
import { apiRequest } from './client';
import type { Address, AddressRequest } from './types';

export function listAddresses(): Promise<Address[]> {
  return apiRequest<Address[]>('/api/addresses');
}

export function createAddress(request: AddressRequest): Promise<Address> {
  return apiRequest<Address>('/api/addresses', { method: 'POST', body: JSON.stringify(request) });
}

export async function isPostalCodeValid(postalCode: string, country: string): Promise<boolean> {
  const response = await fetch(ADDRESS_CHECK_URL, {
    method: 'POST',
    headers: { Authorization: `Bearer ${ADDRESS_CHECK_SECRET_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ postalCode, country }),
  });
  if (!response.ok) return true;
  const result = (await response.json()) as { valid?: boolean };
  return result.valid !== false;
}
