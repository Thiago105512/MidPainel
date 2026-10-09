"""Operação: lista de separação (com dados para etiqueta) e marcação de pedidos separados."""

import sqlite3

from . import ajustes, horario, legal, notificacoes
from .reservas import STATUS_PEDIDO
from .validacao import ErroValidacao


def _colunas(conn, tabela):
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({tabela})")}


def _tabela_existe(conn, nome):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (nome,)).fetchone() is not None


def _viagens(conn, ids_viagem):
    """Viagem atribuída (rodada 2: tabela `viagens` e coluna pedidos.viagem_id), quando existir."""
    ids = sorted({i for i in ids_viagem if i})
    if not ids or not _tabela_existe(conn, "viagens"):
        return {}
    rows = conn.execute(f"SELECT * FROM viagens WHERE id IN ({','.join('?' * len(ids))})", ids).fetchall()
    return {r["id"]: {k: r[k] for k in r.keys() if k in ("id", "zona", "embarcacao", "saida", "chegada_prevista")}
            for r in rows}


def remetente(conn):
    a = ajustes.obter(conn)
    e = legal.empresa(a)
    return {
        "nome": e["razao_social"] or e["nome_fantasia"],
        "documento": e["documento_formatado"],
        "endereco": a.get("empresa_endereco") or None,
        "cidade": a.get("empresa_cidade") or None,
        "uf": a.get("empresa_uf") or None,
        "cep": legal.formatar_cep(a.get("empresa_cep") or "") or None,
        "telefone": e["telefone"],
    }


def listar(conn, status="pago"):
    status = status or "pago"
    if status not in STATUS_PEDIDO:
        raise ErroValidacao({"status": "Status inválido."})
    com_viagem = "viagem_id" in _colunas(conn, "pedidos")
    pedidos = conn.execute("SELECT * FROM pedidos WHERE status = ? ORDER BY id LIMIT 500", (status,)).fetchall()
    ids = [p["id"] for p in pedidos]
    itens = {}
    if ids:
        for i in conn.execute(
                f"""SELECT i.pedido_id, i.nome, i.variacao_nome, i.quantidade, p.slug, v.sku
                    FROM itens_pedido i JOIN produtos p ON p.id = i.produto_id
                    LEFT JOIN variacoes v ON v.id = i.variacao_id
                    WHERE i.pedido_id IN ({','.join('?' * len(ids))}) ORDER BY i.id""", ids).fetchall():
            itens.setdefault(i["pedido_id"], []).append(
                {"produto": i["nome"], "variacao": i["variacao_nome"] or None, "sku": i["sku"] or i["slug"],
                 "quantidade": i["quantidade"]})
    viagens = _viagens(conn, [p["viagem_id"] for p in pedidos] if com_viagem else [])
    lista, consolidado = [], {}
    for p in pedidos:
        for i in itens.get(p["id"], []):
            chave = (i["produto"], i["variacao"], i["sku"])
            consolidado[chave] = consolidado.get(chave, 0) + i["quantidade"]
        lista.append({
            "codigo": p["codigo"], "status": p["status"], "criado_em": horario.iso_z(p["criado_em"]),
            "destinatario": p["cliente_nome"], "telefone": p["cliente_telefone"],
            "endereco": p["endereco"], "numero": p["numero"], "complemento": p["complemento"], "bairro": p["bairro"],
            "cep": legal.formatar_cep(p["cep"]), "cidade": p["cidade"], "uf": p["uf"],
            "zona": p["zona_frete"], "viagem": viagens.get(p["viagem_id"]) if com_viagem else None,
            "itens": itens.get(p["id"], []), "separado_em": horario.iso_z(p["separado_em"]),
        })
    return {
        "remetente": remetente(conn),
        "pedidos": lista,
        "consolidado": [{"produto": k[0], "variacao": k[1], "sku": k[2], "quantidade": q}
                        for k, q in sorted(consolidado.items(), key=lambda x: (x[0][0], x[0][1] or ""))],
    }


def registrar_evento_separado(conn, pedido_id, codigo):
    """Registra o evento "separado".

    Ponto de integração com o rastreio da rodada 2: grava `pedidos.separado_em` e, se houver uma tabela
    `eventos_pedido` (pedido_id, tipo, mensagem, data/criado_em), insere o evento nela. Na fusão, pode ser
    redirecionado para a função de eventos do módulo de rastreio.
    """
    agora = horario.agora_db()
    conn.execute("UPDATE pedidos SET separado_em = ? WHERE id = ?", (agora, pedido_id))
    if _tabela_existe(conn, "eventos_pedido"):
        cols = _colunas(conn, "eventos_pedido")
        coluna_data = next((c for c in ("data", "criado_em") if c in cols), None)
        if {"pedido_id", "tipo"} <= cols:
            campos, valores = ["pedido_id", "tipo"], [pedido_id, "separado"]
            if "mensagem" in cols:
                campos.append("mensagem")
                valores.append("Pedido separado e embalado.")
            if coluna_data:
                campos.append(coluna_data)
                valores.append(agora)
            try:
                conn.execute(f"INSERT INTO eventos_pedido ({', '.join(campos)}) "
                             f"VALUES ({', '.join('?' * len(campos))})", valores)
            except sqlite3.Error:  # esquema diferente do esperado: separado_em continua valendo
                pass
    notificacoes.evento_pedido(conn, codigo, "separado", "Seu pedido foi separado e embalado.")


def marcar_separados(conn, dados):
    codigos = dados.get("codigos") if isinstance(dados, dict) else None
    if not isinstance(codigos, list) or not codigos or len(codigos) > 200 or \
            not all(isinstance(c, str) and 4 <= len(c) <= 20 for c in codigos):
        raise ErroValidacao({"codigos": "Informe os códigos dos pedidos."})
    separados, nao_encontrados = [], []
    for codigo in dict.fromkeys(c.upper() for c in codigos):
        row = conn.execute("SELECT id, status FROM pedidos WHERE codigo = ?", (codigo,)).fetchone()
        if not row or row["status"] == "cancelado":
            nao_encontrados.append(codigo)
            continue
        registrar_evento_separado(conn, row["id"], codigo)
        separados.append(codigo)
    return {"separados": separados, "nao_encontrados": nao_encontrados}
