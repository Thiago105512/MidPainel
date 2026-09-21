"""R80 — POR ONDE PASSAM OS FIOS E OS TUBOS, E O QUE OS SEGURA.

  73  ELETRICA: PONTOS, PERCURSOS E FIXADORES — cada tomada, interruptor,
      luminaria e TUE com coordenada e altura; o eletroduto de cada circuito
      parede a parede (arvore), o ponto mais longe e a queda; buchas, clips,
      abracadeiras e caixas contados (229, 586)
  74  AGUA E ESGOTO: PERCURSO OCULTO, FUROS E FIXADORES — o PEX de cada peca
      pela parede a 400 mm, o esgoto sob o piso, os paineis que ganham furo
      hidraulico, o que cada parede esconde e onde nao furar (585, 587)
  75  CLIMATIZACAO EM ISOMETRICO, MAPA DE TESTES E PONTOS CRITICOS — as
      linhas frigorigenas do nicho ao evaporador em isometrico; o teste de
      cada sistema com fase, criterio e registro; os pontos criticos (313,
      541-543, 561-568)
Tudo sai de nucleo/pontos, nucleo/percurso e nucleo/testes.
"""
from __future__ import annotations

import projeto as pj
import anotacao as an
import nucleo.pontos as pt
import nucleo.percurso as pr
import nucleo.testes as ts
from core import P, Canvas, View, TXT, CINZA
from pranchas import base, _tabela
from pranchas6 import _fundo
from pranchas11 import _Iso

COR = {"iluminacao": "#e0a800", "tug": "#c00", "tue": "#1f4b8a", "agua": "#06c", "esgoto": "#8a5a2b", "frigorigena": "#7a4fd0"}


def _fm(mm, nd=1) -> str:
    return f"{mm / 1000:.{nd}f}".replace(".", ",")


def _tipo_circ(cod: str) -> str:
    return "iluminacao" if cod.startswith("ILU") else ("tug" if cod.startswith("TUG") else "tue")


def _rota(cv, vw, trechos, cor, dash_planos=("forro", "entrepiso", "enterrado", "radier")):
    for t in trechos:
        a, b = t["de"], t["para"]
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) < 1:
            continue
        cv.linha_p(vw.pt(P(a[0], a[1])), vw.pt(P(b[0], b[1])), "fino", cor=cor, dash="1.2,0.8" if t["plano"] in dash_planos else None)


def _plantas(cv, desenhar, titulo):
    for pav, ox, num in (("T", 40, "1"), ("S", 320, "2")):
        vw = View(75, ox, 350, 1_800, 6_800)
        an.titulo_desenho(cv, (ox - 10, 372), num, f"{titulo} — {'TERREO' if pav == 'T' else 'SUPERIOR'}", "1:75")
        _fundo(cv, vw, pav)
        desenhar(cv, vw, pav)


