"""GAS, RENOVACAO DE AR E SUPORTES — o que faltava nas instalacoes (R72).

GAS. A central GLP (TC-04, 2 x P-45) esta locada desde R41 e o cooktop e a
churrasqueira estao nas bancadas; faltava a rede entre eles. Aqui ela sai
do caso: percurso Manhattan pela faixa tecnica, cobre rigido classe A,
regulador de primeiro estagio na central, registro de esfera em cada ponto,
abrigo ventilado pela NBR 13523 e rede pela NBR 15526.

RENOVACAO DE AR. Ambiente climatizado fechado precisa de ar novo: 7,5 L/s
por pessoa mais 0,3 L/s por m2 (H, ASHRAE 62.1 adaptada a residencia). O
projeto nao tem VMC; a renovacao e por janela e pelos exaustores dos banhos.
A vazao requerida fica declarada por ambiente para que a decisao seja vista.

SUPORTES. Condensadora em mao-francesa, linha frigorigena em abracadeira a
cada 1,5 m na horizontal e 2,0 m na vertical, isolada; sai de linhas_frigorigenas().
"""
from __future__ import annotations

from nucleo.esgoto import _manh

import math

POTENCIA_KW = {"cooktop": 9.0, "churrasqueira": 6.0}     # (H) 5 bocas; churrasqueira a gas
PCI_GLP_KWH_KG = 12.8
CONSUMO_P45_DIAS = None
TUBO = dict(material="cobre rigido classe A, NBR 13206", dn=15, uniao="solda forte (brasagem)",
            protecao="eletroduto PVC DN32 enterrado / embutido; sem emenda embutida")
REGULADOR = "regulador de 1o estagio 12 kg/h na central; 2o estagio (2,8 kPa) na entrada da casa"
ABRIGO = dict(norma="NBR 13523", afastamento_vao_mm=1_500, afastamento_ignicao_mm=3_000,
              ventilacao="duas aberturas de 200 cm2 (superior e inferior), tela metalica",
              piso="concreto nivelado, sem ralo em 1,5 m", porta="veneziana metalica com cadeado")
FATOR_PERCURSO = 1.20
AR_NOVO_LS_PESSOA = 7.5
AR_NOVO_LS_M2 = 0.3
# R73 — NENHUMA condensadora em mao-francesa numa casa de light steel frame: a
# parede e leve (60 kg/m2) e vira caixa de som para a vibracao do compressor.
# Toda condensadora vai ao PISO do nicho, sobre base de concreto e isoladores.
SUPORTE_COND = ("base de concreto 100 mm no piso do nicho, isoladores de borracha (deflexao "
                "estatica >= 6 mm, frequencia natural <= 10 Hz), 200 mm da parede, sem contato "
                "com o LSF; linhas com abracadeiras de borracha")
LW_CONDENSADORA = {9_000: 52.0, 18_000: 56.0, 30_000: 60.0}   # dB(A) potencia sonora (H)
LW_BOMBA = 58.0                                              # bomba de recalque / pressurizador
LW_BOMBA_PISCINA = 55.0                                      # (H) bomba de velocidade variavel em rotacao baixa, a das 6 h de renovacao
LIMITE_DECK = 45.0                                           # (H) NBR 10152, area externa de lazer
RW_JANELA = 30.0                                             # vidro laminado fechado (H)
LIMITE_DORMITORIO = 35.0                                     # NBR 10152, dormitorio, conforto
Z_CONDENSADORA = 600
ABRAC_H = 1_500
ABRAC_V = 2_000




def pontos(pj) -> list[dict]:
    out = []
    for b in pj.BANCADAS:
        if b.get("cooktop"):
            out.append(dict(cod=f"GAS-{b['cod']}", amb=b["amb"], tipo="cooktop", x=b["x"], y=b["y"],
                            kw=POTENCIA_KW["cooktop"], registro="registro de esfera DN15 + engate flexivel"))
        if b.get("ignicao"):
            out.append(dict(cod=f"GAS-{b['cod']}", amb=b["amb"], tipo="churrasqueira", x=b["x"], y=b["y"],
                            kw=POTENCIA_KW["churrasqueira"], registro="registro de esfera DN15 + engate flexivel"))
    return out


