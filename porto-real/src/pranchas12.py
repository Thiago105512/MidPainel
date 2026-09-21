"""R74 — LOTE 4 DO BACKLOG: DADOS, CFTV, ALARME, AUTOMACAO E INCENDIO.

  65  DADOS, WI-FI, CFTV, ALARME E AUTOMACAO — plantas com cada ponto, cabo
      ate o rack, cobertura e as tabelas (316-338)
  66  PREVENCAO CONTRA INCENDIO — extintores, detectores, manta e gas, com a
      exigencia declarada como boa pratica (339-346)
Tudo sai de nucleo/seguranca.
"""
from __future__ import annotations

import projeto as pj
import anotacao as an
import nucleo.seguranca as sg
from core import P, Canvas, View, TXT, CINZA
from pranchas import base, _tabela
from pranchas11 import _planta_base

COR = dict(dados="#1f6f8b", wifi="#2a9d8f", cam="#7b2d8e", mag="#c0392b", ivp="#e67e22", aut="#6c5ce7",
           ext="#c0392b", det="#d35400")


def _sim(cv, vw, x, y, letra, cor, r=2.0, quad=False):
    c = vw.pt(P(x, y))
    if quad:
        cv.poli_p([(c[0] - r, c[1] - r), (c[0] + r, c[1] - r), (c[0] + r, c[1] + r), (c[0] - r, c[1] + r)],
                  "vista", fechado=True, preenche="#fff", cor=cor)
    else:
        cv.circ_p(c, r, "vista", preenche="#fff", cor=cor)
    cv.texto_p((c[0], c[1] + 0.7), letra, 1.6, "middle", cor=cor)
    return c


def seguranca_eletronica() -> Canvas:
    r = sg.resumo(pj)
    cv = base("DADOS, WI-FI, CFTV, ALARME E AUTOMACAO", "1:100", "65", notas=[
        f"Rack TC-07 na garagem: {r['pontos_dados']} pontos RJ45 Cat.6, {r['access_points']} access points, "
        f"{r['cameras']} cameras IP PoE; {r['cabo_utp_m']:.0f} m de UTP por percurso Manhattan x {sg.FATOR_PERCURSO} "
        f"(maximo {sg.CABO_MAX / 1000:.0f} m por lance). Wi-Fi: raio de {sg.RAIO_WIFI / 1000:.0f} m em planta (H); "
        f"{r['cobertos']} de {r['ambientes']} ambientes cobertos.",
        f"Alarme: {r['magneticos']} sensores magneticos (todo vao externo de porta), {r['ivp']} IVP nos ambientes de passagem, "
        "sirene externa, central no rack; videoporteiro e fechadura eletrica no portao de pedestre, biometrica na P01.",
        f"Automacao (H): {sg.PROTOCOLO}. {r['modulos_automacao']} modulos nos circuitos de iluminacao social e externa, "
        f"{r['cortinas']} cortinas blackout motorizadas, presenca nas circulacoes, 4 cenas.",
        "Simbolos: D dados · W access point · C camera · M magnetico · P presenca · A modulo de automacao · K cortina.",
    ])
    pd = sg.pontos_dados(pj); aps = sg.access_points(pj); cams = sg.cameras(pj); al = sg.alarme(pj); au = sg.automacao(pj)
    ambs = {a.cod: a for a in pj.TERREO + pj.SUPERIOR}
    rack = sg._rack(pj)
    for pav, vw, tit, num in (("T", View(100, 40, 470, 0, 0), "TERREO E LOTE", "1"),
                              ("S", View(100, 270, 470, pj.RECUO_ESQ, pj.RECUO_FRENTE), "SUPERIOR", "2")):
        _planta_base(cv, vw, pav, com_abertos=(pav == "T"))
        if pav == "T":
            c = vw.pt(P(rack["x"], rack["y"]))
            cv.poli_p([(c[0] - 2.5, c[1] - 2.5), (c[0] + 2.5, c[1] - 2.5), (c[0] + 2.5, c[1] + 2.5), (c[0] - 2.5, c[1] + 2.5)],
                      "corte", fechado=True, preenche="#dfe9f2")
            cv.texto_p((c[0] + 3.5, c[1] + 1), "RACK TC-07", TXT["micro"], "start", peso="bold")
            for cm in cams:
                with cv.escopo("cftv", cm["cod"], onde=cm["onde"]):
                    p = _sim(cv, vw, cm["x"], cm["y"], "C", COR["cam"], 2.2, quad=True)
                    cv.texto_p((p[0] + 3, p[1] + 1), cm["cod"], 1.5, "start", cor=COR["cam"])
            for a in al["acesso"]:
                p = _sim(cv, vw, a["x"], a["y"] + 400, a["cod"][:2], "#333", 2.0)
        for p_ in pd:
            if p_["pav"] == pav:
                with cv.escopo("dados", p_["cod"], uso=p_["uso"]):
                    _sim(cv, vw, p_["x"], p_["y"], f"D{p_['n']}", COR["dados"])
        # o raio de cobertura fica recortado na planta: fora dela nao ha o que cobrir
        a0 = vw.pt(P(0 if pav == "T" else pj.RECUO_ESQ, pj.LOTE_P if pav == "T" else 30_000))
        a1 = vw.pt(P(pj.LOTE_L, 0 if pav == "T" else pj.RECUO_FRENTE))
        with cv.recorte(a0[0], a0[1], a1[0], a1[1]):
            for ap in aps:
                if ap["pav"] == pav:
                    p = vw.pt(P(ap["x"], ap["y"]))
                    cv.circ_p(p, sg.RAIO_WIFI / 100, "cota", preenche="none", cor=COR["wifi"])
        for ap in aps:
            if ap["pav"] == pav:
                _sim(cv, vw, ap["x"], ap["y"], "W", COR["wifi"], 2.4)
        for m in al["magneticos"]:
            if m["pav"] == pav:
                _sim(cv, vw, m["x"], m["y"], "M", COR["mag"], 1.6)
        for i in al["ivp"]:
            if i["pav"] == pav:
                _sim(cv, vw, i["x"] + 600, i["y"] + 600, "P", COR["ivp"], 1.6)
        for m in au["modulos"]:
            a = ambs.get(m["amb"])
            if a is not None and (a.cod.startswith("S-")) == (pav == "S"):
                _sim(cv, vw, a.x + 600, a.y + a.h - 600, "A", COR["aut"], 1.6)
        for k in au["cortinas"]:
            a = ambs[k["amb"]]
            if (a.cod.startswith("S-")) == (pav == "S"):
                _sim(cv, vw, a.x + a.w - 600, a.y + 600, "K", COR["aut"], 1.6)
        an.titulo_desenho(cv, (vw.ox, 500), num, f"DADOS, CFTV, ALARME E AUTOMACAO — {tit}", "1:100")
    lin = [[p_["cod"], p_["amb"], p_["uso"], str(p_["n"]), f"{p_['cabo_mm'] / 1000:.1f}"] for p_ in pd] + \
          [[a["cod"], a["amb"], a["onde"][:24], "1", f"{a['cabo_mm'] / 1000:.1f}"] for a in aps]
    y = _tabela(cv, (480, 40), "PONTOS DE DADOS E ACCESS POINTS", ["COD", "AMB", "USO", "N", "CABO m"], lin,
                larguras=[28, 18, 44, 8, 16], h_lin=3.8)
    lin = [[c["cod"], c["onde"][:30], c["olha"][:30], f"{c['cabo_mm'] / 1000:.1f}"] for c in cams]
    y = _tabela(cv, (480, y + 6), "CAMERAS — " + cams[0]["tipo"], ["COD", "ONDE", "OLHA", "CABO m"], lin,
                larguras=[20, 60, 60, 16], h_lin=3.8)
    lin = [[a["cod"], a["onde"], a["item"][:44]] for a in al["acesso"]] + [["CENTRAL", "rack", al["central"][:44]]]
    y = _tabela(cv, (480, y + 6), f"ACESSO E ALARME — {al['zonas']} zonas", ["COD", "ONDE", "ITEM"], lin, larguras=[20, 40, 96], h_lin=3.8)
    lin = [[m["cod"][:16], m["amb"], m["tipo"][:40]] for m in au["modulos"]] + [[k["cod"], k["amb"], k["tipo"][:40]] for k in au["cortinas"]] + \
          [[s["cod"], s["amb"], s["tipo"][:40]] for s in au["sensores"]]
    y = _tabela(cv, (480, y + 6), "AUTOMACAO — MODULOS, CORTINAS E SENSORES", ["COD", "AMB", "TIPO"], lin, larguras=[30, 18, 108], h_lin=3.6)
    for k, c in enumerate(au["cenas"]):
        cv.texto_p((480, y + 8 + k * 3.4), f"cena {k + 1}: {c}", TXT["micro"], "start", cor="#333")
    return cv


