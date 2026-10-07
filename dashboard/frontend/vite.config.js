import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
export default defineConfig({
  // Enables React handling during Vite development/build.
  plugins: [react()],
  // Forwards /api to a locally configured gateway during Vite development. Production traffic uses
  // nginx in EKS instead.
  server: {proxy: {'/api': {target: process.env.GATEWAY_URL || 'http://127.0.0.1:8000', changeOrigin: true, rewrite: path => path.replace(/^\/api/, '')}}},
})
