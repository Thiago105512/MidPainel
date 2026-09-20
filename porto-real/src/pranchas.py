"""Geradores de prancha — implantacao, plantas baixas e cobertura."""
from __future__ import annotations

import math

import projeto as pj
import elementos as el
import mobiliario as mob
import anotacao as an
from core import P, Canvas, View, TXT, CINZA, PRETO, MARGEM_ESQ

TOTAL_PRANCHAS = "40"


def base(titulo: str, escala: str, prancha: str, formato: str = "A1",
         notas: list[str] | None = None) -> Canvas:
    cv = Canvas(formato)
    cv.moldura()
    an.carimbo(cv, titulo, escala, prancha, TOTAL_PRANCHAS, notas)
    cv.abrir_folha()          # nada mais nesta folha sai da moldura sem ser medido
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
    vw = View(50, 78, 522, 2_400, 7_200)

    # A 1:50 os 40 m de lote dariam 800 mm de papel numa folha de 594: a planta
    # baixa nao comporta o lote inteiro, e ate R11 o excedente era simplesmente
    # emitido fora da moldura — invisivel no papel, invisivel na tela, e nunca
    # declarado. Agora e recortado de proposito e anunciado por linha de ruptura.
    fechados = pj.TERREO if pav == "T" else pj.SUPERIOR
    abertos = pj.TERREO_ABERTO if pav == "T" else pj.SUPERIOR_ABERTO
    paredes = el.derivar_paredes(fechados)
    vaos = list(el.vaos_do_pavimento(pav))

    # ---- pisos e areas abertas
    pat_deck = cv.hachura("deck", espac=1.4, ang=0, w=0.08, cor="#bbb")
    for a in abertos:
        with cv.escopo("piso", a.cod, rot=a.nome, area=f"{a.area_mod:.2f}"):
            cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                       vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                      "fino", fechado=True, preenche=f"url(#{pat_deck})", cor=CINZA)

    # ---- piso impermeavel dos ambientes molhados (simbologia da aula de DT)
    pat_cer = cv.hachura_dupla("ceramica", espac=2.2, w=0.05, cor="#ccc")
    for a in fechados:
        if a.molhado:
            with cv.escopo("piso", a.cod, rot=a.nome, molhado="sim"):
                cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                           vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                          "hachura", fechado=True, preenche=f"url(#{pat_cer})", cor="#ddd")

    # ---- elementos externos no terreo
    if pav == "T":
        mob.piscina(cv, vw)
        cm = pj.CASA_MAQUINAS
        cv.poli_p([vw.pt(P(cm["x"], cm["y"])), vw.pt(P(cm["x"] + cm["w"], cm["y"])),
                   vw.pt(P(cm["x"] + cm["w"], cm["y"] + cm["h"])),
                   vw.pt(P(cm["x"], cm["y"] + cm["h"]))], "oculto", fechado=True,
                  preenche="none", cor="#06c")
        c = vw.pt(P(cm["x"] + cm["w"] / 2, cm["y"] + cm["h"] / 2))
        cv.texto_p((c[0], c[1] - 1.6), "C. MAQ. ENTERRADA", TXT["micro"], "middle", cor="#06c")
        cv.texto_p((c[0], c[1] + 1.8), "alcapao 800x800", TXT["micro"], "middle", cor="#06c")

    # ---- projecao do pavimento superior / da cobertura
    proj = pj.SUPERIOR + pj.SUPERIOR_ABERTO if pav == "T" else []
    for a in proj:
        cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                   vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                  "oculto", fechado=True, cor="#999")

    # ---- paredes e vaos
    el.desenhar_paredes(cv, vw, paredes, vaos)
    el.desenhar_vaos(cv, vw, paredes, vaos, pav)

    # ---- divisorias internas de suite (banho e closet)
    _desenhar_subdivisoes(cv, vw, pav)

    # ---- mobiliario
    mob.desenhar(cv, vw, pav, layout=layout)

    # ---- rotulos de ambiente: nome, area e cota de nivel
    ext_faces = {"O", "L", "S", "N"}
    def _caixa(a):
        """Retangulo do ambiente em coordenadas de PAPEL — e o que a interface
        usa para realcar o ambiente inteiro, nao apenas o rotulo."""
        p0, p1 = vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y + a.h))
        return (f"{min(p0[0], p1[0]):.2f} {min(p0[1], p1[1]):.2f} "
                f"{abs(p1[0] - p0[0]):.2f} {abs(p1[1] - p0[1]):.2f}")

    for a in fechados:
        c = vw.pt(P(a.cx, a.cy))
        with cv.escopo("ambiente", a.cod, rot=a.nome, area=f"{a.area_mod:.2f}",
                       pav=pav, molhado="sim" if a.molhado else "nao",
                       larg=a.w, prof=a.h, box=_caixa(a)):
            cv.texto_p((c[0], c[1] - 3.0), a.nome, TXT["peq"], "middle", peso="bold")
            cv.texto_p((c[0], c[1] + 0.6), f"{a.area_mod:.2f} m2".replace(".", ","),
                       TXT["min"], "middle")
            cv.texto_p((c[0], c[1] + 3.8), a.cod, TXT["micro"], "middle", cor=CINZA)
    for a in abertos:
        c = vw.pt(P(a.cx, a.cy))
        with cv.escopo("ambiente", a.cod, rot=a.nome, area=f"{a.area_mod:.2f}",
                       pav=pav, aberto="sim", larg=a.w, prof=a.h, box=_caixa(a)):
            cv.texto_p((c[0], c[1] - 1.6), a.nome, TXT["min"], "middle", cor=CINZA)
            cv.texto_p((c[0], c[1] + 1.8), f"{a.area_mod:.2f} m2".replace(".", ","),
                       TXT["micro"], "middle", cor=CINZA)

    # ---- brises verticais (sombreamento das faces leste e oeste)
    for b in pj.BRISES:
        if (b["cod"] == "BR-OS") != (pav == "S"):
            continue
        x, y, w, h = b["x"], b["y"], b["w"], b["h"]
        cv.poli_p([vw.pt(P(x, y)), vw.pt(P(x + w, y)), vw.pt(P(x + w, y + h)),
                   vw.pt(P(x, y + h))], "vista", fechado=True, preenche="#f3e3cf")
        n = int(w / b["passo"])
        for i in range(n + 1):
            xx = x + i * b["passo"]
            cv.linha_p(vw.pt(P(xx, y)), vw.pt(P(xx, y + h)), "fino", cor="#a9743a")
        cv.texto_p(vw.pt(P(x + w / 2, y + h + 500)),
                   f"{b['cod']}  RIPADO VERTICAL", TXT["micro"], "middle", cor="#a9743a")

    # ---- cotas de nivel
    if pav == "T":
        # R60 — a cota de nivel estava no CENTRO do ambiente, em cima do
        # nome: "GOURMET" e "ESTAR / JANTAR" saiam com o triangulo por cima.
        # Vai 1.500 mm ao sul do rotulo, ainda dentro do comodo.
        an.nivel(cv, vw, P(5_400, 8_700), 0)
        an.nivel(cv, vw, P(7_500, 14_700), 0)
        an.nivel(cv, vw, P(7_500, 21_300), 0)
        an.nivel(cv, vw, P(6_900, 29_100), -20)
        an.nivel(cv, vw, P(13_200, 26_400), -150)
    else:
        an.nivel(cv, vw, P(5_100, 14_100), pj.NIVEL_SUPERIOR)
        an.nivel(cv, vw, P(13_200, 17_400), pj.NIVEL_SUPERIOR)

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
    eixos_y = [7_200, 13_200, 19_200, 26_400, 30_600]
    for i, xv in enumerate(eixos_x):
        an.eixo_modular(cv, vw, xv, y0, y1, "V", chr(65 + i))
    for i, yv in enumerate(eixos_y):
        an.eixo_modular(cv, vw, yv, x0, x1, "H", str(i + 1))

    # ---- indicacao dos cortes
    if pav == "T":
        an.marca_corte(cv, vw, P(1_200, 16_200), P(18_000, 16_200), "A")
        an.marca_corte(cv, vw, P(7_500, 5_400), P(7_500, 32_400), "B")

    an.norte(cv, (800, 46), 9, pj.NORTE_EM_PLANTA)

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

    _rosa_solar(cv, (768, 128))
    an.titulo_desenho(cv, (78, 560), "1", nome.split("—")[-1].strip(), "1:50")
    an.escala_grafica(cv, (78, 574), vw, 1_000, 5)
    if cv.cortado():
        an.ruptura(cv, 60, 520, cv.marg + 3,
                   "AREAS EXTERNAS CONTINUAM ALEM DESTE LIMITE — VER PR-01 (1:200) E PR-34")

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
    # R60 — 1:100, nao 1:200. Em 1:200 o lote de 20 x 40 m ocupava 100 x 200
    # mm num papel de 841 x 594: 4 % da folha, o resto em branco. A prancha de
    # implantacao e a primeira que prefeitura, vizinho e construtor abrem, e
    # era a menos legivel do caderno.
    cv = base("IMPLANTACAO E SITUACAO", "1:100", "01", notas=[
        "Lote 20.000 x 40.000 mm = 800,00 m2.",
        "Recuos: frontal 7.200 / lateral esq. 2.400 / faixa tecnica dir. 3.200 / fundo 13.600 mm.",
        "Parametros do SU16 Tarumã/Tarumã-Açu sao hipoteses (H) — pendente certidao de uso do solo.",
        "Sem muro frontal; muros laterais e de fundo h = 2.200 mm.",
    ])
    vw = View(100, 150, 520, 0, 0)

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

    # ---- areas tecnicas e pilares
    _tecnicos(cv, vw)

    # ---- cotas do lote e recuos
    an.cadeia(cv, vw, [0, 2_400, 8_400, 16_800, L], 0, "H", 12)
    an.cadeia(cv, vw, [0, L], 0, "H", 22)
    an.cadeia(cv, vw, [0, 7_200, 13_200, 19_200, 26_400, Pf], 0, "V", -12)
    an.cadeia(cv, vw, [0, Pf], 0, "V", -22)

    an.norte(cv, (735, 92), 9, pj.NORTE_EM_PLANTA)
    an.titulo_desenho(cv, (150, 540), "1", "IMPLANTACAO", "1:100")
    an.escala_grafica(cv, (150, 556), vw, 5_000, 4)

    # ---- quadro de verificacao urbanistica
    _tabela(cv, (470, 120), "VERIFICACAO URBANISTICA (H)",
            ["PARAMETRO", "PROJETO", "LIMITE", ""],
            [[n, v, l, "OK" if ok else "REVER"] for n, v, l, ok in pj.verificacao_urbanistica()],
            larguras=[62, 40, 48, 18])
    return cv



