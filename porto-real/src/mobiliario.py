"""
Mobiliario fixo e equipamentos.

A aula de Desenho Tecnico anexada define o criterio: o mobiliario fixo
(pecas de banheiro, cozinha e area de servico) e OBRIGATORIO em planta baixa
porque indica a posicao das instalacoes de agua e esgoto. O mobiliario solto
e opcional e aqui aparece apenas na planta de layout.
"""
from __future__ import annotations

import math

import projeto as pj
from core import P, Canvas, View, TXT, CINZA


def _ret(cv, vw, x, y, w, h, estilo="fino", preenche="none"):
    cv.poli_p([vw.pt(P(x, y)), vw.pt(P(x + w, y)),
               vw.pt(P(x + w, y + h)), vw.pt(P(x, y + h))],
              estilo, fechado=True, preenche=preenche)


def _rot(cv, vw, cx, cy, rx, ry, estilo="fino"):
    a = vw.pt(P(cx, cy))
    cv.circ_p(a, vw.d(rx), estilo)


# --------------------------------------------------------------- pecas
def vaso(cv, vw, x, y, rot=0):
    """Bacia sanitaria 400 x 650, ancorada na parede em y."""
    if rot in (0, 180):
        _ret(cv, vw, x - 200, y, 400, 150, "fino", "#fff")      # caixa acoplada
        cv.circ_p(vw.pt(P(x, y + 380)), vw.d(200), "fino")
    else:
        _ret(cv, vw, x, y - 200, 150, 400, "fino", "#fff")
        cv.circ_p(vw.pt(P(x + 380, y)), vw.d(200), "fino")


def lavatorio(cv, vw, x, y, w=600, h=450):
    _ret(cv, vw, x, y, w, h, "fino", "#fff")
    cv.circ_p(vw.pt(P(x + w / 2, y + h / 2)), vw.d(min(w, h) * 0.30), "fino")


def box(cv, vw, x, y, w=900, h=900):
    _ret(cv, vw, x, y, w, h, "fino")
    c = vw.pt(P(x + w / 2, y + h / 2))
    cv.circ_p(c, vw.d(90), "fino")
    cv.linha_p(vw.pt(P(x, y)), vw.pt(P(x + w, y + h)), "fino", cor=CINZA)


def bancada(cv, vw, x, y, w, h, cubas=1, cooktop=False):
    """Bancada de 600 mm de profundidade, altura 900 (nao aparece em planta)."""
    _ret(cv, vw, x, y, w, h, "vista", "#f4f4f4")
    if cubas:
        passo = w / (cubas + 1)
        for i in range(1, cubas + 1):
            cx = x + passo * i
            _ret(cv, vw, cx - 200, y + h / 2 - 175, 400, 350, "fino", "#fff")
    if cooktop:
        cx = x + w * 0.72
        _ret(cv, vw, cx - 300, y + h / 2 - 250, 600, 500, "fino", "#fff")
        for dx, dy in ((-150, -120), (150, -120), (-150, 120), (150, 120)):
            cv.circ_p(vw.pt(P(cx + dx, y + h / 2 + dy)), vw.d(90), "fino")


def geladeira(cv, vw, x, y, w=900, h=750):
    _ret(cv, vw, x, y, w, h, "fino")
    cv.linha_p(vw.pt(P(x + w * 0.5, y)), vw.pt(P(x + w * 0.5, y + h)), "fino", cor=CINZA)
    cv.texto_p(vw.pt(P(x + w / 2, y + h / 2)), "REF", TXT["micro"], "middle", cor=CINZA)


def tanque(cv, vw, x, y, w=600, h=550):
    _ret(cv, vw, x, y, w, h, "fino", "#fff")
    _ret(cv, vw, x + 60, y + 60, w - 120, h - 120, "fino")


def maquina(cv, vw, x, y, s=600, rotulo="ML"):
    _ret(cv, vw, x, y, s, s, "fino")
    cv.circ_p(vw.pt(P(x + s / 2, y + s / 2)), vw.d(s * 0.32), "fino")
    cv.texto_p(vw.pt(P(x + s / 2, y + s * 0.12)), rotulo, TXT["micro"], "middle", cor=CINZA)


