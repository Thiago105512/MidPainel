"""Cotagem, simbolos de anotacao e carimbo (NBR 8402 / 6492 / 10582)."""
from __future__ import annotations

import math

from core import P, Canvas, View, TXT, LW, PRETO, CINZA, MARGEM_ESQ


# ------------------------------------------------------------------ cotas
def _fmt(mm: float) -> str:
    """Cota em metros, 2 casas, padrao de prancha brasileira."""
    return f"{mm/1000:.2f}".replace(".", ",")


def cadeia(cv: Canvas, vw: View, coords: list[float], fixo: float,
           eixo: str, offset: float, h: float = TXT["min"],
           tracos: bool = True) -> None:
    """Linha de cota com cotas parciais entre coords consecutivas.

    eixo 'H': cota dimensoes ao longo de X, linha paralela a X.
    eixo 'V': cota dimensoes ao longo de Y, linha paralela a Y.
    offset  : distancia em mm de PAPEL a partir de `fixo` (sinal define o lado).
    """
    coords = sorted(set(coords))
    if len(coords) < 2:
        return
    if eixo == "H":
        ylin = vw.pt(P(0, fixo))[1] + offset
        for c in coords:
            xp = vw.pt(P(c, fixo))[0]
            cv.linha_p((xp, vw.pt(P(c, fixo))[1]), (xp, ylin + math.copysign(1.2, offset)),
                       "cota", cor=CINZA)
        cv.linha_p((vw.pt(P(coords[0], fixo))[0], ylin),
                   (vw.pt(P(coords[-1], fixo))[0], ylin), "cota")
        for a, b in zip(coords, coords[1:]):
            xa, xb = vw.pt(P(a, fixo))[0], vw.pt(P(b, fixo))[0]
            if tracos:
                _tique(cv, (xa, ylin))
                _tique(cv, (xb, ylin))
            if xb - xa > h * 1.6:
                cv.texto_p(((xa + xb) / 2, ylin - h * 0.62), _fmt(b - a), h, "middle")
            else:
                cv.texto_p(((xa + xb) / 2, ylin - h * 1.5), _fmt(b - a), h * 0.85,
                           "middle", rot=90)
    else:
        xlin = vw.pt(P(fixo, 0))[0] + offset
        for c in coords:
            yp = vw.pt(P(fixo, c))[1]
            cv.linha_p((vw.pt(P(fixo, c))[0], yp), (xlin + math.copysign(1.2, offset), yp),
                       "cota", cor=CINZA)
        cv.linha_p((xlin, vw.pt(P(fixo, coords[0]))[1]),
                   (xlin, vw.pt(P(fixo, coords[-1]))[1]), "cota")
        for a, b in zip(coords, coords[1:]):
            ya, yb = vw.pt(P(fixo, a))[1], vw.pt(P(fixo, b))[1]
            if tracos:
                _tique(cv, (xlin, ya))
                _tique(cv, (xlin, yb))
            if abs(yb - ya) > h * 1.6:
                cv.texto_p((xlin - h * 0.62, (ya + yb) / 2), _fmt(b - a), h, "middle", rot=90)
            else:
                cv.texto_p((xlin - h * 1.5, (ya + yb) / 2), _fmt(b - a), h * 0.85, "middle")


def _tique(cv: Canvas, p: tuple[float, float], r: float = 1.0) -> None:
    """Traco a 45 graus, padrao de cotagem arquitetonica."""
    cv.linha_p((p[0] - r * 0.7, p[1] + r * 0.7), (p[0] + r * 0.7, p[1] - r * 0.7), "cota")


# ------------------------------------------------------------- simbolos
def norte(cv: Canvas, pos: tuple[float, float], r: float = 9.0, ang: float = 0.0) -> None:
    a = math.radians(90 + ang)
    pt = (pos[0] + r * math.cos(a), pos[1] - r * math.sin(a))
    b1 = (pos[0] + r * 0.34 * math.cos(a - 2.4), pos[1] - r * 0.34 * math.sin(a - 2.4))
    b2 = (pos[0] + r * 0.34 * math.cos(a + 2.4), pos[1] - r * 0.34 * math.sin(a + 2.4))
    cv.circ_p(pos, r, "fino", cor=CINZA)
    cv.poli_p([pt, b1, pos, b2], "vista", fechado=True, preenche="#000")
    # o rotulo acompanha a ponta da seta, nao o topo da folha
    lx = pos[0] + (r + 4.0) * math.cos(a)
    ly = pos[1] - (r + 4.0) * math.sin(a)
    cv.texto_p((lx, ly), "N", TXT["peq"], "middle", peso="bold")