def _tecnicos(cv: Canvas, vw: View, rotulos: bool = True) -> None:
    """Areas tecnicas do modelo (TECNICOS) sobre a implantacao.

    Enterrado e rasante em tracejado; equipamento aparente em linha cheia.
    Os nichos de condensadoras recebem a contagem de posicoes de CLIMATIZACAO.
    """
    for t in pj.TECNICOS:
        if t.get("zona") == "INT":
            continue
        x, y, w, h = t["x"], t["y"], t["w"], t["h"]
        sob = t.get("rasante") or t.get("prof")
        cv.poli_p([vw.pt(P(x, y)), vw.pt(P(x + w, y)),
                   vw.pt(P(x + w, y + h)), vw.pt(P(x, y + h))],
                  "oculto" if sob else "vista", fechado=True,
                  preenche="none" if sob else "#fff3d6", cor="#b5651d")
        if not rotulos:
            continue
        n = len(pj.nicho_de(t["cod"]))
        rot = t["cod"] + (f" ({n})" if n else "")
        vert = h > w
        cv.texto_p(vw.pt(P(x + w / 2, y + h / 2)), rot, TXT["micro"], "middle",
                   rot=90 if vert else 0, cor="#b5651d")
    for p in pj.PILARES:
        c = vw.pt(P(p["x"], p["y"]))
        cv.poli_p([(c[0] - 1.6, c[1] - 1.6), (c[0] + 1.6, c[1] - 1.6),
                   (c[0] + 1.6, c[1] + 1.6), (c[0] - 1.6, c[1] + 1.6)],
                  "corte", fechado=True, preenche="#444", cor="#444")


