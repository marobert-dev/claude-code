import { useCallback, useMemo, useState, type ReactNode } from 'react';
import { login } from '../api/auth';
import { AUTH_STORAGE_KEY } from '../api/client';
import { AuthContext, type Session } from './AuthContext';

function readSession(): Session | null {
  const raw = sessionStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) return null;
  try {
    const session = JSON.parse(raw) as Session;
    return new Date(session.expiresAt).getTime() > Date.now() ? session : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(readSession);

  const signIn = useCallback(async (username: string, password: string) => {
    const response = await login({ username, password });
    sessionStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(response));
    setSession(response);
  }, []);

  const signOut = useCallback(() => {
    sessionStorage.removeItem(AUTH_STORAGE_KEY);
    setSession(null);
  }, []);

  const value = useMemo(() => ({ session, signIn, signOut }), [session, signIn, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
