"""
Regras do pedido on-line (ADR-0004).

Ciclo de vida:

    aguardando_pagamento ──(cliente envia comprovante)──▶ aguardando_conferencia
            │  └─(prazo vence)─▶ expirado                         │
            └──────────────(loja aprova o Pix)─────────────────────┴─▶ preparando
    preparando ─▶ pronto_retirada | saiu_entrega ─▶ entregue
    qualquer um ─▶ cancelado

A **reserva** não escreve em `Variacao.saldo` (só `apps.estoque.servicos`
escreve). O disponível é `saldo − itens de pedidos que ainda reservam`, e a
criação do pedido trava as linhas de variação para que dois clientes não
levem a mesma última unidade.
"""

from collections import defaultdict
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.utils import timezone

from apps.core.exceptions import ErroDeNegocio
from apps.core.utils import apenas_digitos, quantizar
from apps.produtos.models import Variacao

from .models import (
    STATUS_PAGOS,
    ItemPedidoOnline,
    PedidoOnline,
    StatusPedido,
    TipoEntrega,
    gerar_codigo,
)

MAXIMO_POR_ITEM = 20
MAXIMO_DE_ITENS = 30
# Quantos pedidos sem pagamento um mesmo telefone pode ter de uma vez —
# sem isso, um curioso reserva o estoque inteiro e ninguém mais compra.
MAXIMO_PENDENTES_POR_TELEFONE = 3
# Comprovante enviado depois do prazo ainda é aceito por este tempo: o
# cliente que pagou no minuto 31 não pode ficar sem caminho.
TOLERANCIA_COMPROVANTE = timedelta(hours=24)


# ------------------------------------------------------------------
# Telefone
# ------------------------------------------------------------------


def normalizar_telefone(telefone: str) -> str:
    """'+55 (86) 99567-5461' → '86995675461'. Levanta erro se não tiver DDD."""
    digitos = apenas_digitos(telefone)
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        digitos = digitos[2:]
    if len(digitos) not in (10, 11):
        raise ErroDeNegocio("Informe o telefone com DDD.", campo="telefone")
    return digitos


# ------------------------------------------------------------------
# Reserva
# ------------------------------------------------------------------


def _filtro_reservando(agora=None) -> Q:
    """Pedido que ainda segura estoque."""
    agora = agora or timezone.now()
    return Q(status=StatusPedido.AGUARDANDO_CONFERENCIA) | Q(
        status=StatusPedido.AGUARDANDO_PAGAMENTO, expira_em__gt=agora
    )


def reservas_ativas(loja, variacao_ids=None) -> dict[int, int]:
    """Unidades reservadas por variação, em pedidos ainda sem aprovação."""
    filtro = Q(pedido__loja=loja) & Q(
        pedido__in=PedidoOnline.objects.filter(_filtro_reservando(), loja=loja)
    )
    if variacao_ids is not None:
        filtro &= Q(variacao_id__in=list(variacao_ids))
    linhas = (
        ItemPedidoOnline.objects.filter(filtro)
        .values("variacao_id").annotate(total=Sum("quantidade"))
    )
    return {linha["variacao_id"]: linha["total"] for linha in linhas}


def expirar_vencidos(loja) -> int:
    """Marca como expirado o que passou do prazo sem comprovante."""
    return PedidoOnline.objects.filter(
        loja=loja,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
        expira_em__lte=timezone.now(),
    ).update(status=StatusPedido.EXPIRADO, atualizado_em=timezone.now())


def _configuracao_de_venda(loja):
    configuracao = getattr(loja, "configuracao", None)
    if (configuracao is None or not configuracao.vitrine_publica
            or not configuracao.venda_online):
        raise ErroDeNegocio("Esta loja não está vendendo pela vitrine.", campo="loja")
    return configuracao


# ------------------------------------------------------------------
# Criação (cliente, na vitrine)
# ------------------------------------------------------------------


