"""CIRCUITOS — cada circuito com corrente, disjuntor, secao, eletroduto, fase,
queda de tensao e o que se compra; o unifilar e os dois quadros (R72).

eletrica.py (R52) provou que a carga cabe em tres fases equilibradas e que a
entrada e de 125 A. Faltava o que o eletricista executa: 59 circuitos, cada
um com o seu disjuntor e o seu cabo, num quadro que tem de ter vias para
todos, e com queda de tensao dentro dos 4 % da NBR 5410 no ponto mais longe.

Regras (H, NBR 5410):
  - iluminacao 1,5 mm2 / disjuntor 10 A; TUG 2,5 mm2 / 20 A;
  - TUE: disjuntor comercial acima da corrente, secao pela capacidade da
    tabela 36 (B1, PVC, 2 condutores carregados);
  - DR 30 mA para banheiro, cozinha, lavanderia, area externa e chuveiros;
  - queda de tensao terminal <= 4 % (6.2.7), com o ramal de entrada a parte;
  - condutores: fase por cor da fase, neutro azul-claro, protecao verde.
"""
from __future__ import annotations

from nucleo.esgoto import _manh

import math

DISJ = (10, 16, 20, 25, 32, 40, 50, 63)
IZ = {1.5: 17.5, 2.5: 24, 4: 32, 6: 41, 10: 57, 16: 76, 25: 101}     # tabela 36, B1, PVC, 2 carr.
ELETRODUTO = {1.5: 20, 2.5: 20, 4: 25, 6: 25, 10: 32, 16: 32, 25: 40}   # 3 condutores, 40 % (H)
RHO = 0.0172                                                          # ohm mm2/m, cobre
QUEDA_MAX = 4.0
COR_FASE = {"A": "preto", "B": "vermelho", "C": "branco"}
FATOR_PERCURSO = 1.20
PONTO_ILUM_M2 = 6.0            # uma luminaria a cada 6 m2 (H)
DR = dict(tipo="DR 4P 40 A 30 mA", circuitos_por_dr=6)
DPS = dict(tipo="DPS classe II 20 kA, 3F+N", modulos=4)
DG = dict(modulos=3)
RESERVA_VIAS = 0.20


def _quadros(pj) -> dict:
    q = {}
    for t in pj.TECNICOS:
        if t["nome"].lower().startswith("quadro geral"):
            q["QDG"] = dict(cod=t["cod"], nome=t["nome"], x=t["x"], y=t["y"], pav="T",
                            vias=int("".join(ch for ch in t["nome"] if ch.isdigit())))
        if t["nome"].lower().startswith("quadro superior"):
            q["QDS"] = dict(cod=t["cod"], nome=t["nome"], x=t["x"], y=t["y"], pav="S",
                            vias=int("".join(ch for ch in t["nome"] if ch.isdigit())))
    return q


def _amb_de(c: dict) -> str | None:
    if c.get("amb"):
        return c["amb"]
    d = c.get("desc", "").lower()
    for a in ("suite master", "master"):
        if a in d: return "S-MAS"
    if "suite 02" in d: return "S-S02"
    if "suite 03" in d: return "S-S03"
    if "reversivel" in d: return "T-REV"
    if "mini lounge" in d: return "S-LOU"
    if "garagem" in d or "portao" in d or "rack" in d: return "T-GAR"
    if "cozinha" in d or "forno" in d or "micro" in d or "lava-loucas" in d: return "T-COZ"
    if "secadora" in d or "lavadora" in d: return "T-LAV"
    if "zona social" in d or "ventiladores" in d or "coifas" in d: return "T-SOC"
    return None


def _molhado(pj, amb: str | None, c: dict) -> bool:
    if c["tipo"] == "tue" and "chuveiro" in c.get("desc", "").lower():
        return True
    prev = {p["amb"]: p for p in pj.previsao_iluminacao_tug()}
    if amb in prev and prev[amb]["molhada"] and c["tipo"] == "tug":
        return True
    return c["tipo"] == "tug" and amb in ("T-COZ", "T-LAV", "T-GAR", "T-GOU")


