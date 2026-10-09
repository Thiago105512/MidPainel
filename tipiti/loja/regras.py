"""Regras de negócio: catálogo, carrinho, pedidos e validações."""

import re
import secrets

from . import config, frete
from .db import atualizar_busca, normaliza


class ErroValidacao(Exception):
    def __init__(self, campos, mensagem="Verifique os dados informados."):
        super().__init__(mensagem)
        self.campos = campos
        self.mensagem = mensagem


class NaoEncontrado(Exception):
    pass


STATUS_PEDIDO = {
    "aguardando_pagamento": "Aguardando pagamento",
    "pago": "Pago",
    "enviado": "Enviado",
    "entregue": "Entregue",
    "cancelado": "Cancelado",
}

FORMAS_PAGAMENTO = {"pix": "Pix", "cartao": "Cartão de crédito", "boleto": "Boleto"}

UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

ORDENACOES = {
    "relevancia": "p.destaque DESC, p.nome",
    "menor_preco": "p.preco_centavos, p.nome",
    "maior_preco": "p.preco_centavos DESC, p.nome",
    "novidades": "p.id DESC",
    "nome": "p.nome",
}

# Mudanças de status permitidas no painel. Cancelar devolve as unidades ao estoque.
TRANSICOES = {
    "aguardando_pagamento": ("pago", "cancelado"),
    "pago": ("enviado", "cancelado", "aguardando_pagamento"),
    "enviado": ("entregue",),
    "entregue": (),
    "cancelado": (),
}

_ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_TAMANHO_CODIGO = 12
INTEIRO_MAX = 10 ** 9


# ---------------------------------------------------------------- validações

def so_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def cpf_valido(cpf):
    d = so_digitos(cpf)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        if (soma * 10) % 11 % 10 != int(d[n]):
            return False
    return True


def email_valido(email):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email or "")) and len(email) <= 254


def cep_digitos(cep):
    d = so_digitos(cep)
    if len(d) != 8:
        raise ErroValidacao({"cep": "Informe um CEP com 8 dígitos."})
    return d


# ---------------------------------------------------------------- catálogo

def url_imagem(slug, foto=""):
    return f"/fotos/{foto}" if foto else f"/img/produto/{slug}.svg"


def gerar_slug(texto):
    slug = re.sub(r"[^a-z0-9]+", "-", normaliza(texto)).strip("-")
    return slug[:80].strip("-") or "produto"


def url_miniatura(row):
    """Miniatura da capa; fotos antigas, sem miniatura própria, usam o arquivo principal."""
    if not row["foto"]:
        return None
    return f"/fotos/{row['foto_miniatura'] or row['foto']}"


