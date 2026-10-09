"""Programa de revendedoras: cadastro, aprovação no painel, link e cupom próprios, comissão por pedido e painel dela.

Regras da comissão (em centavos, arredondada para baixo):
    comissao = comissao_pct × (subtotal − desconto do cupom − desconto do Pix) // 100   — o frete fica fora.
- Atribuição: o cupom de uma revendedora ativa usado no pedido vence o código do link (`revendedora`).
- Quem compra com o próprio CPF não gera comissão para si (o pedido fica sem revendedora).
- A comissão só conta (vendas, "a receber") em pedidos pagos, enviados ou entregues. Cancelar zera a comissão,
  a não ser que ela já tenha sido paga (o valor pago fica registrado).
- O painel da revendedora nunca mostra nome, CPF, telefone, e-mail ou endereço dos clientes.
"""

import hmac
import re
import secrets
import sqlite3
from datetime import date, datetime, timedelta

from . import config, cupons, horario
from .ajustes import normalizar_whatsapp
from .db import normaliza
from .validacao import UFS, ErroValidacao, NaoEncontrado, cpf_valido, so_digitos

STATUS = {"pendente": "Pendente", "ativa": "Ativa", "inativa": "Inativa"}
PCT_MAX = 50
_SQL_COMISSIONADO = "status IN ('pago', 'enviado', 'entregue')"
_CODIGO = re.compile(r"[a-z0-9-]{3,20}")
_INSTAGRAM = re.compile(r"[A-Za-z0-9._]{1,30}")


# ---------------------------------------------------------------- cadastro público

def _texto(dados, campo, erros, rotulo, minimo, maximo, obrigatorio=True):
    valor = dados.get(campo)
    if valor is not None and not isinstance(valor, str):
        erros[campo] = f"{rotulo.capitalize()}: valor inválido."
        return ""
    valor = " ".join((valor or "").split())
    if not valor and obrigatorio:
        erros[campo] = f"Informe {rotulo}."
    elif valor and not minimo <= len(valor) <= maximo:
        erros[campo] = f"{rotulo.capitalize()} deve ter entre {minimo} e {maximo} caracteres."
    return valor


def cadastrar(conn, dados):
    """Pedido de cadastro: {nome, whatsapp, cpf, cidade, uf, instagram?, mensagem?} -> {"status": "pendente"}.

    Um CPF já cadastrado recebe a mesma resposta (sem criar outro cadastro), para o formulário não revelar
    quem já é revendedora.
    """
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    erros = {}
    nome = _texto(dados, "nome", erros, "o nome completo", 3, 80)
    cidade = _texto(dados, "cidade", erros, "a cidade", 2, 80)
    instagram = _texto(dados, "instagram", erros, "o Instagram", 1, 60, obrigatorio=False)
    mensagem = (dados.get("mensagem") or "") if isinstance(dados.get("mensagem"), (str, type(None))) else None
    if mensagem is None:
        erros["mensagem"] = "Mensagem inválida."
        mensagem = ""
    mensagem = mensagem.strip()
    if len(mensagem) > 500:
        erros["mensagem"] = "A mensagem deve ter no máximo 500 caracteres."
    instagram = re.sub(r"^(https?://)?(www\.)?instagram\.com/", "", instagram).strip("/").lstrip("@")
    if instagram and not _INSTAGRAM.fullmatch(instagram):
        erros["instagram"] = "Informe o usuário do Instagram (ex.: @maria.achadinhos)."
    try:
        whatsapp = normalizar_whatsapp(dados.get("whatsapp") if isinstance(dados.get("whatsapp"), str) else "")
        if not whatsapp:
            erros["whatsapp"] = "Informe o WhatsApp com DDD, ex.: (92) 99123-4567."
    except ErroValidacao as e:
        erros.update(e.campos)
        whatsapp = ""
    cpf = so_digitos(dados.get("cpf")) if isinstance(dados.get("cpf"), str) else ""
    if not cpf_valido(cpf):
        erros["cpf"] = "Informe um CPF válido."
    uf = str(dados.get("uf") or "").strip().upper()
    if uf not in UFS:
        erros["uf"] = "Selecione o estado."
    if erros:
        raise ErroValidacao(erros)
    conn.execute(
        """INSERT INTO revendedoras (nome, whatsapp, cpf, cidade, uf, instagram, mensagem) VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(cpf) DO NOTHING""",
        (nome, whatsapp, cpf, cidade, uf, instagram, mensagem),
    )
    return {"status": "pendente"}


