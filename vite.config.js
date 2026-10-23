import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// בפיתוח: Vite על 5335, ה-API (uvicorn) על 8115
const backend = 'http://127.0.0.1:8115'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5335,
    proxy: {
      '/api': backend,
      '/files': backend,
      '/auth': backend,
      '/login': backend,
      '/logout': backend,
      '/emergency-login': backend,
    },
  },
})
