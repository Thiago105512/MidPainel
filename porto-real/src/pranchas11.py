"""R72 — LOTE 3 DO BACKLOG: INSTALACOES PECA A PECA (itens 237-314 da matriz).

  60  UNIFILAR E QUADROS — entrada, QDG, QDS, cada circuito com disjuntor,
      secao, fase e queda; tabela dos 59 circuitos (237, 240, 244)
  61  ELETRICA: MATERIAL POR CIRCUITO E FOTOVOLTAICA — o que se compra,
      circuito a circuito; diagrama do FV e passagem dos cabos (252, 255, 256)
  62  ESGOTO E VENTILACAO — isometrico, planta de caixas, coletor com cotas,
      caixa de gordura (274-282)
  63  AGUA FRIA — isometrico, diagrama vertical, pressao em cada peca,
      registros e barrilete (266, 267, 269, 270)
  64  PLUVIAL, GAS, AR NOVO E SUPORTES (294-300, 312-314)

Toda geometria sai de nucleo/esgoto, nucleo/agua, nucleo/circuitos e
nucleo/gas; a projecao isometrica e uma so (_iso) para as tres redes.
"""
from __future__ import annotations

import math

import projeto as pj
import anotacao as an
import elementos as el
import nucleo.esgoto as es
import nucleo.agua as ag
import nucleo.circuitos as ci
import nucleo.gas as gs
import nucleo.fotovoltaica as fv
from core import P, Canvas, View, TXT, CINZA, PRETO
from pranchas import base, _tabela, _desenhar_subdivisoes, _extremos

COS30, SIN30 = math.cos(math.radians(30)), 0.5
COR_DN = {40: "#8e6bb0", 50: "#6b4f8a", 75: "#4b3566", 100: "#2d1f40", 150: "#1a1026"}
COR_AF = {20: "#7fb0e0", 25: "#3f6fb5", 32: "#1f4b8a", 40: "#12315e"}
COR_PLUV = "#0a8fa0"
COR_GAS = "#c8781e"


class _Iso:
    """Projecao isometrica: u = (x - y) cos30, v = z + (x + y) sin30, em mm de papel."""
    def __init__(self, esc: float, pontos: list, x_min: float, y_max: float):
        self.esc = esc
        us = [(x - y) * COS30 / esc for x, y, z in pontos]
        vs = [(z + (x + y) * SIN30) / esc for x, y, z in pontos]
        self.ox = x_min - min(us)
        self.oy = y_max + min(vs)
        self.larg = max(us) - min(us)
        self.alt = max(vs) - min(vs)

    def pt(self, x, y, z):
        return (self.ox + (x - y) * COS30 / self.esc, self.oy - (z + (x + y) * SIN30) / self.esc)

    def linha(self, cv, a, b, cor, w="fino", dash=None):
        cv.linha_p(self.pt(*a), self.pt(*b), w, cor=cor, dash=dash)

    def manhattan(self, cv, a, b, cor, w="fino", dash=None):
        """a -> b andando primeiro em x, depois em y, depois em z."""
        m1 = (b[0], a[1], a[2]); m2 = (b[0], b[1], a[2])
        for p, q in ((a, m1), (m1, m2), (m2, b)):
            if p != q:
                self.linha(cv, p, q, cor, w, dash)

    def caixa(self, cv, x, y, z, w, h, alt, cor, preenche="none"):
        p = self.pt
        base_ = [p(x, y, z), p(x + w, y, z), p(x + w, y + h, z), p(x, y + h, z)]
        topo = [p(x, y, z + alt), p(x + w, y, z + alt), p(x + w, y + h, z + alt), p(x, y + h, z + alt)]
        cv.poli_p(base_, "fino", fechado=True, preenche=preenche, cor=cor)
        if alt:
            cv.poli_p(topo, "fino", fechado=True, preenche=preenche, cor=cor)
            for a, b in zip(base_, topo):
                cv.linha_p(a, b, "fino", cor=cor)

    def rotulo(self, cv, x, y, z, s, cor="#333", h=None, anchor="start", dx=1.5):
        p = self.pt(x, y, z)
        cv.texto_p((p[0] + dx, p[1]), s, h or TXT["micro"], anchor, cor=cor)


def _z_pav(pav):
    return pj.NIVEL_SUPERIOR if pav == "S" else 0


def _planta_base(cv, vw, pav, com_abertos=False):
    fech = pj.TERREO if pav == "T" else pj.SUPERIOR
    for a in fech:
        cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)), vw.pt(P(a.x + a.w, a.y + a.h)),
                   vw.pt(P(a.x, a.y + a.h))], "fino", fechado=True, preenche="#fbfaf7", cor="#bbb")
        c = vw.pt(P(a.cx, a.cy))
        cv.texto_p((c[0], c[1] + 1.2), a.cod, TXT["micro"], "middle", cor="#bbb")
    el.desenhar_paredes(cv, vw, el.derivar_paredes(fech), list(el.vaos_do_pavimento(pav)))
    _desenhar_subdivisoes(cv, vw, pav)
    if com_abertos:
        L, Pf = pj.LOTE_L, pj.LOTE_P
        cv.poli_p([vw.pt(P(0, 0)), vw.pt(P(L, 0)), vw.pt(P(L, Pf)), vw.pt(P(0, Pf))], "cota",
                  fechado=True, preenche="none", cor="#999", dash="3 2")


