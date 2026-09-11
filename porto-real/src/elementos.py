"""
Derivacao automatica de paredes a partir da malha modular e biblioteca de
simbolos de representacao (NBR 6492).

As paredes NAO sao desenhadas a mao: sao deduzidas do preenchimento da malha
de 600 mm pelos ambientes. Uma face entre dois ambientes vira divisoria
interna (100 mm); uma face entre ambiente e exterior vira parede externa
(150 mm). Isso garante que planta, cortes e fachadas usem a MESMA geometria.
"""
from __future__ import annotations

from dataclasses import dataclass

import projeto as pj
from core import P, Canvas, View, TXT, LW, PRETO, CINZA

G = pj.GRID


@dataclass
class Parede:
    x1: int
    y1: int
    x2: int
    y2: int
    esp: int
    externa: bool

    @property
    def horizontal(self) -> bool:
        return self.y1 == self.y2

    @property
    def comp(self) -> int:
        return abs(self.x2 - self.x1) + abs(self.y2 - self.y1)


def _integrado(a: str | None, b: str | None) -> bool:
    """Nao ha parede entre ambientes declarados integrados em projeto.INTEGRADOS."""
    return a is not None and b is not None and frozenset((a, b)) in pj.INTEGRADOS


def _celulas(ambientes: list[pj.Amb]) -> dict[tuple[int, int], str]:
    c: dict[tuple[int, int], str] = {}
    for a in ambientes:
        for i in range(a.x // G, (a.x + a.w) // G):
            for j in range(a.y // G, (a.y + a.h) // G):
                c[(i, j)] = a.cod
    return c


def derivar_paredes(ambientes: list[pj.Amb]) -> list[Parede]:
    """Extrai os trechos de parede do contorno e das divisas entre ambientes."""
    cel = _celulas(ambientes)
    if not cel:
        return []
    imin = min(i for i, _ in cel) - 1
    imax = max(i for i, _ in cel) + 1
    jmin = min(j for _, j in cel) - 1
    jmax = max(j for _, j in cel) + 1

    verticais: list[tuple[int, int, int, bool]] = []   # x, j, esp, externa
    horizontais: list[tuple[int, int, int, bool]] = []  # y, i, esp, externa

    for i in range(imin, imax + 1):
        for j in range(jmin, jmax + 1):
            a, b = cel.get((i, j)), cel.get((i + 1, j))
            if a != b and not _integrado(a, b):
                ext = a is None or b is None
                verticais.append(((i + 1) * G, j, pj.PAR_EXT if ext else pj.PAR_INT, ext))
            a, b = cel.get((i, j)), cel.get((i, j + 1))
            if a != b and not _integrado(a, b):
                ext = a is None or b is None
                horizontais.append(((j + 1) * G, i, pj.PAR_EXT if ext else pj.PAR_INT, ext))

    paredes: list[Parede] = []
    # une trechos colineares contiguos de mesma espessura
    for x, grupo in _agrupar(verticais):
        for esp, ext, ini, fim in grupo:
            paredes.append(Parede(x, ini * G, x, (fim + 1) * G, esp, ext))
    for y, grupo in _agrupar(horizontais):
        for esp, ext, ini, fim in grupo:
            paredes.append(Parede(ini * G, y, (fim + 1) * G, y, esp, ext))
    return paredes


def _agrupar(itens):
    """itens = (coord_fixa, indice, esp, externa) -> runs contiguos."""
    por_coord: dict[int, list[tuple[int, int, bool]]] = {}
    for coord, idx, esp, ext in itens:
        por_coord.setdefault(coord, []).append((idx, esp, ext))
    for coord, lst in sorted(por_coord.items()):
        lst.sort()
        runs = []
        ini, ant, esp0, ext0 = lst[0][0], lst[0][0], lst[0][1], lst[0][2]
        for idx, esp, ext in lst[1:]:
            if idx == ant + 1 and esp == esp0 and ext == ext0:
                ant = idx
            else:
                runs.append((esp0, ext0, ini, ant))
                ini = ant = idx
                esp0, ext0 = esp, ext
        runs.append((esp0, ext0, ini, ant))
        yield coord, runs


# ------------------------------------------------------------------ vaos
def vaos_do_pavimento(pav: str):
    for tipo, x, y, ori, p in pj.VAOS:
        if p == pav:
            larg, alt, peit, desc = pj.ESQUADRIAS[tipo]
            yield dict(tipo=tipo, x=x, y=y, ori=ori, larg=larg, alt=alt,
                       peitoril=peit, desc=desc)


def recortes_na_parede(par: Parede, vaos) -> list[tuple[int, int]]:
    """Intervalos (inicio, fim) ao longo da parede ocupados por vaos."""
    out = []
    for v in vaos:
        if par.horizontal and v["ori"] == "H" and abs(v["y"] - par.y1) < 1:
            a, b = min(par.x1, par.x2), max(par.x1, par.x2)
            if a <= v["x"] <= b:
                out.append((v["x"] - v["larg"] // 2, v["x"] + v["larg"] // 2))
        elif (not par.horizontal) and v["ori"] == "V" and abs(v["x"] - par.x1) < 1:
            a, b = min(par.y1, par.y2), max(par.y1, par.y2)
            if a <= v["y"] <= b:
                out.append((v["y"] - v["larg"] // 2, v["y"] + v["larg"] // 2))
    return sorted(out)


# =========================================================================
# desenho de paredes em planta (elemento seccionado -> traco grosso + hachura)
# =========================================================================
def desenhar_paredes(cv: Canvas, vw: View, paredes: list[Parede], vaos) -> None:
    pat = cv.hachura("lsf", espac=0.9, ang=45, w=0.06, cor="#444")
    for par in paredes:
        cortes = recortes_na_parede(par, vaos)
        e = par.esp
        if par.horizontal:
            a, b = min(par.x1, par.x2), max(par.x1, par.x2)
            trechos = _subtrair(a, b, cortes)
            for t0, t1 in trechos:
                _bloco(cv, vw, t0, par.y1 - e / 2, t1 - t0, e, pat)
        else:
            a, b = min(par.y1, par.y2), max(par.y1, par.y2)
            trechos = _subtrair(a, b, cortes)
            for t0, t1 in trechos:
                _bloco(cv, vw, par.x1 - e / 2, t0, e, t1 - t0, pat)


def _subtrair(a: int, b: int, cortes: list[tuple[int, int]]):
    seg = [(a, b)]
    for c0, c1 in cortes:
        novo = []
        for s0, s1 in seg:
            if c1 <= s0 or c0 >= s1:
                novo.append((s0, s1))
            else:
                if s0 < c0:
                    novo.append((s0, c0))
                if c1 < s1:
                    novo.append((c1, s1))
        seg = novo
    return [s for s in seg if s[1] - s[0] > 1]


def _bloco(cv: Canvas, vw: View, x, y, w, h, pat) -> None:
    pts = [vw.pt(P(x, y)), vw.pt(P(x + w, y)), vw.pt(P(x + w, y + h)), vw.pt(P(x, y + h))]
    cv.poli_p(pts, "corte", fechado=True, preenche=f"url(#{pat})")


# =========================================================================
# simbolos de esquadria
# =========================================================================
def desenhar_vaos(cv: Canvas, vw: View, paredes: list[Parede], vaos) -> None:
    for v in vaos:
        par = _parede_do_vao(paredes, v)
        if par is None:
            continue
        e = par.esp
        t = v["tipo"]
        if t == "PG01":
            _portao_correr(cv, vw, v, par, e)
        elif t.startswith("PV"):
            _correr(cv, vw, v, par, e)
        elif t.startswith("P"):
            _porta(cv, vw, v, par, e)
        else:
            _janela(cv, vw, v, par, e)


def _parede_do_vao(paredes, v):
    for par in paredes:
        if par.horizontal and v["ori"] == "H" and abs(par.y1 - v["y"]) < 1:
            if min(par.x1, par.x2) <= v["x"] <= max(par.x1, par.x2):
                return par
        if (not par.horizontal) and v["ori"] == "V" and abs(par.x1 - v["x"]) < 1:
            if min(par.y1, par.y2) <= v["y"] <= max(par.y1, par.y2):
                return par
    return None


def _porta(cv: Canvas, vw: View, v, par, e) -> None:
    L = v["larg"]
    if par.horizontal:
        x0, y0 = v["x"] - L / 2, v["y"]
        # batentes
        cv.linha_p(vw.pt(P(x0, y0 - e / 2)), vw.pt(P(x0, y0 + e / 2)), "corte")
        cv.linha_p(vw.pt(P(x0 + L, y0 - e / 2)), vw.pt(P(x0 + L, y0 + e / 2)), "corte")
        # folha + arco de varredura
        cv.linha_p(vw.pt(P(x0, y0)), vw.pt(P(x0, y0 + L)), "vista")
        c = vw.pt(P(x0, y0))
        cv.arco_p(c, vw.d(L), 90, 0, "fino")
    else:
        x0, y0 = v["x"], v["y"] - L / 2
        cv.linha_p(vw.pt(P(x0 - e / 2, y0)), vw.pt(P(x0 + e / 2, y0)), "corte")
        cv.linha_p(vw.pt(P(x0 - e / 2, y0 + L)), vw.pt(P(x0 + e / 2, y0 + L)), "corte")
        cv.linha_p(vw.pt(P(x0, y0)), vw.pt(P(x0 + L, y0)), "vista")
        c = vw.pt(P(x0, y0))
        cv.arco_p(c, vw.d(L), 0, -90, "fino")


def _janela(cv: Canvas, vw: View, v, par, e) -> None:
    L = v["larg"]
    if par.horizontal:
        x0, y = v["x"] - L / 2, v["y"]
        for off in (-e / 2, -e / 6, e / 6, e / 2):
            cv.linha_p(vw.pt(P(x0, y + off)), vw.pt(P(x0 + L, y + off)), "fino")
        cv.linha_p(vw.pt(P(x0, y - e / 2)), vw.pt(P(x0, y + e / 2)), "corte")
        cv.linha_p(vw.pt(P(x0 + L, y - e / 2)), vw.pt(P(x0 + L, y + e / 2)), "corte")
    else:
        x, y0 = v["x"], v["y"] - L / 2
        for off in (-e / 2, -e / 6, e / 6, e / 2):
            cv.linha_p(vw.pt(P(x + off, y0)), vw.pt(P(x + off, y0 + L)), "fino")
        cv.linha_p(vw.pt(P(x - e / 2, y0)), vw.pt(P(x + e / 2, y0)), "corte")
        cv.linha_p(vw.pt(P(x - e / 2, y0 + L)), vw.pt(P(x + e / 2, y0 + L)), "corte")


def _portao_correr(cv: Canvas, vw: View, v, par, e) -> None:
    """Portao de correr: folha recolhida lateralmente + seta de deslizamento."""
    L = v["larg"]
    x0, y = v["x"] - L / 2, v["y"]
    cv.linha_p(vw.pt(P(x0, y - e / 2)), vw.pt(P(x0, y + e / 2)), "corte")
    cv.linha_p(vw.pt(P(x0 + L, y - e / 2)), vw.pt(P(x0 + L, y + e / 2)), "corte")
    for off in (-e / 4, e / 4):
        cv.linha_p(vw.pt(P(x0, y + off)), vw.pt(P(x0 + L, y + off)), "fino")
    a, b = vw.pt(P(x0 + L * 0.25, y)), vw.pt(P(x0 + L * 0.75, y))
    cv.linha_p(a, b, "fino", cor=CINZA)
    cv.poli_p([b, (b[0] - 2.4, b[1] - 1.2), (b[0] - 2.4, b[1] + 1.2)], "fino",
              fechado=True, preenche="#888")
    cv.texto_p(((a[0] + b[0]) / 2, a[1] - 2.4), "CORRER", TXT["micro"], "middle", cor=CINZA)


def _correr(cv: Canvas, vw: View, v, par, e) -> None:
    """Vao envidracado de correr (porta-balcao): duas folhas sobrepostas."""
    L = v["larg"]
    if par.horizontal:
        x0, y = v["x"] - L / 2, v["y"]
        cv.linha_p(vw.pt(P(x0, y - e / 2)), vw.pt(P(x0, y + e / 2)), "corte")
        cv.linha_p(vw.pt(P(x0 + L, y - e / 2)), vw.pt(P(x0 + L, y + e / 2)), "corte")
        cv.linha_p(vw.pt(P(x0, y - e / 6)), vw.pt(P(x0 + L * 0.55, y - e / 6)), "vista")
        cv.linha_p(vw.pt(P(x0 + L * 0.45, y + e / 6)), vw.pt(P(x0 + L, y + e / 6)), "vista")
    else:
        x, y0 = v["x"], v["y"] - L / 2
        cv.linha_p(vw.pt(P(x - e / 2, y0)), vw.pt(P(x + e / 2, y0)), "corte")
        cv.linha_p(vw.pt(P(x - e / 2, y0 + L)), vw.pt(P(x + e / 2, y0 + L)), "corte")
        cv.linha_p(vw.pt(P(x - e / 6, y0)), vw.pt(P(x - e / 6, y0 + L * 0.55)), "vista")
        cv.linha_p(vw.pt(P(x + e / 6, y0 + L * 0.45)), vw.pt(P(x + e / 6, y0 + L)), "vista")
