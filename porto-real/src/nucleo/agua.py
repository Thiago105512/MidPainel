"""AGUA FRIA — do reservatorio a cada peca, com diametro, registro e pressao (R72).

A PR-26 dimensionava o alimentador pelo metodo dos pesos e parava. Aqui a rede
e percorrida inteira: barrilete sob a caixa, coluna, ramal de cada ambiente
molhado, sub-ramal de cada peca — e em cada peca a pressao que sobra depois
das perdas. E essa conta, e nao uma frase, que diz por que o pavimento
superior e pressurizado (TC-14) e o terreo nao.

Perda de carga por Fair-Whipple-Hsiao para PVC (NBR 5626):
    J = 8,69 x 10^6 x Q^1,75 x D^-4,75   [kPa/m; Q em L/s; D interno em mm]
Perdas localizadas como 30 % das distribuidas (H). Pressao dinamica minima
de 10 kPa em qualquer peca (NBR 5626); estatica maxima de 400 kPa.
"""
from __future__ import annotations

from nucleo.esgoto import _manh, _pav

import math

# diametro interno comercial do PVC soldavel (mm) por DN
DI = {20: 17.0, 25: 21.6, 32: 27.8, 40: 35.2, 50: 44.0, 60: 53.4, 75: 66.6}
# sub-ramal por peca (H): NBR 5626 nao fixa; pratica com PVC soldavel
DN_SUB = {"lavatorio": 20, "vaso": 20, "box": 20, "pia": 20, "tanque": 25,
          "lavadora": 25, "ducha_externa": 20}
PRESSAO_MIN_KPA = 10.0
PRESSAO_MAX_KPA = 400.0
NIVEL_MIN_ACIMA_FUNDO = 200          # lamina minima util na caixa (H)
FATOR_LOCALIZADAS = 1.30
FATOR_PERCURSO = 1.20
Z_PECA = {"lavatorio": 600, "vaso": 300, "box": 2_100, "pia": 900, "tanque": 900,
          "lavadora": 900, "ducha_externa": 2_100}
Z_BARRILETE_ABAIXO = 300
REGISTRO = {"ramal": "registro de gaveta", "box": "registro de pressao", "coluna": "registro de gaveta",
            "geral": "registro de gaveta + valvula de retencao"}


def _q(pesos: float) -> float:
    return 0.3 * math.sqrt(pesos)


def _dn_para(q_ls: float, v_max: float) -> int:
    for dn in sorted(DI):
        a = math.pi * (DI[dn] / 1000) ** 2 / 4
        if q_ls / 1000 / a <= v_max:
            return dn
    return 75


def _j(q_ls: float, dn: int) -> float:
    return 8.69e6 * q_ls ** 1.75 * DI[dn] ** -4.75 if q_ls > 0 else 0.0






def _z_piso(pav, pj):
    return pj.NIVEL_SUPERIOR if pav == "S" else 0


def reservatorio(pj) -> dict:
    cd = pj.CAIXA_DAGUA
    return dict(x=cd["x"] + cd["w"] / 2, y=cd["y"] + cd["h"] / 2, volume_l=cd["volume_l"],
                nivel_fundo=cd["nivel_base"], nivel_min=cd["nivel_base"] + NIVEL_MIN_ACIMA_FUNDO,
                z_barrilete=cd["nivel_base"] - Z_BARRILETE_ABAIXO)


def ramais(pj) -> list[dict]:
    """Um ramal por ambiente molhado, da coluna ate o ambiente, com o registro
    de gaveta na entrada; DN pela vazao dos pesos a v <= VEL_CONFORTO."""
    col = next(p for p in pj.PRUMADAS if p["tipo"] == "agua fria")
    por_amb = {}
    for p in pj.pecas_hidraulicas():
        por_amb.setdefault(p["amb"], []).append(p)
    out = []
    for amb, pecas in por_amb.items():
        pesos = sum(p["peso"] for p in pecas)
        q = _q(pesos)
        dn = _dn_para(q, pj.VEL_CONFORTO)
        cx = sum(p["x"] for p in pecas) / len(pecas)
        cy = sum(p["y"] for p in pecas) / len(pecas)
        comp = _manh((col["x"], col["y"]), (cx, cy)) * FATOR_PERCURSO
        out.append(dict(cod=f"RA-{amb}", amb=amb, pav=_pav(amb), pecas=[p["cod"] for p in pecas],
                        pesos=round(pesos, 2), q_ls=round(q, 3), dn=dn,
                        v_ms=round(q / 1000 / (math.pi * (DI[dn] / 1000) ** 2 / 4), 2),
                        comp_mm=round(comp), registro=f"{REGISTRO['ramal']} DN{dn}",
                        j_kpa_m=round(_j(q, dn), 3), perda_kpa=round(_j(q, dn) * comp / 1000 * FATOR_LOCALIZADAS, 1)))
    return out


