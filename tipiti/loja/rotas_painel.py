"""Rotas do painel da rodada 3: login, usuários, 2FA, histórico, e-mails, LGPD, avise-me, carrinhos e separação.

Permissões: rotas admin=True exigem sessão (ou o TIPITI_ADMIN_TOKEN); o operador só passa nas rotas de
usuarios.OPERADOR_PODE (ou com papel="operador"). O filtro de custo/lucro e o histórico são aplicados no servidor.
"""

from http import HTTPStatus

from . import avise_me, carrinhos, emails, historico, privacidade, retencao, separacao, usuarios
from .limites import MSG_LIMITE
from .rotas import ErroHttp, _limitar, _registrar, rota
from .validacao import ErroValidacao


def _limitar_chave(req, nome, chave):
    if req.handler.server.limites[nome].excedido(chave):
        raise ErroHttp(HTTPStatus.TOO_MANY_REQUESTS, MSG_LIMITE)


# ---------------------------------------------------------------- login

@rota("POST", r"/api/admin/login")
def api_admin_login(conn, req):
    """Mesmo limite do token do painel (por IP), mais um limite por login."""
    _limitar(req, "admin")
    corpo = req.json()
    login = str(corpo.get("login") or "").strip().lower()[:254]
    _limitar_chave(req, "login", login)
    ip = req.handler.ip_cliente
    codigo = corpo.get("codigo_2fa")
    try:
        resultado = usuarios.autenticar(conn, login, corpo.get("senha"), codigo, ip)
    except usuarios.FalhaLogin as falha:
        if not (falha.precisa_2fa and not codigo):  # pedir o código depois da senha certa não é tentativa errada
            _registrar(req, "admin")
            req.handler.server.limites["login"].registrar(login)
        historico.registrar(conn, None, "login_falhou", "/api/admin/login", {"login": login}, ip)
        if falha.precisa_2fa:
            mensagem = "Código de verificação inválido." if codigo else "Informe o código de verificação do aplicativo."
            return HTTPStatus.UNAUTHORIZED, {"erro": mensagem, "precisa_2fa": True}
        return HTTPStatus.UNAUTHORIZED, {"erro": "Login ou senha incorretos."}
    ator = usuarios.ator_da_sessao(conn, resultado["sessao"])
    historico.registrar(conn, ator, "login", "/api/admin/login", None, ip)
    return resultado


@rota("POST", r"/api/admin/logout", admin=True, papel="operador")
def api_admin_logout(conn, req):
    if not req.ator["via_token"]:
        usuarios.encerrar_sessao(conn, req.handler._token_enviado())
    return {"ok": True}


# ---------------------------------------------------------------- o próprio usuário

@rota("GET", r"/api/admin/eu", admin=True, papel="operador")
def api_admin_eu(conn, req):
    return usuarios.eu(conn, req.ator)


def _tentativa_2fa(req, conn, funcao, *args):
    """Confirmar/desativar 2FA e trocar senha: tentativas erradas contam por usuário e por IP."""
    chave = f"u{req.ator['id']}"
    _limitar(req, "admin")
    _limitar_chave(req, "dois_fatores", chave)
    try:
        return funcao(conn, req.ator, *args)
    except ErroValidacao as e:
        if set(e.campos) & {"codigo", "senha", "atual"}:
            _registrar(req, "admin")
            req.handler.server.limites["dois_fatores"].registrar(chave)
        raise


@rota("POST", r"/api/admin/eu/2fa/iniciar", admin=True, papel="operador")
def api_admin_2fa_iniciar(conn, req):
    return usuarios.iniciar_2fa(conn, req.ator)


@rota("POST", r"/api/admin/eu/2fa/confirmar", admin=True, papel="operador")
def api_admin_2fa_confirmar(conn, req):
    return _tentativa_2fa(req, conn, usuarios.confirmar_2fa, req.json().get("codigo"))


@rota("POST", r"/api/admin/eu/2fa/desativar", admin=True, papel="operador")
def api_admin_2fa_desativar(conn, req):
    corpo = req.json()
    return _tentativa_2fa(req, conn, usuarios.desativar_2fa, corpo.get("senha"), corpo.get("codigo"))


@rota("POST", r"/api/admin/eu/senha", admin=True, papel="operador")
def api_admin_trocar_senha(conn, req):
    corpo = req.json()
    return _tentativa_2fa(req, conn, usuarios.trocar_senha, corpo.get("atual"), corpo.get("nova"))


