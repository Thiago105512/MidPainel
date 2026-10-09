"""Pedidos: criação (com baixa de estoque), consulta, listagem do painel e resumo de vendas."""

import secrets

from . import config, cupons
from .avaliacoes import produtos_avaliados
from .carrinho import FORMAS_PAGAMENTO, _cotar, _linhas, _normalizar_itens
from .catalogo import _sincronizar_estoque
from .imagens import url_imagem
from .reservas import STATUS_PEDIDO, TRANSICOES, expirar_pendentes
from .validacao import UFS, ErroValidacao, NaoEncontrado, cpf_valido, email_valido, so_digitos
from . import rastreio, revendedoras


_ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_TAMANHO_CODIGO = 12


def _texto(dados, campo, erros, rotulo, minimo=1, maximo=120, obrigatorio=True):
    valor = str(dados.get(campo) or "").strip()
    if not valor and obrigatorio:
        erros[campo] = f"Informe {rotulo}."
    elif valor and not (minimo <= len(valor) <= maximo):
        erros[campo] = f"{rotulo.capitalize()} deve ter entre {minimo} e {maximo} caracteres."
    return valor


def _validar_cliente(dados):
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    erros = {}
    c = {
        "nome": _texto(dados, "nome", erros, "o nome completo", minimo=3),
        "email": str(dados.get("email") or "").strip().lower(),
        "cpf": so_digitos(dados.get("cpf")),
        "telefone": so_digitos(dados.get("telefone")),
        "cep": so_digitos(dados.get("cep")),
        "endereco": _texto(dados, "endereco", erros, "o endereço"),
        "numero": _texto(dados, "numero", erros, "o número", maximo=20),
        "complemento": _texto(dados, "complemento", erros, "o complemento", obrigatorio=False),
        "bairro": _texto(dados, "bairro", erros, "o bairro"),
        "cidade": _texto(dados, "cidade", erros, "a cidade"),
        "uf": str(dados.get("uf") or "").strip().upper(),
        "pagamento": str(dados.get("pagamento") or ""),
    }
    if not email_valido(c["email"]):
        erros["email"] = "Informe um e-mail válido."
    if not cpf_valido(c["cpf"]):
        erros["cpf"] = "Informe um CPF válido."
    if len(c["telefone"]) not in (10, 11):
        erros["telefone"] = "Informe o telefone com DDD."
    if len(c["cep"]) != 8:
        erros["cep"] = "Informe um CEP com 8 dígitos."
    if c["uf"] not in UFS:
        erros["uf"] = "Selecione o estado."
    if c["pagamento"] not in FORMAS_PAGAMENTO:
        erros["pagamento"] = "Escolha a forma de pagamento."
    try:
        c["parcelas"] = int(dados.get("parcelas") or 1)
    except (TypeError, ValueError):
        erros["parcelas"] = "Parcelamento inválido."
    c["cupom"] = dados.get("cupom")
    if c["cupom"] is not None and not isinstance(c["cupom"], str):
        erros["cupom"] = "Cupom inválido. Confira o código."
    if erros:
        raise ErroValidacao(erros)
    return c


def _gerar_codigo(conn):
    while True:
        codigo = "TPT-" + "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(_TAMANHO_CODIGO))
        if not conn.execute("SELECT 1 FROM pedidos WHERE codigo = ?", (codigo,)).fetchone():
            return codigo