def rede(pj) -> dict:
    tc = next(t for t in pj.TECNICOS if "GLP" in t["nome"])
    ft = pj.FAIXA_TECNICA
    ps = pontos(pj)
    # tronco: da central pela faixa tecnica ate a parede norte da casa, na altura do gourmet
    trechos = []
    kw = sum(p["kw"] for p in ps)
    x_par = max(a.x + a.w for a in pj.TERREO)
    for p in ps:
        comp = (_manh((tc["x"], tc["y"]), (x_par, p["y"])) + abs(x_par - p["x"])) * FATOR_PERCURSO
        trechos.append(dict(de=tc["cod"], para=p["cod"], dn=TUBO["dn"], comp_mm=round(comp), kw=p["kw"]))
    consumo_kg_h = kw / PCI_GLP_KWH_KG
    autonomia_dias = round(2 * 45 / (consumo_kg_h * 2.0), 0)     # 2 h de uso pleno por dia (H)
    return dict(central=dict(cod=tc["cod"], x=tc["x"], y=tc["y"], nome=tc["nome"], **ABRIGO),
                pontos=ps, trechos=trechos, comp_total_mm=sum(t["comp_mm"] for t in trechos),
                potencia_kw=kw, consumo_pleno_kg_h=round(consumo_kg_h, 2), autonomia_dias=autonomia_dias,
                tubo=TUBO, regulador=REGULADOR)


def renovacao(pj) -> list[dict]:
    ambs = {a.cod: a for a in pj.TERREO + pj.SUPERIOR}
    out = []
    for c in pj.CLIMATIZACAO:
        a = ambs[c["amb"]]
        area = c.get("area_m2", a.area_mod)
        q = c["pessoas"] * AR_NOVO_LS_PESSOA + area * AR_NOVO_LS_M2
        out.append(dict(amb=c["amb"], compartimento=c.get("compartimento", "—"), pessoas=c["pessoas"],
                        area_m2=round(area, 1), q_ls=round(q, 1), q_m3h=round(q * 3.6, 0),
                        como=("exaustor do banho + fresta de porta" if c["amb"].startswith("S-") or c["amb"] == "T-REV"
                              else "janela e porta-balcao; coifa da cozinha na fita social")))
    return out


def suportes(pj) -> dict:
    lf = pj.linhas_frigorigenas()
    cond = sum(1 for l in lf if not l.get("reserva"))
    abr = 0
    for l in lf:
        abr += math.ceil(l["horizontal"] / ABRAC_H) + math.ceil(l["subida"] / ABRAC_V)
    return dict(condensadoras=cond, suporte=SUPORTE_COND, abracadeiras=abr,
                isolamento_m=round(sum(l["comp"] for l in lf) / 1000 * 2, 1),
                regra=f"abracadeira a cada {ABRAC_H} mm na horizontal e {ABRAC_V} mm na vertical; "
                      "linha isolada com elastomerico 9 mm, acabamento em canaleta",
                bombas="bomba de recalque TC-02 e pressurizador TC-14 sobre coxins de borracha, com "
                       "conexoes flexiveis nos dois lados: sem tubo rigido ligando bomba a parede")


def _fontes(pj) -> list[dict]:
    """Cada nicho e cada bomba como fonte sonora, com a potencia somada."""
    tc = {t["cod"]: t for t in pj.TECNICOS}
    por_nicho = {}
    for c in pj.CLIMATIZACAO:
        if c.get("reserva"):
            continue
        por_nicho.setdefault(c["nicho"], []).append(LW_CONDENSADORA.get(c["capacidade"], 56.0))
    out = []
    for n, lws in por_nicho.items():
        t = tc[n]
        lw = 10 * math.log10(sum(10 ** (l / 10) for l in lws))
        out.append(dict(cod=n, nome=t["nome"], x=t["x"] + t["w"] / 2, y=t["y"] + t["h"] / 2, z=Z_CONDENSADORA,
                        unidades=len(lws), lw=round(lw, 1)))
    if "TC-02" in tc:
        t = tc["TC-02"]
        out.append(dict(cod="TC-02", nome=t["nome"], x=t["x"] + t["w"] / 2, y=t["y"] + t["h"] / 2, z=300,
                        unidades=1, lw=LW_BOMBA))
    # R79 — a bomba da piscina nao estava aqui: a casa de maquinas fica na faixa
    # tecnica norte, a 5,6 m do deck e a poucos metros das janelas do fundo
    cm = next((t for t in tc.values() if t.get("casa_maquinas")), None)
    if cm:
        out.append(dict(cod=cm["cod"], nome=cm["nome"], x=cm["x"] + cm["w"] / 2, y=cm["y"] + cm["h"] / 2, z=300,
                        unidades=1, lw=LW_BOMBA_PISCINA))
    return out


