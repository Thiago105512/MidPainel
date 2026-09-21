"""PERCURSO — por onde cada fio e cada tubo passa, e o que os segura (R80).

Ate R79 o comprimento de um circuito era a distancia Manhattan do quadro ao
centro do ambiente vezes 1,2 — serve para a queda de tensao, mas nao diz por
qual parede o eletroduto vai. Aqui cada ponto (nucleo/pontos) e alcancado
pelo GRAFO DAS PAREDES do pavimento (Dijkstra), e o caminho vira trechos
com sistema, plano e fixadores.

  ELETRICA. Do quadro, o eletroduto corrugado corre DENTRO da parede, na
  altura dos furos de servico dos montantes (Z_ELETRICA = 1.450, os mesmos
  furos que a fabricacao ja abre), atravessando um montante a cada 600 mm
  com bucha de protecao. Desce ou sobe na parede ate a caixa do ponto.
  Luminaria e ventilador: sobe na parede ate o forro e cruza o entreforro
  (ou o entrepiso, no terreo) em linha reta ate a caixa octogonal.
  Equipamento externo (bombas, portao): sai pela parede externa mais
  proxima e segue enterrado a 400 mm.
  AGUA. Da coluna AF-01 (barrilete -> coluna do pavimento) o PEX DN20 corre
  na parede a Z_AGUA = 400 mm por furos de 32 mm (que R80 acrescenta a
  fabricacao) e sobe ate a peca. Esgoto nao entra em montante (DN50 e mais:
  furo maior que meia alma): corre SOB o piso — no radier, envelopado; no
  entrepiso, entre as vigas — ate a prumada ou a caixa, e so a prumada e
  vertical. Frigorigena: do nicho ao evaporador, pela fachada e pela parede.
  FIXADORES (H). Eletroduto: bucha passa-fio em cada montante atravessado;
  clip plastico a cada 1.200 mm nos montantes; abracadeira a cada 1.000 mm
  no forro/entrepiso; caixa 4x2 em tomada e interruptor, 4x4 octogonal em
  luminaria e ventilador, 4x4 em TUE; caixa de passagem a cada 15 m de
  eletroduto ou 3 curvas (NBR 5410 6.2.11). PEX: luva de protecao em cada
  montante, clip a cada 600 mm, barra de fixacao entre montantes em cada
  peca. Esgoto: arame a tela a cada 1,5 m no radier; abracadeira isofonica a
  cada 1,0 m no entrepiso, suporte na descida.
"""
from __future__ import annotations

import heapq
import math
from functools import lru_cache

# ------------------------------------------------------------------ (H)
Z_ELETRICA = 1_450          # furo de servico dos montantes (peca.furos_de_servico, comp/2)
Z_AGUA = 400                # furo hidraulico: acima da guia e abaixo de qualquer caixa
Z_ENTERRADO = -400
Z_ESGOTO_T = -150           # sob o radier
Z_ESGOTO_S_DESCE = -150     # dentro do vigamento, abaixo do piso do superior
D_ELETRODUTO = 25
D_PEX = 20
FURO_HIDRAULICO = 32
PASSO_MONTANTE_CLIP = 1_200
PASSO_ABRAC_FORRO = 1_000
PASSO_CLIP_PEX = 600
PASSO_ARAME_RADIER = 1_500
PASSO_ABRAC_ESGOTO = 1_000
CAIXA_PASSAGEM_M = 15_000
CAIXA_PASSAGEM_CURVAS = 3
TOL = 80


# ================================================================== grafo das paredes
def _seg(w):
    return (min(w["x1"], w["x2"]), min(w["y1"], w["y2"]), max(w["x1"], w["x2"]), max(w["y1"], w["y2"]))


def _projecao(w, x, y):
    x0, y0, x1, y1 = _seg(w)
    if w["horizontal"]:
        return (min(max(x, x0), x1), y0)
    return (x0, min(max(y, y0), y1))