def circuitos(pj) -> list[dict]:
    """Os circuitos de eletrica.py, cada um dimensionado e locado num quadro."""
    import nucleo.eletrica as el
    eq = el.equilibrar(pj)
    qs = _quadros(pj)
    ambs = {a.cod: a for a in pj.TERREO + pj.SUPERIOR}
    prev = {p["amb"]: p for p in pj.previsao_iluminacao_tug()}
    out = []
    for c in eq["circuitos"]:
        amb = _amb_de(c)
        pav = "S" if (amb or "").startswith("S-") else "T"
        q = qs["QDS"] if pav == "S" else qs["QDG"]
        ib = c["va"] / c["v"]
        if c["tipo"] == "iluminacao":
            s, disj = 1.5, 10
        elif c["tipo"] == "tug":
            disj = max(20, next((d for d in DISJ if d >= ib), DISJ[-1]))
            s = max(2.5, next((k for k in sorted(IZ) if IZ[k] >= disj), 25))
        else:
            disj = next((d for d in DISJ if d >= ib * 1.0), DISJ[-1])
            s = next((k for k in sorted(IZ) if IZ[k] >= disj), 25)
            if s < 2.5:
                s = 2.5
        a = ambs.get(amb)
        if a is not None:
            comp = (_manh((q["x"], q["y"]), (a.cx, a.cy)) + (a.w + a.h) / 2) * FATOR_PERCURSO
        else:
            comp = 15_000 * FATOR_PERCURSO
        comp += 2_500                                        # descida do quadro e subida ao ponto
        queda = 2 * RHO * (comp / 1000) * ib / (s * c["v"]) * 100
        # nos circuitos longos (cozinha e gourmet ficam a 30 m do quadro da
        # garagem) a queda de tensao manda mais que a corrente: sobe a secao
        # ate caber nos 4 %, e a prancha diz por que o cabo e maior
        secao_por_corrente = s
        while queda > QUEDA_MAX and s < 25:
            s = next(k for k in sorted(IZ) if k > s)
            queda = 2 * RHO * (comp / 1000) * ib / (s * c["v"]) * 100
        n_cond = 3                                           # F+N+PE ou F+F+PE
        polos = 1 if c["v"] == 127 else 2
        p = prev.get(amb, {})
        if c["tipo"] == "iluminacao":
            pontos = max(1, math.ceil(p.get("area", 6) / PONTO_ILUM_M2))
            interruptores = max(1, math.ceil(p.get("area", 6) / 12))
            tomadas = 0
        elif c["tipo"] == "tug":
            pontos = 0; interruptores = 0; tomadas = p.get("tugs", 2)
        else:
            pontos = 0; interruptores = 0; tomadas = 1
        out.append(dict(cod=c["cod"], amb=amb, pav=pav, quadro="QDS" if pav == "S" else "QDG",
                        tipo=c["tipo"], desc=c.get("desc", c["cod"]), va=c["va"], v=c["v"],
                        fases=list(c["fases"]), cores=[COR_FASE[f] for f in c["fases"]],
                        ib_a=round(ib, 1), disjuntor_a=disj, polos=polos, secao_mm2=s,
                        secao_por_corrente=secao_por_corrente, subiu_por_queda=s > secao_por_corrente,
                        iz_a=IZ[s], eletroduto_mm=ELETRODUTO[s], comp_mm=round(comp),
                        cabo_m=round(comp / 1000 * n_cond, 1), queda_pct=round(queda, 2),
                        queda_ok=queda <= QUEDA_MAX, dr=_molhado(pj, amb, c),
                        pontos_luz=pontos, interruptores=interruptores, tomadas=tomadas))
    return out




def quadros(pj) -> list[dict]:
    """Cada quadro: seus circuitos, DR, DPS, vias usadas contra vias que tem."""
    qs = _quadros(pj)
    cs = circuitos(pj)
    out = []
    for k, q in qs.items():
        meus = [c for c in cs if c["quadro"] == k]
        n_dr = math.ceil(sum(1 for c in meus if c["dr"]) / DR["circuitos_por_dr"]) if any(c["dr"] for c in meus) else 0
        vias = sum(c["polos"] for c in meus) + n_dr * 4 + (DPS["modulos"] + DG["modulos"] if k == "QDG" else DG["modulos"])
        vias_reserva = math.ceil(vias * (1 + RESERVA_VIAS))
        va = sum(c["va"] for c in meus)
        por_fase = {f: round(sum(c["va"] / len(c["fases"]) for c in meus if f in c["fases"]), 0) for f in "ABC"}
        out.append(dict(quadro=k, **q, circuitos=len(meus), va=va, por_fase=por_fase,
                        n_dr=n_dr, dr=DR["tipo"], dps=DPS["tipo"] if k == "QDG" else "—",
                        vias_usadas=vias, vias_com_reserva=vias_reserva, vias_disponiveis=q["vias"],
                        cabe=vias_reserva <= q["vias"],
                        alimentador=("ramal de entrada 4 x 50 mm2 + PE 25" if k == "QDG" else
                                     "do QDG, 3F+N+PE 16 mm2, disjuntor 63 A tripolar")))
    return out


def entrada(pj) -> dict:
    import nucleo.eletrica as el
    e = el.entrada(pj)
    med = next(t for t in pj.TECNICOS if "medidor" in t["nome"].lower())
    q = _quadros(pj)["QDG"]
    comp = _manh((med["x"], med["y"]), (q["x"], q["y"])) * FATOR_PERCURSO + 3_000
    queda = math.sqrt(3) * RHO * (comp / 1000) * e["corrente_a"] / (e["secao_mm2"] * 220) * 100
    return dict(**e, medidor=med["cod"], comp_mm=round(comp), queda_pct=round(queda, 2),
                eletroduto="PEAD corrugado 2 x DN75 enterrado (um reserva)")


