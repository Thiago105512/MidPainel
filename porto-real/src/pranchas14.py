"""R78 — PISCINA EXECUTIVA.

  70  PISCINA: CORTES, ESCADA, BORDA E ILUMINACAO — corte longitudinal e
      transversal (1:25), escada de praia (1:10), borda com pingadeira (1:5),
      nicho do LED (1:5) e planta de iluminacao (1:50) (348-353, 361-363)
  71  PISCINA: HIDRAULICA, DIAGRAMA E CASA DE MAQUINAS — planta de succao,
      retorno, drenos e skimmer (1:50), diagrama hidraulico, casa de maquinas
      em planta e corte (1:20), linhas, bomba e filtro (354-360)
Tudo sai de nucleo/piscina; a PR-34 e a PR-10 leem as mesmas posicoes.
"""
from __future__ import annotations

import projeto as pj
import anotacao as an
import nucleo.piscina as psc
from core import P, Canvas, View, TXT, CINZA
from pranchas import base, _tabela
from pranchas13 import _caixa_det

AGUA, AGUA_F, CONC, TERRA = "#06c", "#e8f4fb", "#9a9a9a", "#c9b79c"
SUC, RET, LED, LARANJA = "#b5651d", "#1f4b8a", "#c0269a", "#d9822b"


def _f(v: float, nd: int = 1) -> str:
    return f"{v:.{nd}f}".replace(".", ",")


def _perfil_longitudinal(g: dict, e: dict) -> list[tuple[float, float]]:
    """Linha do piso da piscina, da borda leste... nao: do lado SUL (x = 0) ao NORTE (x = w), em (x, z)."""
    pts = [(0, g["nivel_agua"]), (0, -g["prof_prainha"])]
    for d in e["degraus"]:
        pts += [(d["x0"], d["z"]), (d["x0"], d["z"] - d["espelho"])]
    pts += [(g["w"] - g["banco_w"], -g["prof_principal"]), (g["w"] - g["banco_w"], g["banco_assento"]),
            (g["w"], g["banco_assento"]), (g["w"], g["nivel_agua"])]
    return pts


