"""Cortes, fachadas, croqui axonometrico, detalhes e quadros gerais."""
from __future__ import annotations

import math

import projeto as pj
import elementos as el
import anotacao as an
from core import P, Canvas, View, TXT, CINZA, PRETO
from pranchas import base, _tabela, _extremos

LAJE = 150
PLATIBANDA_1PAV = 3_150
PLATIBANDA_2PAV = pj.TOPO_PLATIBANDA
RADIER = 180


def _dentro(ambs, x, y) -> bool:
    return any(a.x <= x < a.x + a.w and a.y <= y < a.y + a.h for a in ambs)


def _amb_em(ambs, x, y):
    for a in ambs:
        if a.x <= x < a.x + a.w and a.y <= y < a.y + a.h:
            return a
    return None


# =========================================================================
# CORTES
# =========================================================================
def _desenhar_corte(cv: Canvas, vw: View, eixo: str, coord: int, letra: str,
                    ini: int, fim: int) -> None:
    """eixo 'H': plano em y=coord, eixo horizontal do desenho = X.
       eixo 'V': plano em x=coord, eixo horizontal do desenho = Y."""
    pat = cv.hachura("lsfc", espac=0.9, ang=45, w=0.06, cor="#444")
    pat_cc = cv.hachura_dupla("concreto", espac=1.1, w=0.06, cor="#666")
    T, S = pj.TERREO, pj.SUPERIOR

    def ponto(u, z):
        return vw.pt(P(u, z))

    def barra(u0, u1, z0, z1, padrao, estilo="corte"):
        cv.poli_p([ponto(u0, z0), ponto(u1, z0), ponto(u1, z1), ponto(u0, z1)],
                  estilo, fechado=True, preenche=f"url(#{padrao})" if padrao else "#fff")

    passo = 300
    # ---- radier, lajes, cobertura e platibanda (trechos contiguos mesclados)
    celulas = []
    u = ini
    while u < fim:
        x, y = (u, coord) if eixo == "H" else (coord, u)
        celulas.append((u, _dentro(T, x + 1, y + 1), _dentro(S, x + 1, y + 1)))
        u += passo
    runs = []
    for u, t, s_ in celulas:
        if runs and runs[-1][2] == t and runs[-1][3] == s_:
            runs[-1][1] = u + passo
        else:
            runs.append([u, u + passo, t, s_])
    for u0, u1, t, s_ in runs:
        if t:
            barra(u0, u1, -RADIER, 0, pat_cc)
        if s_:
            barra(u0, u1, pj.NIVEL_SUPERIOR - LAJE, pj.NIVEL_SUPERIOR, pat_cc)
            ztopo = pj.NIVEL_SUPERIOR + pj.PE_DIREITO
            barra(u0, u1, ztopo, ztopo + LAJE, pat_cc)
            barra(u0, u1, ztopo + LAJE, PLATIBANDA_2PAV, None, "corte2")
        elif t:
            ztopo = pj.PE_DIREITO
            barra(u0, u1, ztopo, ztopo + LAJE, pat_cc)
            barra(u0, u1, ztopo + LAJE, PLATIBANDA_1PAV, None, "corte2")

    # ---- paredes seccionadas
    for ambs, z0 in ((T, 0), (S, pj.NIVEL_SUPERIOR)):
        for par in el.derivar_paredes(ambs):
            if eixo == "H":
                if par.horizontal:
                    continue
                a, b = min(par.y1, par.y2), max(par.y1, par.y2)
                if not (a <= coord < b):
                    continue
                up = par.x1
            else:
                if not par.horizontal:
                    continue
                a, b = min(par.x1, par.x2), max(par.x1, par.x2)
                if not (a <= coord < b):
                    continue
                up = par.y1
            e = par.esp
            barra(up - e / 2, up + e / 2, z0, z0 + pj.PE_DIREITO, pat)

    # ---- linha do terreno
    cv.linha_p(ponto(ini - 900, 0), ponto(fim + 900, 0), "corte")
    for k in range(int((fim - ini + 1800) / 600)):
        xx = ini - 900 + k * 600
        cv.linha_p(ponto(xx, 0), ponto(xx + 300, -250), "fino", cor=CINZA)

    # ---- rotulos de ambiente no plano de corte
    for ambs, z0 in ((T, 0), (S, pj.NIVEL_SUPERIOR)):
        vistos = set()
        u = ini
        while u < fim:
            x, y = (u, coord) if eixo == "H" else (coord, u)
            a = _amb_em(ambs, x + 1, y + 1)
            if a and a.cod not in vistos:
                vistos.add(a.cod)
                p = ponto(a.x + a.w / 2 if eixo == "H" else a.y + a.h / 2,
                          z0 + pj.PE_DIREITO * 0.55)
                cv.texto_p(p, a.nome, TXT["min"], "middle", cor=CINZA)
            u += passo

    # ---- cotas verticais
    niveis = [-RADIER, 0, pj.PE_DIREITO, pj.NIVEL_SUPERIOR,
              pj.NIVEL_SUPERIOR + pj.PE_DIREITO, PLATIBANDA_2PAV]
    an.cadeia(cv, vw, niveis, fim, "V", 16)
    for z in niveis:
        an.nivel(cv, vw, P(ini - 700, z), z)


