import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from '../api/client';

interface AuthState {
  role: string; name: string; email: string; loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState({ role: '', name: '', email: '' });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.me().then(u => setUser(u)).catch(() => setUser({ role: '', name: '', email: '' })).finally(() => setLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    const u = await api.login(email, password);
    setUser(u);
  };

  const logout = async () => {
    await api.logout();
    setUser({ role: '', name: '', email: '' });
  };

  return (
    <AuthContext.Provider value={{ ...user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