# =========================================================================
# PR-60 — UNIFILAR E QUADROS
# =========================================================================
def _unifilar_quadro(cv, ox, oy, q: dict, circs: list, larg: float):
    """Barramento horizontal com um ramo por circuito; o DR agrupa os molhados."""
    cv.poli_p([(ox, oy), (ox + larg, oy), (ox + larg, oy + 10), (ox, oy + 10)], "corte", fechado=True, preenche="#f2f2f2")
    cv.texto_p((ox + 2, oy + 6.5), f"{q['quadro']} — {q['nome']} · {q['circuitos']} circuitos · "
               f"{q['vias_usadas']} vias (+20 % = {q['vias_com_reserva']}) de {q['vias_disponiveis']}",
               TXT["peq"], "start", peso="bold")
    # barramento trifasico
    yb = oy + 22
    for k, f in enumerate("ABC"):
        cv.linha_p((ox, yb + k * 2.2), (ox + larg, yb + k * 2.2), "vista", cor=("#222", "#b22", "#888")[k])
        cv.texto_p((ox - 2, yb + k * 2.2 + 0.8), f, TXT["micro"], "end")
    cv.linha_p((ox, yb + 6.6), (ox + larg, yb + 6.6), "fino", cor="#39f", dash="2 1")
    cv.texto_p((ox - 2, yb + 7.4), "N", TXT["micro"], "end", cor="#39f")
    n = len(circs)
    passo = (larg - 20) / max(n, 1)
    dr_x0 = None
    for i, c in enumerate(sorted(circs, key=lambda c: (not c["dr"], c["tipo"], c["cod"]))):
        x = ox + 12 + i * passo
        y0 = yb + (0 if "A" in c["fases"] else 2.2 if "B" in c["fases"] else 4.4)
        cv.linha_p((x, y0), (x, yb + 14), "fino", cor="#333")
        # disjuntor: retangulo pequeno
        cv.poli_p([(x - 1.2, yb + 14), (x + 1.2, yb + 14), (x + 1.2, yb + 18), (x - 1.2, yb + 18)],
                  "fino", fechado=True, preenche="#fff", cor="#333")
        cv.texto_p((x, yb + 17), f"{c['disjuntor_a']}", 1.4, "middle")
        cv.linha_p((x, yb + 18), (x, yb + 26), "fino", cor="#333")
        cv.texto_p((x + 0.6, yb + 27), f"{c['cod']} · {c['va']} VA · {c['v']} V · {'+'.join(c['fases'])} · "
                   f"{c['secao_mm2']} mm2 · {c['queda_pct']:.1f} %", 1.5, "start", rot=90, cor="#333")
        if c["dr"] and dr_x0 is None:
            dr_x0 = x
        if c["dr"]:
            dr_x1 = x
    if dr_x0 is not None:
        cv.poli_p([(dr_x0 - 3, yb + 10.5), (dr_x1 + 3, yb + 10.5), (dr_x1 + 3, yb + 13), (dr_x0 - 3, yb + 13)],
                  "fino", fechado=True, preenche="#e8f1fb", cor="#3f6fb5")
        cv.texto_p((dr_x0 - 3, yb + 12.4), f"{q['n_dr']} x {q['dr']} — circuitos de area molhada", TXT["micro"], "start", cor="#3f6fb5")
    return yb + 90


def unifilar() -> Canvas:
    e = ci.entrada(pj)
    qs = ci.quadros(pj)
    cs = ci.circuitos(pj)
    cv = base("ELETRICA — DIAGRAMA UNIFILAR E QUADROS DE DISTRIBUICAO", "s/ escala", "60", notas=[
        f"Entrada {e['tipo']}: {e['corrente_a']} A de demanda, disjuntor geral {e['disjuntor_a']} A, "
        f"ramal {e['secao_mm2']} mm2 do medidor {e['medidor']} ao QDG em {e['comp_mm'] / 1000:.1f} m "
        f"({e['queda_pct']:.2f} % de queda).",
        "Iluminacao 1,5 mm2 / 10 A; TUG 2,5 mm2 / 20 A; TUE pela corrente (tabela 36 da NBR 5410, B1). "
        "Onde a queda passa de 4 %, a secao sobe — e a tabela diz qual.",
        "DR 30 mA para banhos, cozinha, lavanderia, garagem, area externa e chuveiros; DPS classe II no QDG.",
        "Fases equilibradas por eletrica.equilibrar (R52): a cor da fase e a do condutor.",
    ])
    # entrada
    x0, y0 = 40, 40
    cv.texto_p((x0, y0), "ENTRADA E MEDICAO", TXT["peq"], "start", peso="bold")
    cadeia = [("rede BT", "Amazonas Energia\n220/127 V"), (e["medidor"], "medidor trifasico\nna testada"),
              (f"DG {e['disjuntor_a']} A", "tripolar, curva C"), ("DPS", ci.DPS["tipo"]),
              ("QDG", f"{qs[0]['nome']}\n{e['secao_mm2']} mm2 x 4 + PE {e['aterramento_mm2']:.0f}")]
    for i, (t, sub) in enumerate(cadeia):
        x = x0 + i * 60
        cv.poli_p([(x, y0 + 6), (x + 44, y0 + 6), (x + 44, y0 + 20), (x, y0 + 20)], "corte", fechado=True, preenche="#fff")
        cv.texto_p((x + 22, y0 + 11), t, TXT["peq"], "middle", peso="bold")
        for k, l in enumerate(sub.split("\n")):
            cv.texto_p((x + 22, y0 + 15 + k * 2.8), l, TXT["micro"], "middle", cor=CINZA)
        if i < len(cadeia) - 1:
            cv.linha_p((x + 44, y0 + 13), (x + 60, y0 + 13), "vista")
    cv.texto_p((x0 + 300, y0 + 13), f"aterramento TN-S: haste + malha do SPDA (PR-41); PE {e['aterramento_mm2']:.0f} mm2",
               TXT["micro"], "start", cor=CINZA)
    # quadros
    y = _unifilar_quadro(cv, 40, 75, qs[0], [c for c in cs if c["quadro"] == "QDG"], 560)
    cv.texto_p((40, y - 8), f"alimentador do QDS: {qs[1]['alimentador']}", TXT["micro"], "start", cor=CINZA)
    y = _unifilar_quadro(cv, 40, y, qs[1], [c for c in cs if c["quadro"] == "QDS"], 320)
    # tabela dos circuitos
    linhas = [[c["cod"], c["quadro"], c["tipo"][:4], str(c["va"]), str(c["v"]), "+".join(c["fases"]),
               f"{c['ib_a']:.1f}", f"{c['disjuntor_a']} A {c['polos']}P", f"{c['secao_mm2']}" + (" *" if c["subiu_por_queda"] else ""),
               f"DN{c['eletroduto_mm']}", f"{c['comp_mm'] / 1000:.1f}", f"{c['queda_pct']:.2f}", "DR" if c["dr"] else ""]
              for c in cs]
    cab = ["CIRCUITO", "QD", "TIPO", "VA", "V", "FASE", "Ib A", "DISJ", "mm2", "ELETR.", "L m", "dV %", ""]
    lg = [26, 10, 10, 10, 8, 10, 10, 18, 10, 12, 10, 10, 6]
    _tabela(cv, (620, 40), f"CIRCUITOS — {len(cs)} (* secao subiu pela queda de tensao)", cab, linhas[:60], larguras=lg, h_lin=3.6)
    _tabela(cv, (620, 40 + 8 + 61 * 3.6), "", cab, linhas[60:], larguras=lg, h_lin=3.6) if len(linhas) > 60 else None
    # resumo dos quadros
    lin = [[q["quadro"], q["nome"][:26], str(q["circuitos"]), str(q["va"]),
            " / ".join(f"{v:.0f}" for v in q["por_fase"].values()), str(q["n_dr"]), str(q["vias_usadas"]),
            str(q["vias_com_reserva"]), str(q["vias_disponiveis"]), "cabe" if q["cabe"] else "NAO CABE"] for q in qs]
    _tabela(cv, (380, 330), "QUADROS", ["QD", "NOME", "CIRC", "VA", "VA POR FASE A/B/C", "DR", "VIAS", "+20 %", "TEM", ""],
            lin, larguras=[12, 50, 12, 14, 40, 10, 12, 14, 12, 18], h_lin=4.4)
    return cv