def pendentes(conn):
    return conn.execute("SELECT COUNT(*) FROM revendedoras WHERE status = 'pendente'").fetchone()[0]


# ---------------------------------------------------------------- painel da loja

def _obter_row(conn, revendedora_id):
    row = conn.execute("SELECT * FROM revendedoras WHERE id = ?", (revendedora_id,)).fetchone()
    if not row:
        raise NaoEncontrado("Revendedora não encontrada.")
    return row


def _slug(texto):
    return re.sub(r"[^a-z0-9]+", "-", normaliza(texto)).strip("-")


def _codigo_livre(conn, codigo, revendedora_id):
    if conn.execute("SELECT 1 FROM revendedoras WHERE codigo = ? AND id != ?", (codigo, revendedora_id)).fetchone():
        return False
    # o código vira cupom (maiúsculo): não pode colidir com um cupom que não é dela
    return not conn.execute("SELECT 1 FROM cupons WHERE codigo = ? AND COALESCE(revendedora_id, 0) != ?",
                            (codigo.upper(), revendedora_id)).fetchone()


def _gerar_codigo(conn, row):
    """"Maria José" de "Boa Vista" -> "maria-boa-vista" (até 20 caracteres; "-2", "-3"… se já existir)."""
    primeiro = _slug((row["nome"].split() or ["revenda"])[0])[:10] or "revenda"
    base = f"{primeiro}-{_slug(row['cidade'])}".strip("-")[:20].strip("-")
    if len(base) < 3:
        base = f"revenda-{base}".strip("-")
    for n in range(1, 1000):
        sufixo = "" if n == 1 else f"-{n}"
        codigo = base[:20 - len(sufixo)].rstrip("-") + sufixo
        if _CODIGO.fullmatch(codigo) and _codigo_livre(conn, codigo, row["id"]):
            return codigo
    while True:  # praticamente inalcançável
        codigo = f"revenda-{secrets.token_hex(4)}"
        if _codigo_livre(conn, codigo, row["id"]):
            return codigo


def _pct(dados, campo, atual, erros):
    valor = dados.get(campo, atual)
    if isinstance(valor, bool) or not isinstance(valor, int) or not 0 <= valor <= PCT_MAX:
        erros[campo] = f"Use uma porcentagem inteira de 0 a {PCT_MAX}."
        return atual
    return valor


def _sincronizar_cupom(conn, row_id, codigo, status, desconto_pct):
    """Cupom com o código dela (maiúsculo), ativo enquanto ela estiver ativa e com desconto para o cliente."""
    if not codigo:
        return
    existente = conn.execute("SELECT codigo FROM cupons WHERE revendedora_id = ?", (row_id,)).fetchone()
    ativo = status == "ativa" and desconto_pct > 0
    if existente:
        if ativo:
            conn.execute("UPDATE cupons SET tipo = 'pct', valor = ?, ativo = 1 WHERE revendedora_id = ?",
                         (desconto_pct, row_id))
        else:
            conn.execute("UPDATE cupons SET ativo = 0 WHERE revendedora_id = ?", (row_id,))
    elif ativo:
        try:
            conn.execute("INSERT INTO cupons (codigo, tipo, valor, revendedora_id) VALUES (?, 'pct', ?, ?)",
                         (codigo.upper(), desconto_pct, row_id))
        except sqlite3.IntegrityError:
            raise ErroValidacao({"desconto_cliente_pct": f"Já existe um cupom {codigo.upper()} de outra campanha."})


