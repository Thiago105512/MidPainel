"""R75 — LOTE 5 DO BACKLOG: COMPLEMENTOS DO LIGHT STEEL FRAME.

  67  CONTRAVENTAMENTO E ANCORAGEM — planta dos paineis com fita X, hold-down
      em cada extremidade, chumbador, veredito por direcao; tolerancias de
      montagem (190, 228)
  68  DETALHES DO LSF — encontro em T, canto em L, reforco para carga
      suspensa (com os 13 itens locados), rodape, junta de movimentacao de
      fachada (187, 208, 411, 78, 480)
  69  PAGINACAO DE FACHADA E VISTA EXPLODIDA — grade de placas por painel
      externo, juntas, e os paineis afastados em isometrico (380, 215)
Tudo sai de nucleo/detalhes_lsf; a explodida usa a mesma projecao das redes.
"""
from __future__ import annotations

import math

import projeto as pj
import anotacao as an
import nucleo.detalhes_lsf as dl
from core import P, Canvas, View, TXT, CINZA
from pranchas import base, _tabela
from pranchas11 import _planta_base, _Iso

AZUL, LARANJA, VERDE = "#1f4b8a", "#d9822b", "#2a9d6f"


def contraventamento() -> Canvas:
    c = dl.contraventamento(pj)
    v = c["veredito"]
    cv = base("CONTRAVENTAMENTO, ANCORAGEM E TOLERANCIAS DE MONTAGEM", "1:100", "67", notas=[
        f"Sistema: {c['sistema']}. {len(c['paineis'])} paineis contraventados, {c['n_fitas']} fitas, "
        f"{c['holddowns']} hold-downs (um em cada extremidade de painel com fita).",
        f"Vento X: capacidade {v['X']['capacidade']} kN contra demanda {v['X']['demanda']} kN; "
        f"Y: {v['Y']['capacidade']} contra {v['Y']['demanda']} kN (piso.contraventar, NBR 6123 categoria IV; "
        "a III tambem passa, R68).",
        "Hold-down: cantoneira 2,0 mm parafusada ao montante duplo de extremidade e chumbador no radier; "
        "o tipo de chumbador sai de ligacoes.ancoragem pelo arrancamento de cada painel.",
        "Tolerancias (H): NBR 16970 e pratica de montagem; cada linha diz o que se mede, com o que e quando.",
    ])
    pat = cv.hachura("fitax", espac=1.6, ang=45, w=0.12, cor=AZUL)
    for pav, vw, tit, num in (("T", View(100, 40, 470, 0, 0), "TERREO", "1"),
                              ("S", View(100, 270, 470, pj.RECUO_ESQ, pj.RECUO_FRENTE), "SUPERIOR", "2")):
        _planta_base(cv, vw, pav, com_abertos=(pav == "T"))
        for p in c["paineis"]:
            if p["pav"] != pav:
                continue
            with cv.escopo("contraventamento", p["cod"], vrd=str(p["vrd"]), chumbador=p["chumbador"]):
                a, b = vw.pt(P(p["x1"], p["y1"])), vw.pt(P(p["x2"], p["y2"]))
                e = 2.2
                if p["direcao"] == "X":
                    pts = [(a[0], a[1] - e), (b[0], b[1] - e), (b[0], b[1] + e), (a[0], a[1] + e)]
                else:
                    pts = [(a[0] - e, a[1]), (b[0] - e, b[1]), (b[0] + e, b[1]), (a[0] + e, a[1])]
                cv.poli_p(pts, "vista", fechado=True, preenche=f"url(#{pat})", cor=AZUL)
                m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                cv.texto_p((m[0] + (0 if p["direcao"] == "X" else 4), m[1] - (4 if p["direcao"] == "X" else 0)),
                           p["cod"], 1.6, "middle", cor=AZUL, rot=(0 if p["direcao"] == "X" else 90))
                if p["holddown"]:
                    for q in (a, b):
                        cv.poli_p([(q[0], q[1] - 2.4), (q[0] + 2.1, q[1] + 1.2), (q[0] - 2.1, q[1] + 1.2)], "vista",
                                  fechado=True, preenche="#fff", cor=LARANJA)
        an.titulo_desenho(cv, (vw.ox, 500), num, f"CONTRAVENTAMENTO — {tit}  (hachura: fita X; triangulo: hold-down)", "1:100")
    lin = [[p["cod"], p["direcao"], f"{p['comp']}", f"{p['vrd']}", f"{p['aspecto']}", f"{p['v_kn']}", f"{p['uplift']}",
            "sim" if p["holddown"] else "nao", p["chumbador"][:28]] for p in c["paineis"]]
    y = _tabela(cv, (480, 40), "PAINEIS COM FITA X — ESFORCO, ARRANCAMENTO E CHUMBADOR",
                ["PAINEL", "DIR", "L mm", "Vrd kN", "ASP.", "V kN", "UPLIFT kN", "HD", "CHUMBADOR"], lin,
                larguras=[22, 10, 14, 16, 12, 14, 20, 10, 60], h_lin=3.8)
    lin = [[d, f"{x['capacidade']}", f"{x['demanda']}", f"{x['folga']}", "ok" if x["ok"] else "NAO"] for d, x in v.items()]
    y = _tabela(cv, (480, y + 6), "VEREDITO POR DIRECAO (kN)", ["DIR", "CAPACIDADE", "DEMANDA", "FOLGA", ""], lin,
                larguras=[14, 30, 30, 30, 14], h_lin=4.2)
    lin = [[a, b, c_, d] for a, b, c_, d in dl.TOLERANCIAS]
    _tabela(cv, (480, y + 6), "TOLERANCIAS DE MONTAGEM (H — NBR 16970 e pratica)", ["O QUE", "QUANTO", "COM O QUE", "QUANDO"],
            lin, larguras=[40, 56, 40, 50], h_lin=4.2)
    return cv


