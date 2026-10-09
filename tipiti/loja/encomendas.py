"""“Encomenda pra mim”: o cliente pede um produto que a loja não tem (link ou descrição), a loja cota e ele aceita.

O link enviado pelo cliente só é guardado e mostrado de volta: o servidor nunca o acessa.
"""

import hmac
import re
import secrets
from urllib.parse import urlsplit

from . import horario
from .ajustes import normalizar_whatsapp
from .validacao import UFS, ErroValidacao, NaoEncontrado

STATUS_ENCOMENDA = {
    "nova": "Recebida — vamos cotar",
    "cotada": "Cotada — aguardando sua resposta",
    "aceita": "Aceita",
    "recusada": "Recusada",
    "comprada": "Comprada",
    "entregue": "Entregue",
    "cancelada": "Cancelada",
}

# Mudanças de status pelo painel. "cotada" exige cotação e prazo preenchidos.
TRANSICOES_ENCOMENDA = {
    "nova": ("cotada", "cancelada"),
    "cotada": ("aceita", "recusada", "cancelada", "nova"),
    "aceita": ("comprada", "cancelada"),
    "recusada": ("cotada", "cancelada"),
    "comprada": ("entregue", "cancelada"),
    "entregue": (),
    "cancelada": (),
}

LINK_MAX = 500
DESCRICAO_MAX = 1000
OBSERVACAO_MAX = 1000
QTD_MAX = 50
PRAZO_MAX_DIAS = 365
COTACAO_MAX = 10 ** 9
_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_TAMANHO_CODIGO = 8


class Conflito(Exception):
    """Ação que não vale no estado atual (vira 409)."""


def link_valido(link):
    """Só http/https com endereço de servidor; sem espaços nem caracteres de controle."""
    if not isinstance(link, str) or not link or len(link) > LINK_MAX:
        return False
    if re.search(r"[\s\x00-\x1f\x7f<>\"'`\\]", link):
        return False
    try:
        partes = urlsplit(link)
    except ValueError:
        return False
    return partes.scheme.lower() in ("http", "https") and bool(partes.hostname)


def _gerar_codigo(conn):
    while True:
        codigo = "ENC-" + "".join(secrets.choice(_ALFABETO) for _ in range(_TAMANHO_CODIGO))
        if not conn.execute("SELECT 1 FROM encomendas WHERE codigo = ?", (codigo,)).fetchone():
            return codigo