# =========================================================================
# PR-05 — COBERTURA
# =========================================================================
def cobertura() -> Canvas:
    cb = pj.COBERTURA
    cv = base("PLANTA DE COBERTURA", "1:100", "05", notas=[
        f"Painel sanduiche PIR {pj.ESP_PAINEL_PIR} mm; inclinacao {cb['inclinacao']*100:.0f} %.",
        f"Calha externa {cb['calha_l']}x{cb['calha_h']} mm; {cb['descidas']} descidas DN{cb['dn_descida']}.",
        f"Contribuicao {pj.area_contribuicao_m2():.2f} m2 | i = {cb['intensidade_mm_h']} mm/h | "
        f"C = {cb['coef_escoamento']} -> Q = {pj.vazao_pluvial_ls():.4f} L/s.",
        "Reservatorio de retencao pluvial 2.500 L — irrigacao e lavagem, sem ligacao a rede potavel.",
    ])
    vw = View(100, 150, 470, 2_400, 7_200)

    baixos = pj.cobertos()
    altos = pj.SUPERIOR
    pat = cv.hachura("pir", espac=2.6, ang=0, w=0.06, cor="#ccc")

    for a in baixos:
        cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                   vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                  "fino", fechado=True, preenche=f"url(#{pat})", cor="#aaa")
    x0, y0, x1, y1 = _extremos(pj.cobertos())
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
        cv.texto_p((p[0] + 4, p[1]), f"DN{cb['dn_descida']}  {pj.vazao_pluvial_ls()/4:.4f} L/s",
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
    an.norte(cv, (735, 92), 9, pj.NORTE_EM_PLANTA)
    an.titulo_desenho(cv, (150, 512), "1", "COBERTURA", "1:100")
    an.escala_grafica(cv, (150, 528), vw, 2_000, 5)
    return cv


# ------------------------------------------------------------- tabelas
def _tabela(cv: Canvas, pos, titulo: str, cabec: list[str], linhas: list[list[str]],
            larguras: list[float], h_lin: float = 5.2) -> float:
    """Tabela que se recusa a transbordar a folha.

    Ate R11 uma tabela iniciada em y = 570 numa folha cujo quadro termina em 584
    simplesmente continuava para fora — e as linhas de baixo, que costumam ser
    justamente as do fim do quadro, nunca chegavam ao papel. Agora a tabela
    mede o espaco que tem e comprime a entrelinha ate o minimo legivel; se ainda
    assim nao couber, quebra em duas colunas lado a lado.
    """
    x, y = pos
    disponivel = (cv.alt - cv.marg) - y - 2
    preciso = (len(linhas) + 1) * h_lin
    if preciso > disponivel:
        h_min = 3.4
        if (len(linhas) + 1) * h_min <= disponivel:
            h_lin = max(h_min, disponivel / (len(linhas) + 1))
        elif x + 2 * sum(larguras) + 10 <= cv.larg - cv.marg:
            # cabe uma segunda coluna ao lado: metade das linhas vai para la
            meio = (len(linhas) + 1) // 2
            _tabela(cv, (x, y), titulo, cabec, linhas[:meio], larguras, h_min)
            _tabela(cv, (x + sum(larguras) + 10, y), "(continuacao)", cabec,
                    linhas[meio:], larguras, h_min)
            return y + (meio + 1) * h_min
        else:
            # nao ha espaco lateral: comprime ate o limite e deixa a auditoria
            # gritar se a entrelinha ficar ilegivel
            h_lin = disponivel / (len(linhas) + 1)
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


def _rosa_solar(cv: Canvas, pos) -> None:
    """Percurso solar: faces criticas em latitude 3 S, com a testada a leste."""
    import math
    x, y = pos
    r = 22.0
    cv.texto_p((x, y - r - 10), "PERCURSO SOLAR — MANAUS 3 S", TXT["micro"],
               "middle", peso="bold")
    cv.circ_p((x, y), r, "fino", cor=CINZA)
    # em planta, com testada a leste: +X = norte (direita), +Y = oeste (cima)
    for rotulo, dx, dy, cor in (("N", 1, 0, "#0a6"), ("S", -1, 0, "#0a6"),
                                ("O", 0, -1, "#c00"), ("L", 0, 1, "#c00")):
        cv.texto_p((x + dx * (r + 5), y + dy * (r + 5)), rotulo, TXT["min"],
                   "middle", cor=cor, peso="bold")
    # eixo critico leste-oeste
    cv.linha_p((x, y - r), (x, y + r), "eixo", cor="#c00")
    # trajetoria do sol: nasce a leste (baixo), poe a oeste (cima)
    cv.arco_p((x, y), r * 0.62, 250, 290, "fino")
    for ang, txt in ((265, "8h"), (275, "16h")):
        px = x + r * 0.78 * math.cos(math.radians(ang))
        py = y - r * 0.78 * math.sin(math.radians(ang))
        cv.texto_p((px, py), txt, TXT["micro"], "middle", cor="#c00")
    for i, (t, cor) in enumerate([
            ("faces L e O: sol a 30 graus", "#c00"),
            ("-> exigem brise VERTICAL", "#c00"),
            ("faces N e S: sol 63 a 87 graus", "#0a6"),
            ("-> beiral de 1.200 mm resolve", "#0a6")]):
        cv.texto_p((x, y + r + 12 + i * 4.6), t, TXT["micro"], "middle", cor=cor)


def _desenhar_subdivisoes(cv: Canvas, vw: View, pav: str) -> None:
    """Divisorias de banho e closet dentro dos modulos de suite.

    So recebem parede as faces internas ao modulo: as que coincidem com a
    parede externa do ambiente ja foram desenhadas pela derivacao.
    """
    ambs = {a.cod: a for a in (pj.TERREO if pav == "T" else pj.SUPERIOR)}
    esp = pj.PAR_INT
    pat = cv.hachura("lsf", espac=0.9, ang=45, w=0.06, cor="#444")
    for sd in pj.SUBDIVISOES:
        pai = ambs.get(sd["pai"])
        if pai is None:
            continue
        x, y, w, h = sd["x"], sd["y"], sd["w"], sd["h"]
        faces = [
            ("S", x, x, y, y + h, x > pai.x),
            ("N", x + w, x + w, y, y + h, x + w < pai.x + pai.w),
            ("L", x, x + w, y, y, y > pai.y),
            ("O", x, x + w, y + h, y + h, y + h < pai.y + pai.h),
        ]
        for face, x1, x2, y1, y2, interna in faces:
            if not interna:
                continue
            vertical = x1 == x2
            a0, a1 = (y1, y2) if vertical else (x1, x2)
            trechos = [(a0, a1)]
            # R53 — uma subdivisao pode ter DUAS portas: a do pai e a `liga`
            # (banho -> closet da master). Cada uma abre o seu vao na face.
            aberturas = [(sd["face"], sd["pos"], sd["vao"])]
            if sd.get("liga"):
                lg = sd["liga"]
                aberturas.append((lg["face"], lg["pos"], lg["vao"]))
            for f_ab, pos_ab, vao_ab in aberturas:
                if face != f_ab:
                    continue
                v0, v1 = pos_ab - vao_ab / 2, pos_ab + vao_ab / 2
                novos = []
                for t0, t1 in trechos:
                    novos += [t for t in ((t0, min(v0, t1)), (max(v1, t0), t1))
                              if t[1] - t[0] > 1]
                trechos = novos
            for t0, t1 in trechos:
                if vertical:
                    bx, by, bw, bh = x1 - esp / 2, t0, esp, t1 - t0
                else:
                    bx, by, bw, bh = t0, y1 - esp / 2, t1 - t0, esp
                cv.poli_p([vw.pt(P(bx, by)), vw.pt(P(bx + bw, by)),
                           vw.pt(P(bx + bw, by + bh)), vw.pt(P(bx, by + bh))],
                          "corte", fechado=True, preenche=f"url(#{pat})")
        c = vw.pt(P(x + w / 2, y + h / 2))
        cv.texto_p(c, sd["nome"], TXT["micro"], "middle", cor=CINZA,
                   rot=90 if h > w * 1.5 else 0)