def _produto(row, admin=False, com_descricao=True):
    produto = {
        "id": row["id"],
        "slug": row["slug"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "preco_centavos": row["preco_centavos"],
        "preco_de_centavos": row["preco_de_centavos"],
        "estoque": row["estoque"],
        "icone": row["icone"],
        "destaque": bool(row["destaque"]),
        "ativo": bool(row["ativo"]),
        "imagem": url_imagem(row["slug"], row["foto"]),
        "imagem_miniatura": url_miniatura(row),
        "cor": row["categoria_cor"],
        "tem_variacoes": row["n_variacoes"] > 0,
        "categoria": {"slug": row["categoria_slug"], "nome": row["categoria_nome"]},
    }
    if not com_descricao:
        del produto["descricao"]
    if admin:
        produto["custo_centavos"] = row["custo_centavos"]
    return produto


_SELECT_PRODUTO = """
    SELECT p.*, c.slug AS categoria_slug, c.nome AS categoria_nome, c.cor AS categoria_cor,
           (SELECT COUNT(*) FROM variacoes v WHERE v.produto_id = p.id AND v.ativo = 1) AS n_variacoes,
           (SELECT COUNT(*) FROM variacoes v WHERE v.produto_id = p.id) AS n_variacoes_total,
           (SELECT f.miniatura FROM fotos_produto f WHERE f.produto_id = p.id ORDER BY f.ordem, f.id LIMIT 1)
               AS foto_miniatura
    FROM produtos p JOIN categorias c ON c.id = p.categoria_id
"""


def listar_categorias(conn):
    rows = conn.execute(
        """SELECT c.slug, c.nome, c.descricao, c.icone, c.cor,
                  (SELECT COUNT(*) FROM produtos p WHERE p.categoria_id = c.id AND p.ativo = 1) AS total
           FROM categorias c ORDER BY c.ordem, c.nome"""
    ).fetchall()
    return [dict(r) for r in rows]


def obter_categoria(conn, slug):
    row = conn.execute(
        "SELECT slug, nome, descricao, icone, cor FROM categorias WHERE slug = ?", (slug,)
    ).fetchone()
    if not row:
        raise NaoEncontrado("Categoria não encontrada.")
    return dict(row)


def listar_produtos(conn, categoria=None, busca=None, ordem="relevancia", destaque=False,
                    limite=None, offset=0, incluir_inativos=False, admin=False):
    """Listagens públicas não trazem a descrição (só a página do produto precisa dela)."""
    where, params = [], []
    if not incluir_inativos:
        where.append("p.ativo = 1")
    if categoria:
        where.append("c.slug = ?")
        params.append(categoria)
    if destaque:
        where.append("p.destaque = 1")
    for termo in normaliza(busca or "").split()[:8]:
        termo = termo.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where.append("p.busca LIKE ? ESCAPE '\\'")
        params.append(f"%{termo}%")
    sql = _SELECT_PRODUTO
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY " + ORDENACOES.get(ordem, ORDENACOES["relevancia"])
    if limite or offset:
        sql += " LIMIT ? OFFSET ?"
        params += [int(limite) if limite else -1, int(offset or 0)]
    return [_produto(r, admin, com_descricao=admin) for r in conn.execute(sql, params).fetchall()]


def _variacoes(conn, produto_id, incluir_inativas=False):
    sql = "SELECT id, nome, sku, preco_centavos, estoque, ativo FROM variacoes WHERE produto_id = ?"
    if not incluir_inativas:
        sql += " AND ativo = 1"
    rows = conn.execute(sql + " ORDER BY ordem, id", (produto_id,)).fetchall()
    return [dict(r, ativo=bool(r["ativo"])) for r in rows]


def _fotos(conn, produto_id):
    rows = conn.execute(
        "SELECT id, arquivo, miniatura FROM fotos_produto WHERE produto_id = ? ORDER BY ordem, id", (produto_id,)
    ).fetchall()
    return [{"id": r["id"], "url": f"/fotos/{r['arquivo']}", "miniatura": f"/fotos/{r['miniatura'] or r['arquivo']}"}
            for r in rows]


def obter_produto(conn, slug, incluir_inativos=False, admin=False):
    sql = _SELECT_PRODUTO + " WHERE p.slug = ?"
    if not incluir_inativos:
        sql += " AND p.ativo = 1"
    row = conn.execute(sql, (slug,)).fetchone()
    if not row:
        raise NaoEncontrado("Produto não encontrado.")
    produto = _produto(row, admin)
    produto["variacoes"] = _variacoes(conn, row["id"], incluir_inativas=admin)
    if not admin:
        for v in produto["variacoes"]:
            del v["sku"], v["ativo"]
    produto["fotos"] = _fotos(conn, row["id"])
    relacionados = conn.execute(
        _SELECT_PRODUTO + " WHERE c.slug = ? AND p.slug != ? AND p.ativo = 1 ORDER BY p.destaque DESC, RANDOM() LIMIT 4",
        (row["categoria_slug"], slug),
    ).fetchall()
    produto["relacionados"] = [_produto(r, com_descricao=False) for r in relacionados]
    return produto


def cor_e_icone(conn, slug):
    row = conn.execute(
        """SELECT p.nome, p.icone, c.cor FROM produtos p JOIN categorias c ON c.id = p.categoria_id
           WHERE p.slug = ? AND p.ativo = 1""",
        (slug,),
    ).fetchone()
    if not row:
        raise NaoEncontrado("Produto não encontrado.")
    return dict(row)


def _sincronizar_estoque(conn, produto_id):
    """Produto com variações: o estoque do produto é a soma do estoque das variações ativas.

    Se todas as variações foram desativadas, o estoque zera — o estoque antigo do produto não volta a ser vendido.
    """
    conn.execute(
        """UPDATE produtos SET estoque = (
               SELECT COALESCE(SUM(estoque), 0) FROM variacoes WHERE produto_id = ? AND ativo = 1)
           WHERE id = ? AND EXISTS (SELECT 1 FROM variacoes WHERE produto_id = ?)""",
        (produto_id, produto_id, produto_id),
    )


# ---------------------------------------------------------------- carrinho

def _normalizar_itens(itens):
    """Agrupa os itens por (slug, variação) e valida as quantidades."""
    if not isinstance(itens, list) or not itens:
        raise ErroValidacao({"itens": "O carrinho está vazio."})
    if len(itens) > 50:
        raise ErroValidacao({"itens": "Carrinho com itens demais."})
    quantidades = {}
    for item in itens:
        if not isinstance(item, dict):
            raise ErroValidacao({"itens": "Item inválido."})
        slug = str(item.get("slug") or "")
        variacao = item.get("variacao")
        try:
            qtd = int(item.get("quantidade", 1))
            variacao = int(variacao) if variacao not in (None, "") else None
        except (TypeError, ValueError, OverflowError):  # OverflowError: 1e400 vira float infinito
            raise ErroValidacao({"itens": "Item inválido."})
        if not slug or qtd < 1 or (variacao is not None and not 0 < variacao <= 2 ** 62):
            raise ErroValidacao({"itens": "Item inválido."})
        chave = (slug, variacao)
        quantidades[chave] = quantidades.get(chave, 0) + qtd
    if any(q > config.QTD_MAX_POR_ITEM for q in quantidades.values()):
        raise ErroValidacao({"itens": f"Máximo de {config.QTD_MAX_POR_ITEM} unidades por produto."})
    return quantidades


def chave_item(slug, variacao_id):
    return f"{slug}:{variacao_id or ''}"


def _linhas(conn, quantidades):
    slugs = sorted({slug for slug, _ in quantidades})
    produtos = {
        r["slug"]: r for r in conn.execute(
            f"""SELECT id, slug, nome, icone, foto, preco_centavos, custo_centavos, estoque,
                       (SELECT COUNT(*) FROM variacoes v WHERE v.produto_id = produtos.id AND v.ativo = 1) AS n_variacoes
                FROM produtos WHERE ativo = 1 AND slug IN ({",".join("?" * len(slugs))})""",
            slugs,
        ).fetchall()
    }
    ids_var = sorted({v for _, v in quantidades if v})
    variacoes = {}
    if ids_var:
        variacoes = {
            r["id"]: r for r in conn.execute(
                f"SELECT id, produto_id, nome, preco_centavos, estoque FROM variacoes WHERE ativo = 1 AND id IN ({','.join('?' * len(ids_var))})",
                ids_var,
            ).fetchall()
        }
    linhas = []
    for (slug, vid), qtd in quantidades.items():
        r = produtos.get(slug)
        base = {"slug": slug, "variacao_id": vid, "chave": chave_item(slug, vid), "quantidade": qtd}
        if r is None:
            linhas.append({**base, "disponivel": False, "erro": "Produto indisponível."})
            continue
        v = variacoes.get(vid) if vid else None
        if vid and (v is None or v["produto_id"] != r["id"]):
            linhas.append({**base, "nome": r["nome"], "disponivel": False, "erro": "Opção indisponível."})
            continue
        if r["n_variacoes"] and not v:
            linhas.append({**base, "nome": r["nome"], "disponivel": False, "erro": "Escolha uma opção do produto."})
            continue
        preco = v["preco_centavos"] if v and v["preco_centavos"] is not None else r["preco_centavos"]
        estoque = v["estoque"] if v else r["estoque"]
        linha = {
            **base,
            "produto_id": r["id"],
            "nome": r["nome"],
            "variacao_nome": v["nome"] if v else "",
            "icone": r["icone"],
            "imagem": url_imagem(slug, r["foto"]),
            "preco_unit_centavos": preco,
            "custo_unit_centavos": r["custo_centavos"],
            "estoque": estoque,
            "total_centavos": preco * qtd,
            "disponivel": qtd <= estoque,
        }
        if not linha["disponivel"]:
            linha["erro"] = "Sem estoque." if estoque == 0 else f"Restam apenas {estoque} unidade(s)."
        linhas.append(linha)
    return linhas


def parcelas_maximas(total_centavos):
    return max(1, min(config.PARCELAS_MAX, total_centavos // config.PARCELA_MINIMA))


def cotar_carrinho(conn, itens, cep=None, pagamento="pix"):
    """Recalcula o carrinho com os preços do banco — o navegador nunca define preço."""
    expirar_pendentes(conn)
    return _cotar(conn, itens, cep, pagamento)


def _cotar(conn, itens, cep, pagamento):
    quantidades = _normalizar_itens(itens)
    if pagamento not in FORMAS_PAGAMENTO:
        pagamento = "pix"
    linhas = _linhas(conn, quantidades)
    validas = [l for l in linhas if l["disponivel"]]
    subtotal = sum(l["total_centavos"] for l in validas)
    desconto = subtotal * config.DESCONTO_PIX_PCT // 100 if pagamento == "pix" else 0
    cotacao_frete = frete.cotar(cep_digitos(cep), subtotal) if cep else None
    valor_frete = cotacao_frete["valor_centavos"] if cotacao_frete else 0
    total = subtotal - desconto + valor_frete
    for l in linhas:  # o custo é informação interna
        l.pop("custo_unit_centavos", None)
    return {
        "itens": linhas,
        "valido": len(validas) == len(linhas),
        "pagamento": pagamento,
        "subtotal_centavos": subtotal,
        "desconto_centavos": desconto,
        "frete": cotacao_frete,
        "total_centavos": total,
        "parcelas_max": parcelas_maximas(total) if pagamento == "cartao" else 1,
        "falta_para_frete_gratis": max(0, config.FRETE_GRATIS_A_PARTIR - subtotal),
    }


# ---------------------------------------------------------------- pedidos

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
                         cep=cliente["cep"], pagamento=cliente["pagamento"])
        if not cotacao["valido"]:
            problemas = {l["chave"]: l["erro"] for l in cotacao["itens"] if not l["disponivel"]}
            raise ErroValidacao({"itens": problemas}, "Alguns itens do carrinho não estão mais disponíveis.")
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
                   pagamento, parcelas, subtotal_centavos, desconto_centavos, frete_centavos, total_centavos)
               VALUES (?, 'aguardando_pagamento', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                codigo, cliente["nome"], cliente["email"], cliente["cpf"], cliente["telefone"],
                cliente["cep"], cliente["endereco"], cliente["numero"], cliente["complemento"],
                cliente["bairro"], cliente["cidade"], cliente["uf"], f["zona_nome"], f["prazo_dias"],
                cliente["pagamento"], cliente["parcelas"], cotacao["subtotal_centavos"],
                cotacao["desconto_centavos"], f["valor_centavos"], cotacao["total_centavos"],
            ),
        )
        pedido_id = cur.lastrowid
        conn.executemany(
            """INSERT INTO itens_pedido (pedido_id, produto_id, variacao_id, nome, variacao_nome,
                   preco_unit_centavos, custo_unit_centavos, quantidade) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [(pedido_id, l["produto_id"], l["variacao_id"], l["nome"], l["variacao_nome"], l["preco_unit_centavos"],
              custos.get(l["chave"]), l["quantidade"]) for l in cotacao["itens"]],
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return codigo


def _itens_dos_pedidos(conn, pedido_ids, admin=False):
    """Itens de vários pedidos numa consulta só: {pedido_id: [itens]}."""
    itens = {pid: [] for pid in pedido_ids}
    if not itens:
        return itens
    rows = conn.execute(
        f"""SELECT i.pedido_id, i.nome, i.variacao_nome, i.preco_unit_centavos, i.custo_unit_centavos, i.quantidade,
                   p.slug, p.foto
            FROM itens_pedido i JOIN produtos p ON p.id = i.produto_id
            WHERE i.pedido_id IN ({",".join("?" * len(itens))}) ORDER BY i.id""",
        list(itens),
    ).fetchall()
    for r in rows:
        item = dict(r, imagem=url_imagem(r["slug"], r["foto"]))
        del item["foto"], item["pedido_id"]
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
    """Receita dos produtos (já com o desconto) menos o custo deles. None se faltar o custo de algum item.

    O frete cobrado é tratado como repasse e fica fora da conta.
    """
    if any(i["custo_unit_centavos"] is None for i in resumo["itens"]):
        return None
    custo = sum(i["custo_unit_centavos"] * i["quantidade"] for i in resumo["itens"])
    return resumo["subtotal_centavos"] - resumo["desconto_centavos"] - custo


def obter_pedido_publico(conn, codigo):
    """Visão do cliente pelo código: sem CPF, e-mail, telefone nem endereço completo."""
    row = conn.execute("SELECT * FROM pedidos WHERE codigo = ?", (str(codigo).upper(),)).fetchone()
    if not row:
        raise NaoEncontrado("Pedido não encontrado.")
    resumo = _resumo_pedido(row, _itens_dos_pedidos(conn, [row["id"]])[row["id"]])
    resumo["primeiro_nome"] = row["cliente_nome"].split()[0]
    resumo["destino"] = f"{row['cidade']} - {row['uf']}"
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
    return pedidos


def resumo_vendas(conn):
    """Totais de todos os pedidos não cancelados. O lucro só soma pedidos em que todo item tem custo."""
    expirar_pendentes(conn)
    totais = conn.execute(
        """SELECT COUNT(*) AS pedidos,
                  COALESCE(SUM(p.total_centavos), 0) AS faturamento,
                  COALESCE(SUM(CASE WHEN COALESCE(i.sem_custo, 0) = 0
                               THEN p.subtotal_centavos - p.desconto_centavos - COALESCE(i.custo, 0) END), 0) AS lucro,
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


def _devolver_estoque(conn, pedido_id):
    itens = conn.execute(
        "SELECT produto_id, variacao_id, quantidade FROM itens_pedido WHERE pedido_id = ?", (pedido_id,)
    ).fetchall()
    for item in itens:
        if item["variacao_id"]:
            conn.execute("UPDATE variacoes SET estoque = estoque + ? WHERE id = ?",
                         (item["quantidade"], item["variacao_id"]))
        else:
            conn.execute("UPDATE produtos SET estoque = estoque + ? WHERE id = ?",
                         (item["quantidade"], item["produto_id"]))
    # também cobre pedidos antigos, sem variação, de produtos que depois ganharam variações
    for produto_id in {i["produto_id"] for i in itens}:
        _sincronizar_estoque(conn, produto_id)


def atualizar_status(conn, codigo, novo_status, somente_se=None):
    """Muda o status respeitando TRANSICOES. Com somente_se, só age se o pedido ainda estiver nesse status."""
    if not isinstance(novo_status, str) or novo_status not in STATUS_PEDIDO:
        raise ErroValidacao({"status": "Status inválido."})
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT id, status FROM pedidos WHERE codigo = ?", (codigo,)).fetchone()
        if not row:
            raise NaoEncontrado("Pedido não encontrado.")
        atual = row["status"]
        if atual != novo_status and (somente_se is None or atual == somente_se):
            if novo_status not in TRANSICOES[atual]:
                raise ErroValidacao({"status": f"Um pedido “{STATUS_PEDIDO[atual]}” não pode passar para "
                                               f"“{STATUS_PEDIDO[novo_status]}”."})
            if novo_status == "cancelado":
                _devolver_estoque(conn, row["id"])
            conn.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, row["id"]))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def expirar_pendentes(conn):
    """Cancela pedidos não pagos dentro do prazo de reserva, devolvendo as unidades ao estoque.

    Sem isso, pedidos abandonados (ou feitos de má-fé) prenderiam o estoque para sempre.
    """
    vencidos = conn.execute(
        "SELECT codigo FROM pedidos WHERE status = 'aguardando_pagamento' AND criado_em < datetime('now', ?)",
        (f"-{int(config.PRAZO_RESERVA_HORAS)} hours",),
    ).fetchall()
    for row in vencidos:
        atualizar_status(conn, row["codigo"], "cancelado", somente_se="aguardando_pagamento")