def cortes() -> Canvas:
    cv = base("CORTES AA E BB", "1:60", "06", notas=[
        f"Pe-direito acabado {pj.PE_DIREITO} mm; piso a piso {pj.PISO_A_PISO} mm.",
        f"Topo da platibanda +{PLATIBANDA_2PAV/1000:.3f} m (dois pavimentos) e "
        f"+{PLATIBANDA_1PAV/1000:.3f} m (um pavimento) — H.",
        f"Fundacao em radier {RADIER} mm, fck 30 MPa, aco CA-50 (H).",
        "Vedacao em Light Steel Frame; vaos grandes em perfis metalicos estruturais.",
    ])
    x0, y0, x1, y1 = _extremos(pj.TERREO)

    vwA = View(60, 80, 240, x0, 0)
    _desenhar_corte(cv, vwA, "H", 16_200, "A", x0, x1)
    an.titulo_desenho(cv, (80, 262), "1", "CORTE AA — TRANSVERSAL", "1:60")

    vwB = View(60, 80, 490, y0, 0)
    _desenhar_corte(cv, vwB, "V", 7_500, "B", y0, y1)
    an.titulo_desenho(cv, (80, 512), "2", "CORTE BB — LONGITUDINAL", "1:60")
    an.escala_grafica(cv, (80, 528), vwB, 2_000, 5)
    return cv


# =========================================================================
# FACHADAS
# =========================================================================
def _skyline(eixo: str, ini: int, fim: int, fixo_min: bool):
    """Perfil de alturas ao longo do eixo do desenho, passo 300 mm."""
    T, S = pj.TERREO, pj.SUPERIOR
    passo = 300
    perfil = []
    u = ini
    while u < fim:
        alt = 0
        for a in (T + S):
            if eixo == "H":
                dentro = a.x <= u < a.x + a.w
            else:
                dentro = a.y <= u < a.y + a.h
            if dentro:
                alt = max(alt, PLATIBANDA_2PAV if a.pav == "S" else PLATIBANDA_1PAV)
        perfil.append((u, u + passo, alt))
        u += passo
    return perfil


def _na_face(pav: str, x: int, y: int, ori: str, face_dir: str) -> bool:
    """O vao esta numa parede externa voltada para a face pedida?"""
    ambs = pj.TERREO if pav == "T" else pj.SUPERIOR
    d = 300
    if ori == "H":
        sul, norte = _dentro(ambs, x, y - d), _dentro(ambs, x, y + d)
        return (face_dir == "S" and norte and not sul) or \
               (face_dir == "N" and sul and not norte)
    oeste, leste = _dentro(ambs, x - d, y), _dentro(ambs, x + d, y)
    return (face_dir == "O" and leste and not oeste) or \
           (face_dir == "L" and oeste and not leste)


