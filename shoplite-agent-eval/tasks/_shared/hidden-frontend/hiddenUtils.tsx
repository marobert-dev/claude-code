import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import App from '../../src/App';
import i18n from '../../src/i18n';

// Self-contained on purpose: hidden tests must not depend on helpers the agent may have edited.
export interface HiddenRequest {
  method: string;
  path: string;
  url: URL;
  body: unknown;
  headers: Headers;
}

export function json(body: unknown, status = 200): Response {
  if (status === 204) return new Response(null, { status });
  const contentType = status >= 400 ? 'application/problem+json' : 'application/json';
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': contentType } });
}

export function stubFetch(handler: (request: HiddenRequest) => Response | Promise<Response>) {
  const mock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(typeof input === 'string' || input instanceof URL ? String(input) : input.url, 'http://localhost');
    let body: unknown;
    if (typeof init?.body === 'string') {
      try {
        body = JSON.parse(init.body);
      } catch {
        body = init.body;
      }
    }
    return handler({ method: (init?.method ?? 'GET').toUpperCase(), path: url.pathname, url, body, headers: new Headers(init?.headers) });
  });
  vi.stubGlobal('fetch', mock);
  return mock;
}

export function requestedUrls(mock: ReturnType<typeof stubFetch>): string[] {
  return mock.mock.calls.map(([input]) => (typeof input === 'string' || input instanceof URL ? String(input) : (input as Request).url));
}

export function signIn(role: 'customer' | 'admin' = 'customer', username = role === 'admin' ? 'admin' : 'alice') {
  sessionStorage.setItem(
    'shoplite.auth',
    JSON.stringify({ accessToken: 'hidden-test-token', expiresAt: '2999-01-01T00:00:00Z', username, role }),
  );
}

export async function setLanguage(language: 'en' | 'fr') {
  await i18n.changeLanguage(language);
}

export function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

export const sampleOrder = {
  id: 4,
  number: 'SL-000004',
  createdAtUtc: '2026-10-01T09:30:00Z',
  subtotal: 128,
  discount: 6.4,
  total: 121.6,
  lines: [
    { productId: 12, productName: 'Whiteboard', quantity: 2, unitPrice: 64, lineTotal: 128 },
  ],
};
