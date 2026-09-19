import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '')
  const proxyTarget = env.VITE_DEV_API_TARGET || 'http://127.0.0.1:8000'

  return {
    plugins: [react()],
    server: {
      port: 3000,
      proxy: {
        '/check': { target: proxyTarget, changeOrigin: true },
        '/investigate': { target: proxyTarget, changeOrigin: true },
        '/sessions': { target: proxyTarget, changeOrigin: true },
        '/reports': { target: proxyTarget, changeOrigin: true },
        '/uploads': { target: proxyTarget, changeOrigin: true },
        '/batches': { target: proxyTarget, changeOrigin: true },
        '/manufacturers': { target: proxyTarget, changeOrigin: true },
        '/admin': { target: proxyTarget, changeOrigin: true },
        '/health': { target: proxyTarget, changeOrigin: true },
      },
    },
  };
});

