/** Catálogo: produtos, variações, categorias e marcas. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronDown, ChevronRight, Package, Pencil, Plus, Tag, Trash2 } from 'lucide-react'
import { useState } from 'react'

import {
  Alerta, AreaTexto, Botao, CabecalhoPagina, Campo, Carregando, Cartao, Modal,
  Paginacao, Selecao, Selo, TabelaEnvolvida, Vazio,
} from '../componentes/ui'
import { ErroApi, api, querystring } from '../lib/api'
import { useAutenticacao } from '../lib/auth'
import { formatarMoeda, paraCentavos } from '../lib/formato'
import type { Categoria, Marca, Pagina, Produto, Variacao } from '../lib/tipos'

const TIPOS = [
  { valor: 'descartavel', rotulo: 'Descartável' },
  { valor: 'pod', rotulo: 'Pod / dispositivo' },
  { valor: 'liquido', rotulo: 'Líquido' },
  { valor: 'resistencia', rotulo: 'Resistência / coil' },
  { valor: 'bateria', rotulo: 'Bateria' },
  { valor: 'acessorio', rotulo: 'Acessório' },
  { valor: 'outro', rotulo: 'Outro' },
]

export function Produtos() {
  const { podeGerenciar } = useAutenticacao()
  const clienteQuery = useQueryClient()

  const [busca, setBusca] = useState('')
  const [categoriaFiltro, setCategoriaFiltro] = useState('')
  const [expandido, setExpandido] = useState<number | null>(null)
  const [modalProduto, setModalProduto] = useState<Produto | 'novo' | null>(null)
  const [modalVariacao, setModalVariacao] = useState<{ produto: Produto; variacao: Variacao | null } | null>(null)
  const [aba, setAba] = useState<'produtos' | 'organizacao'>('produtos')
  const [pagina, setPagina] = useState(1)

  const { data: produtos, isLoading } = useQuery({
    queryKey: ['produtos', busca, categoriaFiltro, pagina],
    queryFn: () =>
      api.get<Pagina<Produto>>(
        `/produtos/${querystring({ search: busca, categoria: categoriaFiltro, page: pagina })}`,
      ),
  })

  const { data: categorias } = useQuery({
    queryKey: ['categorias'],
    queryFn: () => api.get<Pagina<Categoria>>('/categorias/'),
  })

  const { data: marcas } = useQuery({
    queryKey: ['marcas'],
    queryFn: () => api.get<Pagina<Marca>>('/marcas/'),
  })

  const excluir = useMutation({
    mutationFn: (id: number) => api.delete(`/produtos/${id}/`),
    onSuccess: () => clienteQuery.invalidateQueries({ queryKey: ['produtos'] }),
  })

  return (
    <>
      <CabecalhoPagina
        titulo="Produtos"
        descricao="Cada produto tem variações — é a variação que tem preço e estoque."
        acoes={
          podeGerenciar && (
            <Botao icone={<Plus size={16} />} onClick={() => setModalProduto('novo')}>
              Novo produto
            </Botao>
          )
        }
      />

      <div className="mb-4 flex gap-1 border-b border-slate-200">
        {(['produtos', 'organizacao'] as const).map((valor) => (
          <button
            key={valor}
            onClick={() => setAba(valor)}
            className={`px-4 py-2 text-sm font-medium transition ${
              aba === valor
                ? 'border-b-2 border-marca-700 text-marca-800'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {valor === 'produtos' ? 'Catálogo' : 'Categorias e marcas'}
          </button>
        ))}
      </div>

      {aba === 'produtos' ? (
        <>
          <div className="mb-3 grid gap-2 sm:grid-cols-[1fr_200px]">
            <Campo
              placeholder="Buscar por nome, sabor, SKU ou código de barras…"
              value={busca}
              onChange={(evento) => { setBusca(evento.target.value); setPagina(1) }}
            />
            <Selecao
              value={categoriaFiltro}
              onChange={(evento) => { setCategoriaFiltro(evento.target.value); setPagina(1) }}
            >
              <option value="">Todas as categorias</option>
              {categorias?.results.map((categoria) => (
                <option key={categoria.id} value={categoria.id}>
                  {categoria.nome}
                </option>
              ))}
            </Selecao>
          </div>

          {isLoading ? (
            <Carregando />
          ) : !produtos?.results.length ? (
            <Cartao>
              <Vazio
                titulo="Nenhum produto cadastrado"
                descricao="Cadastre o primeiro produto para começar a vender."
                acao={
                  podeGerenciar && <Botao onClick={() => setModalProduto('novo')}>Novo produto</Botao>
                }
              />
            </Cartao>
          ) : (
            <div className="space-y-2">
              {produtos.results.map((produto) => {
                const aberto = expandido === produto.id
                return (
                  <div key={produto.id} className="cartao overflow-hidden">
                    <div className="flex items-center gap-3 px-4 py-3">
                      <button
                        onClick={() => setExpandido(aberto ? null : produto.id)}
                        className="text-slate-400 transition hover:text-slate-700"
                        aria-label={aberto ? 'Recolher' : 'Expandir'}
                      >
                        {aberto ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                      </button>

                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-medium text-slate-900">{produto.nome}</p>
                          {!produto.ativo && <Selo cor="cinza">inativo</Selo>}
                        </div>
                        <p className="text-xs text-slate-500">
                          {[produto.marca_nome, produto.categoria_nome].filter(Boolean).join(' · ') ||
                            'sem categoria'}{' '}
                          · {produto.variacoes.length} variação(ões)
                        </p>
                      </div>

                      <div className="hidden text-right sm:block">
                        <p className="numerico text-sm font-semibold text-slate-800">
                          {produto.saldo_total} un.
                        </p>
                        <p className="text-xs text-slate-500">em estoque</p>
                      </div>

                      {podeGerenciar && (
                        <div className="flex gap-1">
                          <button
                            onClick={() => setModalProduto(produto)}
                            className="rounded p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-marca-700"
                            title="Editar produto"
                          >
                            <Pencil size={15} />
                          </button>
                          <button
                            onClick={() => {
                              if (confirm(`Remover “${produto.nome}”? Produtos com histórico são apenas desativados.`)) {
                                excluir.mutate(produto.id)
                              }
                            }}
                            className="rounded p-1.5 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"
                            title="Remover produto"
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      )}
                    </div>

                    {aberto && (
                      <div className="border-t border-slate-100 bg-slate-50/60 px-4 py-3">
                        <TabelaEnvolvida>
                          <table className="tabela">
                            <thead>
                              <tr>
                                <th>Variação</th>
                                <th>SKU / código</th>
                                <th className="text-right">Custo</th>
                                <th className="text-right">Venda</th>
                                <th className="text-right">Margem</th>
                                <th className="text-right">Saldo</th>
                                {podeGerenciar && <th />}
                              </tr>
                            </thead>
                            <tbody>
                              {produto.variacoes.map((variacao) => (
                                <tr key={variacao.id}>
                                  <td>
                                    <span className="text-sm">{variacao.sabor || '—'}</span>
                                    {variacao.nicotina_mg && (
                                      <span className="ml-1.5 text-xs text-slate-500">
                                        {Number(variacao.nicotina_mg)} mg
                                      </span>
                                    )}
                                  </td>
                                  <td className="text-xs text-slate-500">
                                    {variacao.sku || '—'}
                                    {variacao.codigo_barras && <div>{variacao.codigo_barras}</div>}
                                  </td>
                                  <td className="numerico text-right">
                                    {formatarMoeda(variacao.preco_custo_centavos)}
                                  </td>
                                  <td className="numerico text-right font-semibold">
                                    {formatarMoeda(variacao.preco_venda_centavos)}
                                  </td>
                                  <td className="numerico text-right text-slate-600">
                                    {Number(variacao.margem).toFixed(0)}%
                                  </td>
                                  <td className="text-right">
                                    <Selo
                                      cor={
                                        variacao.saldo <= 0
                                          ? 'vermelho'
                                          : variacao.abaixo_do_minimo
                                            ? 'ambar'
                                            : 'verde'
                                      }
                                    >
                                      {variacao.saldo}
                                    </Selo>
                                  </td>
                                  {podeGerenciar && (
                                    <td className="text-right">
                                      <button
                                        onClick={() => setModalVariacao({ produto, variacao })}
                                        className="rounded p-1 text-slate-400 hover:text-marca-700"
                                      >
                                        <Pencil size={14} />
                                      </button>
                                    </td>
                                  )}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </TabelaEnvolvida>

                        {podeGerenciar && (
                          <Botao
                            variante="secundario"
                            tamanho="pequeno"
                            icone={<Plus size={14} />}
                            className="mt-3"
                            onClick={() => setModalVariacao({ produto, variacao: null })}
                          >
                            Adicionar variação
                          </Botao>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
              <div className="cartao">
                <Paginacao pagina={pagina} total={produtos.count} aoMudar={setPagina} />
              </div>
            </div>
          )}
        </>
      ) : (
        <Organizacao categorias={categorias?.results ?? []} marcas={marcas?.results ?? []} />
      )}

      {modalProduto && (
        <ModalProduto
          produto={modalProduto === 'novo' ? null : modalProduto}
          categorias={categorias?.results ?? []}
          marcas={marcas?.results ?? []}
          aoFechar={() => setModalProduto(null)}
        />
      )}

      {modalVariacao && (
        <ModalVariacao
          produto={modalVariacao.produto}
          variacao={modalVariacao.variacao}
          aoFechar={() => setModalVariacao(null)}
        />
      )}
    </>
  )
}

// ------------------------------------------------------------------ produto

function ModalProduto({
  produto, categorias, marcas, aoFechar,
}: {
  produto: Produto | null
  categorias: Categoria[]
  marcas: Marca[]
  aoFechar: () => void
}) {
  const clienteQuery = useQueryClient()
  const [erro, setErro] = useState<ErroApi | null>(null)
  const [dados, setDados] = useState({
    nome: produto?.nome ?? '',
    descricao: produto?.descricao ?? '',
    tipo: produto?.tipo ?? 'descartavel',
    categoria: produto?.categoria?.toString() ?? '',
    marca: produto?.marca?.toString() ?? '',
    ativo: produto?.ativo ?? true,
  })
  // Só no cadastro: a primeira variação nasce junto com o produto.
  const [sabor, setSabor] = useState('')
  const [precoVenda, setPrecoVenda] = useState('')
  const [precoCusto, setPrecoCusto] = useState('')

  const salvar = useMutation({
    mutationFn: () => {
      const corpo: Record<string, unknown> = {
        nome: dados.nome,
        descricao: dados.descricao,
        tipo: dados.tipo,
        categoria: dados.categoria ? Number(dados.categoria) : null,
        marca: dados.marca ? Number(dados.marca) : null,
        ativo: dados.ativo,
      }
      if (produto) return api.patch(`/produtos/${produto.id}/`, corpo)

      corpo.variacoes = [
        {
          sabor: sabor || 'Padrão',
          preco_venda_centavos: paraCentavos(precoVenda),
          preco_custo_centavos: paraCentavos(precoCusto),
        },
      ]
      return api.post('/produtos/', corpo)
    },
    onSuccess: () => {
      clienteQuery.invalidateQueries({ queryKey: ['produtos'] })
      aoFechar()
    },
    onError: (falha) => setErro(falha instanceof ErroApi ? falha : null),
  })

  return (
    <Modal
      aberto
      aoFechar={aoFechar}
      titulo={produto ? 'Editar produto' : 'Novo produto'}
      largura="max-w-xl"
    >
      <form
        className="space-y-3"
        onSubmit={(evento) => { evento.preventDefault(); salvar.mutate() }}
      >
        <Campo
          rotulo="Nome do produto"
          value={dados.nome}
          onChange={(evento) => setDados({ ...dados, nome: evento.target.value })}
          placeholder="Elf Bar BC10000"
          required
          autoFocus
          erro={erro?.doCampo('nome')}
        />

        <div className="grid gap-3 sm:grid-cols-3">
          <Selecao
            rotulo="Tipo"
            value={dados.tipo}
            onChange={(evento) => setDados({ ...dados, tipo: evento.target.value })}
          >
            {TIPOS.map((tipo) => (
              <option key={tipo.valor} value={tipo.valor}>{tipo.rotulo}</option>
            ))}
          </Selecao>
          <Selecao
            rotulo="Categoria"
            value={dados.categoria}
            onChange={(evento) => setDados({ ...dados, categoria: evento.target.value })}
          >
            <option value="">Sem categoria</option>
            {categorias.map((categoria) => (
              <option key={categoria.id} value={categoria.id}>{categoria.nome}</option>
            ))}
          </Selecao>
          <Selecao
            rotulo="Marca"
            value={dados.marca}
            onChange={(evento) => setDados({ ...dados, marca: evento.target.value })}
          >
            <option value="">Sem marca</option>
            {marcas.map((marca) => (
              <option key={marca.id} value={marca.id}>{marca.nome}</option>
            ))}
          </Selecao>
        </div>

        <AreaTexto
          rotulo="Descrição"
          value={dados.descricao}
          onChange={(evento) => setDados({ ...dados, descricao: evento.target.value })}
          placeholder="Opcional"
        />

        {!produto && (
          <fieldset className="rounded-lg border border-slate-200 p-3">
            <legend className="px-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Primeira variação
            </legend>
            <div className="grid gap-3 sm:grid-cols-3">
              <Campo
                rotulo="Sabor"
                value={sabor}
                onChange={(evento) => setSabor(evento.target.value)}
                placeholder="Blue Razz"
              />
              <Campo
                rotulo="Preço de custo"
                value={precoCusto}
                onChange={(evento) => setPrecoCusto(evento.target.value)}
                placeholder="0,00"
                inputMode="decimal"
              />
              <Campo
                rotulo="Preço de venda"
                value={precoVenda}
                onChange={(evento) => setPrecoVenda(evento.target.value)}
                placeholder="0,00"
                inputMode="decimal"
                required
              />
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Outras variações (sabores, teores) podem ser adicionadas depois.
            </p>
          </fieldset>
        )}

        {produto && (
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={dados.ativo}
              onChange={(evento) => setDados({ ...dados, ativo: evento.target.checked })}
              className="h-4 w-4 rounded border-slate-300"
            />
            Produto ativo (aparece no PDV)
          </label>
        )}

        {erro && !erro.doCampo('nome') && <Alerta>{erro.message}</Alerta>}

        <div className="flex gap-2 pt-1">
          <Botao type="button" variante="secundario" className="flex-1" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" className="flex-1" carregando={salvar.isPending}>
            Salvar
          </Botao>
        </div>
      </form>
    </Modal>
  )
}

// ------------------------------------------------------------------ variação

function ModalVariacao({
  produto, variacao, aoFechar,
}: {
  produto: Produto
  variacao: Variacao | null
  aoFechar: () => void
}) {
  const clienteQuery = useQueryClient()
  const [erro, setErro] = useState<ErroApi | null>(null)
  const [dados, setDados] = useState({
    sabor: variacao?.sabor ?? '',
    nicotina_mg: variacao?.nicotina_mg ?? '',
    puffs: variacao?.puffs?.toString() ?? '',
    sku: variacao?.sku ?? '',
    codigo_barras: variacao?.codigo_barras ?? '',
    custo: variacao ? (variacao.preco_custo_centavos / 100).toFixed(2).replace('.', ',') : '',
    venda: variacao ? (variacao.preco_venda_centavos / 100).toFixed(2).replace('.', ',') : '',
    estoque_minimo: variacao?.estoque_minimo?.toString() ?? '0',
    ativo: variacao?.ativo ?? true,
  })

  const salvar = useMutation({
    mutationFn: () => {
      const corpo = {
        sabor: dados.sabor,
        nicotina_mg: dados.nicotina_mg === '' ? null : dados.nicotina_mg,
        puffs: dados.puffs === '' ? null : Number(dados.puffs),
        sku: dados.sku,
        codigo_barras: dados.codigo_barras,
        preco_custo_centavos: paraCentavos(dados.custo),
        preco_venda_centavos: paraCentavos(dados.venda),
        estoque_minimo: Number(dados.estoque_minimo) || 0,
        ativo: dados.ativo,
      }
      return variacao
        ? api.patch(`/variacoes/${variacao.id}/`, corpo)
        : api.post(`/produtos/${produto.id}/variacoes/`, corpo)
    },
    onSuccess: () => {
      clienteQuery.invalidateQueries({ queryKey: ['produtos'] })
      aoFechar()
    },
    onError: (falha) => setErro(falha instanceof ErroApi ? falha : null),
  })

  return (
    <Modal
      aberto
      aoFechar={aoFechar}
      titulo={variacao ? 'Editar variação' : 'Nova variação'}
      descricao={produto.nome}
      largura="max-w-xl"
    >
      <form className="space-y-3" onSubmit={(evento) => { evento.preventDefault(); salvar.mutate() }}>
        <div className="grid gap-3 sm:grid-cols-3">
          <Campo
            rotulo="Sabor"
            value={dados.sabor}
            onChange={(evento) => setDados({ ...dados, sabor: evento.target.value })}
            placeholder="Blue Razz"
            autoFocus
            erro={erro?.doCampo('sabor')}
          />
          <Campo
            rotulo="Nicotina (mg/mL)"
            value={dados.nicotina_mg}
            onChange={(evento) => setDados({ ...dados, nicotina_mg: evento.target.value })}
            placeholder="5"
            inputMode="decimal"
          />
          <Campo
            rotulo="Puffs"
            value={dados.puffs}
            onChange={(evento) => setDados({ ...dados, puffs: evento.target.value })}
            placeholder="10000"
            inputMode="numeric"
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <Campo
            rotulo="SKU"
            value={dados.sku}
            onChange={(evento) => setDados({ ...dados, sku: evento.target.value })}
            erro={erro?.doCampo('sku')}
          />
          <Campo
            rotulo="Código de barras"
            value={dados.codigo_barras}
            onChange={(evento) => setDados({ ...dados, codigo_barras: evento.target.value })}
            erro={erro?.doCampo('codigo_barras')}
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <Campo
            rotulo="Preço de custo"
            value={dados.custo}
            onChange={(evento) => setDados({ ...dados, custo: evento.target.value })}
            placeholder="0,00"
            inputMode="decimal"
          />
          <Campo
            rotulo="Preço de venda"
            value={dados.venda}
            onChange={(evento) => setDados({ ...dados, venda: evento.target.value })}
            placeholder="0,00"
            inputMode="decimal"
            required
          />
          <Campo
            rotulo="Estoque mínimo"
            value={dados.estoque_minimo}
            onChange={(evento) => setDados({ ...dados, estoque_minimo: evento.target.value })}
            inputMode="numeric"
            dica="Alerta quando o saldo chegar aqui."
          />
        </div>

        <label className="flex items-center gap-2 text-sm text-slate-700">
          <input
            type="checkbox"
            checked={dados.ativo}
            onChange={(evento) => setDados({ ...dados, ativo: evento.target.checked })}
            className="h-4 w-4 rounded border-slate-300"
          />
          Variação ativa
        </label>

        {variacao && (
          <p className="text-xs text-slate-500">
            Saldo atual: <strong>{variacao.saldo}</strong>. O saldo só muda por movimentação
            de estoque — nunca pela edição do cadastro.
          </p>
        )}

        {erro && <Alerta>{erro.message}</Alerta>}

        <div className="flex gap-2 pt-1">
          <Botao type="button" variante="secundario" className="flex-1" onClick={aoFechar}>
            Cancelar
          </Botao>
          <Botao type="submit" className="flex-1" carregando={salvar.isPending}>
            Salvar
          </Botao>
        </div>
      </form>
    </Modal>
  )
}

// ------------------------------------------------------------------ categorias e marcas

function Organizacao({ categorias, marcas }: { categorias: Categoria[]; marcas: Marca[] }) {
  const { podeGerenciar } = useAutenticacao()
  const clienteQuery = useQueryClient()
  const [novaCategoria, setNovaCategoria] = useState('')
  const [novaMarca, setNovaMarca] = useState('')

  const criarCategoria = useMutation({
    mutationFn: (nome: string) => api.post('/categorias/', { nome }),
    onSuccess: () => {
      clienteQuery.invalidateQueries({ queryKey: ['categorias'] })
      setNovaCategoria('')
    },
  })

  const criarMarca = useMutation({
    mutationFn: (nome: string) => api.post('/marcas/', { nome }),
    onSuccess: () => {
      clienteQuery.invalidateQueries({ queryKey: ['marcas'] })
      setNovaMarca('')
    },
  })

  const excluirCategoria = useMutation({
    mutationFn: (id: number) => api.delete(`/categorias/${id}/`),
    onSuccess: () => clienteQuery.invalidateQueries({ queryKey: ['categorias'] }),
  })

  const excluirMarca = useMutation({
    mutationFn: (id: number) => api.delete(`/marcas/${id}/`),
    onSuccess: () => clienteQuery.invalidateQueries({ queryKey: ['marcas'] }),
  })

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Cartao titulo="Categorias">
        {podeGerenciar && (
          <form
            className="mb-3 flex gap-2"
            onSubmit={(evento) => {
              evento.preventDefault()
              if (novaCategoria.trim()) criarCategoria.mutate(novaCategoria.trim())
            }}
          >
            <Campo
              className="flex-1"
              placeholder="Nova categoria"
              value={novaCategoria}
              onChange={(evento) => setNovaCategoria(evento.target.value)}
            />
            <Botao type="submit" icone={<Plus size={15} />} carregando={criarCategoria.isPending}>
              Adicionar
            </Botao>
          </form>
        )}
        {categorias.length === 0 ? (
          <p className="py-4 text-center text-sm text-slate-400">Nenhuma categoria.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {categorias.map((categoria) => (
              <li key={categoria.id} className="flex items-center justify-between gap-2 py-2">
                <span className="flex items-center gap-2 text-sm">
                  <Package size={14} className="text-slate-400" />
                  {categoria.nome}
                  <span className="text-xs text-slate-400">
                    ({categoria.total_produtos} produto(s))
                  </span>
                </span>
                {podeGerenciar && categoria.total_produtos === 0 && (
                  <button
                    onClick={() => excluirCategoria.mutate(categoria.id)}
                    className="text-slate-300 transition hover:text-rose-600"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Cartao>

      <Cartao titulo="Marcas">
        {podeGerenciar && (
          <form
            className="mb-3 flex gap-2"
            onSubmit={(evento) => {
              evento.preventDefault()
              if (novaMarca.trim()) criarMarca.mutate(novaMarca.trim())
            }}
          >
            <Campo
              className="flex-1"
              placeholder="Nova marca"
              value={novaMarca}
              onChange={(evento) => setNovaMarca(evento.target.value)}
            />
            <Botao type="submit" icone={<Plus size={15} />} carregando={criarMarca.isPending}>
              Adicionar
            </Botao>
          </form>
        )}
        {marcas.length === 0 ? (
          <p className="py-4 text-center text-sm text-slate-400">Nenhuma marca.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {marcas.map((marca) => (
              <li key={marca.id} className="flex items-center justify-between gap-2 py-2">
                <span className="flex items-center gap-2 text-sm">
                  <Tag size={14} className="text-slate-400" />
                  {marca.nome}
                  <span className="text-xs text-slate-400">({marca.total_produtos} produto(s))</span>
                </span>
                {podeGerenciar && marca.total_produtos === 0 && (
                  <button
                    onClick={() => excluirMarca.mutate(marca.id)}
                    className="text-slate-300 transition hover:text-rose-600"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Cartao>
    </div>
  )
}
