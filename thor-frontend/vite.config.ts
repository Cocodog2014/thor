import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxyTarget = env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000'

  const hmrHost = env.VITE_HMR_HOST
  const hmrProtocol = env.VITE_HMR_PROTOCOL
  const hmrClientPort = env.VITE_HMR_CLIENT_PORT
    ? Number(env.VITE_HMR_CLIENT_PORT)
    : undefined

  const hmrConfig = hmrHost || hmrProtocol || hmrClientPort
    ? {
        host: hmrHost,
        protocol: hmrProtocol,
        clientPort: hmrClientPort,
      }
    : undefined

  return {
    plugins: [react()],
    server: {
      port: 5173,
      host: true,
      strictPort: true,
      allowedHosts: [
        'thor.360edu.org',
        'dev-thor.360edu.org',
        'localhost',
        '127.0.0.1',
      ],
      ...(hmrConfig ? { hmr: hmrConfig } : {}),
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  }
})

