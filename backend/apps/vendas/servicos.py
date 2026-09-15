"""
Serviços de venda e de caixa.

Finalizar uma venda toca quatro coisas ao mesmo tempo — estoque, caixa,
financeiro e a própria venda. Ou tudo acontece, ou nada: daí o
`transaction.atomic` em cada operação pública deste módulo.
"""

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Max, Sum
from django.utils import timezone

from apps.core.exceptions import CaixaFechado, ErroDeNegocio
from apps.core.utils import calcular_idade, quantizar
from apps.estoque.models import TipoMovimento
from apps.estoque.servicos import registrar_movimento
from apps.produtos.models import Variacao

from .models import (
    Caixa,
    FormaPagamento,
    ItemVenda,
    MovimentoCaixa,
    Pagamento,
    StatusCaixa,
    StatusVenda,
    TipoMovimentoCaixa,
    Venda,
)

# ------------------------------------------------------------------
# Caixa
# ------------------------------------------------------------------


def caixa_aberto(loja) -> Caixa | None:
    return Caixa.objects.filter(loja=loja, status=StatusCaixa.ABERTO).first()


@transaction.atomic
def abrir_caixa(*, loja, usuario, saldo_inicial: Decimal = Decimal("0.00")) -> Caixa:
    if caixa_aberto(loja):
        raise ErroDeNegocio(
            "Já existe um caixa aberto. Feche-o antes de abrir outro.", campo="caixa"
        )
    if saldo_inicial < 0:
        raise ErroDeNegocio("O saldo inicial não pode ser negativo.", campo="saldo_inicial")

    caixa = Caixa.objects.create(
        loja=loja, usuario_abertura=usuario, saldo_inicial=quantizar(saldo_inicial)
    )
    if saldo_inicial > 0:
        MovimentoCaixa.objects.create(
            loja=loja, caixa=caixa, tipo=TipoMovimentoCaixa.SUPRIMENTO,
            valor=quantizar(saldo_inicial), descricao="Saldo inicial (fundo de troco)",
            usuario=usuario,
        )
    return caixa


def calcular_saldo_do_caixa(caixa: Caixa) -> Decimal:
    """
    Dinheiro que deveria estar na gaveta.

    Só conta movimento em espécie — o saldo inicial já entrou como suprimento
    na abertura, por isso não é somado de novo aqui.
    """
    total = Decimal("0.00")
    for movimento in caixa.movimentos.all():
        total += movimento.valor_com_sinal
    return quantizar(total)


@transaction.atomic
def fechar_caixa(
    *, caixa: Caixa, usuario, saldo_informado: Decimal, observacoes: str = ""
) -> Caixa:
    """
    Fecha o caixa e registra a diferença entre gaveta e sistema.

    A diferença não bloqueia o fechamento: ela é o dado que interessa. Falta
    recorrente é problema de gestão, não de software.
    """
    caixa = Caixa.objects.select_for_update().get(pk=caixa.pk)

    if caixa.status == StatusCaixa.FECHADO:
        raise ErroDeNegocio("Este caixa já está fechado.", campo="status")

    # Vendas abertas ainda não têm caixa vinculado (o vínculo só acontece na
    # finalização), por isso a busca é por loja, não por `caixa.vendas`.
    ha_vendas_abertas = Venda.objects.filter(
        loja=caixa.loja, status=StatusVenda.ABERTA
    ).exists()
    if ha_vendas_abertas:
        raise ErroDeNegocio(
            "Há vendas em aberto. Finalize ou cancele antes de fechar o caixa.",
            campo="caixa",
        )

    calculado = calcular_saldo_do_caixa(caixa)
    informado = quantizar(saldo_informado)

    caixa.saldo_calculado = calculado
    caixa.saldo_informado = informado
    caixa.diferenca = quantizar(informado - calculado)
    caixa.status = StatusCaixa.FECHADO
    caixa.fechado_em = timezone.now()
    caixa.usuario_fechamento = usuario
    caixa.observacoes = observacoes
    caixa.save()
    return caixa


