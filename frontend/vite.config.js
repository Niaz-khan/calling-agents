import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const API_PROXY_TARGET = process.env.VITE_API_TARGET || 'http://127.0.0.1:8000'

const API_PREFIXES = [
  '/auth',
  '/agents',
  '/deployments',
  '/services',
  '/business-config',
  '/calls',
  '/customers',
  '/appointments',
  '/phone-numbers',
  '/telephony',
  '/knowledge',
  '/analytics',
]

const proxy = Object.fromEntries(
  API_PREFIXES.map((prefix) => [prefix, { target: API_PROXY_TARGET, changeOrigin: true }])
)

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy,
  },
  preview: {
    port: 4173,
    proxy,
  },
})
