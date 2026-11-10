/** Tipos da API. Espelham os serializers do backend. */

export type Papel = 'dono' | 'gerente' | 'vendedor'

export interface Loja {
  id: number
  nome: string
  slug: string
  cnpj: string
  telefone: string
  email: string
  endereco: string
  cidade: string
  uf: string
  cep: string
  plano: string
  ativa: boolean
  configuracao: ConfiguracaoLoja | null
}

export interface ConfiguracaoLoja {
  exigir_cliente_na_venda: boolean
  permitir_venda_sem_estoque: boolean
  permitir_fiado: boolean
  prazo_fiado_dias: number
  alerta_estoque_minimo: boolean
  mensagem_recibo: string
  vitrine_publica: boolean
  vitrine_mostrar_preco: boolean
  vitrine_mensagem: string
  vitrine_whatsapp: string
  venda_online: boolean
  pix_chave: string
  pix_nome: string
  pix_cidade: string
  reserva_minutos: number
  aceita_entrega: boolean
  aceita_retirada: boolean
  texto_retirada: string
}

export interface Usuario {
  id: number
  nome: string
  email: string
  papel: Papel
  telefone: string
  loja: Loja
  pode_gerenciar: boolean
}

export interface UsuarioEquipe {
  id: number
  nome: string
  email: string
  papel: Papel
  telefone: string
  is_active: boolean
  date_joined: string
}

export interface Pagina<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface Categoria {
  id: number
  nome: string
  descricao: string
  ativo: boolean
  total_produtos: number
}

export interface Marca {
  id: number
  nome: string
  ativo: boolean
  total_produtos: number
}

export interface Variacao {
  id: number
  produto: number
  sabor: string
  nicotina_mg: string | null
  puffs: number | null
  volume_ml: string | null
  sku: string
  codigo_barras: string
  preco_custo_centavos: number
  preco_venda_centavos: number
  saldo: number
  estoque_minimo: number
  ativo: boolean
  descricao_completa: string
  abaixo_do_minimo: boolean
  margem: string
}

export interface VariacaoResumo {
  id: number
  produto: number
  produto_nome: string
  descricao_completa: string
  sabor: string
  nicotina_mg: string | null
  sku: string
  codigo_barras: string
  preco_venda_centavos: number
  saldo: number
  estoque_minimo: number
  ativo: boolean
}

export interface Produto {
  id: number
  nome: string
  descricao: string
  tipo: string
  categoria: number | null
  categoria_nome: string
  marca: number | null
  marca_nome: string
  ativo: boolean
  variacoes: Variacao[]
  saldo_total: number
  imagem_url: string | null
  criado_em: string
}

export interface Cliente {
  id: number
  nome: string
  telefone: string
  email: string
  cpf: string
  data_nascimento: string | null
  idade: number | null
  endereco: string
  cidade: string
  observacoes: string
  limite_credito_centavos: number
  saldo_devedor_centavos: number
  credito_disponivel_centavos: number
  ativo: boolean
}

export interface Fornecedor {
  id: number
  nome: string
  cnpj: string
  contato: string
  telefone: string
  email: string
  endereco: string
  cidade: string
  observacoes: string
  ativo: boolean
  total_compras: number
}

export interface ItemCompra {
  id?: number
  variacao: number
  variacao_descricao?: string
  quantidade: number
  custo_unitario_centavos: number
  total_centavos?: number
}

export interface Compra {
  id: number
  fornecedor: number
  fornecedor_nome: string
  numero_documento: string
  data: string
  status: 'rascunho' | 'recebida' | 'cancelada'
  status_display: string
  frete_centavos: number
  desconto_centavos: number
  total_centavos: number
  vencimento: string | null
  observacoes: string
  itens: ItemCompra[]
  editavel: boolean
  recebida_em: string | null
}