def _agrupar_itens(itens) -> dict[int, int]:
    if not itens:
        raise ErroDeNegocio("O pedido está vazio.", campo="itens")
    agrupado: dict[int, int] = defaultdict(int)
    for entrada in itens:
        try:
            variacao_id = int(entrada["variacao"])
            quantidade = int(entrada["quantidade"])
        except (KeyError, TypeError, ValueError) as erro:
            raise ErroDeNegocio("Item do pedido inválido.", campo="itens") from erro
        if quantidade < 1:
            raise ErroDeNegocio("Quantidade inválida.", campo="itens")
        agrupado[variacao_id] += quantidade
    if len(agrupado) > MAXIMO_DE_ITENS:
        raise ErroDeNegocio("Pedido com itens demais.", campo="itens")
    for quantidade in agrupado.values():
        if quantidade > MAXIMO_POR_ITEM:
            raise ErroDeNegocio(
                f"No máximo {MAXIMO_POR_ITEM} unidades por item.", campo="itens"
            )
    return agrupado


@transaction.atomic
def criar_pedido(*, loja, telefone, codinome, itens, tipo_entrega,
                 declarou_maioridade, latitude=None, longitude=None,
                 precisao_m=None, endereco="", referencia="", observacoes="") -> PedidoOnline:
    configuracao = _configuracao_de_venda(loja)

    if not declarou_maioridade:
        raise ErroDeNegocio(
            "A venda é proibida para menores de 18 anos. Confirme sua idade.",
            campo="declarou_maioridade",
        )
    telefone = normalizar_telefone(telefone)
    codinome = (codinome or "").strip()
    if len(codinome) < 2:
        raise ErroDeNegocio("Informe um nome ou codinome.", campo="codinome")

    if tipo_entrega == TipoEntrega.ENTREGA:
        if not configuracao.aceita_entrega:
            raise ErroDeNegocio("Esta loja não faz entrega.", campo="tipo_entrega")
        tem_gps = latitude is not None and longitude is not None
        if not tem_gps and not (endereco or "").strip():
            raise ErroDeNegocio(
                "Para entrega, compartilhe a localização ou escreva o endereço.",
                campo="endereco",
            )
    elif tipo_entrega == TipoEntrega.RETIRADA:
        if not configuracao.aceita_retirada:
            raise ErroDeNegocio("Esta loja não trabalha com retirada.", campo="tipo_entrega")
        latitude = longitude = precisao_m = None
    else:
        raise ErroDeNegocio("Escolha entrega ou retirada.", campo="tipo_entrega")

    pendentes = PedidoOnline.objects.filter(
        _filtro_reservando(), loja=loja, telefone=telefone,
        status=StatusPedido.AGUARDANDO_PAGAMENTO,
    ).count()
    if pendentes >= MAXIMO_PENDENTES_POR_TELEFONE:
        raise ErroDeNegocio(
            "Você já tem pedidos aguardando pagamento. Pague ou cancele um deles "
            "antes de fazer outro.",
            campo="telefone",
        )

    quantidades = _agrupar_itens(itens)

    # Trava as linhas em ordem de pk (evita deadlock entre dois pedidos) e
    # só depois lê as reservas: o que outra transação reservou já está
    # gravado quando a trava for liberada.
    variacoes = {
        v.pk: v for v in Variacao.objects.select_for_update(of=("self",))
        .select_related("produto")
        .filter(loja=loja, pk__in=quantidades, ativo=True, produto__ativo=True)
        .order_by("pk")
    }
    if len(variacoes) != len(quantidades):
        raise ErroDeNegocio(
            "Algum item do pedido não está mais disponível. Atualize a página.",
            campo="itens",
        )
    reservado = reservas_ativas(loja, variacoes.keys())

    total = quantizar(0)
    linhas = []
    for variacao_id, quantidade in quantidades.items():
        variacao = variacoes[variacao_id]
        disponivel = variacao.saldo - reservado.get(variacao_id, 0)
        if quantidade > disponivel:
            if disponivel <= 0:
                mensagem = f"{variacao.descricao_completa} acabou de esgotar."
            else:
                mensagem = (
                    f"Só restam {disponivel} unidade(s) de {variacao.descricao_completa}."
                )
            raise ErroDeNegocio(mensagem, campo="itens")
        preco = quantizar(variacao.preco_venda)
        total += preco * quantidade
        linhas.append((variacao, quantidade, preco))

    agora = timezone.now()
    pedido = None
    for _ in range(5):
        try:
            with transaction.atomic():
                pedido = PedidoOnline.objects.create(
                    loja=loja, codigo=gerar_codigo(),
                    telefone=telefone, codinome=codinome[:60],
                    declarou_maioridade=True,
                    tipo_entrega=tipo_entrega,
                    latitude=latitude, longitude=longitude, precisao_m=precisao_m,
                    endereco=(endereco or "").strip()[:200],
                    referencia=(referencia or "").strip()[:200],
                    observacoes=(observacoes or "").strip()[:300],
                    total=quantizar(total),
                    expira_em=agora + timedelta(minutes=configuracao.reserva_minutos),
                )
            break
        except IntegrityError:
            continue  # código repetido na loja: sorteia outro
    if pedido is None:
        raise ErroDeNegocio("Não foi possível registrar o pedido. Tente de novo.")

    ItemPedidoOnline.objects.bulk_create([
        ItemPedidoOnline(
            pedido=pedido, variacao=variacao, descricao=variacao.descricao_completa,
            quantidade=quantidade, preco_unitario=preco,
        )
        for variacao, quantidade, preco in linhas
    ])
    return pedido


