"""Avaliações de compra verificada: só quem recebeu o pedido avalia, e a loja modera antes de publicar."""

import sqlite3
from decimal import ROUND_HALF_UP, Decimal

from .validacao import ErroValidacao, NaoEncontrado

STATUS_AVALIACAO = ("pendente", "aprovada", "oculta")
COMENTARIO_MAX = 1000
MAX_PUBLICAS = 50

# Soma e número de notas aprovadas por produto (para a média), juntado às listagens numa consulta só.
SQL_NOTAS = """
    SELECT produto_id, SUM(nota) AS soma_notas, COUNT(*) AS total
    FROM avaliacoes WHERE status = 'aprovada' GROUP BY produto_id
"""

# Data da avaliação no horário da loja (Manaus, UTC−4)
_SQL_DATA = "date(a.criado_em, '-4 hours')"


def nota_media(soma, total):
    """Média com uma casa decimal (meio para cima); None sem avaliações aprovadas."""
    if not total:
        return None
    return float((Decimal(soma) / Decimal(total)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def nome_exibicao(nome_cliente, cidade):
    """Só o primeiro nome e a cidade: "Maria de Parintins"."""
    partes = (nome_cliente or "").split()
    primeiro = partes[0].capitalize() if partes else "Cliente"
    cidade = (cidade or "").strip()
    return f"{primeiro} de {cidade}" if cidade else primeiro


def listar_avaliacoes(conn, slug):
    produto = conn.execute("SELECT id FROM produtos WHERE slug = ? AND ativo = 1", (slug,)).fetchone()
    if not produto:
        raise NaoEncontrado("Produto não encontrado.")
    rows = conn.execute(
        f"""SELECT a.nome_exibicao, a.nota, a.comentario, {_SQL_DATA} AS data FROM avaliacoes a
            WHERE a.produto_id = ? AND a.status = 'aprovada' ORDER BY a.criado_em DESC, a.id DESC LIMIT ?""",
        (produto["id"], MAX_PUBLICAS),
    ).fetchall()
    return [{"nome": r["nome_exibicao"], "nota": r["nota"], "comentario": r["comentario"], "data": r["data"]}
            for r in rows]


def produtos_avaliados(conn, pedido_id):
    """Ids dos produtos que já têm avaliação (qualquer status) deste pedido."""
    return {r[0] for r in conn.execute("SELECT produto_id FROM avaliacoes WHERE pedido_id = ?", (pedido_id,))}


def criar_avaliacao(conn, dados):
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    erros = {}
    codigo = str(dados.get("codigo") or "").strip().upper()
    email = str(dados.get("email") or "").strip().lower()
    slug = str(dados.get("slug") or "").strip()
    nota = dados.get("nota")
    comentario = dados.get("comentario")
    if not codigo:
        erros["codigo"] = "Informe o código do pedido."
    if not email:
        erros["email"] = "Informe o e-mail usado no pedido."
    if not slug:
        erros["slug"] = "Escolha o produto."
    if isinstance(nota, bool) or not isinstance(nota, int) or not 1 <= nota <= 5:
        erros["nota"] = "Dê uma nota de 1 a 5 estrelas."
    if comentario is None:
        comentario = ""
    if not isinstance(comentario, str):
        erros["comentario"] = "Comentário inválido."
    elif len(comentario.strip()) > COMENTARIO_MAX:
        erros["comentario"] = f"O comentário deve ter no máximo {COMENTARIO_MAX} caracteres."
    if erros:
        raise ErroValidacao(erros)

    pedido = conn.execute("SELECT id, status, cliente_email, cliente_nome, cidade FROM pedidos WHERE codigo = ?",
                          (codigo,)).fetchone()
    if not pedido:
        raise ErroValidacao({"codigo": "Pedido não encontrado. Confira o código."})
    if pedido["cliente_email"].strip().lower() != email:
        raise ErroValidacao({"email": "Este e-mail não é o do pedido informado."})
    if pedido["status"] != "entregue":
        raise ErroValidacao({"codigo": "Você poderá avaliar assim que o pedido for entregue."})
    produto = conn.execute(
        """SELECT DISTINCT p.id FROM itens_pedido i JOIN produtos p ON p.id = i.produto_id
           WHERE i.pedido_id = ? AND p.slug = ?""", (pedido["id"], slug),
    ).fetchone()
    if not produto:
        raise ErroValidacao({"slug": "Este produto não faz parte do pedido."})
    ja_avaliou = ErroValidacao({"slug": "Você já avaliou este produto neste pedido."})
    if produto["id"] in produtos_avaliados(conn, pedido["id"]):
        raise ja_avaliou
    try:
        conn.execute(
            """INSERT INTO avaliacoes (produto_id, pedido_id, nota, comentario, nome_exibicao, status)
               VALUES (?, ?, ?, ?, ?, 'pendente')""",
            (produto["id"], pedido["id"], nota, comentario.strip(),
             nome_exibicao(pedido["cliente_nome"], pedido["cidade"])),
        )
    except sqlite3.IntegrityError:  # duas avaliações iguais ao mesmo tempo: a UNIQUE segura a segunda
        raise ja_avaliou
    return {"status": "pendente"}


def _avaliacao_admin(r):
    return {
        "id": r["id"], "produto": {"nome": r["produto_nome"], "slug": r["produto_slug"]}, "pedido": r["pedido_codigo"],
        "nome": r["nome_exibicao"], "nota": r["nota"], "comentario": r["comentario"], "status": r["status"],
        "data": r["data"],
    }


_SELECT_ADMIN = f"""
    SELECT a.*, {_SQL_DATA} AS data, p.nome AS produto_nome, p.slug AS produto_slug, pe.codigo AS pedido_codigo
    FROM avaliacoes a JOIN produtos p ON p.id = a.produto_id JOIN pedidos pe ON pe.id = a.pedido_id
"""


def listar_avaliacoes_admin(conn, status=None):
    """Todas (pendentes primeiro, depois as mais novas) ou só as de um status."""
    sql, params = _SELECT_ADMIN, []
    if status:
        if status not in STATUS_AVALIACAO:
            raise ErroValidacao({"status": "Status inválido."})
        sql += " WHERE a.status = ?"
        params.append(status)
    sql += " ORDER BY a.status != 'pendente', a.id DESC LIMIT 500"
    return [_avaliacao_admin(r) for r in conn.execute(sql, params).fetchall()]


def moderar_avaliacao(conn, avaliacao_id, status):
    if not isinstance(status, str) or status not in STATUS_AVALIACAO:
        raise ErroValidacao({"status": "Use “pendente”, “aprovada” ou “oculta”."})
    if conn.execute("UPDATE avaliacoes SET status = ? WHERE id = ?", (status, avaliacao_id)).rowcount != 1:
        raise NaoEncontrado("Avaliação não encontrada.")
    return _avaliacao_admin(conn.execute(_SELECT_ADMIN + " WHERE a.id = ?", (avaliacao_id,)).fetchone())
