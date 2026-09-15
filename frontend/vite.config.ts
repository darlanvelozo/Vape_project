/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Em desenvolvimento o Vite faz proxy do /api para o Django, assim o
    // frontend usa caminho relativo igual em produção — sem CORS no meio.
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/admin': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/static': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  test: {
    // Fuso fixo: os testes de data precisam de um fuso negativo para provar
    // que data pura não escorrega para o dia anterior.
    environment: 'node',
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        // Bibliotecas grandes em chunks próprios: mudam pouco e permanecem
        // no cache do navegador entre deploys do sistema.
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          graficos: ['recharts'],
          dados: ['@tanstack/react-query'],
        },
      },
    },
  },
})