# ------------------------------------------------------------------
# Cliente: comprovante e desistência
# ------------------------------------------------------------------


@transaction.atomic
def informar_pagamento(*, pedido: PedidoOnline, comprovante=None) -> PedidoOnline:
    """O cliente avisa que pagou, com ou sem a imagem do comprovante."""
    from apps.core.imagens import processar

    pedido = PedidoOnline.objects.select_for_update().get(pk=pedido.pk)
    agora = timezone.now()
    aceita = pedido.status in (
        StatusPedido.AGUARDANDO_PAGAMENTO, StatusPedido.AGUARDANDO_CONFERENCIA
    ) or (
        pedido.status == StatusPedido.EXPIRADO
        and agora - pedido.expira_em <= TOLERANCIA_COMPROVANTE
    )
    if not aceita:
        raise ErroDeNegocio(
            "Este pedido não está aguardando pagamento.", campo="status"
        )

    if comprovante is not None:
        pedido.comprovante.save("comprovante.jpg", processar(comprovante), save=False)
        pedido.comprovante_enviado_em = agora
    pedido.status = StatusPedido.AGUARDANDO_CONFERENCIA
    pedido.save()
    return pedido


@transaction.atomic
def cliente_cancelar(*, pedido: PedidoOnline) -> PedidoOnline:
    pedido = PedidoOnline.objects.select_for_update().get(pk=pedido.pk)
    if pedido.status != StatusPedido.AGUARDANDO_PAGAMENTO:
        raise ErroDeNegocio(
            "Este pedido não pode mais ser cancelado por aqui. Fale com a loja.",
            campo="status",
        )
    pedido.status = StatusPedido.CANCELADO
    pedido.cancelado_em = timezone.now()
    pedido.motivo_cancelamento = "Cancelado pelo cliente."
    pedido.save()
    return pedido


# ------------------------------------------------------------------
# Loja: aprovação, entrega e cancelamento
# ------------------------------------------------------------------


def _cliente_do_pedido(pedido: PedidoOnline):
    from apps.clientes.models import Cliente

    cliente = (
        Cliente.objects.filter(loja=pedido.loja, telefone=pedido.telefone)
        .order_by("-ativo", "pk").first()
    )
    if cliente is None:
        cliente = Cliente.objects.create(
            loja=pedido.loja, nome=pedido.codinome, telefone=pedido.telefone,
            observacoes=f"Cadastrado pela vitrine (pedido {pedido.codigo}).",
        )
    return cliente


