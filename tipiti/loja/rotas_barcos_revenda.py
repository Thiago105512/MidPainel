"""Rotas do calendário de barcos, do rastreio dos pedidos e do programa de revendedoras."""

from http import HTTPStatus

from . import rastreio, regras, revendedoras, viagens
from .limites import MSG_LIMITE
from .rotas import ErroHttp, _limitar, _registrar, rota

# ---------------------------------------------------------------- calendário de barcos


@rota("GET", r"/api/viagens")
def api_viagens(conn, req):
    """Próximas 5 saídas da zona (?zona=parintins); sem zona, as próximas de todas as zonas."""
    zona = req.query.get("zona")
    return viagens.proximas(conn, zona or None)


@rota("GET", r"/api/admin/viagens", admin=True, papel="operador")
def api_admin_viagens(conn, req):
    return viagens.listar_admin(conn)


@rota("POST", r"/api/admin/viagens", admin=True, papel="operador")
def api_admin_criar_viagem(conn, req):
    return HTTPStatus.CREATED, viagens.criar(conn, req.json())


@rota("PATCH", r"/api/admin/viagens/(?P<viagem_id>[0-9]{1,18})", admin=True, papel="operador")
def api_admin_viagem(conn, req, viagem_id):
    return viagens.atualizar(conn, int(viagem_id), req.json())


# ---------------------------------------------------------------- rastreio


@rota("POST", r"/api/admin/pedidos/(?P<codigo>[A-Z0-9-]{4,20})/eventos", admin=True, papel="operador")
def api_admin_evento(conn, req, codigo):
    rastreio.adicionar_evento(conn, codigo, req.json())
    return HTTPStatus.CREATED, {**regras.obter_pedido_publico(conn, codigo),
                                "whatsapp_aviso": rastreio.aviso_whatsapp(conn, codigo)}


# ---------------------------------------------------------------- revendedoras


@rota("POST", r"/api/revendedoras")
def api_cadastro_revendedora(conn, req):
    _limitar(req, "revendedoras")
    resposta = revendedoras.cadastrar(conn, req.json())
    _registrar(req, "revendedoras")
    return HTTPStatus.CREATED, resposta


@rota("GET", r"/api/revenda/painel")
def api_painel_revenda(conn, req):
    """Painel da revendedora com o token dela (Authorization: Bearer). Tokens errados contam como no painel admin."""
    limite = req.handler.server.limites["revenda"]
    ip = req.handler.ip_cliente
    if limite.excedido(ip):
        raise ErroHttp(HTTPStatus.TOO_MANY_REQUESTS, MSG_LIMITE)
    token = req.handler._token_enviado()
    row = revendedoras.autenticar(conn, token)
    if row is None:
        if token:
            limite.registrar(ip)
        raise ErroHttp(HTTPStatus.UNAUTHORIZED, "Acesso restrito.")
    if row["status"] != "ativa":
        raise ErroHttp(HTTPStatus.FORBIDDEN, "Seu acesso de revendedora está desativado. Fale com a loja.")
    return revendedoras.painel(conn, row)


@rota("GET", r"/api/admin/revendedoras", admin=True, papel="dono")
def api_admin_revendedoras(conn, req):
    status = req.query.get("status")
    if status and status not in revendedoras.STATUS:
        raise regras.ErroValidacao({"status": "Status inválido."})
    return revendedoras.listar_admin(conn, status=status)


@rota("PATCH", r"/api/admin/revendedoras/(?P<revendedora_id>[0-9]{1,18})", admin=True, papel="dono")
def api_admin_revendedora(conn, req, revendedora_id):
    return revendedoras.atualizar(conn, int(revendedora_id), req.json())


@rota("POST", r"/api/admin/revendedoras/(?P<revendedora_id>[0-9]{1,18})/pagamentos", admin=True, papel="dono")
def api_admin_pagamento_revendedora(conn, req, revendedora_id):
    return revendedoras.registrar_pagamento(conn, int(revendedora_id), req.json())