def criar_pedido(conn, dados):
    cliente = _validar_cliente(dados)
    quantidades = _normalizar_itens(dados.get("itens"))
    expirar_pendentes(conn)

    conn.execute("BEGIN IMMEDIATE")
    try:
        cotacao = _cotar(conn, [{"slug": s, "variacao": v, "quantidade": q} for (s, v), q in quantidades.items()],
                         cep=cliente["cep"], pagamento=cliente["pagamento"], cupom=cliente["cupom"], cpf=cliente["cpf"])
        if not cotacao["valido"]:
            problemas = {l["chave"]: l["erro"] for l in cotacao["itens"] if not l["disponivel"]}
            raise ErroValidacao({"itens": problemas}, "Alguns itens do carrinho não estão mais disponíveis.")
        if cotacao["cupom_erro"]:
            raise ErroValidacao({"cupom": cotacao["cupom_erro"]}, cotacao["cupom_erro"])
        cupom = cotacao["cupom"]
        # dentro da transação: dois pedidos simultâneos não passam do limite de usos
        if cupom and not cupons.registrar_uso(conn, cupom["codigo"]):
            esgotado = "Este cupom já atingiu o limite de usos."
            raise ErroValidacao({"cupom": esgotado}, esgotado)
        if not 1 <= cliente["parcelas"] <= cotacao["parcelas_max"]:
            raise ErroValidacao({"parcelas": f"Parcelamento em até {cotacao['parcelas_max']}x."})

        custos = {l["chave"]: l["custo_unit_centavos"] for l in _linhas(conn, quantidades)}
        for linha in cotacao["itens"]:
            if linha["variacao_id"]:
                sql = "UPDATE variacoes SET estoque = estoque - ? WHERE id = ? AND estoque >= ?"
                alvo = linha["variacao_id"]
            else:
                sql = "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?"
                alvo = linha["produto_id"]
            if conn.execute(sql, (linha["quantidade"], alvo, linha["quantidade"])).rowcount != 1:
                raise ErroValidacao({"itens": {linha["chave"]: "Sem estoque."}}, "Estoque insuficiente.")
        for produto_id in {l["produto_id"] for l in cotacao["itens"] if l["variacao_id"]}:
            _sincronizar_estoque(conn, produto_id)

        codigo = _gerar_codigo(conn)
        f = cotacao["frete"]
        cur = conn.execute(
            """INSERT INTO pedidos (codigo, status, cliente_nome, cliente_email, cliente_cpf, cliente_telefone,
                   cep, endereco, numero, complemento, bairro, cidade, uf, zona_frete, prazo_dias,
                   pagamento, parcelas, subtotal_centavos, desconto_centavos, frete_centavos, total_centavos,
                   cupom_codigo, desconto_cupom_centavos)
               VALUES (?, 'aguardando_pagamento', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                codigo, cliente["nome"], cliente["email"], cliente["cpf"], cliente["telefone"],
                cliente["cep"], cliente["endereco"], cliente["numero"], cliente["complemento"],
                cliente["bairro"], cliente["cidade"], cliente["uf"], f["zona_nome"], f["prazo_dias"],
                cliente["pagamento"], cliente["parcelas"], cotacao["subtotal_centavos"],
                cotacao["desconto_centavos"], f["valor_centavos"], cotacao["total_centavos"],
                cupom["codigo"] if cupom else None, cotacao["desconto_cupom_centavos"],
            ),
        )
        pedido_id = cur.lastrowid
        conn.executemany(
            """INSERT INTO itens_pedido (pedido_id, produto_id, variacao_id, nome, variacao_nome,
                   preco_unit_centavos, preco_ancora_unit_centavos, custo_unit_centavos, quantidade)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [(pedido_id, l["produto_id"], l["variacao_id"], l["nome"], l["variacao_nome"], l["preco_unit_centavos"],
              l["preco_ancora_unit_centavos"], custos.get(l["chave"]), l["quantidade"]) for l in cotacao["itens"]],
        )
        revendedoras.atribuir_pedido(conn, pedido_id, dados, cotacao, cliente["cpf"])
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return codigo


def _itens_dos_pedidos(conn, pedido_ids, admin=False, pode_avaliar=None):
    """Itens de vários pedidos numa consulta só: {pedido_id: [itens]}. pode_avaliar(produto_id) -> bool, opcional."""
    itens = {pid: [] for pid in pedido_ids}
    if not itens:
        return itens
    rows = conn.execute(
        f"""SELECT i.pedido_id, i.produto_id, i.nome, i.variacao_nome, i.preco_unit_centavos,
                   i.preco_ancora_unit_centavos, i.custo_unit_centavos, i.quantidade, p.slug, p.foto
            FROM itens_pedido i JOIN produtos p ON p.id = i.produto_id
            WHERE i.pedido_id IN ({",".join("?" * len(itens))}) ORDER BY i.id""",
        list(itens),
    ).fetchall()
    for r in rows:
        item = dict(r, imagem=url_imagem(r["slug"], r["foto"]))
        del item["foto"], item["pedido_id"], item["produto_id"]
        if pode_avaliar is not None:
            item["pode_avaliar"] = pode_avaliar(r["produto_id"])
        if not admin:
            del item["custo_unit_centavos"]
        itens[r["pedido_id"]].append(item)
    return itens


def _resumo_pedido(row, itens, admin=False):
    resumo = {
        "codigo": row["codigo"],
        "status": row["status"],
        "status_nome": STATUS_PEDIDO[row["status"]],
        "pagamento": row["pagamento"],
        "pagamento_nome": FORMAS_PAGAMENTO[row["pagamento"]],
        "parcelas": row["parcelas"],
        "subtotal_centavos": row["subtotal_centavos"],
        "cupom_codigo": row["cupom_codigo"],
        "desconto_cupom_centavos": row["desconto_cupom_centavos"],
        "desconto_centavos": row["desconto_centavos"],
        "frete_centavos": row["frete_centavos"],
        "total_centavos": row["total_centavos"],
        "zona_frete": row["zona_frete"],
        "prazo_dias": row["prazo_dias"],
        "criado_em": row["criado_em"],
        "itens": itens,
    }
    if admin:
        resumo["lucro_centavos"] = lucro_do_pedido(resumo)
        resumo["proximos_status"] = list(TRANSICOES[row["status"]])
    return resumo


