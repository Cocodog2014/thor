import React, { createContext, useContext, useMemo, useState } from 'react';

type AuthContextValue = {
  isAuthenticated: boolean;
  token: string | null;
  login: (token: string) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('thor_token'));

  const login = (newToken: string) => {
    setToken(newToken);
    localStorage.setItem('thor_token', newToken);
  };

  const logout = () => {
    setToken(null);
    localStorage.removeItem('thor_token');
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
