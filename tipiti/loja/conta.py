"""Minha conta, sem senha: link de acesso de uso único por e-mail e sessão de 30 dias.

Tokens (link e sessão) são gerados com secrets.token_urlsafe(32) e só o SHA-256 deles fica no banco.
Nenhuma resposta revela se um e-mail tem pedidos na loja.
"""

import hashlib
import secrets

from . import horario, notificacoes
from .pedidos import obter_pedido_publico
from .validacao import UFS, ErroValidacao, NaoEncontrado, email_valido, so_digitos

LINK_MINUTOS = 30
SESSAO_DIAS = 30
ENDERECOS_MAX = 10
PEDIDOS_MAX = 50


class SessaoInvalida(Exception):
    pass


def hash_token(token):
    return hashlib.sha256(str(token).encode()).hexdigest()


def normalizar_email(email):
    texto = str(email or "").strip().lower()
    if not email_valido(texto) or any(c in texto for c in "\r\n"):
        raise ErroValidacao({"email": "Informe um e-mail válido."})
    return texto


def solicitar_acesso(conn, email):
    """Envia o link só se houver pedidos com esse e-mail; a resposta é sempre a mesma."""
    email = normalizar_email(email)
    if conn.execute("SELECT 1 FROM pedidos WHERE cliente_email = ? LIMIT 1", (email,)).fetchone():
        token = secrets.token_urlsafe(32)
        conn.execute("INSERT INTO links_conta (token_hash, email, criado_em, expira_em) VALUES (?, ?, ?, ?)",
                     (hash_token(token), email, horario.agora_db(), horario.agora_db(minutes=LINK_MINUTOS)))
        notificacoes.link_conta(conn, email, token)
    return {"ok": True}


def criar_sessao(conn, token):
    """Troca o link (uso único, 30 min) por uma sessão de 30 dias."""
    if not isinstance(token, str) or not 20 <= len(token) <= 100:
        raise SessaoInvalida()
    agora = horario.agora_db()
    th = hash_token(token)
    row = conn.execute("SELECT email FROM links_conta WHERE token_hash = ? AND usado_em IS NULL AND expira_em > ?",
                       (th, agora)).fetchone()
    # marcar como usado é condicional: dois pedidos simultâneos com o mesmo link não geram duas sessões
    if not row or conn.execute("UPDATE links_conta SET usado_em = ? WHERE token_hash = ? AND usado_em IS NULL",
                               (agora, th)).rowcount != 1:
        raise SessaoInvalida()
    sessao = secrets.token_urlsafe(32)
    expira = horario.agora_db(days=SESSAO_DIAS)
    conn.execute("INSERT INTO sessoes_conta (token_hash, email, criada_em, expira_em) VALUES (?, ?, ?, ?)",
                 (hash_token(sessao), row["email"], agora, expira))
    return {"sessao": sessao, "expira_em": horario.iso_z(expira)}


def email_da_sessao(conn, sessao):
    if not isinstance(sessao, str) or not 20 <= len(sessao) <= 100:
        raise SessaoInvalida()
    row = conn.execute("SELECT email FROM sessoes_conta WHERE token_hash = ? AND expira_em > ?",
                       (hash_token(sessao), horario.agora_db())).fetchone()
    if not row:
        raise SessaoInvalida()
    return row["email"]


def encerrar_sessao(conn, sessao):
    conn.execute("DELETE FROM sessoes_conta WHERE token_hash = ?", (hash_token(sessao),))
    return {"ok": True}


def _endereco_dict(r):
    return {k: r[k] for k in ("id", "apelido", "cep", "endereco", "numero", "complemento", "bairro", "cidade", "uf")}


def listar_enderecos(conn, email):
    return [_endereco_dict(r) for r in conn.execute(
        "SELECT * FROM enderecos_conta WHERE email = ? ORDER BY id", (email,)).fetchall()]


def resumo(conn, email):
    from . import avise_me
    rows = conn.execute("SELECT codigo, cliente_nome FROM pedidos WHERE cliente_email = ? ORDER BY id DESC LIMIT ?",
                        (email, PEDIDOS_MAX)).fetchall()
    pedidos = [obter_pedido_publico(conn, r["codigo"]) for r in rows]
    avisos = conn.execute(avise_me._SELECT + " WHERE a.email = ? ORDER BY a.id DESC LIMIT 100", (email,)).fetchall()
    return {
        "email": email,
        "nome": rows[0]["cliente_nome"] if rows else None,
        "pedidos": pedidos,
        "enderecos": listar_enderecos(conn, email),
        "avise_me": [{"id": a["id"], "produto": {"nome": a["produto_nome"], "slug": a["produto_slug"]},
                      "variacao": a["variacao_nome"], "status": a["status"], "criado_em": horario.iso_z(a["criado_em"])}
                     for a in avisos],
    }


def _texto(dados, campo, erros, rotulo, maximo=120, obrigatorio=True):
    valor = " ".join(str(dados.get(campo) or "").split())
    if not valor and obrigatorio:
        erros[campo] = f"Informe {rotulo}."
    elif len(valor) > maximo:
        erros[campo] = f"Use no máximo {maximo} caracteres."
    return valor


def salvar_endereco(conn, email, dados):
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    erros = {}
    e = {
        "apelido": _texto(dados, "apelido", erros, "um apelido", maximo=40, obrigatorio=False),
        "cep": so_digitos(dados.get("cep")),
        "endereco": _texto(dados, "endereco", erros, "o endereço"),
        "numero": _texto(dados, "numero", erros, "o número", maximo=20),
        "complemento": _texto(dados, "complemento", erros, "o complemento", obrigatorio=False),
        "bairro": _texto(dados, "bairro", erros, "o bairro"),
        "cidade": _texto(dados, "cidade", erros, "a cidade"),
        "uf": str(dados.get("uf") or "").strip().upper(),
    }
    if len(e["cep"]) != 8:
        erros["cep"] = "Informe um CEP com 8 dígitos."
    if e["uf"] not in UFS:
        erros["uf"] = "Selecione o estado."
    if erros:
        raise ErroValidacao(erros)
    total = conn.execute("SELECT COUNT(*) FROM enderecos_conta WHERE email = ?", (email,)).fetchone()[0]
    if total >= ENDERECOS_MAX:
        raise ErroValidacao({"geral": f"Máximo de {ENDERECOS_MAX} endereços salvos."})
    cur = conn.execute(
        """INSERT INTO enderecos_conta (email, apelido, cep, endereco, numero, complemento, bairro, cidade, uf, criado_em)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (email, e["apelido"], e["cep"], e["endereco"], e["numero"], e["complemento"], e["bairro"], e["cidade"],
         e["uf"], horario.agora_db()),
    )
    return _endereco_dict(conn.execute("SELECT * FROM enderecos_conta WHERE id = ?", (cur.lastrowid,)).fetchone())


def remover_endereco(conn, email, endereco_id):
    if conn.execute("DELETE FROM enderecos_conta WHERE id = ? AND email = ?", (endereco_id, email)).rowcount != 1:
        raise NaoEncontrado("Endereço não encontrado.")
    return {"ok": True}
