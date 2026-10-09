"""Calculadora de preço para produtos importados.

Parte do custo unitário na moeda do fornecedor, rateia os custos do lote e chega ao custo final
por unidade no Brasil; o preço sugerido cobre a taxa do meio de pagamento e a margem desejada.
"""

from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal, InvalidOperation

from .regras import ErroValidacao

MOEDAS = ("BRL", "USD", "CNY")


def _decimal(dados, campo, erros, padrao=None, minimo=Decimal(0), maximo=None):
    valor = dados.get(campo, padrao)
    if valor in (None, ""):
        valor = padrao
    try:
        numero = Decimal(str(valor).replace(",", "."))
    except (InvalidOperation, ValueError):
        erros[campo] = "Número inválido."
        return Decimal(0)
    if not numero.is_finite() or numero < minimo or (maximo is not None and numero > maximo):
        erros[campo] = "Valor fora do permitido."
        return Decimal(0)
    return numero


def _centavos(valor):
    return int(valor.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def arredondar_preco(centavos):
    """Arredonda para cima até o próximo final ,90 (ex.: 47,12 -> 47,90)."""
    reais = -(-(centavos - 90) // 100)
    return max(90, reais * 100 + 90)


def calcular(dados):
    if not isinstance(dados, dict):
        raise ErroValidacao({"geral": "Dados inválidos."})
    erros = {}
    moeda = str(dados.get("moeda") or "BRL").upper()
    if moeda not in MOEDAS:
        erros["moeda"] = "Moeda inválida."
    custo_moeda = _decimal(dados, "custo_unitario", erros)  # na moeda do fornecedor, ex.: 3.25 (USD)
    cambio = Decimal(1) if moeda == "BRL" else _decimal(dados, "cambio", erros, minimo=Decimal("0.0001"))
    quantidade = _decimal(dados, "quantidade", erros, padrao=1, minimo=Decimal(1))
    frete_lote = _decimal(dados, "frete_lote", erros, padrao=0)          # R$
    outros_lote = _decimal(dados, "outros_lote", erros, padrao=0)        # R$ (despachante, armazenagem…)
    impostos_pct = _decimal(dados, "impostos_pct", erros, padrao=0, maximo=Decimal(300))
    embalagem = _decimal(dados, "embalagem_unidade", erros, padrao=0)    # R$ por unidade
    taxa_pct = _decimal(dados, "taxa_pagamento_pct", erros, padrao=0, maximo=Decimal(50))
    margem_pct = _decimal(dados, "margem_pct", erros, padrao=0, maximo=Decimal(90))
    if not erros and taxa_pct + margem_pct >= 95:
        erros["margem_pct"] = "Taxa + margem precisam somar menos de 95%."
    if erros:
        raise ErroValidacao(erros)

    cem = Decimal(100)
    produto = custo_moeda * cambio * cem                 # centavos por unidade
    frete = frete_lote * cem / quantidade
    impostos = (produto + frete) * impostos_pct / cem
    outros = outros_lote * cem / quantidade
    embal = embalagem * cem
    custo_final = produto + frete + impostos + outros + embal

    divisor = 1 - (taxa_pct + margem_pct) / cem
    preco_exato = custo_final / divisor
    preco_sugerido = arredondar_preco(int(preco_exato.to_integral_value(rounding=ROUND_CEILING)))

    def analisar(preco):
        taxa = Decimal(preco) * taxa_pct / cem
        lucro = Decimal(preco) - taxa - custo_final
        return {
            "preco_centavos": preco,
            "taxa_centavos": _centavos(taxa),
            "lucro_centavos": _centavos(lucro),
            "margem_pct": float((lucro / Decimal(preco) * cem).quantize(Decimal("0.1"))) if preco else 0.0,
            "markup": float((Decimal(preco) / custo_final).quantize(Decimal("0.01"))) if custo_final else None,
        }

    resultado = {
        "custo": {
            "produto_centavos": _centavos(produto),
            "frete_centavos": _centavos(frete),
            "impostos_centavos": _centavos(impostos),
            "outros_centavos": _centavos(outros),
            "embalagem_centavos": _centavos(embal),
            "total_centavos": _centavos(custo_final),
        },
        "sugerido": analisar(preco_sugerido),
    }
    preco_atual = dados.get("preco_centavos")
    if isinstance(preco_atual, int) and not isinstance(preco_atual, bool) and preco_atual > 0:
        resultado["atual"] = analisar(preco_atual)
    return resultado