def _fachada(cv: Canvas, vw: View, eixo: str, ini: int, fim: int,
             nome: str, face: str, face_dir: str = "S") -> None:
    pat = cv.hachura("fach", espac=3.2, ang=0, w=0.05, cor="#ddd")
    perfil = _skyline(eixo, ini, fim, True)
    # massa da edificacao
    for u0, u1, alt in perfil:
        if alt <= 0:
            continue
        cv.poli_p([vw.pt(P(u0, 0)), vw.pt(P(u1, 0)), vw.pt(P(u1, alt)), vw.pt(P(u0, alt))],
                  "hachura", fechado=True, preenche=f"url(#{pat})", cor="#eee")
    # contorno
    pts = []
    ant = 0
    for u0, u1, alt in perfil:
        if alt != ant:
            pts.append(vw.pt(P(u0, ant)))
            pts.append(vw.pt(P(u0, alt)))
            ant = alt
        pts.append(vw.pt(P(u1, alt)))
    cv.poli_p(pts, "vista")
    # linha de terreno
    cv.linha_p(vw.pt(P(ini - 1_200, 0)), vw.pt(P(fim + 1_200, 0)), "corte")

    # ---- esquadrias visiveis nesta fachada
    ori = "H" if eixo == "H" else "V"
    for tipo, x, y, o, pav in pj.VAOS:
        if o != ori:
            continue
        lg, al, pe, _ = pj.ESQUADRIAS[tipo]
        u = x if eixo == "H" else y
        if not (ini <= u <= fim):
            continue
        if not _na_face(pav, x, y, o, face_dir):
            continue
        z0 = (pj.NIVEL_SUPERIOR if pav == "S" else 0) + pe
        cv.poli_p([vw.pt(P(u - lg / 2, z0)), vw.pt(P(u + lg / 2, z0)),
                   vw.pt(P(u + lg / 2, z0 + al)), vw.pt(P(u - lg / 2, z0 + al))],
                  "vista", fechado=True, preenche="#eaf2f8")
        if tipo.startswith(("J", "PV")):
            cv.linha_p(vw.pt(P(u - lg / 2, z0 + al * 0.5)),
                       vw.pt(P(u + lg / 2, z0 + al * 0.5)), "fino", cor=CINZA)
        cv.texto_p(vw.pt(P(u, z0 + al / 2)), tipo, TXT["micro"], "middle", cor=CINZA)

    # ---- muro lateral / de fundo
    if face != "frontal":
        cv.poli_p([vw.pt(P(ini - 1_200, 0)), vw.pt(P(ini, 0)),
                   vw.pt(P(ini, pj.ALT_MURO)), vw.pt(P(ini - 1_200, pj.ALT_MURO))],
                  "fino", fechado=True, preenche="#f6f6f6", cor=CINZA)

    an.cadeia(cv, vw, [0, pj.PE_DIREITO, pj.NIVEL_SUPERIOR,
                       pj.NIVEL_SUPERIOR + pj.PE_DIREITO, PLATIBANDA_2PAV],
              fim, "V", 12)
    cv.texto_p(vw.pt(P((ini + fim) / 2, -1_400)), nome, TXT["peq"], "middle", peso="bold")


def fachadas() -> Canvas:
    cv = base("FACHADAS", "1:80", "07", notas=[
        "Maximo de 3 familias de acabamento: mineral claro, aluminio grafite, aluminio amadeirado.",
        "Vidro reduzido na frente e concentrado no social posterior.",
        "Condensadoras concentradas na faixa tecnica lateral direita, ocultas por painel ventilado h=1.800 mm.",
        "Muros laterais e de fundo h = 2.200 mm; sem muro frontal.",
    ])
    x0, y0, x1, y1 = _extremos(pj.TERREO)

    _fachada(cv, View(80, 60, 160, x0, 0), "H", x0, x1, "FACHADA FRONTAL (SUL)", "frontal", "S")
    _fachada(cv, View(80, 60, 330, x0, 0), "H", x0, x1, "FACHADA POSTERIOR (NORTE)", "posterior", "N")
    _fachada(cv, View(80, 60, 500, y0, 0), "V", y0, y1,
             "FACHADA LATERAL ESQUERDA (OESTE)", "lateral", "O")
    _fachada(cv, View(80, 400, 500, y0, 0), "V", y0, y1,
             "FACHADA LATERAL DIREITA (LESTE)", "lateral", "L")

    an.titulo_desenho(cv, (400, 170), "1", "FACHADAS", "1:80")
    an.escala_grafica(cv, (400, 190), View(80, 0, 0), 2_000, 5)
    return cv


# =========================================================================
# CROQUI AXONOMETRICO
# =========================================================================
def _iso(x, y, z, ox, oy, k):
    c, s = math.cos(math.radians(30)), math.sin(math.radians(30))
    return (ox + (x - y) * c * k, oy - ((x + y) * s + z) * k)