def nivel(cv: Canvas, vw: View, p: P, valor_mm: float, acabado: bool = True) -> None:
    x, y = vw.pt(p)
    s = 1.8
    cv.poli_p([(x, y), (x - s, y - s * 1.4), (x + s, y - s * 1.4)], "fino",
              fechado=True, preenche="#000")
    txt = f"{'+' if valor_mm >= 0 else '-'}{abs(valor_mm)/1000:.2f}".replace(".", ",")
    cv.texto_p((x + s + 0.8, y - s * 0.9), f"{txt} ({'NA' if acabado else 'NO'})",
               TXT["micro"], "start")


def marca_corte(cv: Canvas, vw: View, a: P, b: P, letra: str) -> None:
    """Linha de corte com setas e identificacao nas duas extremidades."""
    pa, pb = vw.pt(a), vw.pt(b)
    cv.linha_p(pa, pb, "eixo", cor="#c00")
    for p, sinal in ((pa, 1), (pb, -1)):
        cv.circ_p(p, 3.2, "vista", preenche="#fff", cor="#c00")
        cv.texto_p(p, letra, TXT["min"], "middle", cor="#c00", peso="bold")


def eixo_modular(cv: Canvas, vw: View, coord: float, ini: float, fim: float,
                 eixo: str, rotulo: str, ext: float = 7.0) -> None:
    if eixo == "V":
        p0, p1 = vw.pt(P(coord, ini)), vw.pt(P(coord, fim))
        cv.linha_p((p0[0], p0[1] + ext), (p1[0], p1[1] - ext), "eixo", cor="#0a6")
        cv.circ_p((p1[0], p1[1] - ext - 3.4), 3.4, "fino", preenche="#fff", cor="#0a6")
        cv.texto_p((p1[0], p1[1] - ext - 3.4), rotulo, TXT["min"], "middle", cor="#0a6")
    else:
        p0, p1 = vw.pt(P(ini, coord)), vw.pt(P(fim, coord))
        cv.linha_p((p0[0] - ext, p0[1]), (p1[0] + ext, p1[1]), "eixo", cor="#0a6")
        cv.circ_p((p0[0] - ext - 3.4, p0[1]), 3.4, "fino", preenche="#fff", cor="#0a6")
        cv.texto_p((p0[0] - ext - 3.4, p0[1]), rotulo, TXT["min"], "middle", cor="#0a6")


def titulo_desenho(cv: Canvas, pos: tuple[float, float], num: str, nome: str,
                   escala: str) -> None:
    cv.circ_p((pos[0] + 4, pos[1] - 4), 4, "vista")
    cv.texto_p((pos[0] + 4, pos[1] - 4), num, TXT["peq"], "middle", peso="bold")
    cv.texto_p((pos[0] + 11, pos[1] - 5.6), nome, TXT["med"], "start", peso="bold")
    cv.texto_p((pos[0] + 11, pos[1] - 0.8), f"ESCALA {escala}", TXT["peq"], "start")
    cv.linha_p((pos[0], pos[1] + 1.6), (pos[0] + 11 + len(nome) * 2.1, pos[1] + 1.6), "vista")


def escala_grafica(cv: Canvas, pos: tuple[float, float], vw: View,
                   passo_mm: int = 1000, n: int = 5) -> None:
    x, y = pos
    larg = vw.d(passo_mm)
    for i in range(n):
        cv.poli_p([(x + i * larg, y), (x + (i + 1) * larg, y),
                   (x + (i + 1) * larg, y + 1.6), (x + i * larg, y + 1.6)],
                  "fino", fechado=True, preenche="#000" if i % 2 == 0 else "#fff")
        cv.texto_p((x + i * larg, y + 4.4), f"{i*passo_mm/1000:.0f}", TXT["micro"], "middle")
    cv.texto_p((x + n * larg, y + 4.4), f"{n*passo_mm/1000:.0f} m", TXT["micro"], "start")


