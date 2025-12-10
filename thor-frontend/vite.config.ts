import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    strictPort: true,
    allowedHosts: [
      'thor.360edu.org',
      'dev-thor.360edu.org',
      'localhost',
      '127.0.0.1',   // <- fix typo, was 127.0.0.0
    ],
    hmr: {
      clientPort: 443,
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',  // ALWAYS dev backend
        changeOrigin: true,
        secure: false,
      },
    },
  },
})