class Grafo:
    def __init__(self, paredes: list[dict], extras: list[tuple[float, float]] = ()):
        self.paredes = paredes
        self.adj: dict = {}
        self.no_parede: dict = {}
        cortes = {w["cod"]: set() for w in paredes}
        for w in paredes:
            x0, y0, x1, y1 = _seg(w)
            cortes[w["cod"]].update({(x0, y0), (x1, y1)})
            for v in paredes:
                if v is w:
                    continue
                a0, b0, a1, b1 = _seg(v)
                if w["horizontal"] and not v["horizontal"] and x0 - TOL <= a0 <= x1 + TOL and b0 - TOL <= y0 <= b1 + TOL:
                    cortes[w["cod"]].add((a0, y0))
                if not w["horizontal"] and v["horizontal"] and y0 - TOL <= b0 <= y1 + TOL and a0 - TOL <= x0 <= a1 + TOL:
                    cortes[w["cod"]].add((x0, b0))
        for (x, y) in extras:
            w = self.parede_mais_proxima(x, y)
            if w is not None:
                cortes[w["cod"]].add(_projecao(w, x, y))
        for w in paredes:
            pts = sorted(cortes[w["cod"]], key=lambda p: (p[0], p[1]))
            for a, b in zip(pts, pts[1:]):
                d = abs(b[0] - a[0]) + abs(b[1] - a[1])
                if d == 0:
                    continue
                self.adj.setdefault(a, {})[b] = (d, w["cod"])
                self.adj.setdefault(b, {})[a] = (d, w["cod"])
                self.no_parede.setdefault(a, w["cod"]); self.no_parede.setdefault(b, w["cod"])

    def parede_mais_proxima(self, x, y, tol=None):
        melhor, dm = None, 1e18
        for w in self.paredes:
            px, py = _projecao(w, x, y)
            d = abs(px - x) + abs(py - y)
            if d < dm:
                melhor, dm = w, d
        return melhor if (tol is None or dm <= tol) else None

    def no_de(self, x, y):
        w = self.parede_mais_proxima(x, y)
        p = _projecao(w, x, y)
        if p in self.adj:
            return p
        # o ponto cai no meio de uma aresta: liga aos dois vizinhos dessa parede
        melhor = min(self.adj, key=lambda q: abs(q[0] - p[0]) + abs(q[1] - p[1]))
        return melhor

    def caminho(self, a, b) -> tuple[list, float, list]:
        """Dijkstra; devolve nos, comprimento e a parede de cada aresta."""
        dist = {a: 0.0}; prev = {}; fila = [(0.0, a)]
        while fila:
            d, u = heapq.heappop(fila)
            if u == b:
                break
            if d > dist.get(u, 1e18):
                continue
            for v, (dv, cod) in self.adj.get(u, {}).items():
                nd = d + dv
                if nd < dist.get(v, 1e18):
                    dist[v] = nd; prev[v] = (u, cod); heapq.heappush(fila, (nd, v))
        if b not in dist:
            return [], 0.0, []
        nos, pars = [b], []
        while nos[-1] != a:
            u, cod = prev[nos[-1]]
            nos.append(u); pars.append(cod)
        return nos[::-1], dist[b], pars[::-1]


@lru_cache(maxsize=None)
def _grafo(pj, pav: str) -> Grafo:
    import nucleo.pontos as pt
    todos = pt.todos(pj)
    extras = [(p["x"], p["y"]) for k in ("tomadas", "interruptores", "tue", "agua") for p in todos[k] if p["pav"] == pav and p.get("parede")]
    for k in ("luminarias",):
        extras += [(p["x"], p["y"]) for p in todos[k] if p["pav"] == pav]
    extras += [(q["x"] + q["w"] / 2, q["y"] + q["h"] / 2) for q in pj.TECNICOS if q["zona"] == "INT"]
    extras += [(p["x"], p["y"]) for p in pj.PRUMADAS]
    return Grafo(pt.paredes(pj, pav), extras)


def _z_do_pav(pj, pav):
    return pj.NIVEL_SUPERIOR if pav == "S" else 0


def _quadro(pj, pav):
    cod = "TC-06" if pav == "S" else "TC-05"
    t = next(q for q in pj.TECNICOS if q["cod"] == cod)
    return dict(cod=cod, x=t["x"] + t["w"] / 2, y=t["y"] + t["h"] / 2)


