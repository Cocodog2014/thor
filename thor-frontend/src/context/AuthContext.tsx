import React, { createContext, useContext, useMemo, useState } from 'react';

type AuthContextValue = {
  isAuthenticated: boolean;
  token: string | null;
  login: (token: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

// Use the same key as the rest of the app ('thor_access_token') to stay consistent
const ACCESS_KEY = 'thor_access_token';
const REFRESH_KEY = 'thor_refresh_token';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => {
    try {
      return localStorage.getItem(ACCESS_KEY);
    } catch {
      return null;
    }
  });

  const login = (newToken: string) => {
    setToken(newToken);
    try {
      localStorage.setItem(ACCESS_KEY, newToken);
    } catch {}
  };

  const logout = () => {
    setToken(null);
    try {
      localStorage.removeItem(ACCESS_KEY);
      localStorage.removeItem(REFRESH_KEY);
    } catch {}
  };

  // Keep a boolean for convenience
  const isAuthenticated = !!token;

  const value = useMemo(() => ({ isAuthenticated, token, login, logout }), [isAuthenticated, token]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
};
