"""Carrinho: itens, preços recalculados no servidor, frete, desconto no Pix e parcelas."""

from . import config, frete
from .catalogo import url_imagem
from .reservas import expirar_pendentes
from .validacao import ErroValidacao, cep_digitos


FORMAS_PAGAMENTO = {"pix": "Pix", "cartao": "Cartão de crédito", "boleto": "Boleto"}


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
