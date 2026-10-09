"""Avise-me quando chegar: pedidos de aviso por e-mail ou WhatsApp para produtos (ou opções) sem estoque.

A passagem de "aguardando" para "pronto" é feita por gatilhos no banco (db.ESQUEMA_CONTAS) quando o estoque volta
de 0 para mais de 0, seja qual for o caminho (painel, cancelamento de pedido, opções). Os e-mails saem por
`enfileirar_avisos`, chamado depois das escritas do painel e pela thread de fundo.
"""

import re
from urllib.parse import quote

from . import config, emails, horario, notificacoes
from .ajustes import normalizar_whatsapp
from .validacao import ErroValidacao, NaoEncontrado, email_valido

STATUS = ("aguardando", "pronto", "avisado")


def criar(conn, dados):
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    erros = {}
    produto = conn.execute("SELECT id, nome FROM produtos WHERE slug = ? AND ativo = 1",
                           (str(dados.get("slug") or ""),)).fetchone()
    if not produto:
        raise NaoEncontrado("Produto não encontrado.")
    variacao_id = dados.get("variacao")
    if variacao_id in (None, ""):
        variacao_id = None
    elif isinstance(variacao_id, str) and re.fullmatch(r"[0-9]{1,18}", variacao_id):
        variacao_id = int(variacao_id)
    if variacao_id is None:
        pass
    elif (isinstance(variacao_id, bool) or not isinstance(variacao_id, int) or not conn.execute(
            "SELECT 1 FROM variacoes WHERE id = ? AND produto_id = ? AND ativo = 1",
            (variacao_id, produto["id"])).fetchone()):
        erros["variacao"] = "Opção inválida."
    nome = " ".join(str(dados.get("nome") or "").split())[:80]
    email = str(dados.get("email") or "").strip().lower()
    if email and (not email_valido(email) or any(c in email for c in "\r\n")):
        erros["email"] = "Informe um e-mail válido."
    whatsapp = ""
    if dados.get("whatsapp"):
        try:
            whatsapp = normalizar_whatsapp(dados.get("whatsapp"))
        except ErroValidacao as e:
            erros.update(e.campos)
    if not email and not whatsapp and "email" not in erros and "whatsapp" not in erros:
        erros["contato"] = "Informe um e-mail ou WhatsApp para receber o aviso."
    if dados.get("aceite") is not True:
        erros["aceite"] = "É preciso autorizar o aviso."
    if erros:
        raise ErroValidacao(erros)
    duplicado = conn.execute(
        """SELECT 1 FROM avise_me WHERE produto_id = ? AND variacao_id IS ? AND status IN ('aguardando', 'pronto')
           AND ((? != '' AND email = ?) OR (? != '' AND whatsapp = ?))""",
        (produto["id"], variacao_id, email, email, whatsapp, whatsapp),
    ).fetchone()
    if not duplicado:
        conn.execute("""INSERT INTO avise_me (produto_id, variacao_id, nome, email, whatsapp, criado_em)
                        VALUES (?, ?, ?, ?, ?, ?)""", (produto["id"], variacao_id, nome, email, whatsapp,
                                                       horario.agora_db()))
    return {"ok": True}


def total_produto(conn, produto_id):
    return conn.execute("SELECT COUNT(*) FROM avise_me WHERE produto_id = ? AND status IN ('aguardando', 'pronto')",
                        (produto_id,)).fetchone()[0]


_SELECT = """SELECT a.*, p.nome AS produto_nome, p.slug AS produto_slug, v.nome AS variacao_nome
             FROM avise_me a JOIN produtos p ON p.id = a.produto_id LEFT JOIN variacoes v ON v.id = a.variacao_id"""


def _link_whatsapp(r):
    if not r["whatsapp"]:
        return None
    item = r["produto_nome"] + (f" ({r['variacao_nome']})" if r["variacao_nome"] else "")
    nome = (r["nome"].split() or [""])[0]
    texto = (f"Oi{', ' + nome if nome else ''}! Aqui é da Tipiti. Chegou o {item} que você pediu para avisar: "
             f"{config.SITE_URL}/produto/{r['produto_slug']}")
    return f"https://wa.me/{r['whatsapp']}?text={quote(texto)}"


def _dict(r):
    return {
        "id": r["id"], "produto": {"nome": r["produto_nome"], "slug": r["produto_slug"]},
        "variacao": r["variacao_nome"], "nome": r["nome"], "email": r["email"] or None,
        "whatsapp": r["whatsapp"] or None, "status": r["status"], "email_enviado": bool(r["email_enviado"]),
        "whatsapp_link": _link_whatsapp(r), "criado_em": horario.iso_z(r["criado_em"]),
    }


def listar_admin(conn, status=None):
    sql, params = _SELECT, []
    if status:
        if status not in STATUS:
            raise ErroValidacao({"status": "Status inválido."})
        sql += " WHERE a.status = ?"
        params.append(status)
    return [_dict(r) for r in conn.execute(sql + " ORDER BY a.id DESC LIMIT 500", params).fetchall()]


def atualizar_admin(conn, aviso_id, dados):
    status = dados.get("status") if isinstance(dados, dict) else None
    if status not in STATUS:
        raise ErroValidacao({"status": "Status inválido."})
    if conn.execute("UPDATE avise_me SET status = ?, avisado_em = CASE WHEN ? = 'avisado' THEN ? END WHERE id = ?",
                    (status, status, horario.agora_db(), aviso_id)).rowcount != 1:
        raise NaoEncontrado("Aviso não encontrado.")
    return _dict(conn.execute(_SELECT + " WHERE a.id = ?", (aviso_id,)).fetchone())


def enfileirar_avisos(conn):
    """E-mails dos avisos "prontos" (só com SMTP configurado). Quem só tem e-mail passa a "avisado"."""
    if not emails.configurado():
        return 0
    rows = conn.execute(_SELECT + """ WHERE a.status = 'pronto' AND a.email != '' AND a.email_enviado = 0
                                      AND COALESCE(a.pronto_em, a.criado_em) >= ? LIMIT 200""",
                        (horario.agora_db(days=-7),)).fetchall()
    for r in rows:
        # marca antes de enfileirar: uma segunda chamada simultânea não manda o mesmo aviso duas vezes
        if conn.execute("UPDATE avise_me SET email_enviado = 1 WHERE id = ? AND email_enviado = 0",
                        (r["id"],)).rowcount != 1:
            continue
        try:
            notificacoes.avise_me(conn, r["email"], r["nome"], r["produto_nome"], r["variacao_nome"],
                                  r["produto_slug"])
        except ErroValidacao:
            continue
        if not r["whatsapp"]:
            conn.execute("UPDATE avise_me SET status = 'avisado', avisado_em = ? WHERE id = ?",
                         (horario.agora_db(), r["id"]))
    return len(rows)
