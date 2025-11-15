/* eslint-env node */

import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const rootDir = path.dirname(fileURLToPath(import.meta.url))

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, rootDir, '')

  const host = env.VITE_FRONTEND_HOST || '0.0.0.0'
  const port = Number.parseInt(env.VITE_FRONTEND_PORT || '5173', 10)

  return {
    plugins: [react()],
    resolve: {
      alias: {
        'react-router-dom': path.resolve(rootDir, 'src/router/react-router-dom.jsx'),
      },
    },
    server: {
      host,
      port,
    },
  }
})