# =========================================================================
# PR-73 — ELETRICA
# =========================================================================
def eletrica_pontos_percursos() -> Canvas:
    import nucleo.circuitos as ci
    t = pt.todos(pj)
    arv = pr.arvores_eletrica(pj)
    fx = pr.fixadores(pj)
    r = pr.resumo(pj)
    rp = pt.resumo(pj)
    cs = {c["cod"]: c for c in ci.circuitos(pj)}
    cv = base("ELETRICA: PONTOS, PERCURSOS E FIXADORES", "1:75", "73", notas=[
        f"{rp['tomadas']} pontos de tomada ({sum(x['n'] for x in t['tomadas'])} tomadas, {rp['duplas']} duplos, {rp['bancada']} de bancada a 1.100 mm), "
        f"{rp['interruptores']} interruptores ({rp['paralelos']} paralelos), {rp['luminarias']} luminarias, {rp['tue']} pontos de TUE — "
        "todos com x, y, z e parede (nucleo/pontos).",
        f"Eletroduto DENTRO da parede a {pr.Z_ELETRICA} mm, pelos furos de servico dos montantes; sobe ao forro para luminaria e ventilador; "
        f"sai enterrado a {-pr.Z_ENTERRADO} mm para bombas e portao. {r['eletroduto_m']} m de eletroduto em {r['circuitos']} arvores; "
        f"ponto mais longe {r['mais_longo']} a {r['mais_longo_m']} m do quadro.",
        f"Fixadores (H): bucha passa-fio em cada um dos {r['montantes_eletrica']} montantes atravessados; clip a cada {pr.PASSO_MONTANTE_CLIP} mm; "
        f"abracadeira a cada {pr.PASSO_ABRAC_FORRO} mm no forro; caixa 4x2 em tomada e interruptor, 4x4 em luminaria e TUE; "
        f"caixa de passagem a cada {pr.CAIXA_PASSAGEM_M // 1000} m (NBR 5410 6.2.11).",
        "Linhas: amarelo iluminacao, vermelho TUG, azul TUE; tracejado no forro, entrepiso ou enterrado. Cota da tomada so quando difere de 300 mm.",
    ])

    def desenhar(cv, vw, pav):
        with cv.escopo("percurso", f"ELE-{pav}"):
            for g in arv:
                if g["pav"] != pav:
                    continue
                _rota(cv, vw, g["trechos_parede"] + g["proprios"], COR[_tipo_circ(g["circuito"])])
            for q in ("TC-05", "TC-06"):
                tq = next(x for x in pj.TECNICOS if x["cod"] == q)
                if (q == "TC-05") == (pav == "T"):
                    cv.poli_p([vw.pt(P(tq["x"], tq["y"])), vw.pt(P(tq["x"] + tq["w"], tq["y"])), vw.pt(P(tq["x"] + tq["w"], tq["y"] + tq["h"])),
                               vw.pt(P(tq["x"], tq["y"] + tq["h"]))], "vista", fechado=True, preenche="#1f4b8a", cor="#1f4b8a")
                    cv.texto_p(vw.pt(P(tq["x"] - 250, tq["y"] + tq["h"] / 2)), q, TXT["micro"], "end", cor="#1f4b8a", rot=90)
        for x in t["tomadas"]:
            if x["pav"] != pav:
                continue
            with cv.escopo("ponto", x["cod"], amb=x["amb"], z=str(x["z"]), n=str(x["n"])):
                c = vw.pt(P(x["x"], x["y"]))
                cv.arco_p(c, 1.4, 0, 180, "vista", cor=COR["tug"])
                if x["n"] == 2:
                    cv.arco_p(c, 2.0, 0, 180, "fino", cor=COR["tug"])
                if x["z"] != pt.Z_TUG:
                    cv.texto_p((c[0], c[1] - 2.2), f"{x['z']}", 1.1, "middle", cor=COR["tug"])
        for x in t["interruptores"]:
            if x["pav"] != pav:
                continue
            with cv.escopo("ponto", x["cod"], amb=x["amb"], funcao=x["tipo"]):
                c = vw.pt(P(x["x"], x["y"]))
                cv.circ_p(c, 1.2, "vista", preenche="#fff", cor="#333")
                cv.texto_p((c[0], c[1] + 0.6), "P" if x["tipo"] == "paralelo" else "S", 1.2, "middle", cor="#333")
        for x in t["luminarias"]:
            if x["pav"] != pav:
                continue
            c = vw.pt(P(x["x"], x["y"]))
            cv.circ_p(c, 1.3, "fino", preenche="#fffbe6", cor=COR["iluminacao"])
            cv.linha_p((c[0] - 1.8, c[1]), (c[0] + 1.8, c[1]), "fino", cor=COR["iluminacao"])
        for x in t["tue"]:
            if x["pav"] != pav or x["externo"]:
                continue
            with cv.escopo("ponto", x["cod"], amb=x["amb"] or "", z=str(x["z"])):
                c = vw.pt(P(x["x"], x["y"]))
                cv.poli_p([(c[0] - 1.4, c[1] - 1.4), (c[0] + 1.4, c[1] - 1.4), (c[0] + 1.4, c[1] + 1.4), (c[0] - 1.4, c[1] + 1.4)], "vista",
                          fechado=True, preenche="#eef3fb", cor=COR["tue"])
                cv.texto_p((c[0] + 2.2, c[1] + 0.6), x["circuito"].replace("TUE-", ""), 1.1, "start", cor=COR["tue"])

    _plantas(cv, desenhar, "PONTOS E PERCURSOS")

    # ---- tabelas
    ambs = [a.cod for a in pj.TERREO + pj.SUPERIOR]
    lin = []
    for a in ambs:
        tm = [x for x in t["tomadas"] if x["amb"] == a]
        if not tm and not any(x["amb"] == a for x in t["interruptores"]):
            continue
        lin.append([a, f"{len(tm)}/{sum(x['n'] for x in tm)}", f"{sum(1 for x in tm if x['n'] == 2)}", f"{sum(1 for x in tm if x['z'] >= 1100)}",
                    f"{sum(1 for x in t['interruptores'] if x['amb'] == a)}", f"{sum(1 for x in t['luminarias'] if x['amb'] == a)}",
                    f"{sum(1 for x in t['tue'] if x['amb'] == a)}"])
    y = _tabela(cv, (600, 40), "PONTOS POR AMBIENTE", ["AMB", "PTS/TOM", "DUPLO", "ALTAS", "INT", "LUM", "TUE"], lin,
                larguras=[24, 30, 24, 24, 24, 24, 24], h_lin=3.6)
    lin = [[k[:60], f"{v['qtd']:.0f}" if v["un"] == "un" else f"{v['qtd']:.1f}", v["un"]] for k, v in fx.items()
           if any(s in k for s in ("eletroduto", "passa-fio", "caixa", "abracadeira de eletroduto"))]
    y = _tabela(cv, (600, y + 5), "FIXADORES E CAIXAS (H)", ["ITEM", "QTD", "UN"], lin, larguras=[140, 24, 14], h_lin=4.0)
    conf = pt.conferir(pj) + [c for c in pr.conferir(pj) if "eletric" in c[0] or "queda" in c[0] or "caixa" in c[0]]
    _tabela(cv, (600, y + 5), "CONFERENCIAS DESTA PRANCHA", ["O QUE", "COMO", ""], [[a[:40], b[:52], "ok" if o else "NAO"] for a, b, o in conf],
            larguras=[62, 100, 14], h_lin=3.6)
    lin = []
    for g in sorted(arv, key=lambda g: g["circuito"]):
        c = cs.get(g["circuito"], {})
        lin.append([g["circuito"], g["quadro"], f"{g['pontos']}", f"{g['paredes']}", _fm(g["arvore_mm"]), _fm(g["mais_longe_mm"]),
                    _fm(c.get("comp_manhattan_mm", 0)), f"{c.get('queda_pct', 0):.2f}".replace(".", ","), f"{c.get('secao_mm2', '')}",
                    f"{g['montantes']}", f"{g['caixas_passagem']}"])
    _tabela(cv, (40, 385), "CIRCUITOS: ARVORE REAL, PONTO MAIS LONGE, O QUE ERA MANHATTAN x 1,2, QUEDA E SECAO",
            ["CIRCUITO", "QD", "PTS", "PAR.", "ARVORE m", "+LONGE m", "MANH. m", "QUEDA %", "mm2", "MONT.", "CX PASS."], lin,
            larguras=[30, 16, 14, 14, 26, 26, 26, 24, 16, 18, 20], h_lin=3.2)
    return cv