# =========================================================================
# PR-61 — MATERIAL POR CIRCUITO E FOTOVOLTAICA
# =========================================================================
def material_eletrico() -> Canvas:
    cs = ci.circuitos(pj)
    mat = ci.materiais(pj)
    cons = fv.consumo_dia(pj)
    kwp = cons["total"] / (fv.HSP * fv.PR)
    n_mod = math.ceil(kwp * 1000 / fv.MODULO["wp"])
    tc = next(t for t in pj.TECNICOS if "fotovoltaico" in t["nome"].lower())
    kw_inv = int("".join(ch for ch in tc["nome"].split("kW")[0] if ch.isdigit()))
    por_string = 12 if n_mod > 12 else n_mod
    n_str = math.ceil(n_mod / por_string)
    cv = base("ELETRICA — MATERIAL POR CIRCUITO E SISTEMA FOTOVOLTAICO", "s/ escala", "61", notas=[
        "Cada linha da lista de material vem da soma dos circuitos da PR-60: cabo por secao e cor "
        "(fase na cor da fase, neutro azul, PE verde), eletroduto por diametro, disjuntor por corrente e polos.",
        f"Comprimentos por percurso Manhattan do quadro ao centro do ambiente x {ci.FATOR_PERCURSO} "
        "(limite inferior declarado, como em nucleo/instalacoes) mais descida e subida.",
        f"Fotovoltaico: {cons['total']:.1f} kWh/dia -> {kwp:.1f} kWp -> {n_mod} modulos de {fv.MODULO['wp']} Wp "
        f"em {n_str} string(s), inversor {kw_inv} kW ({tc['cod']}) na faixa tecnica norte.",
        "Cabos solares 6 mm2 1,8 kV em eletroduto proprio da cobertura ao inversor; string box com fusivel, "
        "DPS CC e chave seccionadora; disjuntor CA no QDG.",
    ])
    linhas = [[m["item"][:44], f"{m['qtd']:.1f}" if isinstance(m["qtd"], float) else str(m["qtd"]), m["un"]] for m in mat]
    _tabela(cv, (30, 40), "LISTA DE MATERIAL — TOTAIS", ["ITEM", "QTD", "UN"], linhas, larguras=[100, 20, 10], h_lin=4.2)
    lin = [[c["cod"], c["quadro"], f"{c['secao_mm2']}", f"{c['cabo_m']:.1f}", f"DN{c['eletroduto_mm']}",
            f"{c['comp_mm'] / 1000:.1f}", f"{c['disjuntor_a']} A {c['polos']}P", str(c["tomadas"]), str(c["interruptores"]),
            str(c["pontos_luz"])] for c in cs]
    cab = ["CIRC", "QD", "mm2", "CABO m", "ELETR.", "m", "DISJ", "TOM", "INT", "LUZ"]
    lg = [26, 10, 8, 14, 12, 10, 18, 8, 8, 8]
    _tabela(cv, (180, 40), f"POR CIRCUITO — {len(cs)}", cab, lin[:60], larguras=lg, h_lin=3.6)
    if len(lin) > 60:
        _tabela(cv, (320, 40), "", cab, lin[60:], larguras=lg, h_lin=3.6)
    # ---- diagrama FV
    ox, oy = 470, 60
    cv.texto_p((ox, oy - 6), "SISTEMA FOTOVOLTAICO — DIAGRAMA", TXT["peq"], "start", peso="bold")
    y = oy
    for s in range(n_str):
        nm = por_string if s < n_str - 1 else n_mod - por_string * (n_str - 1)
        for k in range(nm):
            x = ox + k * 9
            cv.poli_p([(x, y), (x + 7, y), (x + 7, y + 5), (x, y + 5)], "fino", fechado=True, preenche="#1f4b8a", cor="#0d2a52")
        cv.linha_p((ox + nm * 9, y + 2.5), (ox + 140, y + 2.5), "fino", cor="#c33")
        cv.texto_p((ox + nm * 9 + 1, y + 1.5), f"string {s + 1}: {nm} x {fv.MODULO['wp']} Wp", TXT["micro"], "start", cor="#333")
        y += 12
    cv.poli_p([(ox + 140, oy - 2), (ox + 170, oy - 2), (ox + 170, y), (ox + 140, y)], "corte", fechado=True, preenche="#fff")
    cv.texto_p((ox + 155, oy + 4), "STRING BOX", TXT["micro"], "middle", peso="bold")
    for k, t in enumerate(("fusivel gPV 15 A", "DPS CC 1.000 V", "chave CC")):
        cv.texto_p((ox + 155, oy + 8 + k * 3), t, TXT["micro"], "middle", cor=CINZA)
    cv.linha_p((ox + 170, (oy + y) / 2), (ox + 190, (oy + y) / 2), "vista", cor="#c33")
    cv.poli_p([(ox + 190, oy - 2), (ox + 230, oy - 2), (ox + 230, y), (ox + 190, y)], "corte", fechado=True, preenche="#fff")
    cv.texto_p((ox + 210, oy + 4), f"INVERSOR {kw_inv} kW", TXT["micro"], "middle", peso="bold")
    cv.texto_p((ox + 210, oy + 8), f"{tc['cod']} · {tc['obs'][:30]}", TXT["micro"], "middle", cor=CINZA)
    cv.texto_p((ox + 210, oy + 11), "trifasico 220 V · anti-ilhamento", TXT["micro"], "middle", cor=CINZA)
    cv.linha_p((ox + 230, (oy + y) / 2), (ox + 250, (oy + y) / 2), "vista")
    cv.poli_p([(ox + 250, oy - 2), (ox + 290, oy - 2), (ox + 290, y), (ox + 250, y)], "corte", fechado=True, preenche="#fff")
    cv.texto_p((ox + 270, oy + 4), "QDG", TXT["micro"], "middle", peso="bold")
    cv.texto_p((ox + 270, oy + 8), f"disjuntor CA {math.ceil(kw_inv * 1000 / (math.sqrt(3) * 220) * 1.25 / 5) * 5} A tripolar", TXT["micro"], "middle", cor=CINZA)
    cv.texto_p((ox + 270, oy + 11), "medidor bidirecional (GD)", TXT["micro"], "middle", cor=CINZA)
    # passagem de cabos: da cobertura ao inversor
    x0, y0, x1, y1 = _extremos(pj.SUPERIOR)
    comp = (abs(tc["x"] - x1) + abs(tc["y"] - y0) + (pj.TOPO_PLATIBANDA - 1_500)) * 1.2
    yy = y + 14
    cv.texto_p((ox, yy), "PASSAGEM DOS CABOS SOLARES", TXT["peq"], "start", peso="bold")
    for k, t in enumerate((
            f"cobertura do superior (PIR, sem sombra) -> descida pela face norte em eletroduto PVC DN25 aparente pintado",
            f"-> {tc['cod']} a 1.500 mm do piso: {comp / 1000:.1f} m de percurso x 2 condutores + PE",
            f"estrutura: trilho de aluminio sobre a telha, presilhas intermediarias e de extremidade, 4 fixacoes por modulo; "
            f"carga {fv.MODULO['massa_kg'] * n_mod:.0f} kg em {n_mod * fv.MODULO['larg'] * fv.MODULO['comp'] / 1e6:.1f} m2",
            "aterramento dos trilhos na malha do SPDA (PR-41)")):
        cv.texto_p((ox, yy + 5 + k * 3.6), t, TXT["micro"], "start", cor="#333")
    return cv


