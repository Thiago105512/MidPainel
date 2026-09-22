"""VERIFICACAO — NBR 14762:2010, Metodo da Resistencia Direta (secao 15).

Perfil formado a frio nao falha como perfil laminado. A chapa e tao fina que a
secao perde a forma antes de o aco escoar, e sao TRES instabilidades
independentes competindo:

  GLOBAL       a barra inteira encurva ou torce — e onde Cw e o centro de
               torcao, calculados na E1, finalmente entram;
  LOCAL        a alma ou a aba ondula sozinha, com os cantos parados;
  DISTORCIONAL o conjunto aba + labio gira em torno do canto da alma, levando a
               forma da secao junto. E o modo que nao existe em laminado e o que
               mais surpreende quem vem do concreto.

A resistencia e a MENOR das tres, e qual governa muda com o comprimento: local
em barra curta, distorcional em comprimento intermediario, global em barra
longa. Por isso nao se dimensiona perfil formado a frio "pela tensao".

LIMITE DECLARADO (H): a carga de flambagem DISTORCIONAL elastica sai aqui de um
modelo de placa com o labio como enrijecedor de borda, que e conservador. O
valor rigoroso vem de analise de faixas finitas (CUFSM) ou da tabela do
fabricante. Esta e uma pendencia declarada, nao um numero apresentado como
exato.
"""
from __future__ import annotations

import math

NU = 0.30
GAMA = 1.10          # coeficiente de ponderacao da resistencia, NBR 14762


# ------------------------------------------------------- flambagem elastica
def n_global(props: dict, fy: float, E: float, G: float,
             kx=1.0, ky=1.0, kz=1.0, L=3000.0) -> dict:
    """Carga critica elastica de flambagem global (flexao e flexo-torcao)."""
    Ix, Iy, J, Cw = props["Ix"], props["Iy"], props["J"], props["Cw"]
    A, xo, yo, ro = props["A"], props["xo"], props["yo"], props["ro"]
    nex = math.pi ** 2 * E * Ix / (kx * L) ** 2
    ney = math.pi ** 2 * E * Iy / (ky * L) ** 2
    nez = (math.pi ** 2 * E * Cw / (kz * L) ** 2 + G * J) / (ro ** 2)
    modos = {"flexao x": nex, "flexao y": ney, "torcao": nez}
    # flexo-torcao: so existe em secao monossimetrica (xo nao nulo)
    if abs(xo) > 1e-6:
        beta = 1 - (xo / ro) ** 2
        disc = (ney + nez) ** 2 - 4 * beta * ney * nez
        if disc >= 0 and beta > 0:
            modos["flexo-torcao"] = (ney + nez - math.sqrt(disc)) / (2 * beta)
    modo = min(modos, key=modos.get)
    return dict(ne=modos[modo], modo=modo, modos=modos)


def _k_placa(apoiada_dos_lados: bool) -> float:
    """Coeficiente de flambagem de placa em compressao uniforme."""
    return 4.0 if apoiada_dos_lados else 0.425


def sigma_placa(b: float, t: float, E: float, k: float) -> float:
    """Tensao critica de flambagem local de uma placa (Bryan)."""
    return k * math.pi ** 2 * E / (12 * (1 - NU ** 2)) * (t / b) ** 2


def n_local(perfil, props: dict, E: float) -> dict:
    """Carga de flambagem local elastica pelo elemento mais esbelto.

    Cada parede plana e tratada como placa: alma e aba entre dobras sao
    apoiadas dos dois lados (k = 4,0); o labio tem uma borda livre (k = 0,425).
    A menor tensao critica governa a secao inteira, porque a onda local de uma
    parede arrasta as vizinhas.
    """
    t = perfil.t
    elementos = []
    alma = perfil.bw - 2 * (perfil.t)
    elementos.append(("alma", alma, True))
    aba = perfil.bf - perfil.t
    elementos.append(("aba", aba, bool(perfil.D)))
    if perfil.D:
        elementos.append(("labio", perfil.D - perfil.t / 2, False))
    piores = []
    for nome, b, apoiada in elementos:
        if b <= 0:
            continue
        piores.append((sigma_placa(b, t, E, _k_placa(apoiada)), nome, b))
    sig, nome, b = min(piores)
    return dict(sigma=sig, nl=sig * props["A"], elemento=nome, largura=b,
                esbeltez=b / t)


def n_distorcional(perfil, props: dict, E: float) -> dict:
    """(H) Flambagem distorcional por modelo de placa com enrijecedor de borda.

    Conservador por construcao: trata o conjunto aba + labio como uma placa de
    largura equivalente com um lado livre. O valor rigoroso exige faixas finitas.
    """
    if not perfil.D:
        return dict(sigma=float("inf"), nd=float("inf"), nota="sem labio")
    beq = perfil.bf + 0.5 * perfil.D
    sig = sigma_placa(beq, perfil.t, E, 0.9)
    return dict(sigma=sig, nd=sig * props["A"], largura_eq=beq,
                nota="(H) modelo de placa conservador; confirmar por faixas finitas")


