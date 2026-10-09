"""Rotas da API de Pix (copia e cola + QR Code), "Encomenda pra mim" e feeds de produtos (painel).

Registradas no mesmo `ROTAS` de rotas.py (o servidor importa este módulo).
"""

from http import HTTPStatus

from . import ajustes, encomendas, feeds, pix
from .reservas import expirar_pendentes
from .rotas import ErroHttp, _limitar, _registrar, rota
from .validacao import NaoEncontrado


class RespostaBruta:
    """Resposta que não é JSON (ex.: SVG): o servidor envia `corpo` com o `tipo` e os cabeçalhos dados."""

    def __init__(self, corpo, tipo, cabecalhos=None):
        self.corpo = corpo
        self.tipo = tipo
        self.cabecalhos = cabecalhos or {}


# ---------------------------------------------------------------- Pix

def _pix_do_pedido(conn, req, codigo):
    """Payload Pix do pedido; mesma limitação por IP da consulta de pedido (só erros de código contam)."""
    _limitar(req, "consulta")
    expirar_pendentes(conn)  # um pedido vencido não deve ganhar um Pix pagável
    row = conn.execute("SELECT codigo, status, pagamento, total_centavos FROM pedidos WHERE codigo = ?",
                       (str(codigo).upper(),)).fetchone()
    if not row:
        _registrar(req, "consulta")
        raise NaoEncontrado("Pedido não encontrado.")
    if row["pagamento"] != "pix":
        raise ErroHttp(HTTPStatus.CONFLICT, "Este pedido não é pago com Pix.")
    if row["status"] != "aguardando_pagamento":
        raise ErroHttp(HTTPStatus.CONFLICT, "Este pedido não está aguardando pagamento.")
    recebedor = pix.configurado(ajustes.obter(conn))
    if recebedor is None:
        raise ErroHttp(HTTPStatus.CONFLICT, "O Pix da loja ainda não está configurado. Fale com a loja.")
    payload = pix.copia_e_cola(recebedor["chave"], recebedor["nome"], recebedor["cidade"],
                               row["total_centavos"], pix.txid_do_pedido(row["codigo"]))
    return row, payload


@rota("GET", r"/api/pedidos/(?P<codigo>[A-Za-z0-9-]{4,20})/pix")
def api_pedido_pix(conn, req, codigo):
    row, payload = _pix_do_pedido(conn, req, codigo)
    return {"copia_e_cola": payload, "valor_centavos": row["total_centavos"],
            "qr_svg": f"/api/pedidos/{row['codigo']}/pix.svg"}


@rota("GET", r"/api/pedidos/(?P<codigo>[A-Za-z0-9-]{4,20})/pix\.svg")
def api_pedido_pix_svg(conn, req, codigo):
    _, payload = _pix_do_pedido(conn, req, codigo)
    return RespostaBruta(pix.qr_svg(payload), "image/svg+xml; charset=utf-8", {"Cache-Control": "no-store"})


# ---------------------------------------------------------------- "Encomenda pra mim"

@rota("POST", r"/api/encomendas")
def api_criar_encomenda(conn, req):
    _limitar(req, "encomendas")
    codigo = encomendas.criar(conn, req.json())
    _registrar(req, "encomendas")
    return HTTPStatus.CREATED, {"codigo": codigo}


@rota("GET", r"/api/encomendas/(?P<codigo>[A-Za-z0-9-]{4,20})")
def api_encomenda(conn, req, codigo):
    _limitar(req, "consulta")  # código + WhatsApp errados contam, como na consulta de pedido
    try:
        return encomendas.obter_publica(conn, codigo, req.query.get("whatsapp"))
    except NaoEncontrado:
        _registrar(req, "consulta")
        raise


@rota("POST", r"/api/encomendas/(?P<codigo>[A-Za-z0-9-]{4,20})/resposta")
def api_responder_encomenda(conn, req, codigo):
    _limitar(req, "consulta")
    try:
        return encomendas.responder(conn, codigo, req.json())
    except NaoEncontrado:
        _registrar(req, "consulta")
        raise
    except encomendas.Conflito as e:
        raise ErroHttp(HTTPStatus.CONFLICT, str(e))


@rota("GET", r"/api/admin/encomendas", admin=True)
def api_admin_encomendas(conn, req):
    return encomendas.listar_admin(conn, status=req.query.get("status"))


@rota("PATCH", r"/api/admin/encomendas/(?P<codigo>[A-Za-z0-9-]{4,20})", admin=True)
def api_admin_encomenda(conn, req, codigo):
    return encomendas.atualizar_admin(conn, codigo, req.json())


# ---------------------------------------------------------------- feeds (Google / Meta)

@rota("GET", r"/api/admin/feeds", admin=True)
def api_admin_feeds(conn, req):
    return feeds.resumo_admin(conn)

