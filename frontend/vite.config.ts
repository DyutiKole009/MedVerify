import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/check': 'http://localhost:8000',
      '/investigate': 'http://localhost:8000',
      '/sessions': 'http://localhost:8000',
      '/reports': 'http://localhost:8000',
      '/uploads': 'http://localhost:8000',
      '/batches': 'http://localhost:8000',
      '/manufacturers': 'http://localhost:8000',
      '/admin': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    }
  }
})