# ---------------------------------------------------------------- usuários e histórico (dono)

@rota("GET", r"/api/admin/usuarios", admin=True, papel="dono")
def api_admin_usuarios(conn, req):
    return usuarios.listar(conn)


@rota("POST", r"/api/admin/usuarios", admin=True, papel="dono")
def api_admin_criar_usuario(conn, req):
    return HTTPStatus.CREATED, usuarios.criar(conn, req.json())


@rota("PATCH", r"/api/admin/usuarios/(?P<usuario_id>[0-9]{1,18})", admin=True, papel="dono")
def api_admin_usuario(conn, req, usuario_id):
    return usuarios.atualizar(conn, int(usuario_id), req.json())


@rota("GET", r"/api/admin/historico", admin=True, papel="dono")
def api_admin_historico(conn, req):
    q = req.query
    return historico.listar(conn, usuario=q.get("usuario"), alvo=q.get("alvo"), pagina=q.get("pagina"),
                            por_pagina=q.get("por_pagina"))


# ---------------------------------------------------------------- e-mails (dono)

@rota("GET", r"/api/admin/emails", admin=True, papel="dono")
def api_admin_emails(conn, req):
    return emails.listar(conn, req.query.get("status"))


@rota("POST", r"/api/admin/emails/(?P<email_id>[0-9]{1,18})/reenviar", admin=True, papel="dono")
def api_admin_reenviar_email(conn, req, email_id):
    return emails.reenviar(conn, int(email_id))


# ---------------------------------------------------------------- LGPD (dono)

_PROTOCOLO = r"(?P<protocolo>LGPD-[A-Za-z0-9]{8})"


@rota("GET", r"/api/admin/privacidade", admin=True, papel="dono")
def api_admin_privacidade(conn, req):
    return privacidade.listar(conn, req.query.get("status"))


@rota("PATCH", r"/api/admin/privacidade/" + _PROTOCOLO, admin=True, papel="dono")
def api_admin_atualizar_privacidade(conn, req, protocolo):
    return privacidade.atualizar(conn, protocolo, req.json())


@rota("GET", r"/api/admin/privacidade/" + _PROTOCOLO + r"/dados", admin=True, papel="dono")
def api_admin_exportar_privacidade(conn, req, protocolo):
    dados = privacidade.exportar(conn, protocolo)
    # leitura de dados pessoais também fica registrada
    historico.registrar(conn, req.ator, "lgpd_exportar", f"/api/admin/privacidade/{protocolo}",
                        None, req.handler.ip_cliente)
    return dados


@rota("POST", r"/api/admin/privacidade/" + _PROTOCOLO + r"/anonimizar", admin=True, papel="dono")
def api_admin_anonimizar(conn, req, protocolo):
    resultado = privacidade.anonimizar(conn, protocolo)
    req.historico_detalhes = resultado
    return resultado


# ---------------------------------------------------------------- avise-me e carrinhos (operador também)

@rota("GET", r"/api/admin/avise-me", admin=True, papel="operador")
def api_admin_avise_me(conn, req):
    return avise_me.listar_admin(conn, req.query.get("status"))


@rota("PATCH", r"/api/admin/avise-me/(?P<aviso_id>[0-9]{1,18})", admin=True, papel="operador")
def api_admin_atualizar_avise_me(conn, req, aviso_id):
    return avise_me.atualizar_admin(conn, int(aviso_id), req.json())


@rota("GET", r"/api/admin/carrinhos", admin=True, papel="operador")
def api_admin_carrinhos(conn, req):
    retencao.purgar(conn)
    return carrinhos.listar_admin(conn, req.query.get("status"))


@rota("PATCH", r"/api/admin/carrinhos/(?P<token>[A-Za-z0-9_-]{16,64})", admin=True, papel="operador")
def api_admin_carrinho(conn, req, token):
    return carrinhos.marcar_lembrete(conn, token, req.json())


# ---------------------------------------------------------------- separação e etiquetas (operador também)

@rota("GET", r"/api/admin/separacao", admin=True, papel="operador")
def api_admin_separacao(conn, req):
    return separacao.listar(conn, req.query.get("status") or "pago")


@rota("POST", r"/api/admin/pedidos/separados", admin=True, papel="operador")
def api_admin_separados(conn, req):
    return separacao.marcar_separados(conn, req.json())
