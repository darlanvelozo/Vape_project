"""
Processamento das imagens do catálogo.

Foto tirada no celular chega com 3 a 8 MB e 4000 px de largura. Servida
assim, a vitrine ficaria pesada justamente para quem a abre — o cliente, no
celular, em rede de rua. Toda imagem é reduzida e recomprimida no upload;
o que vai para o disco é sempre um JPEG pequeno.
"""

import uuid
from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image, ImageOps, UnidentifiedImageError

from .exceptions import ErroDeNegocio

# Um lado maior que isto não melhora nada numa vitrine de celular.
LADO_MAXIMO = 900
QUALIDADE = 82
TAMANHO_MAXIMO_BYTES = 10 * 1024 * 1024  # 10 MB no upload, antes de reduzir
FORMATOS_ACEITOS = {"JPEG", "PNG", "WEBP", "HEIF", "HEIC", "MPO"}


def caminho_da_imagem(instancia, nome_original: str) -> str:
    """
    Guarda em `produtos/<loja>/<uuid>.jpg`.

    O nome vem de UUID, não do arquivo enviado: nome original pode conter
    acento, espaço ou caminho, e dois produtos podem mandar "foto.jpg".
    """
    loja = getattr(instancia, "loja", None)
    pasta = loja.slug if loja else "sem-loja"
    extensao = Path(nome_original).suffix.lower() or ".jpg"
    if extensao not in (".jpg", ".jpeg", ".png", ".webp"):
        extensao = ".jpg"
    return f"produtos/{pasta}/{uuid.uuid4().hex}{extensao}"


def processar(arquivo):
    """
    Valida e reduz a imagem enviada.

    Devolve um arquivo pronto para o ImageField. Levanta `ErroDeNegocio` com
    mensagem em português quando o arquivo não é uma imagem utilizável —
    o usuário precisa entender o que houve, não ver um erro 500.
    """
    if arquivo is None:
        return None

    if arquivo.size > TAMANHO_MAXIMO_BYTES:
        limite = TAMANHO_MAXIMO_BYTES // (1024 * 1024)
        raise ErroDeNegocio(
            f"A imagem tem {arquivo.size / 1024 / 1024:.1f} MB e o limite é {limite} MB.",
            campo="imagem",
        )

    try:
        imagem = Image.open(arquivo)
        imagem.verify()  # detecta arquivo corrompido ou que só finge ser imagem
        arquivo.seek(0)
        imagem = Image.open(arquivo)
    except (UnidentifiedImageError, OSError) as erro:
        raise ErroDeNegocio(
            "O arquivo enviado não é uma imagem válida.", campo="imagem"
        ) from erro

    if imagem.format not in FORMATOS_ACEITOS:
        raise ErroDeNegocio(
            f"Formato {imagem.format or 'desconhecido'} não suportado. "
            "Use JPG, PNG ou WEBP.",
            campo="imagem",
        )

    # `exif_transpose` respeita a orientação da câmera: sem isto, foto tirada
    # na vertical aparece deitada na vitrine.
    imagem = ImageOps.exif_transpose(imagem)

    # Transparência e modos exóticos viram fundo branco ao salvar em JPEG.
    if imagem.mode in ("RGBA", "LA", "P"):
        fundo = Image.new("RGB", imagem.size, (255, 255, 255))
        convertida = imagem.convert("RGBA")
        fundo.paste(convertida, mask=convertida.split()[-1])
        imagem = fundo
    elif imagem.mode != "RGB":
        imagem = imagem.convert("RGB")

    imagem.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.Resampling.LANCZOS)

    saida = BytesIO()
    imagem.save(saida, format="JPEG", quality=QUALIDADE, optimize=True, progressive=True)
    saida.seek(0)

    nome = Path(getattr(arquivo, "name", "imagem")).stem[:40] or "imagem"
    return InMemoryUploadedFile(
        saida, "ImageField", f"{nome}.jpg", "image/jpeg", saida.getbuffer().nbytes, None
    )
