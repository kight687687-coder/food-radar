/* global process */
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react()],
    server: {
      host: true,
      port: 5173,
      strictPort: true,
      proxy: env.VITE_DEV_API_TARGET
        ? { '/backend-api': { target: env.VITE_DEV_API_TARGET, changeOrigin: true, rewrite: path => path.replace(/^\/backend-api/, '') } }
        : undefined,
    },
  }
})
