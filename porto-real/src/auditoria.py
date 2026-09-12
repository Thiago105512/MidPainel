"""
Auditoria automatica do modelo.

Verificacoes rodadas sobre a geometria declarada, nao sobre o desenho: se o
modelo passa, as 13 pranchas passam junto, porque todas leem a mesma fonte.

Criterios: NBR 9050 (acessibilidade), NBR 15575 (desempenho), NBR 9077
(saidas), LC 003/2014 de Manaus (iluminacao e ventilacao, marcado H) e as
proprias metas do briefing.
"""
from __future__ import annotations

import math
from collections import defaultdict

import projeto as pj
import elementos as el
import especificacao as ep

# permanencia prolongada exige 1/6; demais, 1/8 (H — confirmar na LC 003/2014)
PROLONGADA = {"T-REV", "T-SOC", "T-COZ", "T-GOU", "T-OFI",
              "S-S02", "S-S03", "S-MAS"}
# circulacao, garagem e depositos sao dispensados de iluminacao natural pelo
# Codigo de Obras; a garagem ventila pelo proprio portao
DISPENSADOS = {"T-HAL", "S-HAL", "T-COR", "T-GAR", "T-DEP"}
FRAC_PROLONGADA = 1 / 6
FRAC_DEMAIS = 1 / 8
VAO_LIVRE_MIN = 800          # NBR 9050: vao livre de porta
GIRO_PNE = 1_500             # NBR 9050: circulo de giro de 360 graus
MAX_CIRCULACAO = 0.08        # meta do briefing
MAX_RESIDUAL = 0.50          # m2 — meta do briefing


class Achado:
    def __init__(self, nivel, item, detalhe, ref=""):
        self.nivel, self.item, self.detalhe, self.ref = nivel, item, detalhe, ref

    def __repr__(self):
        return f"[{self.nivel}] {self.item}: {self.detalhe}"


def _ambs(pav):
    return pj.TERREO if pav == "T" else pj.SUPERIOR


# ---------------------------------------------------------------- 1. malha
def checar_malha() -> list[Achado]:
    out = []
    for pav in ("T", "S"):
        for a in _ambs(pav) + (pj.TERREO_ABERTO if pav == "T" else pj.SUPERIOR_ABERTO):
            for nome, v in (("x", a.x), ("y", a.y), ("largura", a.w), ("altura", a.h)):
                if v % pj.SUBGRID:
                    out.append(Achado("ERRO", "Malha modular",
                                      f"{a.cod}: {nome} = {v} mm nao e multiplo de {pj.SUBGRID}"))
    return out


# ------------------------------------------------------------ 2. colisoes
def checar_colisoes() -> list[Achado]:
    out = []
    for pav in ("T", "S"):
        lst = _ambs(pav)
        for i, a in enumerate(lst):
            for b in lst[i + 1:]:
                ox = max(0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x))
                oy = max(0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y))
                if ox and oy:
                    out.append(Achado("ERRO", "Sobreposicao",
                                      f"{a.cod} e {b.cod} se sobrepoem em {ox*oy/1e6:.2f} m2"))
    return out


# ----------------------------------------------------- 3. conectividade
def _amb_em(lst, x, y):
    for a in lst:
        if a.x <= x < a.x + a.w and a.y <= y < a.y + a.h:
            return a.cod
    return None


def grafo(pav: str) -> dict[str, set[str]]:
    """Liga ambientes por vaos internos e por integracao declarada."""
    lst = _ambs(pav)
    g = defaultdict(set)
    for tipo, x, y, ori, p in pj.VAOS:
        if p != pav or tipo.startswith("J"):
            continue
        d = 400
        if ori == "H":
            a, b = _amb_em(lst, x, y - d), _amb_em(lst, x, y + d)
        else:
            a, b = _amb_em(lst, x - d, y), _amb_em(lst, x + d, y)
        if a and b and a != b:
            g[a].add(b)
            g[b].add(a)
        elif a or b:
            g[a or b].add("EXTERIOR")
            g["EXTERIOR"].add(a or b)
    for par in pj.INTEGRADOS:
        a, b = tuple(par)
        if a in {x.cod for x in lst} and b in {x.cod for x in lst}:
            g[a].add(b)
            g[b].add(a)
    return g


