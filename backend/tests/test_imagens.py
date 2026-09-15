"""
Upload de imagem do catálogo.

É a única entrada de arquivo do sistema, então o foco é o que chega torto:
arquivo que não é imagem, foto gigante de celular, PNG transparente, e a
imagem de uma loja aparecendo na vitrine de outra.
"""

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.core.exceptions import ErroDeNegocio
from apps.core.imagens import LADO_MAXIMO, processar
from apps.produtos.models import Produto

pytestmark = pytest.mark.django_db


def imagem_falsa(largura=1200, altura=900, formato="JPEG", modo="RGB", cor=(200, 30, 60)):
    buffer = BytesIO()
    Image.new(modo, (largura, altura), cor).save(buffer, format=formato)
    buffer.seek(0)
    extensao = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[formato]
    return SimpleUploadedFile(
        f"foto.{extensao}", buffer.getvalue(), content_type=f"image/{extensao}"
    )


class TestProcessamento:
    def test_reduz_foto_grande(self):
        """Foto de celular chega com milhares de pixels; a vitrine não precisa."""
        processada = processar(imagem_falsa(4000, 3000))
        imagem = Image.open(processada)

        assert max(imagem.size) == LADO_MAXIMO
        assert imagem.size == (LADO_MAXIMO, int(LADO_MAXIMO * 3 / 4))

    def test_nao_amplia_imagem_pequena(self):
        imagem = Image.open(processar(imagem_falsa(300, 200)))
        assert imagem.size == (300, 200)

    def test_converte_tudo_para_jpeg(self):
        for formato in ("PNG", "WEBP", "JPEG"):
            imagem = Image.open(processar(imagem_falsa(formato=formato)))
            assert imagem.format == "JPEG"

    def test_png_transparente_ganha_fundo_branco(self):
        """Sem o fundo, a transparência vira preto ao salvar em JPEG."""
        buffer = BytesIO()
        Image.new("RGBA", (200, 200), (255, 0, 0, 0)).save(buffer, format="PNG")
        buffer.seek(0)
        arquivo = SimpleUploadedFile("t.png", buffer.getvalue(), content_type="image/png")

        imagem = Image.open(processar(arquivo))
        assert imagem.mode == "RGB"
        assert imagem.getpixel((100, 100)) == (255, 255, 255)

    def test_recusa_arquivo_que_nao_e_imagem(self):
        arquivo = SimpleUploadedFile(
            "virus.jpg", b"isto nao e uma imagem", content_type="image/jpeg"
        )
        with pytest.raises(ErroDeNegocio, match="não é uma imagem"):
            processar(arquivo)

    def test_recusa_arquivo_grande_demais(self):
        from apps.core.imagens import TAMANHO_MAXIMO_BYTES

        arquivo = SimpleUploadedFile("g.jpg", b"x" * (TAMANHO_MAXIMO_BYTES + 1))
        with pytest.raises(ErroDeNegocio, match="limite"):
            processar(arquivo)

    def test_o_arquivo_final_e_menor_que_o_enviado(self):
        original = imagem_falsa(3000, 2000)
        tamanho_original = original.size
        processada = processar(original)
        assert processada.size < tamanho_original


class TestUploadPelaApi:
    def test_dono_envia_foto_do_produto(self, api_dono, loja):
        produto = Produto.objects.create(loja=loja, nome="Elf Bar BC10000")

        resposta = api_dono.patch(
            f"/api/produtos/{produto.id}/",
            {"imagem": imagem_falsa()},
            format="multipart",
        )
        assert resposta.status_code == 200
        assert resposta.json()["imagem_url"], "a URL precisa voltar para a tela exibir"

        produto.refresh_from_db()
        assert produto.imagem
        assert produto.imagem.name.startswith(f"produtos/{loja.slug}/")
        assert produto.imagem.name.endswith(".jpg")

    def test_nome_do_arquivo_nao_vem_do_usuario(self, api_dono, loja):
        """Nome enviado pode ter acento, espaço ou caminho — não vai para o disco."""
        produto = Produto.objects.create(loja=loja, nome="Produto")
        arquivo = imagem_falsa()
        arquivo.name = "../../etc/foto do José.jpg"

        api_dono.patch(f"/api/produtos/{produto.id}/", {"imagem": arquivo}, format="multipart")

        produto.refresh_from_db()
        assert ".." not in produto.imagem.name
        assert " " not in produto.imagem.name

    def test_arquivo_invalido_devolve_mensagem_util(self, api_dono, loja):
        produto = Produto.objects.create(loja=loja, nome="Produto")
        arquivo = SimpleUploadedFile("t.jpg", b"nao sou imagem", content_type="image/jpeg")

        resposta = api_dono.patch(
            f"/api/produtos/{produto.id}/", {"imagem": arquivo}, format="multipart"
        )
        assert resposta.status_code == 400
        assert "imagem" in str(resposta.json()).lower()

    def test_vendedor_nao_envia_foto(self, api_vendedor, loja):
        produto = Produto.objects.create(loja=loja, nome="Produto")
        resposta = api_vendedor.patch(
            f"/api/produtos/{produto.id}/", {"imagem": imagem_falsa()}, format="multipart"
        )
        assert resposta.status_code == 403

    def test_remover_a_foto(self, api_dono, loja):
        produto = Produto.objects.create(loja=loja, nome="Produto")
        api_dono.patch(f"/api/produtos/{produto.id}/", {"imagem": imagem_falsa()},
                       format="multipart")

        resposta = api_dono.delete(f"/api/produtos/{produto.id}/imagem/")
        assert resposta.status_code == 200
        assert resposta.json()["imagem_url"] is None

        produto.refresh_from_db()
        assert not produto.imagem

    def test_produto_de_outra_loja_nao_recebe_foto(self, api_dono, outra_loja):
        alheio = Produto.objects.create(loja=outra_loja, nome="Produto B")
        resposta = api_dono.patch(
            f"/api/produtos/{alheio.id}/", {"imagem": imagem_falsa()}, format="multipart"
        )
        assert resposta.status_code == 404

    def test_editar_produto_sem_mandar_foto_nao_apaga_a_existente(self, api_dono, loja):
        """PATCH de nome não pode limpar a imagem já enviada."""
        produto = Produto.objects.create(loja=loja, nome="Produto")
        api_dono.patch(f"/api/produtos/{produto.id}/", {"imagem": imagem_falsa()},
                       format="multipart")
        produto.refresh_from_db()
        nome_do_arquivo = produto.imagem.name

        api_dono.patch(f"/api/produtos/{produto.id}/", {"nome": "Outro nome"}, format="json")

        produto.refresh_from_db()
        assert produto.imagem.name == nome_do_arquivo


class TestImagemNaVitrine:
    def test_vitrine_traz_a_url_da_foto(self, api_dono, loja, variacao):
        configuracao = loja.configuracao
        configuracao.vitrine_publica = True
        configuracao.save()

        api_dono.patch(
            f"/api/produtos/{variacao.produto_id}/",
            {"imagem": imagem_falsa()},
            format="multipart",
        )

        from rest_framework.test import APIClient

        corpo = APIClient().get(f"/api/vitrine/{loja.slug}/").json()
        assert corpo["produtos"][0]["imagem_url"]

    def test_produto_sem_foto_vem_com_url_nula(self, api_dono, loja, variacao):
        configuracao = loja.configuracao
        configuracao.vitrine_publica = True
        configuracao.save()

        from rest_framework.test import APIClient

        corpo = APIClient().get(f"/api/vitrine/{loja.slug}/").json()
        assert corpo["produtos"][0]["imagem_url"] is None
