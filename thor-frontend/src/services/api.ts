import axios from 'axios';

// Create axios instance with base configuration
// Use a relative baseURL so Vite proxy (dev) and same-origin (prod) both work without CORS issues
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 seconds timeout
});

// Public endpoints that don't require authentication
const PUBLIC_ENDPOINTS = [
  '/global-markets/markets',
  '/quotes',
  '/vwap',
  '/account-statement/summary',
];

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Skip auth headers for public endpoints
    const isPublic = PUBLIC_ENDPOINTS.some(endpoint => 
      config.url?.startsWith(endpoint)
    );
    
    if (!isPublic) {
      // Attach JWT access token if present
      try {
        const token = localStorage.getItem('thor_access_token');
        if (token) {
          (config.headers = config.headers || {}).Authorization = `Bearer ${token}`;
        }
      } catch {
        // Ignore storage access errors (private mode, disabled storage)
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    
    // Check if this is a public endpoint - don't try auth refresh
    const isPublic = PUBLIC_ENDPOINTS.some(endpoint => 
      originalRequest.url?.startsWith(endpoint)
    );
    
    // If 401 and we haven't tried refreshing yet and it's not a public endpoint
    if (error.response?.status === 401 && !originalRequest._retry && !isPublic) {
      originalRequest._retry = true;
      
      try {
        // Try to refresh the token
        const refreshToken = localStorage.getItem('thor_refresh_token');
        if (refreshToken) {
          const { data } = await axios.post('/api/users/token/refresh/', {
            refresh: refreshToken
          });
          
          // Store new access token
          localStorage.setItem('thor_access_token', data.access);
          
          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${data.access}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, clear tokens and redirect to login
        try {
          localStorage.removeItem('thor_access_token');
          localStorage.removeItem('thor_refresh_token');
        } catch {
          // Swallow storage removal errors
        }
        // Don't redirect on public endpoint failures
        if (!isPublic) {
          window.location.href = '/auth/login';
        }
        return Promise.reject(refreshError);
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