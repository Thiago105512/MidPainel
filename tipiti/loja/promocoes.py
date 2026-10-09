"""Ofertas relâmpago: desconto percentual com data de término real, aplicado ao produto e às suas opções.

A promoção vale enquanto `promo_pct` e `promo_fim` estão preenchidos e `promo_fim` está no futuro.
Terminado o prazo ela some sozinha — o contador nunca é reiniciado.
"""

from . import horario
from .validacao import ErroValidacao

PROMO_PCT_MIN, PROMO_PCT_MAX = 1, 90

# Percentual da promoção ativa agora (ou NULL), calculado no banco junto com o produto `p`.
SQL_PROMO_ATIVA = "CASE WHEN p.promo_pct IS NOT NULL AND p.promo_fim > datetime('now') THEN p.promo_pct END"


def preco_com_desconto(preco, pct):
    """Preço efetivo: preço × (100 − pct) / 100, arredondado para o centavo mais próximo (meio para cima)."""
    if not pct:
        return preco
    return (preco * (100 - pct) + 50) // 100


def sql_preco_final(coluna_preco="p.preco_centavos"):
    """O mesmo cálculo de preco_com_desconto, em SQL (para ordenar por preço)."""
    return (f"CASE WHEN ({SQL_PROMO_ATIVA}) IS NULL THEN {coluna_preco} "
            f"ELSE ({coluna_preco} * (100 - p.promo_pct) + 50) / 100 END")


def preco_ancora(preco, preco_de, pct):
    """Preço riscado: com promoção, o maior entre o preço "de" e o preço normal; sem, o "de" se for maior."""
    if pct:
        return max(preco_de or 0, preco)
    if preco_de and preco_de > preco:
        return preco_de
    return None


def validar(dados, pct_atual, fim_atual):
    """Valida promo_pct/promo_fim enviados pelo painel. Devolve (pct, fim no formato do banco) ou None se nada mudou.

    Os dois andam juntos: ou a promoção tem percentual e término (no futuro), ou os dois ficam vazios.
    """
    if "promo_pct" not in dados and "promo_fim" not in dados:
        return None
    erros = {}
    pct = dados.get("promo_pct", pct_atual)
    fim = dados.get("promo_fim", fim_atual)
    pct = None if pct == "" else pct
    fim = None if fim == "" else fim
    if pct is not None and (isinstance(pct, bool) or not isinstance(pct, int)
                            or not PROMO_PCT_MIN <= pct <= PROMO_PCT_MAX):
        erros["promo_pct"] = f"Use um desconto inteiro entre {PROMO_PCT_MIN}% e {PROMO_PCT_MAX}%."
    if fim is not None:
        try:
            fim = horario.ler_data(fim)
        except (TypeError, ValueError):
            erros["promo_fim"] = "Informe a data e hora de término da oferta."
    if not erros and (pct, fim) == (pct_atual, fim_atual):
        return None  # reenviada sem mudança (ex.: o formulário inteiro salvo de novo): não exige término futuro
    if not erros and (pct is None) != (fim is None):
        erros["promo"] = "Informe o desconto e o término da oferta juntos (ou deixe os dois vazios para encerrar)."
    if not erros and fim is not None and horario.de_db(fim) <= horario.agora():
        erros["promo_fim"] = "O término da oferta precisa ser no futuro."
    if erros:
        raise ErroValidacao(erros)
    return pct, fim
