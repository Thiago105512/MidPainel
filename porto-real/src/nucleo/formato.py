"""Formatacao numerica brasileira — UMA funcao, usada pelo nucleo e pelo desenho.

R65: `_brl` existia em viabilidade.py, em acabamento.py e como `brl` em
core.py, tres corpos para o mesmo "R$ 1.234,56". O nucleo nao pode importar
core (fronteira do nucleo), entao a funcao mora aqui e core a reexporta.
"""


def num_br(v, casas: int = 0) -> str:
    """Numero no padrao brasileiro: 1.234,56. Milhar com ponto, decimal com virgula.

    R61 — o idioma `f"{v:,}".replace(",", ".")` estava em 34 lugares. Nos
    numeros puros ele funciona; aplicado a uma frase inteira, troca toda
    virgula do texto por ponto (defeito 77). Formatar e trabalho de funcao.
    """
    s = f"{v:,.{casas}f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def brl(v) -> str:
    return "R$ " + num_br(v, 2)