# --------------------------------------------------------------- compressao
def compressao(perfil, aco, L=3000.0, kx=1.0, ky=1.0, kz=1.0,
               E=205_000.0, G=78_850.0) -> dict:
    """Forca axial resistente de calculo pelo MRD (NBR 14762, anexo C)."""
    p = perfil.props()
    fy = aco.fy
    A = p["A"]
    ny = A * fy / 1000.0                       # kN

    g = n_global(p, fy, E, G, kx, ky, kz, L)
    ne = g["ne"] * 1e-3                        # kN
    lam0 = math.sqrt(ny / ne)
    if lam0 <= 1.5:
        nc = 0.658 ** (lam0 ** 2) * ny
    else:
        nc = 0.877 / lam0 ** 2 * ny

    loc = n_local(perfil, p, E)
    nl = loc["nl"] / 1000.0
    laml = math.sqrt(nc / nl)
    if laml <= 0.776:
        ncl = nc
    else:
        r = nl / nc
        ncl = (1 - 0.15 * r ** 0.4) * r ** 0.4 * nc

    dis = n_distorcional(perfil, p, E)
    nd_e = dis["nd"] / 1000.0 if dis["nd"] != float("inf") else float("inf")
    if nd_e == float("inf"):
        nd = ny
        lamd = 0.0
    else:
        lamd = math.sqrt(ny / nd_e)
        if lamd <= 0.561:
            nd = ny
        else:
            r = nd_e / ny
            nd = (1 - 0.25 * r ** 0.6) * r ** 0.6 * ny

    modos = {"global": nc, "local": ncl, "distorcional": nd}
    critico = min(modos, key=modos.get)
    nrk = modos[critico]
    return dict(nrd=nrk / GAMA, nrk=nrk, modo=critico, modos=modos,
                ny=ny, ne=ne, nl=nl, nd=nd_e,
                lam0=lam0, laml=laml, lamd=lamd,
                modo_global=g["modo"], elemento_local=loc["elemento"],
                esbeltez_local=loc["esbeltez"], nota_distorcional=dis.get("nota", ""))


# ------------------------------------------------------------------ flexao
def flexao(perfil, aco, L=3000.0, cb=1.0, E=205_000.0, G=78_850.0,
           travado=False) -> dict:
    """Momento fletor resistente de calculo pelo MRD."""
    p = perfil.props()
    fy = aco.fy
    my = p["Wx"] * fy / 1e6                    # kNm
    if travado:
        me = float("inf")
        lam0 = 0.0
        mc = my
    else:
        # momento critico de flambagem lateral com torcao, secao monossimetrica
        cy = math.pi ** 2 * E * p["Iy"] / L ** 2
        cz = (math.pi ** 2 * E * p["Cw"] / L ** 2 + G * p["J"]) / p["ro"] ** 2
        me = cb * p["ro"] * math.sqrt(cy * cz) / 1e6
        lam0 = math.sqrt(my / me)
        if lam0 ** 2 <= 0.6:
            mc = my
        elif lam0 ** 2 < 1.336:
            mc = (10 / 9) * my * (1 - 10 * lam0 ** 2 / 36)
        else:
            mc = my / lam0 ** 2

    loc = n_local(perfil, p, E)
    ml = loc["sigma"] * p["Wx"] / 1e6
    laml = math.sqrt(mc / ml)
    if laml <= 0.776:
        mcl = mc
    else:
        r = ml / mc
        mcl = (1 - 0.15 * r ** 0.4) * r ** 0.4 * mc

    dis = n_distorcional(perfil, p, E)
    if dis["nd"] == float("inf"):
        md, lamd = my, 0.0
    else:
        mdist = dis["sigma"] * p["Wx"] / 1e6
        lamd = math.sqrt(my / mdist)
        if lamd <= 0.673:
            md = my
        else:
            r = mdist / my
            md = (1 - 0.22 * r ** 0.5) * r ** 0.5 * my

    modos = {"global": mc, "local": mcl, "distorcional": md}
    critico = min(modos, key=modos.get)
    mrk = modos[critico]
    return dict(mrd=mrk / GAMA, mrk=mrk, modo=critico, modos=modos,
                my=my, me=me, lam0=lam0, laml=laml, lamd=lamd)


def cisalhamento(perfil, aco, E=205_000.0) -> dict:
    """Forca cortante resistente (NBR 14762, item 9.7)."""
    h = perfil.bw - 2 * perfil.t
    t = perfil.t
    fy = aco.fy
    kv = 5.0                                   # alma sem enrijecedor transversal
    lam = (h / t) / math.sqrt(E * kv / fy)
    if lam <= 0.82:
        vn = 0.60 * fy * h * t
    elif lam <= 1.40:
        vn = 0.60 * fy * h * t * 0.82 / lam
    else:
        vn = 0.905 * E * kv * t ** 3 / h
    return dict(vrd=vn / 1000.0 / GAMA, vrk=vn / 1000.0, lam=lam, esbeltez=h / t)


def interacao(nsd: float, msd: float, nrd: float, mrd: float) -> dict:
    """Interacao forca axial + momento fletor (NBR 14762, item 9.8)."""
    u = abs(nsd) / nrd + abs(msd) / mrd
    return dict(uso=u, ok=u <= 1.0,
                parcela_n=abs(nsd) / nrd, parcela_m=abs(msd) / mrd,
                governa="axial" if abs(nsd) / nrd > abs(msd) / mrd else "flexao")
