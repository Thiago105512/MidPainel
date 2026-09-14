"""CONTRAVENTAMENTO — estabilidade horizontal e trelicas (secoes 27, 28, 29).

Uma parede de LSF nao resiste a forca horizontal por si: montante e guia formam
um quadrilatero articulado, que e um MECANISMO. O que impede a casa de deitar e
sempre uma das tres coisas — uma diagonal, uma placa colada ao quadro, ou um
portico rigido —, e escolher qual e a decisao que governa o custo do
contraventamento inteiro.

O ponto que costuma passar: a parede que resiste ao vento tambem tenta GIRAR.
O momento de tombamento nao some porque a diagonal e forte; ele desce pelo
montante de extremidade e tenta arrancar a parede do radier. Quem segura e o
hold-down, e ele so existe se alguem calcular o arrancamento — que e o que esta
implementado aqui.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import nucleo.solver as sv


@dataclass
class ShearWall:
    cod: str
    comp: float            # mm, comprimento do segmento de parede
    altura: float          # mm
    tipo: str              # "fita X", "OSB", "portal"
    peso_permanente: float = 0.0    # kN sobre o segmento (favoravel ao tombamento)


# Resistencia ao cisalhamento no plano, kN/m de parede. (H) — vem de ENSAIO do
# fabricante do painel; nenhuma tabela substitui o relatorio. Os valores abaixo
# sao ordens de grandeza usuais para dimensionar o estudo.
RESISTENCIA_UNITARIA = {
    "fita X 38x0,80 a 45 graus": 3.5,
    "fita X 50x1,25 a 45 graus": 7.0,
    "OSB 11,1 mm, parafuso a 150 mm": 6.5,
    "OSB 11,1 mm, parafuso a 100 mm": 9.0,
    "OSB 15,1 mm, parafuso a 100 mm": 12.0,
    "portal frame": 0.0,          # nao se mede por metro: resolve por rigidez
}
# Relacao altura/comprimento maxima admitida para o segmento contar como
# parede de cisalhamento. Acima disso ele gira mais do que resiste.
ASPECTO_MAX = {"fita X": 2.0, "OSB": 2.0, "portal": 4.0}


def capacidade(sw: ShearWall, sistema: str) -> dict:
    """Forca horizontal que o segmento resiste, e se a esbeltez permite conta-lo."""
    if sistema not in RESISTENCIA_UNITARIA:
        raise KeyError(f"sistema '{sistema}' sem resistencia declarada")
    familia = "fita X" if "fita" in sistema else ("OSB" if "OSB" in sistema else "portal")
    aspecto = sw.altura / sw.comp
    limite = ASPECTO_MAX[familia]
    v = RESISTENCIA_UNITARIA[sistema] * sw.comp / 1000.0
    return dict(vrd=v if aspecto <= limite else 0.0, aspecto=aspecto,
                limite=limite, familia=familia,
                conta=aspecto <= limite,
                motivo="" if aspecto <= limite else
                f"aspecto {aspecto:.2f} acima de {limite}: o segmento gira em "
                f"vez de resistir e nao pode ser contado")


def tombamento(sw: ShearWall, v_kn: float) -> dict:
    """Arrancamento no montante de extremidade (secao 29).

    O momento de tombamento V.h e equilibrado pelo binario T.L menos o peso
    proprio, que entra MINORADO (0,9) porque aliviar o tombamento e efeito
    favoravel — a mesma logica do permanente favoravel da NBR 8681.
    """
    m_tomb = v_kn * sw.altura / 1000.0                 # kNm
    m_estab = 0.9 * sw.peso_permanente * (sw.comp / 1000.0) / 2
    t = (m_tomb - m_estab) / (sw.comp / 1000.0)        # kN de tracao
    return dict(m_tombamento=m_tomb, m_estabilizante=m_estab,
                uplift=max(0.0, t), precisa_holddown=t > 0,
                compressao=max(0.0, t) + sw.peso_permanente / 2)


def forca_na_diagonal(v_kn: float, comp: float, altura: float) -> dict:
    """A fita so trabalha a TRACAO: a diagonal comprimida enruga e nao conta."""
    ang = math.degrees(math.atan2(altura, comp))
    f = v_kn / math.cos(math.radians(ang))
    return dict(angulo=ang, forca=f,
                eficiente=30 <= ang <= 60,
                obs="fora de 30 a 60 graus a fita perde eficiencia: muito "
                    "deitada puxa demais a guia, muito em pe quase nao resiste "
                    "a horizontal")


# ------------------------------------------------------------------ trelicas
TIPOS_TRELICA = {
    "Fink": "duas diagonais por agua formando W — a mais economica em telhado",
    "Howe": "montantes verticais tracionados, diagonais comprimidas",
    "Pratt": "o inverso do Howe: diagonais tracionadas, melhor para aco",
    "Warren": "diagonais alternadas sem montante, banzos mais solicitados",
    "Scissor": "banzo inferior inclinado — ganha pe-direito, perde rigidez",
    "Mono": "uma agua so",
    "Attic": "banzo inferior interrompido para abrir espaco utilizavel",
}


def geometria_trelica(tipo: str, vao: float, altura: float, n: int = 4) -> dict:
    """Nos e barras da trelica, prontos para o solver da E5."""
    if tipo not in TIPOS_TRELICA:
        raise KeyError(f"trelica '{tipo}' nao implementada")
    nos, barras = {}, []
    if tipo == "Mono":
        for i in range(n + 1):
            x = vao * i / n
            nos[f"i{i}"] = (x, 0.0)
            nos[f"s{i}"] = (x, altura * i / n)
    elif tipo == "Scissor":
        for i in range(n + 1):
            x = vao * i / n
            f = 1 - abs(2 * i / n - 1)
            nos[f"i{i}"] = (x, altura * 0.35 * f)
            nos[f"s{i}"] = (x, altura * f)
    else:
        for i in range(n + 1):
            x = vao * i / n
            f = 1 - abs(2 * i / n - 1)
            nos[f"i{i}"] = (x, 0.0)
            nos[f"s{i}"] = (x, altura * f)
    for i in range(n):
        barras.append((f"i{i}", f"i{i+1}", "banzo inferior"))
        barras.append((f"s{i}", f"s{i+1}", "banzo superior"))
    for i in range(n + 1):
        if nos[f"s{i}"][1] - nos[f"i{i}"][1] > 1.0:
            barras.append((f"i{i}", f"s{i}", "montante"))
    for i in range(n):
        if tipo in ("Howe", "Fink", "Scissor", "Mono"):
            barras.append((f"i{i}", f"s{i+1}", "diagonal"))
        elif tipo == "Pratt":
            barras.append((f"s{i}", f"i{i+1}", "diagonal"))
        elif tipo == "Warren":
            barras.append((f"i{i}", f"s{i+1}", "diagonal") if i % 2 == 0
                          else (f"s{i}", f"i{i+1}", "diagonal"))
        elif tipo == "Attic":
            if i in (0, n - 1):
                barras.append((f"i{i}", f"s{i+1}", "diagonal"))
    return dict(nos=nos, barras=barras, tipo=tipo, vao=vao, altura=altura)


def resolver_trelica(g: dict, secao: sv.Secao, carga_kn_m: float) -> dict:
    """Roda a trelica no solver da E5 e devolve o esforco de cada barra."""
    m = sv.Modelo()
    n = len(g["nos"])
    apoios = sorted(g["nos"])
    esq = min(g["nos"], key=lambda k: (g["nos"][k][0], g["nos"][k][1]))
    dir_ = max(g["nos"], key=lambda k: (g["nos"][k][0], -g["nos"][k][1]))
    for cod, (x, z) in g["nos"].items():
        ap = sv.LIVRE
        if cod == esq:
            ap = (True, True, True, True, False, False)
        elif cod == dir_:
            ap = (False, True, True, False, False, False)
        m.no(cod, x, 0.0, z, ap)
    # trelica plana: trava o fora do plano em todos os nos
    for cod in g["nos"]:
        no = m.nos[cod]
        no.apoio = tuple(a or i in (1, 3, 5) for i, a in enumerate(no.apoio))
    for k, (a, b, papel) in enumerate(g["barras"]):
        m.barra(f"B{k:02d}", a, b, secao)
    sup = [c for c in g["nos"] if c.startswith("s")]
    p = carga_kn_m * (g["vao"] / 1000.0) / max(1, len(sup) - 1)
    for c in sup:
        m.carga(c, fz=-p)
    r = m.resolver()
    esf = {}
    for k, (a, b, papel) in enumerate(g["barras"]):
        n_ax = -r["esforcos"][f"B{k:02d}"][0]
        esf[f"B{k:02d}"] = dict(de=a, para=b, papel=papel, N=n_ax,
                                estado="tracao" if n_ax > 0 else "compressao")
    # Devolve QUAIS nos sao apoio de verdade. Todos os nos recebem restricao
    # fora do plano — senao a trelica plana e um mecanismo no espaco —, e sem
    # esta lista quem conferir o equilibrio somaria as reacoes de todos eles,
    # obtendo zero por construcao: num no livre a soma das forcas de
    # extremidade e igual a carga aplicada ali.
    return dict(esforcos=esf, reacoes=r["reacoes"], carga_total=p * len(sup),
                apoios=(esq, dir_))
