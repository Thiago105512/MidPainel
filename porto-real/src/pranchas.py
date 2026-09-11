"""Geradores de prancha — implantacao, plantas baixas e cobertura."""
from __future__ import annotations

import math

import projeto as pj
import elementos as el
import mobiliario as mob
import anotacao as an
from core import P, Canvas, View, TXT, CINZA, PRETO

TOTAL_PRANCHAS = "10"


def base(titulo: str, escala: str, prancha: str, formato: str = "A1",
         notas: list[str] | None = None) -> Canvas:
    cv = Canvas(formato)
    cv.moldura()
    an.carimbo(cv, titulo, escala, prancha, TOTAL_PRANCHAS, notas)
    return cv


def _ambientes(pav: str, abertos: bool = True):
    if pav == "T":
        return pj.TERREO + (pj.TERREO_ABERTO if abertos else [])
    return pj.SUPERIOR + (pj.SUPERIOR_ABERTO if abertos else [])


def _extremos(ambs):
    return (min(a.x for a in ambs), min(a.y for a in ambs),
            max(a.x + a.w for a in ambs), max(a.y + a.h for a in ambs))


# =========================================================================
# PR-02 / PR-03 — PLANTAS BAIXAS
# =========================================================================
def planta(pav: str, prancha: str, layout: bool = False) -> Canvas:
    nome = "PLANTA BAIXA — PAVIMENTO TERREO" if pav == "T" else "PLANTA BAIXA — PAVIMENTO SUPERIOR"
    if layout:
        nome = nome.replace("PLANTA BAIXA", "PLANTA DE LAYOUT")
    cv = base(nome, "1:50", prancha, notas=[
        "Dimensoes em milimetros; cotas de nivel em metros.",
        "Malha modular 600 mm; cotas eixo a eixo.",
        "Parede externa 150 mm / divisoria interna 100 mm (H).",
        "Mobiliario fixo indica pontos de agua e esgoto (NBR 6492).",
    ])
    vw = View(50, 78, 476, 2_400, 7_200)

    fechados = pj.TERREO if pav == "T" else pj.SUPERIOR
    abertos = pj.TERREO_ABERTO if pav == "T" else pj.SUPERIOR_ABERTO
    paredes = el.derivar_paredes(fechados)
    vaos = list(el.vaos_do_pavimento(pav))

    # ---- pisos e areas abertas
    pat_deck = cv.hachura("deck", espac=1.4, ang=0, w=0.08, cor="#bbb")
    for a in abertos:
        cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                   vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                  "fino", fechado=True, preenche=f"url(#{pat_deck})", cor=CINZA)

    # ---- piso impermeavel dos ambientes molhados (simbologia da aula de DT)
    pat_cer = cv.hachura_dupla("ceramica", espac=2.2, w=0.05, cor="#ccc")
    for a in fechados:
        if a.molhado:
            cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                       vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                      "hachura", fechado=True, preenche=f"url(#{pat_cer})", cor="#ddd")

    # ---- elementos externos no terreo
    if pav == "T":
        mob.piscina(cv, vw)
        cm = pj.CASA_MAQUINAS
        cv.poli_p([vw.pt(P(cm["x"], cm["y"])), vw.pt(P(cm["x"] + cm["w"], cm["y"])),
                   vw.pt(P(cm["x"] + cm["w"], cm["y"] + cm["h"])),
                   vw.pt(P(cm["x"], cm["y"] + cm["h"]))], "corte2", fechado=True,
                  preenche="#f7f7f7")
        cv.texto_p(vw.pt(P(cm["x"] + cm["w"] / 2, cm["y"] + cm["h"] / 2)),
                   "C. MAQ.", TXT["micro"], "middle")

    # ---- projecao do pavimento superior / da cobertura
    proj = pj.SUPERIOR + pj.SUPERIOR_ABERTO if pav == "T" else []
    for a in proj:
        cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                   vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                  "oculto", fechado=True, cor="#999")

    # ---- paredes e vaos
    el.desenhar_paredes(cv, vw, paredes, vaos)
    el.desenhar_vaos(cv, vw, paredes, vaos)

    # ---- mobiliario
    mob.desenhar(cv, vw, pav, layout=layout)

    # ---- rotulos de ambiente: nome, area e cota de nivel
    ext_faces = {"O", "L", "S", "N"}
    for a in fechados:
        c = vw.pt(P(a.cx, a.cy))
        cv.texto_p((c[0], c[1] - 3.0), a.nome, TXT["peq"], "middle", peso="bold")
        cv.texto_p((c[0], c[1] + 0.6), f"{a.area_mod:.2f} m2".replace(".", ","),
                   TXT["min"], "middle")
        cv.texto_p((c[0], c[1] + 3.8), a.cod, TXT["micro"], "middle", cor=CINZA)
    for a in abertos:
        c = vw.pt(P(a.cx, a.cy))
        cv.texto_p((c[0], c[1] - 1.6), a.nome, TXT["min"], "middle", cor=CINZA)
        cv.texto_p((c[0], c[1] + 1.8), f"{a.area_mod:.2f} m2".replace(".", ","),
                   TXT["micro"], "middle", cor=CINZA)

    # ---- cotas de nivel
    if pav == "T":
        an.nivel(cv, vw, P(5_400, 10_200), 0)
        an.nivel(cv, vw, P(7_500, 16_200), 0)
        an.nivel(cv, vw, P(7_500, 22_800), 0)
        an.nivel(cv, vw, P(7_800, 28_800), -150)
    else:
        an.nivel(cv, vw, P(5_100, 15_600), pj.NIVEL_SUPERIOR)
        an.nivel(cv, vw, P(13_200, 18_600), pj.NIVEL_SUPERIOR)

    # ---- cadeias de cotas (parciais + totais, externas ao desenho)
    xs = sorted({a.x for a in fechados} | {a.x + a.w for a in fechados})
    ys = sorted({a.y for a in fechados} | {a.y + a.h for a in fechados})
    x0, y0, x1, y1 = _extremos(fechados)
    an.cadeia(cv, vw, xs, y0, "H", 14)          # parciais, abaixo
    an.cadeia(cv, vw, [x0, x1], y0, "H", 24)    # total, abaixo
    an.cadeia(cv, vw, ys, x0, "V", -14)         # parciais, a esquerda
    an.cadeia(cv, vw, [y0, y1], x0, "V", -24)   # total, a esquerda
    an.cadeia(cv, vw, ys, x1, "V", 14)          # parciais, a direita
    an.cadeia(cv, vw, xs, y1, "H", -14)         # parciais, acima

    # ---- eixos modulares estruturais
    eixos_x = [2_400, 8_400, 9_600, 12_000, 16_800]
    eixos_y = [7_200, 13_200, 19_200, 26_400]
    for i, xv in enumerate(eixos_x):
        an.eixo_modular(cv, vw, xv, y0, y1, "V", chr(65 + i))
    for i, yv in enumerate(eixos_y):
        an.eixo_modular(cv, vw, yv, x0, x1, "H", str(i + 1))

    # ---- indicacao dos cortes
    if pav == "T":
        an.marca_corte(cv, vw, P(1_200, 16_200), P(18_000, 16_200), "A")
        an.marca_corte(cv, vw, P(7_500, 5_400), P(7_500, 31_200), "B")

    an.norte(cv, (800, 46))

    # ---- quadro de areas do pavimento
    linhas = [[a.cod, a.nome, f"{a.w}x{a.h}", f"{a.area_mod:.2f}".replace(".", ",")]
              for a in fechados]
    linhas.append(["", "TOTAL FECHADO", "",
                   f"{sum(a.area_mod for a in fechados):.2f}".replace(".", ",")])
    for a in abertos:
        linhas.append([a.cod, a.nome + " (aberta)", f"{a.w}x{a.h}",
                       f"{a.area_mod:.2f}".replace(".", ",")])
    fim = _tabela(cv, (470, 40), f"QUADRO DE AREAS — PAVIMENTO {'TERREO' if pav=='T' else 'SUPERIOR'}",
                  ["COD", "AMBIENTE", "MODULO (mm)", "AREA (m2)"], linhas,
                  larguras=[16, 58, 32, 24])

    # ---- mapa de esquadrias do pavimento
    usados = {}
    for v in vaos:
        usados[v["tipo"]] = usados.get(v["tipo"], 0) + 1
    linhas = []
    for t, q in sorted(usados.items()):
        lg, al, pe, desc = pj.ESQUADRIAS[t]
        linhas.append([t, f"{lg}x{al}", str(pe), str(q), desc[:46]])
    fim2 = _tabela(cv, (470, fim + 18), "MAPA DE ESQUADRIAS DO PAVIMENTO",
                   ["REF", "VAO (mm)", "PEIT.", "QTD", "TIPO"], linhas,
                   larguras=[14, 26, 14, 12, 98])

    # ---- legenda de convencoes
    _legenda_convencoes(cv, (470, fim2 + 18))

    an.titulo_desenho(cv, (78, 520), "1", nome.split("—")[-1].strip(), "1:50")
    an.escala_grafica(cv, (78, 536), vw, 1_000, 5)
    return cv


