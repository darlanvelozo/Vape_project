from rest_framework import serializers

from apps.core.serializers import CNPJField

from .models import ConfiguracaoLoja, Loja


class ConfiguracaoLojaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracaoLoja
        fields = [
            "exigir_cliente_na_venda",
            "permitir_venda_sem_estoque",
            "permitir_fiado",
            "prazo_fiado_dias",
            "alerta_estoque_minimo",
            "mensagem_recibo",
        ]


class LojaSerializer(serializers.ModelSerializer):
    cnpj = CNPJField(required=False, allow_blank=True, max_length=18)
    configuracao = ConfiguracaoLojaSerializer(read_only=True)

    class Meta:
        model = Loja
        fields = [
            "id", "nome", "slug", "cnpj", "telefone", "email",
            "endereco", "cidade", "uf", "cep",
            "plano", "ativa", "limite_usuarios", "limite_produtos",
            "configuracao", "criado_em",
        ]
        read_only_fields = ["id", "slug", "plano", "ativa",
                            "limite_usuarios", "limite_produtos", "criado_em"]