def checar_conectividade() -> list[Achado]:
    out = []
    for pav in ("T", "S"):
        lst = _ambs(pav)
        g = grafo(pav)
        origem = "EXTERIOR" if pav == "T" else "S-HAL"
        vistos, fila = {origem}, [origem]
        while fila:
            n = fila.pop()
            for m in g.get(n, ()):
                if m not in vistos:
                    vistos.add(m)
                    fila.append(m)
        for a in lst:
            if a.cod not in vistos:
                out.append(Achado("ERRO", "Ambiente inacessivel",
                                  f"{a.cod} ({a.nome}) nao e alcancavel a partir de {origem}"))
            elif not g.get(a.cod):
                out.append(Achado("ERRO", "Sem acesso",
                                  f"{a.cod} nao tem porta nem integracao"))
    return out


# ------------------------------------------- 4. vaos cabem nas paredes
def checar_vaos() -> list[Achado]:
    out = []
    for pav in ("T", "S"):
        paredes = el.derivar_paredes(_ambs(pav))
        for v in el.vaos_do_pavimento(pav):
            par = el._parede_do_vao(paredes, v)
            if par is None:
                out.append(Achado("ERRO", "Vao sem parede",
                                  f"{v['tipo']} em ({v['x']}, {v['y']}) nao encontra parede"))
                continue
            if par.horizontal:
                a, b = min(par.x1, par.x2), max(par.x1, par.x2)
                ini, fim = v["x"] - v["larg"] / 2, v["x"] + v["larg"] / 2
            else:
                a, b = min(par.y1, par.y2), max(par.y1, par.y2)
                ini, fim = v["y"] - v["larg"] / 2, v["y"] + v["larg"] / 2
            if ini < a or fim > b:
                out.append(Achado("ERRO", "Vao extrapola a parede",
                                  f"{v['tipo']} em ({v['x']}, {v['y']}): vao de "
                                  f"{ini:.0f} a {fim:.0f} contra trecho de {a} a {b}"))
    return out


# --------------------------------------- 5. iluminacao e ventilacao
def grupos_integrados(pav: str) -> list[set[str]]:
    lst = {a.cod for a in _ambs(pav)}
    pai = {c: c for c in lst}

    def find(c):
        while pai[c] != c:
            pai[c] = pai[pai[c]]
            c = pai[c]
        return c

    for par in pj.INTEGRADOS:
        a, b = tuple(par)
        if a in lst and b in lst:
            pai[find(a)] = find(b)
    g = defaultdict(set)
    for c in lst:
        g[find(c)].add(c)
    return list(g.values())


def area_vaos_por_ambiente(pav: str) -> dict[str, float]:
    lst = _ambs(pav)
    res = defaultdict(float)
    for tipo, x, y, ori, p in pj.VAOS:
        if p != pav or not tipo.startswith(("J", "PV")):
            continue
        lg, al, _, _ = pj.ESQUADRIAS[tipo]
        d = 400
        if ori == "H":
            cods = [_amb_em(lst, x, y - d), _amb_em(lst, x, y + d)]
        else:
            cods = [_amb_em(lst, x - d, y), _amb_em(lst, x + d, y)]
        internos = [c for c in cods if c]
        for c in internos:
            res[c] += (lg * al) / 1e6 / len(internos)
    return res


