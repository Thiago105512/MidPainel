"""Configurações da loja editáveis no painel (guardadas no banco)."""

import re
from datetime import datetime

from . import config, horario, pix
from .legal import PADROES_EMPRESA, validar_campo as validar_campo_empresa
from .validacao import ErroValidacao, so_digitos

PADROES = {
    "whatsapp": "",
    "whatsapp_mensagem": "Olá! Vim pelo site da Tipiti.",
    "chave_pix": "",
    "cambio_usd": "5.50",
    "cambio_cny": "0.76",
    "impostos_pct": "60",
    "taxa_pagamento_pct": "4.99",
    "margem_pct": "35",
    "horario_corte": "",   # "HH:MM" (horário de Manaus): pedidos até essa hora, em dia útil, saem no mesmo dia
    "prova_social": "1",   # "1" mostra compras recentes reais na loja; "0" desliga
    "pix_nome": "",        # nome do recebedor no Pix copia e cola (≤25, sem acentos, maiúsculas)
    "pix_cidade": "MANAUS",  # cidade do recebedor (≤15, sem acentos, maiúsculas)
}
PADROES.update(PADROES_EMPRESA)  # identificação da loja e encarregado LGPD (legal.py)


def obter(conn):
    valores = dict(PADROES)
    if config.WHATSAPP:
        valores["whatsapp"] = so_digitos(config.WHATSAPP)
    valores.update({r["chave"]: r["valor"] for r in conn.execute("SELECT chave, valor FROM ajustes")})
    return valores


def normalizar_whatsapp(numero):
    d = so_digitos(numero)
    if not d:
        return ""
    if len(d) in (10, 11):  # DDD + número, sem o código do país
        d = "55" + d
    if not (len(d) in (12, 13) and d.startswith("55")):
        raise ErroValidacao({"whatsapp": "Informe o WhatsApp com DDD, ex.: (92) 99123-4567."})
    return d


def salvar(conn, dados):
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    novos, erros = {}, {}
    for chave, valor in dados.items():
        if chave not in PADROES:
            continue
        texto = str(valor if valor is not None else "").strip()
        if chave in PADROES_EMPRESA:
            texto = validar_campo_empresa(chave, valor, erros)
        elif chave == "whatsapp":
            try:
                texto = normalizar_whatsapp(texto)
            except ErroValidacao as e:
                erros.update(e.campos)
        elif chave == "whatsapp_mensagem":
            texto = texto[:300]
        elif chave == "chave_pix":
            if len(texto) > 120:  # cortar geraria uma chave errada; melhor recusar
                erros[chave] = "A chave Pix deve ter no máximo 120 caracteres."
            elif texto and not pix.normalizar_chave(texto):
                erros[chave] = ("Não deu para reconhecer a chave Pix. Use o e-mail, o CPF (000.000.000-00), o CNPJ, "
                                "o celular com DDD entre parênteses — (92) 99123-4567 — ou a chave aleatória.")
        elif chave == "horario_corte":
            if texto and not re.fullmatch(r"([01][0-9]|2[0-3]):[0-5][0-9]", texto):
                erros[chave] = "Use o formato HH:MM (ex.: 14:00), ou deixe vazio."
        elif chave in ("pix_nome", "pix_cidade"):
            maximo = pix.NOME_MAX if chave == "pix_nome" else pix.CIDADE_MAX
            texto = pix.normalizar_texto(texto, 200)
            if len(texto) > maximo:
                erros[chave] = f"Use no máximo {maximo} caracteres."
            elif chave == "pix_cidade" and not texto:
                texto = pix.CIDADE_PADRAO
        elif chave == "prova_social":
            if valor in (True, 1, "1", "true"):
                texto = "1"
            elif valor in (False, 0, "0", "false", None, ""):
                texto = "0"
            else:
                erros[chave] = "Use 1 (ligado) ou 0 (desligado)."
        else:
            try:
                numero = float(texto.replace(",", "."))
                if not 0 <= numero <= 1000:
                    raise ValueError
                texto = f"{numero:g}"
            except ValueError:
                erros[chave] = "Use um número."
        novos[chave] = texto
    if erros:
        raise ErroValidacao(erros)
    conn.executemany("INSERT INTO ajustes (chave, valor) VALUES (?, ?) ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor",
                     list(novos.items()))
    return obter(conn)


def envio_hoje(valores, agora=None):
    """{"ate": ISO Z} se há horário de corte, hoje (em Manaus) é dia útil e ainda não passou do corte; senão None."""
    corte = valores.get("horario_corte") or ""
    if not re.fullmatch(r"([01][0-9]|2[0-3]):[0-5][0-9]", corte):
        return None
    local = (agora or horario.agora()).astimezone(horario.FUSO_LOJA)
    if local.weekday() >= 5:  # sábado e domingo
        return None
    hora, minuto = map(int, corte.split(":"))
    limite = datetime(local.year, local.month, local.day, hora, minuto, tzinfo=horario.FUSO_LOJA)
    if local >= limite:
        return None
    return {"ate": horario.iso_z(horario.texto_db(limite))}
