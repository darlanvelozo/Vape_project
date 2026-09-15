"""Paginação padrão da API."""

from rest_framework.pagination import PageNumberPagination


class PaginacaoPadrao(PageNumberPagination):
    page_size = 50
    page_size_query_param = "tamanho_pagina"
    max_page_size = 200
