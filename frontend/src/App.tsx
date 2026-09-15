import { Suspense, lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'

import { Layout } from './componentes/Layout'
import { Carregando } from './componentes/ui'
import { useAutenticacao } from './lib/auth'
import { Entrar } from './paginas/Entrar'
import { PDV } from './paginas/PDV'
import { Vitrine } from './paginas/Vitrine'

/**
 * Entrar e PDV entram no pacote principal — são o caminho quente do balcão.
 * O resto carrega sob demanda; em especial o Painel, que puxa a biblioteca
 * de gráficos (o maior pedaço do sistema) e não interessa a quem abre o
 * navegador direto no PDV.
 */
const Painel = lazy(() => import('./paginas/Painel').then((m) => ({ default: m.Painel })))
const Caixa = lazy(() => import('./paginas/Caixa').then((m) => ({ default: m.Caixa })))
const Vendas = lazy(() => import('./paginas/Vendas').then((m) => ({ default: m.Vendas })))
const Produtos = lazy(() => import('./paginas/Produtos').then((m) => ({ default: m.Produtos })))
const Estoque = lazy(() => import('./paginas/Estoque').then((m) => ({ default: m.Estoque })))
const Clientes = lazy(() => import('./paginas/Clientes').then((m) => ({ default: m.Clientes })))
const Fornecedores = lazy(() =>
  import('./paginas/Fornecedores').then((m) => ({ default: m.Fornecedores })),
)
const Financeiro = lazy(() =>
  import('./paginas/Financeiro').then((m) => ({ default: m.Financeiro })),
)
const Relatorios = lazy(() =>
  import('./paginas/Relatorios').then((m) => ({ default: m.Relatorios })),
)
const Configuracoes = lazy(() =>
  import('./paginas/Configuracoes').then((m) => ({ default: m.Configuracoes })),
)
const Guia = lazy(() => import('./paginas/Guia').then((m) => ({ default: m.Guia })))

export function App() {
  const { usuario, carregando, podeGerenciar } = useAutenticacao()

  if (carregando) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Carregando texto="Abrindo o sistema…" />
      </div>
    )
  }

  if (!usuario) {
    return (
      <Routes>
        {/* A vitrine é pública: responde igual com ou sem sessão. */}
        <Route path="/vitrine/:slug" element={<Vitrine />} />
        <Route path="/entrar" element={<Entrar />} />
        <Route path="*" element={<Navigate to="/entrar" replace />} />
      </Routes>
    )
  }

  return (
    <Suspense fallback={<Carregando />}>
      <Routes>
        <Route path="/entrar" element={<Navigate to="/" replace />} />
        <Route element={<Layout />}>
          <Route index element={<Painel />} />
          <Route path="pdv" element={<PDV />} />
          <Route path="caixa" element={<Caixa />} />
          <Route path="vendas" element={<Vendas />} />
          <Route path="produtos" element={<Produtos />} />
          <Route path="estoque" element={<Estoque />} />
          <Route path="clientes" element={<Clientes />} />
          <Route path="fornecedores" element={<Fornecedores />} />
          <Route
            path="financeiro"
            element={podeGerenciar ? <Financeiro /> : <Navigate to="/" replace />}
          />
          <Route path="relatorios" element={<Relatorios />} />
          <Route path="configuracoes" element={<Configuracoes />} />
        <Route path="guia" element={<Guia />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
