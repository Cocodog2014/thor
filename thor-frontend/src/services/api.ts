import axios, { AxiosHeaders } from 'axios';
import { AUTH_ACCESS_TOKEN_KEY, AUTH_REFRESH_TOKEN_KEY } from '../constants/storageKeys';

/**
 * Resolve API base URL in a way that works for:
 * - Local dev (localhost:5173 → localhost:8000)
 * - Cloudflare tunnel (thor.360edu.org → /api)
 * - Docker (using VITE_API_BASE_URL inside containers)
 */
const API_BASE_URL = (() => {
  const envUrl = import.meta.env.VITE_API_BASE_URL?.trim();
  if (envUrl) {
    return envUrl;
  }

  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') {
      return 'http://localhost:8000/api';
    }
  }

  return '/api';
})();

// Create axios instance with base configuration
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 seconds timeout
});

const readStoredToken = (key: string): string | null => {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
};

type RefreshQueueItem = {
  resolve: (accessToken: string) => void;
  reject: (error: unknown) => void;
};

type RetriableRequestConfig = {
  _retry?: boolean;
  url?: string;
  headers?: unknown;
};

let isRefreshing = false;
let refreshQueue: RefreshQueueItem[] = [];

const setRequestAuthHeader = (requestConfig: RetriableRequestConfig, accessToken: string) => {
  const headerValue = `Bearer ${accessToken}`;

  if (requestConfig.headers instanceof AxiosHeaders) {
    requestConfig.headers.set('Authorization', headerValue);
    return;
  }

  const currentHeaders: Record<string, unknown> =
    requestConfig.headers && typeof requestConfig.headers === 'object'
      ? (requestConfig.headers as Record<string, unknown>)
      : {};

  requestConfig.headers = {
    ...currentHeaders,
    Authorization: headerValue,
  };
};

const flushRefreshQueue = (error: unknown, accessToken: string | null) => {
  const queue = refreshQueue;
  refreshQueue = [];

  queue.forEach(({ resolve, reject }) => {
    if (accessToken) {
      resolve(accessToken);
    } else {
      reject(error);
    }
  });
};

export const setAuthHeader = (token: string | null) => {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
};

// Public endpoints that don't require authentication
const PUBLIC_ENDPOINTS = [
  '/global-markets/markets',
  '/global-markets/stats',
  '/quotes',
  '/vwap',
];

// Request interceptor
api.interceptors.request.use(
  (config) => {
    const isPublic = PUBLIC_ENDPOINTS.some(endpoint =>
      config.url?.startsWith(endpoint)
    );

    if (isPublic && config.headers?.Authorization) {
      delete config.headers.Authorization;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config as RetriableRequestConfig | undefined;
    if (!originalRequest) {
      return Promise.reject(error);
    }
    
    // Check if this is a public endpoint - don't try auth refresh
    const isPublic = PUBLIC_ENDPOINTS.some(endpoint => 
      originalRequest.url?.startsWith(endpoint)
    );
    
    // If 401 and we haven't tried refreshing yet and it's not a public endpoint
    // NOTE: Use a single refresh lock + queue so we don't spam refresh calls during app boot.
    if (error.response?.status === 401 && !isPublic) {
      if (originalRequest._retry) {
        return Promise.reject(error);
      }
      originalRequest._retry = true;

      const refreshToken = readStoredToken(AUTH_REFRESH_TOKEN_KEY);
      if (!refreshToken) {
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          refreshQueue.push({
            resolve: (accessToken) => {
              setRequestAuthHeader(originalRequest, accessToken);
              resolve(api(originalRequest));
            },
            reject,
          });
        });
      }

      isRefreshing = true;

      try {
        const { data } = await axios.post(`${API_BASE_URL}/users/token/refresh/`, {
          refresh: refreshToken,
        });

        const newAccessToken = data?.access as string | undefined;
        if (!newAccessToken) {
          throw new Error('Missing access token in refresh response');
        }

        localStorage.setItem(AUTH_ACCESS_TOKEN_KEY, newAccessToken);
        setAuthHeader(newAccessToken);
        flushRefreshQueue(null, newAccessToken);

        setRequestAuthHeader(originalRequest, newAccessToken);
        return api(originalRequest);
      } catch (refreshError) {
        flushRefreshQueue(refreshError, null);

        // Refresh failed, clear tokens and redirect to login
        try {
          localStorage.removeItem(AUTH_ACCESS_TOKEN_KEY);
          localStorage.removeItem(AUTH_REFRESH_TOKEN_KEY);
          setAuthHeader(null);
        } catch {
          // Swallow storage removal errors
        }
        // Don't redirect on public endpoint failures
        if (!isPublic) {
          window.location.href = '/auth/login';
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    
    // Handle other errors
    if (error.response?.status === 500) {
      console.error('Server error');
    }
    return Promise.reject(error);
  }
);

export default api;