# ---------------------------------------------------------------- administração de produtos

def _inteiro_ou_nulo(valor, erros, campo, aceita_nulo):
    if valor in (None, "") and aceita_nulo:
        return None
    if isinstance(valor, bool) or not isinstance(valor, int) or not 0 <= valor <= INTEIRO_MAX:
        erros[campo] = "Use um número inteiro entre 0 e 1.000.000.000."
        return None
    return valor


def atualizar_produto(conn, slug, dados):
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    row = conn.execute(_SELECT_PRODUTO + " WHERE p.slug = ?", (slug,)).fetchone()
    if not row:
        raise NaoEncontrado("Produto não encontrado.")
    sets, params, erros = [], [], {}
    for campo, aceita_nulo in (("preco_centavos", False), ("preco_de_centavos", True),
                               ("custo_centavos", True), ("estoque", False)):
        if campo in dados:
            if campo == "estoque" and row["n_variacoes_total"]:
                continue  # controlado pelas variações, mesmo que todas estejam desativadas
            valor = _inteiro_ou_nulo(dados[campo], erros, campo, aceita_nulo)
            if campo == "preco_centavos" and valor == 0:
                erros[campo] = "Informe o preço."
            if campo not in erros:
                sets.append(f"{campo} = ?")
                params.append(valor)
    for campo in ("ativo", "destaque"):
        if campo in dados:
            sets.append(f"{campo} = ?")
            params.append(1 if dados[campo] else 0)
    for campo in ("nome", "descricao", "icone"):
        if campo in dados:
            valor = str(dados[campo] or "").strip()
            if campo == "nome" and not 3 <= len(valor) <= 120:
                erros[campo] = "O nome deve ter entre 3 e 120 caracteres."
                continue
            sets.append(f"{campo} = ?")
            params.append(valor[:8] if campo == "icone" else valor[:2000])
    if "categoria" in dados:
        cat = conn.execute("SELECT id FROM categorias WHERE slug = ?", (str(dados["categoria"]),)).fetchone()
        if cat:
            sets.append("categoria_id = ?")
            params.append(cat["id"])
        else:
            erros["categoria"] = "Categoria inválida."
    if erros:
        raise ErroValidacao(erros)
    if not sets:
        raise ErroValidacao({"geral": "Nada para atualizar."})
    conn.execute(f"UPDATE produtos SET {', '.join(sets)} WHERE id = ?", (*params, row["id"]))
    atualizar_busca(conn, row["id"])
    return obter_produto(conn, slug, incluir_inativos=True, admin=True)