def lucro_do_pedido(resumo):
    """Receita dos produtos (já com os descontos do cupom e do Pix) menos o custo deles. None se faltar o custo de
    algum item.

    O frete cobrado é tratado como repasse e fica fora da conta.
    """
    if any(i["custo_unit_centavos"] is None for i in resumo["itens"]):
        return None
    custo = sum(i["custo_unit_centavos"] * i["quantidade"] for i in resumo["itens"])
    descontos = resumo.get("desconto_cupom_centavos", 0) + resumo["desconto_centavos"]
    return resumo["subtotal_centavos"] - descontos - custo


def obter_pedido_publico(conn, codigo):
    """Visão do cliente pelo código: sem CPF, e-mail, telefone nem endereço completo."""
    row = conn.execute("SELECT * FROM pedidos WHERE codigo = ?", (str(codigo).upper(),)).fetchone()
    if not row:
        raise NaoEncontrado("Pedido não encontrado.")
    # cada produto entregue pode ser avaliado uma vez por pedido
    avaliados = produtos_avaliados(conn, row["id"]) if row["status"] == "entregue" else None
    itens = _itens_dos_pedidos(conn, [row["id"]],
                               pode_avaliar=lambda pid: avaliados is not None and pid not in avaliados)
    resumo = _resumo_pedido(row, itens[row["id"]])
    resumo["primeiro_nome"] = row["cliente_nome"].split()[0]
    resumo["destino"] = f"{row['cidade']} - {row['uf']}"
    rastreio.anexar(conn, [(row, resumo)])
    return resumo


def listar_pedidos(conn, status=None):
    expirar_pendentes(conn)
    sql, params = "SELECT * FROM pedidos", []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY id DESC LIMIT 500"
    rows = conn.execute(sql, params).fetchall()
    itens = _itens_dos_pedidos(conn, [r["id"] for r in rows], admin=True)
    pedidos = []
    for row in rows:
        resumo = _resumo_pedido(row, itens[row["id"]], admin=True)
        resumo["cliente"] = {
            "nome": row["cliente_nome"], "email": row["cliente_email"], "cpf": row["cliente_cpf"],
            "telefone": row["cliente_telefone"],
        }
        resumo["entrega"] = {
            "cep": row["cep"], "endereco": row["endereco"], "numero": row["numero"],
            "complemento": row["complemento"], "bairro": row["bairro"], "cidade": row["cidade"], "uf": row["uf"],
        }
        pedidos.append(resumo)
    rastreio.anexar(conn, list(zip(rows, pedidos)), admin=True)
    revendedoras.anexar_aos_pedidos(conn, list(zip(rows, pedidos)))
    return pedidos


def resumo_vendas(conn):
    """Totais de todos os pedidos não cancelados. O lucro só soma pedidos em que todo item tem custo."""
    expirar_pendentes(conn)
    totais = conn.execute(
        """SELECT COUNT(*) AS pedidos,
                  COALESCE(SUM(p.total_centavos), 0) AS faturamento,
                  COALESCE(SUM(CASE WHEN COALESCE(i.sem_custo, 0) = 0
                               THEN p.subtotal_centavos - p.desconto_cupom_centavos - p.desconto_centavos
                                    - COALESCE(i.custo, 0) END), 0) AS lucro,
                  COALESCE(SUM(COALESCE(i.sem_custo, 0) > 0), 0) AS sem_custo
           FROM pedidos p
           LEFT JOIN (SELECT pedido_id, SUM(custo_unit_centavos * quantidade) AS custo,
                             SUM(custo_unit_centavos IS NULL) AS sem_custo
                      FROM itens_pedido GROUP BY pedido_id) i ON i.pedido_id = p.id
           WHERE p.status != 'cancelado'"""
    ).fetchone()
    baixo = conn.execute(
        "SELECT slug, nome, estoque FROM produtos WHERE ativo = 1 AND estoque <= ? ORDER BY estoque, nome",
        (config.ESTOQUE_BAIXO,),
    ).fetchall()
    return {
        "pedidos": totais["pedidos"],
        "faturamento_centavos": totais["faturamento"],
        "ticket_medio_centavos": totais["faturamento"] // totais["pedidos"] if totais["pedidos"] else 0,
        "lucro_centavos": totais["lucro"],
        "pedidos_sem_custo": totais["sem_custo"],
        "estoque_baixo": [dict(r) for r in baixo],
    }
