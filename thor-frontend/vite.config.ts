import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  // Use the same backend host the React app will call in production,
  // defaulting to the legacy localhost:8000 dev server.
  const apiBase = (env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api').replace(/\/+$/, '')
  const proxyTarget = apiBase.endsWith('/api') ? apiBase.slice(0, -4) : apiBase

  return {
    plugins: [react()],
    server: {
      port: 5173,
      host: true, // Listen on all addresses (0.0.0.0)
      // Allow access from Cloudflare tunnel
      allowedHosts: [
        'thor.360edu.org',
        'dev-thor.360edu.org',
        'localhost',
        '127.0.0.1',
      ],
      hmr: {
        clientPort: 443,
      },
      // Proxy API calls from the frontend dev server to Django backend
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