# =========================================================================
# PR-62 — ESGOTO E VENTILACAO
# =========================================================================
def _pos_esgoto(pj):
    pos = {p["cod"]: (p["x"], p["y"]) for p in pj.pecas_hidraulicas() + pj.RALOS}
    pos.update({d["cod"]: (d["x"], d["y"]) for d in es.desconectores(pj)})
    pos.update({c["cod"]: (c["x"], c["y"]) for c in es.caixas(pj)})
    pos.update({p["cod"]: (p["x"], p["y"]) for p in pj.PRUMADAS})
    cg = es.caixa_gordura(pj); pos[cg["cod"]] = (cg["x"], cg["y"])
    return pos


def esgoto() -> Canvas:
    r = es.resumo(pj)
    cv = base("ESGOTO SANITARIO E VENTILACAO — ISOMETRICO, CAIXAS E COLETOR", "1:75 · 1:150 · 1:10", "62", notas=[
        f"Ramal de descarga por peca com DN da NBR 8160; caimento adotado 2 % em toda a rede predial "
        f"(a norma permite 1 % em DN100) — a decisao 'para nao entupir'. Coletor enterrado a 1 %.",
        f"Lavatorio, box e ralo de cada banho caem em caixa sifonada {es.CAIXA_SIFONADA['dim']}; vaso direto "
        f"ao tubo de queda ou a caixa de inspecao. {r['ventilacao_ramais']} ramais de ventilacao DN50 onde o "
        f"sifao fica alem da distancia da tabela 5.",
        f"{r['caixas']} caixas de inspecao {es.CI_DIM[0]} x {es.CI_DIM[1]} (pe de cada tubo de queda, frente, "
        f"encontros e espacamento de 15 m); fundo final a {r['prof_final_mm']:.0f} mm na testada, no sentido em "
        f"que o lote desce (R68): a profundidade nao cresce.",
        f"Caixa de gordura {es.CAIXA_GORDURA['tipo'].split(',')[0]} de {es.CAIXA_GORDURA['volume_l']} L a jusante "
        "das duas pias; tubos de queda DN100 com terminal de ventilacao 300 mm acima da cobertura.",
    ])
    pos = _pos_esgoto(pj)
    ramais = es.ramais(pj); cx = es.caixas(pj); col = es.coletor(pj); vent = es.ventilacao(pj)
    pts = []
    for rr in ramais:
        a, b = pos[rr["peca"]], pos[rr["destino"]]
        z = _z_pav(rr["pav"])
        pts += [(a[0], a[1], z), (b[0], b[1], z)]
    for c in cx:
        pts.append((c["x"], c["y"], -800))
    for v in vent["colunas"]:
        pts.append((v["x"], v["y"], v["topo"]))
    iso = _Iso(75, pts, 40, 480)
    # ramais
    for rr in ramais:
        a, b = pos[rr["peca"]], pos[rr["destino"]]
        z = _z_pav(rr["pav"])
        with cv.escopo("esgoto", rr["peca"], dn=str(rr["dn"]), destino=rr["destino"]):
            iso.manhattan(cv, (a[0], a[1], z), (b[0], b[1], z), COR_DN[rr["dn"]],
                          "vista" if rr["dn"] >= 75 else "fino")
            iso.rotulo(cv, a[0], a[1], z + 150, rr["peca"], "#333")
            if rr["classe"] == "ramal de esgoto" or rr["dn"] >= 100:
                m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                iso.rotulo(cv, b[0], m[1], z - 150, f"DN{rr['dn']} {rr['caimento'] * 100:.0f}%", COR_DN[rr["dn"]])
    # tubos de queda e colunas de ventilacao
    for p in pj.PRUMADAS:
        if p["tipo"] != "esgoto":
            continue
        iso.linha(cv, (p["x"], p["y"], pj.NIVEL_SUPERIOR + 300), (p["x"], p["y"], -500), COR_DN[100], "vista")
        iso.rotulo(cv, p["x"], p["y"], pj.NIVEL_SUPERIOR + 1_000, f"{p['cod']} TQ DN{p['dn']}", COR_DN[100])
    for v in vent["colunas"]:
        iso.linha(cv, (v["x"], v["y"], pj.NIVEL_SUPERIOR + 300), (v["x"], v["y"], v["topo"]), "#2a9d6f", "fino", dash="2 1")
        iso.rotulo(cv, v["x"], v["y"], v["topo"], f"{v['cod']} DN{v['dn']} — terminal", "#2a9d6f")
    for vr in vent["ramais"]:
        a = pos[vr["de"]]; col_ = next(c for c in vent["colunas"] if c["cod"] == vr["para"])
        pav = next(rr["pav"] for rr in ramais if rr["peca"] == vr["de"])
        z = _z_pav(pav) + 2_000
        iso.manhattan(cv, (a[0], a[1], z), (col_["x"], col_["y"], z), "#2a9d6f", "fino", dash="1 1")
    # caixas e coletor
    for c in cx:
        iso.caixa(cv, c["x"] - 300, c["y"] - 300, -800, 600, 600, 500, "#1a1026", "#efe9f6")
        iso.rotulo(cv, c["x"] + 300, c["y"], -400, c["cod"], "#1a1026")
    for t in col:
        a = next(c for c in cx if c["cod"] == t["de"]); b = next(c for c in cx if c["cod"] == t["para"])
        za = -t.get("prof_montante_mm", 500); zb = -t.get("prof_jusante_mm", 500)
        iso.linha(cv, (a["x"], a["y"], za), (b["x"], b["y"], zb), COR_DN[100], "vista")
    cg = es.caixa_gordura(pj)
    iso.caixa(cv, cg["x"] - 200, cg["y"] - 200, -600, 400, 400, 500, "#8a5a1e", "#f6ead8")
    iso.rotulo(cv, cg["x"] + 200, cg["y"], -300, f"{cg['cod']} caixa de gordura {cg['volume_l']} L", "#8a5a1e")
    # rede publica
    xc = pj.RECUO_ESQ // 2
    iso.linha(cv, (xc, 1_200, -col[-1]["prof_jusante_mm"]), (xc, -1_500, -col[-1]["prof_jusante_mm"] - 100), COR_DN[150], "vista", dash="3 2")
    iso.rotulo(cv, xc, -1_500, -col[-1]["prof_jusante_mm"], "rede publica (testada, y = 0)", "#333")
    an.titulo_desenho(cv, (40, 505), "1", "ISOMETRICO DE ESGOTO E VENTILACAO", "1:75")
    # ---- planta de caixas 1:150
    vw = View(150, 470, 300, 0, 0)
    _planta_base(cv, vw, "T", com_abertos=True)
    for c in cx:
        p = vw.pt(P(c["x"], c["y"]))
        cv.poli_p([(p[0] - 2, p[1] - 2), (p[0] + 2, p[1] - 2), (p[0] + 2, p[1] + 2), (p[0] - 2, p[1] + 2)],
                  "vista", fechado=True, preenche="#fff", cor="#1a1026")
        cv.texto_p((p[0] + 3, p[1] + 1), c["cod"], 1.6, "start", cor="#1a1026")
    for t in col:
        a = next(c for c in cx if c["cod"] == t["de"]); b = next(c for c in cx if c["cod"] == t["para"])
        cv.linha_p(vw.pt(P(a["x"], a["y"])), vw.pt(P(b["x"], b["y"])), "vista", cor=COR_DN[100])
    p = vw.pt(P(cg["x"], cg["y"])); cv.circ_p(p, 2, "vista", preenche="#f6ead8", cor="#8a5a1e")
    an.titulo_desenho(cv, (470, 320), "2", "PLANTA DE CAIXAS DE INSPECAO E COLETOR", "1:150")
    # ---- coletor com cotas
    lin = [[t["de"], t["para"], f"DN{t['dn']}", f"{t['comp_mm'] / 1000:.1f}", f"{t['caimento'] * 100:.0f} %",
            f"{t.get('cota_fundo_montante', '—')}", f"{t.get('cota_fundo_jusante', '—')}",
            f"{t.get('prof_jusante_mm', '—')}"] for t in col]
    _tabela(cv, (470, 335), "COLETOR — COTA DE FUNDO (mm, RN = piso do terreo)",
            ["DE", "PARA", "DN", "L m", "i", "FUNDO MONT.", "FUNDO JUS.", "PROF. JUS."], lin,
            larguras=[26, 26, 14, 12, 12, 24, 24, 22], h_lin=3.8)
    # ---- ramais (tabela)
    lin = [[rr["peca"], rr["amb"], rr["tipo"][:10], f"DN{rr['dn']}", str(rr["uhc"]), f"{rr['caimento'] * 100:.0f} %",
            f"{rr['comp_mm'] / 1000:.1f}", rr["destino"], "sim" if rr["ventilado"] else "VR DN50"] for rr in ramais]
    _tabela(cv, (640, 40), f"RAMAIS — {len(ramais)}", ["PECA", "AMB", "TIPO", "DN", "UHC", "i", "L m", "DESTINO", "VENT."],
            lin, larguras=[22, 16, 22, 14, 10, 10, 12, 24, 16], h_lin=3.6)
    # ---- caixa de gordura 1:10
    ox, oy = 500, 470
    vwg = View(10, ox, oy, 0, 0)
    d, h = cg["diametro"], cg["altura"]
    cv.poli_p([vwg.pt(P(0, 0)), vwg.pt(P(d, 0)), vwg.pt(P(d, h)), vwg.pt(P(0, h))], "corte", fechado=True, preenche="#fff")
    cv.poli_p([vwg.pt(P(0, h - 150)), vwg.pt(P(d, h - 150)), vwg.pt(P(d, h - 150 - 20)), vwg.pt(P(0, h - 170))],
              "fino", fechado=True, preenche="#cfe3f5", cor="#3f6fb5")
    cv.poli_p([vwg.pt(P(d / 2 - 10, h - 100)), vwg.pt(P(d / 2 + 10, h - 100)), vwg.pt(P(d / 2 + 10, h - 150 - cg["septo_submerso"])),
               vwg.pt(P(d / 2 - 10, h - 150 - cg["septo_submerso"]))], "corte", fechado=True, preenche="#999")
    cv.texto_p(vwg.pt(P(d / 2, h - 60)), "septo", TXT["micro"], "middle")
    cv.linha_p(vwg.pt(P(-100, h - 150)), vwg.pt(P(0, h - 150)), "vista", cor=COR_DN[75])
    cv.texto_p(vwg.pt(P(-110, h - 120)), f"entrada DN{cg['entrada']}", TXT["micro"], "end")
    cv.linha_p(vwg.pt(P(d, h - 180)), vwg.pt(P(d + 100, h - 180)), "vista", cor=COR_DN[75])
    cv.texto_p(vwg.pt(P(d + 110, h - 150)), f"saida DN{cg['saida']}", TXT["micro"], "start")
    an.cadeia(cv, vwg, [0, d], 0, "H", 6)
    an.cadeia(cv, vwg, [0, h - 150 - cg["septo_submerso"], h - 150, h], d, "V", 8)
    an.titulo_desenho(cv, (ox - 10, oy + 22), "3", f"CAIXA DE GORDURA {cg['volume_l']} L — {cg['tampa']}", "1:10")
    return cv