def _caixa_det(cv, vw, x, z, w, h, cor, preenche, rot=None, estilo="corte"):
    cv.poli_p([vw.pt(P(x, z)), vw.pt(P(x + w, z)), vw.pt(P(x + w, z + h)), vw.pt(P(x, z + h))], estilo, fechado=True, preenche=preenche, cor=cor)
    if rot:
        cv.texto_p(vw.pt(P(x + w / 2, z + h / 2)), rot, TXT["micro"], "middle")


def _ue(cv, vw, x, y, larg=90, alt=40, esp=0.95, rot=0):
    """Montante Ue 90 x 40 em planta (secao), a 1:5."""
    pts = [(x, y), (x + larg, y), (x + larg, y + alt), (x + larg - 12, y + alt), (x + larg - 12, y + alt - 8),
           (x + larg - 2, y + alt - 8), (x + larg - 2, y + 2), (x + 2, y + 2), (x + 2, y + alt - 8), (x + 12, y + alt - 8),
           (x + 12, y + alt), (x, y + alt)]
    cv.poli_p([vw.pt(P(px, py)) for px, py in pts], "corte", fechado=True, preenche="#9bb7d4")


def detalhes() -> Canvas:
    cs = dl.cargas_suspensas(pj); ts = dl.encontros_t(pj); pf = dl.paginacao_fachada(pj)
    cv = base("DETALHES DO LSF — ENCONTROS, CARGA SUSPENSA, RODAPE E JUNTA DE FACHADA", "1:5 · 1:20", "68", notas=[
        f"Encontro em T: {len(ts)} na casa, derivados das paredes (ponta de uma parede dentro de outra). "
        "Detalhe unico: montante adicional na parede continua, clip de guia, 4 parafusos 4,8 x 19 por metro.",
        f"Carga suspensa: {len(cs)} itens (gabinetes de banho, paineis de TV, cabeceiras e as duas TVs) locados na "
        "parede que os recebe; reforco de OSB 18 mm entre montantes na faixa de altura do item, "
        f"{sum(x['osb_m2'] for x in cs):.1f} m2. Parede de LSF nao segura bucha: segura montante e reforco.",
        "Rodape: perfil de poliestireno 100 x 15 sobre a placa, 5 mm acima do piso, selado; nos molhados, "
        "o proprio porcelanato recortado (acabamentos()).",
        f"Junta de movimentacao de fachada: {pf['juntas_mov']} (a cada {dl.JUNTA_MOV_MAX / 1000:.0f} m e em cada canto), "
        f"{pf['junta_mov']['largura']} mm com {pf['junta_mov']['selante']}, sobre {pf['junta_mov']['apoio']}.",
    ])
    # ---- A: encontro em T, planta 1:5
    vw = View(5, 100, 200, 0, 0)
    _caixa_det(cv, vw, -300, 0, 900, 12.5, "#888", "#f0eee8")                 # placa da parede continua (face)
    _caixa_det(cv, vw, -300, 12.5 + 90, 900, 12.5, "#888", "#f0eee8")
    for xx in (-300 + 20, -300 + 600 + 20):
        _ue(cv, vw, xx, 12.5)
    _ue(cv, vw, 150 - 45 - 100, 12.5)                                     # montante adicional
    _ue(cv, vw, 150 - 45 + 100, 12.5)
    # parede que chega (vertical no detalhe), com guia
    _caixa_det(cv, vw, 150 - 45, 12.5 + 90 + 12.5, 90, 300, "#9bb7d4", "#dfe9f2", "guia U 92")
    _caixa_det(cv, vw, 150 - 45 - 12.5, 12.5 + 90 + 12.5, 12.5, 300, "#888", "#f0eee8")
    _caixa_det(cv, vw, 150 + 45, 12.5 + 90 + 12.5, 12.5, 300, "#888", "#f0eee8")
    cv.texto_p(vw.pt(P(150, 12.5 + 90 + 12.5 + 340)), "parede que chega", TXT["micro"], "middle")
    cv.texto_p(vw.pt(P(-280, -40)), "montantes a 600 + 2 adicionais junto ao encontro; clip de guia 4,8 x 19", TXT["micro"], "start", cor=CINZA)
    an.titulo_desenho(cv, (40, 226), "A", "ENCONTRO EM T — PLANTA", "1:5")
    # ---- B: canto em L, 1:5
    vw = View(5, 300, 200, 0, 0)
    _caixa_det(cv, vw, 0, 0, 12.5, 500, "#888", "#f0eee8")
    _caixa_det(cv, vw, 0, 0, 500, 12.5, "#888", "#f0eee8")
    _ue(cv, vw, 12.5, 12.5)
    _ue(cv, vw, 12.5 + 90 + 4, 12.5)
    _ue(cv, vw, 12.5, 12.5 + 40 + 4, larg=40, alt=90)
    _caixa_det(cv, vw, 12.5 + 200, 12.5 + 100, 12.5, 400, "#888", "#f0eee8")
    _caixa_det(cv, vw, 12.5 + 100, 12.5 + 200, 400, 12.5, "#888", "#f0eee8")
    cv.texto_p(vw.pt(P(250, 350)), "canto com tres montantes: apoio de placa nas duas faces internas", TXT["micro"], "middle", cor=CINZA)
    an.titulo_desenho(cv, (280, 226), "B", "CANTO EM L — PLANTA", "1:5")
    # ---- C: reforco para carga suspensa, elevacao 1:10
    vw = View(20, 560, 250, 0, 0)
    for k in range(4):
        _caixa_det(cv, vw, k * pj.MONTANTE_ESPACAMENTO, 0, 40, pj.PE_DIREITO, "#9bb7d4", "#dfe9f2")
    _caixa_det(cv, vw, 0, 0, 1_840, 40, "#9bb7d4", "#dfe9f2"); _caixa_det(cv, vw, 0, pj.PE_DIREITO - 40, 1_840, 40, "#9bb7d4", "#dfe9f2")
    r = dl.REFORCO["gabinete banho"]
    _caixa_det(cv, vw, 40, r["z0"], 1_760, r["z1"] - r["z0"], "#8a6d3b", "#e9dcc4", "OSB 18 mm entre montantes")
    r2 = dl.REFORCO["tv"]
    _caixa_det(cv, vw, 40, 1_500, 1_760, 90, "#9bb7d4", "#dfe9f2", "travessa Ue 90 para TV a 1.500")
    an.cadeia(cv, vw, [0, r["z0"], r["z1"], 1_500, pj.PE_DIREITO], 1_840, "V", 8)
    an.titulo_desenho(cv, (540, 276), "C", "REFORCO PARA CARGA SUSPENSA — ELEVACAO DA PAREDE", "1:20")
    # ---- D: rodape, 1:5
    vw = View(5, 60, 440, 0, 0)
    _caixa_det(cv, vw, 0, -150, 400, 150, "#999", "#cfcac1", "radier + contrapiso")
    _caixa_det(cv, vw, 0, 0, 400, 12, "#999", "#e9e6df", "porcelanato")
    _caixa_det(cv, vw, -90, -150, 40, 600, "#9bb7d4", "#dfe9f2")
    _caixa_det(cv, vw, -50, -150, 12.5, 600, "#888", "#f0eee8")
    _caixa_det(cv, vw, -37.5, 17, 15, 100, "#555", "#fff", "rodape 100 x 15")
    cv.texto_p(vw.pt(P(-30, 140)), "poliestireno colado, selante acrilico no topo; 5 mm acima do piso", TXT["micro"], "start", cor=CINZA)
    an.titulo_desenho(cv, (40, 466), "D", "RODAPE — SECAO", "1:5")
    # ---- E: junta de movimentacao, planta 1:5
    vw = View(5, 300, 440, 0, 0)
    _ue(cv, vw, -100, 12.5); _ue(cv, vw, 10, 12.5)
    _caixa_det(cv, vw, -300, 0, 295, 10, "#888", "#d8d3c8", "placa cimenticia")
    _caixa_det(cv, vw, 5, 0, 295, 10, "#888", "#d8d3c8", "placa cimenticia")
    _caixa_det(cv, vw, -5, 0, 10, 10, "#c33", "#f6c9c9")
    cv.texto_p(vw.pt(P(0, -30)), "junta 10 mm: tarucel + selante PU; membrana continua por tras", TXT["micro"], "middle", cor=CINZA)
    _caixa_det(cv, vw, -300, 12.5 + 90 + 2, 600, 3, "#2a9d6f", "#cdeedd", "membrana hidrofuga")
    an.titulo_desenho(cv, (280, 466), "E", "JUNTA DE MOVIMENTACAO DE FACHADA — PLANTA (montante duplo)", "1:5")
    # ---- tabelas
    lin = [[x["cod"], x["amb"], x["familia"], f"{x['carga_kg']}", x["parede"] or "—", f"{x['z0']}-{x['z1']}", str(x["montantes"]),
            f"{x['osb_m2']}"] for x in cs]
    y = _tabela(cv, (480, 300), "CARGAS SUSPENSAS — ONDE E QUANTO", ["ITEM", "AMB", "FAMILIA", "kg", "PAREDE", "z mm", "MONT.", "OSB m2"],
                lin, larguras=[20, 16, 26, 10, 26, 22, 12, 14], h_lin=3.8)
    lin = [[t["pav"], f"{t['x']}", f"{t['y']}", t["continua"], "sim" if t["externa"] else "nao"] for t in ts]
    _tabela(cv, (480, y + 6), f"ENCONTROS EM T — {len(ts)}", ["PAV", "x", "y", "CONTINUA", "EXTERNA"], lin,
            larguras=[12, 18, 18, 22, 20], h_lin=3.6)
    return cv


