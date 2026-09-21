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
SUPORTE_COND = "mao-francesa em aco galvanizado 450 mm, par, carga 60 kg, com coxim"
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
                      "linha isolada com elastomerico 9 mm, acabamento em canaleta")


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
    return out