def atualizar(conn, revendedora_id, dados):
    """PATCH do painel: {status?, comissao_pct?, desconto_cliente_pct?, novo_token?}.

    Ao ativar pela primeira vez gera o código do link e o token do painel dela. `novo_token: true` troca o token
    (o link antigo do painel deixa de funcionar).
    """
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    row = _obter_row(conn, revendedora_id)
    erros = {}
    status = dados.get("status", row["status"])
    if not isinstance(status, str) or status not in STATUS:
        erros["status"] = "Status inválido: use ativa, inativa ou pendente."
    comissao = _pct(dados, "comissao_pct", row["comissao_pct"], erros)
    desconto = _pct(dados, "desconto_cliente_pct", row["desconto_cliente_pct"], erros)
    novo_token = dados.get("novo_token") is True
    if erros:
        raise ErroValidacao(erros, "Revise a revendedora.")
    conn.execute("BEGIN IMMEDIATE")
    try:
        codigo, token, ativada_em = row["codigo"], row["token_acesso"], row["ativada_em"]
        if status == "ativa":
            codigo = codigo or _gerar_codigo(conn, row)
            ativada_em = ativada_em or horario.texto_db(horario.agora())
            if not token:
                token = secrets.token_urlsafe(32)
        if novo_token and token:
            token = secrets.token_urlsafe(32)
        conn.execute(
            """UPDATE revendedoras SET status = ?, comissao_pct = ?, desconto_cliente_pct = ?, codigo = ?,
                   token_acesso = ?, ativada_em = ? WHERE id = ?""",
            (status, comissao, desconto, codigo, token, ativada_em, row["id"]),
        )
        _sincronizar_cupom(conn, row["id"], codigo, status, desconto)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return obter_admin(conn, row["id"])


def _cupom_publico(conn, revendedora_id):
    c = conn.execute(f"SELECT * FROM cupons WHERE revendedora_id = ? AND {cupons.SQL_VIGENTE}",
                     (revendedora_id,)).fetchone()
    return {"codigo": c["codigo"], "descricao": cupons.descricao(c)} if c else None


def _totais(conn, revendedora_id):
    t = conn.execute(
        f"""SELECT COALESCE(SUM({_SQL_COMISSIONADO}), 0) AS vendas,
                   COALESCE(SUM(CASE WHEN {_SQL_COMISSIONADO} AND comissao_paga_em IS NULL
                                     THEN comissao_centavos END), 0) AS a_receber,
                   COALESCE(SUM(CASE WHEN comissao_paga_em IS NOT NULL THEN comissao_centavos END), 0) AS pago
            FROM pedidos WHERE revendedora_id = ?""",
        (revendedora_id,),
    ).fetchone()
    return {"vendas": t["vendas"], "a_receber_centavos": t["a_receber"], "pago_centavos": t["pago"]}


def link_divulgacao(codigo):
    return f"{config.SITE_URL}/?r={codigo}" if codigo else None


def link_painel(token):
    return f"{config.SITE_URL}/revenda#{token}" if token else None


def _primeiro_nome(nome):
    return (nome.split() or [""])[0]


def texto_boas_vindas(row, cupom):
    linhas = [
        f"Oi, {_primeiro_nome(row['nome'])}! Seu cadastro de revendedora Tipiti foi aprovado. Seja bem-vinda!",
        "",
        f"Seu link para divulgar: {link_divulgacao(row['codigo'])}",
    ]
    if cupom:
        linhas.append(f"Seu cupom para as clientes: {cupom['codigo']} ({cupom['descricao']})")
    linhas += [
        f"Sua comissão: {row['comissao_pct']}% sobre o valor dos produtos (sem o frete) de cada pedido pago.",
        "",
        f"Seu painel com vendas e comissões: {link_painel(row['token_acesso'])}",
        "Esse link é só seu: não compartilhe com ninguém.",
    ]
    return "\n".join(linhas)


