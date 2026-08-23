import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ready': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            {
              name: 'react-vendor',
              test: /node_modules[/\\](react|react-dom|react-router|react-router-dom|scheduler)/,
            },
            {
              name: 'data-vendor',
              test: /node_modules[/\\](@tanstack|axios|sonner)/,
            },
            {
              name: 'form-vendor',
              test: /node_modules[/\\](react-hook-form|zod|@hookform|class-variance-authority|@radix-ui)/,
            },
          ],
        },
      },
    },
  },
})