/** Estrutura da aplicação: navegação lateral, cabeçalho e área de conteúdo. */

import clsx from 'clsx'
import {
  BarChart3, BookOpen, Boxes, ChevronDown, LayoutDashboard, LogOut, Menu,
  Package, Receipt, Settings, ShoppingCart, Truck, Users, Wallet, X,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'

import { useAutenticacao } from '../lib/auth'

interface ItemMenu {
  para: string
  rotulo: string
  icone: typeof LayoutDashboard
  somenteGestao?: boolean
}

const MENU: { grupo: string; itens: ItemMenu[] }[] = [
  {
    grupo: 'Operação',
    itens: [
      { para: '/', rotulo: 'Painel', icone: LayoutDashboard },
      { para: '/pdv', rotulo: 'PDV — Vender', icone: ShoppingCart },
      { para: '/caixa', rotulo: 'Caixa', icone: Wallet },
      { para: '/vendas', rotulo: 'Vendas', icone: Receipt },
    ],
  },
  {
    grupo: 'Cadastros',
    itens: [
      { para: '/produtos', rotulo: 'Produtos', icone: Package },
      { para: '/estoque', rotulo: 'Estoque', icone: Boxes },
      { para: '/clientes', rotulo: 'Clientes', icone: Users },
      { para: '/fornecedores', rotulo: 'Fornecedores e compras', icone: Truck },
    ],
  },
  {
    grupo: 'Gestão',
    itens: [
      { para: '/financeiro', rotulo: 'Financeiro', icone: Wallet, somenteGestao: true },
      { para: '/relatorios', rotulo: 'Relatórios', icone: BarChart3 },
      { para: '/configuracoes', rotulo: 'Configurações', icone: Settings },
      { para: '/guia', rotulo: 'Guia de uso', icone: BookOpen },
    ],
  },
]

export function Layout() {
  const { usuario, sair, podeGerenciar } = useAutenticacao()
  const [menuAberto, setMenuAberto] = useState(false)
  const [contaAberta, setContaAberta] = useState(false)
  const local = useLocation()

  // Navegar fecha o menu no celular; sem isso a lista fica por cima da tela.
  useEffect(() => {
    setMenuAberto(false)
    setContaAberta(false)
  }, [local.pathname])

  const navegacao = (
    <nav className="flex flex-col gap-5 p-3">
      {MENU.map(({ grupo, itens }) => {
        const visiveis = itens.filter((item) => !item.somenteGestao || podeGerenciar)
        if (!visiveis.length) return null
        return (
          <div key={grupo}>
            <p className="mb-1.5 px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
              {grupo}
            </p>
            <ul className="space-y-0.5">
              {visiveis.map(({ para, rotulo, icone: Icone }) => (
                <li key={para}>
                  <NavLink
                    to={para}
                    end={para === '/'}
                    className={({ isActive }) =>
                      clsx(
                        'flex min-h-[44px] items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition',
                        isActive
                          ? 'bg-marca-700 text-white shadow-sm'
                          : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900',
                      )
                    }
                  >
                    <Icone size={17} />
                    {rotulo}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        )
      })}
    </nav>
  )

  return (
    <div className="min-h-screen lg:flex">
      {/* Navegação — fixa no desktop */}
      <aside className="hidden w-60 shrink-0 border-r border-slate-200 bg-white lg:flex lg:flex-col">
        <div className="flex h-14 items-center gap-2 border-b border-slate-200 px-4">
          <span className="text-xl">💨</span>
          <span className="font-bold text-slate-900">Vape Project</span>
        </div>
        <div className="flex-1 overflow-y-auto">{navegacao}</div>
        <div className="border-t border-slate-200 p-3">
          <p className="truncate px-2 text-xs text-slate-500">{usuario?.loja.nome}</p>
        </div>
      </aside>

      {/* Navegação — gaveta no celular */}
      {menuAberto && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-slate-900/40"
            onClick={() => setMenuAberto(false)}
            aria-hidden
          />
          <aside className="absolute left-0 top-0 flex h-full w-64 flex-col bg-white shadow-xl">
            <div className="flex h-14 items-center justify-between border-b border-slate-200 px-4">
              <span className="font-bold text-slate-900">💨 Vape Project</span>
              <button
                onClick={() => setMenuAberto(false)}
                aria-label="Fechar menu"
                className="-mr-1 inline-flex h-11 w-11 items-center justify-center rounded-lg
                           text-slate-500 transition active:bg-slate-100"
              >
                <X size={22} />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto">{navegacao}</div>
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-slate-200 bg-white/95 px-3 backdrop-blur sm:px-5">
          <button
            onClick={() => setMenuAberto(true)}
            aria-label="Abrir menu"
            className="-ml-1 inline-flex h-11 w-11 items-center justify-center rounded-lg
                       text-slate-600 transition hover:bg-slate-100 active:bg-slate-200 lg:hidden"
          >
            <Menu size={22} />
          </button>

          <span className="truncate text-sm font-semibold text-slate-700 lg:hidden">
            {usuario?.loja.nome}
          </span>

          <div className="ml-auto relative">
            <button
              onClick={() => setContaAberta((estado) => !estado)}
              className="flex h-11 items-center gap-2 rounded-lg px-2 text-sm text-slate-700 transition hover:bg-slate-100"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-marca-700 text-xs font-semibold text-white">
                {usuario?.nome.slice(0, 2).toUpperCase()}
              </span>
              <span className="hidden max-w-[10rem] truncate sm:inline">{usuario?.nome}</span>
              <ChevronDown size={15} className="text-slate-400" />
            </button>

            {contaAberta && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setContaAberta(false)} aria-hidden />
                <div className="absolute right-0 z-20 mt-1 w-56 rounded-lg border border-slate-200 bg-white py-1 shadow-lg">
                  <div className="border-b border-slate-100 px-3 py-2">
                    <p className="truncate text-sm font-medium text-slate-800">{usuario?.nome}</p>
                    <p className="truncate text-xs text-slate-500">{usuario?.email}</p>
                    <p className="mt-1 text-xs capitalize text-marca-700">{usuario?.papel}</p>
                  </div>
                  <button
                    onClick={sair}
                    className="flex min-h-[44px] w-full items-center gap-2 px-3 py-2 text-left text-sm text-rose-600 transition hover:bg-rose-50"
                  >
                    <LogOut size={15} />
                    Sair
                  </button>
                </div>
              </>
            )}
          </div>
        </header>

        <main className="min-w-0 flex-1 px-3 py-5 sm:px-5 lg:px-7">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