# =========================================================================
# PR-63 — AGUA FRIA
# =========================================================================
def agua_fria() -> Canvas:
    r = ag.resumo(pj)
    res = r["reservatorio"]
    col = ag.coluna(pj); ram = ag.ramais(pj); pcs = ag.pecas(pj); regs = ag.registros(pj)
    afc = next(p for p in pj.PRUMADAS if p["tipo"] == "agua fria")
    cv = base("AGUA FRIA — ISOMETRICO, DIAGRAMA VERTICAL, PRESSOES E REGISTROS", "1:75", "63", notas=[
        f"Reservatorio de {res['volume_l']} L com fundo a +{res['nivel_fundo'] / 1000:.2f} m; barrilete DN{col[0]['dn']} "
        f"a +{res['z_barrilete'] / 1000:.2f} m; coluna AF-01 DN{col[0]['dn']}.",
        f"Pressao dinamica = estatica (lamina minima {ag.NIVEL_MIN_ACIMA_FUNDO} mm sobre o fundo) menos as perdas "
        f"por Fair-Whipple-Hsiao (PVC) com {int((ag.FATOR_LOCALIZADAS - 1) * 100)} % de localizadas; minimo {ag.PRESSAO_MIN_KPA:.0f} kPa (NBR 5626).",
        f"Terreo: pior peca com {r['pior_terreo']:.0f} kPa — passa por gravidade. Superior: pior peca com "
        f"{r['pior_superior']:.0f} kPa — {r['pressurizadas']} pecas so funcionam com o pressurizador TC-14. "
        "E a conta, nao a frase, que justifica o equipamento.",
        "Registro de gaveta na entrada de cada ramal; registro de pressao em cada chuveiro; geral com retencao no barrilete.",
    ])
    pts = [(res["x"], res["y"], res["nivel_fundo"] + 1_000), (afc["x"], afc["y"], 0)]
    for p in pcs:
        pts.append((p["cod"] and pj.pecas_hidraulicas()[0]["x"], 0, 0))
    pos = {p["cod"]: (p["x"], p["y"]) for p in pj.pecas_hidraulicas()}
    for p in pcs:
        pts.append((pos[p["cod"]][0], pos[p["cod"]][1], p["z_mm"]))
    iso = _Iso(75, pts, 40, 480)
    cd = pj.CAIXA_DAGUA
    iso.caixa(cv, cd["x"], cd["y"], cd["nivel_base"], cd["w"], cd["h"], 1_000, "#1f4b8a", "#e8f1fb")
    iso.rotulo(cv, cd["x"] + cd["w"], cd["y"], cd["nivel_base"] + 1_100, f"reservatorio {cd['volume_l']} L", "#1f4b8a")
    zb = res["z_barrilete"]
    iso.manhattan(cv, (res["x"], res["y"], cd["nivel_base"]), (res["x"], res["y"], zb), COR_AF[col[0]["dn"]], "vista")
    iso.manhattan(cv, (res["x"], res["y"], zb), (afc["x"], afc["y"], zb), COR_AF[col[0]["dn"]], "vista")
    iso.rotulo(cv, (res["x"] + afc["x"]) / 2, afc["y"], zb + 200, f"barrilete DN{col[0]['dn']} · {col[0]['registro']}", COR_AF[col[0]["dn"]])
    iso.linha(cv, (afc["x"], afc["y"], zb), (afc["x"], afc["y"], 2_400), COR_AF[col[0]["dn"]], "vista")
    iso.rotulo(cv, afc["x"], afc["y"], 4_500, f"AF-01 DN{col[0]['dn']}", COR_AF[col[0]["dn"]])
    amb_c = {}
    for p in pj.pecas_hidraulicas():
        amb_c.setdefault(p["amb"], []).append((p["x"], p["y"]))
    for rr in ram:
        z = _z_pav(rr["pav"]) + 2_400
        cxy = amb_c[rr["amb"]]
        cx_, cy_ = sum(a for a, _ in cxy) / len(cxy), sum(b for _, b in cxy) / len(cxy)
        with cv.escopo("agua", rr["cod"], dn=str(rr["dn"])):
            iso.manhattan(cv, (afc["x"], afc["y"], z), (cx_, cy_, z), COR_AF[rr["dn"]], "vista")
            q = iso.pt(afc["x"] + (cx_ - afc["x"]) * 0.15, afc["y"], z)
            cv.circ_p(q, 1.2, "vista", preenche="#fff", cor="#333")
            iso.rotulo(cv, cx_, cy_, z + 150, f"{rr['cod']} DN{rr['dn']} · {rr['pesos']} p", COR_AF[rr["dn"]])
        for p in pcs:
            if p["amb"] != rr["amb"]:
                continue
            x, y = pos[p["cod"]]
            iso.manhattan(cv, (cx_, cy_, z), (x, y, z), COR_AF[p["dn_sub"]], "fino")
            iso.linha(cv, (x, y, z), (x, y, p["z_mm"]), COR_AF[p["dn_sub"]], "fino")
            iso.rotulo(cv, x, y, p["z_mm"], f"{p['cod']} {p['dinamica_kpa']:.0f} kPa" + ("" if p["gravidade_ok"] else " *"),
                       "#c0392b" if not p["gravidade_ok"] else "#333")
    an.titulo_desenho(cv, (40, 505), "1", "ISOMETRICO DE AGUA FRIA (* abaixo de 10 kPa por gravidade: pressurizado)", "1:75")
    # ---- diagrama vertical
    ox, oy = 470, 60
    cv.texto_p((ox, oy - 6), "DIAGRAMA VERTICAL", TXT["peq"], "start", peso="bold")
    esc = 40
    def zp(z): return oy + (7_500 - z) / esc
    cv.poli_p([(ox + 40, zp(cd["nivel_base"] + 1_000)), (ox + 80, zp(cd["nivel_base"] + 1_000)), (ox + 80, zp(cd["nivel_base"])), (ox + 40, zp(cd["nivel_base"]))],
              "corte", fechado=True, preenche="#e8f1fb")
    cv.texto_p((ox + 60, zp(cd["nivel_base"] + 500)), "RES.", TXT["micro"], "middle")
    cv.linha_p((ox + 60, zp(cd["nivel_base"])), (ox + 60, zp(zb)), "vista", cor="#1f4b8a")
    cv.linha_p((ox + 60, zp(zb)), (ox + 120, zp(zb)), "vista", cor="#1f4b8a")
    cv.texto_p((ox + 90, zp(zb) - 1.5), f"barrilete DN{col[0]['dn']}", TXT["micro"], "middle", cor="#1f4b8a")
    cv.linha_p((ox + 120, zp(zb)), (ox + 120, zp(2_400)), "vista", cor="#1f4b8a")
    for pav, z, dn in (("S", pj.NIVEL_SUPERIOR + 2_400, col[1]["dn"]), ("T", 2_400, col[2]["dn"])):
        cv.linha_p((ox + 120, zp(z)), (ox + 300, zp(z)), "fino", cor="#3f6fb5")
        cv.texto_p((ox + 122, zp(z) - 1.5), f"ramais do {'superior' if pav == 'S' else 'terreo'} · coluna DN{dn}", TXT["micro"], "start", cor="#3f6fb5")
        xs = ox + 130
        for rr in [x for x in ram if x["pav"] == pav]:
            cv.linha_p((xs, zp(z)), (xs, zp(z) + 6), "fino", cor="#3f6fb5")
            cv.texto_p((xs + 1, zp(z) + 6), f"{rr['amb']} DN{rr['dn']}", 1.5, "start", rot=90, cor="#333")
            xs += 18
        cv.linha_p((ox + 20, zp(z - 2_400)), (ox + 300, zp(z - 2_400)), "cota", cor="#999", dash="2 2")
        cv.texto_p((ox + 20, zp(z - 2_400) - 1), f"piso {'superior' if pav == 'S' else 'terreo'} +{(z - 2_400) / 1000:.2f}", TXT["micro"], "start", cor="#666")
    # ---- pressoes
    lin = [[p["cod"], p["amb"], p["tipo"][:10], f"{p['z_mm']}", f"DN{p['dn_sub']}", f"{p['estatica_kpa']:.0f}",
            f"{p['perdas_kpa']:.0f}", f"{p['dinamica_kpa']:.0f}", "gravidade" if p["gravidade_ok"] else "TC-14"] for p in pcs]
    _tabela(cv, (470, 240), "PRESSAO EM CADA PECA (kPa)", ["PECA", "AMB", "TIPO", "z mm", "SUB", "ESTAT.", "PERDAS", "DINAM.", "COMO"],
            lin, larguras=[20, 16, 22, 14, 14, 16, 16, 16, 20], h_lin=3.6)
    lin = [[g["cod"], g["onde"][:36], g["tipo"][:34]] for g in regs]
    _tabela(cv, (640, 240), f"REGISTROS — {len(regs)}", ["COD", "ONDE", "TIPO"], lin, larguras=[24, 76, 70], h_lin=3.6)
    lin = [[c["cod"], f"DN{c['dn']}", f"{c['pesos']}", f"{c['q_ls']}", f"{c['comp_mm'] / 1000:.1f}", f"{c['perda_kpa']}"] for c in col] + \
          [[x["cod"], f"DN{x['dn']}", f"{x['pesos']}", f"{x['q_ls']}", f"{x['comp_mm'] / 1000:.1f}", f"{x['perda_kpa']}"] for x in ram]
    _tabela(cv, (470, 330), "TRECHOS — BARRILETE, COLUNA E RAMAIS", ["TRECHO", "DN", "PESOS", "Q L/s", "L m", "PERDA kPa"],
            lin, larguras=[28, 14, 16, 16, 14, 20], h_lin=3.6)
    return cv