@transaction.atomic
def movimentar_caixa(*, caixa: Caixa, usuario, tipo: str, valor: Decimal, descricao: str = ""):
    """Sangria ou suprimento manual."""
    if not caixa.aberto:
        raise CaixaFechado("O caixa está fechado.", campo="caixa")
    if valor <= 0:
        raise ErroDeNegocio("O valor deve ser maior que zero.", campo="valor")

    valor = quantizar(valor)
    if tipo == TipoMovimentoCaixa.SANGRIA and valor > calcular_saldo_do_caixa(caixa):
        raise ErroDeNegocio(
            "A sangria é maior que o dinheiro disponível no caixa.", campo="valor"
        )

    return MovimentoCaixa.objects.create(
        loja=caixa.loja, caixa=caixa, tipo=tipo, valor=valor,
        descricao=descricao, usuario=usuario,
    )


# ------------------------------------------------------------------
# Venda
# ------------------------------------------------------------------


def _proximo_numero(loja) -> int:
    ultimo = Venda.objects.filter(loja=loja).aggregate(maximo=Max("numero"))["maximo"]
    return (ultimo or 0) + 1


def _verificar_idade(cliente):
    """Bloqueia venda a menor de idade identificado (ADR-0003)."""
    minima = getattr(settings, "IDADE_MINIMA_COMPRA", 18)
    if not minima or cliente is None or not cliente.data_nascimento:
        return
    if calcular_idade(cliente.data_nascimento) < minima:
        raise ErroDeNegocio(
            f"Venda não permitida: o cliente tem menos de {minima} anos.",
            campo="cliente",
        )


@transaction.atomic
def criar_venda(*, loja, usuario, itens, cliente=None, desconto=Decimal("0.00"),
                observacoes: str = "") -> Venda:
    """
    Cria a venda como **aberta**, sem tocar no estoque.

    A baixa acontece em `finalizar_venda`: enquanto a venda está aberta o
    cliente ainda pode desistir, e travar estoque nesse meio-tempo seria pior
    do que o risco de vender a última unidade duas vezes — risco que a trava
    de `registrar_movimento` resolve na finalização.
    """
    from apps.lojas.models import ConfiguracaoLoja

    if not itens:
        raise ErroDeNegocio("A venda precisa de ao menos um item.", campo="itens")

    configuracao, _ = ConfiguracaoLoja.objects.get_or_create(loja=loja)

    if configuracao.exigir_cliente_na_venda and cliente is None:
        raise ErroDeNegocio(
            "Esta loja exige identificar o cliente na venda.", campo="cliente"
        )
    _verificar_idade(cliente)

    venda = Venda.objects.create(
        loja=loja,
        numero=_proximo_numero(loja),
        usuario=usuario,
        cliente=cliente,
        status=StatusVenda.ABERTA,
        desconto=quantizar(desconto),
        observacoes=observacoes,
    )

    # As variações são recarregadas do banco em vez de confiar no objeto
    # recebido: o custo médio muda a cada compra, e uma instância carregada
    # antes disso gravaria no item um custo velho — que fica congelado no
    # snapshot e distorce a margem para sempre.
    ids = [entrada["variacao"].pk for entrada in itens]
    atuais = {
        variacao.pk: variacao
        for variacao in Variacao.objects.select_related("produto").filter(pk__in=ids)
    }

    for entrada in itens:
        variacao = atuais.get(entrada["variacao"].pk)
        if variacao is None or variacao.loja_id != loja.id:
            raise ErroDeNegocio("Há itens que não pertencem a esta loja.", campo="itens")

        preco = entrada.get("preco_unitario")
        if preco is None:
            preco = variacao.preco_venda

        ItemVenda.objects.create(
            venda=venda,
            variacao=variacao,
            descricao=variacao.descricao_completa,
            quantidade=entrada["quantidade"],
            preco_unitario=quantizar(preco),
            desconto=quantizar(entrada.get("desconto", Decimal("0.00"))),
            custo_unitario=variacao.preco_custo,
        )

    _recalcular_totais(venda)
    return venda


def _recalcular_totais(venda: Venda) -> Venda:
    itens = list(venda.itens.all())
    subtotal = sum((item.total for item in itens), Decimal("0.00"))
    custo = sum((item.custo_total for item in itens), Decimal("0.00"))

    if venda.desconto > subtotal:
        raise ErroDeNegocio(
            "O desconto não pode ser maior que o subtotal da venda.", campo="desconto"
        )

    venda.subtotal = quantizar(subtotal)
    venda.custo_total = quantizar(custo)
    venda.total = quantizar(subtotal - venda.desconto)
    venda.save(update_fields=["subtotal", "custo_total", "total", "atualizado_em"])
    return venda


