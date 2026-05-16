import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import fs from 'fs'
import os from 'os'

// Load .cresus/.env file
function loadEnvFile() {
  const envPath = path.join(os.homedir(), '.cresus', '.env')
  const env: Record<string, string> = {}

  if (fs.existsSync(envPath)) {
    const content = fs.readFileSync(envPath, 'utf-8')
    content.split('\n').forEach(line => {
      line = line.trim()
      if (!line || line.startsWith('#')) return
      const [key, value] = line.split('=')
      if (key && value) {
        env[key.trim()] = value.trim()
      }
    })
  }
  return env
}

const envConfig = loadEnvFile()
const API_HOST = envConfig.API_HOST || process.env.API_HOST || 'localhost'
const API_PORT = envConfig.API_PORT || process.env.API_PORT || '8000'
const FRONT_PORT = parseInt(envConfig.FRONT_PORT || process.env.FRONT_PORT || '5173')

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
