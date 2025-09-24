import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Proxy API calls from the frontend dev server to Django backend
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // Keep the /api prefix (Django already serves under /api)
        // If your backend path changes, you can rewrite here
        // rewrite: (path) => path.replace(/^\/api/, '/api'),
      },
    },
  },
})
