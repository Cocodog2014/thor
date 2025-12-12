import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { setAuthHeader } from '../services/api';
import { AUTH_ACCESS_TOKEN_KEY, AUTH_REFRESH_TOKEN_KEY } from '../constants/storageKeys';

type AuthContextValue = {
  isAuthenticated: boolean;
  token: string | null;
  login: (accessToken: string, refreshToken?: string | null) => void;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const readStoredAccessToken = () => {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    return localStorage.getItem(AUTH_ACCESS_TOKEN_KEY);
  } catch {
    return null;
  }
};

const persistTokens = (accessToken: string, refreshToken?: string | null) => {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    localStorage.setItem(AUTH_ACCESS_TOKEN_KEY, accessToken);
    if (refreshToken) {
      localStorage.setItem(AUTH_REFRESH_TOKEN_KEY, refreshToken);
    } else {
      localStorage.removeItem(AUTH_REFRESH_TOKEN_KEY);
    }
  } catch {
    // Ignore storage issues (private mode, etc.)
  }
};

const clearStoredTokens = () => {
  if (typeof window === 'undefined') {
    return;
  }
  try {
    localStorage.removeItem(AUTH_ACCESS_TOKEN_KEY);
    localStorage.removeItem(AUTH_REFRESH_TOKEN_KEY);
  } catch {
    // Ignore storage errors
  }
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => {
    return readStoredAccessToken();
  });

  useEffect(() => {
    setAuthHeader(token);
  }, [token]);

  const login = (accessToken: string, refreshToken?: string | null) => {
    setToken(accessToken);
    persistTokens(accessToken, refreshToken);
  };

  const logout = () => {
    setToken(null);
    clearStoredTokens();
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