def _legenda_convencoes(cv: Canvas, pos) -> None:
    x, y = pos
    cv.texto_p((x, y - 3), "LEGENDA E CONVENCOES (NBR 6492 / 8403)", TXT["peq"],
               "start", peso="bold")
    itens = [
        ("corte", "Elemento seccionado pelo plano de corte (h = 1,50 m)"),
        ("vista", "Aresta vista / folha de esquadria"),
        ("fino", "Mobiliario fixo, equipamentos e simbologia"),
        ("oculto", "Projecao do pavimento superior e da cobertura"),
        ("eixo", "Eixo modular e linha de corte"),
        ("cota", "Linha de cota e linha auxiliar"),
    ]
    for i, (est, txt) in enumerate(itens):
        yy = y + 5 + i * 5.0
        cv.linha_p((x, yy), (x + 16, yy), est, cor="#0a6" if est == "eixo" else None)
        cv.texto_p((x + 20, yy), txt, TXT["micro"], "start")


# =========================================================================
# PR-01 — IMPLANTACAO E SITUACAO
# =========================================================================
def implantacao() -> Canvas:
    cv = base("IMPLANTACAO E SITUACAO", "1:200", "01", notas=[
        "Lote 20.000 x 40.000 mm = 800,00 m2.",
        "Recuos: frontal 7.200 / lateral esq. 2.400 / faixa tecnica dir. 3.200 / fundo 13.600 mm.",
        "Parametros do SU16 Tarumã/Tarumã-Açu sao hipoteses (H) — pendente certidao de uso do solo.",
        "Sem muro frontal; muros laterais e de fundo h = 2.200 mm.",
    ])
    vw = View(200, 120, 500, 0, 0)

    # ---- lote
    L, Pf = pj.LOTE_L, pj.LOTE_P
    cv.poli_p([vw.pt(P(0, 0)), vw.pt(P(L, 0)), vw.pt(P(L, Pf)), vw.pt(P(0, Pf))],
              "corte", fechado=True, preenche="#fcfcfc")

    # ---- faixa de recuos (area nao edificavel)
    pat = cv.hachura("recuo", espac=1.6, ang=45, w=0.05, cor="#e0a")
    cv.poli_p([vw.pt(P(0, 0)), vw.pt(P(L, 0)), vw.pt(P(L, pj.RECUO_FRENTE)),
               vw.pt(P(0, pj.RECUO_FRENTE))], "cota", fechado=True,
              preenche=f"url(#{pat})", cor="#e0a")

    # ---- faixa tecnica lateral
    ft = pj.FAIXA_TECNICA
    pat2 = cv.hachura("ftec", espac=1.4, ang=-45, w=0.05, cor="#09a")
    cv.poli_p([vw.pt(P(ft["x"], 0)), vw.pt(P(ft["x"] + ft["w"], 0)),
               vw.pt(P(ft["x"] + ft["w"], Pf)), vw.pt(P(ft["x"], Pf))],
              "cota", fechado=True, preenche=f"url(#{pat2})", cor="#09a")
    cv.texto_p(vw.pt(P(ft["x"] + ft["w"] / 2, Pf * 0.62)), "FAIXA TECNICA 3.200",
               TXT["min"], "middle", rot=90, cor="#09a")

    # ---- projecao da edificacao
    for a in pj.TERREO:
        cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                   vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                  "vista", fechado=True, preenche="#ededed", cor="#666")
    for a in pj.SUPERIOR + pj.SUPERIOR_ABERTO:
        cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                   vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                  "oculto", fechado=True, preenche="none", cor="#c00")
    x0, y0, x1, y1 = _extremos(pj.TERREO)
    cv.poli_p([vw.pt(P(x0, y0)), vw.pt(P(x1, y0)), vw.pt(P(x1, y1)), vw.pt(P(x0, y1))],
              "corte", fechado=True, preenche="none")

    # ---- piscina, deck, casa de maquinas
    mob.piscina(cv, vw)
    dk = pj.DECK
    cv.poli_p([vw.pt(P(dk["x"], dk["y"])), vw.pt(P(dk["x"] + dk["w"], dk["y"])),
               vw.pt(P(dk["x"] + dk["w"], dk["y"] + dk["h"])),
               vw.pt(P(dk["x"], dk["y"] + dk["h"]))], "fino", fechado=True,
              preenche="none", cor="#0a6")

    # ---- acesso de veiculos e pedestres
    cv.poli_p([vw.pt(P(2_400, 0)), vw.pt(P(8_400, 0)), vw.pt(P(8_400, 7_200)),
               vw.pt(P(2_400, 7_200))], "fino", fechado=True, preenche="#f5f5f5", cor=CINZA)
    cv.texto_p(vw.pt(P(5_400, 3_600)), "ACESSO DE VEICULOS", TXT["micro"], "middle", cor=CINZA)
    cv.texto_p(vw.pt(P(9_300, 3_600)), "PEDESTRES", TXT["micro"], "middle", cor=CINZA)

    # ---- cotas do lote e recuos
    an.cadeia(cv, vw, [0, 2_400, 8_400, 16_800, L], 0, "H", 12)
    an.cadeia(cv, vw, [0, L], 0, "H", 22)
    an.cadeia(cv, vw, [0, 7_200, 13_200, 19_200, 26_400, Pf], 0, "V", -12)
    an.cadeia(cv, vw, [0, Pf], 0, "V", -22)

    an.norte(cv, (735, 92))
    an.titulo_desenho(cv, (120, 528), "1", "IMPLANTACAO", "1:200")
    an.escala_grafica(cv, (120, 544), vw, 5_000, 4)

    # ---- quadro de verificacao urbanistica
    _tabela(cv, (430, 120), "VERIFICACAO URBANISTICA (H)",
            ["PARAMETRO", "PROJETO", "LIMITE", ""],
            [[n, v, l, "OK" if ok else "REVER"] for n, v, l, ok in pj.verificacao_urbanistica()],
            larguras=[62, 40, 48, 18])
    return cv


