"""Operação: lista de separação (com dados para etiqueta) e marcação de pedidos separados."""

from . import ajustes, horario, legal, rastreio
from .reservas import STATUS_PEDIDO
from .validacao import ErroValidacao


def _viagens(conn, ids_viagem):
    """Viagens atribuídas aos pedidos (pedidos.viagem_id)."""
    ids = sorted({i for i in ids_viagem if i})
    if not ids:
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
    viagens = _viagens(conn, [p["viagem_id"] for p in pedidos])
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
            "zona": p["zona_frete"], "viagem": viagens.get(p["viagem_id"]),
            "itens": itens.get(p["id"], []), "separado_em": horario.iso_z(p["separado_em"]),
        })
    return {
        "remetente": remetente(conn),
        "pedidos": lista,
        "consolidado": [{"produto": k[0], "variacao": k[1], "sku": k[2], "quantidade": q}
                        for k, q in sorted(consolidado.items(), key=lambda x: (x[0][0], x[0][1] or ""))],
    }


def registrar_evento_separado(conn, codigo):
    """Evento "separado" do rastreio (com a mensagem padrão e o e-mail ao cliente) e `pedidos.separado_em`,
    na mesma transação."""
    rastreio.adicionar_evento(
        conn, codigo, {"tipo": "separado"},
        junto=lambda row: conn.execute("UPDATE pedidos SET separado_em = ? WHERE id = ?",
                                       (horario.agora_db(), row["id"])))


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
        registrar_evento_separado(conn, codigo)
        separados.append(codigo)
    return {"separados": separados, "nao_encontrados": nao_encontrados}
