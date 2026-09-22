"""Retangulo de um ambiente OU de uma subdivisao — uma funcao para todos.

R65: acabamento.py, luminotecnica.py e outros tinham cada um o seu
`_geom`/`_rect` que procurava o codigo primeiro em TERREO + SUPERIOR e depois
em SUBDIVISOES. Corpos "quase iguais" com o mesmo nome: quando um deles
aceitar um caso que o outro nao aceita, o orcamento e a luminotecnica
passam a discordar sobre o que e um comodo.
"""


def retangulo(pj, cod: str) -> tuple:
    """(x, y, w, h) em mm do ambiente ou da subdivisao `pai/nome`; zeros se nao existe."""
    a = next((x for x in pj.TERREO + pj.SUPERIOR if x.cod == cod), None)
    if a is not None:
        return a.x, a.y, a.w, a.h
    d = next((x for x in pj.SUBDIVISOES if f"{x['pai']}/{x['nome']}" == cod), None)
    return (d["x"], d["y"], d["w"], d["h"]) if d else (0, 0, 0, 0)


def dimensoes_m(pj, cod: str) -> tuple:
    """(largura m, profundidade m)."""
    _, _, w, h = retangulo(pj, cod)
    return w / 1000.0, h / 1000.0


def area_perimetro(pj, cod: str) -> tuple:
    """(area m2, perimetro m)."""
    _, _, w, h = retangulo(pj, cod)
    return w * h / 1e6, 2 * (w + h) / 1000.0
