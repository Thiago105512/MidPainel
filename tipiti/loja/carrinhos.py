"""Carrinho abandonado: o checkout guarda o carrinho (com WhatsApp autorizado) e o painel lembra o cliente.

O token do carrinho é o que vai no link `/?c=<token>`; a consulta pública devolve só os itens (sem dados pessoais).
Carrinhos são apagados depois de RETENCAO_DIAS (retencao.py).
"""

import json
import secrets
from urllib.parse import quote

from . import config, horario
from .ajustes import normalizar_whatsapp
from .carrinho import _linhas, _normalizar_itens
from .validacao import ErroValidacao, NaoEncontrado, so_digitos

RETENCAO_DIAS = 30
ABANDONADO_APOS_HORAS = 1
JANELA_ABANDONO_DIAS = 7
STATUS_FILTRO = ("abandonado", "aberto", "convertido")


def _itens(lista):
    quantidades = _normalizar_itens(lista)
    return [{"slug": s, "variacao": v, "quantidade": q} for (s, v), q in quantidades.items()]


def _whatsapp(valor):
    try:
        numero = normalizar_whatsapp(valor)
    except ErroValidacao:
        numero = ""
    if not numero:
        raise ErroValidacao({"whatsapp": "Informe o WhatsApp com DDD."})
    return numero


def criar(conn, dados):
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    erros = {}
    if dados.get("aceite_whatsapp") is not True:
        erros["aceite_whatsapp"] = "É preciso autorizar o contato pelo WhatsApp."
    try:
        whatsapp = _whatsapp(dados.get("whatsapp"))
    except ErroValidacao as e:
        erros.update(e.campos)
    try:
        itens = _itens(dados.get("itens"))
    except ErroValidacao as e:
        erros.update(e.campos)
    if erros:
        raise ErroValidacao(erros)
    nome = " ".join(str(dados.get("nome") or "").split())[:120]
    agora = horario.agora_db()
    token = secrets.token_urlsafe(16)
    conn.execute("BEGIN IMMEDIATE")
    try:
        # um carrinho aberto por WhatsApp: o anterior é descartado (sem revelar o token dele a ninguém)
        conn.execute("DELETE FROM carrinhos WHERE whatsapp = ? AND status = 'aberto'", (whatsapp,))
        conn.execute("""INSERT INTO carrinhos (token, nome, whatsapp, itens, criado_em, atualizado_em)
                        VALUES (?, ?, ?, ?, ?, ?)""", (token, nome, whatsapp, json.dumps(itens), agora, agora))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return {"id": token}


def _por_token(conn, token):
    row = conn.execute("SELECT * FROM carrinhos WHERE token = ? AND atualizado_em >= ?",
                       (str(token), horario.agora_db(days=-RETENCAO_DIAS))).fetchone()
    if not row:
        raise NaoEncontrado("Carrinho não encontrado.")
    return row


def atualizar(conn, token, dados):
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    row = _por_token(conn, token)
    if row["status"] != "aberto":
        raise NaoEncontrado("Carrinho não encontrado.")
    itens = _itens(dados.get("itens"))
    sets, params = ["itens = ?", "atualizado_em = ?"], [json.dumps(itens), horario.agora_db()]
    if "nome" in dados:
        sets.append("nome = ?")
        params.append(" ".join(str(dados.get("nome") or "").split())[:120])
    conn.execute(f"UPDATE carrinhos SET {', '.join(sets)} WHERE id = ?", (*params, row["id"]))
    return {"id": row["token"]}


def obter_publico(conn, token):
    """Só os itens, para restaurar o carrinho no navegador."""
    return {"itens": json.loads(_por_token(conn, token)["itens"])}


def converter(conn, pedido_id, token=None, telefone=None):
    """Pedido criado: o carrinho do token (ou do mesmo WhatsApp) vira "convertido"."""
    agora = horario.agora_db()
    if isinstance(token, str) and token:
        conn.execute("UPDATE carrinhos SET status = 'convertido', pedido_id = ?, atualizado_em = ? "
                     "WHERE token = ? AND status = 'aberto'", (pedido_id, agora, token))
    try:
        whatsapp = normalizar_whatsapp(so_digitos(telefone)) if telefone else ""
    except ErroValidacao:
        whatsapp = ""
    if whatsapp:
        conn.execute("UPDATE carrinhos SET status = 'convertido', pedido_id = ?, atualizado_em = ? "
                     "WHERE whatsapp = ? AND status = 'aberto'", (pedido_id, agora, whatsapp))


def _resumo_itens(conn, itens):
    """[{nome, quantidade}] e total pelos preços atuais (itens que saíram da loja ficam fora do total)."""
    try:
        quantidades = _normalizar_itens(itens)
    except ErroValidacao:
        return [], 0
    linhas = _linhas(conn, quantidades)
    resumo = [{"nome": (l.get("nome") or l["slug"])
               + (f" ({l['variacao_nome']})" if l.get("variacao_nome") else ""), "quantidade": l["quantidade"]}
              for l in linhas]
    total = sum(l.get("total_centavos", 0) for l in linhas if l.get("disponivel"))
    return resumo, total


def _link_whatsapp(row, resumo):
    nome = (row["nome"].split() or [""])[0]
    lista = ", ".join(f"{i['quantidade']}x {i['nome']}" for i in resumo[:5])
    texto = (f"Oi{', ' + nome if nome else ''}! Aqui é da Tipiti. Vi que você separou {lista} e não finalizou. "
             f"Seu carrinho ficou salvo aqui: {config.SITE_URL}/?c={row['token']} — posso ajudar com alguma dúvida?")
    return f"https://wa.me/{row['whatsapp']}?text={quote(texto)}"


def listar_admin(conn, status="abandonado"):
    status = status or "abandonado"
    if status not in STATUS_FILTRO:
        raise ErroValidacao({"status": "Status inválido."})
    if status == "abandonado":
        rows = conn.execute(
            """SELECT * FROM carrinhos WHERE status = 'aberto' AND atualizado_em < ? AND atualizado_em >= ?
               ORDER BY atualizado_em DESC LIMIT 300""",
            (horario.agora_db(hours=-ABANDONADO_APOS_HORAS), horario.agora_db(days=-JANELA_ABANDONO_DIAS)),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM carrinhos WHERE status = ? ORDER BY atualizado_em DESC LIMIT 300",
                            (status,)).fetchall()
    resultado = []
    for r in rows:
        resumo, total = _resumo_itens(conn, json.loads(r["itens"]))
        resultado.append({
            "id": r["token"], "nome": r["nome"], "whatsapp": r["whatsapp"], "itens": resumo,
            "total_centavos": total, "status": r["status"], "atualizado_em": horario.iso_z(r["atualizado_em"]),
            "lembrete_enviado": bool(r["lembrete_enviado"]), "lembrete_em": horario.iso_z(r["lembrete_em"]),
            "whatsapp_link": _link_whatsapp(r, resumo),
        })
    return resultado


def marcar_lembrete(conn, token, dados):
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    enviado = dados.get("lembrete_enviado", True)
    if not isinstance(enviado, bool):
        raise ErroValidacao({"lembrete_enviado": "Use verdadeiro ou falso."})
    if conn.execute("UPDATE carrinhos SET lembrete_enviado = ?, lembrete_em = ? WHERE token = ?",
                    (int(enviado), horario.agora_db() if enviado else None, str(token))).rowcount != 1:
        raise NaoEncontrado("Carrinho não encontrado.")
    return {"id": token, "lembrete_enviado": enviado}
