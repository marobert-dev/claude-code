import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import App from '../src/App';
import { AUTH_STORAGE_KEY } from '../src/api/client';
import type { LoginResponse } from '../src/api/types';

export interface MockRequest {
  method: string;
  path: string;
  url: URL;
  body: unknown;
  headers: Headers;
}

export type MockHandler = (request: MockRequest) => Response | Promise<Response>;

export function jsonResponse(body: unknown, status = 200): Response {
  if (status === 204) return new Response(null, { status });
  const contentType = status >= 400 ? 'application/problem+json' : 'application/json';
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': contentType } });
}

export function mockFetch(handler: MockHandler) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), 'http://localhost');
    const body = typeof init?.body === 'string' ? JSON.parse(init.body) : undefined;
    return handler({ method: init?.method ?? 'GET', path: url.pathname, url, body, headers: new Headers(init?.headers) });
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

export function signInAs(role: LoginResponse['role'] = 'customer', username = role === 'admin' ? 'admin' : 'alice') {
  const session: LoginResponse = { accessToken: 'test-token', expiresAt: '2999-01-01T00:00:00Z', username, role };
  sessionStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
}

export function renderApp(path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}