def coluna(pj) -> list[dict]:
    """Barrilete e coluna: pesos acumulados por trecho."""
    r = reservatorio(pj)
    col = next(p for p in pj.PRUMADAS if p["tipo"] == "agua fria")
    rs = ramais(pj)
    pesos_s = sum(x["pesos"] for x in rs if x["pav"] == "S")
    pesos_t = sum(x["pesos"] for x in rs if x["pav"] == "T")
    tot = pesos_s + pesos_t
    q_tot, q_t = _q(tot), _q(pesos_t)
    dn_b = _dn_para(q_tot, pj.VEL_CONFORTO)
    dn_ct = _dn_para(q_t, pj.VEL_CONFORTO)
    comp_b = _manh((r["x"], r["y"]), (col["x"], col["y"])) * FATOR_PERCURSO + Z_BARRILETE_ABAIXO
    trechos = [
        dict(cod="BAR", de="reservatorio", para="coluna AF-01", pesos=round(tot, 2), q_ls=round(q_tot, 3),
             dn=dn_b, comp_mm=round(comp_b), z0=r["z_barrilete"], z1=r["z_barrilete"],
             registro=f"{REGISTRO['geral']} DN{dn_b}", perda_kpa=round(_j(q_tot, dn_b) * comp_b / 1000 * FATOR_LOCALIZADAS, 1)),
        dict(cod="COL-S", de="barrilete", para="ramais do superior", pesos=round(tot, 2), q_ls=round(q_tot, 3),
             dn=dn_b, comp_mm=r["z_barrilete"] - (pj.NIVEL_SUPERIOR + 2_400), z0=r["z_barrilete"], z1=pj.NIVEL_SUPERIOR + 2_400,
             registro=f"{REGISTRO['coluna']} DN{dn_b}",
             perda_kpa=round(_j(q_tot, dn_b) * (r["z_barrilete"] - pj.NIVEL_SUPERIOR - 2_400) / 1000 * FATOR_LOCALIZADAS, 1)),
        dict(cod="COL-T", de="ramais do superior", para="ramais do terreo", pesos=round(pesos_t, 2), q_ls=round(q_t, 3),
             dn=dn_ct, comp_mm=pj.NIVEL_SUPERIOR + 2_400 - 2_400, z0=pj.NIVEL_SUPERIOR + 2_400, z1=2_400,
             registro=f"{REGISTRO['coluna']} DN{dn_ct}",
             perda_kpa=round(_j(q_t, dn_ct) * pj.NIVEL_SUPERIOR / 1000 * FATOR_LOCALIZADAS, 1)),
    ]
    return trechos


def pecas(pj) -> list[dict]:
    """Cada peca: sub-ramal, altura, pressao estatica e dinamica, e o veredito."""
    r = reservatorio(pj)
    col = {c["cod"]: c for c in coluna(pj)}
    rs = {x["amb"]: x for x in ramais(pj)}
    press = {p["pav"]: p.get("pressurizado", False) for p in pj.prumadas_hidraulicas() if p["pav"] in ("T", "S")}
    out = []
    for p in pj.pecas_hidraulicas():
        pav = _pav(p["amb"])
        z = _z_piso(pav, pj) + Z_PECA[p["tipo"]]
        dn = DN_SUB[p["tipo"]]
        q = _q(p["peso"])
        ram = rs[p["amb"]]
        cx = sum(pj.pecas_hidraulicas()[i]["x"] for i in range(len(pj.pecas_hidraulicas())) if pj.pecas_hidraulicas()[i]["amb"] == p["amb"]) / len(ram["pecas"])
        cy = sum(pj.pecas_hidraulicas()[i]["y"] for i in range(len(pj.pecas_hidraulicas())) if pj.pecas_hidraulicas()[i]["amb"] == p["amb"]) / len(ram["pecas"])
        comp_sub = (_manh((cx, cy), (p["x"], p["y"])) + abs(2_400 - Z_PECA[p["tipo"]])) * FATOR_PERCURSO + 300
        # R80 — onde o percurso parede a parede existe, o sub-ramal e o trecho
        # real da coluna ate a peca, sem o fator 1,2
        import nucleo.percurso as _pr
        _real = _pr.comprimentos_agua(pj).get(p["cod"])
        if _real:
            # o percurso vai da coluna a peca; o ramal do ambiente ja esta
            # contado em ram["perda_kpa"], entao o sub-ramal e o que sobra
            comp_sub = max(300, _real - ram["comp_mm"])
        estatica = 9.81 * (r["nivel_min"] - z) / 1000
        perdas = col["BAR"]["perda_kpa"] + col["COL-S"]["perda_kpa"] + (col["COL-T"]["perda_kpa"] if pav == "T" else 0) \
            + ram["perda_kpa"] + _j(q, dn) * comp_sub / 1000 * FATOR_LOCALIZADAS
        dinamica = estatica - perdas
        ok_grav = dinamica >= PRESSAO_MIN_KPA
        out.append(dict(cod=p["cod"], amb=p["amb"], pav=pav, tipo=p["tipo"], peso=p["peso"], z_mm=z,
                        dn_sub=dn, comp_sub_mm=round(comp_sub), q_ls=round(q, 3),
                        estatica_kpa=round(estatica, 1), perdas_kpa=round(perdas, 1), dinamica_kpa=round(dinamica, 1),
                        minimo_kpa=PRESSAO_MIN_KPA, gravidade_ok=ok_grav,
                        pressurizado=press.get(pav, False),
                        ok=ok_grav or press.get(pav, False),
                        registro=(f"{REGISTRO['box']} DN{dn}" if p["tipo"] in ("box", "ducha_externa") else "—")))
    return out


