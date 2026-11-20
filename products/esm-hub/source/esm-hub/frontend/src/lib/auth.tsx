import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, getToken, setToken, setUnauthorizedHandler } from './api';
import { decodeToken, isExpired, type Claims } from './jwt';

interface AuthState {
  user: Claims | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthState | null>(null);

function initialUser(): Claims | null {
  const c = decodeToken(getToken());
  if (isExpired(c)) { setToken(null); return null; }
  return c;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Claims | null>(initialUser);
  const qc = useQueryClient();

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    qc.clear();
  }, [qc]);

  useEffect(() => { setUnauthorizedHandler(logout); }, [logout]);

  const login = useCallback(async (email: string, password: string) => {
    const r = await api<{ accessToken: string }>('/auth/login', { body: { email, password }, auth: false });
    const c = decodeToken(r.accessToken);
    if (!c) throw new Error('The server returned an unreadable token.');
    qc.clear();
    setToken(r.accessToken);
    setUser(c);
  }, [qc]);

  const value = useMemo(() => ({ user, login, logout }), [user, login, logout]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAuth must be used inside AuthProvider');
  return v;
}

export function useUser(): Claims {
  const { user } = useAuth();
  if (!user) throw new Error('No signed-in user');
  return user;
}