# =========================================================================
# PR-74 — AGUA E ESGOTO
# =========================================================================
def agua_esgoto_ocultos() -> Canvas:
    import nucleo.agua as agm
    import nucleo.detalhes_lsf as dl
    arv = pr.arvores_agua(pj)
    es = pr.esgoto(pj)
    fx = pr.fixadores(pj)
    r = pr.resumo(pj)
    pp = pr.por_parede(pj)
    pT, pS, _ = dl._paineis(pj)
    serv = pr.servicos_por_painel(pj, pT + pS)
    cv = base("AGUA E ESGOTO: PERCURSO OCULTO POR PAREDE, FUROS E FIXADORES", "1:75", "74", notas=[
        f"PEX DN20 da coluna {pr._fonte_agua(pj)['cod']} ate cada peca, DENTRO da parede a {pr.Z_AGUA} mm por furos de {pr.FURO_HIDRAULICO} mm "
        f"(que a fabricacao passa a abrir em {sum(1 for v in serv.values() if len(v) == 2)} paineis); sobe na parede ate a peca. "
        f"{r['pex_m']} m em {len(arv)} ramais; {r['montantes_agua']} montantes atravessados.",
        f"Esgoto NUNCA em montante (DN50 e mais e furo maior que meia alma): {r['esgoto_m']} m sob o piso — envelopado no radier, entre as vigas no "
        "entrepiso — ate a prumada ou a caixa; so a prumada e vertical (PR-62).",
        f"Mapa de ocultos: {r['paredes_ocupadas']} paredes levam eletrica e/ou agua. Regra de obra: parafuso de placa e furo de morador fora das "
        "faixas 350-450 (agua) e 1.400-1.500 mm (eletrica); as verticais ficam junto aos pontos.",
        "Fixadores (H): luva no furo, clip de PEX a cada 600 mm, barra de fixacao entre montantes em cada peca; esgoto amarrado a tela do radier "
        "a cada 1,5 m e em abracadeira isofonica a cada 1,0 m no entrepiso.",
    ])
    paredes = {w["cod"]: w for pav in ("T", "S") for w in pt.paredes(pj, pav)}
    com_agua = {t["parede"] for g in arv for t in g["trechos_parede"] if t["parede"]}

    def desenhar(cv, vw, pav):
        with cv.escopo("percurso", f"HID-{pav}"):
            # paredes com agua: faixa azul clara por tras do percurso
            for cod in com_agua:
                w = paredes.get(cod)
                if not w or cod[1] != pav:
                    continue
                cv.linha_p(vw.pt(P(w["x1"], w["y1"])), vw.pt(P(w["x2"], w["y2"])), "grosso", cor="#cfe3f7")
            for g in arv:
                if g["pav"] != pav:
                    continue
                _rota(cv, vw, g["trechos_parede"] + g["proprios"], COR["agua"])
            for e in es:
                if e["pav"] != pav:
                    continue
                _rota(cv, vw, e["trechos"], COR["esgoto"], dash_planos=("radier", "entrepiso"))
        for q in pj.PRUMADAS:
            c = vw.pt(P(q["x"], q["y"]))
            cor = COR["agua"] if q["tipo"] == "agua fria" else COR["esgoto"]
            cv.poli_p([(c[0] - 1.6, c[1] - 1.6), (c[0] + 1.6, c[1] - 1.6), (c[0] + 1.6, c[1] + 1.6), (c[0] - 1.6, c[1] + 1.6)], "vista", fechado=True,
                      preenche="#fff", cor=cor)
            cv.texto_p((c[0], c[1] - 2.4), q["cod"], 1.1, "middle", cor=cor)
        for x in pt.agua(pj):
            if x["pav"] != pav or x["externo"]:
                continue
            with cv.escopo("ponto", x["cod"], amb=x["amb"], z=str(x["z"])):
                c = vw.pt(P(x["x"], x["y"]))
                cv.circ_p(c, 1.4, "vista", preenche="#fff", cor=COR["agua"])
                cv.texto_p((c[0] + 2.0, c[1] + 0.6), f"{x['cod']} {x['z']}", 1.1, "start", cor=COR["agua"])
        # paineis com furo hidraulico: marca no eixo do painel
        for p in (pT if pav == "T" else pS):
            if len(serv.get(p.cod, [])) == 2:
                x1, y1 = (p.x + p.comp, p.y) if p.horizontal else (p.x, p.y + p.comp)
                m = vw.pt(P((p.x + x1) / 2, (p.y + y1) / 2))
                cv.texto_p((m[0], m[1] - 1.2 if p.horizontal else m[1]), "o32", 1.0, "middle", cor="#06c", rot=0 if p.horizontal else 90)

    _plantas(cv, desenhar, "AGUA (azul, a 400 mm) E ESGOTO (marrom, sob o piso)")

    lin = [[e["parede"], f"{e['x1']},{e['y1']}-{e['x2']},{e['y2']}", "ext" if e["externa"] else "int", _fm(e["eletrica_m"] * 1000), _fm(e["agua_m"] * 1000),
            f"{e['verticais']}", f"{e['pontos']}", "/".join(str(z) for z in e["cotas"])] for e in sorted(pp, key=lambda e: -(e["agua_m"] * 10 + e["eletrica_m"]))[:44]]
    y = _tabela(cv, (600, 40), f"O QUE CADA PAREDE ESCONDE ({len(pp)} paredes; as {len(lin)} mais carregadas)",
                ["PAREDE", "DE-ATE (mm)", "", "ELE m", "AGUA m", "VERT", "PTS", "COTAS"], lin,
                larguras=[18, 62, 10, 18, 20, 14, 14, 24], h_lin=3.3)
    lin = [[k[:60], f"{v['qtd']:.0f}", v["un"]] for k, v in fx.items() if any(s in k for s in ("PEX", "luva", "barra", "esgoto"))]
    y = _tabela(cv, (600, y + 5), "FIXADORES DE AGUA E ESGOTO (H)", ["ITEM", "QTD", "UN"], lin, larguras=[140, 24, 14], h_lin=4.0)
    conf = [c for c in pr.conferir(pj) if any(k in c[0] for k in ("agua", "peca", "pressao", "esgoto", "furo"))] + agm.conferir(pj)[:4]
    _tabela(cv, (600, y + 5), "CONFERENCIAS DESTA PRANCHA", ["O QUE", "COMO", ""], [[a[:40], b[:52], "ok" if o else "NAO"] for a, b, o in conf],
            larguras=[62, 100, 14], h_lin=3.6)
    lin = []
    for p in pT + pS:
        sv = serv.get(p.cod, [])
        if len(sv) == 2:
            lin.append([p.cod, p.parede, p.pav, f"{p.comp}", "; ".join(f"{s['servico']} o{s['d']} a {s['z']}" for s in sv), f"{p.comp // pj.MONTANTE_ESPACAMENTO + 1}"])
    y2 = _tabela(cv, (40, 385), f"PAINEIS COM FURO HIDRAULICO ({len(lin)} de {len(pT) + len(pS)}; todos tem o furo eletrico a {pr.Z_ELETRICA})",
                 ["PAINEL", "PAREDE", "PAV", "COMP mm", "FUROS POR MONTANTE", "MONT."], lin, larguras=[26, 22, 12, 22, 120, 18], h_lin=3.3)
    lin = [[g["cod"], g["onde"][:52], g["tipo"][:44]] for g in agm.registros(pj)]
    _tabela(cv, (300, 385), "REGISTROS E VALVULAS (PR-63)", ["COD", "ONDE", "TIPO"], lin, larguras=[26, 130, 120], h_lin=3.6)
    return cv