def ruido_deck(pj) -> dict | None:
    """A bomba da piscina ouvida do canto mais proximo do deck (fonte em recinto
    com venezianas: sem credito de atenuacao, a favor da seguranca)."""
    f = next((x for x in _fontes(pj) if "piscina" in x["nome"].lower()), None)
    if not f:
        return None
    dk = pj.DECK
    px = min(max(f["x"], dk["x"]), dk["x"] + dk["w"])
    py = min(max(f["y"], dk["y"]), dk["y"] + dk["h"])
    d = math.sqrt((px - f["x"]) ** 2 + (py - f["y"]) ** 2 + (1_200 - f["z"]) ** 2)
    lp = f["lw"] - 20 * math.log10(max(d, 1_000) / 1000) - 8
    return dict(fonte=f["cod"], lw=f["lw"], d_m=round(d / 1000, 1), lp=round(lp, 1), limite=LIMITE_DECK, ok=lp <= LIMITE_DECK)


def ruido(pj) -> list[dict]:
    """Nivel sonoro de cada fonte externa na janela de cada dormitorio, e
    dentro com a janela fechada: Lp = Lw - 20 log d - 8 (hemisferico, sem
    credito do painel ripado), interno = Lp - (Rw - 3)."""
    out = []
    for f in _fontes(pj):
        for tipo, x, y, o, pav in pj.VAOS:
            amb = pj.amb_do_vao(x, y, pav)
            if pj.CATEGORIA.get(amb) != "intimo" or not tipo.startswith("J") or not pj.vao_externo(x, y, o, pav):
                continue
            lg, al, pe, _ = pj.ESQUADRIAS[tipo]
            z = (pj.NIVEL_SUPERIOR if pav == "S" else 0) + pe + al / 2
            d = math.sqrt((x - f["x"]) ** 2 + (y - f["y"]) ** 2 + (z - f["z"]) ** 2)
            lp = f["lw"] - 20 * math.log10(max(d, 1_000) / 1000) - 8
            dentro = lp - (RW_JANELA - 3)
            out.append(dict(fonte=f["cod"], lw=f["lw"], janela=tipo, amb=amb, pav=pav, d_m=round(d / 1000, 1),
                            lp_janela=round(lp, 1), lp_dentro=round(dentro, 1), limite=LIMITE_DORMITORIO,
                            ok=dentro <= LIMITE_DORMITORIO))
    return sorted(out, key=lambda r: -r["lp_dentro"])


def conferir(pj) -> list[tuple[str, str, bool]]:
    r = rede(pj)
    out = []
    c = r["central"]
    # afastamento da central a qualquer vao (janela/porta externa)
    dmin = min(_manh((c["x"], c["y"]), (x, y)) for _, x, y, _, _ in pj.VAOS)
    out.append(("central GLP longe de vaos", f"{dmin / 1000:.2f} m do vao mais proximo (minimo 1,50 m)",
                dmin >= ABRIGO["afastamento_vao_mm"]))
    out.append(("rede de gas", f"{r['comp_total_mm'] / 1000:.1f} m de cobre DN{TUBO['dn']} para {r['potencia_kw']} kW",
                r["comp_total_mm"] < 60_000))
    for x in renovacao(pj):
        out.append((f"ar novo {x['amb']}", f"{x['q_ls']} L/s ({x['q_m3h']:.0f} m3/h) — {x['como']}", True))
    pior = {}
    for r in ruido(pj):
        if r["amb"] not in pior or r["lp_dentro"] > pior[r["amb"]]["lp_dentro"]:
            pior[r["amb"]] = r
    for amb, r in pior.items():
        out.append((f"ruido em {amb}", f"{r['fonte']} ({r['lw']} dB(A)) a {r['d_m']} m da {r['janela']}: "
                    f"{r['lp_janela']:.0f} dB(A) na janela, {r['lp_dentro']:.0f} dentro (limite {LIMITE_DORMITORIO:.0f})",
                    r["ok"]))
    out.append(("condensadoras no piso", "nenhuma em mao-francesa: " + SUPORTE_COND[:60], "mao-francesa" not in SUPORTE_COND))
    rd = ruido_deck(pj)
    if rd:
        out.append(("bomba da piscina ouvida do deck", f"{rd['fonte']} ({rd['lw']} dB(A)) a {rd['d_m']} m: {rd['lp']:.0f} dB(A) "
                    f"(limite {rd['limite']:.0f}, area de lazer)", rd["ok"]))
    return out