def incendio() -> Canvas:
    inc = sg.incendio(pj)
    cv = base("PREVENCAO CONTRA INCENDIO — EXTINTORES, DETECTORES E GAS", "1:100", "66", notas=[
        inc["exigencia"],
        f"{len(inc['extintores'])} x {sg.EXTINTOR}: garagem, cozinha e hall superior — um por pavimento mais a garagem.",
        f"{len(inc['detectores'])} detectores: fumaca em cada dormitorio e circulacao ({sg.DETECTOR}); calor na cozinha.",
        "Manta antichamas na cozinha e no gourmet; detector de GLP junto ao cooktop com corte na central (PR-64).",
        "Simbolos: E extintor · F detector de fumaca · Q detector de calor.",
    ])
    for pav, vw, tit, num in (("T", View(100, 40, 470, 0, 0), "TERREO", "1"),
                              ("S", View(100, 270, 470, pj.RECUO_ESQ, pj.RECUO_FRENTE), "SUPERIOR", "2")):
        _planta_base(cv, vw, pav, com_abertos=(pav == "T"))
        for e in inc["extintores"]:
            if e["pav"] == pav:
                with cv.escopo("incendio", e["cod"], amb=e["amb"]):
                    p = _sim(cv, vw, e["x"], e["y"], "E", COR["ext"], 2.4, quad=True)
                    cv.texto_p((p[0] + 3.2, p[1] + 1), e["cod"], 1.5, "start", cor=COR["ext"])
        for d in inc["detectores"]:
            if d["pav"] == pav:
                with cv.escopo("incendio", d["cod"], amb=d["amb"]):
                    _sim(cv, vw, d["x"], d["y"], "Q" if d["cod"].startswith("DC") else "F", COR["det"], 1.8)
        an.titulo_desenho(cv, (vw.ox, 500), num, f"INCENDIO — {tit}", "1:100")
    lin = [[e["cod"], e["amb"], e["item"][:60]] for e in inc["extintores"]] + \
          [[d["cod"], d["amb"], d["tipo"][:60]] for d in inc["detectores"]] + \
          [[o["cod"], o["amb"], o["item"][:60]] for o in inc["outros"]]
    _tabela(cv, (480, 40), "EQUIPAMENTOS", ["COD", "AMB", "ITEM"], lin, larguras=[22, 18, 120], h_lin=4.0)
    return cv
