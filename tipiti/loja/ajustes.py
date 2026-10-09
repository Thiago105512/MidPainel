"""Configurações da loja editáveis no painel (guardadas no banco)."""

from . import config
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
}


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
        if chave == "whatsapp":
            try:
                texto = normalizar_whatsapp(texto)
            except ErroValidacao as e:
                erros.update(e.campos)
        elif chave == "whatsapp_mensagem":
            texto = texto[:300]
        elif chave == "chave_pix":
            if len(texto) > 120:  # cortar geraria uma chave errada; melhor recusar
                erros[chave] = "A chave Pix deve ter no máximo 120 caracteres."
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
