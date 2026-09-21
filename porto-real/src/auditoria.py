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
DISPENSADOS = {"T-HAL", "T-CIR", "S-HAL", "T-COR", "T-GAR", "T-DEP"}
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


def checar_acesso_por_molhado() -> list[Achado]:
    """Ambiente de permanencia nao pode ter como unico acesso um ambiente
    molhado ou privativo de outro. Atravessar banheiro para chegar ao quarto
    e erro de partido, nao de desenho."""
    out = []
    for pav in ("T", "S"):
        g = grafo(pav)
        for a_ in _ambs(pav):
            if a_.cod not in PROLONGADA:
                continue
            viz = g.get(a_.cod, set())
            if not viz:
                continue
            molhados = {v for v in viz if any(
                x.cod == v and (x.molhado or "BANHO" in x.nome)
                for x in _ambs(pav))}
            if viz and viz <= molhados:
                out.append(Achado("ERRO", "Acesso so por ambiente molhado",
                                  f"{a_.cod} ({a_.nome}) so e alcancavel atravessando "
                                  f"{', '.join(sorted(viz))}"))
    return out


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
            desc = sum(sd["w"] * sd["h"] / 1e6 for sd in pj.SUBDIVISOES
                       if sd["pai"] in grupo)
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
    # R54 — o lavabo virou subdivisao do core, e a regra segue a mesma: o giro
    # de 1.500 mm nao cabe num lavabo sob escada e nunca coube num de 1,80 m.
    # O que muda e que agora esta escrito de onde a dimensao vem.
    bwc = next((d for d in pj.SUBDIVISOES
                if f"{d['pai']}/{d['nome']}" in pj.LAVABOS), None)
    if bwc:
        menor = min(bwc["w"], bwc["h"])
        if menor < GIRO_PNE:
            out.append(Achado("ATENCAO", "Circulo de giro",
                              f"Lavabo tem {menor} mm na menor dimensao; o giro de "
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
    for s in pj.SUPERIOR + pj.SUPERIOR_ABERTO:
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


# ------------------------------------------- 10. espacos mortos
def espacos_mortos() -> list[tuple[float, int, int]]:
    """Varre o lote em celulas de 600 mm e acha bolsoes sem funcao declarada
    que encostam na edificacao. Jardim e recuo declarado nao contam."""
    G = pj.GRID
    nx, ny = pj.LOTE_L // G, pj.LOTE_P // G
    declarado = [[False] * ny for _ in range(nx)]

    def marcar(x, y, w, h):
        for i in range(max(0, x // G), min(nx, (x + w) // G)):
            for j in range(max(0, y // G), min(ny, (y + h) // G)):
                declarado[i][j] = True

    for amb in pj.TERREO + pj.TERREO_ABERTO:
        marcar(amb.x, amb.y, amb.w, amb.h)
    marcar(pj.PISCINA["x"], pj.PISCINA["y"], pj.PISCINA["w"], pj.PISCINA["h"])
    marcar(pj.DECK["x"], pj.DECK["y"], pj.DECK["w"], pj.DECK["h"])
    ft = pj.FAIXA_TECNICA
    marcar(ft["x"], ft["y"], ft["w"], ft["h"])
    marcar(0, 0, pj.LOTE_L, pj.RECUO_FRENTE)              # acesso e manobra
    marcar(0, 0, pj.RECUO_ESQ, pj.LOTE_P)                  # recuo lateral sul

    edif = [[False] * ny for _ in range(nx)]
    for amb in pj.TERREO:
        for i in range(amb.x // G, (amb.x + amb.w) // G):
            for j in range(amb.y // G, (amb.y + amb.h) // G):
                edif[i][j] = True

    vistos, achados = set(), []
    for i in range(nx):
        for j in range(ny):
            if declarado[i][j] or (i, j) in vistos:
                continue
            fila, comp, encosta = [(i, j)], [], False
            vistos.add((i, j))
            while fila:
                ci, cj = fila.pop()
                comp.append((ci, cj))
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ni, nj = ci + di, cj + dj
                    if not (0 <= ni < nx and 0 <= nj < ny):
                        continue
                    if edif[ni][nj]:
                        encosta = True
                    elif not declarado[ni][nj] and (ni, nj) not in vistos:
                        vistos.add((ni, nj))
                        fila.append((ni, nj))
            area = len(comp) * (G / 1000) ** 2
            # jardim amplo NAO e espaco morto. E morto o bolsao estreito
            # (menos de 2.400 mm no menor lado) ou o pequeno e enclausurado.
            xs = [c[0] for c in comp]
            ys = [c[1] for c in comp]
            menor = min((max(xs) - min(xs) + 1), (max(ys) - min(ys) + 1)) * G
            estreito = menor < 2_400
            pequeno_fechado = area < 10.0
            if encosta and area > MAX_RESIDUAL and (estreito or pequeno_fechado):
                cx = sum(xs) / len(comp) * G
                cy = sum(ys) / len(comp) * G
                achados.append((area, int(cx), int(cy), int(menor)))
    return sorted(achados, reverse=True)


def checar_espacos_mortos() -> list[Achado]:
    out = []
    for area, cx, cy, menor in espacos_mortos():
        out.append(Achado("ATENCAO", "Espaco morto",
                          f"{area:.2f} m2 encostando na edificacao, centro em "
                          f"({cx}, {cy}), menor dimensao {menor} mm — "
                          f"estreito ou enclausurado demais para ter uso",
                          f"briefing: maximo {MAX_RESIDUAL:.2f} m2"))
    return out


# ---------------------------------- 11. bancadas: densidade e folga
def checar_bancadas() -> list[Achado]:
    out = []
    for b in pj.BANCADAS:
        amb = next((x for x in pj.TERREO + pj.SUPERIOR if x.cod == b["amb"]), None)
        if amb is None:
            out.append(Achado("ERRO", "Bancada sem ambiente",
                              f"{b['cod']} referencia {b['amb']}"))
            continue
        dentro = (amb.x <= b["x"] and b["x"] + b["w"] <= amb.x + amb.w and
                  amb.y <= b["y"] and b["y"] + b["h"] <= amb.y + amb.h)
        if not dentro and not _cabe_no_grupo(b):
            out.append(Achado("ERRO", "Bancada fora do ambiente",
                              f"{b['cod']} em ({b['x']}, {b['y']}) nao cabe em {b['amb']} "
                              f"[{amb.x}, {amb.y}, {amb.w} x {amb.h}]"))
    social = [b for b in pj.BANCADAS if b["amb"] in ("T-COZ", "T-GOU")]
    linear = sum(max(b["w"], b["h"]) / 1000 for b in social)
    cubas = sum(b["cubas"] for b in social)
    pessoas = 5
    if linear / pessoas > 3.0:
        out.append(Achado("ATENCAO", "Densidade de bancada",
                          f"{linear:.2f} m lineares na fita social para {pessoas} pessoas "
                          f"({linear/pessoas:.2f} m por pessoa); referencia usual 1,5 a 2,5",
                          "pratica corrente"))
    if cubas > 2:
        out.append(Achado("ATENCAO", "Pontos de agua redundantes",
                          f"{cubas} cubas na mesma sala integrada; o usual e uma principal "
                          f"mais, quando muito, uma de apoio"))
    # A versao anterior desta verificacao subtraia a largura de TODAS as bancadas
    # paralelas do mesmo ambiente, como se estivessem todas na mesma secao
    # transversal. Duas bancadas na mesma parede, uma depois da outra, nunca
    # disputam o mesmo corredor — e a conta acusava 600 mm onde havia 1.700.
    # Agora o corredor e medido de fato: da face livre da bancada ate o primeiro
    # obstaculo que COINCIDE com ela no eixo longo.
    for b in pj.BANCADAS:
        amb = next((x for x in pj.TERREO if x.cod == b["amb"]), None)
        if amb is None:
            continue
        vertical = b["h"] > b["w"]
        # eixo longo (onde a bancada se estende) e eixo do corredor
        if vertical:
            ini, fim = b["y"], b["y"] + b["h"]
            face_a, face_b = b["x"], b["x"] + b["w"]
            lim_a, lim_b = amb.x, amb.x + amb.w
        else:
            ini, fim = b["x"], b["x"] + b["w"]
            face_a, face_b = b["y"], b["y"] + b["h"]
            lim_a, lim_b = amb.y, amb.y + amb.h
        encostada_a = abs(face_a - lim_a) <= 200
        encostada_b = abs(lim_b - face_b) <= 200
        def _obstaculos(desde, sentido):
            d = abs(lim_b - face_b) if sentido > 0 else abs(face_a - lim_a)
            for o in pj.BANCADAS:
                if o["cod"] == b["cod"] or o["amb"] != b["amb"]:
                    continue
                oi, of = ((o["y"], o["y"] + o["h"]) if vertical
                          else (o["x"], o["x"] + o["w"]))
                if of <= ini or oi >= fim:      # nao coincide no eixo longo
                    continue
                oa, ob = ((o["x"], o["x"] + o["w"]) if vertical
                          else (o["y"], o["y"] + o["h"]))
                if sentido > 0 and oa >= desde:
                    d = min(d, oa - desde)
                elif sentido < 0 and ob <= desde:
                    d = min(d, desde - ob)
            return d
        if encostada_a and not encostada_b:
            livre = _obstaculos(face_b, +1)
        elif encostada_b and not encostada_a:
            livre = _obstaculos(face_a, -1)
        else:   # peninsula ou ilha: o menor dos dois lados que tenham obstaculo
            livre = max(_obstaculos(face_b, +1), _obstaculos(face_a, -1))
        if livre < pj.CIRC_BANCADA_MIN:
            out.append(Achado("ERRO", "Circulacao em frente a bancada",
                              f"{b['cod']} em {b['amb']}: {livre:.0f} mm livres, "
                              f"minimo {pj.CIRC_BANCADA_MIN}", "briefing"))
        elif livre < pj.CIRC_BANCADA_DESEJADA:
            out.append(Achado("NOTA", "Circulacao em frente a bancada",
                              f"{b['cod']}: {livre:.0f} mm — atende o minimo, abaixo do "
                              f"desejado de {pj.CIRC_BANCADA_DESEJADA}"))
    return out


# ------------------------------------ 12. loucas e equipamentos
def _cabe_no_grupo(peca) -> bool:
    """A peca cabe na uniao do grupo integrado do seu ambiente?"""
    cod = peca["amb"]
    grupo = {cod}
    for par in pj.INTEGRADOS:
        if cod in par:
            grupo |= set(par)
    rects = [(a.x, a.y, a.w, a.h) for a in pj.TERREO + pj.SUPERIOR if a.cod in grupo]
    passo = 100
    x, y = peca["x"], peca["y"]
    while x < peca["x"] + peca["w"]:
        y = peca["y"]
        while y < peca["y"] + peca["h"]:
            if not any(rx <= x < rx + rw and ry <= y < ry + rh for rx, ry, rw, rh in rects):
                return False
            y += passo
        x += passo
    return True


def _area_alvo(peca) -> tuple[int, int, int, int] | None:
    """Onde a peca deve caber: a subdivisao BANHO, quando existir; senao o ambiente."""
    cod = peca["amb"]
    if peca["tipo"] in ("vaso", "lavatorio", "box"):
        for sd in pj.SUBDIVISOES:
            if sd["pai"] == cod and sd["nome"] == "BANHO":
                return sd["x"], sd["y"], sd["w"], sd["h"]
    for a_ in pj.TERREO + pj.SUPERIOR:
        if a_.cod == cod:
            return a_.x, a_.y, a_.w, a_.h
    return None


def checar_loucas() -> list[Achado]:
    out = []
    for p in pj.LOUCAS + pj.EQUIPAMENTOS + pj.ARMARIOS:
        alvo = _area_alvo(p)
        if alvo is None:
            out.append(Achado("ERRO", "Peca sem ambiente",
                              f"{p['cod']} referencia {p['amb']}, que nao existe"))
            continue
        ax, ay, aw, ah = alvo
        if not (ax <= p["x"] and p["x"] + p["w"] <= ax + aw and
                ay <= p["y"] and p["y"] + p["h"] <= ay + ah) and not _cabe_no_grupo(p):
            out.append(Achado("ERRO", "Peca fora do ambiente",
                              f"{p['cod']} ({p['tipo']}) em ({p['x']}, {p['y']}) "
                              f"nao cabe em {p['amb']} [{ax}, {ay}, {aw} x {ah}]"))

    # loucas obrigatorias por ambiente molhado
    # R53 — derivado: todo ambiente ou subdivisao molhada exige vaso e
    # lavatorio; box so onde ha banho (lavabo declarado em pj.LAVABOS nao
    # tem). Antes era dicionario escrito a mao, e o lavabo novo reprovou por
    # "falta de box" — a regra estava certa e a lista estava velha.
    exigidas = {}
    for a in pj.TERREO + pj.SUPERIOR:
        if getattr(a, "molhado", False) and a.cod not in ("T-COZ", "T-GOU",
                                                           "T-LAV", "T-DEP"):
            exigidas[a.cod] = ({"vaso", "lavatorio"} if a.cod in pj.LAVABOS
                               else {"vaso", "lavatorio", "box"})
    for sd in pj.SUBDIVISOES:
        if not sd.get("molhado"):
            continue
        cod = f"{sd['pai']}/{sd['nome']}"
        # as loucas sao declaradas com o codigo do PAI: a subdivisao nao e um
        # ambiente do modelo, e sim um recorte dele
        exigidas[sd["pai"]] = ({"vaso", "lavatorio"} if cod in pj.LAVABOS
                               else {"vaso", "lavatorio", "box"})
    exigidas["T-LAV"] = {"tanque"}
    for cod, req in exigidas.items():
        tem = {p["tipo"] for p in pj.LOUCAS if p["amb"] == cod}
        faltando = req - tem
        if faltando:
            out.append(Achado("ERRO", "Louca faltando",
                              f"{cod}: sem {', '.join(sorted(faltando))}"))

    # folgas
    for p in pj.LOUCAS:
        alvo = _area_alvo(p)
        if alvo is None:
            continue
        ax, ay, aw, ah = alvo
        if p["tipo"] == "box":
            if min(p["w"], p["h"]) < pj.BOX_MIN:
                out.append(Achado("ERRO", "Box abaixo do minimo",
                                  f"{p['cod']}: {min(p['w'], p['h'])} mm, "
                                  f"minimo {pj.BOX_MIN}", "NBR 15575"))
            continue
        frente = (ay + ah) - (p["y"] + p["h"])
        frente = max(frente, p["y"] - ay)
        if frente < pj.FOLGA_FRONTAL_LOUCA:
            out.append(Achado("ATENCAO", "Folga frontal de louca",
                              f"{p['cod']} ({p['tipo']}): {frente} mm livres, "
                              f"minimo {pj.FOLGA_FRONTAL_LOUCA}", "NBR 9050"))
        if p["tipo"] == "vaso":
            eixo = p["x"] + p["w"] / 2
            lateral = min(eixo - ax, (ax + aw) - eixo)
            if lateral < pj.FOLGA_LATERAL_VASO:
                out.append(Achado("ATENCAO", "Afastamento lateral do vaso",
                                  f"{p['cod']}: eixo a {lateral:.0f} mm da parede, "
                                  f"minimo {pj.FOLGA_LATERAL_VASO}"))
    return out


# ------------------------------------------- 13. subdivisoes
BANHO_MIN = 1_500          # menor dimensao util de banho
CLOSET_PROF_MIN = 600      # profundidade minima de closet


def checar_subdivisoes() -> list[Achado]:
    out = []
    por_pai: dict[str, list] = {}
    for sd in pj.SUBDIVISOES:
        por_pai.setdefault(sd["pai"], []).append(sd)

    for pai_cod, lista in por_pai.items():
        pai = next((a for a in pj.TERREO + pj.SUPERIOR if a.cod == pai_cod), None)
        if pai is None:
            out.append(Achado("ERRO", "Subdivisao orfa",
                              f"{pai_cod} nao existe como ambiente"))
            continue
        for sd in lista:
            # dentro do pai
            if not (pai.x <= sd["x"] and sd["x"] + sd["w"] <= pai.x + pai.w and
                    pai.y <= sd["y"] and sd["y"] + sd["h"] <= pai.y + pai.h):
                out.append(Achado("ERRO", "Subdivisao fora do ambiente",
                                  f"{pai_cod}/{sd['nome']} nao cabe em "
                                  f"[{pai.x}, {pai.y}, {pai.w} x {pai.h}]"))
            # dimensoes minimas
            if sd["nome"] == "BANHO" and min(sd["w"], sd["h"]) < BANHO_MIN:
                out.append(Achado("ATENCAO", "Banho estreito",
                                  f"{pai_cod}: {min(sd['w'], sd['h'])} mm, "
                                  f"minimo util {BANHO_MIN}"))
            if sd["nome"] == "CLOSET" and min(sd["w"], sd["h"]) < CLOSET_PROF_MIN:
                out.append(Achado("ATENCAO", "Closet raso",
                                  f"{pai_cod}: {min(sd['w'], sd['h'])} mm, "
                                  f"minimo {CLOSET_PROF_MIN}"))
            # a face da porta e interna?
            f = sd["face"]
            externa = ((f == "S" and sd["x"] == pai.x) or
                       (f == "N" and sd["x"] + sd["w"] == pai.x + pai.w) or
                       (f == "L" and sd["y"] == pai.y) or
                       (f == "O" and sd["y"] + sd["h"] == pai.y + pai.h))
            if externa:
                out.append(Achado("ERRO", "Porta em face externa",
                                  f"{pai_cod}/{sd['nome']}: a porta esta na face {f}, "
                                  f"que coincide com a parede externa do modulo"))
            # o vao cabe na face?
            if f in ("S", "N"):
                a0, a1 = sd["y"], sd["y"] + sd["h"]
            else:
                a0, a1 = sd["x"], sd["x"] + sd["w"]
            if not (a0 <= sd["pos"] - sd["vao"] / 2 and sd["pos"] + sd["vao"] / 2 <= a1):
                out.append(Achado("ERRO", "Vao de subdivisao extrapola a face",
                                  f"{pai_cod}/{sd['nome']}: vao de {sd['vao']} mm em "
                                  f"{sd['pos']}, face de {a0} a {a1}"))
        # sobreposicao entre subdivisoes do mesmo modulo
        for i, s1 in enumerate(lista):
            for s2 in lista[i + 1:]:
                ox = max(0, min(s1["x"] + s1["w"], s2["x"] + s2["w"]) - max(s1["x"], s2["x"]))
                oy = max(0, min(s1["y"] + s1["h"], s2["y"] + s2["h"]) - max(s1["y"], s2["y"]))
                if ox and oy:
                    out.append(Achado("ERRO", "Subdivisoes sobrepostas",
                                      f"{pai_cod}: {s1['nome']} e {s2['nome']} em "
                                      f"{ox*oy/1e6:.2f} m2"))
        # sobra de dormitorio
        resto = pai.area_mod - sum(s["w"] * s["h"] / 1e6 for s in lista)
        if resto < 9.0:
            out.append(Achado("ATENCAO", "Dormitorio pequeno",
                              f"{pai_cod}: {resto:.2f} m2 livres apos banho e closet"))
    return out


# --------------------------- 14. colisao de porta com mobiliario
def _pecas_do_pav(pav: str):
    pref = "T-" if pav == "T" else "S-"
    for p in pj.LOUCAS + pj.EQUIPAMENTOS + pj.ARMARIOS:
        if p["amb"].startswith(pref):
            yield p["cod"], p["tipo"], p["x"], p["y"], p["w"], p["h"]
    for b in pj.BANCADAS:
        if b["amb"].startswith(pref):
            yield b["cod"], "bancada", b["x"], b["y"], b["w"], b["h"]


def checar_colisao_porta() -> list[Achado]:
    """A folha de porta varre um quadrado de lado igual a sua largura."""
    out = []
    for pav in ("T", "S"):
        pecas = list(_pecas_do_pav(pav))
        for tipo, x, y, ori, p in pj.VAOS:
            if p != pav or not tipo.startswith("P") or tipo.startswith(("PG", "PV", "P05")):
                continue
            lg = pj.ESQUADRIAS[tipo][0]
            if ori == "H":
                lados = {"+Y": (x - lg / 2, y, lg, lg), "-Y": (x - lg / 2, y - lg, lg, lg)}
            else:
                lados = {"+X": (x, y - lg / 2, lg, lg), "-X": (x - lg, y - lg / 2, lg, lg)}
            bloqueado = {}
            for nome, (bx, by, bw, bh) in lados.items():
                for cod, ctipo, cx, cy, cw, ch in pecas:
                    ox = max(0, min(bx + bw, cx + cw) - max(bx, cx))
                    oy = max(0, min(by + bh, cy + ch) - max(by, cy))
                    if ox * oy / 1e6 > 0.05:
                        bloqueado.setdefault(nome, []).append(f"{cod} ({ctipo})")
            if len(bloqueado) == 2:
                out.append(Achado("ERRO", "Porta sem lado livre",
                                  f"{tipo} em ({x}, {y}): varredura obstruida dos dois lados "
                                  f"por {', '.join(sorted({v for l in bloqueado.values() for v in l}))}"))
            elif bloqueado:
                lado, itens = next(iter(bloqueado.items()))
                out.append(Achado("NOTA", "Lado de abertura definido",
                                  f"{tipo} em ({x}, {y}): abre para o lado oposto a {lado} — "
                                  f"{', '.join(itens)} ocupa a varredura"))
    return out


# ------------------------ 15. janela contra mobiliario alto
ALTURA_PECA = {"bancada": 900, "armario alto": 2_200, "prateleiras": 1_800,
               "geladeira": 1_900, "lavadora": 900, "secadora": 900,
               "box": 1_900, "tanque": 900, "vaso": 800, "lavatorio": 900}


def checar_janela_mobiliario() -> list[Achado]:
    out = []
    for pav in ("T", "S"):
        pecas = list(_pecas_do_pav(pav))
        for tipo, x, y, ori, p in pj.VAOS:
            if p != pav or not tipo.startswith("J"):
                continue
            lg, al, peit, _ = pj.ESQUADRIAS[tipo]
            if ori == "H":
                bx, by, bw, bh = x - lg / 2, y - 700, lg, 1_400
            else:
                bx, by, bw, bh = x - 700, y - lg / 2, 1_400, lg
            for cod, ctipo, cx, cy, cw, ch in pecas:
                ox = max(0, min(bx + bw, cx + cw) - max(bx, cx))
                oy = max(0, min(by + bh, cy + ch) - max(by, cy))
                if ox * oy / 1e6 <= 0.05:
                    continue
                altura = ALTURA_PECA.get(ctipo, 900)
                if altura > peit:
                    nivel = "ERRO" if altura > peit + 400 else "ATENCAO"
                    out.append(Achado(nivel, "Janela obstruida por mobiliario",
                                      f"{tipo} em ({x}, {y}) com peitoril {peit} mm contra "
                                      f"{cod} ({ctipo}) de {altura} mm de altura"))
    return out



# ---------------------------------------------- 16. areas tecnicas (TECNICOS)
PASSAGEM_MIN = 900          # NBR 9050: faixa de circulacao de uma pessoa
FRENTE_QUADRO = 700         # NBR 5410: zona livre a frente de quadro/rack
DIST_CISTERNA_ESGOTO = 3_000   # potavel x caixas de esgoto
DIST_GLP_IGNICAO = 3_000       # NBR 13523: fonte de ignicao
DIST_CONDENSADORA_VAO = 1_500   # recirculacao de ar quente pela janela
SUCCAO_BOMBA_MAX = 10_000      # limite pratico de succao da motobomba


def _ret(t):
    return (t["x"], t["y"], t["w"], t["h"])


def _folga(a, b) -> float:
    """Distancia minima em planta entre dois retangulos (0 se encostam)."""
    dx = max(a[0] - (b[0] + b[2]), b[0] - (a[0] + a[2]), 0)
    dy = max(a[1] - (b[1] + b[3]), b[1] - (a[1] + a[3]), 0)
    return math.hypot(dx, dy)


def _manhattan(a, b) -> float:
    dx = max(a[0] - (b[0] + b[2]), b[0] - (a[0] + a[2]), 0)
    dy = max(a[1] - (b[1] + b[3]), b[1] - (a[1] + a[3]), 0)
    return dx + dy


def _sobrepoe(a, b) -> float:
    ox = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    oy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    return ox * oy / 1e6


def _ret_vao(tipo, x, y, ori):
    """Retangulo (de espessura nula) ocupado por um vao no plano."""
    lg = pj.ESQUADRIAS[tipo][0]
    return (x - lg / 2, y, lg, 0) if ori == "H" else (x, y - lg / 2, 0, lg)


def checar_tecnicos() -> list[Achado]:
    """Auditoria das areas tecnicas: existencia, lugar, folga e distancia.

    Enquanto a bomba, o nicho de condensadoras e a central de GLP nao estavam
    no modelo, nada disso podia ser verificado — e o projeto passava limpo com
    um buraco de coordenacao. Este bloco fecha esse buraco.
    """
    out = []
    tecs = pj.TECNICOS
    amb_por_cod = {a.cod: a for a in pj.TERREO + pj.SUPERIOR}

    # 16.1 dentro do lote e em ajuste fino de 100 mm
    for t in tecs:
        x, y, w, h = _ret(t)
        if x < 0 or y < 0 or x + w > pj.LOTE_L or y + h > pj.LOTE_P:
            out.append(Achado("ERRO", "Area tecnica fora do lote",
                              f"{t['cod']} {t['nome']} em ({x}, {y})"))
        for nome, v in (("x", x), ("y", y), ("largura", w), ("profundidade", h)):
            if v % 100:
                out.append(Achado("NOTA", "Area tecnica fora do ajuste fino",
                                  f"{t['cod']}: {nome} = {v} mm nao e multiplo de 100"))

    # 16.2 nao podem se sobrepor entre si
    for i, a in enumerate(tecs):
        for b in tecs[i + 1:]:
            if a.get("zona") == "INT" or b.get("zona") == "INT":
                continue
            if _sobrepoe(_ret(a), _ret(b)) > 0:
                out.append(Achado("ERRO", "Areas tecnicas sobrepostas",
                                  f"{a['cod']} x {b['cod']}"))

    # 16.3 zona INT: dentro do ambiente declarado, encostado em parede,
    #      e com a zona livre de manutencao a frente
    pecas_t = list(_pecas_do_pav("T")) + list(_pecas_do_pav("S"))
    for t in tecs:
        if t.get("zona") != "INT":
            continue
        amb = amb_por_cod.get(t.get("amb", ""))
        if amb is None:
            out.append(Achado("ERRO", "Area tecnica sem ambiente",
                              f"{t['cod']} declara zona INT e ambiente "
                              f"{t.get('amb', '-')}, que nao existe"))
            continue
        x, y, w, h = _ret(t)
        if not (amb.x <= x and x + w <= amb.x + amb.w
                and amb.y <= y and y + h <= amb.y + amb.h):
            out.append(Achado("ERRO", "Area tecnica fora do ambiente",
                              f"{t['cod']} em ({x}, {y}) nao cabe em {amb.cod}"))
            continue
        encostado = min(abs(x - amb.x), abs(amb.x + amb.w - (x + w)),
                        abs(y - amb.y), abs(amb.y + amb.h - (y + h)))
        if encostado > 100:
            out.append(Achado("ATENCAO", "Quadro solto no ambiente",
                              f"{t['cod']} esta a {encostado} mm da parede mais "
                              f"proxima de {amb.cod}: precisa de parede de apoio"))
        # zona livre de manutencao, projetada para o interior do ambiente
        if abs(x - amb.x) <= 100:
            zl = (x + w, y, FRENTE_QUADRO, h)
        elif abs(amb.x + amb.w - (x + w)) <= 100:
            zl = (x - FRENTE_QUADRO, y, FRENTE_QUADRO, h)
        elif abs(y - amb.y) <= 100:
            zl = (x, y + h, w, FRENTE_QUADRO)
        else:
            zl = (x, y - FRENTE_QUADRO, w, FRENTE_QUADRO)
        for cod, ctipo, cx, cy, cw, ch in pecas_t:
            if _sobrepoe(zl, (cx, cy, cw, ch)) > 0.02:
                out.append(Achado("ERRO", "Quadro sem zona de manutencao",
                                  f"{t['cod']}: os {FRENTE_QUADRO} mm livres a frente "
                                  f"estao ocupados por {cod} ({ctipo})",
                                  "NBR 5410 6.5.4"))

    # 16.4 zonas externas: nao invadir ambiente coberto, salvo se enterrada
    fechados = [(a.cod, a.x, a.y, a.w, a.h) for a in pj.cobertos()]
    for t in tecs:
        if t.get("zona") == "INT":
            continue
        sob_solo = t.get("prof") and (t.get("zona") == "ENT")
        for cod, ax, ay, aw, ah in fechados:
            ov = _sobrepoe(_ret(t), (ax, ay, aw, ah))
            if ov <= 0:
                continue
            if sob_solo:
                out.append(Achado("NOTA", "Area tecnica sob area coberta",
                                  f"{t['cod']} enterrada sob {cod} ({ov:.2f} m2) — "
                                  f"prever acesso de inspecao"))
            else:
                out.append(Achado("ERRO", "Area tecnica invadindo ambiente",
                                  f"{t['cod']} sobrepoe {cod} em {ov:.2f} m2"))

    # 16.5 passagem livre na faixa tecnica e no recuo sul
    faixas = {"FT-N": (pj.FAIXA_TECNICA["x"], pj.FAIXA_TECNICA["x"] + pj.FAIXA_TECNICA["w"]),
              "TEST": (pj.FAIXA_TECNICA["x"], pj.FAIXA_TECNICA["x"] + pj.FAIXA_TECNICA["w"]),
              "REC-S": (0, pj.RECUO_ESQ)}
    for t in tecs:
        lim = faixas.get(t.get("zona", ""))
        if not lim:
            continue
        x, _, w, _ = _ret(t)
        livre = max(x - lim[0], lim[1] - (x + w))
        if livre < PASSAGEM_MIN:
            out.append(Achado("ERRO", "Passagem tecnica obstruida",
                              f"{t['cod']} deixa apenas {livre:.0f} mm livres na "
                              f"faixa {t['zona']} (min {PASSAGEM_MIN} mm)",
                              "NBR 9050 6.11"))

    # 16.6 climatizacao: carga, capacidade, linha frigorigena e nicho
    grupos = {frozenset(g) for g in grupos_integrados("T")}
    for c in pj.CLIMATIZACAO:
        amb = amb_por_cod.get(c["amb"])
        nicho = next((t for t in tecs if t["cod"] == c["nicho"]), None)
        if amb is None or nicho is None:
            out.append(Achado("ERRO", "Climatizacao sem referencia",
                              f"{c['amb']} / {c['nicho']}"))
            continue
        carga = pj.carga_termica(c["amb"], c["pessoas"], c["equip"], c.get("mais"),
                                 c.get("conta_ventilador", False),
                                 c.get("duto", False),
                                 c.get("area_m2"), c.get("vidro_m2"))
        if c.get("conta_ventilador") and c["amb"] not in {v["amb"] for v in pj.VENTILADORES}:
            out.append(Achado("ERRO", "Desconto de ventilador sem ventilador",
                              f"{c['amb']}: a carga foi reduzida por "
                              f"FATOR_VENTILADOR e nao ha pa declarada no ambiente"))
        minimo = pj.capacidade_comercial(carga)
        if c["capacidade"] < carga:
            out.append(Achado("ERRO", "Evaporadora subdimensionada",
                              f"{c['amb']}: {c['capacidade']} BTU/h para carga de "
                              f"{carga} BTU/h (minimo comercial {minimo})"))
        elif c["capacidade"] > minimo:
            out.append(Achado("ATENCAO", "Evaporadora superdimensionada",
                              f"{c['amb']}: {c['capacidade']} BTU/h contra {minimo} "
                              f"suficiente — em Manaus (UR 80 %) o equipamento grande "
                              f"liga e desliga e deixa de desumidificar"))
        subida = (pj.PISO_A_PISO + 600) if amb.pav == "S" else pj.PE_DIREITO
        comp = _manhattan(_ret(nicho), (amb.x, amb.y, amb.w, amb.h)) + subida + 1_500
        if comp > pj.LINHA_FRIG_LIMITE:
            out.append(Achado("ERRO", "Linha frigorigena longa demais",
                              f"{nicho['cod']} -> {c['amb']}: {comp/1000:.1f} m "
                              f"(limite {pj.LINHA_FRIG_LIMITE/1000:.0f} m)"))
        elif comp > pj.LINHA_FRIG_MAX:
            out.append(Achado("ATENCAO", "Linha frigorigena acima do conforto",
                              f"{nicho['cod']} -> {c['amb']}: {comp/1000:.1f} m "
                              f"(acima de {pj.LINHA_FRIG_MAX/1000:.0f} m exige carga "
                              f"extra de refrigerante e perde rendimento)"))
        # volume aberto: so e aceitavel com fronteira climatica declarada
        if not c.get("reserva"):
            for g in grupos:
                if c["amb"] not in g:
                    continue
                fora = sorted(g - {c["amb"]} - set(c.get("mais", []))
                              - set(c.get("zona_aberta", [])))
                if fora:
                    out.append(Achado(
                        "ATENCAO", "Evaporadora em volume aberto",
                        f"{c['amb']} e integrado a {', '.join(fora)} sem parede e "
                        f"sem fronteira declarada: a carga real e a do volume inteiro"))
    # 16.7 nicho: comprimento suficiente para as condensadoras alocadas
    for t in tecs:
        alocadas = pj.nicho_de(t["cod"])
        if not alocadas:
            continue
        need = 0
        for c in alocadas:
            need += next(l for lim, l in pj.LARGURA_NICHO if c["capacidade"] <= lim)
        disp = max(t["w"], t["h"])
        if disp < need:
            out.append(Achado("ERRO", "Nicho de condensadoras curto",
                              f"{t['cod']}: {disp} mm para {len(alocadas)} posicoes "
                              f"que somam {need} mm"))
        # descarga de ar quente longe de vao de ambiente
        for tipo, x, y, ori, pav in pj.VAOS:
            if not (tipo.startswith("J") or tipo.startswith("PV")):
                continue
            d = _folga(_ret(t), _ret_vao(tipo, x, y, ori))
            if d < DIST_CONDENSADORA_VAO:
                out.append(Achado("ATENCAO", "Condensadora perto de vao",
                                  f"{t['cod']} a {d:.0f} mm de {tipo} em ({x}, {y}): "
                                  f"ar de descarga a 45 graus entra pela janela "
                                  f"(min {DIST_CONDENSADORA_VAO} mm)"))

    # 16.8 GLP: afastamento de vaos e de fonte de ignicao (NBR 13523)
    glp = [t for t in tecs if "GLP" in t["nome"]]
    for g in glp:
        for tipo, x, y, ori, pav in pj.VAOS:
            d = _folga(_ret(g), _ret_vao(tipo, x, y, ori))
            if d < pj.GLP_DIST_VAO:
                out.append(Achado("ERRO", "Central de GLP perto de vao",
                                  f"{g['cod']} a {d:.0f} mm de {tipo} em ({x}, {y}) — "
                                  f"min {pj.GLP_DIST_VAO} mm", "NBR 13523"))
        for b in pj.BANCADAS:
            if not (b.get("cooktop") or b.get("ignicao")):
                continue
            d = _folga(_ret(g), (b["x"], b["y"], b["w"], b["h"]))
            if d < DIST_GLP_IGNICAO:
                out.append(Achado("ERRO", "Central de GLP perto de ignicao",
                                  f"{g['cod']} a {d:.0f} mm de {b['cod']} (cooktop) — "
                                  f"min {DIST_GLP_IGNICAO} mm", "NBR 13523"))
        if pj.LOTE_L - (g["x"] + g["w"]) < pj.GLP_DIST_VAO:
            out.append(Achado("ATENCAO", "Central de GLP junto a divisa",
                              f"{g['cod']} a {pj.LOTE_L - (g['x'] + g['w'])} mm da divisa norte"))

    # 16.9 cisterna potavel afastada das caixas de esgoto
    potavel = [t for t in tecs if "Cisterna" in t["nome"]]
    esgoto = [t for t in tecs if "Caixa" in t["nome"]]
    for p in potavel:
        for e in esgoto:
            d = _folga(_ret(p), _ret(e))
            if d < DIST_CISTERNA_ESGOTO:
                out.append(Achado("ERRO", "Cisterna perto de caixa de esgoto",
                                  f"{p['cod']} a {d:.0f} mm de {e['cod']} — "
                                  f"min {DIST_CISTERNA_ESGOTO} mm"))

    # 16.10 casa de maquinas da piscina: succao curta e coerente com o modelo
    cm = [t for t in tecs if t.get("casa_maquinas")]
    pisc = (pj.PISCINA["x"], pj.PISCINA["y"], pj.PISCINA["w"], pj.PISCINA["h"])
    for c in cm:
        d = _folga(_ret(c), pisc)
        if d > SUCCAO_BOMBA_MAX:
            out.append(Achado("ERRO", "Casa de maquinas distante da piscina",
                              f"{c['cod']} a {d:.0f} mm (max {SUCCAO_BOMBA_MAX} mm de succao)"))
        if _ret(c) != (pj.CASA_MAQUINAS["x"], pj.CASA_MAQUINAS["y"],
                       pj.CASA_MAQUINAS["w"], pj.CASA_MAQUINAS["h"]):
            out.append(Achado("ERRO", "Casa de maquinas em duas posicoes",
                              f"{c['cod']} divergente de CASA_MAQUINAS"))

    # 16.11 medidores acessiveis da via publica
    med = [t for t in tecs if "Medidores" in t["nome"]]
    for m in med:
        if m["y"] + m["h"] > 1_500:
            out.append(Achado("ATENCAO", "Medidores longe da testada",
                              f"{m['cod']} a {m['y']} mm da divisa frontal: a leitura "
                              f"deixa de ser feita pela via"))

    # 16.12 a motobomba precisa da cisterna por perto
    bomba = [t for t in tecs if "Motobomba" in t["nome"]]
    for b in bomba:
        if potavel and _folga(_ret(b), _ret(potavel[0])) > 3_000:
            out.append(Achado("ATENCAO", "Motobomba longe da cisterna",
                              f"{b['cod']} a {_folga(_ret(b), _ret(potavel[0])):.0f} mm "
                              f"da {potavel[0]['cod']}: succao longa cavita"))
    return out


# ------------------------- 17. projecao do pavimento superior
def _sup_de(cod: str):
    return next(a for a in pj.SUPERIOR + pj.SUPERIOR_ABERTO if a.cod == cod)


def checar_projecao_superior() -> list[Achado]:
    """Todo trecho do superior precisa de apoio e cobre o que esta embaixo.

    Duas perguntas distintas: (a) o trecho esta sobre ambiente fechado, sobre
    apoio declarado (pilar/viga) ou em balanco nao declarado? (b) a area aberta
    sob ele esta marcada como coberta? A segunda e o que alimenta a taxa de
    ocupacao — e foi exatamente onde o modelo estava errado.
    """
    out = []
    passo = 300
    ter = [(a.cod, a.x, a.y, a.w, a.h, a.aberto, a.coberto)
           for a in pj.TERREO + pj.TERREO_ABERTO]
    apoios = [(p["x"], p["y"]) for p in pj.PILARES]
    sobre = defaultdict(float)
    vazio = 0.0
    for a in pj.SUPERIOR + pj.SUPERIOR_ABERTO:
        for i in range(a.x, a.x + a.w, passo):
            for j in range(a.y, a.y + a.h, passo):
                alvo = None
                for cod, x, y, w, h, ab, cb in ter:
                    if x <= i < x + w and y <= j < y + h:
                        alvo = (cod, ab, cb)
                        break
                if alvo is None:
                    vazio += passo * passo / 1e6
                elif alvo[1]:
                    sobre[(a.cod, alvo[0], alvo[2])] += passo * passo / 1e6
    if vazio > 0.09:
        out.append(Achado("ERRO", "Superior sobre o vazio",
                          f"{vazio:.2f} m2 do pavimento superior nao tem nada "
                          f"abaixo, nem ambiente nem area aberta declarada"))
    for (sup, inf, marcado), area in sorted(sobre.items()):
        if marcado:
            continue
        # area aberta coberta pela laje do superior e nao declarada coberta
        out.append(Achado("ATENCAO", "Area aberta coberta sem declaracao",
                          f"{sup} cobre {area:.2f} m2 de {inf}, que nao esta "
                          f"marcado como coberto: a taxa de ocupacao conta essa "
                          f"projecao de qualquer modo"))
    # apoio: cada area aberta coberta pelo superior precisa de pilar ou viga
    vigados = {v["sobre"] for v in pj.VIGAS}
    for (sup, inf, _), area in sorted(sobre.items()):
        if inf in vigados:
            continue
        alvo = next((a for a in pj.TERREO_ABERTO if a.cod == inf), None)
        if alvo is None:
            continue
        # pilar dentro da area aberta ou na borda dela (tolerancia de 300 mm)
        tem_apoio = any(alvo.x - 300 <= px <= alvo.x + alvo.w + 300
                        and alvo.y - 300 <= py <= alvo.y + alvo.h + 300
                        for px, py in apoios)
        if tem_apoio:
            continue
        # balanco curto resolve-se no proprio vigamento; so o longo exige apoio
        ox = max(0, min(alvo.x + alvo.w, _sup_de(sup).x + _sup_de(sup).w)
                 - max(alvo.x, _sup_de(sup).x))
        oy = max(0, min(alvo.y + alvo.h, _sup_de(sup).y + _sup_de(sup).h)
                 - max(alvo.y, _sup_de(sup).y))
        if min(ox, oy) <= pj.BALANCO_MAX_LSF:
            out.append(Achado("NOTA", "Balanco curto sobre area aberta",
                              f"{sup} avanca {min(ox, oy)} mm sobre {inf} "
                              f"({area:.2f} m2): dentro do limite de "
                              f"{pj.BALANCO_MAX_LSF} mm do vigamento de LSF"))
            continue
        out.append(Achado("ATENCAO", "Trecho do superior sem apoio declarado",
                          f"{sup} avanca {area:.2f} m2 sobre {inf} sem pilar nem "
                          f"viga declarada: confirmar balanco e perfil de borda"))
    return out



# ------------------------- 18. fronteira climatica e movimentacao de ar
ALTURA_LIVRE_MIN = 2_100      # altura livre sob rebaixo de forro
REBAIXO_MIN = 200             # abaixo disso o rebaixo nao retem a camada fria
VAZAO_POR_1000BTU = 50        # m3/h por 1.000 BTU/h em split duto
TOLERANCIA_VAZAO = 0.15
VEL_AR_ALVO = 0.8             # m/s na zona de permanencia (NBR 16401-2)


def checar_fronteira_climatica() -> list[Achado]:
    """A fita social e climatizada sem parede: a fronteira tem de existir.

    Nao basta escrever 'ambiente integrado climatizado'. Cada medida da
    FRONTEIRA_CLIMATICA e verificavel: o rebaixo esta na linha certa, o
    insuflamento esta longe dela, o retorno esta junto dela, o lado quente tem
    ventilador e a exaustao existe para manter a depressao.
    """
    out = []
    fr = pj.FRONTEIRA_CLIMATICA
    amb_por_cod = {a.cod: a for a in pj.TERREO + pj.SUPERIOR}
    ventilados = {v["amb"] for v in pj.VENTILADORES}
    exauridos = {e["amb"] for e in pj.EXAUSTAO}

    ativos = [c for c in pj.CLIMATIZACAO
              if not c.get("reserva") and c.get("zona_aberta")]
    for c in ativos:
        a, b = fr["entre"]
        if c["amb"] not in fr["entre"]:
            out.append(Achado("ERRO", "Fronteira climatica ausente",
                              f"{c['amb']} climatiza volume aberto para "
                              f"{', '.join(c['zona_aberta'])} e nao aparece em "
                              f"FRONTEIRA_CLIMATICA"))
            continue
        if fr["rebaixo"] < REBAIXO_MIN:
            out.append(Achado("ERRO", "Rebaixo de forro insuficiente",
                              f"{fr['rebaixo']} mm nao retem a camada fria "
                              f"(min {REBAIXO_MIN} mm)"))
        if fr["altura_livre"] < ALTURA_LIVRE_MIN:
            out.append(Achado("ERRO", "Altura livre sob o rebaixo",
                              f"{fr['altura_livre']} mm sob a fronteira "
                              f"(min {ALTURA_LIVRE_MIN} mm)"))
        # a linha da fronteira deve coincidir com o contato real dos ambientes
        ra, rb = amb_por_cod.get(a), amb_por_cod.get(b)
        if ra and rb:
            contato = (abs(ra.y + ra.h - rb.y) <= 1 or abs(rb.y + rb.h - ra.y) <= 1
                       or abs(ra.x + ra.w - rb.x) <= 1 or abs(rb.x + rb.w - ra.x) <= 1)
            if not contato:
                out.append(Achado("ERRO", "Fronteira fora do contato",
                                  f"{a} e {b} nao se encostam: a linha declarada "
                                  f"em ({fr['x']}, {fr['y']}) nao existe"))
        # lado quente: ventilador e exaustao
        for z in c["zona_aberta"]:
            if z not in ventilados:
                out.append(Achado("ERRO", "Lado quente sem ventilador",
                                  f"{z} fica fora da zona climatizada e nao tem "
                                  f"ventilador: sem {VEL_AR_ALVO} m/s o gradiente "
                                  f"de 3 C deixa de ser confortavel"))
        if not (set(c["zona_aberta"]) & exauridos):
            out.append(Achado("ERRO", "Fronteira sem depressao",
                              f"nenhum ambiente de {', '.join(c['zona_aberta'])} tem "
                              f"exaustao: sem depressao o fluxo se inverte e o ar "
                              f"quente volta para a zona fria"))

    # difusores: dentro do ambiente, vazao coerente e geometria da fronteira
    if ativos:
        cap = sum(c["capacidade"] for c in ativos)
        ins = sum(d["vazao_m3h"] for d in pj.DIFUSORES if d["tipo"] == "insuflamento")
        ret = sum(d["vazao_m3h"] for d in pj.DIFUSORES if d["tipo"] == "retorno")
        alvo = cap / 1_000 * VAZAO_POR_1000BTU
        if abs(ins - alvo) > alvo * TOLERANCIA_VAZAO:
            out.append(Achado("ATENCAO", "Vazao de insuflamento fora da faixa",
                              f"{ins} m3/h para {cap} BTU/h (esperado "
                              f"{alvo:.0f} +/- {TOLERANCIA_VAZAO*100:.0f} %)"))
        if ret < ins * 0.95:
            out.append(Achado("ERRO", "Retorno menor que o insuflamento",
                              f"retorno {ret} m3/h contra insuflamento {ins} m3/h: "
                              f"a zona pressuriza e empurra o ar frio para fora"))
        eixo_fr = fr["y"] if fr["eixo"] == "H" else fr["x"]
        d_ins, d_ret = [], []
        for d in pj.DIFUSORES:
            amb = amb_por_cod.get(d["amb"])
            if amb is None or not (amb.x <= d["x"] and d["x"] + d["w"] <= amb.x + amb.w
                                   and amb.y <= d["y"] and d["y"] + d["h"] <= amb.y + amb.h):
                out.append(Achado("ERRO", "Difusor fora do ambiente",
                                  f"{d['cod']} em ({d['x']}, {d['y']}) nao cabe em "
                                  f"{d['amb']}"))
                continue
            pos = d["y"] if fr["eixo"] == "H" else d["x"]
            (d_ins if d["tipo"] == "insuflamento" else d_ret).append(
                (abs(pos - eixo_fr), d["cod"]))
        if d_ins and d_ret and min(x for x, _ in d_ins) <= max(x for x, _ in d_ret):
            out.append(Achado("ERRO", "Insuflamento e retorno invertidos",
                              "o insuflamento precisa ficar LONGE da fronteira e o "
                              "retorno JUNTO a ela, para a circulacao puxar o ar "
                              "para dentro da zona fria"))
        ev = pj.EVAPORADORA_DUTO
        amb = amb_por_cod.get(ev["amb"])
        if amb and not (amb.x <= ev["x"] and ev["x"] + ev["w"] <= amb.x + amb.w
                        and amb.y <= ev["y"] and ev["y"] + ev["h"] <= amb.y + amb.h):
            out.append(Achado("ERRO", "Evaporadora de duto fora do ambiente",
                              f"{ev['amb']} em ({ev['x']}, {ev['y']})"))
        if ev["altura"] > pj.PISO_A_PISO - pj.PE_DIREITO:
            out.append(Achado("ERRO", "Evaporadora nao cabe no entreforro",
                              f"{ev['altura']} mm de equipamento em "
                              f"{pj.PISO_A_PISO - pj.PE_DIREITO} mm de entreforro"))

    # ventiladores: pa a 2.300 mm do piso e folga de 500 mm ate a parede
    for v in pj.VENTILADORES:
        amb = (amb_por_cod.get(v["amb"])
               or next((a for a in pj.TERREO_ABERTO if a.cod == v["amb"]), None))
        if amb is None:
            out.append(Achado("ERRO", "Ventilador sem ambiente", v["cod"]))
            continue
        menor = min(amb.w, amb.h)
        if menor < v["diam"] + 1_000:
            out.append(Achado("ATENCAO", "Ventilador grande para o ambiente",
                              f"{v['cod']} de {v['diam']} mm em {amb.cod} de "
                              f"{menor} mm de menor dimensao (min 500 mm de folga "
                              f"por lado)"))
        if v["qtd"] > 1 and amb.area_mod / v["qtd"] < 12:
            out.append(Achado("NOTA", "Ventiladores adensados",
                              f"{v['cod']}: {v['qtd']} pas em {amb.area_mod:.2f} m2"))

    # exaustao mecanica obrigatoria em molhado sem janela
    com_janela = set()
    for tipo, x, y, ori, pav in pj.VAOS:
        if not tipo.startswith("J"):
            continue
        for a in pj.TERREO + pj.SUPERIOR:
            if a.pav != pav:
                continue
            if (a.x - 200 <= x <= a.x + a.w + 200 and a.y - 200 <= y <= a.y + a.h + 200):
                com_janela.add(a.cod)
    for cod in sorted(ep.MOLHADOS):
        if cod in com_janela or cod in exauridos:
            continue
        out.append(Achado("ATENCAO", "Molhado sem janela nem exaustao",
                          f"{cod} nao tem vao de ventilacao nem exaustao mecanica"))
    return out



# ------------------------- 19. estrutura: flecha, tensao e junta deslizante
USO_MAX_PERFIL = 0.85        # fracao da resistencia admitida no pre-dimensionamento


def checar_estrutura() -> list[Achado]:
    """Cada viga resolvida pela flecha, com junta de deslizamento onde ha gesso.

    O perfil laminado flete; a chapa de gesso acima fissura. Duas medidas
    independentes: limite L/500 e slip track com folga de 1,5 x flecha. Uma sem
    a outra apenas atrasa a fissura.
    """
    out = []
    abertos = {a.cod: a for a in pj.TERREO_ABERTO}
    for v in pj.dimensionar_vigas():
        lim_vao = v.get("vao_max", pj.VAO_MAX_VIGA)
        if v["vao"] > lim_vao:
            out.append(Achado("ERRO", "Vao de viga acima do limite",
                              f"{v['cod']}: {v['vao']} mm (max {lim_vao} mm "
                              f"sem apoio intermediario)"))
        elif v["vao"] > pj.VAO_MAX_VIGA:
            out.append(Achado("NOTA", "Vao acima do padrao do projeto",
                              f"{v['cod']}: {v['vao']} mm contra {pj.VAO_MAX_VIGA} mm "
                              f"de padrao — excecao declarada: {v['desc'][:60]}"))
        if v["sobre"] not in abertos and v["sobre"] not in {a.cod for a in pj.TERREO}:
            out.append(Achado("ERRO", "Viga sobre ambiente inexistente",
                              f"{v['cod']} -> {v['sobre']}"))
        if v["flecha"] > v["flecha_adm"]:
            out.append(Achado("ERRO", "Flecha acima do limite",
                              f"{v['cod']} {v['perfil']}: {v['flecha']} mm contra "
                              f"{v['flecha_adm']} mm (L/{v['limite']})"))
        if v["uso"] > USO_MAX_PERFIL * 100:
            out.append(Achado("ERRO", "Perfil no limite da resistencia",
                              f"{v['cod']} {v['perfil']}: {v['tensao']} MPa = "
                              f"{v['uso']} % de {v['tensao_adm']} MPa"))
        if v["vedacao"] and not v["slip_exec"]:
            out.append(Achado("ERRO", "Vedacao fragil sem junta deslizante",
                              f"{v['cod']} sustenta parede de LSF e nao tem slip track"))
        if v["vedacao"] and v["slip_exec"] < v["slip"]:
            out.append(Achado("ERRO", "Folga de slip insuficiente",
                              f"{v['cod']}: {v['slip_exec']} mm contra {v['slip']} mm "
                              f"necessarios (1,5 x flecha)"))
        livre = pj.PE_DIREITO - pj.PERFIS_LAMINADOS[v["perfil"]]["h"]
        if livre < ALTURA_LIVRE_MIN:
            out.append(Achado("ERRO", "Altura livre sob viga",
                              f"{v['cod']} {v['perfil']}: {livre} mm sob a viga "
                              f"(min {ALTURA_LIVRE_MIN} mm)"))
    # a caixa d'agua precisa cair sobre parede, nao sobre vazio
    cd = pj.CAIXA_DAGUA
    apoio = 0.0
    for a in pj.SUPERIOR:
        ox = max(0, min(cd["x"] + cd["w"], a.x + a.w) - max(cd["x"], a.x))
        oy = max(0, min(cd["y"] + cd["h"], a.y + a.h) - max(cd["y"], a.y))
        apoio += ox * oy / 1e6
    area = cd["w"] * cd["h"] / 1e6
    if apoio < area * 0.999:
        out.append(Achado("ERRO", "Caixa d'agua sobre vazio",
                          f"{area - apoio:.2f} m2 da caixa de {cd['carga_kg']} kg nao "
                          f"tem ambiente fechado abaixo: exigiria plataforma vencendo "
                          f"o poco"))
    # pressao disponivel em cada pavimento
    for pav, nome in (("T", "terreo"), ("S", "superior")):
        mca = pj.carga_hidraulica_mca(pav)
        pressurizado = pav == "S" and pj.PRESSURIZADOR["atende"]
        if mca < 2.0 and not pressurizado:
            out.append(Achado("ERRO", "Pressao insuficiente sem pressurizador",
                              f"{nome}: {mca} mca no chuveiro (min 2,0 mca para "
                              f"chuveiro eletrico)"))
        elif mca < 2.0:
            out.append(Achado("NOTA", "Pavimento pressurizado",
                              f"{nome}: {mca} mca por gravidade — atendido pelo "
                              f"{pj.PRESSURIZADOR['cod']} de "
                              f"{pj.PRESSURIZADOR['potencia_cv']} cv"))
    return out


# ------------------------- 20. penetracoes e furacao em LSF
def checar_penetracoes() -> list[Achado]:
    """Tubo maior que o furo admissivel nao passa em montante. Nunca."""
    out = []
    fmax = pj.furo_max("Ue90x40x0.95")
    fmax_ext = pj.furo_max("Ue140x40x0.95")
    for p in pj.PENETRACOES:
        if p["onde"] == "montante":
            lim = fmax_ext if "externa" in p.get("solucao", "") else fmax
            if p["dn"] > lim:
                out.append(Achado("ERRO", "Tubo maior que o furo admissivel",
                                  f"{p['cod']} {p['tipo']} DN{p['dn']} em montante "
                                  f"de furo maximo {lim} mm: exige shaft ou "
                                  f"entreforro", "NBR 15253"))
        elif p["onde"] == "entreforro":
            if p["dn"] + 100 > pj.ENTREFORRO:
                out.append(Achado("ERRO", "Duto nao cabe no entreforro",
                                  f"{p['cod']} DN{p['dn']} mais 100 mm de suporte em "
                                  f"{pj.ENTREFORRO} mm de entreforro"))
        elif p["onde"] == "shaft":
            if p["dn"] + 100 > pj.SHAFT["w"]:
                out.append(Achado("ERRO", "Shaft estreito",
                                  f"{p['cod']} DN{p['dn']} em shaft de "
                                  f"{pj.SHAFT['w']} mm"))
    # todo esgoto vertical precisa de shaft declarado
    esgotos = [p for p in pj.PENETRACOES if "esgoto" in p["tipo"]]
    for e in esgotos:
        if "shaft" not in e["solucao"]:
            out.append(Achado("ERRO", "Esgoto vertical sem shaft",
                              f"{e['cod']} {e['tipo']}"))
    if pj.FURACAO["dist_centros"] < pj.MONTANTE_ESPACAMENTO:
        out.append(Achado("ATENCAO", "Furos adensados",
                          f"{pj.FURACAO['dist_centros']} mm entre centros com "
                          f"montante a cada {pj.MONTANTE_ESPACAMENTO} mm"))
    return out


# ------------------------- 21. paginacao de piso e revestimento
def checar_paginacao() -> list[Achado]:
    """Recorte pequeno sempre aparece; e junta desalinhada em sala integrada
    aparece no pior lugar possivel, no meio do ambiente, sem parede para
    disfarcar."""
    out = []
    cobertos = {c for z in pj.ZONAS_PAGINACAO for c in z["ambientes"]}
    for z in pj.ZONAS_PAGINACAO:
        peca = pj.PECA_PISO if z["peca"] == "piso" else pj.PECA_PAREDE
        for cod in z["ambientes"]:
            sub = "/" in cod and any(
                f"{d['pai']}/{d['nome']}" == cod for d in pj.SUBDIVISOES)
            if not sub and not any(a.cod == cod
                                   for a in pj.TERREO + pj.SUPERIOR):
                out.append(Achado("ERRO", "Paginacao sem ambiente",
                                  f"{z['cod']} -> {cod}"))
                continue
            res = pj.paginar(cod)
            if not res:
                continue
            alt = res.get("altura")
            if alt and not alt["ok"]:
                out.append(Achado("ERRO", "Fiada do topo recortada",
                                  f"{cod}: revestimento de {alt['altura']} mm deixa "
                                  f"fiada de topo com {alt['fiada_topo']} mm de "
                                  f"{peca['c']} mm — e a fiada na altura dos olhos"))
            for eixo in ("x", "y"):
                r = res[eixo]
                if r["critico"]:
                    out.append(Achado("ERRO", "Recorte critico de peca",
                                      f"{cod} eixo {eixo}: {r['pior']} mm de uma peca "
                                      f"de {peca['l']} mm — abaixo de 1/5 o recorte "
                                      f"descola"))
                elif not r["ok"]:
                    out.append(Achado("NOTA", "Recorte de peca abaixo de 1/3",
                                      f"{cod} eixo {eixo}: {r['pior']} mm (1/3 seria "
                                      f"{int(peca['l']*pj.RECORTE_MIN)} mm) — aceito, "
                                      f"o recorte cai em {z['obs'][:40]}"))
    # todo ambiente com piso ceramico precisa de zona; integrados na MESMA zona
    for g in pj.INTEGRADOS:
        zonas = {pj.zona_de(c)["cod"] for c in g if pj.zona_de(c)}
        if len(zonas) > 1:
            out.append(Achado("ERRO", "Integrados em zonas de paginacao diferentes",
                              f"{' + '.join(sorted(g))}: {', '.join(sorted(zonas))} — "
                              f"sem parede entre eles a costura fica visivel"))
    faltam = [a.cod for a in pj.TERREO + pj.SUPERIOR if a.cod not in cobertos]
    if faltam:
        out.append(Achado("NOTA", "Ambientes sem paginacao declarada",
                          f"{len(faltam)}: {', '.join(faltam)} — recebem a malha "
                          f"padrao a partir do proprio canto de entrada"))
    return out


# ------------------------- 22. altura livre (verificacao em 3 dimensoes)
def _teto_sobre(x: float, y: float) -> float:
    """Cota do teto acima de um ponto em planta do terreo."""
    for a in pj.SUPERIOR + pj.SUPERIOR_ABERTO:
        if a.x <= x < a.x + a.w and a.y <= y < a.y + a.h:
            return float(pj.PISO_A_PISO)
    return float(pj.PISO_A_PISO + pj.PE_DIREITO)     # pe-direito duplo / cobertura


def checar_altura_livre() -> list[Achado]:
    """Primeira verificacao que sai da planta: cada degrau contra o que ha acima.

    Nenhuma verificacao anterior era tridimensional — e altura livre de escada e
    justamente o defeito que nao aparece em planta nenhuma.
    """
    out = []
    passo = 150
    for l in pj.escada_lances():
        n = max(1, l["espelhos"])
        for i in range(int(l["h"] // passo) + 1):
            dy = i * passo
            frac = dy / l["h"] if l["h"] else 0
            if l["sentido"] == "-Y":
                frac = 1 - frac
            z = l["z_ini"] + (l["z_fim"] - l["z_ini"]) * frac
            y = l["y"] + dy
            for dx in (0, l["w"] / 2, l["w"]):
                teto = _teto_sobre(l["x"] + dx, y)
                livre = teto - z
                # o ultimo degrau ENCOSTA no piso do pavimento de cima: ali nao
                # existe altura livre a verificar, existe chegada
                if abs(z - pj.PISO_A_PISO) < 1 or abs(teto - z) < 1:
                    continue
                if livre < pj.ESCADA_EXEC["altura_livre_min"]:
                    out.append(Achado("ERRO", "Altura livre na escada",
                                      f"{l['cod']} em ({l['x']+dx:.0f}, {y:.0f}): "
                                      f"{livre:.0f} mm entre o degrau na cota "
                                      f"{z:.0f} e o teto em {teto:.0f} (min "
                                      f"{pj.ESCADA_EXEC['altura_livre_min']} mm)",
                                      "NBR 9077"))
                    break
    # armario sob escada: onde a altura livre nao serve para circular
    for ar in pj.ARMARIOS:
        if not ar.get("sob_escada"):
            continue
        l2 = next(l for l in pj.escada_lances() if l["cod"] == "L2")
        alturas = []
        for i in range(0, int(ar["h"]), 150):
            y = ar["y"] + i
            frac = 1 - (y - l2["y"]) / l2["h"]
            z = l2["z_ini"] + (l2["z_fim"] - l2["z_ini"]) * max(0.0, min(1.0, frac))
            alturas.append(z)
        if max(alturas) - min(alturas) < 300:
            out.append(Achado("NOTA", "Armario sob escada em trecho uniforme",
                              f"{ar['cod']}: rampa de apenas "
                              f"{max(alturas)-min(alturas):.0f} mm"))
        elif min(alturas) < 600:
            out.append(Achado("NOTA", "Armario sob escada com ponta baixa",
                              f"{ar['cod']}: altura util de {min(alturas):.0f} a "
                              f"{max(alturas):.0f} mm — prever prateleira fixa, nao "
                              f"porta de altura inteira"))
    # pe-direito duplo declarado tem de existir de fato
    for cod in pj.PE_DIREITO_DUPLO:
        amb = next((a for a in pj.TERREO if a.cod == cod), None)
        if amb is None:
            out.append(Achado("ERRO", "Pe-direito duplo em ambiente inexistente", cod))
            continue
        vazio = 0.0
        for i in range(amb.x, amb.x + amb.w, 300):
            for j in range(amb.y, amb.y + amb.h, 300):
                if _teto_sobre(i, j) > pj.PISO_A_PISO:
                    vazio += 0.09
        if vazio < 1.0:
            out.append(Achado("ERRO", "Pe-direito duplo inexistente",
                              f"{cod} declarado com vazio e tem {vazio:.2f} m2 livres"))
    return out


# ------------------------- 23. chamine solar
VAZAO_CHAMINE_MIN = 6.0      # trocas por hora sem vento


def checar_chamine() -> list[Achado]:
    out = []
    lt = pj.LANTERNIM
    trocas = pj.trocas_por_hora()
    if trocas < VAZAO_CHAMINE_MIN:
        out.append(Achado("ATENCAO", "Chamine solar fraca",
                          f"{trocas} trocas/h sem vento (min {VAZAO_CHAMINE_MIN}): "
                          f"ampliar veneziana ou altura do lanternim"))
    # o lanternim tem de estar sobre o vazio, nao sobre laje
    cobre_vazio = 0.0
    for i in range(lt["x"], lt["x"] + lt["w"], 300):
        for j in range(lt["y"], lt["y"] + lt["h"], 300):
            if _teto_sobre(i, j) > pj.PISO_A_PISO:
                cobre_vazio += 0.09
    area = lt["w"] * lt["h"] / 1e6
    if cobre_vazio < area * 0.9:
        out.append(Achado("ERRO", "Lanternim sobre laje",
                          f"so {cobre_vazio:.2f} m2 de {area:.2f} m2 do lanternim "
                          f"ficam sobre o pe-direito duplo: o resto nao ventila nada"))
    if lt["altura_peitoril"] < pj.PISO_A_PISO + pj.PE_DIREITO:
        out.append(Achado("ERRO", "Lanternim baixo",
                          "o peitoril tem de ficar acima do forro do superior"))
    return out



# ------------------------- 24. instalacoes hidrossanitarias
# R53 — o lavabo e molhado e NAO tem ralo: sem chuveiro nao ha lamina no piso.
MOLHADOS_COM_RALO = {"T-REV", "S-S02", "S-S03", "S-MAS", "T-LAV", "T-COZ"}


def checar_hidraulica() -> list[Achado]:
    out = []
    for p in pj.prumadas_hidraulicas():
        if p["v"] > pj.VEL_MAX_AGUA:
            out.append(Achado("ERRO", "Velocidade acima da norma",
                              f"{p['pav']}: {p['v']} m/s em DN{p['dn_agua']} "
                              f"(max {pj.VEL_MAX_AGUA} m/s)", "NBR 5626"))
        elif p["v"] > pj.VEL_CONFORTO:
            out.append(Achado("ATENCAO", "Velocidade acima do conforto",
                              f"{p['pav']}: {p['v']} m/s em DN{p['dn_agua']} — acima "
                              f"de {pj.VEL_CONFORTO} m/s o tubo assobia"))
        if p["dn_esgoto"] < pj.dn_esgoto(p["uhc"]):
            out.append(Achado("ERRO", "Esgoto subdimensionado",
                              f"{p['pav']}: DN{p['dn_esgoto']} para {p['uhc']} UHC"))
    # toda peca precisa de ambiente e de peso declarado
    for p in pj.pecas_hidraulicas():
        if p["peso"] <= 0:
            out.append(Achado("ERRO", "Peca sem peso", p["cod"]))
        if not any(a.cod == p["amb"] for a in pj.TERREO + pj.SUPERIOR + pj.TERREO_ABERTO):
            out.append(Achado("ERRO", "Peca em ambiente inexistente",
                              f"{p['cod']} -> {p['amb']}"))
    # chuveiro eletrico precisa de pressao minima
    for pav in ("T", "S"):
        mca = pj.carga_hidraulica_mca(pav)
        if mca < 2.0 and pav not in {"S"}:
            out.append(Achado("ERRO", "Pressao insuficiente",
                              f"{pav}: {mca} mca sem pressurizador"))
    # area molhada sem ralo
    com_ralo = {r["amb"] for r in pj.RALOS}
    for cod in sorted(MOLHADOS_COM_RALO):
        if cod not in com_ralo:
            out.append(Achado("ERRO", "Area molhada sem ralo", cod))
    # ralo dentro do ambiente declarado
    for r in pj.RALOS:
        amb = next((a for a in pj.TERREO + pj.SUPERIOR + pj.TERREO_ABERTO
                    if a.cod == r["amb"]), None)
        if amb is None:
            out.append(Achado("ERRO", "Ralo em ambiente inexistente",
                              f"{r['cod']} -> {r['amb']}"))
            continue
        if not (amb.x <= r["x"] <= amb.x + amb.w and amb.y <= r["y"] <= amb.y + amb.h):
            out.append(Achado("ERRO", "Ralo fora do ambiente",
                              f"{r['cod']} em ({r['x']}, {r['y']}) fora de {amb.cod}"))
    return out


# ------------------------- 25. eletrica: previsao, demanda e condutor
AMPACIDADE = {10: 50, 16: 68, 25: 89, 35: 111, 50: 134}


def checar_eletrica() -> list[Achado]:
    out = []
    d = pj.demanda_eletrica()
    if d["corrente_a"] > AMPACIDADE[d["secao_mm2"]]:
        out.append(Achado("ERRO", "Condutor de entrada subdimensionado",
                          f"{d['corrente_a']} A em {d['secao_mm2']} mm2 "
                          f"(ampacidade {AMPACIDADE[d['secao_mm2']]} A)", "NBR 5410"))
    if d["padrao_a"] < d["corrente_a"]:
        out.append(Achado("ERRO", "Padrao de entrada menor que a demanda",
                          f"{d['padrao_a']} A para {d['corrente_a']} A"))
    # cada equipamento de climatizacao precisa de circuito proprio (TUE)
    splits = {c["capacidade"] for c in pj.CLIMATIZACAO if not c.get("reserva")}
    tues = [c for c in pj.CARGAS_ESPECIAIS if c["grupo"] == "climatizacao"]
    ativos = [c for c in pj.CLIMATIZACAO if not c.get("reserva")]
    if len(tues) < len(ativos):
        out.append(Achado("ERRO", "Climatizacao sem circuito proprio",
                          f"{len(ativos)} equipamentos ativos e {len(tues)} circuitos "
                          f"declarados: ar condicionado exige TUE individual"))
    # fator de demanda da climatizacao nao pode ser reduzido em ZB8
    for c in tues:
        if c["fd"] < 1.0:
            out.append(Achado("ERRO", "Fator de demanda reduzido na climatizacao",
                              f"{c['cod']}: fd {c['fd']} — em Manaus o ar condicionado "
                              f"e carga continua"))
    # chuveiros: conferir com a decisao ja fechada em AQUECIMENTO
    aq = [c for c in pj.CARGAS_ESPECIAIS if c["grupo"] == "aquecimento"]
    if len(aq) != pj.AQUECIMENTO["quantidade"]:
        out.append(Achado("ERRO", "Chuveiros divergentes",
                          f"{len(aq)} circuitos contra "
                          f"{pj.AQUECIMENTO['quantidade']} em AQUECIMENTO"))
    for c in aq:
        if c["va"] != pj.AQUECIMENTO["potencia_un"]:
            out.append(Achado("ERRO", "Potencia de chuveiro divergente",
                              f"{c['cod']}: {c['va']} W contra "
                              f"{pj.AQUECIMENTO['potencia_un']} W em AQUECIMENTO"))
    # previsao minima por ambiente (NBR 5410 9.5.2)
    for p in pj.previsao_iluminacao_tug():
        if p["ilum_va"] < pj.ILUM_VA_BASE:
            out.append(Achado("ERRO", "Iluminacao abaixo do minimo",
                              f"{p['amb']}: {p['ilum_va']} VA"))
        if p["tugs"] < 1:
            out.append(Achado("ERRO", "Ambiente sem tomada", p["amb"]))
        esperado = max(1, math.ceil(p["perim"] / (pj.TUG_PERIM_MOLHADA if p["molhada"]
                                                  else pj.TUG_PERIM_SECA)))
        if p["tugs"] < esperado:
            out.append(Achado("ERRO", "Tomadas abaixo do perimetro",
                              f"{p['amb']}: {p['tugs']} para {p['perim']} mm de "
                              f"perimetro (minimo {esperado})"))
    # o quadro geral tem de ter modulos para os circuitos
    circuitos = len(pj.CARGAS_ESPECIAIS) + len(pj.previsao_iluminacao_tug()) * 0 + 12
    if circuitos > 36:
        out.append(Achado("ATENCAO", "Quadro geral no limite",
                          f"{circuitos} circuitos estimados em quadro de 36 modulos"))
    return out


# ------------------------- 26. drenagem e impermeabilizacao
def checar_drenagem() -> list[Achado]:
    out = []
    cb = pj.COBERTURA
    q = pj.vazao_pluvial_ls()
    q_por_descida = q / cb["descidas"]
    lim = pj.CAPACIDADE_DESCIDA[cb["dn_descida"]]
    if q_por_descida > lim:
        out.append(Achado("ERRO", "Descida pluvial subdimensionada",
                          f"{q_por_descida:.2f} L/s por descida DN{cb['dn_descida']} "
                          f"(limite de projeto {lim} L/s)", "NBR 10844"))
    # a calha recebe a vazao de um trecho entre descidas
    cap = pj.capacidade_calha_ls()
    if q_por_descida > cap:
        out.append(Achado("ERRO", "Calha subdimensionada",
                          f"{q_por_descida:.2f} L/s por trecho contra {cap} L/s de "
                          f"capacidade em calha {cb['calha_l']} x {cb['calha_h']} mm "
                          f"a {cb['decliv_calha']:.1%}", "NBR 10844"))
    # a area de contribuicao tem de cobrir a projecao real mais beiral
    real = pj.projecao_coberta_m2()
    if pj.area_contribuicao_m2() < real:
        out.append(Achado("ERRO", "Area de contribuicao menor que a cobertura",
                          f"{pj.area_contribuicao_m2():.2f} m2 contra {real:.2f} m2 de "
                          f"projecao coberta"))
    if pj.CAIMENTO_AREA_MOLHADA < 0.005:
        out.append(Achado("ERRO", "Caimento insuficiente",
                          f"{pj.CAIMENTO_AREA_MOLHADA:.1%} em area molhada"))
    if pj.IMPERMEABILIZACAO["subida_box"] < pj.ALTURA_CHUVEIRO - 400:
        out.append(Achado("ATENCAO", "Impermeabilizacao baixa no box",
                          f"{pj.IMPERMEABILIZACAO['subida_box']} mm para chuveiro a "
                          f"{pj.ALTURA_CHUVEIRO} mm"))
    # R52 — a verificacao do reuso virou a verificacao DA SUA AUSENCIA. Ate
    # R51 era preciso garantir que a rede de reuso nao alcancasse vaso
    # sanitario; com o reuso encerrado por decisao do proprietario, o que
    # precisa ser garantido e que nao restou rede nao potavel nenhuma —
    # meia-decisao em instalacao e o que produz conexao cruzada.
    if pj.PLUVIAL.get("reuso", "").startswith("REJEITADO"):
        if "nao_estender_a" in pj.PLUVIAL:
            out.append(Achado("ERRO", "Sobra de reuso na decisao",
                              "PLUVIAL ainda carrega campo de rede nao "
                              "potavel depois de o reuso ser encerrado"))
        if pj.IRRIGACAO["fonte"].lower().startswith("reservatorio"):
            out.append(Achado("ERRO", "Irrigacao orfa",
                              f"a irrigacao ainda diz vir de "
                              f"'{pj.IRRIGACAO['fonte']}', que nao existe mais"))
    elif "vaso" not in pj.PLUVIAL.get("nao_estender_a", ""):
        out.append(Achado("ERRO", "Reuso sem restricao declarada",
                          "a rede de reuso precisa de restricao escrita de uso"))
    return out



# ------------------------- 27. integridade referencial de codigos
def _todos_os_codigos() -> set[str]:
    cods = {a.cod for a in pj.TERREO + pj.SUPERIOR + pj.TERREO_ABERTO
            + pj.SUPERIOR_ABERTO}
    cods |= {sd["nome"] for sd in pj.SUBDIVISOES}
    # R45 — o codigo QUALIFICADO tambem vale. "BANHO" sozinho e ambiguo: ha
    # tres, e a zona de revestimento precisa dizer de qual fala. Foi ao
    # referenciar S-MAS/BANHO na ZP-4 que esta verificacao acusou — e acusou
    # certo: o codigo nao existia no universo que ela conhecia.
    cods |= {f"{sd['pai']}/{sd['nome']}" for sd in pj.SUBDIVISOES}
    return cods


def checar_integridade_referencial() -> list[Achado]:
    """Todo codigo de ambiente citado em qualquer lista tem de existir.

    Esta verificacao nasceu de tres achados reais: T-PSE e T-CSE em definicoes
    mortas de cobertos(), e T-DML na lista de forros. Codigo orfao nao quebra
    nada — simplesmente deixa de ser aplicado, silenciosamente, e o projeto
    passa a ter uma decisao que nao chega ao desenho.
    """
    out = []
    validos = _todos_os_codigos()
    fontes = [
        ("FORROS", [f[0] for f in ep.FORROS]),
        ("CATEGORIA", list(ep.CATEGORIA.keys())),
        ("MOLHADOS", list(ep.MOLHADOS)),
        ("SILENCIO", list(ep.SILENCIO)),
        ("CLIMATIZACAO.amb", [c["amb"] for c in pj.CLIMATIZACAO]),
        ("CLIMATIZACAO.mais", [x for c in pj.CLIMATIZACAO for x in c.get("mais", [])]),
        ("CLIMATIZACAO.zona_aberta",
         [x for c in pj.CLIMATIZACAO for x in c.get("zona_aberta", [])]),
        ("TECNICOS.amb", [t["amb"] for t in pj.TECNICOS if t.get("amb")]),
        ("DIFUSORES", [d["amb"] for d in pj.DIFUSORES]),
        ("VENTILADORES", [v["amb"] for v in pj.VENTILADORES]),
        ("EXAUSTAO", [e["amb"] for e in pj.EXAUSTAO]),
        ("RALOS", [r["amb"] for r in pj.RALOS]),
        ("LOUCAS", [l["amb"] for l in pj.LOUCAS]),
        ("BANCADAS", [b["amb"] for b in pj.BANCADAS]),
        ("EQUIPAMENTOS", [e["amb"] for e in pj.EQUIPAMENTOS]),
        ("ARMARIOS", [a["amb"] for a in pj.ARMARIOS]),
        ("SUBDIVISOES.pai", [sd["pai"] for sd in pj.SUBDIVISOES]),
        ("VIGAS.sobre", [v["sobre"] for v in pj.VIGAS]),
        ("PAISAGISMO", [p["amb"] for p in pj.PAISAGISMO]),
        ("PE_DIREITO_DUPLO", list(pj.PE_DIREITO_DUPLO)),
        ("ZONAS_PAGINACAO", [c for z in pj.ZONAS_PAGINACAO for c in z["ambientes"]]),
        ("FRONTEIRA_CLIMATICA.entre", list(pj.FRONTEIRA_CLIMATICA["entre"])),
        ("PRESSURIZADOR.atende", list(pj.PRESSURIZADOR["atende"])),
        ("INTEGRADOS", [c for g in pj.INTEGRADOS for c in g]),
        ("PROLONGADA", list(PROLONGADA)),
        ("DISPENSADOS", list(DISPENSADOS)),
    ]
    for nome, lst in fontes:
        for cod in lst:
            if cod not in validos:
                out.append(Achado("ERRO", "Codigo de ambiente orfao",
                                  f"{nome} cita {cod}, que nao existe no modelo"))
    # codigos internos unicos
    for nome, lst in (("TECNICOS", [t["cod"] for t in pj.TECNICOS]),
                      ("LOUCAS", [l["cod"] for l in pj.LOUCAS]),
                      ("BANCADAS", [b["cod"] for b in pj.BANCADAS]),
                      ("ARMARIOS", [a["cod"] for a in pj.ARMARIOS]),
                      ("RALOS", [r["cod"] for r in pj.RALOS]),
                      ("VIGAS", [v["cod"] for v in pj.VIGAS]),
                      ("DIFUSORES", [d["cod"] for d in pj.DIFUSORES]),
                      ("VENTILADORES", [v["cod"] for v in pj.VENTILADORES]),
                      ("PENETRACOES", [p["cod"] for p in pj.PENETRACOES]),
                      ("PAISAGISMO", [p["cod"] for p in pj.PAISAGISMO]),
                      ("CARGAS_ESPECIAIS", [c["cod"] for c in pj.CARGAS_ESPECIAIS])):
        vistos = set()
        for c in lst:
            if c in vistos:
                out.append(Achado("ERRO", "Codigo duplicado",
                                  f"{nome}: {c} aparece mais de uma vez"))
            vistos.add(c)
    # ambiente fechado sem acabamento definido
    cobertos_fechados = {a.cod for a in pj.TERREO + pj.SUPERIOR}
    com_acab = {a["amb"] for a in pj.acabamentos()}
    for cod in sorted(cobertos_fechados - com_acab):
        out.append(Achado("ERRO", "Ambiente sem acabamento", cod))
    return out


# ------------------------- 28. acabamentos, locacao e paisagismo
def checar_fechamento() -> list[Achado]:
    out = []
    # acabamento coerente com as decisoes de origem
    alt = pj.alturas_revestimento()
    for a in pj.acabamentos():
        if a["amb"] in alt and str(alt[a["amb"]]) not in a["parede"]:
            out.append(Achado("ERRO", "Acabamento divergente da paginacao",
                              f"{a['amb']}: revestimento de {alt[a['amb']]} mm nao "
                              f"aparece na especificacao de parede"))
        if a["amb"] in ep.MOLHADOS and "antiderrapante" not in a["piso"] \
                and "cimenticio" not in a["piso"]:
            out.append(Achado("ERRO", "Area molhada sem piso antiderrapante",
                              f"{a['amb']}: {a['piso'][:40]}"))
        if a["forro_h"] > pj.PE_DIREITO:
            out.append(Achado("ERRO", "Forro acima do pe-direito",
                              f"{a['amb']}: {a['forro_h']} mm"))
        if a["forro_h"] < ALTURA_LIVRE_MIN:
            out.append(Achado("ERRO", "Forro abaixo da altura livre minima",
                              f"{a['amb']}: {a['forro_h']} mm"))
    # locacao: cantos dentro do lote e fora dos recuos
    for c in pj.cantos_locacao():
        if not (0 <= c["x"] <= pj.LOTE_L and 0 <= c["y"] <= pj.LOTE_P):
            out.append(Achado("ERRO", "Canto de locacao fora do lote", c["canto"]))
        if c["da_divisa_sul"] < pj.RECUO_ESQ:
            out.append(Achado("ERRO", "Canto dentro do recuo esquerdo",
                              f"{c['canto']}: {c['da_divisa_sul']} mm"))
        if c["da_testada"] < pj.RECUO_FRENTE:
            out.append(Achado("ERRO", "Canto dentro do recuo frontal",
                              f"{c['canto']}: {c['da_testada']} mm"))
        if c["do_fundo"] < pj.RECUO_FUNDO_MIN:
            out.append(Achado("ERRO", "Canto dentro do recuo de fundo",
                              f"{c['canto']}: {c['do_fundo']} mm"))
    # eixos de locacao tem de existir na malha
    for eixo, lst in (("x", pj.EIXOS_LOCACAO["x"]), ("y", pj.EIXOS_LOCACAO["y"])):
        for v in lst:
            if v % pj.SUBGRID:
                out.append(Achado("ERRO", "Eixo de locacao fora da malha",
                                  f"{eixo} = {v} mm"))
    # paisagismo: afastamento medido da POSICAO da muda, nao do canteiro
    for p in pj.PAISAGISMO:
        amb = next((a for a in pj.TERREO_ABERTO if a.cod == p["amb"]), None)
        if amb is None:
            continue
        if p.get("x") and not (amb.x <= p["x"] <= amb.x + amb.w
                               and amb.y <= p["y"] <= amb.y + amb.h):
            out.append(Achado("ERRO", "Muda fora do canteiro declarado",
                              f"{p['cod']} em ({p['x']}, {p['y']}) fora de {amb.cod}"))
            continue
        d = pj.afastamentos_especie(p)
        # muda em VASO nao tem raiz no solo: a distancia a edificacao deixa de
        # ser criterio (a horta da varanda esta encostada na casa de proposito)
        if "vaso" in str(p.get("raiz", "")) or "vaso" in p["especie"].lower():
            d.pop("edificacao", None)
        for onde, val in d.items():
            if p["afast_min"] and val < p["afast_min"]:
                nivel = "ERRO" if val < p["afast_min"] * 0.7 else "ATENCAO"
                out.append(Achado(nivel, "Especie perto demais",
                                  f"{p['cod']} {p['especie'].split('(')[0].strip()} a "
                                  f"{val:.0f} mm de {onde}; pede {p['afast_min']} mm"))
        if p.get("poda") and "rotineira" in str(p.get("poda", "")):
            out.append(Achado("ERRO", "Especie com poda rotineira",
                              f"{p['cod']}: o programa proibe poda rotineira"))
    # R52 — o balanco de reuso saiu com o reuso. A irrigacao continua existindo
    # e continua tendo de ser PEQUENA: a verificacao passa a ser contra a
    # demanda total da casa, nao contra a chuva captada.
    dia = pj.demanda_irrigacao_ldia()
    if dia > 300:
        out.append(Achado("ATENCAO", "Irrigacao pesada para a rede",
                          f"{dia:.0f} L/dia vindos da rede publica"))
    # emissao coerente com o historico de revisoes
    if pj.EMISSAO["revisao"] != pj.REVISOES[-1][0]:
        out.append(Achado("ERRO", "Revisao de emissao divergente",
                          f"EMISSAO diz {pj.EMISSAO['revisao']} e REVISOES termina em "
                          f"{pj.REVISOES[-1][0]}"))
    return out



# ------------------------- 29. piscina, deck e lounge (programa do YAML)
DIST_TV_MIN = 1.5          # x a largura da tela, para tela de 50 a 55"
LARGURA_TV_50 = 1_110      # mm — tela de 50 polegadas 16:9
PROF_SOFA = 900
DRENOS_MIN_AFAST = 900     # antiaprisionamento


def checar_piscina() -> list[Achado]:
    """Piscina: faixa seca, recirculacao, drenos e casa de maquinas."""
    out = []
    p, ps, dk = pj.PISCINA, pj.PISCINA_SISTEMA, pj.DECK
    # R78 — x cresce para o NORTE e y para o OESTE (testada em y = 0, leste)
    folgas = {"sul": p["x"] - dk["x"], "norte": (dk["x"] + dk["w"]) - (p["x"] + p["w"]),
              "leste": p["y"] - dk["y"], "oeste": (dk["y"] + dk["h"]) - (p["y"] + p["h"])}
    for lado, f in folgas.items():
        if f < p["faixa_seca_min"]:
            out.append(Achado("ERRO", "Faixa seca insuficiente",
                              f"lado {lado}: {f} mm de deck seco (min "
                              f"{p['faixa_seca_min']} mm)"))
    if abs(p["lamina_m2"] - p["w"] * p["h"] / 1e6) > 0.01:
        out.append(Achado("ERRO", "Lamina divergente da geometria",
                          f"{p['lamina_m2']} m2 declarados contra "
                          f"{p['w']*p['h']/1e6:.2f} m2 de retangulo"))
    if ps["drenos_fundo"] < 2:
        out.append(Achado("ERRO", "Dreno de fundo unico",
                          "com um so dreno o corpo veda a succao: exigencia "
                          "antiaprisionamento e de dois drenos afastados "
                          f"{DRENOS_MIN_AFAST} mm"))
    q = pj.vazao_recirculacao_m3h()
    if q > 8.0:
        out.append(Achado("ATENCAO", "Recirculacao acima da bomba prevista",
                          f"{q} m3/h para bomba de 0,5 cv"))
    # a casa de maquinas saiu do deck: conferir succao e ventilacao
    cm = next((t for t in pj.TECNICOS if t.get("casa_maquinas")), None)
    if cm:
        d = _folga(_ret(cm), (p["x"], p["y"], p["w"], p["h"]))
        if d > SUCCAO_BOMBA_MAX:
            out.append(Achado("ERRO", "Succao longa demais",
                              f"{d:.0f} mm da piscina (max {SUCCAO_BOMBA_MAX})"))
        if not pj.CASA_MAQUINAS.get("ventilacao"):
            out.append(Achado("ERRO", "Casa de maquinas sem ventilacao declarada",
                              cm["cod"]))
        if not pj.CASA_MAQUINAS.get("dreno"):
            out.append(Achado("ERRO", "Casa de maquinas sem dreno declarado",
                              cm["cod"]))
    return out


def checar_lounge() -> list[Achado]:
    """O mini lounge so existe se a distancia de visao couber nele.

    O YAML pede 2,40 x 2,60 m com televisor de 50 a 55 polegadas. Com o sofa
    encostado numa parede e o painel na outra, sobram 1,20 m de distancia — menos
    da metade do minimo confortavel. Esta verificacao mede o ambiente contra o
    equipamento que ele precisa abrigar, em vez de aceitar a dimensao declarada.
    """
    out = []
    lou = next((a for a in pj.SUPERIOR if a.cod == "S-LOU"), None)
    if lou is None:
        return out
    prof = max(lou.w, lou.h)
    dist = prof - 150 - PROF_SOFA
    minimo = LARGURA_TV_50 * DIST_TV_MIN
    if dist < minimo:
        out.append(Achado("ERRO", "Lounge curto para o televisor",
                          f"{dist:.0f} mm de distancia de visao em {prof} mm de "
                          f"profundidade; uma tela de 50 pede {minimo:.0f} mm"))
    else:
        out.append(Achado("NOTA", "Distancia de visao verificada",
                          f"{dist:.0f} mm com painel e sofa, contra {minimo:.0f} mm "
                          f"minimos para tela de 50 polegadas"))
    # a parede do painel nao pode encostar em dormitorio
    for a in pj.SUPERIOR:
        if a.cod in ("S-LOU", "S-HAL"):
            continue
        encosta = (abs(a.x + a.w - lou.x) < 1 or abs(lou.x + lou.w - a.x) < 1) and \
                  not (a.y + a.h <= lou.y or lou.y + lou.h <= a.y)
        if encosta and a.cod.startswith("S-S"):
            out.append(Achado("ATENCAO", "Lounge encostado em dormitorio",
                              f"{a.cod} divide parede com o lounge: o painel de TV "
                              f"precisa ir para a face oposta"))
    return out



# ------------------------- 32. cortina de vidro e eixo visual
DESALINHAMENTO_MAX = 900       # entre o eixo do social e o da piscina


def checar_cortina_vidro() -> list[Achado]:
    """A abertura que o proprietario quer so existe se tres coisas derem certo:
    a verga nao travar o trilho, nada estacionar na frente dela, e o piso
    atravessar a soleira sem degrau."""
    out = []
    cv, vg = pj.CORTINA_VIDRO, pj.VARANDA_GOURMET
    tipo = pj.ESQUADRIAS.get(cv["vao"])
    if tipo is None:
        out.append(Achado("ERRO", "Cortina sem esquadria declarada", cv["vao"]))
        return out
    if tipo[0] != cv["largura"]:
        out.append(Achado("ERRO", "Cortina divergente da esquadria",
                          f"{cv['largura']} mm contra {tipo[0]} mm em ESQUADRIAS"))
    if cv["folhas"] * cv["largura_folha"] != cv["largura"]:
        out.append(Achado("ERRO", "Folhas nao fecham o vao",
                          f"{cv['folhas']} x {cv['largura_folha']} = "
                          f"{cv['folhas']*cv['largura_folha']} para "
                          f"{cv['largura']} mm"))
    # a verga precisa do limite proprio de trilho
    v10 = next((v for v in pj.dimensionar_vigas()
                if v.get("limite_flecha") == "cortina_vidro"), None)
    if v10 is None:
        out.append(Achado("ERRO", "Cortina sem verga dimensionada",
                          "nenhuma viga declara limite_flecha de cortina_vidro"))
    elif v10["flecha"] > v10["flecha_adm"]:
        out.append(Achado("ERRO", "Verga da cortina flete demais",
                          f"{v10['flecha']} mm contra {v10['flecha_adm']} — o "
                          f"trilho fecha sobre as folhas"))
    # nada de mobiliario encostado na linha da cortina, dos dois lados
    faixa = (cv["x"], cv["y"] - 900, cv["largura"], 1_800)
    for cod, ctipo, x, y, w, h in _pecas_do_pav("T"):
        if _sobrepoe(faixa, (x, y, w, h)) > 0.05:
            out.append(Achado("ERRO", "Mobiliario na linha da cortina",
                              f"{cod} ({ctipo}) ocupa a faixa de 900 mm dos dois "
                              f"lados da cortina: e ele que tapa a vista, nao a "
                              f"esquadria"))
    # continuidade interno/externo
    cont = pj.CONTINUIDADE_INTERNO_EXTERNO
    if cont["desnivel_piso"] != 0:
        out.append(Achado("ERRO", "Degrau na soleira da cortina",
                          f"{cont['desnivel_piso']} mm: com degrau o olho le dois "
                          f"ambientes, nao um"))
    if not cont["junta_alinhada"]:
        out.append(Achado("ATENCAO", "Paginacao interrompida na soleira",
                          "a junta precisa atravessar a linha da cortina"))
    # a varanda precisa de profundidade de permanencia
    if vg["prof"] < 2_400:
        out.append(Achado("ERRO", "Varanda rasa demais",
                          f"{vg['prof']} mm nao abrigam mesa durante chuva com vento"))
    if vg["largura"] != cv["largura"]:
        out.append(Achado("ATENCAO", "Varanda mais estreita que a abertura",
                          f"{vg['largura']} contra {cv['largura']} mm"))
    # ralo sob o trilho
    if not any(r["amb"] == "T-ALP" and "cortina" in r["tipo"] for r in pj.RALOS):
        out.append(Achado("ERRO", "Cortina sem ralo linear sob o trilho",
                          "7,20 m de fresta rente ao piso sem canal de drenagem"))
    # eixo visual
    ev = pj.eixo_visual()
    if ev["desalinhamento"] > DESALINHAMENTO_MAX:
        out.append(Achado("ATENCAO", "Piscina fora do eixo do social",
                          f"{ev['desalinhamento']:.0f} mm entre o eixo do estar e o "
                          f"da piscina (max {DESALINHAMENTO_MAX})"))
    else:
        out.append(Achado("NOTA", "Eixo visual verificado",
                          f"estar -> cortina -> varanda -> piscina em "
                          f"{ev['profundidade_total']/1000:.1f} m de profundidade, "
                          f"com {ev['desalinhamento']:.0f} mm de desalinhamento e "
                          f"{ev['vao_livre']} mm de vao livre quando aberta"))
    return out


# -------------------------------------------------------- consolidado
def verificacoes() -> list:
    """As funcoes de verificacao, em ordem de execucao."""
    return [checar_malha, checar_colisoes, checar_conectividade, checar_vaos,
            checar_acesso_por_molhado, checar_iluminacao, checar_acessibilidade,
            checar_metas, checar_escada, checar_vedacao, checar_espacos_mortos,
            checar_bancadas, checar_loucas, checar_subdivisoes,
            checar_colisao_porta, checar_janela_mobiliario, checar_tecnicos,
            checar_projecao_superior, checar_fronteira_climatica,
            checar_estrutura, checar_penetracoes, checar_paginacao,
            checar_altura_livre, checar_chamine, checar_hidraulica,
            checar_eletrica, checar_drenagem,
            checar_integridade_referencial, checar_fechamento,
            checar_piscina, checar_lounge, checar_cortina_vidro]


def metrica() -> dict:
    """Quantas verificacoes e quantas CONDICOES a auditoria testa.

    Medido no proprio codigo, por contagem de emissoes de Achado, para que o
    numero citado nas pranchas e nos documentos nao possa divergir do que a
    auditoria de fato faz. Os numeros informados nas revisoes 15 a 17 do
    DIVERGENCIAS contavam "verificacoes" de forma inconsistente; esta funcao
    encerra a questao medindo em vez de estimar.
    """
    import inspect
    fns = verificacoes()
    cond = sum(inspect.getsource(f).count("Achado(") for f in fns)
    return dict(funcoes=len(fns), condicoes=cond)


def auditar() -> list[Achado]:
    return (checar_malha() + checar_colisoes() + checar_conectividade() +
            checar_vaos() + checar_acesso_por_molhado() +
            checar_iluminacao() + checar_acessibilidade() +
            checar_metas() + checar_escada() + checar_vedacao() +
            checar_espacos_mortos() + checar_bancadas() + checar_loucas() +
            checar_subdivisoes() + checar_colisao_porta() + checar_janela_mobiliario() +
            checar_tecnicos() + checar_projecao_superior() +
            checar_fronteira_climatica() + checar_estrutura() +
            checar_penetracoes() + checar_paginacao() +
            checar_altura_livre() + checar_chamine() +
            checar_hidraulica() + checar_eletrica() + checar_drenagem() +
            checar_integridade_referencial() + checar_fechamento() +
            checar_piscina() + checar_lounge() + checar_cortina_vidro())


if __name__ == "__main__":
    achados = auditar()
    for n in ("ERRO", "ATENCAO", "NOTA"):
        grupo = [a for a in achados if a.nivel == n]
        print(f"\n=== {n}  ({len(grupo)}) ===")
        for a in grupo:
            print(f"  {a.item}: {a.detalhe}" + (f"  [{a.ref}]" if a.ref else ""))
    print(f"\ntotal: {len(achados)} achados")