def _admin_dict(conn, row):
    cupom = _cupom_publico(conn, row["id"])
    ativa = row["status"] == "ativa"
    return {
        "id": row["id"],
        "nome": row["nome"],
        "whatsapp": row["whatsapp"],
        "cpf": row["cpf"],
        "cidade": row["cidade"],
        "uf": row["uf"],
        "instagram": row["instagram"],
        "mensagem": row["mensagem"],
        "status": row["status"],
        "status_nome": STATUS[row["status"]],
        "codigo": row["codigo"],
        "comissao_pct": row["comissao_pct"],
        "desconto_cliente_pct": row["desconto_cliente_pct"],
        "token_acesso": row["token_acesso"],
        "link_divulgacao": link_divulgacao(row["codigo"]),
        "link_painel": link_painel(row["token_acesso"]),
        "whatsapp_boas_vindas": texto_boas_vindas(row, cupom) if ativa and row["token_acesso"] else None,
        "cupom": cupom,
        "totais": _totais(conn, row["id"]),
        "criado_em": horario.iso_z(row["criado_em"]),
        "ativada_em": horario.iso_z(row["ativada_em"]),
    }


def obter_admin(conn, revendedora_id):
    return _admin_dict(conn, _obter_row(conn, revendedora_id))


def listar_admin(conn, status=None):
    sql, params = "SELECT * FROM revendedoras", []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY status = 'pendente' DESC, id DESC LIMIT 500"
    return [_admin_dict(conn, r) for r in conn.execute(sql, params).fetchall()]