@transaction.atomic
def aprovar_pedido(*, pedido: PedidoOnline, usuario) -> PedidoOnline:
    """
    O atendente conferiu o Pix no banco: vira venda finalizada.

    Usa os mesmos serviços do PDV — estoque baixa com trava, financeiro recebe
    a receita, recibo e relatórios enxergam a venda como qualquer outra.
    """
    from apps.vendas.models import FormaPagamento
    from apps.vendas.servicos import criar_venda, finalizar_venda

    pedido = PedidoOnline.objects.select_for_update().get(pk=pedido.pk)
    if pedido.status not in (
        StatusPedido.AGUARDANDO_PAGAMENTO,
        StatusPedido.AGUARDANDO_CONFERENCIA,
        StatusPedido.EXPIRADO,
    ):
        raise ErroDeNegocio(
            f"Pedido {pedido.get_status_display().lower()} não pode ser aprovado.",
            campo="status",
        )

    itens = [
        {"variacao": item.variacao, "quantidade": item.quantidade,
         "preco_unitario": item.preco_unitario}
        for item in pedido.itens.select_related("variacao")
    ]
    venda = criar_venda(
        loja=pedido.loja, usuario=usuario, itens=itens,
        cliente=_cliente_do_pedido(pedido),
        observacoes=f"Pedido on-line {pedido.codigo} ({pedido.get_tipo_entrega_display()}).",
    )
    finalizar_venda(
        venda=venda, usuario=usuario, exigir_caixa=False,
        pagamentos=[{
            "forma": FormaPagamento.PIX, "valor": venda.total,
            "observacao": f"Pix do pedido on-line {pedido.codigo}",
        }],
    )

    pedido.venda = venda
    pedido.status = StatusPedido.PREPARANDO
    pedido.aprovado_por = usuario
    pedido.pago_em = timezone.now()
    pedido.save()
    return pedido


TRANSICOES_DE_ENTREGA = {
    TipoEntrega.ENTREGA: (StatusPedido.PREPARANDO, StatusPedido.SAIU_ENTREGA,
                          StatusPedido.ENTREGUE),
    TipoEntrega.RETIRADA: (StatusPedido.PREPARANDO, StatusPedido.PRONTO_RETIRADA,
                           StatusPedido.ENTREGUE),
}


@transaction.atomic
def atualizar_entrega(*, pedido: PedidoOnline, status=None, previsao_entrega=...,
                      recado_loja=None) -> PedidoOnline:
    """
    A loja move o pedido pago entre preparando → a caminho/pronto → entregue,
    e informa previsão e recado. Voltar um passo é permitido (clique errado
    acontece); sair da trilha do tipo de recebimento, não.
    """
    pedido = PedidoOnline.objects.select_for_update().get(pk=pedido.pk)
    if pedido.status not in STATUS_PAGOS:
        raise ErroDeNegocio(
            "Só pedido pago tem acompanhamento de entrega.", campo="status"
        )

    if status is not None and status != pedido.status:
        permitidos = TRANSICOES_DE_ENTREGA[pedido.tipo_entrega]
        if status not in permitidos:
            raise ErroDeNegocio(
                "Status não combina com o tipo de recebimento do pedido.", campo="status"
            )
        agora = timezone.now()
        pedido.status = status
        if status == StatusPedido.SAIU_ENTREGA:
            pedido.saiu_em = agora
        if status == StatusPedido.ENTREGUE:
            pedido.entregue_em = agora
        else:
            pedido.entregue_em = None

    if previsao_entrega is not ...:
        pedido.previsao_entrega = previsao_entrega
    if recado_loja is not None:
        pedido.recado_loja = recado_loja.strip()[:200]
    pedido.save()
    return pedido


@transaction.atomic
def cancelar_pedido(*, pedido: PedidoOnline, usuario, motivo: str = "") -> PedidoOnline:
    """Cancela pela loja. Pedido já pago estorna a venda (estoque e financeiro)."""
    from apps.vendas.models import StatusVenda
    from apps.vendas.servicos import cancelar_venda

    pedido = PedidoOnline.objects.select_for_update().get(pk=pedido.pk)
    if pedido.status in (StatusPedido.CANCELADO, StatusPedido.ENTREGUE):
        raise ErroDeNegocio(
            f"Pedido {pedido.get_status_display().lower()} não pode ser cancelado.",
            campo="status",
        )
    if pedido.venda_id and pedido.venda.status != StatusVenda.CANCELADA:
        cancelar_venda(
            venda=pedido.venda, usuario=usuario,
            motivo=f"Pedido on-line {pedido.codigo} cancelado. {motivo}".strip(),
        )
    pedido.status = StatusPedido.CANCELADO
    pedido.cancelado_em = timezone.now()
    pedido.motivo_cancelamento = (motivo or "Cancelado pela loja.").strip()[:200]
    pedido.save()
    return pedido
