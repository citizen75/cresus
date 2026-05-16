import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const API_HOST = process.env.API_HOST || 'localhost'
const API_PORT = process.env.API_PORT || '8000'
const FRONT_PORT = parseInt(process.env.FRONT_PORT || '5173')

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  define: {
    // Expose environment variables to frontend code
    __API_HOST__: JSON.stringify(API_HOST),
    __API_PORT__: JSON.stringify(API_PORT),
  },
  server: {
    port: FRONT_PORT,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: `http://${API_HOST}:${API_PORT}`,
        changeOrigin: true,
      },
    },
  },
})