def criar(conn, dados):
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    erros = {}
    nome = str(dados.get("nome") or "").strip()
    if not 3 <= len(nome) <= 120:
        erros["nome"] = "Informe seu nome (3 a 120 caracteres)."
    try:
        whatsapp = normalizar_whatsapp(dados.get("whatsapp"))
        if not whatsapp:
            erros["whatsapp"] = "Informe o WhatsApp com DDD, ex.: (92) 99123-4567."
    except ErroValidacao as e:
        erros.update(e.campos)
        whatsapp = ""
    cidade = str(dados.get("cidade") or "").strip()
    if not 2 <= len(cidade) <= 80:
        erros["cidade"] = "Informe a cidade."
    uf = str(dados.get("uf") or "").strip().upper()
    if uf not in UFS:
        erros["uf"] = "Selecione o estado."
    link = dados.get("link")
    link = link.strip() if isinstance(link, str) else ("" if link is None else None)
    if link is None or (link and not link_valido(link)):
        erros["link"] = f"Cole um link que comece com http:// ou https:// (até {LINK_MAX} caracteres)."
        link = ""
    descricao = dados.get("descricao")
    descricao = descricao.strip() if isinstance(descricao, str) else ""
    if len(descricao) > DESCRICAO_MAX:
        erros["descricao"] = f"A descrição deve ter no máximo {DESCRICAO_MAX} caracteres."
    if not link and not descricao and "link" not in erros:
        erros["descricao"] = "Cole o link do produto ou descreva o que você procura."
    quantidade = dados.get("quantidade", 1)
    if isinstance(quantidade, str) and re.fullmatch(r"[0-9]{1,3}", quantidade.strip()):
        quantidade = int(quantidade)
    if isinstance(quantidade, bool) or not isinstance(quantidade, int) or not 1 <= quantidade <= QTD_MAX:
        erros["quantidade"] = f"Quantidade de 1 a {QTD_MAX}."
    if erros:
        raise ErroValidacao(erros)
    codigo = _gerar_codigo(conn)
    conn.execute(
        """INSERT INTO encomendas (codigo, nome, whatsapp, cidade, uf, link, descricao, quantidade)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (codigo, nome, whatsapp, cidade, uf, link, descricao, quantidade),
    )
    return codigo


def _publica(row):
    return {
        "codigo": row["codigo"],
        "status": row["status"],
        "status_nome": STATUS_ENCOMENDA[row["status"]],
        "descricao": row["descricao"],
        "link": row["link"] or None,
        "quantidade": row["quantidade"],
        "cotacao_centavos": row["cotacao_centavos"],
        "prazo_dias": row["prazo_dias"],
        "observacao": row["observacao"],
        "criado_em": horario.iso_z(row["criado_em"]),
    }


def _admin(row):
    return {
        **_publica(row),
        "nome": row["nome"],
        "whatsapp": row["whatsapp"],
        "cidade": row["cidade"],
        "uf": row["uf"],
        "atualizado_em": horario.iso_z(row["atualizado_em"]),
        "proximos_status": list(TRANSICOES_ENCOMENDA[row["status"]]),
    }


def _confere(row, whatsapp):
    """WhatsApp informado (com ou sem 55) confere com o da encomenda? Comparação em tempo constante."""
    try:
        informado = normalizar_whatsapp(whatsapp if isinstance(whatsapp, (str, int)) else "")
    except ErroValidacao:
        return False
    return bool(informado) and hmac.compare_digest(informado.encode(), row["whatsapp"].encode())


def _buscar(conn, codigo, whatsapp):
    """Encomenda pelo código + WhatsApp. Código inexistente e WhatsApp errado dão a mesma resposta."""
    row = conn.execute("SELECT * FROM encomendas WHERE codigo = ?", (str(codigo).upper(),)).fetchone()
    if not row or not _confere(row, whatsapp):
        raise NaoEncontrado("Encomenda não encontrada. Confira o código e o WhatsApp.")
    return row


def obter_publica(conn, codigo, whatsapp):
    return _publica(_buscar(conn, codigo, whatsapp))


def responder(conn, codigo, dados):
    """O cliente aceita ou recusa a cotação (só quando a encomenda está "cotada")."""
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    row = _buscar(conn, codigo, dados.get("whatsapp"))
    aceitar = dados.get("aceitar")
    if not isinstance(aceitar, bool):
        raise ErroValidacao({"aceitar": "Responda se aceita (true) ou não (false) a cotação."})
    novo = "aceita" if aceitar else "recusada"
    cur = conn.execute(
        "UPDATE encomendas SET status = ?, atualizado_em = datetime('now') WHERE id = ? AND status = 'cotada'",
        (novo, row["id"]),
    )
    if cur.rowcount != 1:
        raise Conflito("Esta encomenda não está aguardando resposta.")
    return _publica(conn.execute("SELECT * FROM encomendas WHERE id = ?", (row["id"],)).fetchone())


def listar_admin(conn, status=None):
    sql, params = "SELECT * FROM encomendas", []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    return [_admin(r) for r in conn.execute(sql + " ORDER BY id DESC LIMIT 500", params)]


def contar_novas(conn):
    return conn.execute("SELECT COUNT(*) FROM encomendas WHERE status = 'nova'").fetchone()[0]


def _inteiro(valor, erros, campo, maximo, mensagem):
    if valor is None or valor == "":
        return None
    if isinstance(valor, bool) or not isinstance(valor, int) or not 1 <= valor <= maximo:
        erros[campo] = mensagem
        return None
    return valor


def atualizar_admin(conn, codigo, dados):
    """PATCH do painel: {status?, cotacao_centavos?, prazo_dias?, observacao?}.

    Preencher cotação e prazo de uma encomenda "nova" (ou "recusada", para cotar de novo) já a deixa "cotada".
    """
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    row = conn.execute("SELECT * FROM encomendas WHERE codigo = ?", (str(codigo).upper(),)).fetchone()
    if not row:
        raise NaoEncontrado("Encomenda não encontrada.")
    erros = {}
    valores = {"cotacao_centavos": row["cotacao_centavos"], "prazo_dias": row["prazo_dias"],
               "observacao": row["observacao"]}
    if "cotacao_centavos" in dados:
        valores["cotacao_centavos"] = _inteiro(dados["cotacao_centavos"], erros, "cotacao_centavos", COTACAO_MAX,
                                               "Informe o valor da cotação em centavos.")
    if "prazo_dias" in dados:
        valores["prazo_dias"] = _inteiro(dados["prazo_dias"], erros, "prazo_dias", PRAZO_MAX_DIAS,
                                         f"Informe o prazo em dias (1 a {PRAZO_MAX_DIAS}).")
    if "observacao" in dados:
        obs = dados["observacao"]
        obs = "" if obs is None else obs
        if not isinstance(obs, str) or len(obs.strip()) > OBSERVACAO_MAX:
            erros["observacao"] = f"Observação com no máximo {OBSERVACAO_MAX} caracteres."
        else:
            valores["observacao"] = obs.strip()
    atual = row["status"]
    novo = atual
    if "status" in dados and dados["status"] not in (None, "", atual):
        novo = dados["status"]
        if not isinstance(novo, str) or novo not in STATUS_ENCOMENDA:
            erros["status"] = "Status inválido."
        elif novo not in TRANSICOES_ENCOMENDA[atual]:
            erros["status"] = (f"Uma encomenda “{STATUS_ENCOMENDA[atual]}” não pode passar para "
                               f"“{STATUS_ENCOMENDA[novo]}”.")
    mudou_cotacao = any(c in dados for c in ("cotacao_centavos", "prazo_dias"))
    if mudou_cotacao and atual not in ("nova", "cotada", "recusada") and novo == atual:
        erros["cotacao_centavos"] = "A cotação não pode mudar depois de aceita."
    cotada = valores["cotacao_centavos"] is not None and valores["prazo_dias"] is not None
    if not erros and novo == atual and mudou_cotacao and cotada and atual in ("nova", "recusada"):
        novo = "cotada"
    if not erros and novo == "cotada" and not cotada:
        erros["cotacao_centavos"] = "Para cotar, informe o valor e o prazo."
    if erros:
        raise ErroValidacao(erros)
    conn.execute(
        """UPDATE encomendas SET status = ?, cotacao_centavos = ?, prazo_dias = ?, observacao = ?,
               atualizado_em = datetime('now') WHERE id = ?""",
        (novo, valores["cotacao_centavos"], valores["prazo_dias"], valores["observacao"], row["id"]),
    )
    return _admin(conn.execute("SELECT * FROM encomendas WHERE id = ?", (row["id"],)).fetchone())