@transaction.atomic
def finalizar_venda(*, venda: Venda, usuario, pagamentos) -> Venda:
    """
    Fecha a venda: baixa estoque, registra pagamentos, movimenta caixa e
    gera a conta a receber do fiado.

    `pagamentos` é uma lista de dicts `{forma, valor, observacao?}` — venda
    dividida entre dinheiro e cartão é rotina no balcão.
    """
    from apps.lojas.models import ConfiguracaoLoja

    venda = Venda.objects.select_for_update().get(pk=venda.pk)

    if venda.status != StatusVenda.ABERTA:
        raise ErroDeNegocio(
            f"Só é possível finalizar venda aberta (status atual: "
            f"{venda.get_status_display()}).",
            campo="status",
        )
    if not pagamentos:
        raise ErroDeNegocio("Informe ao menos uma forma de pagamento.", campo="pagamentos")

    configuracao, _ = ConfiguracaoLoja.objects.get_or_create(loja=venda.loja)
    _recalcular_totais(venda)

    caixa = caixa_aberto(venda.loja)
    if caixa is None:
        raise CaixaFechado(
            "Não há caixa aberto. Abra o caixa para registrar vendas.", campo="caixa"
        )

    total_informado = sum((quantizar(p["valor"]) for p in pagamentos), Decimal("0.00"))
    total_fiado = sum(
        (quantizar(p["valor"]) for p in pagamentos if p["forma"] == FormaPagamento.FIADO),
        Decimal("0.00"),
    )

    if total_informado < venda.total:
        raise ErroDeNegocio(
            f"Pagamento insuficiente: informado R$ {total_informado}, "
            f"total da venda R$ {venda.total}.",
            campo="pagamentos",
        )

    # Só dinheiro gera troco. Pagar R$ 60 no cartão numa venda de R$ 50 é erro
    # de digitação, não troco.
    total_em_dinheiro = sum(
        (quantizar(p["valor"]) for p in pagamentos if p["forma"] == FormaPagamento.DINHEIRO),
        Decimal("0.00"),
    )
    troco = quantizar(total_informado - venda.total)
    if troco > 0 and troco > total_em_dinheiro:
        raise ErroDeNegocio(
            "O valor informado excede o total da venda e não há dinheiro "
            "suficiente para gerar troco. Confira os valores.",
            campo="pagamentos",
        )

    if total_fiado > 0:
        _validar_fiado(venda, configuracao, total_fiado)

    # --- estoque ---
    for item in venda.itens.select_related("variacao").all():
        registrar_movimento(
            variacao=item.variacao,
            tipo=TipoMovimento.SAIDA,
            quantidade=item.quantidade,
            usuario=usuario,
            custo_unitario=item.custo_unitario,
            motivo=f"Venda #{venda.numero}",
            venda=venda,
            permitir_negativo=configuracao.permitir_venda_sem_estoque,
        )

    # --- pagamentos ---
    troco_restante = troco
    for entrada in pagamentos:
        valor = quantizar(entrada["valor"])
        troco_do_pagamento = Decimal("0.00")
        # O troco é atribuído ao pagamento em dinheiro, para o recibo bater.
        if entrada["forma"] == FormaPagamento.DINHEIRO and troco_restante > 0:
            troco_do_pagamento = min(troco_restante, valor)
            troco_restante -= troco_do_pagamento

        Pagamento.objects.create(
            venda=venda,
            forma=entrada["forma"],
            valor=valor,
            troco=troco_do_pagamento,
            observacao=entrada.get("observacao", ""),
        )

    # --- caixa (somente espécie, líquido do troco) ---
    dinheiro_liquido = quantizar(total_em_dinheiro - troco)
    if dinheiro_liquido > 0:
        MovimentoCaixa.objects.create(
            loja=venda.loja, caixa=caixa, tipo=TipoMovimentoCaixa.VENDA,
            valor=dinheiro_liquido, descricao=f"Venda #{venda.numero}",
            usuario=usuario, venda=venda,
        )

    # --- financeiro ---
    _lancar_financeiro(venda, pagamentos, total_fiado, configuracao)

    venda.caixa = caixa
    venda.status = StatusVenda.FINALIZADA
    venda.finalizada_em = timezone.now()
    venda.save(update_fields=["caixa", "status", "finalizada_em", "atualizado_em"])
    return venda