# ------------------------------------------------------------- carimbo
def carimbo(cv: Canvas, titulo: str, escala: str, prancha: str,
            total: str, notas: list[str] | None = None,
            revisao: str | None = None) -> None:
    """Legenda na margem inferior direita (NBR 10582), 175 mm de largura."""
    if revisao is None:
        import projeto as _pj
        revisao = _pj.EMISSAO["revisao"]
    L, A, m = cv.larg, cv.alt, cv.marg
    w, h = 175.0, 62.0
    x0, y0 = L - m - w, A - m - h
    cv.poli_p([(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)],
              "moldura", fechado=True, preenche="#fff")

    def linha_h(yy):
        cv.linha_p((x0, yy), (x0 + w, yy), "vista")

    def texto(xx, yy, s, hh=TXT["min"], anc="start", peso="normal", cor=PRETO):
        cv.texto_p((xx, yy), s, hh, anc, peso=peso, cor=cor)

    texto(x0 + 3, y0 + 6, "PROJETO PORTO REAL", TXT["med"], peso="bold")
    texto(x0 + 3, y0 + 12.5, "RESIDENCIA UNIFAMILIAR  |  MANAUS - AM  |  SU16 TARUMA (H)", TXT["micro"])
    linha_h(y0 + 16)
    texto(x0 + 3, y0 + 22, "PROJETO ARQUITETONICO", TXT["micro"], cor=CINZA)
    texto(x0 + 3, y0 + 28, titulo.upper(), TXT["med"], peso="bold")
    linha_h(y0 + 33)

    col = [x0, x0 + 46, x0 + 92, x0 + 133, x0 + w]
    for cx in col[1:-1]:
        cv.linha_p((cx, y0 + 33), (cx, y0 + h), "vista")
    cv.linha_p((col[3], y0 + 33), (col[3], y0 + h), "vista")

    texto(col[0] + 3, y0 + 38, "BASE GEOMETRICA", TXT["micro"], cor=CINZA)
    texto(col[0] + 3, y0 + 44, "Lista Consolidada", TXT["min"])
    texto(col[0] + 3, y0 + 49, "pos-R32 (prevalece)", TXT["micro"])
    texto(col[0] + 3, y0 + 56, "UNIDADE MESTRE: mm", TXT["micro"], cor=CINZA)

    texto(col[1] + 3, y0 + 38, "ESCALA", TXT["micro"], cor=CINZA)
    texto(col[1] + 3, y0 + 45, escala, TXT["gr"], peso="bold")
    texto(col[1] + 3, y0 + 53, f"FORMATO {cv.formato}", TXT["micro"])
    texto(col[1] + 3, y0 + 58, "MALHA 600/300/150", TXT["micro"])

    texto(col[2] + 3, y0 + 38, "EMISSAO", TXT["micro"], cor=CINZA)
    texto(col[2] + 3, y0 + 44, f"ESTUDO PRELIMINAR  {revisao}", TXT["min"])
    texto(col[2] + 3, y0 + 50, "NAO LIBERADO PARA OBRA", TXT["micro"], cor="#c00")
    texto(col[2] + 3, y0 + 56, "SEM ART / RRT", TXT["micro"], cor="#c00")

    texto(col[3] + 3, y0 + 38, "PRANCHA", TXT["micro"], cor=CINZA)
    texto(col[3] + 3, y0 + 48, prancha, TXT["tit"], peso="bold")
    texto(col[3] + 3, y0 + 57, f"de {total}   REV {revisao}", TXT["micro"])

    if notas:
        ny = y0 - 4 - 4.2 * len(notas)
        cv.texto_p((x0, ny - 5), "NOTAS", TXT["min"], "start", peso="bold")
        for i, n in enumerate(notas):
            cv.texto_p((x0, ny + i * 4.2), f"- {n}", TXT["micro"], "start")