def registros(pj) -> list[dict]:
    out = [dict(cod="RG-GERAL", onde="saida do reservatorio (barrilete)", tipo=coluna(pj)[0]["registro"])]
    for c in coluna(pj)[1:]:
        out.append(dict(cod=f"RG-{c['cod']}", onde=c["para"], tipo=c["registro"]))
    for r in ramais(pj):
        out.append(dict(cod=f"RG-{r['amb']}", onde=f"entrada do ramal de {r['amb']}", tipo=r["registro"]))
    for p in pecas(pj):
        if p["registro"] != "—":
            out.append(dict(cod=f"RP-{p['cod']}", onde=f"{p['tipo']} {p['cod']}", tipo=p["registro"]))
    return out


def resumo(pj) -> dict:
    ps = pecas(pj)
    comp = {}
    for c in coluna(pj):
        comp[c["dn"]] = comp.get(c["dn"], 0) + c["comp_mm"]
    for r in ramais(pj):
        comp[r["dn"]] = comp.get(r["dn"], 0) + r["comp_mm"]
    for p in ps:
        comp[p["dn_sub"]] = comp.get(p["dn_sub"], 0) + p["comp_sub_mm"]
    return dict(pecas=len(ps), ramais=len(ramais(pj)), registros=len(registros(pj)),
                comp_por_dn_m={dn: round(v / 1000, 1) for dn, v in sorted(comp.items())},
                gravidade_ok=sum(1 for p in ps if p["gravidade_ok"]),
                pressurizadas=sum(1 for p in ps if not p["gravidade_ok"] and p["pressurizado"]),
                pior_terreo=min((p["dinamica_kpa"] for p in ps if p["pav"] == "T"), default=None),
                pior_superior=min((p["dinamica_kpa"] for p in ps if p["pav"] == "S"), default=None),
                reservatorio=reservatorio(pj))


def conferir(pj) -> list[tuple[str, str, bool]]:
    out = []
    for p in pecas(pj):
        out.append((f"pressao {p['cod']}",
                    f"{p['tipo']} a z={p['z_mm']}: estatica {p['estatica_kpa']:.0f} kPa, dinamica "
                    f"{p['dinamica_kpa']:.0f} kPa (minimo {PRESSAO_MIN_KPA:.0f})"
                    + ("" if p["gravidade_ok"] else " — pressurizado por TC-14" if p["pressurizado"] else " — INSUFICIENTE"),
                    p["ok"]))
        out.append((f"estatica maxima {p['cod']}", f"{p['estatica_kpa']:.0f} kPa (maximo {PRESSAO_MAX_KPA:.0f})",
                    p["estatica_kpa"] <= PRESSAO_MAX_KPA))
    for r in ramais(pj) + coluna(pj):
        v = r.get("v_ms", None)
        if v is not None:
            out.append((f"velocidade {r['cod']}", f"{v:.2f} m/s em DN{r['dn']} (conforto {pj.VEL_CONFORTO})",
                        v <= pj.VEL_CONFORTO + 0.01))
    # o superior so passa pressurizado: a conta tem de dizer isso, nao a frase
    sup = [p for p in pecas(pj) if p["pav"] == "S"]
    out.append(("superior pressurizado por necessidade",
                f"{sum(1 for p in sup if not p['gravidade_ok'])} de {len(sup)} pecas do superior ficam abaixo "
                f"de {PRESSAO_MIN_KPA:.0f} kPa por gravidade: o pressurizador TC-14 nao e opcao",
                any(not p["gravidade_ok"] for p in sup) == any(p["pressurizado"] for p in sup)))
    return out