def checar_iluminacao() -> list[Achado]:
    out = []
    for pav in ("T", "S"):
        vaos = area_vaos_por_ambiente(pav)
        por_cod = {a.cod: a for a in _ambs(pav)}
        for grupo in grupos_integrados(pav):
            if grupo <= DISPENSADOS:
                continue
            # desconta banho e closet: a exigencia recai sobre o compartimento
            # de permanencia, nao sobre o modulo inteiro da suite
            desc = sum(w * h / 1e6 for cod, _, _, _, w, h in pj.SUBDIVISOES
                       if cod in grupo)
            piso = sum(por_cod[c].area_mod for c in grupo) - desc
            aber = sum(vaos.get(c, 0.0) for c in grupo)
            frac = FRAC_PROLONGADA if grupo & PROLONGADA else FRAC_DEMAIS
            req = piso * frac
            nome = " + ".join(sorted(grupo))
            if aber < req:
                out.append(Achado("ATENCAO" if aber >= req * 0.75 else "ERRO",
                                  "Iluminacao/ventilacao",
                                  f"{nome}: {aber:.2f} m2 de vao para {piso:.2f} m2 de piso "
                                  f"(exigido {req:.2f} m2 = 1/{round(1/frac)})", "LC 003/2014 (H)"))
    return out


# ------------------------------------------------ 6. acessibilidade
def checar_acessibilidade() -> list[Achado]:
    out = []
    for tipo, (lg, al, _, _) in pj.ESQUADRIAS.items():
        if tipo.startswith("P") and not tipo.startswith(("PG", "PV")):
            livre = lg - 60          # desconto de batente e folha aberta
            if livre < VAO_LIVRE_MIN:
                out.append(Achado("ERRO", "Vao livre de porta",
                                  f"{tipo}: {livre} mm livres, minimo {VAO_LIVRE_MIN}", "NBR 9050"))
    bwc = next((a for a in pj.TERREO if a.cod == "T-BWC"), None)
    if bwc:
        menor = min(bwc.w, bwc.h)
        if menor < GIRO_PNE:
            out.append(Achado("ATENCAO", "Circulo de giro",
                              f"Banho compartilhado tem {menor} mm na menor dimensao; o giro de "
                              f"{GIRO_PNE} mm exige porta de correr e area livre sob a bancada",
                              "NBR 9050"))
    return out


# --------------------------------------------- 7. metas do briefing
def checar_metas() -> list[Achado]:
    out = []
    interna = pj.area_fechada("T") + pj.area_fechada("S")
    halls = sum(a.area_mod for a in pj.TERREO + pj.SUPERIOR
                if a.cod in ("T-HAL", "S-HAL"))
    vertical = sum(a.area_mod for a in pj.TERREO if a.cod == "T-COR")
    if halls / interna > MAX_CIRCULACAO:
        out.append(Achado("ATENCAO", "Circulacao horizontal",
                          f"{halls:.2f} m2 = {halls/interna*100:.1f} % da area interna "
                          f"(meta {MAX_CIRCULACAO*100:.0f} %)", "briefing"))
    out.append(Achado("NOTA", "Circulacao",
                      f"halls {halls:.2f} m2 ({halls/interna*100:.1f} %) + core vertical "
                      f"{vertical:.2f} m2; a meta de 8 % do briefing incide sobre halls"))
    for s in pj.SUPERIOR:
        apoio = 0.0
        for t in pj.TERREO:
            ox = max(0, min(s.x + s.w, t.x + t.w) - max(s.x, t.x))
            oy = max(0, min(s.y + s.h, t.y + t.h) - max(s.y, t.y))
            apoio += ox * oy / 1e6
        if apoio < s.area_mod * 0.999:
            sobre_pilares = any(s.x <= p["x"] <= s.x + s.w and s.y <= p["y"] <= s.y + s.h
                                for p in pj.PILARES)
            vencido = 0.0
            for v in pj.VIGAS:
                amb = next((x for x in pj.TERREO_ABERTO if x.cod == v["sobre"]), None)
                if amb and v["vao"] <= pj.VAO_MAX_VIGA:
                    ox = max(0, min(s.x + s.w, amb.x + amb.w) - max(s.x, amb.x))
                    oy = max(0, min(s.y + s.h, amb.y + amb.h) - max(s.y, amb.y))
                    vencido += ox * oy / 1e6
            if vencido >= (s.area_mod - apoio) - 0.01:
                out.append(Achado("NOTA", "Vao vencido por viga",
                                  f"{s.cod}: {vencido:.2f} m2 sobre area aberta, vencidos por "
                                  f"viga entre apoios existentes — laje apoiada, nao balanco"))
            elif sobre_pilares:
                out.append(Achado("NOTA", "Apoio sobre pilares",
                                  f"{s.cod}: {s.area_mod-apoio:.2f} m2 sobre area aberta, "
                                  f"apoiados em {len(pj.PILARES)} pilares — terraco coberto "
                                  f"no terreo, nao balanco"))
            else:
                nivel = "ATENCAO" if apoio >= s.area_mod * 0.5 else "ERRO"
                out.append(Achado(nivel, "Balanco estrutural",
                                  f"{s.cod}: {s.area_mod-apoio:.2f} m2 sem apoio "
                                  f"({(1-apoio/s.area_mod)*100:.0f} % em balanco)"))
    return out