# =========================================================================
# PR-05 — COBERTURA
# =========================================================================
def cobertura() -> Canvas:
    cb = pj.COBERTURA
    cv = base("PLANTA DE COBERTURA", "1:100", "05", notas=[
        f"Painel sanduiche PIR {pj.ESP_PAINEL_PIR} mm; inclinacao {cb['inclinacao']*100:.0f} %.",
        f"Calha externa {cb['calha_l']}x{cb['calha_h']} mm; {cb['descidas']} descidas DN{cb['dn_descida']}.",
        f"Contribuicao {cb['area_contrib_m2']:.2f} m2 | i = {cb['intensidade_mm_h']} mm/h | "
        f"C = {cb['coef_escoamento']} -> Q = {cb['vazao_total_ls']:.4f} L/s.",
        "Reservatorio de retencao pluvial 2.500 L — irrigacao e lavagem, sem ligacao a rede potavel.",
    ])
    vw = View(100, 150, 470, 2_400, 7_200)

    baixos = [a for a in pj.TERREO]
    altos = pj.SUPERIOR
    pat = cv.hachura("pir", espac=2.6, ang=0, w=0.06, cor="#ccc")

    for a in baixos:
        cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                   vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                  "fino", fechado=True, preenche=f"url(#{pat})", cor="#aaa")
    x0, y0, x1, y1 = _extremos(pj.TERREO)
    cv.poli_p([vw.pt(P(x0, y0)), vw.pt(P(x1, y0)), vw.pt(P(x1, y1)), vw.pt(P(x0, y1))],
              "corte", fechado=True, preenche="none")
    for a in altos:
        cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                   vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                  "corte2", fechado=True, preenche="#f2f2f2", cor="#666")
    ax0, ay0, ax1, ay1 = _extremos(pj.SUPERIOR)
    cv.poli_p([vw.pt(P(ax0, ay0)), vw.pt(P(ax1, ay0)), vw.pt(P(ax1, ay1)), vw.pt(P(ax0, ay1))],
              "corte", fechado=True, preenche="none")

    # ---- setas de caimento 5 %
    for (cx, cy, dx, dy) in [(5_400, 10_200, 0, -1), (4_500, 16_200, -1, 0),
                             (10_500, 23_000, 1, 0), (14_000, 19_000, 1, 0),
                             (5_000, 20_000, -1, 0), (13_200, 18_600, 1, 0)]:
        a = vw.pt(P(cx, cy))
        b = (a[0] + dx * 14, a[1] - dy * 14)
        cv.linha_p(a, b, "fino", cor="#09a")
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        for s in (2.5, -2.5):
            cv.linha_p(b, (b[0] - 3.2 * math.cos(ang + math.radians(s * 8)),
                           b[1] - 3.2 * math.sin(ang + math.radians(s * 8))), "fino", cor="#09a")
        cv.texto_p(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 - 2.2), "i=5%",
                   TXT["micro"], "middle", cor="#09a")

    # ---- calhas no perimetro e descidas pluviais
    cv.poli_p([vw.pt(P(x0, y0)), vw.pt(P(x1, y0)), vw.pt(P(x1, y1)), vw.pt(P(x0, y1))],
              "fino", fechado=True, preenche="none", cor="#09a", dash="2,1.4")
    descidas = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
    for i, (dx, dy) in enumerate(descidas, 1):
        p = vw.pt(P(dx, dy))
        cv.circ_p(p, 2.4, "vista", preenche="#fff", cor="#09a")
        cv.texto_p(p, str(i), TXT["micro"], "middle", cor="#09a")
        cv.texto_p((p[0] + 4, p[1]), f"DN{cb['dn_descida']}  {cb['vazao_total_ls']/4:.4f} L/s",
                   TXT["micro"], "start", cor="#09a")

    # ---- area tecnica da caixa d'agua
    cd = pj.CAIXA_DAGUA
    cv.poli_p([vw.pt(P(cd["x"], cd["y"])), vw.pt(P(cd["x"] + cd["w"], cd["y"])),
               vw.pt(P(cd["x"] + cd["w"], cd["y"] + cd["h"])),
               vw.pt(P(cd["x"], cd["y"] + cd["h"]))], "corte", fechado=True,
              preenche="#eef6ff", cor="#06c")
    c = vw.pt(P(cd["x"] + cd["w"] / 2, cd["y"] + cd["h"] / 2))
    cv.texto_p((c[0], c[1] - 2.4), "AREA TECNICA", TXT["micro"], "middle", cor="#06c")
    cv.texto_p((c[0], c[1] + 0.8), f"CX. {cd['volume_l']} L", TXT["min"], "middle", cor="#06c")
    cv.texto_p((c[0], c[1] + 4.0), f"{cd['carga_kg']} kg", TXT["micro"], "middle", cor="#06c")

    an.cadeia(cv, vw, [x0, ax0, ax1, x1], y0, "H", 14)
    an.cadeia(cv, vw, [y0, ay0, ay1, y1], x0, "V", -14)
    an.norte(cv, (735, 92))
    an.titulo_desenho(cv, (150, 512), "1", "COBERTURA", "1:100")
    an.escala_grafica(cv, (150, 528), vw, 2_000, 5)
    return cv


