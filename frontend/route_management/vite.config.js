import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const proxyTarget = globalThis?.process?.env?.VITE_API_PROXY_TARGET || 'http://backend:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react({
      babel: {
        plugins: [['babel-plugin-react-compiler']],
      },
    }),
    tailwindcss(),
  ],
  server: {
    proxy: {
      // This intercepts any request starting with '/api'
      '/api': {
        target: proxyTarget,
        changeOrigin: true,
        secure: false,
      },
      '/ws': {
        target: proxyTarget.replace('http', 'ws'),
        ws: true,
        changeOrigin: true,
        secure: false,
      },
      '/media': {
        target: proxyTarget,
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
