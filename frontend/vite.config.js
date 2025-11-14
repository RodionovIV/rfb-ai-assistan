import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      'react-router-dom': path.resolve(__dirname, 'src/router/react-router-dom.jsx'),
    },
  },
})
