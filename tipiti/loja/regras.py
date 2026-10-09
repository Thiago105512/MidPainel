"""Regras de negócio: catálogo, carrinho, pedidos e validações."""

import re
import secrets

from . import config, frete
from .db import normaliza


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

_ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


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

def _produto(row):
    return {
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
        "imagem": f"/img/produto/{row['slug']}.svg",
        "categoria": {"slug": row["categoria_slug"], "nome": row["categoria_nome"]},
    }


_SELECT_PRODUTO = """
    SELECT p.*, c.slug AS categoria_slug, c.nome AS categoria_nome, c.cor AS categoria_cor
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
                    limite=None, incluir_inativos=False):
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
        where.append(
            "normaliza(p.nome || ' ' || p.descricao || ' ' || c.nome) LIKE ? ESCAPE '\\'"
        )
        params.append(f"%{termo}%")
    sql = _SELECT_PRODUTO
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY " + ORDENACOES.get(ordem, ORDENACOES["relevancia"])
    if limite:
        sql += " LIMIT ?"
        params.append(int(limite))
    return [_produto(r) for r in conn.execute(sql, params).fetchall()]


def obter_produto(conn, slug, incluir_inativos=False):
    sql = _SELECT_PRODUTO + " WHERE p.slug = ?"
    if not incluir_inativos:
        sql += " AND p.ativo = 1"
    row = conn.execute(sql, (slug,)).fetchone()
    if not row:
        raise NaoEncontrado("Produto não encontrado.")
    produto = _produto(row)
    relacionados = conn.execute(
        _SELECT_PRODUTO + " WHERE c.slug = ? AND p.slug != ? AND p.ativo = 1 ORDER BY p.destaque DESC, RANDOM() LIMIT 4",
        (row["categoria_slug"], slug),
    ).fetchall()
    produto["relacionados"] = [_produto(r) for r in relacionados]
    return produto


def cor_e_icone(conn, slug):
    row = conn.execute(
        "SELECT p.nome, p.icone, c.cor FROM produtos p JOIN categorias c ON c.id = p.categoria_id WHERE p.slug = ?",
        (slug,),
    ).fetchone()
    if not row:
        raise NaoEncontrado("Produto não encontrado.")
    return dict(row)


# ---------------------------------------------------------------- carrinho

def _normalizar_itens(itens):
    if not isinstance(itens, list) or not itens:
        raise ErroValidacao({"itens": "O carrinho está vazio."})
    if len(itens) > 50:
        raise ErroValidacao({"itens": "Carrinho com itens demais."})
    quantidades = {}
    for item in itens:
        if not isinstance(item, dict):
            raise ErroValidacao({"itens": "Item inválido."})
        slug = str(item.get("slug") or "")
        try:
            qtd = int(item.get("quantidade", 1))
        except (TypeError, ValueError):
            raise ErroValidacao({"itens": "Quantidade inválida."})
        if not slug or qtd < 1:
            raise ErroValidacao({"itens": "Item inválido."})
        quantidades[slug] = quantidades.get(slug, 0) + qtd
    for slug, qtd in quantidades.items():
        if qtd > config.QTD_MAX_POR_ITEM:
            raise ErroValidacao({"itens": f"Máximo de {config.QTD_MAX_POR_ITEM} unidades por produto."})
    return quantidades


def _linhas(conn, quantidades):
    marcadores = ",".join("?" * len(quantidades))
    rows = conn.execute(
        f"SELECT id, slug, nome, icone, preco_centavos, estoque FROM produtos WHERE ativo = 1 AND slug IN ({marcadores})",
        list(quantidades),
    ).fetchall()
    por_slug = {r["slug"]: r for r in rows}
    linhas = []
    for slug, qtd in quantidades.items():
        r = por_slug.get(slug)
        if r is None:
            linhas.append({"slug": slug, "disponivel": False, "erro": "Produto indisponível."})
            continue
        linha = {
            "produto_id": r["id"],
            "slug": slug,
            "nome": r["nome"],
            "icone": r["icone"],
            "imagem": f"/img/produto/{slug}.svg",
            "preco_unit_centavos": r["preco_centavos"],
            "quantidade": qtd,
            "estoque": r["estoque"],
            "total_centavos": r["preco_centavos"] * qtd,
            "disponivel": qtd <= r["estoque"],
        }
        if not linha["disponivel"]:
            linha["erro"] = "Sem estoque." if r["estoque"] == 0 else f"Restam apenas {r['estoque']} unidade(s)."
        linhas.append(linha)
    return linhas


def parcelas_maximas(total_centavos):
    return max(1, min(config.PARCELAS_MAX, total_centavos // config.PARCELA_MINIMA))


def cotar_carrinho(conn, itens, cep=None, pagamento="pix"):
    """Recalcula o carrinho com os preços do banco — o navegador nunca define preço."""
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
        codigo = "TPT-" + "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(8))
        if not conn.execute("SELECT 1 FROM pedidos WHERE codigo = ?", (codigo,)).fetchone():
            return codigo


def criar_pedido(conn, dados):
    cliente = _validar_cliente(dados)
    quantidades = _normalizar_itens(dados.get("itens"))

    conn.execute("BEGIN IMMEDIATE")
    try:
        cotacao = cotar_carrinho(conn, [{"slug": s, "quantidade": q} for s, q in quantidades.items()],
                                 cep=cliente["cep"], pagamento=cliente["pagamento"])
        if not cotacao["valido"]:
            problemas = {l["slug"]: l["erro"] for l in cotacao["itens"] if not l["disponivel"]}
            raise ErroValidacao({"itens": problemas}, "Alguns itens do carrinho não estão mais disponíveis.")
        if not 1 <= cliente["parcelas"] <= cotacao["parcelas_max"]:
            raise ErroValidacao({"parcelas": f"Parcelamento em até {cotacao['parcelas_max']}x."})

        for linha in cotacao["itens"]:
            cur = conn.execute(
                "UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?",
                (linha["quantidade"], linha["produto_id"], linha["quantidade"]),
            )
            if cur.rowcount != 1:
                raise ErroValidacao({"itens": {linha["slug"]: "Sem estoque."}}, "Estoque insuficiente.")

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
            "INSERT INTO itens_pedido (pedido_id, produto_id, nome, preco_unit_centavos, quantidade) VALUES (?, ?, ?, ?, ?)",
            [(pedido_id, l["produto_id"], l["nome"], l["preco_unit_centavos"], l["quantidade"]) for l in cotacao["itens"]],
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return codigo


def _itens_do_pedido(conn, pedido_id):
    rows = conn.execute(
        """SELECT i.nome, i.preco_unit_centavos, i.quantidade, p.slug
           FROM itens_pedido i JOIN produtos p ON p.id = i.produto_id
           WHERE i.pedido_id = ? ORDER BY i.id""",
        (pedido_id,),
    ).fetchall()
    return [dict(r, imagem=f"/img/produto/{r['slug']}.svg") for r in rows]


def _resumo_pedido(conn, row):
    return {
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
        "itens": _itens_do_pedido(conn, row["id"]),
    }


def obter_pedido_publico(conn, codigo):
    """Visão do cliente pelo código: sem CPF, e-mail, telefone nem endereço completo."""
    row = conn.execute("SELECT * FROM pedidos WHERE codigo = ?", (str(codigo).upper(),)).fetchone()
    if not row:
        raise NaoEncontrado("Pedido não encontrado.")
    resumo = _resumo_pedido(conn, row)
    resumo["primeiro_nome"] = row["cliente_nome"].split()[0]
    resumo["destino"] = f"{row['cidade']} - {row['uf']}"
    return resumo


def listar_pedidos(conn, status=None):
    sql, params = "SELECT * FROM pedidos", []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY id DESC LIMIT 500"
    pedidos = []
    for row in conn.execute(sql, params).fetchall():
        resumo = _resumo_pedido(conn, row)
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


def atualizar_status(conn, codigo, novo_status):
    if novo_status not in STATUS_PEDIDO:
        raise ErroValidacao({"status": "Status inválido."})
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT id, status FROM pedidos WHERE codigo = ?", (codigo,)).fetchone()
        if not row:
            raise NaoEncontrado("Pedido não encontrado.")
        if row["status"] == "cancelado" and novo_status != "cancelado":
            raise ErroValidacao({"status": "Pedido cancelado não pode ser reaberto."})
        if novo_status == "cancelado" and row["status"] != "cancelado":
            # devolve as unidades ao estoque
            conn.execute(
                """UPDATE produtos SET estoque = estoque + (
                       SELECT SUM(quantidade) FROM itens_pedido WHERE pedido_id = ? AND produto_id = produtos.id)
                   WHERE id IN (SELECT produto_id FROM itens_pedido WHERE pedido_id = ?)""",
                (row["id"], row["id"]),
            )
        conn.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, row["id"]))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


# ---------------------------------------------------------------- administração de produtos

_CAMPOS_INTEIROS = ("preco_centavos", "preco_de_centavos", "estoque")
_CAMPOS_BOOLEANOS = ("ativo", "destaque")
_CAMPOS_TEXTO = ("nome", "descricao")


def atualizar_produto(conn, slug, dados):
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    sets, params, erros = [], [], {}
    for campo in _CAMPOS_INTEIROS:
        if campo in dados:
            valor = dados[campo]
            if campo == "preco_de_centavos" and valor in (None, ""):
                sets.append(f"{campo} = NULL")
                continue
            if isinstance(valor, bool) or not isinstance(valor, int) or valor < 0:
                erros[campo] = "Use um número inteiro maior ou igual a zero."
                continue
            sets.append(f"{campo} = ?")
            params.append(valor)
    for campo in _CAMPOS_BOOLEANOS:
        if campo in dados:
            sets.append(f"{campo} = ?")
            params.append(1 if dados[campo] else 0)
    for campo in _CAMPOS_TEXTO:
        if campo in dados:
            valor = str(dados[campo] or "").strip()
            if campo == "nome" and not valor:
                erros[campo] = "O nome não pode ficar vazio."
                continue
            sets.append(f"{campo} = ?")
            params.append(valor[:2000])
    if erros:
        raise ErroValidacao(erros)
    if not sets:
        raise ErroValidacao({"geral": "Nada para atualizar."})
    cur = conn.execute(f"UPDATE produtos SET {', '.join(sets)} WHERE slug = ?", (*params, slug))
    if cur.rowcount == 0:
        raise NaoEncontrado("Produto não encontrado.")
    return obter_produto(conn, slug, incluir_inativos=True)
