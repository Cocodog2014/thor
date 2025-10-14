import axios from 'axios';

// Create axios instance with base configuration
const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 seconds timeout
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    // Attach token if present
    try {
      const token = localStorage.getItem('thor_token');
      if (token) {
        (config.headers = config.headers || {}).Authorization = `Bearer ${token}`;
      }
    } catch {}
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
  (error) => {
    // Handle common errors
    if (error.response?.status === 401) {
      // Handle unauthorized access
      console.error('Unauthorized access');
    } else if (error.response?.status === 500) {
      console.error('Server error');
    }
    return Promise.reject(error);
  }
);

export default api;