# ------------------------------------------------- 8. escada e niveis
def checar_escada() -> list[Achado]:
    e = pj.ESCADA
    out = []
    b = e["blondel"]
    if not 630 <= b <= 650:
        out.append(Achado("ATENCAO", "Formula de Blondel",
                          f"2h + p = {b:.2f} mm, fora da faixa de 630 a 650"))
    if e["alt_espelho"] > 180:
        out.append(Achado("ERRO", "Espelho",
                          f"{e['alt_espelho']:.2f} mm acima do maximo usual de 180"))
    if e["larg_lance"] < 900:
        out.append(Achado("ATENCAO", "Largura da escada",
                          f"{e['larg_lance']} mm; 1.200 mm facilita transporte e uso futuro"))
    return out


# ------------------------------------------ 9. coerencia de vedacao
def checar_vedacao() -> list[Achado]:
    out = []
    for s in ep.paredes_classificadas(pj.TERREO):
        if "T-OFI" in (s["a"], s["b"]) and s["familia"] == "PH-1":
            out.append(Achado("ERRO", "Prumada na oficina",
                              "parede hidraulica encostando no ambiente que pede silencio"))
    molhados_sem_prumada = []
    integrados = {c for par in pj.INTEGRADOS for c in par}
    for a in pj.TERREO + pj.SUPERIOR:
        if a.cod in ep.MOLHADOS or "BANHO" in a.nome:
            if a.cod in integrados:
                continue          # divide a prumada do ambiente integrado
            tem = any(s["familia"] in ("PH-1",) and a.cod in (s["a"], s["b"])
                      for s in ep.paredes_classificadas(_ambs(a.pav)))
            if not tem:
                molhados_sem_prumada.append(a.cod)
    if molhados_sem_prumada:
        out.append(Achado("ATENCAO", "Prumada hidraulica",
                          f"sem parede PH-1 identificada: {', '.join(molhados_sem_prumada)}"))
    return out


# -------------------------------------------------------- consolidado
def auditar() -> list[Achado]:
    return (checar_malha() + checar_colisoes() + checar_conectividade() +
            checar_vaos() + checar_iluminacao() + checar_acessibilidade() +
            checar_metas() + checar_escada() + checar_vedacao())


if __name__ == "__main__":
    achados = auditar()
    for n in ("ERRO", "ATENCAO", "NOTA"):
        grupo = [a for a in achados if a.nivel == n]
        print(f"\n=== {n}  ({len(grupo)}) ===")
        for a in grupo:
            print(f"  {a.item}: {a.detalhe}" + (f"  [{a.ref}]" if a.ref else ""))
    print(f"\ntotal: {len(achados)} achados")