export interface MovimentoEstoque {
  id: number
  variacao: number
  variacao_descricao: string
  tipo: string
  tipo_display: string
  quantidade: number
  quantidade_com_sinal: number
  saldo_apos: number
  custo_unitario_centavos: number
  motivo: string
  documento: string
  usuario_nome: string
  criado_em: string
}

export interface PosicaoEstoque {
  id: number
  produto_nome: string
  categoria_nome: string
  descricao_completa: string
  sku: string
  saldo: number
  estoque_minimo: number
  abaixo_do_minimo: boolean
  preco_custo_centavos: number
  preco_venda_centavos: number
  valor_custo_total_centavos: number
  valor_venda_total_centavos: number
}

export type FormaPagamento = 'dinheiro' | 'pix' | 'debito' | 'credito' | 'fiado'

export interface ItemVenda {
  id: number
  variacao: number
  descricao: string
  quantidade: number
  preco_unitario_centavos: number
  desconto_centavos: number
  total_centavos: number
}

export interface Pagamento {
  id: number
  forma: FormaPagamento
  forma_display: string
  valor_centavos: number
  troco_centavos: number
  observacao: string
}

export interface Venda {
  id: number
  numero: number
  status: 'aberta' | 'finalizada' | 'cancelada'
  status_display: string
  caixa: number | null
  cliente: number | null
  cliente_nome: string
  usuario: number
  vendedor_nome: string
  subtotal_centavos: number
  desconto_centavos: number
  total_centavos: number
  lucro_centavos: number
  observacoes: string
  itens: ItemVenda[]
  pagamentos: Pagamento[]
  criado_em: string
  finalizada_em: string | null
  cancelada_em: string | null
  motivo_cancelamento: string
}

export interface VendaResumo {
  id: number
  numero: number
  status: string
  status_display: string
  total_centavos: number
  cliente_nome: string
  vendedor_nome: string
  quantidade_itens: number
  criado_em: string
  finalizada_em: string | null
}

export interface Caixa {
  id: number
  status: 'aberto' | 'fechado'
  status_display: string
  aberto_em: string
  fechado_em: string | null
  usuario_abertura_nome: string
  usuario_fechamento_nome: string
  saldo_inicial_centavos: number
  saldo_informado_centavos: number
  saldo_calculado_centavos: number
  diferenca_centavos: number
  observacoes: string
}

export interface CaixaAtual {
  aberto: boolean
  caixa: Caixa | null
  saldo_atual_centavos?: number
  vendas_no_caixa?: number
}

export interface MovimentoCaixa {
  id: number
  caixa: number
  tipo: string
  tipo_display: string
  valor_centavos: number
  valor_com_sinal_centavos: number
  descricao: string
  usuario_nome: string
  venda: number | null
  criado_em: string
}

export interface Lancamento {
  id: number
  tipo: 'receita' | 'despesa'
  tipo_display: string
  categoria: number | null
  categoria_nome: string
  descricao: string
  valor_centavos: number
  vencimento: string
  pago_em: string | null
  status: 'pendente' | 'pago' | 'cancelado'
  status_display: string
  forma_pagamento: string
  cliente: number | null
  cliente_nome: string
  fornecedor: number | null
  fornecedor_nome: string
  venda: number | null
  compra: number | null
  observacoes: string
  atrasado: boolean
  dias_de_atraso: number
}

export interface CategoriaFinanceira {
  id: number
  nome: string
  tipo: 'receita' | 'despesa'
  ativo: boolean
}

export interface Dashboard {
  hoje: { vendas: number; faturamento_centavos: number; lucro_centavos: number; ticket_medio_centavos: number }
  mes: { vendas: number; faturamento_centavos: number; lucro_centavos: number; ticket_medio_centavos: number }
  estoque: { unidades: number; valor_custo_centavos: number; abaixo_do_minimo: number; zerados: number }
  financeiro: { a_receber_centavos: number; a_pagar_centavos: number; atrasados: number }
  caixa: { aberto: boolean; id: number | null; saldo_centavos: number; aberto_em: string | null }
  clientes_ativos: number
}
