"""Carrinho: itens, preços recalculados no servidor (com ofertas), cupom, frete, desconto no Pix e parcelas."""

from . import config, cupons, frete, prevenda
from .imagens import url_imagem
from .promocoes import SQL_PROMO_ATIVA, preco_ancora, preco_com_desconto
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
            f"""SELECT id, slug, nome, icone, foto, preco_centavos, preco_de_centavos, custo_centavos, estoque,
                       {SQL_PROMO_ATIVA} AS promo_ativa, {prevenda.SQL_PREVENDA_ATIVA} AS prevenda_ativa,
                       (SELECT COUNT(*) FROM variacoes v WHERE v.produto_id = p.id AND v.ativo = 1) AS n_variacoes
                FROM produtos p WHERE ativo = 1 AND slug IN ({",".join("?" * len(slugs))})""",
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
        base = {"slug": slug, "variacao_id": vid, "chave": chave_item(slug, vid), "quantidade": qtd,
                "prevenda_chegada": r["prevenda_ativa"] if r is not None else None}
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
        if v and v["preco_centavos"] is not None:  # preço próprio da opção: o preço "de" do produto não vale para ela
            preco_normal, preco_de = v["preco_centavos"], None
        else:
            preco_normal, preco_de = r["preco_centavos"], r["preco_de_centavos"]
        preco = preco_com_desconto(preco_normal, r["promo_ativa"])
        estoque = v["estoque"] if v else r["estoque"]
        linha = {
            **base,
            "produto_id": r["id"],
            "nome": r["nome"],
            "variacao_nome": v["nome"] if v else "",
            "icone": r["icone"],
            "imagem": url_imagem(slug, r["foto"]),
            "preco_unit_centavos": preco,
            "preco_ancora_unit_centavos": preco_ancora(preco_normal, preco_de, r["promo_ativa"]),
            "custo_unit_centavos": r["custo_centavos"],
            "estoque": estoque,
            "total_centavos": preco * qtd,
            "disponivel": qtd <= estoque,
        }
        if not linha["disponivel"] and r["prevenda_ativa"]:  # na pré-venda, o estoque são as vagas do lote
            linha["erro"] = "Vagas da pré-venda esgotadas." if estoque == 0 else f"Restam apenas {estoque} vaga(s)."
        elif not linha["disponivel"]:
            linha["erro"] = "Sem estoque." if estoque == 0 else f"Restam apenas {estoque} unidade(s)."
        linhas.append(linha)
    return linhas


def parcelas_maximas(total_centavos):
    return max(1, min(config.PARCELAS_MAX, total_centavos // config.PARCELA_MINIMA))


def cotar_carrinho(conn, itens, cep=None, pagamento="pix", cupom=None, cpf=None, revendedora=None):
    """Recalcula o carrinho com os preços do banco — o navegador nunca define preço."""
    expirar_pendentes(conn)
    return _extras_da_cotacao(conn, _cotar(conn, itens, cep, pagamento, cupom, cpf), revendedora)


def _extras_da_cotacao(conn, cotacao, revendedora=None):
    """Próximo barco no frete (a partir da previsão de envio da pré-venda, se houver) e a revendedora."""
    from . import revendedoras, viagens
    viagens.anexar_ao_frete(conn, cotacao["frete"], cotacao.get("previsao_envio"))
    return revendedoras.anexar_a_cotacao(conn, cotacao, revendedora)


def _cotar(conn, itens, cep, pagamento, cupom=None, cpf=None):
    """Ordem do cálculo: subtotal (preços com oferta) → cupom → Pix sobre o que sobrou → frete.

    total = subtotal − desconto do cupom − desconto do Pix + frete; as parcelas usam esse total.
    """
    quantidades = _normalizar_itens(itens)
    if pagamento not in FORMAS_PAGAMENTO:
        pagamento = "pix"
    linhas = _linhas(conn, quantidades)
    validas = [l for l in linhas if l["disponivel"]]
    subtotal = sum(l["total_centavos"] for l in validas)

    if cupom is None or isinstance(cupom, str):
        achado, cupom_erro = cupons.avaliar(conn, cupom, subtotal, cpf)
    else:
        achado, cupom_erro = None, "Cupom inválido. Confira o código."
    desconto_cupom = cupons.desconto(achado, subtotal) if achado else 0
    frete_gratis_cupom = bool(achado) and achado["tipo"] == "frete"

    base_pix = subtotal - desconto_cupom
    desconto = base_pix * config.DESCONTO_PIX_PCT // 100 if pagamento == "pix" else 0
    cotacao_frete = frete.cotar(cep_digitos(cep), subtotal) if cep else None
    if cotacao_frete and frete_gratis_cupom:
        cotacao_frete = {**cotacao_frete, "valor_centavos": 0, "gratis": True}
    # pré-venda: o pedido sai na chegada do lote + manuseio, e o prazo do frete conta a partir daí
    previsao_envio = prevenda.previsao_envio(l["prevenda_chegada"] for l in validas)
    if cotacao_frete and previsao_envio:
        cotacao_frete = {**cotacao_frete, "prazo_dias": cotacao_frete["prazo_dias"] - config.PRAZO_MANUSEIO_DIAS}
    valor_frete = cotacao_frete["valor_centavos"] if cotacao_frete else 0
    total = subtotal - desconto_cupom - desconto + valor_frete
    economia_ofertas = sum((l["preco_ancora_unit_centavos"] - l["preco_unit_centavos"]) * l["quantidade"]
                           for l in validas if l["preco_ancora_unit_centavos"] is not None)
    for l in linhas:  # o custo é informação interna
        l.pop("custo_unit_centavos", None)
    return {
        "itens": linhas,
        "valido": len(validas) == len(linhas),
        "pagamento": pagamento,
        "subtotal_centavos": subtotal,
        "cupom": {
            "codigo": achado["codigo"],
            "descricao": cupons.descricao(achado),
            "desconto_centavos": desconto_cupom,
            "frete_gratis": frete_gratis_cupom,
        } if achado else None,
        "cupom_erro": cupom_erro,
        "desconto_cupom_centavos": desconto_cupom,
        "desconto_centavos": desconto,
        "frete": cotacao_frete,
        "total_centavos": total,
        "economia_centavos": economia_ofertas + desconto_cupom + desconto,
        "parcelas_max": parcelas_maximas(total) if pagamento == "cartao" else 1,
        "falta_para_frete_gratis": 0 if frete_gratis_cupom else max(0, config.FRETE_GRATIS_A_PARTIR - subtotal),
        "previsao_envio": previsao_envio,
    }