def cortes_escada_borda_iluminacao() -> Canvas:
    g, e, b, il = psc.geometria(pj), psc.escada(pj), psc.bordas(pj), psc.iluminacao(pj)
    cv = base("PISCINA: CORTES, ESCADA, BORDA E ILUMINACAO", "indicada", "70", notas=[
        f"Nivel da agua {g['nivel_agua']} mm (skimmer). Prainha {g['prof_prainha']} mm; escada de praia de {e['n']} degraus "
        f"({e['espelho']} x {e['piso']} mm) na largura inteira; fundo {g['prof_principal']} mm; banco com assento a "
        f"{-g['banco_assento']} mm.".replace(".", ","),
        f"Estrutura: {g['concreto']}; lastro {g['lastro']} mm; fundo da escavacao a {g['fundo_escavacao']} mm. "
        f"Impermeabilizacao: {g['impermeabilizacao']}.",
        f"Borda: {b['peca']}; deck com {b['caimento_deck'] * 100:.0f} % {b['sentido']}. "
        f"Iluminacao: {len(il['leds'])} LEDs {il['cor']} a {il['prof_mm']} mm, SELV {il['tensao']} V, {il['w_m2']} W/m2.".replace(".", ","),
        "Numeros marcados (H) sao hipoteses de projeto: limites da NBR 10339 e pratica de piscina residencial.",
    ])
    h_conc = cv.hachura("conc70", espac=1.4, ang=45, w=0.1, cor=CONC)
    h_terra = cv.hachura("terra70", espac=2.0, ang=-45, w=0.1, cor=TERRA)

    # ============ DET 1 — corte longitudinal 1:25 (x, z)
    vw = View(25, 72, 110, 0, 0)
    an.titulo_desenho(cv, (40, 40), "1", "CORTE LONGITUDINAL (SUL -> NORTE)", "1:25")
    with cv.escopo("piscina", "CORTE-L"):
        perfil = _perfil_longitudinal(g, e)
        casca = g["casca"]
        # terreno e lastro
        cv.poli_p([vw.pt(P(-casca - 600, 0)), vw.pt(P(g["w"] + casca + 600, 0)),
                   vw.pt(P(g["w"] + casca + 600, g["fundo_escavacao"] - 200)), vw.pt(P(-casca - 600, g["fundo_escavacao"] - 200))],
                  "fino", fechado=True, preenche=f"url(#{h_terra})", cor=TERRA)
        # casca: poligono externo menos o interno
        ext = [(-casca, 0), (-casca, g["fundo_escavacao"] + g["lastro"]), (g["w"] + casca, g["fundo_escavacao"] + g["lastro"]), (g["w"] + casca, 0)]
        cv.poli_p([vw.pt(P(*q)) for q in ext], "corte", fechado=True, preenche=f"url(#{h_conc})", cor="#555")
        interno = [(0, 0)] + perfil[1:-1] + [(g["w"], 0)]
        cv.poli_p([vw.pt(P(*q)) for q in interno], "corte", fechado=True, preenche="#fff", cor="#555")
        # lastro
        cv.poli_p([vw.pt(P(-casca, g["fundo_escavacao"] + g["lastro"])), vw.pt(P(g["w"] + casca, g["fundo_escavacao"] + g["lastro"])),
                   vw.pt(P(g["w"] + casca, g["fundo_escavacao"])), vw.pt(P(-casca, g["fundo_escavacao"]))],
                  "fino", fechado=True, preenche="#e6e6e6", cor="#888")
        # agua
        cv.poli_p([vw.pt(P(*q)) for q in perfil], "fino", fechado=True, preenche=AGUA_F, cor=AGUA)
        cv.linha_p(vw.pt(P(0, g["nivel_agua"])), vw.pt(P(g["w"], g["nivel_agua"])), "fino", cor=AGUA, dash="2,1")
        cv.texto_p(vw.pt(P(g["w"] / 2, g["nivel_agua"] + 60)), f"N.A. {g['nivel_agua']}", TXT["micro"], "middle", cor=AGUA)
        # bordas nas duas pontas (30 mm sobre a agua)
        for x, s in ((0, -1), (g["w"], 1)):
            _caixa_det(cv, vw, x - 30 * s if s > 0 else x - 300, 0, 330, b["espessura"], "#333", "#d9d2c5")
        cv.texto_p(vw.pt(P(g["prainha_w"] / 2, -g["prof_prainha"] / 2)), "PRAINHA", TXT["micro"], "middle", cor=AGUA)
        cv.texto_p(vw.pt(P((e["x_fim"] + g["w"] - g["banco_w"]) / 2, -g["prof_principal"] / 2)),
                   f"LAMINA {_f(g['lamina_m2'], 2)} m2 · V = {_f(g['volume_m3'], 2)} m3", TXT["min"], "middle", cor=AGUA)
        cv.texto_p(vw.pt(P(g["w"] - g["banco_w"] / 2, g["banco_assento"] - 250)), "BANCO", TXT["micro"], "middle", rot=90, cor=AGUA)
        cv.texto_p(vw.pt(P(g["prainha_w"] + e["avanco"] / 2, -g["prof_prainha"] - 120)), f"ESCADA {e['n']} x {e['espelho']}".replace(".", ","),
                   TXT["micro"], "middle", cor="#333")
        cv.texto_p(vw.pt(P(g["w"] / 2, g["fundo_escavacao"] + 40)), f"LASTRO {g['lastro']} · CASCA {casca}", TXT["micro"], "middle", cor="#666")
        an.cadeia(cv, vw, [0, g["prainha_w"], e["x_fim"], g["w"] - g["banco_w"], g["w"]], g["fundo_escavacao"] - 200, "H", -8)
        an.cadeia(cv, vw, [0, -g["prof_prainha"], g["banco_assento"], -g["prof_principal"], g["fundo_escavacao"]], -casca - 600, "V", -10)
        cv.texto_p(vw.pt(P(-casca - 300, 250)), "SUL", TXT["micro"], "middle", cor=CINZA)
        cv.texto_p(vw.pt(P(g["w"] + casca + 300, 250)), "NORTE", TXT["micro"], "middle", cor=CINZA)

    # ============ DET 2 — corte transversal 1:25 (y, z), pelo dreno DF-1
    pts = {p["cod"]: p for p in psc.pontos(pj)}
    vw2 = View(25, 360, 110, 0, 0)
    an.titulo_desenho(cv, (340, 40), "2", "CORTE TRANSVERSAL PELO DRENO (LESTE -> OESTE)", "1:25")
    with cv.escopo("piscina", "CORTE-T"):
        casca = g["casca"]
        h = g["h"]
        cv.poli_p([vw2.pt(P(-casca - 600, 0)), vw2.pt(P(h + casca + 600, 0)), vw2.pt(P(h + casca + 600, g["fundo_escavacao"] - 200)),
                   vw2.pt(P(-casca - 600, g["fundo_escavacao"] - 200))], "fino", fechado=True, preenche=f"url(#{h_terra})", cor=TERRA)
        cv.poli_p([vw2.pt(P(-casca, 0)), vw2.pt(P(-casca, g["fundo_escavacao"] + g["lastro"])), vw2.pt(P(h + casca, g["fundo_escavacao"] + g["lastro"])),
                   vw2.pt(P(h + casca, 0))], "corte", fechado=True, preenche=f"url(#{h_conc})", cor="#555")
        cv.poli_p([vw2.pt(P(0, 0)), vw2.pt(P(0, -g["prof_principal"])), vw2.pt(P(h, -g["prof_principal"])), vw2.pt(P(h, 0))],
                  "corte", fechado=True, preenche="#fff", cor="#555")
        cv.poli_p([vw2.pt(P(0, g["nivel_agua"])), vw2.pt(P(0, -g["prof_principal"])), vw2.pt(P(h, -g["prof_principal"])),
                   vw2.pt(P(h, g["nivel_agua"]))], "fino", fechado=True, preenche=AGUA_F, cor=AGUA)
        cv.linha_p(vw2.pt(P(0, g["nivel_agua"])), vw2.pt(P(h, g["nivel_agua"])), "fino", cor=AGUA, dash="2,1")
        for y in (0, h):
            _caixa_det(cv, vw2, y - 300 if y else -30, 0, 330, b["espessura"], "#333", "#d9d2c5")
        # dreno de fundo no eixo, retorno e LED na parede leste (y = 0), skimmer na oeste (y = h)
        d = pts["DF-1"]
        _caixa_det(cv, vw2, h / 2 - 125, -g["prof_principal"] - 60, 250, 60, SUC, "#fff", None, "vista")
        cv.texto_p(vw2.pt(P(h / 2, -g["prof_principal"] - 170)), f"{d['cod']} DN50 antiaprisionamento", TXT["micro"], "middle", cor=SUC)
        r = pts["RT-1"]
        cv.circ_p(vw2.pt(P(0, r["z"])), 1.4, "vista", preenche="#fff", cor=RET)
        cv.texto_p(vw2.pt(P(-casca - 100, r["z"])), "RETORNO", TXT["micro"], "end", cor=RET)
        l = il["leds"][0]
        _caixa_det(cv, vw2, -casca, l["z"] - 125, casca - 20, 250, LED, "#fbe6f5", None, "vista")
        cv.texto_p(vw2.pt(P(-casca - 100, l["z"])), f"LED {l['z']}", TXT["micro"], "end", cor=LED)
        s = pts["SK-1"]
        _caixa_det(cv, vw2, h, s["z"] - 150, casca + 200, 250, SUC, "#fff", None, "vista")
        cv.texto_p(vw2.pt(P(h + casca + 100, s["z"] - 320)), "SKIMMER", TXT["micro"], "start", cor=SUC)
        cv.texto_p(vw2.pt(P(h / 2, -g["prof_principal"] / 2)), f"LARGURA {g['h']} · PROF. {g['prof_principal']}", TXT["min"], "middle", cor=AGUA)
        an.cadeia(cv, vw2, [0, h / 2, h], g["fundo_escavacao"] - 200, "H", -8)
        an.cadeia(cv, vw2, [0, g["nivel_agua"], l["z"], -g["prof_principal"], g["fundo_escavacao"]], h + casca + 600, "V", 10)
        cv.texto_p(vw2.pt(P(-casca - 300, 250)), "LESTE (casa)", TXT["micro"], "middle", cor=CINZA)
        cv.texto_p(vw2.pt(P(h + casca + 300, 250)), "OESTE", TXT["micro"], "middle", cor=CINZA)

    # ============ DET 3 — escada 1:10
    vw3 = View(10, 50, 218, g["prainha_w"] - 300, 0)
    an.titulo_desenho(cv, (40, 192), "3", "ESCADA DE PRAIA", "1:10")
    with cv.escopo("piscina", "ESCADA"):
        x0, x1 = g["prainha_w"] - 300, e["x_fim"] + 600
        perfil = [(x0, -g["prof_prainha"])]
        for d in e["degraus"]:
            perfil += [(d["x0"], d["z"]), (d["x0"], d["z"] - d["espelho"])]
        perfil += [(x1, -g["prof_principal"])]
        cv.poli_p([vw3.pt(P(*q)) for q in [(x0, g["nivel_agua"])] + perfil + [(x1, g["nivel_agua"])]], "fino", fechado=True,
                  preenche=AGUA_F, cor=AGUA)
        cv.poli_p([vw3.pt(P(*q)) for q in perfil + [(x1, -g["prof_principal"] - g["casca"]), (x0, -g["prof_principal"] - g["casca"])]],
                  "corte", fechado=True, preenche=f"url(#{h_conc})", cor="#555")
        cv.linha_p(vw3.pt(P(x0, g["nivel_agua"])), vw3.pt(P(x1, g["nivel_agua"])), "fino", cor=AGUA, dash="2,1")
        for d in e["degraus"]:
            # faixa antiderrapante de 50 mm no bordo
            cv.linha_p(vw3.pt(P(d["x0"], d["z"] + 5)), vw3.pt(P(d["x0"] + 50, d["z"] + 5)), "grosso", cor=LARANJA)
            cv.texto_p(vw3.pt(P(d["x0"] + d["piso"] / 2, d["z"] - d["espelho"] / 2)), f"{d['n']}", TXT["micro"], "middle", cor="#333")
        an.cadeia(cv, vw3, [g["prainha_w"]] + [d["x0"] + d["piso"] for d in e["degraus"]], g["nivel_agua"] + 150, "H", 6)
        an.cadeia(cv, vw3, [-g["prof_prainha"]] + [d["z"] - d["espelho"] for d in e["degraus"]], x1 + 100, "V", 8)
        cv.texto_p(vw3.pt(P((x0 + x1) / 2, -g["prof_principal"] - g["casca"] - 150)),
                   f"{e['n']} degraus de {_f(e['espelho'])} mm; piso {e['piso']} mm; faixa antiderrapante laranja de 50 mm", TXT["micro"], "middle")
        cv.texto_p(vw3.pt(P((x0 + x1) / 2, -g["prof_principal"] - g["casca"] - 320)), e["obs"][:96], TXT["micro"], "middle", cor="#555")

    # ============ DET 4 — borda 1:5 (x: 0 = face interna da parede; z)
    vw4 = View(5, 250, 218, -900, 0)
    an.titulo_desenho(cv, (235, 192), "4", "BORDA COM PINGADEIRA E FAIXA SECA", "1:5")
    with cv.escopo("piscina", "BORDA"):
        c = g["casca"]
        # parede da casca e revestimento interno de 10 mm
        _caixa_det(cv, vw4, -c, -700, c, 700 - 30, "#555", f"url(#{h_conc})")
        _caixa_det(cv, vw4, 0, -700, 10, 700 - 30 - 20, AGUA, "#cfe7f5", None, "fino")
        # deck: contrapiso 60 e piso 20, caindo 1 % para fora
        queda = b["caimento_deck"] * 600
        cv.poli_p([vw4.pt(P(-330, -30)), vw4.pt(P(-930, -30 - queda)), vw4.pt(P(-930, -110)), vw4.pt(P(-330, -110))], "corte", fechado=True,
                  preenche="#eee", cor="#777")
        cv.poli_p([vw4.pt(P(-330, -10)), vw4.pt(P(-930, -10 - queda)), vw4.pt(P(-930, -30 - queda)), vw4.pt(P(-330, -30))], "corte", fechado=True,
                  preenche="#d9d2c5", cor="#333")
        # borda 300 + 30 de balanco, 30 de espessura, sobre 20 de argamassa
        _caixa_det(cv, vw4, -300, -50, 300, 20, "#777", "#e0d8cc")
        _caixa_det(cv, vw4, -330, -30, 360, 30, "#333", "#d9d2c5")
        cv.poli_p([vw4.pt(P(30, -30)), vw4.pt(P(30, -25)), vw4.pt(P(15, -20)), vw4.pt(P(15, -30))], "fino", fechado=True, preenche="#333", cor="#333")
        # junta de 5 mm entre a borda e o piso
        cv.linha_p(vw4.pt(P(-330, 0)), vw4.pt(P(-330, -30)), "grosso", cor=LARANJA)
        # cantoneira e agua
        cv.linha_p(vw4.pt(P(-5, -50)), vw4.pt(P(-5, -75)), "grosso", cor="#06a")
        cv.linha_p(vw4.pt(P(-5, -50)), vw4.pt(P(20, -50)), "grosso", cor="#06a")
        cv.poli_p([vw4.pt(P(10, -100)), vw4.pt(P(400, -100)), vw4.pt(P(400, -700)), vw4.pt(P(10, -700))], "fino", fechado=True, preenche=AGUA_F, cor=AGUA)
        cv.linha_p(vw4.pt(P(10, -100)), vw4.pt(P(400, -100)), "fino", cor=AGUA, dash="2,1")
        cv.texto_p(vw4.pt(P(200, -80)), "N.A. -100", TXT["micro"], "middle", cor=AGUA)
        for z, s in ((-320, f"borda {b['espessura']} mm, balanco 30, pingadeira"), (-380, "argamassa colante 20 mm"),
                     (-440, "cantoneira Al 25 x 25 (transicao)"), (-500, "junta 5 mm selante PU (laranja)"),
                     (-560, f"deck: piso R11 20 mm, {b['caimento_deck'] * 100:.0f} % para fora"), (-620, f"casca {c} mm + revestimento 10")):
            cv.texto_p(vw4.pt(P(-880, z)), s, TXT["micro"], "start", cor="#444")
        an.cadeia(cv, vw4, [-930, -330, 0, 30], -720, "H", -6)
        an.cadeia(cv, vw4, [0, -30, -50, -100], 60, "V", 6)

    # ============ DET 5 — nicho do LED 1:5
    vw5 = View(5, 470, 218, -900, 0)
    an.titulo_desenho(cv, (455, 192), "5", "NICHO DO LED E CAIXA DE PASSAGEM", "1:5")
    with cv.escopo("piscina", "LED-NICHO"):
        c = g["casca"]
        z = il["leds"][0]["z"]
        _caixa_det(cv, vw5, -c, -800, c, 800 - 30, "#555", f"url(#{h_conc})")
        _caixa_det(cv, vw5, -330, -30, 360, 30, "#333", "#d9d2c5")
        cv.poli_p([vw5.pt(P(10, -100)), vw5.pt(P(400, -100)), vw5.pt(P(400, -800)), vw5.pt(P(10, -800))], "fino", fechado=True, preenche=AGUA_F, cor=AGUA)
        # nicho de PVC 250 de diametro, 120 de profundidade, na casca; LED na face
        _caixa_det(cv, vw5, -120, z - 125, 120, 250, LED, "#fbe6f5", "NICHO PVC")
        _caixa_det(cv, vw5, 0, z - 100, 25, 200, LED, "#f5c0e8", None, "vista")
        # eletroduto 25 mm dentro da casca ate a caixa de passagem no deck, a 600 mm da borda
        cv.linha_p(vw5.pt(P(-100, z + 125)), vw5.pt(P(-100, -120)), "grosso", cor=LED, dash="1.5,1")
        cv.linha_p(vw5.pt(P(-100, -120)), vw5.pt(P(-600, -120)), "grosso", cor=LED, dash="1.5,1")
        _caixa_det(cv, vw5, -700, -160, 150, 150, LED, "#fff", "CX")
        cv.linha_p(vw5.pt(P(-700, -120)), vw5.pt(P(-900, -120)), "grosso", cor=LED, dash="1.5,1")
        cv.texto_p(vw5.pt(P(-880, -220)), f"-> fonte {il['tensao']} V em TC-13", TXT["micro"], "start", cor=LED)
        for zz, s in ((-330, f"LED {il['leds'][0]['w']} W {il['cor']}, lente a {z} mm"), (-390, "nicho PVC o 250, 120 de fundo, embutido na casca"),
                      (-450, "cabo sem emenda ate a caixa (CX) no deck"), (-510, f"caixa estanque a 600 mm da borda; eletroduto 25 mm"),
                      (-570, f"SELV {il['tensao']} V + DR 30 mA na fonte")):
            cv.texto_p(vw5.pt(P(-880, zz)), s, TXT["micro"], "start", cor="#444")
        an.cadeia(cv, vw5, [0, z, -800], 120, "V", 8)

    # ============ DET 6 — planta de iluminacao 1:50
    dk = pj.DECK
    cm = psc._cm(pj)
    vw6 = View(50, 50, 545, dk["x"] - 600, dk["y"] - 600)
    an.titulo_desenho(cv, (40, 395), "6", "PLANTA DE ILUMINACAO SUBAQUATICA", "1:50")
    with cv.escopo("piscina", "ILUM"):
        cv.poli_p([vw6.pt(P(dk["x"], dk["y"])), vw6.pt(P(dk["x"] + dk["w"], dk["y"])), vw6.pt(P(dk["x"] + dk["w"], dk["y"] + dk["h"])),
                   vw6.pt(P(dk["x"], dk["y"] + dk["h"]))], "vista", fechado=True, preenche="#f3efe6", cor="#a89")
        cv.poli_p([vw6.pt(P(g["x"], g["y"])), vw6.pt(P(g["x"] + g["w"], g["y"])), vw6.pt(P(g["x"] + g["w"], g["y"] + g["h"])),
                   vw6.pt(P(g["x"], g["y"] + g["h"]))], "corte", fechado=True, preenche=AGUA_F, cor=AGUA)
        with cv.recorte(*vw6.pt(P(g["x"], g["y"] + g["h"])), *vw6.pt(P(g["x"] + g["w"], g["y"]))):
            for l in il["leds"]:
                c = vw6.pt(P(l["x"], l["y"]))
                # feixe de 60 graus para oeste (para cima no papel)
                cv.poli_p([c, vw6.pt(P(l["x"] - 2_000, l["y"] + 3_400)), vw6.pt(P(l["x"] + 2_000, l["y"] + 3_400))], "fino",
                          fechado=True, preenche="#fbe6f5", cor="none")
        for l in il["leds"]:
            c = vw6.pt(P(l["x"], l["y"]))
            cv.circ_p(c, 1.6, "vista", preenche="#fff", cor=LED)
            cv.texto_p((c[0], c[1] + 4.5), l["cod"], TXT["micro"], "middle", cor=LED)
            # cabo: nicho -> caixa no deck (600 mm para leste) -> pela faixa seca ate TC-13
            cx = vw6.pt(P(l["x"], l["y"] - 600))
            cv.linha_p(c, cx, "fino", cor=LED, dash="1,1")
            cv.poli_p([(cx[0] - 1, cx[1] - 1), (cx[0] + 1, cx[1] - 1), (cx[0] + 1, cx[1] + 1), (cx[0] - 1, cx[1] + 1)], "vista", fechado=True, preenche="#fff", cor=LED)
        # tronco comum pela faixa seca leste ate a casa de maquinas
        y_cabo = g["y"] - 600
        cv.linha_p(vw6.pt(P(il["leds"][0]["x"], y_cabo)), vw6.pt(P(cm["x"], y_cabo)), "fino", cor=LED, dash="1,1")
        cv.linha_p(vw6.pt(P(cm["x"], y_cabo)), vw6.pt(P(cm["x"], cm["y"] + cm["h"] / 2)), "fino", cor=LED, dash="1,1")
        cv.poli_p([vw6.pt(P(cm["x"], cm["y"])), vw6.pt(P(cm["x"] + cm["w"], cm["y"])), vw6.pt(P(cm["x"] + cm["w"], cm["y"] + cm["h"])),
                   vw6.pt(P(cm["x"], cm["y"] + cm["h"]))], "corte", fechado=True, preenche="#fff3d6", cor=SUC)
        cv.texto_p(vw6.pt(P(cm["x"] + cm["w"] / 2, cm["y"] + cm["h"] / 2)), "TC-13 fonte 12 V", TXT["micro"], "middle", rot=90, cor=SUC)
        cv.texto_p(vw6.pt(P(g["x"] + g["w"] / 2, g["y"] - 1_000)), "GOURMET E VARANDA (leste) — olham para oeste", TXT["micro"], "middle", cor=CINZA)
        cv.texto_p(vw6.pt(P(g["x"] + g["w"] / 2, g["y"] + g["h"] + 300)), "skimmer / parede oeste", TXT["micro"], "middle", cor=CINZA)
        an.cadeia(cv, vw6, [g["x"]] + [l["x"] for l in il["leds"]] + [g["x"] + g["w"]], g["y"] + g["h"] + 900, "H", 6)

    # ============ tabelas
    y = _tabela(cv, (620, 40), "GEOMETRIA E ESTRUTURA", ["ITEM", "VALOR", "ORIGEM"], [
        ["Lamina / volume", f"{_f(g['lamina_m2'], 2)} m2 / {_f(g['volume_m3'], 2)} m3", "PISCINA"],
        ["Nivel da agua", f"{g['nivel_agua']} mm", "skimmer (H)"],
        ["Prainha", f"{g['prainha_w']} x {g['prof_prainha']} mm", "PISCINA"],
        ["Escada", f"{e['n']} x {_f(e['espelho'])} / {e['piso']} mm, avanco {e['avanco']}", "desnivel / 250 (H)"],
        ["Fundo", f"{g['prof_principal']} mm (lamina {g['lamina_agua_principal']})", "PISCINA"],
        ["Banco", f"{g['banco_w']} mm, assento a {g['banco_assento']}", "PISCINA"],
        ["Casca / lastro", f"{g['casca']} / {g['lastro']} mm; escavacao a {g['fundo_escavacao']}", "externo.piscina (H)"],
        ["Concreto", f"{_f(g['concreto_m3'], 2)} m3", g["concreto"][:34]],
        ["Impermeabilizacao", f"{_f(g['revestimento_m2'], 2)} m2", "area molhada"],
        ["Borda", f"{b['n_pecas']} pecas de {psc.BORDA_PECA} mm; {_f(b['perimetro_m'])} m", "perimetro da lamina"],
    ], larguras=[36, 76, 66], h_lin=4.4)
    y = _tabela(cv, (620, y + 5), "ILUMINACAO SUBAQUATICA (SELV 12 V)", ["LED", "x mm", "z mm", "W", "lm", "CABO m", "mm2", "QUEDA"],
                [[l["cod"], f"{l['x']}", f"{l['z']}", f"{l['w']}", f"{l['lm']}", _f(l["cabo_mm"] / 1000), _f(l["secao_mm2"]), f"{_f(l['queda_pct'])} %"]
                 for l in il["leds"]] + [["total", "", "", f"{il['w_total']}", "", "", "", f"{_f(il['w_m2'], 2)} W/m2"]],
                larguras=[18, 20, 20, 14, 18, 24, 18, 46], h_lin=4.2)
    y = _tabela(cv, (620, y + 5), "REGRAS DA ILUMINACAO", ["REGRA", "PROJETO"], [
        ["Lado", il["lado"][:70]], ["Fonte", il["fonte"][:70]], ["Nicho", il["nicho"][:70]],
        ["Potencia especifica", f"{_f(il['w_m2'], 2)} W/m2 na faixa {il['faixa_w_m2'][0]}-{il['faixa_w_m2'][1]} (H)"],
    ], larguras=[36, 142], h_lin=4.4)
    conf = [c for c in psc.conferir(pj) if any(k in c[0] for k in ("escada", "faixa seca", "LED", "12 V", "luz", "borda"))]
    _tabela(cv, (620, y + 5), "CONFERENCIAS DESTA PRANCHA", ["O QUE", "COMO", ""],
            [[t[:34], d[:58], "ok" if ok else "NAO"] for t, d, ok in conf], larguras=[58, 104, 16], h_lin=3.8)
    return cv