# ------------------------------------------------------------- tabelas
def _tabela(cv: Canvas, pos, titulo: str, cabec: list[str], linhas: list[list[str]],
            larguras: list[float], h_lin: float = 5.2) -> float:
    x, y = pos
    largura = sum(larguras)
    cv.texto_p((x, y - 3), titulo, TXT["peq"], "start", peso="bold")
    cv.poli_p([(x, y), (x + largura, y), (x + largura, y + h_lin),
               (x, y + h_lin)], "vista", fechado=True, preenche="#eee")
    cx = x
    for c, w in zip(cabec, larguras):
        cv.texto_p((cx + 1.5, y + h_lin / 2), c, TXT["micro"], "start", peso="bold")
        cx += w
    yy = y + h_lin
    for i, ln in enumerate(linhas):
        cv.poli_p([(x, yy), (x + largura, yy), (x + largura, yy + h_lin), (x, yy + h_lin)],
                  "cota", fechado=True, preenche="#fff" if i % 2 else "#fafafa")
        cx = x
        for c, w in zip(ln, larguras):
            cor = "#c00" if c == "REVER" else PRETO
            cv.texto_p((cx + 1.5, yy + h_lin / 2), str(c), TXT["micro"], "start", cor=cor)
            cx += w
        yy += h_lin
    cx = x
    for w in larguras[:-1]:
        cx += w
        cv.linha_p((cx, y), (cx, yy), "cota")
    return yy
