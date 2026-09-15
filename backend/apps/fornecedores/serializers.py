from django.db import transaction
from rest_framework import serializers

from apps.core.serializers import CentavosField, CNPJField
from apps.produtos.models import Variacao

from .models import Compra, Fornecedor, ItemCompra, StatusCompra


class FornecedorSerializer(serializers.ModelSerializer):
    cnpj = CNPJField(required=False, allow_blank=True, max_length=18)
    total_compras = serializers.IntegerField(read_only=True)

    class Meta:
        model = Fornecedor
        fields = [
            "id", "nome", "cnpj", "contato", "telefone", "email",
            "endereco", "cidade", "observacoes", "ativo", "total_compras", "criado_em",
        ]
        read_only_fields = ["id", "criado_em"]


class ItemCompraSerializer(serializers.ModelSerializer):
    custo_unitario_centavos = CentavosField(source="custo_unitario", min_value=0)
    total_centavos = CentavosField(source="total", read_only=True)
    variacao_descricao = serializers.CharField(source="variacao.descricao_completa", read_only=True)

    class Meta:
        model = ItemCompra
        fields = [
            "id", "variacao", "variacao_descricao", "quantidade",
            "custo_unitario_centavos", "total_centavos",
        ]
        read_only_fields = ["id"]


class CompraSerializer(serializers.ModelSerializer):
    itens = ItemCompraSerializer(many=True)
    fornecedor_nome = serializers.CharField(source="fornecedor.nome", read_only=True)
    frete_centavos = CentavosField(source="frete", required=False, min_value=0)
    desconto_centavos = CentavosField(source="desconto", required=False, min_value=0)
    total_centavos = CentavosField(source="total", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    editavel = serializers.BooleanField(read_only=True)

    class Meta:
        model = Compra
        fields = [
            "id", "fornecedor", "fornecedor_nome", "numero_documento", "data",
            "status", "status_display", "frete_centavos", "desconto_centavos",
            "total_centavos", "vencimento", "observacoes", "itens",
            "editavel", "recebida_em", "criado_em",
        ]
        read_only_fields = ["id", "status", "total_centavos", "recebida_em", "criado_em"]

    def validate_fornecedor(self, fornecedor):
        loja = self.context["request"].loja
        if fornecedor.loja_id != loja.id:
            raise serializers.ValidationError("O fornecedor informado não é desta loja.")
        return fornecedor

    def validate_itens(self, itens):
        if not itens:
            raise serializers.ValidationError("Informe ao menos um item.")
        loja = self.context["request"].loja
        ids = [item["variacao"].id for item in itens]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Há variações repetidas na compra.")
        fora_da_loja = Variacao.objects.filter(id__in=ids).exclude(loja=loja).exists()
        if fora_da_loja:
            raise serializers.ValidationError("Há variações que não pertencem a esta loja.")
        return itens

    @transaction.atomic
    def create(self, dados):
        itens = dados.pop("itens")
        compra = Compra.objects.create(**dados)
        self._gravar_itens(compra, itens)
        compra.total = compra.calcular_total()
        compra.save(update_fields=["total"])
        return compra

    @transaction.atomic
    def update(self, instancia, dados):
        if instancia.status != StatusCompra.RASCUNHO:
            raise serializers.ValidationError(
                "Compra recebida ou cancelada não pode ser alterada."
            )
        itens = dados.pop("itens", None)
        for campo, valor in dados.items():
            setattr(instancia, campo, valor)
        if itens is not None:
            instancia.itens.all().delete()
            self._gravar_itens(instancia, itens)
        instancia.total = instancia.calcular_total()
        instancia.save()
        return instancia

    def _gravar_itens(self, compra, itens):
        ItemCompra.objects.bulk_create([
            ItemCompra(
                compra=compra,
                variacao=item["variacao"],
                quantidade=item["quantidade"],
                custo_unitario=item["custo_unitario"],
            )
            for item in itens
        ])


class CancelarCompraSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=200, required=False, allow_blank=True)
