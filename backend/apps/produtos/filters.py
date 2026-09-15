import django_filters as filtros

from .models import Produto, Variacao


class ProdutoFilter(filtros.FilterSet):
    sem_estoque = filtros.BooleanFilter(method="filtrar_sem_estoque")

    class Meta:
        model = Produto
        fields = ["categoria", "marca", "tipo", "ativo"]

    def filtrar_sem_estoque(self, queryset, nome, valor):
        if valor is None:
            return queryset
        zerados = queryset.filter(variacoes__saldo__lte=0).distinct()
        return zerados if valor else queryset.exclude(pk__in=zerados)


class VariacaoFilter(filtros.FilterSet):
    abaixo_do_minimo = filtros.BooleanFilter(method="filtrar_abaixo_do_minimo")
    produto = filtros.NumberFilter(field_name="produto_id")
    categoria = filtros.NumberFilter(field_name="produto__categoria_id")

    class Meta:
        model = Variacao
        fields = ["produto", "ativo", "categoria"]

    def filtrar_abaixo_do_minimo(self, queryset, nome, valor):
        import django.db.models as modelos

        if valor is None:
            return queryset
        condicao = modelos.Q(estoque_minimo__gt=0, saldo__lte=modelos.F("estoque_minimo"))
        return queryset.filter(condicao) if valor else queryset.exclude(condicao)