def cama(cv, vw, x, y, w=1600, h=2000):
    _ret(cv, vw, x, y, w, h, "fino", "#fafafa")
    _ret(cv, vw, x, y + h - 450, w, 450, "fino")           # travesseiros
    cv.linha_p(vw.pt(P(x, y + h - 700)), vw.pt(P(x + w, y + h - 700)), "fino", cor=CINZA)


def sofa(cv, vw, x, y, w=2400, h=900):
    _ret(cv, vw, x, y, w, h, "fino", "#fafafa")
    _ret(cv, vw, x, y + h - 250, w, 250, "fino")


def mesa(cv, vw, cx, cy, w=1800, h=900, lugares=6):
    _ret(cv, vw, cx - w / 2, cy - h / 2, w, h, "fino", "#fff")
    n = lugares // 2
    for i in range(n):
        xx = cx - w / 2 + w * (i + 0.5) / n
        _ret(cv, vw, xx - 220, cy + h / 2 + 60, 440, 440, "fino")
        _ret(cv, vw, xx - 220, cy - h / 2 - 500, 440, 440, "fino")


def carro(cv, vw, x, y, w=1900, h=4700):
    cv.poli_p([vw.pt(P(x + w * .12, y)), vw.pt(P(x + w * .88, y)),
               vw.pt(P(x + w, y + h * .22)), vw.pt(P(x + w, y + h * .80)),
               vw.pt(P(x + w * .86, y + h)), vw.pt(P(x + w * .14, y + h)),
               vw.pt(P(x, y + h * .80)), vw.pt(P(x, y + h * .22))],
              "fino", fechado=True, preenche="#fbfbfb", cor=CINZA)
    _ret(cv, vw, x + w * .16, y + h * .30, w * .68, h * .30, "fino")


def escada_u(cv, vw, e=pj.ESCADA):
    """Escada em U: dois lances de 1.000 mm e patamar, com seta de subida."""
    x, y, w, h = e["x"], e["y"], e["w"], e["h"]
    lar, piso, pat = e["larg_lance"], e["piso"], e["patamar"]
    n_lance = 8
    # lance ascendente (esquerda, subindo em +Y)
    for i in range(n_lance + 1):
        yy = y + 300 + i * piso
        cv.linha_p(vw.pt(P(x + 150, yy)), vw.pt(P(x + 150 + lar, yy)), "fino")
    # patamar
    _ret(cv, vw, x + 150, y + 300 + n_lance * piso, lar * 2 + 100, pat, "fino")
    # lance descendente (direita, subindo em -Y)
    for i in range(n_lance + 1):
        yy = y + 300 + n_lance * piso + pat - i * piso
        cv.linha_p(vw.pt(P(x + 250 + lar, yy)), vw.pt(P(x + 250 + 2 * lar, yy)), "fino")
    # seta de subida
    a = vw.pt(P(x + 150 + lar / 2, y + 450))
    b = vw.pt(P(x + 150 + lar / 2, y + 300 + n_lance * piso - 150))
    cv.linha_p(a, b, "fino")
    cv.poli_p([b, (b[0] - 1.4, b[1] + 3.2), (b[0] + 1.4, b[1] + 3.2)], "fino",
              fechado=True, preenche="#000")
    cv.texto_p((a[0] + 2.2, a[1] + 2.0), "SOBE", TXT["micro"], "start", cor=CINZA)