def fachada_e_explodida() -> Canvas:
    pf = dl.paginacao_fachada(pj)
    cv = base("PAGINACAO DE FACHADA E VISTA EXPLODIDA DO STEEL FRAME", "1:150 · 1:200", "69", notas=[
        f"Placa cimenticia {dl.PLACA['larg']} x {dl.PLACA['alt']} com junta seca de {dl.PLACA['junta']} mm em cada painel "
        f"externo. Contar placa por painel dava 228 e 44 % de perda; o nesting da casa inteira (camadas.paginar), "
        f"que reaproveita os retalhos, da {pf['placas']} placas ({pf['inteiras']} inteiras + {pf['de_retalho']} de retalho) "
        f"a {pf['aproveitamento'] * 100:.0f} %.",
        f"{pf['juntas_mov']} juntas de movimentacao ({pf['junta_mov']['largura']} mm, detalhe E da PR-68): a cada 6 m e em cada canto.",
        "Explodida: cada painel afastado 1,5 m da sua parede para fora e o superior erguido 2 m; os codigos sao os de "
        "fabricacao (PR-18 e catalogo).",
    ])
    # ---- desenvolvimento das fachadas: paineis externos como retangulos com a grade
    esc = 150
    x, y, linha_h = 40, 60, 0
    cv.texto_p((40, 50), "PAINEIS EXTERNOS COM A GRADE DE PLACAS (1:150) — em sequencia, por pavimento", TXT["peq"], "start", peso="bold")
    for p in pf["paineis"]:
        w, h = p["comp"] / esc, p["alt"] / esc
        if x + w > 470:
            x = 40; y += 30
        with cv.escopo("paginacao", p["cod"], placas=str(p["cols"] * p["rows"])):
            cv.poli_p([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], "vista", fechado=True, preenche="#f4f1ea", cor="#8a6d3b")
            for k in range(1, p["cols"]):
                xx = x + k * dl.PLACA["larg"] / esc
                if xx < x + w:
                    cv.linha_p((xx, y), (xx, y + h), "fino", cor="#8a6d3b")
            for k in range(1, p["rows"]):
                yy = y + h - k * dl.PLACA["alt"] / esc
                if yy > y:
                    cv.linha_p((x, yy), (x + w, yy), "fino", cor="#8a6d3b")
            cv.texto_p((x + w / 2, y + h + 3), f"{p['cod']} {p['comp']}", 1.5, "middle", cor="#5a4630")
        x += w + 4
    # ---- explodida
    pT, pS, _ = dl._paineis(pj)
    cx = sum(a.cx for a in pj.TERREO) / len(pj.TERREO); cy = sum(a.cy for a in pj.TERREO) / len(pj.TERREO)
    AF, UP = 1_500, 2_000
    pts = []
    def desloc(p):
        if p.horizontal:
            dy = AF if p.y > cy else -AF
            return 0, dy
        dx = AF if p.x > cx else -AF
        return dx, 0
    caixas = []
    for p in pT + pS:
        if not p.externa:
            continue
        dx, dy = desloc(p)
        z0 = 0 if p.pav == "T" else pj.NIVEL_SUPERIOR + UP
        x1, y1 = p.x + dx, p.y + dy
        x2, y2 = (x1 + p.comp, y1) if p.horizontal else (x1, y1 + p.comp)
        caixas.append((p, (x1, y1, z0), (x2, y2, z0 + p.altura)))
        pts += [(x1, y1, z0), (x2, y2, z0 + p.altura)]
    iso = _Iso(200, pts, 480, 480)
    for p, a, b in caixas:
        with cv.escopo("explodida", p.cod, pav=p.pav):
            q = [iso.pt(a[0], a[1], a[2]), iso.pt(b[0], b[1], a[2]), iso.pt(b[0], b[1], b[2]), iso.pt(a[0], a[1], b[2])]
            cv.poli_p(q, "fino", fechado=True, preenche="#dfe9f2" if p.pav == "T" else "#e8f1e3", cor="#1f4b8a")
            iso.rotulo(cv, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, b[2] + 200, p.cod, "#1f4b8a", h=1.4, anchor="middle", dx=0)
    for a in pj.TERREO:
        iso.caixa(cv, a.x, a.y, 0, a.w, a.h, 0, "#bbb")
    an.titulo_desenho(cv, (480, 505), "2", "VISTA EXPLODIDA — PAINEIS EXTERNOS AFASTADOS DA PLANTA", "1:200")
    an.titulo_desenho(cv, (40, y + 40), "1", "DESENVOLVIMENTO DOS PAINEIS EXTERNOS", "1:150")
    lin = [[j["pav"], f"{j['x']:.0f}", f"{j['y']:.0f}", j["tipo"][:34]] for j in pf["juntas"]]
    _tabela(cv, (40, y + 50), f"JUNTAS DE MOVIMENTACAO — {pf['juntas_mov']}", ["PAV", "x", "y", "TIPO"], lin[:40],
            larguras=[12, 18, 18, 70], h_lin=3.4)
    return cv
