"""Rotas públicas da rodada 3: textos legais, pedidos LGPD, Minha conta, avise-me e carrinhos salvos."""

from http import HTTPStatus

from . import ajustes, avise_me, carrinhos, conta, legal, privacidade, retencao
from .limites import MSG_LIMITE
from .rotas import ErroHttp, _limitar, _registrar, rota

_LINK_INVALIDO = "Link inválido ou expirado. Peça um novo link de acesso."
_SESSAO_INVALIDA = "Sessão expirada. Entre de novo pela Minha conta."


def _limitar_chave(req, nome, chave):
    if req.handler.server.limites[nome].excedido(chave):
        raise ErroHttp(HTTPStatus.TOO_MANY_REQUESTS, MSG_LIMITE)


# ---------------------------------------------------------------- textos legais e LGPD

@rota("GET", r"/api/legal/privacidade")
def api_politica_privacidade(conn, req):
    return legal.politica_privacidade(ajustes.obter(conn))


@rota("GET", r"/api/legal/termos")
def api_termos(conn, req):
    return legal.termos_uso(ajustes.obter(conn))


@rota("POST", r"/api/privacidade/solicitacoes")
def api_solicitacao_lgpd(conn, req):
    _limitar(req, "privacidade")
    resultado = privacidade.criar_solicitacao(conn, req.json())
    _registrar(req, "privacidade")
    return HTTPStatus.CREATED, resultado


# ---------------------------------------------------------------- Minha conta

@rota("POST", r"/api/conta/acesso")
def api_conta_acesso(conn, req):
    """Sempre {"ok": true}: não revela se o e-mail tem pedidos."""
    retencao.purgar(conn)
    _limitar(req, "conta_acesso")
    email = conta.normalizar_email(req.json().get("email"))
    _limitar_chave(req, "conta_email", email)
    _registrar(req, "conta_acesso")
    req.handler.server.limites["conta_email"].registrar(email)
    return conta.solicitar_acesso(conn, email)


@rota("POST", r"/api/conta/sessao")
def api_conta_sessao(conn, req):
    _limitar(req, "conta_sessao")
    try:
        return conta.criar_sessao(conn, req.json().get("token"))
    except conta.SessaoInvalida:
        _registrar(req, "conta_sessao")
        raise ErroHttp(HTTPStatus.UNAUTHORIZED, _LINK_INVALIDO)


def _sessao_enviada(req):
    cabecalho = req.handler.headers.get("Authorization", "")
    return cabecalho[6:].strip() if cabecalho.startswith("Conta ") else ""


def _email_da_conta(conn, req):
    """E-mail da sessão de "Authorization: Conta <sessao>"; 401 se inválida (tentativas erradas contam)."""
    _limitar(req, "conta_sessao")
    try:
        return conta.email_da_sessao(conn, _sessao_enviada(req))
    except conta.SessaoInvalida:
        if _sessao_enviada(req):
            _registrar(req, "conta_sessao")
        raise ErroHttp(HTTPStatus.UNAUTHORIZED, _SESSAO_INVALIDA)


@rota("GET", r"/api/conta")
def api_conta(conn, req):
    return conta.resumo(conn, _email_da_conta(conn, req))


@rota("DELETE", r"/api/conta/sessao")
def api_conta_sair(conn, req):
    _email_da_conta(conn, req)
    return conta.encerrar_sessao(conn, _sessao_enviada(req))


@rota("POST", r"/api/conta/enderecos")
def api_conta_endereco(conn, req):
    return HTTPStatus.CREATED, conta.salvar_endereco(conn, _email_da_conta(conn, req), req.json())


@rota("DELETE", r"/api/conta/enderecos/(?P<endereco_id>[0-9]{1,18})")
def api_conta_remover_endereco(conn, req, endereco_id):
    return conta.remover_endereco(conn, _email_da_conta(conn, req), int(endereco_id))


# ---------------------------------------------------------------- avise-me

@rota("POST", r"/api/avise-me")
def api_avise_me(conn, req):
    _limitar(req, "avise_me")
    _registrar(req, "avise_me")
    return HTTPStatus.CREATED, avise_me.criar(conn, req.json())


# ---------------------------------------------------------------- carrinhos salvos (carrinho abandonado)

_TOKEN_CARRINHO = r"(?P<token>[A-Za-z0-9_-]{16,64})"


@rota("POST", r"/api/carrinhos")
def api_criar_carrinho(conn, req):
    retencao.purgar(conn)
    _limitar(req, "carrinhos")
    _registrar(req, "carrinhos")
    return HTTPStatus.CREATED, carrinhos.criar(conn, req.json())


@rota("PUT", r"/api/carrinhos/" + _TOKEN_CARRINHO)
def api_atualizar_carrinho(conn, req, token):
    _limitar(req, "consulta")
    try:
        return carrinhos.atualizar(conn, token, req.json())
    except carrinhos.NaoEncontrado:
        _registrar(req, "consulta")
        raise


@rota("GET", r"/api/carrinhos/" + _TOKEN_CARRINHO)
def api_carrinho_salvo(conn, req, token):
    _limitar(req, "consulta")  # só erros contam: dificulta adivinhar tokens
    try:
        return carrinhos.obter_publico(conn, token)
    except carrinhos.NaoEncontrado:
        _registrar(req, "consulta")
        raise