def axonometria() -> Canvas:
    cv = base("CROQUI AXONOMETRICO E ZONEAMENTO", "s/ escala", "08", notas=[
        "Croqui de estudo volumetrico — sem escala, nao cotado.",
        "Cores por zona funcional: social, intimo, servico, apoio e circulacao.",
        "Volume superior em balanco sobre o deck lateral — estrutura metalica especifica (H).",
    ])
    k = 0.0125
    ox, oy = 330, 470
    cores = {
        "T-SOC": "#f6c453", "T-GOU": "#f6c453", "T-HAL": "#dfe6e9", "T-COR": "#b2bec3",
        "T-COZ": "#74b9ff", "T-LAV": "#74b9ff", "T-DML": "#74b9ff", "T-OFI": "#74b9ff",
        "T-GAR": "#b2bec3", "T-REV": "#a29bfe", "T-BWC": "#dfe6e9",
        "S-S02": "#a29bfe", "S-S03": "#a29bfe", "S-MAS": "#a29bfe", "S-HAL": "#dfe6e9",
    }
    blocos = [(a, 0, pj.PE_DIREITO) for a in pj.TERREO] + \
             [(a, pj.NIVEL_SUPERIOR, pj.PE_DIREITO) for a in pj.SUPERIOR]
    blocos.sort(key=lambda t: (-(t[0].x + t[0].y + t[0].w + t[0].h), t[1]))

    for a, z0, h in blocos:
        z1 = z0 + h
        cor = cores.get(a.cod, "#dfe6e9")
        topo = [_iso(a.x, a.y, z1, ox, oy, k), _iso(a.x + a.w, a.y, z1, ox, oy, k),
                _iso(a.x + a.w, a.y + a.h, z1, ox, oy, k), _iso(a.x, a.y + a.h, z1, ox, oy, k)]
        esq = [_iso(a.x, a.y, z0, ox, oy, k), _iso(a.x, a.y + a.h, z0, ox, oy, k),
               _iso(a.x, a.y + a.h, z1, ox, oy, k), _iso(a.x, a.y, z1, ox, oy, k)]
        fre = [_iso(a.x, a.y, z0, ox, oy, k), _iso(a.x + a.w, a.y, z0, ox, oy, k),
               _iso(a.x + a.w, a.y, z1, ox, oy, k), _iso(a.x, a.y, z1, ox, oy, k)]
        cv.poli_p(esq, "vista", fechado=True, preenche=_escurece(cor, 0.80))
        cv.poli_p(fre, "vista", fechado=True, preenche=_escurece(cor, 0.90))
        cv.poli_p(topo, "vista", fechado=True, preenche=cor)
        c = _iso(a.cx, a.cy, z1, ox, oy, k)
        cv.texto_p(c, a.nome, TXT["micro"], "middle", cor="#222")

    # piscina
    ps = pj.PISCINA
    pisc = [_iso(ps["x"], ps["y"], 0, ox, oy, k), _iso(ps["x"] + ps["w"], ps["y"], 0, ox, oy, k),
            _iso(ps["x"] + ps["w"], ps["y"] + ps["h"], 0, ox, oy, k),
            _iso(ps["x"], ps["y"] + ps["h"], 0, ox, oy, k)]
    cv.poli_p(pisc, "vista", fechado=True, preenche="#aed6f1")
    cv.texto_p(_iso(ps["x"] + ps["w"] / 2, ps["y"] + ps["h"] / 2, 0, ox, oy, k),
               "PISCINA", TXT["micro"], "middle")

    # lote
    lot = [_iso(0, 0, 0, ox, oy, k), _iso(pj.LOTE_L, 0, 0, ox, oy, k),
           _iso(pj.LOTE_L, pj.LOTE_P, 0, ox, oy, k), _iso(0, pj.LOTE_P, 0, ox, oy, k)]
    cv.poli_p(lot, "cota", fechado=True, preenche="none", cor=CINZA)

    # legenda de zonas
    zonas = [("#f6c453", "SOCIAL — estar/jantar e gourmet"),
             ("#a29bfe", "INTIMO — suites e quarto reversivel"),
             ("#74b9ff", "SERVICO — cozinha, lavanderia, oficina, DML"),
             ("#b2bec3", "APOIO — garagem e core"),
             ("#dfe6e9", "CIRCULACAO — hall e halls de pavimento")]
    for i, (c, t) in enumerate(zonas):
        y = 100 + i * 7
        cv.poli_p([(640, y), (652, y), (652, y + 5), (640, y + 5)], "fino",
                  fechado=True, preenche=c)
        cv.texto_p((656, y + 2.5), t, TXT["min"], "start")
    cv.texto_p((640, 92), "ZONEAMENTO FUNCIONAL", TXT["peq"], "start", peso="bold")
    an.titulo_desenho(cv, (60, 470), "1", "CROQUI AXONOMETRICO", "s/ escala")
    return cv


def _escurece(hexcor: str, f: float) -> str:
    h = hexcor.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))
