"""Fotos de produtos enviadas pelo painel."""

import base64
import binascii
import secrets
import shutil

from .validacao import ErroValidacao

TAMANHO_MAX_FOTO = 3 * 1024 * 1024
TAMANHO_MAX_MINIATURA = 400 * 1024
ESPACO_LIVRE_MINIMO = 200 * 1024 * 1024

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


def _decodificar(base64_dados, maximo, aviso_tamanho):
    try:
        dados = base64.b64decode(str(base64_dados or ""), validate=True)
    except (binascii.Error, ValueError):
        raise ErroValidacao({"foto": "Arquivo inválido."})
    if not dados:
        raise ErroValidacao({"foto": "Envie uma imagem."})
    if len(dados) > maximo:
        raise ErroValidacao({"foto": aviso_tamanho})
    ext = formato(dados)
    if not ext:
        raise ErroValidacao({"foto": "Use uma foto JPG, PNG ou WEBP."})
    return dados, ext


def salvar(pasta, slug, base64_dados, base64_miniatura=None):
    """Grava a foto (e a miniatura, se veio) e devolve os nomes dos arquivos: (foto, miniatura ou "")."""
    arquivos = [_decodificar(base64_dados, TAMANHO_MAX_FOTO, "A foto deve ter no máximo 3 MB.")]
    if base64_miniatura:
        arquivos.append(_decodificar(base64_miniatura, TAMANHO_MAX_MINIATURA, "A miniatura deve ter no máximo 400 KB."))
    pasta.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(pasta).free < ESPACO_LIVRE_MINIMO:
        raise ErroValidacao({"foto": "Pouco espaço livre no servidor. Remova arquivos antigos antes de enviar fotos."})
    nomes = []
    try:
        for dados, ext in arquivos:
            nome = f"{slug}-{secrets.token_hex(4)}.{ext}"
            (pasta / nome).write_bytes(dados)
            nomes.append(nome)
    except OSError:
        for nome in nomes:
            (pasta / nome).unlink(missing_ok=True)
        raise
    return nomes[0], (nomes[1] if len(nomes) > 1 else "")