def _fonte_agua(pj):
    p = next(q for q in pj.PRUMADAS if q["tipo"] == "agua fria")
    return dict(cod=p["cod"], x=p["x"], y=p["y"])


def _polilinha(nos, z):
    return [(x, y, z) for x, y in nos]


def _comp_pol(pol):
    return sum(abs(b[0] - a[0]) + abs(b[1] - a[1]) + abs(b[2] - a[2]) for a, b in zip(pol, pol[1:]))


def _montantes(comp_mm, pj) -> int:
    return int(comp_mm // pj.MONTANTE_ESPACAMENTO) + 1 if comp_mm > 0 else 0


def _trechos_de(pj, pav, sistema, cod, origem, destino_xy, z_plano, z_ponto, no_forro=False, externo=False, z_forro=None, diam=D_ELETRODUTO):
    """Origem (no do grafo) ate o ponto: trechos com plano, comprimento e parede."""
    g = _grafo(pj, pav)
    zp = _z_do_pav(pj, pav)
    a = g.no_de(origem[0], origem[1])
    if externo:
        w = g.parede_mais_proxima(*destino_xy)
        px, py = _projecao(w, *destino_xy)
        b = g.no_de(px, py)
    else:
        b = g.no_de(*destino_xy)
    nos, comp, pars = g.caminho(a, b)
    if not nos:
        nos, pars = [a, b], ["?"]
    out = []
    pol = _polilinha(nos, zp + z_plano)
    for (p, q), cod_par in zip(zip(pol, pol[1:]), pars):
        d = _comp_pol([p, q])
        if d == 0:
            continue
        out.append(dict(sistema=sistema, cod=cod, plano="parede", parede=cod_par, de=p, para=q, comp_mm=round(d),
                        montantes=_montantes(d, pj), diam=diam))
    fim = pol[-1]
    if no_forro:
        zf = zp + (z_forro if z_forro is not None else pj.PE_DIREITO)
        out.append(dict(sistema=sistema, cod=cod, plano="parede-vertical", parede=pars[-1] if pars else "?", de=fim, para=(fim[0], fim[1], zf),
                        comp_mm=round(abs(zf - fim[2])), montantes=0, diam=diam))
        dx, dy = destino_xy[0] - fim[0], destino_xy[1] - fim[1]
        m = (destino_xy[0], fim[1], zf)
        for p, q in (((fim[0], fim[1], zf), m), (m, (destino_xy[0], destino_xy[1], zf))):
            d = _comp_pol([p, q])
            if d > 0:
                out.append(dict(sistema=sistema, cod=cod, plano="forro" if pav == "S" or z_forro else "entrepiso", parede=None, de=p, para=q,
                                comp_mm=round(d), montantes=0, diam=diam))
        zfinal = zp + z_ponto
        if abs(zfinal - zf) > 1:
            out.append(dict(sistema=sistema, cod=cod, plano="descida", parede=None, de=(destino_xy[0], destino_xy[1], zf),
                            para=(destino_xy[0], destino_xy[1], zfinal), comp_mm=round(abs(zfinal - zf)), montantes=0, diam=diam))
    elif externo:
        # desce na parede externa ate Z_ENTERRADO, segue enterrado em L ate o ponto, sobe ate a cota do ponto
        out.append(dict(sistema=sistema, cod=cod, plano="parede-vertical", parede=pars[-1] if pars else "?", de=fim, para=(fim[0], fim[1], Z_ENTERRADO),
                        comp_mm=round(abs(fim[2] - Z_ENTERRADO)), montantes=0, diam=diam))
        m = (destino_xy[0], fim[1], Z_ENTERRADO)
        for p, q in (((fim[0], fim[1], Z_ENTERRADO), m), (m, (destino_xy[0], destino_xy[1], Z_ENTERRADO))):
            d = _comp_pol([p, q])
            if d > 0:
                out.append(dict(sistema=sistema, cod=cod, plano="enterrado", parede=None, de=p, para=q, comp_mm=round(d), montantes=0, diam=diam))
        out.append(dict(sistema=sistema, cod=cod, plano="subida", parede=None, de=(destino_xy[0], destino_xy[1], Z_ENTERRADO),
                        para=(destino_xy[0], destino_xy[1], z_ponto), comp_mm=round(abs(z_ponto - Z_ENTERRADO)), montantes=0, diam=diam))
    else:
        zfinal = zp + z_ponto
        if abs(zfinal - fim[2]) > 1:
            out.append(dict(sistema=sistema, cod=cod, plano="parede-vertical", parede=pars[-1] if pars else "?", de=fim, para=(fim[0], fim[1], zfinal),
                            comp_mm=round(abs(zfinal - fim[2])), montantes=0, diam=diam))
    return out


# ================================================================== eletrica
@lru_cache(maxsize=None)
def eletrica(pj) -> list[dict]:
    """Um percurso por ponto eletrico, do seu quadro ate ele."""
    import nucleo.pontos as pt
    t = pt.todos(pj)
    out = []
    for grupo, caixa in (("tomadas", "caixa 4x2"), ("interruptores", "caixa 4x2"), ("luminarias", "caixa 4x4 octogonal"), ("tue", "caixa 4x4")):
        for p in t[grupo]:
            pav = p["pav"]
            q = _quadro(pj, pav)
            forro = grupo == "luminarias" and p.get("no_forro", True) or p.get("forro")
            z_forro = None
            if grupo == "luminarias":
                z_forro = p["z"]
            elif p.get("forro"):
                z_forro = min(p["z"], pj.PE_DIREITO)
            tr = _trechos_de(pj, pav, "eletrica", p["cod"], (q["x"], q["y"]), (p["x"], p["y"]), Z_ELETRICA, p["z"],
                             no_forro=bool(forro), externo=bool(p.get("externo")), z_forro=z_forro)
            comp = sum(x["comp_mm"] for x in tr)
            curvas = max(0, len(tr) - 1)
            out.append(dict(cod=p["cod"], circuito=p.get("circuito"), grupo=grupo, amb=p.get("amb"), pav=pav, quadro=q["cod"],
                            trechos=tr, comp_mm=comp, curvas=curvas, caixa=caixa,
                            caixas_passagem=max(math.ceil(comp / CAIXA_PASSAGEM_M) - 1, 0) + (1 if curvas > CAIXA_PASSAGEM_CURVAS else 0)))
    return out


@lru_cache(maxsize=None)
def agua(pj) -> list[dict]:
    import nucleo.pontos as pt
    f = _fonte_agua(pj)
    out = []
    for p in pt.agua(pj):
        pav = p["pav"]
        if p.get("externo"):
            tr = _trechos_de(pj, "T", "agua", p["cod"], (f["x"], f["y"]), (p["x"], p["y"]), Z_AGUA, p["z"], externo=True, diam=D_PEX)
        else:
            tr = _trechos_de(pj, pav, "agua", p["cod"], (f["x"], f["y"]), (p["x"], p["y"]), Z_AGUA, p["z"], diam=D_PEX)
        comp = sum(x["comp_mm"] for x in tr)
        out.append(dict(cod=p["cod"], amb=p["amb"], pav=pav, tipo=p["tipo"], quente=p["quente"], fonte=f["cod"], trechos=tr, comp_mm=comp,
                        curvas=max(0, len(tr) - 1), terminal="barra de fixacao entre montantes + joelho de transicao PEX/rosca"))
    return out


@lru_cache(maxsize=None)
def esgoto(pj) -> list[dict]:
    """Sob o piso, em L, da peca ao destino que nucleo/esgoto ja decidiu."""
    import nucleo.esgoto as es
    import nucleo.pontos as pt
    ramais = {r["peca"]: r for r in es.ramais(pj)}
    destinos = {p["cod"]: p for p in pj.PRUMADAS}
    for c in es._ci_terreo(pj):
        destinos[c["cod"]] = c
    for d in es.desconectores(pj):
        destinos[d["cod"]] = d
    out = []
    for p in pt.esgoto(pj):
        r = ramais.get(p["cod"])
        if not r:
            continue
        dst = destinos.get(r["destino"])
        if not dst:
            continue
        z = (_z_do_pav(pj, p["pav"]) + Z_ESGOTO_S_DESCE) if p["pav"] == "S" else Z_ESGOTO_T
        a = (p["x"], p["y"], z); m = (dst["x"], p["y"], z); b = (dst["x"], dst["y"], z)
        tr = []
        for u, v in ((a, m), (m, b)):
            d = _comp_pol([u, v])
            if d > 0:
                tr.append(dict(sistema="esgoto", cod=p["cod"], plano="radier" if p["pav"] == "T" else "entrepiso", parede=None, de=u, para=v,
                               comp_mm=round(d), montantes=0, diam=r["dn"]))
        out.append(dict(cod=p["cod"], amb=p["amb"], pav=p["pav"], dn=r["dn"], destino=r["destino"], trechos=tr,
                        comp_mm=sum(x["comp_mm"] for x in tr), caimento=r["caimento"]))
    return out


@lru_cache(maxsize=None)
def frigorigena(pj) -> list[dict]:
    """Do nicho ao evaporador: pela parede externa e pela parede do ambiente."""
    import nucleo.pontos as pt
    tc = {t["cod"]: t for t in pj.TECNICOS}
    evap = {p["circuito"]: p for p in pt.tue(pj) if "split" in p["desc"].lower()}
    out = []
    for l in pj.linhas_frigorigenas():
        if l.get("reserva"):
            continue
        n = tc[l["nicho"]]
        cod_tue = next((c["cod"] for c in pj.CARGAS_ESPECIAIS if "split" in c["desc"].lower()
                        and __import__("nucleo.circuitos", fromlist=["_amb_de"])._amb_de(c) == l["amb"]
                        and (("duto" in c["desc"].lower()) == ("duto" in l.get("tipo", "")))), None)
        ev = evap.get(cod_tue) or next((p for p in evap.values() if p["amb"] == l["amb"]), None)
        pav = "S" if l["amb"].startswith("S-") else "T"
        zp = _z_do_pav(pj, pav)
        nx, ny = n["x"] + n["w"] / 2, n["y"] + n["h"] / 2
        if ev is None:
            continue
        # sobe no nicho ate a altura do evaporador, corre pela fachada/parede ate ele
        a = (nx, ny, 600); b = (nx, ny, zp + ev["z"]); m = (ev["x"], ny, zp + ev["z"]); c = (ev["x"], ev["y"], zp + ev["z"])
        tr = []
        for u, v, plano in ((a, b, "subida"), (b, m, "fachada"), (m, c, "parede")):
            d = _comp_pol([u, v])
            if d > 0:
                tr.append(dict(sistema="frigorigena", cod=l["cod"], plano=plano, parede=None, de=u, para=v, comp_mm=round(d), montantes=0, diam=30))
        out.append(dict(cod=l["cod"], amb=l["amb"], nicho=l["nicho"], evaporador=ev["cod"], trechos=tr, comp_mm=sum(x["comp_mm"] for x in tr),
                        declarado_mm=l["comp"], dreno_dn=l["dreno"], suc=l["suc"], liq=l["liq"]))
    return out


# ================================================================== arvores
def _chave(t):
    a, b = t["de"], t["para"]
    return (t["parede"], tuple(sorted((tuple(round(v) for v in a), tuple(round(v) for v in b)))))


@lru_cache(maxsize=None)
def arvores_eletrica(pj) -> list[dict]:
    """Por circuito: a UNIAO dos trechos de parede dos seus pontos (um eletroduto
    serve o ambiente inteiro), mais o que e proprio de cada ponto (subida,
    descida, forro, enterrado). E sobre a arvore que se compra e se fixa."""
    grupos: dict = {}
    for r in eletrica(pj):
        g = grupos.setdefault(r["circuito"] or r["cod"], dict(circuito=r["circuito"] or r["cod"], pav=r["pav"], quadro=r["quadro"], pontos=0,
                                                              parede={}, proprios=[], caixas={}, mais_longe_mm=0))
        g["pontos"] += 1
        g["mais_longe_mm"] = max(g["mais_longe_mm"], r["comp_mm"])
        for t in r["trechos"]:
            if t["plano"] == "parede":
                g["parede"][_chave(t)] = t
            else:
                g["proprios"].append(t)
        g["caixas"][r["caixa"]] = g["caixas"].get(r["caixa"], 0) + 1
    out = []
    for g in grupos.values():
        par = list(g["parede"].values())
        comp_par = sum(t["comp_mm"] for t in par)
        comp_prop = sum(t["comp_mm"] for t in g["proprios"])
        # caixa de passagem: uma a cada 15 m de arvore (NBR 5410 6.2.11) e uma
        # de derivacao onde o circuito se abre para mais de um ponto; as curvas
        # de parede para parede terminam nas caixas dos proprios pontos
        paredes_distintas = len({t["parede"] for t in par})
        out.append(dict(circuito=g["circuito"], pav=g["pav"], quadro=g["quadro"], pontos=g["pontos"], trechos_parede=par, proprios=g["proprios"],
                        arvore_mm=comp_par + comp_prop, parede_mm=comp_par, mais_longe_mm=g["mais_longe_mm"], paredes=paredes_distintas,
                        montantes=sum(t["montantes"] for t in par), caixas=g["caixas"],
                        caixas_passagem=math.ceil(comp_par / CAIXA_PASSAGEM_M) + (1 if g["pontos"] > 1 else 0)))
    return out


@lru_cache(maxsize=None)
def arvores_agua(pj) -> list[dict]:
    grupos: dict = {}
    for r in agua(pj):
        g = grupos.setdefault(r["amb"], dict(amb=r["amb"], pav=r["pav"], pecas=0, parede={}, proprios=[]))
        g["pecas"] += 1
        for t in r["trechos"]:
            if t["plano"] == "parede":
                g["parede"][_chave(t)] = t
            else:
                g["proprios"].append(t)
    out = []
    for g in grupos.values():
        par = list(g["parede"].values())
        out.append(dict(amb=g["amb"], pav=g["pav"], pecas=g["pecas"], trechos_parede=par, proprios=g["proprios"],
                        arvore_mm=sum(t["comp_mm"] for t in par) + sum(t["comp_mm"] for t in g["proprios"]),
                        montantes=sum(t["montantes"] for t in par)))
    return out


# ================================================================== fixadores
def fixadores(pj) -> dict:
    es, fr = esgoto(pj), frigorigena(pj)
    f = dict()
    def add(k, n, un="un"):
        f[k] = f.get(k, dict(qtd=0, un=un)); f[k]["qtd"] += n
    for g in arvores_eletrica(pj):
        for t in g["trechos_parede"]:
            add("bucha passa-fio 25 mm (montante atravessado)", t["montantes"])
            add("clip de eletroduto no montante (a cada 1.200 mm)", math.ceil(t["comp_mm"] / PASSO_MONTANTE_CLIP))
        for t in g["proprios"]:
            if t["plano"] in ("forro", "entrepiso"):
                add("abracadeira de eletroduto no forro/entrepiso (a cada 1.000 mm)", math.ceil(t["comp_mm"] / PASSO_ABRAC_FORRO))
            elif t["plano"] == "enterrado":
                add("eletroduto PEAD enterrado (m)", round(t["comp_mm"] / 1000, 1), "m")
        for k, n in g["caixas"].items():
            add(k, n)
        add("caixa de passagem", g["caixas_passagem"])
    for g in arvores_agua(pj):
        for t in g["trechos_parede"]:
            add(f"luva de protecao no furo de {FURO_HIDRAULICO} mm (montante atravessado)", t["montantes"])
            add("clip de PEX no montante (a cada 600 mm)", math.ceil(t["comp_mm"] / PASSO_CLIP_PEX))
        for t in g["proprios"]:
            if t["plano"] == "parede-vertical":
                add("clip de PEX na subida (a cada 600 mm)", math.ceil(t["comp_mm"] / PASSO_CLIP_PEX))
        add("barra de fixacao entre montantes + joelho de transicao (peca)", g["pecas"])
    for r in es:
        for t in r["trechos"]:
            if t["plano"] == "radier":
                add("arame de amarracao do esgoto a tela do radier (a cada 1,5 m)", math.ceil(t["comp_mm"] / PASSO_ARAME_RADIER))
            else:
                add("abracadeira isofonica de esgoto no entrepiso (a cada 1,0 m)", math.ceil(t["comp_mm"] / PASSO_ABRAC_ESGOTO))
    for r in fr:
        for t in r["trechos"]:
            add("abracadeira de linha frigorigena (a cada 1,0 m)", math.ceil(t["comp_mm"] / PASSO_ABRAC_FORRO))
    return f


# ================================================================== o que cada parede esconde
def por_parede(pj) -> list[dict]:
    """Mapa de tubulacoes e cabos ocultos: parede -> sistemas, cotas, trechos."""
    import nucleo.pontos as pt
    acc: dict = {}
    for grupo, lista in (("eletrica", eletrica(pj)), ("agua", agua(pj))):
        for r in lista:
            for t in r["trechos"]:
                if t["parede"] and t["plano"] in ("parede", "parede-vertical"):
                    e = acc.setdefault(t["parede"], dict(parede=t["parede"], eletrica_mm=0, agua_mm=0, verticais=0, z=set(), pontos=set()))
                    if t["plano"] == "parede":
                        e[f"{grupo}_mm"] += t["comp_mm"]; e["z"].add(int(t["de"][2] - _z_do_pav(pj, r["pav"])))
                    else:
                        e["verticais"] += 1
                    e["pontos"].add(r["cod"])
    paredes = {w["cod"]: w for pav in ("T", "S") for w in pt.paredes(pj, pav)}
    out = []
    for cod, e in sorted(acc.items()):
        w = paredes.get(cod, {})
        out.append(dict(parede=cod, pav=cod[1], x1=w.get("x1"), y1=w.get("y1"), x2=w.get("x2"), y2=w.get("y2"), externa=w.get("externa"),
                        eletrica_m=round(e["eletrica_mm"] / 1000, 1), agua_m=round(e["agua_mm"] / 1000, 1), verticais=e["verticais"],
                        cotas=sorted(e["z"]), pontos=len(e["pontos"]),
                        aviso=("nao furar entre 350 e 450 mm nem entre 1.400 e 1.500 mm; verticais junto aos pontos" if e["agua_mm"]
                               else "nao furar entre 1.400 e 1.500 mm; verticais junto aos pontos")))
    return out


def servicos_por_painel(pj, paineis) -> dict:
    """Que furos cada painel precisa: eletrica em todos; hidraulica onde a agua passa."""
    agua_par = {t["parede"] for r in agua(pj) for t in r["trechos"] if t["plano"] == "parede" and t["parede"]}
    import nucleo.pontos as pt
    paredes = {w["cod"]: w for pav in ("T", "S") for w in pt.paredes(pj, pav)}
    out = {}
    for p in paineis:
        serv = [dict(servico="eletrica", d=D_ELETRODUTO, z=Z_ELETRICA)]
        x0, y0 = p.x, p.y
        x1, y1 = (p.x + p.comp, p.y) if p.horizontal else (p.x, p.y + p.comp)
        for cod in agua_par:
            w = paredes.get(cod)
            if not w or w["cod"][1] != p.pav:
                continue
            a0, b0, a1, b1 = _seg(w)
            if p.horizontal and w["horizontal"] and abs(y0 - b0) <= TOL and min(x1, a1) - max(x0, a0) > 0:
                serv.append(dict(servico="hidraulica", d=FURO_HIDRAULICO, z=Z_AGUA)); break
            if not p.horizontal and not w["horizontal"] and abs(x0 - a0) <= TOL and min(y1, b1) - max(y0, b0) > 0:
                serv.append(dict(servico="hidraulica", d=FURO_HIDRAULICO, z=Z_AGUA)); break
        out[p.cod] = serv
    return out


def comprimentos_eletrica(pj) -> dict:
    """Por circuito: o percurso ate o ponto MAIS LONGE (manda na queda) e a
    arvore (manda no material)."""
    return {g["circuito"]: dict(mais_longe_mm=g["mais_longe_mm"], arvore_mm=g["arvore_mm"]) for g in arvores_eletrica(pj)}


def comprimentos_agua(pj) -> dict:
    return {r["cod"]: r["comp_mm"] for r in agua(pj)}


def resumo(pj) -> dict:
    el, ag, es, fr = eletrica(pj), agua(pj), esgoto(pj), frigorigena(pj)
    ae, aa = arvores_eletrica(pj), arvores_agua(pj)
    f = fixadores(pj)
    return dict(pontos_eletricos=len(el), circuitos=len(ae), eletroduto_m=round(sum(g["arvore_mm"] for g in ae) / 1000, 1),
                pex_m=round(sum(g["arvore_mm"] for g in aa) / 1000, 1), esgoto_m=round(sum(r["comp_mm"] for r in es) / 1000, 1),
                frigorigena_m=round(sum(r["comp_mm"] for r in fr) / 1000, 1),
                montantes_eletrica=sum(g["montantes"] for g in ae),
                montantes_agua=sum(g["montantes"] for g in aa),
                paredes_com_agua=len({t["parede"] for r in ag for t in r["trechos"] if t["plano"] == "parede" and t["parede"]}),
                paredes_ocupadas=len(por_parede(pj)), fixadores=int(sum(v["qtd"] for k, v in f.items() if v["un"] == "un")),
                caixas=int(sum(v["qtd"] for k, v in f.items() if k.startswith("caixa"))),
                mais_longo=max(el, key=lambda r: r["comp_mm"])["cod"], mais_longo_m=round(max(r["comp_mm"] for r in el) / 1000, 1))


def conferir(pj) -> list[tuple[str, str, bool]]:
    out = []
    el, ag, es = eletrica(pj), agua(pj), esgoto(pj)
    sem = [r["cod"] for r in el if any(t["parede"] == "?" for t in r["trechos"])]
    out.append(("todo ponto eletrico alcancado pelo grafo das paredes", ", ".join(sem[:6]) if sem else f"{len(el)} pontos", not sem))
    sem = [r["cod"] for r in ag if any(t["parede"] == "?" for t in r["trechos"])]
    out.append(("toda peca de agua alcancada pela parede", ", ".join(sem[:6]) if sem else f"{len(ag)} pecas", not sem))
    import nucleo.circuitos as ci
    longos = [(r["cod"], r["queda_pct"]) for r in ci.circuitos(pj) if r["queda_pct"] > ci.QUEDA_MAX]
    out.append(("queda de tensao com o percurso real", ", ".join(f"{c} {q:.1f} %" for c, q in longos) if longos else
                f"maxima {max(r['queda_pct'] for r in ci.circuitos(pj)):.2f} % (limite {ci.QUEDA_MAX} %)", not longos))
    import nucleo.agua as agm
    ruins = [p["cod"] for p in agm.pecas(pj) if not p["ok"]]
    out.append(("pressao com o percurso real", ", ".join(ruins) if ruins else "todas as pecas atendidas (gravidade ou TC-14)", not ruins))
    grandes = [f"{r['cod']} DN{r['dn']}" for r in es if any(t["plano"] == "parede" for t in r["trechos"])]
    out.append(("esgoto nunca em montante", ", ".join(grandes) if grandes else f"{len(es)} ramais sob o piso; so a prumada e vertical", not grandes))
    from nucleo.peca import DIAM_MAX_ALMA
    alma = 90.0
    out.append(("furo hidraulico cabe na alma", f"{FURO_HIDRAULICO} mm contra {DIAM_MAX_ALMA * alma:.0f} (meia alma de 90)", FURO_HIDRAULICO <= DIAM_MAX_ALMA * alma))
    out.append(("furos eletrico e hidraulico afastados", f"{Z_ELETRICA - Z_AGUA} mm entre eixos (minimo um diametro)", Z_ELETRICA - Z_AGUA >= FURO_HIDRAULICO))
    cx = sum(g["caixas_passagem"] for g in arvores_eletrica(pj))
    out.append(("caixa de passagem onde a norma pede", f"{cx} caixas (15 m ou 3 curvas, NBR 5410 6.2.11)", True))
    return out
