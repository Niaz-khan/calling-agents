import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const API_PROXY_TARGET = process.env.VITE_API_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/auth': API_PROXY_TARGET,
      '/agents': API_PROXY_TARGET,
      '/calls': API_PROXY_TARGET,
      '/customers': API_PROXY_TARGET,
      '/appointments': API_PROXY_TARGET,
      '/phone-numbers': API_PROXY_TARGET,
      '/knowledge': API_PROXY_TARGET,
      '/analytics': API_PROXY_TARGET,
    },
  },
})