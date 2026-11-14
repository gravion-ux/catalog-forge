import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/** The dev server proxies the API and the media files to the backend. */
const API_TARGET = 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: API_TARGET, changeOrigin: true },
      '/media': { target: API_TARGET, changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
