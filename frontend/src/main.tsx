import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import { App } from './App'
import './index.css'
import { ProvedorAutenticacao } from './lib/auth'

const clienteQuery = new QueryClient({
  defaultOptions: {
    queries: {
      // Conexão de loja costuma ser instável: uma tentativa extra ajuda,
      // três só atrasam o erro na tela.
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={clienteQuery}>
      <BrowserRouter>
        <ProvedorAutenticacao>
          <App />
        </ProvedorAutenticacao>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
