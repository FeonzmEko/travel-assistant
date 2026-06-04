import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import { getProfile, type UserProfile } from '@/api/user';

interface AuthState {
  token: string | null;
  user: UserProfile | null;
  loading: boolean;
  setToken: (token: string | null) => void;
  refreshUser: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => localStorage.getItem('token'));
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(!!token);

  const setToken = useCallback((t: string | null) => {
    if (t) {
      localStorage.setItem('token', t);
    } else {
      localStorage.removeItem('token');
    }
    setTokenState(t);
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const res = await getProfile();
      setUser(res.data);
    } catch {
      setUser(null);
      setToken(null);
    }
  }, [setToken]);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, [setToken]);

  useEffect(() => {
    if (token) {
      setLoading(true);
      refreshUser().finally(() => setLoading(false));
    } else {
      setUser(null);
      setLoading(false);
    }
  }, [token, refreshUser]);

  return (
    <AuthContext.Provider value={{ token, user, loading, setToken, refreshUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