def registrar_pagamento(conn, revendedora_id, dados):
    """Marca como pagas as comissões elegíveis (pedido pago/enviado/entregue, ainda não paga) dos pedidos feitos até
    `ate` (data de Manaus, inclusive). Devolve {"pago_centavos", "pedidos", "ate"}."""
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    _obter_row(conn, revendedora_id)
    ate = dados.get("ate")
    try:
        if not isinstance(ate, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", ate):
            raise ValueError
        dia = date.fromisoformat(ate)
    except ValueError:
        raise ErroValidacao({"ate": "Informe a data no formato AAAA-MM-DD."})
    fim = datetime(dia.year, dia.month, dia.day, tzinfo=horario.FUSO_LOJA) + timedelta(days=1)
    conn.execute("BEGIN IMMEDIATE")
    try:
        filtro = f"""revendedora_id = ? AND {_SQL_COMISSIONADO} AND comissao_paga_em IS NULL
                     AND comissao_centavos > 0 AND criado_em < ?"""
        params = (revendedora_id, horario.texto_db(fim))
        soma = conn.execute(f"SELECT COALESCE(SUM(comissao_centavos), 0), COUNT(*) FROM pedidos WHERE {filtro}",
                            params).fetchone()
        conn.execute(f"UPDATE pedidos SET comissao_paga_em = ? WHERE {filtro}",
                     (horario.texto_db(horario.agora()), *params))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return {"pago_centavos": soma[0], "pedidos": soma[1], "ate": ate}


# ---------------------------------------------------------------- atribuição dos pedidos

def normalizar_codigo(codigo):
    if not isinstance(codigo, str):
        return ""
    codigo = codigo.strip().lower()
    return codigo if _CODIGO.fullmatch(codigo) else ""


def resolver(conn, codigo_link=None, cupom_codigo=None):
    """Revendedora ativa do pedido: a dona do cupom usado vence a do link. None se nenhuma."""
    if cupom_codigo:
        r = conn.execute(
            """SELECT r.* FROM cupons c JOIN revendedoras r ON r.id = c.revendedora_id
               WHERE c.codigo = ? AND r.status = 'ativa'""",
            (cupons.normalizar_codigo(cupom_codigo),),
        ).fetchone()
        if r:
            return r
    codigo = normalizar_codigo(codigo_link)
    if codigo:
        return conn.execute("SELECT * FROM revendedoras WHERE codigo = ? AND status = 'ativa'", (codigo,)).fetchone()
    return None


def comissao(cotacao, pct):
    """pct × (subtotal − cupom − Pix) // 100, sem frete."""
    base = cotacao["subtotal_centavos"] - cotacao["desconto_cupom_centavos"] - cotacao["desconto_centavos"]
    return max(0, base) * pct // 100


def atribuir_pedido(conn, pedido_id, dados, cotacao, cpf):
    """Liga o pedido recém-criado (dentro da transação dele) à revendedora e guarda a comissão."""
    cupom = cotacao["cupom"]["codigo"] if cotacao.get("cupom") else None
    r = resolver(conn, dados.get("revendedora") if isinstance(dados, dict) else None, cupom)
    if not r or r["cpf"] == so_digitos(cpf):  # compra com o próprio CPF não gera comissão
        return
    conn.execute("UPDATE pedidos SET revendedora_id = ?, comissao_centavos = ? WHERE id = ?",
                 (r["id"], comissao(cotacao, r["comissao_pct"]), pedido_id))


def anexar_a_cotacao(conn, cotacao, codigo_link):
    """`revendedora` na cotação: {"nome" (primeiro nome), "cidade"} ou None."""
    cupom = cotacao["cupom"]["codigo"] if cotacao.get("cupom") else None
    r = resolver(conn, codigo_link, cupom)
    cotacao["revendedora"] = {"nome": _primeiro_nome(r["nome"]), "cidade": r["cidade"]} if r else None
    return cotacao


def ao_cancelar(conn, pedido_id):
    """Pedido cancelado não gera comissão (a já paga fica registrada)."""
    conn.execute("UPDATE pedidos SET comissao_centavos = 0 WHERE id = ? AND comissao_paga_em IS NULL", (pedido_id,))


def anexar_aos_pedidos(conn, pares):
    """Painel da loja: {id, nome, codigo} da revendedora, comissão e se já foi paga."""
    ids = sorted({row["revendedora_id"] for row, _ in pares if row["revendedora_id"]})
    nomes = {}
    if ids:
        nomes = {r["id"]: {"id": r["id"], "nome": r["nome"], "codigo": r["codigo"]} for r in conn.execute(
            f"SELECT id, nome, codigo FROM revendedoras WHERE id IN ({','.join('?' * len(ids))})", ids)}
    for row, resumo in pares:
        resumo["revendedora"] = nomes.get(row["revendedora_id"])
        resumo["comissao_centavos"] = row["comissao_centavos"]
        resumo["comissao_paga"] = row["comissao_paga_em"] is not None


# ---------------------------------------------------------------- painel da revendedora

def autenticar(conn, token):
    """Revendedora dona do token (comparação em tempo constante com todas), ou None. Devolve a linha mesmo se
    ela estiver inativa: quem chama decide (o token certo de uma conta desativada não é tentativa de adivinhar)."""
    if not isinstance(token, str) or not 20 <= len(token) <= 200:
        return None
    enviado = token.encode()
    achada = None
    for r in conn.execute("SELECT * FROM revendedoras WHERE token_acesso IS NOT NULL").fetchall():
        if hmac.compare_digest(r["token_acesso"].encode(), enviado):
            achada = r
    return achada


def painel(conn, row):
    pedidos = conn.execute(
        """SELECT codigo, criado_em, cidade, uf, total_centavos, comissao_centavos, status, comissao_paga_em
           FROM pedidos WHERE revendedora_id = ? ORDER BY id DESC LIMIT 300""",
        (row["id"],),
    ).fetchall()
    return {
        "nome": row["nome"],
        "codigo": row["codigo"],
        "cidade": row["cidade"],
        "comissao_pct": row["comissao_pct"],
        "link_divulgacao": link_divulgacao(row["codigo"]),
        "cupom": _cupom_publico(conn, row["id"]),
        "totais": _totais(conn, row["id"]),
        "pedidos": [
            {
                "codigo": p["codigo"],
                "data": horario.iso_z(p["criado_em"]),
                "cidade": p["cidade"],
                "uf": p["uf"],
                "total_centavos": p["total_centavos"],
                "comissao_centavos": p["comissao_centavos"],
                "status": p["status"],
                "comissao_paga": p["comissao_paga_em"] is not None,
            }
            for p in pedidos
        ],
    }