def materiais(pj) -> list[dict]:
    """O que se compra, somado de todos os circuitos."""
    cs = circuitos(pj)
    cabo = {}
    for c in cs:
        km = c["comp_mm"] / 1000
        cabo[(c["secao_mm2"], "fase")] = cabo.get((c["secao_mm2"], "fase"), 0) + km * (2 if c["v"] == 220 else 1)
        if c["v"] == 127:
            cabo[(c["secao_mm2"], "neutro")] = cabo.get((c["secao_mm2"], "neutro"), 0) + km
        cabo[(c["secao_mm2"], "PE")] = cabo.get((c["secao_mm2"], "PE"), 0) + km
    out = [dict(item=f"cabo {s} mm2 {cor}", qtd=round(v * 1.05, 1), un="m")
           for (s, cor), v in sorted(cabo.items())]
    eld = {}
    for c in cs:
        eld[c["eletroduto_mm"]] = eld.get(c["eletroduto_mm"], 0) + c["comp_mm"] / 1000
    out += [dict(item=f"eletroduto corrugado DN{d}", qtd=round(v, 1), un="m") for d, v in sorted(eld.items())]
    disj = {}
    for c in cs:
        k = (c["disjuntor_a"], c["polos"])
        disj[k] = disj.get(k, 0) + 1
    out += [dict(item=f"disjuntor {a} A {p}P curva C", qtd=n, un="un") for (a, p), n in sorted(disj.items())]
    qs = quadros(pj)
    out.append(dict(item=DR["tipo"], qtd=sum(q["n_dr"] for q in qs), un="un"))
    out.append(dict(item=DPS["tipo"], qtd=1, un="un"))
    out.append(dict(item="disjuntor geral 125 A tripolar", qtd=1, un="un"))
    out.append(dict(item="disjuntor 63 A tripolar (alimentador do QDS)", qtd=1, un="un"))
    for q in qs:
        out.append(dict(item=f"{q['nome']} — {q['quadro']}", qtd=1, un="un"))
    out.append(dict(item="tomada 2P+T 10 A (127 V)", qtd=sum(c["tomadas"] for c in cs if c["tipo"] == "tug"), un="un"))
    out.append(dict(item="tomada 2P+T 20 A (220 V, TUE)", qtd=sum(c["tomadas"] for c in cs if c["tipo"] == "tue"), un="un"))
    out.append(dict(item="interruptor (secao)", qtd=sum(c["interruptores"] for c in cs), un="un"))
    out.append(dict(item="ponto de luz (caixa octogonal)", qtd=sum(c["pontos_luz"] for c in cs), un="un"))
    out.append(dict(item="caixa 4 x 2", qtd=sum(c["tomadas"] + c["interruptores"] for c in cs), un="un"))
    return out


def resumo(pj) -> dict:
    cs = circuitos(pj)
    return dict(circuitos=len(cs), por_quadro={q["quadro"]: q["circuitos"] for q in quadros(pj)},
                dr=sum(1 for c in cs if c["dr"]), queda_max=max(c["queda_pct"] for c in cs),
                pior=max(cs, key=lambda c: c["queda_pct"])["cod"],
                cabo_m=round(sum(c["cabo_m"] for c in cs), 0), entrada=entrada(pj),
                quadros=quadros(pj))


def conferir(pj) -> list[tuple[str, str, bool]]:
    out = []
    for c in circuitos(pj):
        out.append((f"queda {c['cod']}", f"{c['queda_pct']:.2f} % em {c['comp_mm'] / 1000:.1f} m de "
                    f"{c['secao_mm2']} mm2 (maximo {QUEDA_MAX:.0f} %)", c["queda_ok"]))
        out.append((f"protecao {c['cod']}", f"Ib {c['ib_a']} A <= In {c['disjuntor_a']} A <= Iz {c['iz_a']} A",
                    c["ib_a"] <= c["disjuntor_a"] <= c["iz_a"]))
        if c["v"] == 220:
            out.append((f"bifasico {c['cod']}", f"fases {'+'.join(c['fases'])}", len(c["fases"]) == 2))
    for q in quadros(pj):
        out.append((f"vias {q['quadro']}", f"{q['vias_usadas']} usadas + 20 % = {q['vias_com_reserva']} "
                    f"de {q['vias_disponiveis']}", q["cabe"]))
    e = entrada(pj)
    out.append(("queda no ramal de entrada", f"{e['queda_pct']:.2f} % em {e['comp_mm'] / 1000:.1f} m de "
                f"{e['secao_mm2']} mm2 (maximo 1 % reservado)", e["queda_pct"] <= 1.0))
    molh = [c for c in circuitos(pj) if c["dr"]]
    out.append(("DR nos circuitos molhados", f"{len(molh)} circuitos sob DR 30 mA", len(molh) > 0))
    return out
