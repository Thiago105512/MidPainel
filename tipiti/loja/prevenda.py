"""Pré-venda do próximo lote.

Um produto com `prevenda_chegada` (data, no horário de Manaus) no futuro está em pré-venda: o `estoque` dele passa a
significar as vagas do lote que será importado, e cada venda baixa uma vaga (a mesma baixa de estoque de sempre, na
mesma transação do pedido; cancelamento e expiração da reserva devolvem a vaga). Chegada a data, o produto volta a
ser vendido do estoque normal — o que sobrou das vagas vira estoque; ajuste-o no painel quando o lote chegar.

O pedido guarda `previsao_envio` = a chegada mais tardia entre os itens em pré-venda + o prazo de manuseio, e o prazo
do frete passa a contar a partir dessa data.
"""

import re
from datetime import date, timedelta

from . import config, horario
from .validacao import ErroValidacao

DIAS_MAX = 366 * 2

# Data de chegada enquanto ainda é futura (hoje em Manaus = UTC−4), senão NULL; calculado junto com o produto `p`.
SQL_PREVENDA_ATIVA = "CASE WHEN p.prevenda_chegada > date('now', '-4 hours') THEN p.prevenda_chegada END"


def hoje_loja():
    return horario.agora().astimezone(horario.FUSO_LOJA).date()


def resumo(chegada_ativa):
    """Campo `prevenda` dos produtos: {"chegada": "AAAA-MM-DD"} ou None."""
    return {"chegada": chegada_ativa} if chegada_ativa else None


def previsao_envio(chegadas):
    """Maior chegada (entre as datas não nulas) + manuseio, como 'AAAA-MM-DD'; None se não há pré-venda."""
    datas = [date.fromisoformat(c) for c in chegadas if c]
    if not datas:
        return None
    return (max(datas) + timedelta(days=config.PRAZO_MANUSEIO_DIAS)).isoformat()


def validar(dados, atual):
    """`prevenda_chegada` enviado pelo painel: devolve ("AAAA-MM-DD" ou None,) ou None se não veio/não mudou.

    Aceita só data futura (amanhã em diante, no horário de Manaus) e até dois anos à frente; null/"" encerra.
    """
    if "prevenda_chegada" not in dados:
        return None
    valor = dados["prevenda_chegada"]
    if valor in (None, ""):
        return None if atual is None else (None,)
    erro = {"prevenda_chegada": "Informe a data de chegada no formato AAAA-MM-DD."}
    if not isinstance(valor, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", valor.strip()):
        raise ErroValidacao(erro)
    try:
        chegada = date.fromisoformat(valor.strip())
    except ValueError:
        raise ErroValidacao(erro)
    texto = chegada.isoformat()
    if texto == atual:
        return None  # reenviada sem mudança (o formulário inteiro salvo de novo)
    hoje = hoje_loja()
    if chegada <= hoje:
        raise ErroValidacao({"prevenda_chegada": "A data de chegada do lote precisa ser no futuro."})
    if chegada > hoje + timedelta(days=DIAS_MAX):
        raise ErroValidacao({"prevenda_chegada": "Use uma data de chegada nos próximos dois anos."})
    return (texto,)
