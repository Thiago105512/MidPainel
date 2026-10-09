"""Fotos de produtos enviadas pelo painel."""

import base64
import binascii
import secrets

from .regras import ErroValidacao

TAMANHO_MAX_FOTO = 3 * 1024 * 1024

# Identifica o formato pelos primeiros bytes, não pelo que o navegador declara.
ASSINATURAS = [
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"RIFF", "webp"),
]

TIPOS = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def formato(dados):
    for assinatura, ext in ASSINATURAS:
        if dados.startswith(assinatura):
            if ext == "webp" and dados[8:12] != b"WEBP":
                continue
            return ext
    return None


def salvar(pasta, slug, base64_dados):
    try:
        dados = base64.b64decode(str(base64_dados or ""), validate=True)
    except (binascii.Error, ValueError):
        raise ErroValidacao({"foto": "Arquivo inválido."})
    if not dados:
        raise ErroValidacao({"foto": "Envie uma imagem."})
    if len(dados) > TAMANHO_MAX_FOTO:
        raise ErroValidacao({"foto": "A foto deve ter no máximo 3 MB."})
    ext = formato(dados)
    if not ext:
        raise ErroValidacao({"foto": "Use uma foto JPG, PNG ou WEBP."})
    pasta.mkdir(parents=True, exist_ok=True)
    nome = f"{slug}-{secrets.token_hex(4)}.{ext}"
    (pasta / nome).write_bytes(dados)
    return nome