def hidraulica_e_casa_de_maquinas() -> Canvas:
    g, ln, f, bm, s = psc.geometria(pj), psc.linhas(pj), psc.filtro(pj), psc.bomba(pj), psc.succao(pj)
    pts = psc.pontos(pj)
    dk, cm = pj.DECK, psc._cm(pj)
    cv = base("PISCINA: HIDRAULICA, DIAGRAMA E CASA DE MAQUINAS", "indicada", "71", notas=[
        f"Vazao {_f(psc.vazao_m3h(pj), 2)} m3/h = {_f(g['volume_m3'], 2)} m3 em {pj.PISCINA_SISTEMA['renovacao_h']} h. "
        f"Succao {_f(s['comp_mm'] / 1000)} m (limite {s['max_mm'] // 1000} m). Todas as linhas em DN50: a velocidade maxima e "
        f"{_f(max(x['v_ms'] for x in ln), 2)} m/s contra {psc.V_SUCCAO_MAX} na succao (H, NBR 10339).",
        f"Skimmer na parede oeste (sotavento do vento {psc.VENTO_DOMINANTE}); retornos na leste, opostos; dois drenos de fundo "
        f"afastados (antiaprisionamento); aspiracao na norte, a mais perto de {cm['cod']}.",
        f"Bomba {bm['descricao']}: {_f(bm['h_man_m'], 2)} m.c.a. com filtro sujo; {bm['va']} VA. Filtro {f['tipo']}: "
        f"{_f(f['taxa_m3h_m2'])} m3/h/m2 (max {f['taxa_max']:.0f}); retrolavagem {_f(f['retrolavagem_m3h'])} m3/h por "
        f"{f['retrolavagem_min']} min para o ralo DN75.",
        "Linhas de succao tracejadas, retorno continuo, 12 V ponto-traco. Comprimentos por percurso Manhattan sob a faixa seca, a 600 mm.",
    ])
    # ============ DET 1 — planta hidraulica 1:50
    vw = View(50, 45, 175, dk["x"] - 600, dk["y"] - 600)
    an.titulo_desenho(cv, (40, 40), "1", "PLANTA HIDRAULICA — SUCCAO, RETORNO, DRENOS E SKIMMER", "1:50")
    with cv.escopo("piscina", "HID"):
        cv.poli_p([vw.pt(P(dk["x"], dk["y"])), vw.pt(P(dk["x"] + dk["w"], dk["y"])), vw.pt(P(dk["x"] + dk["w"], dk["y"] + dk["h"])),
                   vw.pt(P(dk["x"], dk["y"] + dk["h"]))], "vista", fechado=True, preenche="#f3efe6", cor="#a89")
        cv.poli_p([vw.pt(P(g["x"], g["y"])), vw.pt(P(g["x"] + g["w"], g["y"])), vw.pt(P(g["x"] + g["w"], g["y"] + g["h"])),
                   vw.pt(P(g["x"], g["y"] + g["h"]))], "corte", fechado=True, preenche=AGUA_F, cor=AGUA)
        cv.poli_p([vw.pt(P(g["x"], g["y"])), vw.pt(P(g["x"] + g["prainha_w"], g["y"])), vw.pt(P(g["x"] + g["prainha_w"], g["y"] + g["h"])),
                   vw.pt(P(g["x"], g["y"] + g["h"]))], "fino", fechado=True, preenche="#d6ecf8", cor=AGUA)
        cv.texto_p(vw.pt(P(g["x"] + g["prainha_w"] / 2, g["y"] + g["h"] / 2)), "PRAINHA", TXT["micro"], "middle", rot=90, cor=AGUA)
        cv.poli_p([vw.pt(P(cm["x"], cm["y"])), vw.pt(P(cm["x"] + cm["w"], cm["y"])), vw.pt(P(cm["x"] + cm["w"], cm["y"] + cm["h"])),
                   vw.pt(P(cm["x"], cm["y"] + cm["h"]))], "corte", fechado=True, preenche="#fff3d6", cor=SUC)
        cv.texto_p(vw.pt(P(cm["x"] + cm["w"] / 2, cm["y"] + cm["h"] / 2)), f"{cm['cod']} bomba + filtro", TXT["micro"], "middle", rot=90, cor=SUC)
        alvo = (cm["x"], cm["y"] + cm["h"] / 2)
        # coletor de succao: pela faixa seca norte (x = deck norte - 450) ate TC-13
        x_col = dk["x"] + dk["w"] - 450
        y_ret = g["y"] - 450
        for p in pts:
            c = vw.pt(P(p["x"], p["y"]))
            cor = {"succao": SUC, "retorno": RET, "12 V": LED}[p["linha"]]
            if p["linha"] == "12 V":
                cv.circ_p(c, 1.3, "fino", preenche="#fff", cor=LED)
                continue
            if p["tipo"].startswith("dreno"):
                cv.poli_p([(c[0] - 1.8, c[1] - 1.8), (c[0] + 1.8, c[1] - 1.8), (c[0] + 1.8, c[1] + 1.8), (c[0] - 1.8, c[1] + 1.8)], "vista",
                          fechado=True, preenche="#fff", cor=SUC)
                # em T no eixo, depois pela parede norte ate o coletor
                cv.linha_p(c, vw.pt(P(g["x"] + g["w"], p["y"])), "fino", cor=SUC, dash="2,1")
            elif p["tipo"] == "skimmer":
                cv.poli_p([(c[0] - 2.5, c[1] - 1.5), (c[0] + 2.5, c[1] - 1.5), (c[0] + 2.5, c[1] + 1.5), (c[0] - 2.5, c[1] + 1.5)], "vista",
                          fechado=True, preenche="#fff", cor=SUC)
                cv.linha_p(c, vw.pt(P(p["x"], g["y"] + g["h"] + 450)), "fino", cor=SUC, dash="2,1")
                cv.linha_p(vw.pt(P(p["x"], g["y"] + g["h"] + 450)), vw.pt(P(x_col, g["y"] + g["h"] + 450)), "fino", cor=SUC, dash="2,1")
                cv.linha_p(vw.pt(P(x_col, g["y"] + g["h"] + 450)), vw.pt(P(x_col, alvo[1])), "fino", cor=SUC, dash="2,1")
            elif p["tipo"].startswith("tomada"):
                cv.circ_p(c, 1.8, "vista", preenche="#fff", cor=SUC)
                cv.linha_p(c, vw.pt(P(x_col, p["y"])), "fino", cor=SUC, dash="2,1")
            else:
                cv.circ_p(c, 1.6, "vista", preenche="#fff", cor=RET)
                cv.linha_p(c, vw.pt(P(p["x"], y_ret)), "vista", cor=RET)
            cv.texto_p((c[0], c[1] - 3.2), p["cod"], TXT["micro"], "middle", cor=cor)
        cv.linha_p(vw.pt(P(g["x"] + g["w"], g["y"] + g["h"] / 2)), vw.pt(P(x_col, g["y"] + g["h"] / 2)), "fino", cor=SUC, dash="2,1")
        cv.linha_p(vw.pt(P(x_col, alvo[1])), vw.pt(P(alvo[0], alvo[1])), "fino", cor=SUC, dash="2,1")
        # anel de retorno pela faixa seca leste ate TC-13
        cv.linha_p(vw.pt(P(pts[3]["x"] if len(pts) > 3 else g["x"], y_ret)), vw.pt(P(x_col + 300, y_ret)), "vista", cor=RET)
        cv.linha_p(vw.pt(P(x_col + 300, y_ret)), vw.pt(P(x_col + 300, alvo[1] - 300)), "vista", cor=RET)
        cv.linha_p(vw.pt(P(x_col + 300, alvo[1] - 300)), vw.pt(P(alvo[0], alvo[1] - 300)), "vista", cor=RET)
        cv.texto_p(vw.pt(P((x_col + alvo[0]) / 2, alvo[1] + 250)), "succao DN50", TXT["micro"], "middle", cor=SUC)
        cv.texto_p(vw.pt(P((x_col + alvo[0]) / 2, alvo[1] - 550)), "retorno DN50", TXT["micro"], "middle", cor=RET)
        cv.texto_p(vw.pt(P(g["x"] + g["w"] / 2, y_ret - 350)), "anel de retorno sob a faixa seca leste", TXT["micro"], "middle", cor=RET)
        cv.texto_p(vw.pt(P(x_col, g["y"] + g["h"] + 700)), "coletor de succao pela faixa norte", TXT["micro"], "middle", cor=SUC)
        an.cadeia(cv, vw, [g["x"] + g["w"], cm["x"]], g["y"] + g["h"] + 1_000, "H", 6)
        an.cadeia(cv, vw, [g["x"]] + sorted({p["x"] for p in pts if p["tipo"].startswith(("dreno", "dispositivo"))}) + [g["x"] + g["w"]],
                  dk["y"] - 300, "H", -6)
        cv.texto_p(vw.pt(P(dk["x"] - 300, dk["y"] + dk["h"] / 2)), "SUL", TXT["micro"], "middle", rot=90, cor=CINZA)
        cv.texto_p(vw.pt(P(g["x"] + g["w"] / 2, dk["y"] - 900)), "LESTE (casa)", TXT["micro"], "middle", cor=CINZA)

    # ============ DET 2 — diagrama hidraulico (sem escala)
    an.titulo_desenho(cv, (40, 215), "2", "DIAGRAMA HIDRAULICO", "s/ escala")
    with cv.escopo("piscina", "DIAG"):
        def no(x, y, w, h, s, cor, preenche="#fff"):
            cv.poli_p([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], "vista", fechado=True, preenche=preenche, cor=cor)
            for i, t in enumerate(s.split("\n")):
                cv.texto_p((x + w / 2, y + h / 2 + 0.8 + (i - (s.count("\n")) / 2) * 3.2), t, TXT["micro"], "middle", cor=cor)
        def seta(a, b_, cor, dash=None):
            cv.linha_p(a, b_, "vista", cor=cor, dash=dash)
            cv.poli_p([b_, (b_[0] - 1.6, b_[1] - 0.9), (b_[0] - 1.6, b_[1] + 0.9)], "vista", fechado=True, preenche=cor, cor=cor)
        y0 = 228
        fontes = [("SK-1\nskimmer", 0), (f"DF-1 + DF-2\ndrenos em T", 1), ("AS-1\naspiracao", 2)]
        for s_, i in fontes:
            no(40, y0 + i * 16, 30, 12, s_, SUC, "#fff7ef")
            no(76, y0 + i * 16 + 3, 8, 6, "RG", SUC)
            cv.linha_p((70, y0 + i * 16 + 6), (76, y0 + i * 16 + 6), "vista", cor=SUC, dash="2,1")
            cv.linha_p((84, y0 + i * 16 + 6), (94, y0 + i * 16 + 6), "vista", cor=SUC, dash="2,1")
        cv.linha_p((94, y0 + 6), (94, y0 + 38), "vista", cor=SUC, dash="2,1")
        seta((94, y0 + 22), (104, y0 + 22), SUC, "2,1")
        no(104, y0 + 16, 16, 12, "PF\ncesto", SUC)
        seta((120, y0 + 22), (128, y0 + 22), SUC, "2,1")
        no(128, y0 + 13, 34, 18, f"BOMBA\n{bm['descricao'][:22]}\n{_f(bm['q_m3h'], 2)} m3/h · {_f(bm['h_man_m'], 1)} m", RET, "#eef3fb")
        seta((162, y0 + 22), (170, y0 + 22), RET)
        no(170, y0 + 16, 16, 12, "VS\n6 pos.", RET)
        seta((186, y0 + 22), (194, y0 + 22), RET)
        no(194, y0 + 13, 34, 18, f"FILTRO\n{f['tipo']}\n{_f(f['taxa_m3h_m2'])} m3/h/m2", RET, "#eef3fb")
        # retrolavagem
        cv.linha_p((178, y0 + 28), (178, y0 + 46), "vista", cor=SUC, dash="1,1")
        seta((178, y0 + 46), (194, y0 + 46), SUC, "1,1")
        no(194, y0 + 40, 34, 12, f"RALO DN75 ({cm['cod']})\nretrolavagem {_f(f['retrolavagem_m3h'])} m3/h", SUC, "#fff7ef")
        seta((228, y0 + 22), (236, y0 + 22), RET)
        no(236, y0 + 13, 34, 18, "BYPASS AQUEC.\n2 registros + espaco\ndo trocador (nao inst.)", CINZA)
        seta((270, y0 + 22), (278, y0 + 22), RET)
        no(278, y0 + 13, 40, 18, f"{pj.PISCINA_SISTEMA['retornos']} RETORNOS\nanel DN50\n{_f(ln[-1]['q_m3h'], 2)} m3/h cada", RET, "#eef3fb")
        cv.texto_p((40, y0 + 62), "RG: registro de esfera DN50 (um por linha de succao). Aspiracao: so com skimmer e drenos fechados. "
                   "Tratamento: cloro; sal em espera (HOLD).", TXT["micro"], "start", cor="#444")

    # ============ DET 3 — casa de maquinas: planta 1:20
    vw3 = View(20, 350, 340, 0, 0)
    an.titulo_desenho(cv, (340, 215), "3", f"{cm['cod']} — CASA DE MAQUINAS, PLANTA", "1:20")
    with cv.escopo("piscina", "CM-PLANTA"):
        W, H = cm["w"], cm["h"]
        cv.poli_p([vw3.pt(P(-100, -100)), vw3.pt(P(W + 100, -100)), vw3.pt(P(W + 100, H + 100)), vw3.pt(P(-100, H + 100))], "corte", fechado=True,
                  preenche="#e0e0e0", cor="#333")
        cv.poli_p([vw3.pt(P(0, 0)), vw3.pt(P(W, 0)), vw3.pt(P(W, H)), vw3.pt(P(0, H))], "corte", fechado=True, preenche="#fff", cor="#333")
        # porta ripada de 800 na face leste (y = 0), para a faixa tecnica
        cv.poli_p([vw3.pt(P(350, -100)), vw3.pt(P(1_150, -100)), vw3.pt(P(1_150, 0)), vw3.pt(P(350, 0))], "fino", fechado=True, preenche="#fff", cor="#333")
        cv.arco_p(vw3.pt(P(350, 0)), vw3.d(800), 0, 90, "fino")
        cv.texto_p(vw3.pt(P(750, -260)), "porta ripada 800", TXT["micro"], "middle")
        # filtro o500, bomba 300 x 500 sobre base, quadro 300 x 400 na parede
        cv.circ_p(vw3.pt(P(400, 1_450)), vw3.d(250), "vista", preenche="#eef3fb", cor=RET)
        cv.texto_p(vw3.pt(P(400, 1_450)), f"FILTRO\no{f['de_mm']}".split("\n")[0], TXT["micro"], "middle", cor=RET)
        cv.texto_p(vw3.pt(P(400, 1_300)), f"o {f['de_mm']}", TXT["micro"], "middle", cor=RET)
        _caixa_det(cv, vw3, 250, 350, 300, 500, RET, "#eef3fb", "BOMBA", "vista")
        _caixa_det(cv, vw3, W - 60, 800, 60, 400, "#333", "#fff", None, "vista")
        cv.texto_p(vw3.pt(P(W - 200, 1_000)), "QUADRO", TXT["micro"], "middle", rot=90)
        cv.circ_p(vw3.pt(P(1_100, 300)), vw3.d(50), "vista", preenche="#fff", cor=SUC)
        cv.texto_p(vw3.pt(P(1_100, 160)), "ralo DN75", TXT["micro"], "middle", cor=SUC)
        # tubos: succao entra pela parede oeste (x = 0) a meia altura; retorno sai ao lado
        cv.linha_p(vw3.pt(P(-100, H / 2)), vw3.pt(P(250, H / 2)), "vista", cor=SUC, dash="2,1")
        cv.linha_p(vw3.pt(P(-100, H / 2 - 300)), vw3.pt(P(400, H / 2 - 300)), "vista", cor=RET)
        cv.linha_p(vw3.pt(P(400, 850)), vw3.pt(P(400, 1_200)), "vista", cor=RET)
        cv.texto_p(vw3.pt(P(-260, H / 2 + 150)), "succao", TXT["micro"], "middle", rot=90, cor=SUC)
        cv.texto_p(vw3.pt(P(-260, H / 2 - 450)), "retorno", TXT["micro"], "middle", rot=90, cor=RET)
        cv.texto_p(vw3.pt(P(W / 2, H + 300)), "venezianas 0,20 m2 (inferior e superior) na face norte", TXT["micro"], "middle", cor="#444")
        an.cadeia(cv, vw3, [0, W], -650, "H", -6)
        an.cadeia(cv, vw3, [0, H], W + 250, "V", 8)

    # ============ DET 4 — casa de maquinas: corte 1:20 (y, z)
    vw4 = View(20, 500, 340, 0, 0)
    an.titulo_desenho(cv, (490, 215), "4", f"{cm['cod']} — CORTE", "1:20")
    with cv.escopo("piscina", "CM-CORTE"):
        W, H = cm["w"], 2_200
        cv.poli_p([vw4.pt(P(-100, 0)), vw4.pt(P(0, 0)), vw4.pt(P(0, H)), vw4.pt(P(-100, H))], "corte", fechado=True, preenche="#e0e0e0", cor="#333")
        cv.poli_p([vw4.pt(P(W, 0)), vw4.pt(P(W + 100, 0)), vw4.pt(P(W + 100, H)), vw4.pt(P(W, H))], "corte", fechado=True, preenche="#e0e0e0", cor="#333")
        cv.poli_p([vw4.pt(P(-100, H)), vw4.pt(P(W + 100, H)), vw4.pt(P(W + 100, H + 120)), vw4.pt(P(-100, H + 120))], "corte", fechado=True,
                  preenche="#e0e0e0", cor="#333")
        cv.linha_p(vw4.pt(P(-400, 0)), vw4.pt(P(W + 400, 0)), "corte")
        _caixa_det(cv, vw4, 250, 0, 300, bm["cota_eixo"], "#777", "#ddd", None, "vista")
        _caixa_det(cv, vw4, 250, bm["cota_eixo"], 300, 350, RET, "#eef3fb", "BOMBA", "vista")
        _caixa_det(cv, vw4, 900, 0, 500, 900, RET, "#eef3fb", "FILTRO", "vista")
        _caixa_det(cv, vw4, W - 60, 1_200, 60, 400, "#333", "#fff", None, "vista")
        for z in (200, 1_800):
            _caixa_det(cv, vw4, -100, z, 100, 300, "#333", "#fff", None, "fino")
            cv.texto_p(vw4.pt(P(-300, z + 150)), "veneziana", TXT["micro"], "middle", rot=90, cor="#444")
        cv.linha_p(vw4.pt(P(-400, g["nivel_agua"])), vw4.pt(P(W + 400, g["nivel_agua"])), "fino", cor=AGUA, dash="2,1")
        cv.texto_p(vw4.pt(P(W + 380, g["nivel_agua"] - 90)), f"N.A. da piscina {g['nivel_agua']}", TXT["micro"], "end", cor=AGUA)
        cv.texto_p(vw4.pt(P(W / 2, H + 320)), f"bomba a +{bm['cota_eixo']} mm: acima da lamina, retrolavagem por gravidade", TXT["micro"], "middle", cor="#444")
        an.cadeia(cv, vw4, [0, bm["cota_eixo"], 900, H], W + 250, "V", 8)

    # ============ tabelas
    y = _tabela(cv, (600, 40), "LINHAS — DN PELA VELOCIDADE, PERDA POR HAZEN-WILLIAMS", ["PONTO", "LINHA", "Q m3/h", "DN", "v m/s", "L m", "hf m", ""],
                [[x["cod"], x["linha"], _f(x["q_m3h"], 2), f"{x['dn']}", _f(x["v_ms"], 2), _f(x["comp_mm"] / 1000), _f(x["hf_m"], 3), "ok" if x["ok"] else "NAO"]
                 for x in ln], larguras=[20, 22, 24, 14, 24, 22, 24, 12], h_lin=4.0)
    y = _tabela(cv, (600, y + 5), "BOMBA E FILTRO", ["ITEM", "VALOR"], [
        ["Bomba", bm["descricao"]], ["Vazao / altura", f"{_f(bm['q_m3h'], 2)} m3/h a {_f(bm['h_man_m'], 2)} m.c.a. (filtro sujo {psc.H_FILTRO_SUJO} m)"],
        ["Potencia", f"hidraulica {bm['p_hidraulica_w']} W; eletrica {bm['p_eletrica_w']} W = {bm['va']} VA (H)"],
        ["Comando", bm["comando"][:74]],
        ["Filtro", f"{f['tipo']}: {_f(f['area_m2'], 3)} m2, {_f(f['taxa_m3h_m2'])} m3/h/m2 (max {f['taxa_max']:.0f})"],
        ["Retrolavagem", f"{_f(f['retrolavagem_m3h'])} m3/h x {f['retrolavagem_min']} min = {_f(f['retrolavagem_m3'], 2)} m3 -> ralo DN75 ({f['ralo_m3h']:.0f} m3/h)"],
        ["Areia", f"{f['areia_kg']} kg (leito 600 mm)"],
        ["Circuito", (lambda c: f"{c['cod']} {c['va']} VA, {c['v']} V" if c else "—")(psc.circuito_piscina(pj))],
    ], larguras=[30, 148], h_lin=4.4)
    conf = [c for c in psc.conferir(pj) if not any(k in c[0] for k in ("escada", "faixa seca", "LED", "12 V", "luz", "borda"))]
    y = _tabela(cv, (600, y + 5), "CONFERENCIAS DESTA PRANCHA", ["O QUE", "COMO", ""],
                [[t[:36], d[:60], "ok" if ok else "NAO"] for t, d, ok in conf], larguras=[60, 104, 14], h_lin=3.8)
    itens = psc.itens_bom(pj)
    _tabela(cv, (340, 430), "ITENS DO SISTEMA NA BOM (precos H)", ["COD", "ITEM", "UN", "QTD", "R$ un", "R$"],
            [[i["cod"], i["desc"][10:56], i["un"], _f(i["qtd"], 1 if isinstance(i["qtd"], float) else 0), _f(i["preco"], 2), _f(i["qtd"] * i["preco"], 2)]
             for i in itens] + [["", "total do sistema", "", "", "", _f(sum(i["qtd"] * i["preco"] for i in itens), 2)]],
            larguras=[30, 104, 12, 20, 24, 30], h_lin=4.0)
    return cv
