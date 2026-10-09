"""Pix copia e cola (BR Code estático, padrão EMV® QRCPS do Banco Central) e o QR Code dele.

Segue o "Manual de Padrões para Iniciação do Pix" (BCB): campos ID+tamanho(2 dígitos)+valor, na ordem
00 (formato "01"), 26 (conta: GUI br.gov.bcb.pix + 01 chave), 52 "0000", 53 "986" (BRL), 54 valor, 58 "BR",
59 nome do recebedor (≤25), 60 cidade (≤15), 62 (05 txid) e 63 CRC16-CCITT-FALSE em hexadecimal maiúsculo.
"""

import re
import unicodedata

from . import qrcode
from .validacao import cpf_valido, so_digitos

GUI_PIX = "br.gov.bcb.pix"
NOME_MAX = 25
CIDADE_MAX = 15
CIDADE_PADRAO = "MANAUS"
TXID_MAX = 25
CHAVE_MAX = 77  # o campo 26 inteiro tem no máximo 99 caracteres: 99 − "0014br.gov.bcb.pix" − "01NN"


def crc16(texto):
    """CRC16-CCITT-FALSE (polinômio 0x1021, valor inicial 0xFFFF, sem reflexão, sem XOR final)."""
    crc = 0xFFFF
    for byte in texto.encode("utf-8"):
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return crc


def _campo(id_, valor):
    if len(valor) > 99:
        raise ValueError(f"Campo {id_} do Pix grande demais.")
    return f"{id_}{len(valor):02d}{valor}"


def normalizar_texto(texto, maximo):
    """Sem acentos, em maiúsculas, só letras, números, espaço e . - (o que todo app de banco aceita)."""
    sem_acento = unicodedata.normalize("NFKD", str(texto or ""))
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    limpo = re.sub(r"[^A-Z0-9 .\-]", " ", sem_acento.upper())
    return re.sub(r" +", " ", limpo).strip()[:maximo].strip()


def normalizar_chave(chave):
    """Chave no formato que o Pix espera, ou "" se não for possível saber qual é a chave.

    CPF/CNPJ só com dígitos; telefone como +55DDDNÚMERO; e-mail em minúsculas; chave aleatória (EVP) em minúsculas.
    Um erro aqui mandaria o dinheiro para outra pessoa, então nada é adivinhado: "(92) 99123-4567" e "+55…" são
    telefone, "000.000.000-00" é CPF, e 11 dígitos soltos só valem quando não podem ser as duas coisas.
    """
    texto = str(chave or "").strip()
    if not texto or len(texto) > CHAVE_MAX + 20:
        return ""
    if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", texto):
        return texto.lower()
    if "@" in texto:
        email = texto.lower()
        return email if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) and len(email) <= CHAVE_MAX else ""
    if not re.fullmatch(r"[0-9+()./\s-]+", texto):
        return ""
    digitos = so_digitos(texto)
    com_pais = len(digitos) in (12, 13) and digitos.startswith("55")
    telefone = "+55" + (digitos[2:] if com_pais else digitos)
    if texto.startswith("+"):  # telefone internacional: o Pix só aceita números do Brasil
        return telefone if com_pais else ""
    if "(" in texto:
        return telefone if len(digitos) in (10, 11) else ""
    if re.fullmatch(r"\d{3}\.\d{3}\.\d{3}-\d{2}", texto):
        return digitos if cpf_valido(digitos) else ""
    if re.fullmatch(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14}", texto):
        return digitos  # CNPJ
    if len(digitos) == 11:
        # 11 dígitos soltos podem ser CPF ou celular (DDD + 9 + 8 dígitos): na dúvida, não adivinha
        celular = digitos[0] != "0" and digitos[1] != "0" and digitos[2] == "9"
        cpf = cpf_valido(digitos)
        if cpf != celular:
            return digitos if cpf else telefone
        return ""
    if len(digitos) == 10:
        return telefone
    if com_pais:
        return telefone
    return ""


def configurado(valores):
    """Os dados do recebedor nos ajustes, já normalizados, ou None se faltar chave ou nome."""
    chave = normalizar_chave(valores.get("chave_pix"))
    nome = normalizar_texto(valores.get("pix_nome"), NOME_MAX)
    if not chave or not nome:
        return None
    cidade = normalizar_texto(valores.get("pix_cidade"), CIDADE_MAX) or CIDADE_PADRAO
    return {"chave": chave, "nome": nome, "cidade": cidade}


def pix_ativo(valores):
    return configurado(valores) is not None


def txid_do_pedido(codigo):
    return re.sub(r"[^A-Za-z0-9]", "", str(codigo)).upper()[:TXID_MAX] or "***"


def copia_e_cola(chave, nome, cidade, valor_centavos=None, txid="***"):
    """Payload BR Code estático. valor_centavos None = o pagador digita o valor."""
    conta = _campo("00", GUI_PIX) + _campo("01", chave)
    partes = [_campo("00", "01"), _campo("26", conta), _campo("52", "0000"), _campo("53", "986")]
    if valor_centavos is not None:
        if valor_centavos <= 0:
            raise ValueError("Valor do Pix deve ser positivo.")
        partes.append(_campo("54", f"{valor_centavos // 100}.{valor_centavos % 100:02d}"))
    partes += [_campo("58", "BR"), _campo("59", nome), _campo("60", cidade),
               _campo("62", _campo("05", txid))]
    sem_crc = "".join(partes) + "6304"
    return f"{sem_crc}{crc16(sem_crc):04X}"


def copia_e_cola_do_pedido(valores, codigo, total_centavos):
    """Payload do pedido (valor = total, txid = código sem hífen) ou None se o Pix da loja não estiver configurado."""
    recebedor = configurado(valores)
    if recebedor is None:
        return None
    return copia_e_cola(recebedor["chave"], recebedor["nome"], recebedor["cidade"], total_centavos,
                        txid_do_pedido(codigo))


def qr_svg(payload):
    """QR Code do payload (nível de correção M, margem de 4 módulos, fundo branco)."""
    return qrcode.svg(qrcode.gerar(payload.encode("utf-8"), "M"), margem=4)