# =========================================================================
# PR-64 — PLUVIAL, GAS, AR NOVO E SUPORTES
# =========================================================================
def complementares() -> Canvas:
    g = gs.rede(pj); rn = gs.renovacao(pj); sp = gs.suportes(pj)
    cb = pj.COBERTURA
    cv = base("PLUVIAL EM ISOMETRICO, GAS, RENOVACAO DE AR E SUPORTES", "1:150 · s/ escala", "64", notas=[
        f"Pluvial: {cb['descidas']} descidas DN{cb['dn_descida']} nos cantos da cobertura para caixas de areia, "
        "tubulacao enterrada DN100 a 1 % pelo perimetro ate a retencao TC-03 e dela a sarjeta (PR-29 e PR-38).",
        f"Gas: central {g['central']['nome']} ({g['central']['cod']}) a {gs.ABRIGO['afastamento_vao_mm'] / 1000:.1f} m de vaos; "
        f"{g['tubo']['material']} DN{g['tubo']['dn']}; {g['regulador']}; {g['comp_total_mm'] / 1000:.1f} m de rede para "
        f"{g['potencia_kw']} kW; autonomia de {g['autonomia_dias']:.0f} dias a 2 h/dia de uso pleno (H).",
        f"Renovacao de ar: {gs.AR_NOVO_LS_PESSOA} L/s por pessoa + {gs.AR_NOVO_LS_M2} L/s por m2 (H). Sem VMC: a vazao "
        "requerida fica declarada por ambiente e a renovacao e por janela e exaustor.",
        f"Suportes: {sp['suporte']}; {sp['regra']}. {sp['bombas']}.",
        "Ruido nos dormitorios: Lp = Lw - 20 log d - 8 na janela (sem credito do painel ripado), "
        f"dentro com a janela fechada Lp - (Rw {gs.RW_JANELA:.0f} - 3); limite {gs.LIMITE_DORMITORIO:.0f} dB(A) (NBR 10152).",
    ])
    # ---- pluvial iso 1:150
    x0, y0, x1, y1 = _extremos(pj.cobertos())
    zt = pj.TOPO_PLATIBANDA
    tc3 = next(t for t in pj.TECNICOS if t["cod"] == "TC-03")
    desc = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
    pts = [(x, y, zt) for x, y in desc] + [(tc3["x"], tc3["y"], -1_400), (x1 + 1_500, 0, 0), (x0 - 1_500, y1 + 1_500, 0)]
    iso = _Iso(150, pts, 40, 300)
    for a in pj.cobertos():
        iso.caixa(cv, a.x, a.y, zt - 200, a.w, a.h, 0, "#bbb", "#f4f4f4")
    for i, (x, y) in enumerate(desc, 1):
        iso.linha(cv, (x, y, zt), (x, y, -400), COR_PLUV, "vista")
        iso.rotulo(cv, x, y, zt + 300, f"D{i} DN{cb['dn_descida']}", COR_PLUV)
        iso.caixa(cv, x - 200, y - 200, -700, 400, 400, 300, COR_PLUV)
        # pelo perimetro ate o eixo do acesso (x do TC-03), depois ate a caixa
        lado = x0 - 1_000 if x == x0 else x1 + 1_000
        iso.manhattan(cv, (x, y, -600), (lado, y, -600), COR_PLUV, "fino")
        iso.manhattan(cv, (lado, y, -600), (lado, tc3["y"] + tc3["h"] / 2, -900), COR_PLUV, "fino")
        iso.manhattan(cv, (lado, tc3["y"] + tc3["h"] / 2, -900), (tc3["x"] + tc3["w"] / 2, tc3["y"] + tc3["h"] / 2, -1_000), COR_PLUV, "fino")
    iso.caixa(cv, tc3["x"], tc3["y"], -tc3["prof"], tc3["w"], tc3["h"], tc3["prof"] - 200, COR_PLUV, "#e3f4f6")
    iso.rotulo(cv, tc3["x"] + tc3["w"], tc3["y"], -200, f"{tc3['cod']} retencao — orificio calibrado", COR_PLUV)
    iso.manhattan(cv, (tc3["x"] + tc3["w"] / 2, tc3["y"], -1_200), (tc3["x"] + tc3["w"] / 2, -800, -1_300), COR_PLUV, "vista", dash="3 2")
    iso.rotulo(cv, tc3["x"] + tc3["w"] / 2, -800, -1_100, "sarjeta", COR_PLUV)
    an.titulo_desenho(cv, (40, 322), "1", "ISOMETRICO PLUVIAL — DESCIDAS, CAIXAS DE AREIA, RETENCAO E SARJETA", "1:150")
    # ---- gas: planta 1:150
    vw = View(150, 340, 300, 0, 0)
    _planta_base(cv, vw, "T", com_abertos=True)
    c = g["central"]
    p = vw.pt(P(c["x"] + 600, c["y"] + 400))
    cv.poli_p([(p[0] - 4, p[1] - 3), (p[0] + 4, p[1] - 3), (p[0] + 4, p[1] + 3), (p[0] - 4, p[1] + 3)], "vista", fechado=True, preenche="#fbe9d2", cor=COR_GAS)
    cv.texto_p((p[0], p[1] - 4), c["cod"], TXT["micro"], "middle", cor=COR_GAS)
    x_par = max(a.x + a.w for a in pj.TERREO)
    for pt_, t in zip(g["pontos"], g["trechos"]):
        a = vw.pt(P(c["x"], c["y"] + 400)); b = vw.pt(P(x_par, pt_["y"])); d = vw.pt(P(pt_["x"], pt_["y"]))
        cv.linha_p(a, (a[0], b[1]), "vista", cor=COR_GAS); cv.linha_p((a[0], b[1]), b, "vista", cor=COR_GAS); cv.linha_p(b, d, "vista", cor=COR_GAS)
        cv.circ_p(d, 1.6, "vista", preenche="#fff", cor=COR_GAS)
        cv.texto_p((d[0] + 2.5, d[1] + 1), f"{pt_['cod']} {pt_['tipo']} {pt_['kw']} kW", TXT["micro"], "start", cor=COR_GAS)
    an.titulo_desenho(cv, (340, 322), "2", "REDE DE GAS — CENTRAL, PERCURSO E PONTOS", "1:150")
    # abrigo
    lin = [["norma", c["norma"]], ["afastamento de vaos", f"{c['afastamento_vao_mm']} mm"],
           ["afastamento de ignicao", f"{c['afastamento_ignicao_mm']} mm"], ["ventilacao", c["ventilacao"]],
           ["piso", c["piso"]], ["porta", c["porta"]], ["tubo", f"{g['tubo']['material']} DN{g['tubo']['dn']}, {g['tubo']['uniao']}"],
           ["protecao", g["tubo"]["protecao"]], ["regulador", g["regulador"]],
           ["registros", "; ".join(f"{p['cod']}: {p['registro']}" for p in g["pontos"])]]
    _tabela(cv, (340, 340), "ABRIGO, TUBULACAO E REGISTROS DE GAS", ["ITEM", "ESPECIFICACAO"], lin, larguras=[40, 220], h_lin=4.2)
    # renovacao
    lin = [[x["amb"], x["compartimento"], str(x["pessoas"]), f"{x['area_m2']}", f"{x['q_ls']}", f"{x['q_m3h']:.0f}", x["como"][:40]] for x in rn]
    _tabela(cv, (640, 40), "RENOVACAO DE AR — VAZAO REQUERIDA", ["AMB", "COMP.", "PES.", "m2", "L/s", "m3/h", "COMO"],
            lin, larguras=[16, 20, 10, 12, 12, 12, 90], h_lin=3.8)
    lf = pj.linhas_frigorigenas()
    lin = [[l["cod"], l["nicho"], f"{l['comp'] / 1000:.1f}", f"{l['horizontal'] / 1000:.1f}", f"{l['subida'] / 1000:.1f}",
            str(math.ceil(l["horizontal"] / gs.ABRAC_H) + math.ceil(l["subida"] / gs.ABRAC_V)), "reserva" if l.get("reserva") else ""] for l in lf]
    _tabela(cv, (640, 120), f"SUPORTES — {sp['condensadoras']} condensadoras no piso sobre isoladores, {sp['abracadeiras']} abracadeiras",
            ["LINHA", "NICHO", "L m", "HOR.", "SUB.", "ABRAC.", ""], lin, larguras=[24, 16, 12, 12, 12, 14, 16], h_lin=3.8)
    cv.texto_p((640, 180), f"isolamento elastomerico 9 mm: {sp['isolamento_m']} m (ida e volta)", TXT["micro"], "start", cor=CINZA)
    ru = gs.ruido(pj)
    lin = [[r["fonte"], f"{r['lw']:.0f}", r["janela"], r["amb"], f"{r['d_m']}", f"{r['lp_janela']:.0f}", f"{r['lp_dentro']:.0f}",
            "ok" if r["ok"] else "ACIMA"] for r in ru[:26]]
    _tabela(cv, (640, 190), "RUIDO DAS FONTES EXTERNAS NOS DORMITORIOS — dB(A)", ["FONTE", "Lw", "JANELA", "AMB", "d m", "JANELA", "DENTRO", ""],
            lin, larguras=[18, 12, 14, 16, 12, 16, 16, 14], h_lin=3.6)
    return cv