def _validar_fiado(venda, configuracao, total_fiado: Decimal):
    if not configuracao.permitir_fiado:
        raise ErroDeNegocio("Esta loja não trabalha com fiado.", campo="pagamentos")
    if venda.cliente is None:
        raise ErroDeNegocio(
            "Venda fiada exige cliente identificado.", campo="cliente"
        )
    disponivel = venda.cliente.credito_disponivel
    if total_fiado > disponivel:
        raise ErroDeNegocio(
            f"Limite de crédito insuficiente: disponível R$ {disponivel}, "
            f"solicitado R$ {total_fiado}.",
            campo="pagamentos",
        )


def _lancar_financeiro(venda: Venda, pagamentos, total_fiado: Decimal, configuracao=None):
    """
    Fiado vira conta a receber pendente; o restante entra como receita paga.

    Sem isso, o financeiro não fecharia com o PDV — o relatório de fluxo de
    caixa ignoraria as vendas.
    """
    from apps.financeiro.models import (
        CategoriaFinanceira,
        Lancamento,
        StatusLancamento,
        TipoLancamento,
    )

    hoje = timezone.localdate()
    categoria, _ = CategoriaFinanceira.objects.get_or_create(
        loja=venda.loja, nome="Vendas", defaults={"tipo": TipoLancamento.RECEITA}
    )

    recebido = quantizar(venda.total - total_fiado)
    if recebido > 0:
        Lancamento.objects.create(
            loja=venda.loja, tipo=TipoLancamento.RECEITA, categoria=categoria,
            descricao=f"Venda #{venda.numero}", valor=recebido,
            vencimento=hoje, pago_em=hoje, status=StatusLancamento.PAGO,
            cliente=venda.cliente, venda=venda,
        )

    if total_fiado > 0:
        # Fiado vence conforme o prazo da loja: vencer no mesmo dia marcaria
        # toda venda fiada como atrasada já no dia seguinte.
        prazo = getattr(configuracao, "prazo_fiado_dias", 30) or 0
        Lancamento.objects.create(
            loja=venda.loja, tipo=TipoLancamento.RECEITA, categoria=categoria,
            descricao=f"Fiado — venda #{venda.numero}", valor=total_fiado,
            vencimento=hoje + timedelta(days=prazo), status=StatusLancamento.PENDENTE,
            cliente=venda.cliente, venda=venda,
        )


@transaction.atomic
def cancelar_venda(*, venda: Venda, usuario, motivo: str = "") -> Venda:
    """
    Cancela a venda e desfaz tudo o que a finalização fez.

    Venda ainda aberta só muda de status — não há nada a estornar.
    """
    venda = Venda.objects.select_for_update().get(pk=venda.pk)

    if venda.status == StatusVenda.CANCELADA:
        raise ErroDeNegocio("Esta venda já está cancelada.", campo="status")

    if venda.status == StatusVenda.FINALIZADA:
        # --- devolve o estoque ---
        for item in venda.itens.select_related("variacao").all():
            registrar_movimento(
                variacao=item.variacao,
                tipo=TipoMovimento.ESTORNO,
                quantidade=item.quantidade,
                usuario=usuario,
                custo_unitario=item.custo_unitario,
                motivo=f"Cancelamento da venda #{venda.numero}. {motivo}".strip(),
                venda=venda,
            )

        # --- devolve o dinheiro da gaveta ---
        dinheiro = venda.movimentos_caixa.filter(
            tipo=TipoMovimentoCaixa.VENDA
        ).aggregate(total=Sum("valor"))["total"] or Decimal("0.00")

        if dinheiro > 0:
            caixa = caixa_aberto(venda.loja)
            if caixa is None:
                raise CaixaFechado(
                    "Abra o caixa para cancelar uma venda paga em dinheiro — "
                    "o estorno precisa sair da gaveta.",
                    campo="caixa",
                )
            MovimentoCaixa.objects.create(
                loja=venda.loja, caixa=caixa, tipo=TipoMovimentoCaixa.ESTORNO,
                valor=dinheiro, descricao=f"Estorno da venda #{venda.numero}",
                usuario=usuario, venda=venda,
            )

        # --- desfaz o financeiro ---
        from apps.financeiro.models import Lancamento, StatusLancamento

        Lancamento.objects.filter(venda=venda).exclude(
            status=StatusLancamento.CANCELADO
        ).update(status=StatusLancamento.CANCELADO)

    venda.status = StatusVenda.CANCELADA
    venda.cancelada_em = timezone.now()
    venda.motivo_cancelamento = motivo
    venda.save(update_fields=["status", "cancelada_em", "motivo_cancelamento", "atualizado_em"])
    return venda
