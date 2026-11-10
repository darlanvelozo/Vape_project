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
            "vitrine_publica",
            "vitrine_mostrar_preco",
            "vitrine_mensagem",
            "vitrine_whatsapp",
            "venda_online",
            "pix_chave",
            "pix_nome",
            "pix_cidade",
            "reserva_minutos",
            "aceita_entrega",
            "aceita_retirada",
            "texto_retirada",
        ]

    def validate_pix_chave(self, valor):
        from apps.pedidos.pix import normalizar_chave

        return normalizar_chave(valor)

    def validate_reserva_minutos(self, valor):
        if not 5 <= valor <= 24 * 60:
            raise serializers.ValidationError("Use entre 5 minutos e 24 horas.")
        return valor

    def validate(self, dados):
        atual = self.instance
        def valor(campo):
            return dados.get(campo, getattr(atual, campo, None))

        if valor("venda_online"):
            faltando = [rotulo for campo, rotulo in (
                ("pix_chave", "chave Pix"), ("pix_nome", "nome do recebedor"),
                ("pix_cidade", "cidade"),
            ) if not valor(campo)]
            if faltando:
                raise serializers.ValidationError({
                    "venda_online": [f"Para vender on-line, preencha: {', '.join(faltando)}."]
                })
            if not valor("aceita_entrega") and not valor("aceita_retirada"):
                raise serializers.ValidationError({
                    "venda_online": ["Escolha ao menos entrega ou retirada."]
                })
            if not valor("vitrine_publica"):
                raise serializers.ValidationError({
                    "venda_online": ["Ligue a vitrine pública antes da venda on-line."]
                })
        return dados


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