def criar_produto(conn, dados):
    """Cadastro pelo painel. O endereço (slug) é gerado a partir do nome."""
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    erros = {}
    nome = str(dados.get("nome") or "").strip()
    if not 3 <= len(nome) <= 120:
        erros["nome"] = "O nome deve ter entre 3 e 120 caracteres."
    cat = conn.execute("SELECT id FROM categorias WHERE slug = ?", (str(dados.get("categoria") or ""),)).fetchone()
    if not cat:
        erros["categoria"] = "Escolha a categoria."
    numeros = {
        campo: _inteiro_ou_nulo(dados.get(campo), erros, campo, aceita_nulo)
        for campo, aceita_nulo in (("preco_centavos", False), ("preco_de_centavos", True),
                                   ("custo_centavos", True), ("estoque", False))
    }
    if numeros["preco_centavos"] == 0:
        erros["preco_centavos"] = "Informe o preço."
    if erros:
        raise ErroValidacao(erros)

    base = gerar_slug(nome)
    slug, n = base, 2
    while conn.execute("SELECT 1 FROM produtos WHERE slug = ?", (slug,)).fetchone():
        slug, n = f"{base}-{n}", n + 1
    cur = conn.execute(
        """INSERT INTO produtos (slug, nome, descricao, categoria_id, preco_centavos, preco_de_centavos,
               custo_centavos, estoque, icone, destaque, ativo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (slug, nome, str(dados.get("descricao") or "").strip()[:2000], cat["id"], numeros["preco_centavos"],
         numeros["preco_de_centavos"], numeros["custo_centavos"], numeros["estoque"],
         str(dados.get("icone") or "📦")[:8], 1 if dados.get("destaque") else 0,
         0 if dados.get("ativo") is False else 1),
    )
    atualizar_busca(conn, cur.lastrowid)
    return obter_produto(conn, slug, incluir_inativos=True, admin=True)


def _id_produto(conn, slug):
    row = conn.execute("SELECT id FROM produtos WHERE slug = ?", (slug,)).fetchone()
    if not row:
        raise NaoEncontrado("Produto não encontrado.")
    return row["id"]


def salvar_variacoes(conn, slug, lista):
    """Substitui as variações do produto pela lista enviada.

    Variações que saem da lista são desativadas (não apagadas), porque pedidos antigos apontam para elas.
    """
    if not isinstance(lista, list) or len(lista) > 60:
        raise ErroValidacao({"variacoes": "Lista de variações inválida."})
    produto_id = _id_produto(conn, slug)
    existentes = {v["id"] for v in _variacoes(conn, produto_id, incluir_inativas=True)}
    erros, limpas, nomes = {}, [], set()
    for i, v in enumerate(lista):
        if not isinstance(v, dict):
            raise ErroValidacao({"variacoes": "Variação inválida."})
        nome = str(v.get("nome") or "").strip()[:80]
        if not nome:
            erros[f"variacao_{i}"] = "Dê um nome à opção (ex.: Preto, 220 V)."
        elif normaliza(nome) in nomes:
            erros[f"variacao_{i}"] = f"A opção “{nome}” está repetida."
        nomes.add(normaliza(nome))
        e = {}
        preco = _inteiro_ou_nulo(v.get("preco_centavos"), e, "preco", True)
        estoque = _inteiro_ou_nulo(v.get("estoque", 0), e, "estoque", False)
        if e:
            erros[f"variacao_{i}"] = "Preço e estoque devem ser números inteiros maiores ou iguais a zero."
        elif preco == 0:
            erros[f"variacao_{i}"] = "Deixe o preço da opção vazio para usar o do produto, ou informe um valor."
        vid = v.get("id")
        if vid is not None and (isinstance(vid, bool) or not isinstance(vid, int) or vid not in existentes):
            erros[f"variacao_{i}"] = "Variação de outro produto."
        limpas.append((vid, nome, str(v.get("sku") or "").strip()[:60], preco, estoque or 0,
                       0 if v.get("ativo") is False else 1, i))
    if erros:
        raise ErroValidacao(erros, "Revise as variações.")

    conn.execute("BEGIN IMMEDIATE")
    try:
        mantidas = set()
        for vid, nome, sku, preco, estoque, ativo, ordem in limpas:
            if vid:
                conn.execute(
                    "UPDATE variacoes SET nome = ?, sku = ?, preco_centavos = ?, estoque = ?, ativo = ?, ordem = ? WHERE id = ?",
                    (nome, sku, preco, estoque, ativo, ordem, vid),
                )
                mantidas.add(vid)
            else:
                conn.execute(
                    "INSERT INTO variacoes (produto_id, nome, sku, preco_centavos, estoque, ativo, ordem) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (produto_id, nome, sku, preco, estoque, ativo, ordem),
                )
        for vid in existentes - mantidas:
            conn.execute("UPDATE variacoes SET ativo = 0 WHERE id = ?", (vid,))
        _sincronizar_estoque(conn, produto_id)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return obter_produto(conn, slug, incluir_inativos=True, admin=True)


# ---------------------------------------------------------------- galeria de fotos

def _atualizar_capa(conn, produto_id):
    primeira = conn.execute(
        "SELECT arquivo FROM fotos_produto WHERE produto_id = ? ORDER BY ordem, id LIMIT 1", (produto_id,)
    ).fetchone()
    conn.execute("UPDATE produtos SET foto = ? WHERE id = ?", (primeira["arquivo"] if primeira else "", produto_id))


def adicionar_foto(conn, slug, arquivo, miniatura=""):
    produto_id = _id_produto(conn, slug)
    # contagem e inserção na mesma transação: dois envios simultâneos não passam do limite
    conn.execute("BEGIN IMMEDIATE")
    try:
        total = conn.execute("SELECT COUNT(*) FROM fotos_produto WHERE produto_id = ?", (produto_id,)).fetchone()[0]
        if total >= config.FOTOS_POR_PRODUTO:
            raise ErroValidacao({"foto": f"Máximo de {config.FOTOS_POR_PRODUTO} fotos por produto."})
        ordem = conn.execute("SELECT COALESCE(MAX(ordem), -1) + 1 FROM fotos_produto WHERE produto_id = ?",
                             (produto_id,)).fetchone()[0]
        conn.execute("INSERT INTO fotos_produto (produto_id, arquivo, miniatura, ordem) VALUES (?, ?, ?, ?)",
                     (produto_id, arquivo, miniatura, ordem))
        _atualizar_capa(conn, produto_id)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return obter_produto(conn, slug, incluir_inativos=True, admin=True)


def remover_foto(conn, slug, foto_id):
    """Remove a foto do produto e devolve os nomes dos arquivos (foto e miniatura) para apagar do disco."""
    produto_id = _id_produto(conn, slug)
    row = conn.execute("SELECT arquivo, miniatura FROM fotos_produto WHERE id = ? AND produto_id = ?",
                       (foto_id, produto_id)).fetchone()
    if not row:
        raise NaoEncontrado("Foto não encontrada.")
    conn.execute("DELETE FROM fotos_produto WHERE id = ?", (foto_id,))
    _atualizar_capa(conn, produto_id)
    arquivos = [a for a in (row["arquivo"], row["miniatura"]) if a]
    return arquivos, obter_produto(conn, slug, incluir_inativos=True, admin=True)


def definir_capa(conn, slug, foto_id):
    produto_id = _id_produto(conn, slug)
    if not conn.execute("SELECT 1 FROM fotos_produto WHERE id = ? AND produto_id = ?", (foto_id, produto_id)).fetchone():
        raise NaoEncontrado("Foto não encontrada.")
    minimo = conn.execute("SELECT MIN(ordem) FROM fotos_produto WHERE produto_id = ?", (produto_id,)).fetchone()[0]
    conn.execute("UPDATE fotos_produto SET ordem = ? WHERE id = ?", (minimo - 1, foto_id))
    _atualizar_capa(conn, produto_id)
    return obter_produto(conn, slug, incluir_inativos=True, admin=True)
