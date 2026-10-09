"""TOTP (RFC 6238): HMAC-SHA1, 6 dígitos, passos de 30 s, janela de ±1 passo e proteção contra reuso."""

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote, urlencode

PASSO_S = 30
DIGITOS = 6
JANELA = 1
EMISSOR = "Tipiti"


def gerar_segredo():
    """20 bytes aleatórios em base32 (sem '='), o formato que os aplicativos autenticadores esperam."""
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _chave(segredo):
    texto = segredo.strip().replace(" ", "").upper()
    return base64.b32decode(texto + "=" * (-len(texto) % 8))


def codigo(segredo, passo):
    """HOTP(K, passo) com truncamento dinâmico (RFC 4226)."""
    digest = hmac.new(_chave(segredo), struct.pack(">Q", passo), hashlib.sha1).digest()
    deslocamento = digest[-1] & 0x0F
    numero = struct.unpack(">I", digest[deslocamento:deslocamento + 4])[0] & 0x7FFFFFFF
    return str(numero % 10 ** DIGITOS).zfill(DIGITOS)


def passo_atual(agora=None):
    return int((time.time() if agora is None else agora) // PASSO_S)


def verificar(segredo, informado, ultimo_passo=None, agora=None):
    """Devolve o passo aceito (int) ou None. Recusa passos já usados (≤ ultimo_passo): um código não vale duas vezes."""
    if not segredo or not isinstance(informado, str):
        return None
    informado = informado.strip().replace(" ", "")
    if len(informado) != DIGITOS or not informado.isdigit():
        return None
    atual = passo_atual(agora)
    aceito = None
    for passo in range(atual - JANELA, atual + JANELA + 1):
        # compara todos os passos da janela, sem sair antes, em tempo constante
        if hmac.compare_digest(codigo(segredo, passo), informado) and aceito is None:
            aceito = passo
    if aceito is None or (ultimo_passo is not None and aceito <= ultimo_passo):
        return None
    return aceito


def otpauth_url(segredo, conta):
    rotulo = quote(f"{EMISSOR}:{conta}", safe=":@")
    params = urlencode({"secret": segredo, "issuer": EMISSOR, "algorithm": "SHA1", "digits": DIGITOS,
                        "period": PASSO_S})
    return f"otpauth://totp/{rotulo}?{params}"