# =========================================================================
# PR-75 — CLIMATIZACAO EM ISOMETRICO, TESTES E PONTOS CRITICOS
# =========================================================================
def climatizacao_testes() -> Canvas:
    import nucleo.gas as gs
    fr = pr.frigorigena(pj)
    tst = ts.testes(pj)
    pc = ts.pontos_criticos(pj)
    sup = gs.suportes(pj)
    cv = base("CLIMATIZACAO EM ISOMETRICO, MAPA DE TESTES E PONTOS CRITICOS", "indicada", "75", notas=[
        f"{len(fr)} linhas frigorigenas do nicho ao evaporador: sobem no nicho, correm pela fachada na cota do evaporador ({pt.Z_SPLIT} mm) e entram "
        f"na parede do ambiente; {pr.resumo(pj)['frigorigena_m']} m no total contra {sum(l['comp'] for l in pj.linhas_frigorigenas() if not l.get('reserva')) / 1000:.1f} m "
        f"declarados na PR-28 (o declarado nao contava a fachada). {sup['abracadeiras']} abracadeiras; isolamento elastomerico 9 mm, dreno DN25 ao ralo mais proximo.",
        f"Mapa de testes: {len(tst)} testes em {ts.resumo(pj)['sistemas']} sistemas, cada um com fase (PR-72), criterio (H, norma citada) e registro. "
        "O que fica escondido testa ANTES de esconder: esgoto do radier na fase 1, PEX com a parede aberta, N2 na linha antes do fechamento.",
        "Pontos criticos: o que, se sair errado, nao se ve depois — e o que a inspecao fotografa.",
    ])
    # ---- isometrico
    tc = {t["cod"]: t for t in pj.TECNICOS}
    pontos = []
    for r in fr:
        for t in r["trechos"]:
            pontos += [t["de"], t["para"]]
    pla = dict(x0=pj.RECUO_ESQ, y0=pj.RECUO_FRENTE, w=13_200, h=19_200)
    for x in (pla["x0"], pla["x0"] + pla["w"]):
        for y in (pla["y0"], pla["y0"] + pla["h"]):
            pontos += [(x, y, 0), (x, y, pj.NIVEL_SUPERIOR + pj.PE_DIREITO)]
    iso = _Iso(90, pontos, 40, 320)
    an.titulo_desenho(cv, (40, 40), "1", "LINHAS FRIGORIGENAS — ISOMETRICO", "1:90")
    with cv.escopo("percurso", "FRIGO-ISO"):
        iso.caixa(cv, pla["x0"], pla["y0"], 0, pla["w"], pla["h"], pj.PE_DIREITO, "#bbb")
        sup_ambs = [a for a in pj.SUPERIOR]
        x0 = min(a.x for a in sup_ambs); x1 = max(a.x + a.w for a in sup_ambs); y0 = min(a.y for a in sup_ambs); y1 = max(a.y + a.h for a in sup_ambs)
        iso.caixa(cv, x0, y0, pj.NIVEL_SUPERIOR, x1 - x0, y1 - y0, pj.PE_DIREITO, "#bbb")
        for cod in ("TC-09", "TC-10"):
            t = tc[cod]
            iso.caixa(cv, t["x"], t["y"], 0, t["w"], t["h"], 1_200, "#b5651d", "#fff3d6")
            iso.rotulo(cv, t["x"] + t["w"], t["y"], 1_300, f"{cod} {t['nome'][:22]}", "#b5651d")
        for r in fr:
            for t in r["trechos"]:
                iso.linha(cv, t["de"], t["para"], COR["frigorigena"], "vista")
            fim = r["trechos"][-1]["para"]
            p = iso.pt(*fim)
            cv.poli_p([(p[0] - 2, p[1] - 1), (p[0] + 2, p[1] - 1), (p[0] + 2, p[1] + 1), (p[0] - 2, p[1] + 1)], "vista", fechado=True, preenche="#eef3fb", cor=COR["tue"])
            iso.rotulo(cv, fim[0], fim[1], fim[2] + 250, f"{r['cod']} -> {r['evaporador']} ({r['amb']})", COR["frigorigena"])
    lin = [[r["cod"], r["amb"], r["nicho"], r["evaporador"]] + [_fm(next((t["comp_mm"] for t in r["trechos"] if t["plano"] == k), 0)) for k in ("subida", "fachada", "parede")]
           + [_fm(r["comp_mm"]), _fm(r["declarado_mm"]), f"{r['suc']} / {r['liq']}", f"DN{r['dreno_dn']}"] for r in fr]
    y = _tabela(cv, (40, 335), "LINHAS FRIGORIGENAS — TRECHOS (m)", ["LINHA", "AMB", "NICHO", "EVAP.", "SOBE", "FACHADA", "PAREDE", "TOTAL", "PR-28", "SUC/LIQ", "DRENO"],
                lin, larguras=[26, 20, 18, 18, 18, 22, 22, 20, 20, 26, 18], h_lin=3.6)
    lin = [[p["onde"][:30], p["o_que"][:44], p["risco"][:48], p["conferir"][:70]] for p in pc]
    _tabela(cv, (40, y + 6), "PONTOS CRITICOS DE EXECUCAO", ["ONDE", "O QUE", "RISCO", "CONFERIR"], lin, larguras=[52, 74, 78, 104], h_lin=4.2)
    lin = [[x["sistema"][:30], x["fase"], x["teste"][:70], x["criterio"][:76], x["registro"][:48]] for x in tst]
    y = _tabela(cv, (360, 40), "MAPA DE TESTES E INSPECOES (H: normas citadas sao referencia, nao laudo)", ["SISTEMA", "F", "TESTE", "CRITERIO", "REGISTRO"], lin,
                larguras=[50, 8, 130, 140, 96], h_lin=5.0)
    conf = ts.conferir(pj) + [c for c in gs.conferir(pj) if "ruido" not in c[0]][:3]
    _tabela(cv, (360, y + 6), "CONFERENCIAS DESTA PRANCHA", ["O QUE", "COMO", ""], [[a[:44], b[:70], "ok" if o else "NAO"] for a, b, o in conf],
            larguras=[70, 120, 14], h_lin=3.8)
    return cv