def piscina(cv, vw, ps=pj.PISCINA):
    x, y, w, h = ps["x"], ps["y"], ps["w"], ps["h"]
    _ret(cv, vw, x, y, w, h, "corte2", "#e8f4fb")
    _ret(cv, vw, x + 150, y + 150, w - 300, h - 300, "fino")
    # prainha
    pw = ps["prainha_w"]
    cv.linha_p(vw.pt(P(x + pw, y)), vw.pt(P(x + pw, y + h)), "fino")
    cv.texto_p(vw.pt(P(x + pw / 2, y + h / 2)), "PRAINHA", TXT["micro"], "middle",
               rot=90, cor="#0a6")
    cv.texto_p(vw.pt(P(x + pw + (w - pw) / 2, y + h / 2)),
               f"PISCINA  {ps['lamina_m2']:.2f} m2".replace(".", ","),
               TXT["min"], "middle", cor="#0a6")
    cv.texto_p(vw.pt(P(x + pw + (w - pw) / 2, y + h / 2 - 500)),
               f"prof. {ps['prof_principal']/1000:.3f} m".replace(".", ","),
               TXT["micro"], "middle", cor="#0a6")


# ------------------------------------------------------- mapa por ambiente
def desenhar(cv: Canvas, vw: View, pav: str, layout: bool = False) -> None:
    """Mobiliario fixo (sempre) e solto (apenas na planta de layout)."""
    _desenhar_do_modelo(cv, vw, pav)
    if pav == "T":

        # bancadas lidas do modelo (projeto.BANCADAS)
        for b in pj.BANCADAS:
            if b["amb"] in ("T-COZ", "T-GOU", "T-OFI"):
                bancada(cv, vw, b["x"], b["y"], b["w"], b["h"],
                        cubas=b["cubas"], cooktop=b["cooktop"])
        # varal coberto no patio lateral
        # varal coberto no patio lateral
        for i in range(4):
            yv = 19_800 + i * 600
            cv.linha_p(vw.pt(P(13_200, yv)), vw.pt(P(16_200, yv)), "fino", cor=CINZA)
        cv.texto_p(vw.pt(P(14_700, 22_400)), "VARAL COBERTO", TXT["micro"], "middle", cor=CINZA)

        # oficina: bancada 2400x600
        
        escada_u(cv, vw)
        if layout:
            carro(cv, vw, 3_000, 8_000)
            carro(cv, vw, 5_600, 8_000)
            sofa(cv, vw, 5_700, 13_600, 2_400, 900)
            mesa(cv, vw, 7_500, 17_400, 1_800, 900, 6)
            mesa(cv, vw, 7_500, 23_400, 2_400, 1_000, 8)
            cama(cv, vw, 10_500, 7_700, 1_600, 2_000)
    else:
        if layout:
            cama(cv, vw, 5_000, 14_600, 1_600, 2_000)
            cama(cv, vw, 5_000, 19_400, 1_600, 2_000)
            cama(cv, vw, 8_700, 20_400, 1_800, 2_100)


def _desenhar_do_modelo(cv: Canvas, vw: View, pav: str) -> None:
    """Loucas, equipamentos e armarios lidos de projeto — nao mais do desenho."""
    alvo = ("T-", "S-")
    for p in pj.LOUCAS:
        if not p["amb"].startswith("T-" if pav == "T" else "S-"):
            continue
        t = p["tipo"]
        if t == "vaso":
            vaso(cv, vw, p["x"] + p["w"] / 2, p["y"])
        elif t == "lavatorio":
            lavatorio(cv, vw, p["x"], p["y"], p["w"], p["h"])
        elif t == "box":
            box(cv, vw, p["x"], p["y"], p["w"], p["h"])
        elif t == "tanque":
            tanque(cv, vw, p["x"], p["y"], p["w"], p["h"])
    for e in pj.EQUIPAMENTOS:
        if not e["amb"].startswith("T-" if pav == "T" else "S-"):
            continue
        if e["tipo"] == "geladeira":
            geladeira(cv, vw, e["x"], e["y"], e["w"], e["h"])
        else:
            maquina(cv, vw, e["x"], e["y"], e["w"],
                    "ML" if e["tipo"] == "lavadora" else "SEC")
    for a in pj.ARMARIOS:
        if not a["amb"].startswith("T-" if pav == "T" else "S-"):
            continue
        _ret(cv, vw, a["x"], a["y"], a["w"], a["h"], "fino", "#f1ede4")
