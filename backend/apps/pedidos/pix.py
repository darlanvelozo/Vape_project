"""
Pix estático: o "copia e cola" e o conteúdo do QR Code (ADR-0004).

É o BR Code do Banco Central — texto no padrão EMV, uma sequência de campos
`ID (2 dígitos) + TAMANHO (2 dígitos) + VALOR`, fechada por um CRC16. Nenhum
terceiro participa: o código leva a chave Pix da própria loja e o valor do
pedido, e o app do banco do cliente faz o resto.

Referência: Manual de Padrões para Iniciação do Pix (BCB), anexo BR Code.
"""

import re
import unicodedata
from decimal import Decimal

from apps.core.exceptions import ErroDeNegocio
from apps.core.utils import quantizar

GUI_PIX = "br.gov.bcb.pix"
LIMITE_NOME = 25
LIMITE_CIDADE = 15
LIMITE_TXID = 25

_EVP = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _campo(identificador: str, valor: str) -> str:
    if len(valor) > 99:
        raise ValueError(f"Campo {identificador} do BR Code passou de 99 caracteres.")
    return f"{identificador}{len(valor):02d}{valor}"


def crc16(texto: str) -> str:
    """CRC16-CCITT (polinômio 0x1021, valor inicial 0xFFFF), em hexa maiúsculo."""
    crc = 0xFFFF
    for byte in texto.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else (crc << 1)
            crc &= 0xFFFF
    return f"{crc:04X}"


def _ascii(texto: str) -> str:
    """Sem acento e só caracteres que todo app de banco aceita."""
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9 .\-]", "", sem_acento).strip()


def normalizar_chave(chave: str) -> str:
    """
    Põe a chave no formato que o Banco Central espera.

    - aleatória (EVP): minúscula, com hífens;
    - e-mail: minúsculo;
    - telefone: `+55DDDNUMERO` — precisa vir com o `+`, porque 11 dígitos
      soltos são indistinguíveis de um CPF;
    - CPF/CNPJ: só dígitos.
    """
    chave = (chave or "").strip()
    if not chave:
        return ""
    if _EVP.match(chave.lower()):
        return chave.lower()
    if "@" in chave:
        if not _EMAIL.match(chave):
            raise ErroDeNegocio("Chave Pix de e-mail inválida.", campo="pix_chave")
        return chave.lower()
    digitos = re.sub(r"\D", "", chave)
    if chave.startswith("+"):
        if len(digitos) < 12:
            raise ErroDeNegocio(
                "Chave Pix de telefone deve ter DDI e DDD: +55 86 99999-9999.",
                campo="pix_chave",
            )
        return f"+{digitos}"
    if len(digitos) in (11, 14):
        return digitos
    raise ErroDeNegocio(
        "Chave Pix não reconhecida. Use a chave aleatória, e-mail, CPF/CNPJ "
        "ou telefone no formato +55 DDD número.",
        campo="pix_chave",
    )


def gerar_brcode(*, chave: str, nome: str, cidade: str, valor: Decimal | None = None,
                 identificador: str = "") -> str:
    """
    Monta o Pix "copia e cola".

    `identificador` vai no campo txid (62.05): o banco mostra no extrato do
    lojista, o que ajuda a casar o Pix recebido com o pedido.
    """
    chave = normalizar_chave(chave)
    nome = _ascii(nome)[:LIMITE_NOME].upper()
    cidade = _ascii(cidade)[:LIMITE_CIDADE].upper()
    if not chave or not nome or not cidade:
        raise ErroDeNegocio(
            "A loja ainda não configurou a chave Pix, o nome do recebedor e a cidade.",
            campo="pix",
        )

    txid = re.sub(r"[^A-Za-z0-9]", "", identificador or "")[:LIMITE_TXID] or "***"

    conta = _campo("00", GUI_PIX) + _campo("01", chave)
    payload = (
        _campo("00", "01")
        + _campo("26", conta)
        + _campo("52", "0000")
        + _campo("53", "986")
    )
    if valor is not None:
        valor = quantizar(valor)
        if valor <= 0:
            raise ErroDeNegocio("O valor do Pix precisa ser positivo.", campo="valor")
        payload += _campo("54", f"{valor:.2f}")
    payload += (
        _campo("58", "BR")
        + _campo("59", nome)
        + _campo("60", cidade)
        + _campo("62", _campo("05", txid))
        + "6304"
    )
    return payload + crc16(payload)
