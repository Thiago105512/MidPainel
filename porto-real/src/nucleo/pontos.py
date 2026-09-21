"""PONTOS — cada tomada, interruptor, luminaria, TUE e peca com coordenada (R80).

Ate R79 a eletrica sabia QUANTAS tomadas cada ambiente tem (NBR 5410 9.5.2.2,
pelo perimetro e pela bancada) e a PR-27 as espalhava pelo perimetro so para
ilustrar. O eletricista decidia onde. Aqui cada ponto ganha x, y, z e a
parede em que esta, derivado do que o caso ja declara:

  TOMADAS. Primeiro as de bancada (uma a cada TUG_PASSO_BANCADA, a 1.100 mm,
  na parede atras da bancada), a da TV (LAYOUT, a 1.300 mm) e a do lavatorio
  (a 1.100 mm, 350 mm ao lado da cuba, fora da zona 1 do box). O que sobra da
  previsao vai para o perimetro a 300 mm, em passo igual, pulando portas,
  janelas e as subdivisoes (o banho da suite nao recebe a tomada do quarto).
  INTERRUPTORES. Um por porta, do lado da fechadura, a 300 mm do batente e
  1.100 mm do piso, dentro do ambiente que a porta serve; dormitorio ganha
  paralelo na cabeceira (LAYOUT cama). Subdivisao com porta ganha o seu.
  LUMINARIAS. As da luminotecnica (PR-16), no forro.
  TUE. Cada carga especial no equipamento: chuveiro no box, split na parede
  mais perto do seu nicho, secadora ao lado da lavadora, forno e micro-ondas
  na bancada de coccao, bombas nos elementos tecnicos, ventiladores no forro.
  AGUA E ESGOTO. As pecas hidraulicas e os ralos, com a altura da peca.
Tudo com a parede em que esta: e ela que o percurso (nucleo/percurso) usa.
"""
from __future__ import annotations

import math

# ------------------------------------------------------------------ (H) alturas
Z_TUG = 300
Z_TUG_BANCADA = 1_100
Z_TUG_LAVATORIO = 1_100
Z_TV = 1_300
Z_INTERRUPTOR = 1_100
Z_PARALELO = 700
Z_SPLIT = 2_200
Z_EXAUSTOR = 2_200
Z_FORNO = 1_100
Z_TUE_PISO = 300
AFAST_VAO = 300            # do batente ate o interruptor / da tomada ate o vao
AFAST_CANTO = 400
AFAST_LAVATORIO = 350
ZONA1_BOX = 600            # NBR 5410 zona 1: sem tomada a menos de 600 mm do box
RECUO_FACE = 60            # o ponto fica 60 mm para dentro da face da parede
TOL = 80


def _pav_de(cod: str) -> str:
    return "S" if cod.startswith("S-") else "T"


def _ambs_pt(pj):
    return list(pj.TERREO) + list(pj.SUPERIOR)


def _amb_pt(pj, cod):
    """Ambiente fechado ou aberto (varanda com ventilador, deck com ducha)."""
    return next(a for a in _ambs_pt(pj) + list(pj.TERREO_ABERTO) + list(pj.SUPERIOR_ABERTO) if a.cod == cod)


def paredes(pj, pav: str) -> list[dict]:
    """Paredes do pavimento (com as subdivisoes), cada uma com um codigo."""
    import nucleo.detalhes_lsf as dl
    out = []
    for i, p in enumerate(dl._paredes_com_subdivisoes(pj, pav)):
        out.append(dict(cod=f"W{pav}-{i + 1:02d}", x1=p.x1, y1=p.y1, x2=p.x2, y2=p.y2, esp=p.esp,
                        externa=p.externa, horizontal=(p.y1 == p.y2), comp=abs(p.x2 - p.x1) + abs(p.y2 - p.y1)))
    return out


def parede_de(pj, pav: str, x: float, y: float, tol: float = TOL) -> dict | None:
    """A parede mais proxima do ponto, se estiver a menos de `tol`."""
    melhor, dm = None, tol + 1
    for w in paredes(pj, pav):
        if w["horizontal"]:
            d = abs(y - w["y1"]) if min(w["x1"], w["x2"]) - tol <= x <= max(w["x1"], w["x2"]) + tol else 1e9
        else:
            d = abs(x - w["x1"]) if min(w["y1"], w["y2"]) - tol <= y <= max(w["y1"], w["y2"]) + tol else 1e9
        if d < dm:
            melhor, dm = w, d
    return melhor


def _lados(a):
    """Os quatro lados do retangulo, no sentido horario a partir do canto (x, y)."""
    x, y, w, h = a.x, a.y, a.w, a.h
    return [("leste", (x, y), (x + w, y)), ("norte", (x + w, y), (x + w, y + h)),
            ("oeste", (x + w, y + h), (x, y + h)), ("sul", (x, y + h), (x, y))]


def _vaos(pj, pav: str) -> list[dict]:
    import elementos as el
    return list(el.vaos_do_pavimento(pav))


def _intervalos_ocupados(pj, pav: str, a, lado) -> list[tuple[float, float]]:
    """Trechos do lado (em coordenada ao longo dele) tomados por vaos ou subdivisoes."""
    nome, p0, p1 = lado
    hz = p0[1] == p1[1]
    ocup = []
    for v in _vaos(pj, pav):
        if hz and v["ori"] == "H" and abs(v["y"] - p0[1]) <= TOL:
            ocup.append((v["x"] - v["larg"] / 2 - AFAST_VAO, v["x"] + v["larg"] / 2 + AFAST_VAO))
        elif not hz and v["ori"] == "V" and abs(v["x"] - p0[0]) <= TOL:
            ocup.append((v["y"] - v["larg"] / 2 - AFAST_VAO, v["y"] + v["larg"] / 2 + AFAST_VAO))
    for s in pj.SUBDIVISOES:
        if s["pai"] != a.cod:
            continue
        # o lado do pai que coincide com a borda da subdivisao e parede DELA por dentro
        if hz and (abs(s["y"] - p0[1]) <= TOL or abs(s["y"] + s["h"] - p0[1]) <= TOL):
            ocup.append((s["x"], s["x"] + s["w"]))
        if not hz and (abs(s["x"] - p0[0]) <= TOL or abs(s["x"] + s["w"] - p0[0]) <= TOL):
            ocup.append((s["y"], s["y"] + s["h"]))
    return ocup


def _ponto_no_lado(lado, t: float, recuo: float = RECUO_FACE) -> tuple[float, float]:
    nome, p0, p1 = lado
    x = p0[0] + (p1[0] - p0[0]) * t
    y = p0[1] + (p1[1] - p0[1]) * t
    if nome == "leste":
        y += recuo
    elif nome == "oeste":
        y -= recuo
    elif nome == "norte":
        x -= recuo
    else:
        x += recuo
    return x, y


def _ponto_em_subdivisao(pj, cod_amb: str, x: float, y: float) -> bool:
    return any(s["pai"] == cod_amb and s["x"] < x < s["x"] + s["w"] and s["y"] < y < s["y"] + s["h"] for s in pj.SUBDIVISOES)


_OPOSTO = {"leste": "oeste", "oeste": "leste", "norte": "sul", "sul": "norte"}


def _lados_uteis(pj, a) -> list[tuple]:
    """Lados do ambiente que TEM parede (a cozinha abre para o gourmet sem parede),
    mais as faces das subdivisoes voltadas para o ambiente (a parede do banho da
    suite, vista do quarto, recebe tomada do quarto)."""
    pav = getattr(a, "pav", None) or _pav_de(a.cod)
    out = []
    for nome, p0, p1 in _lados(a):
        m = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
        if parede_de(pj, pav, *m) is not None:
            out.append((nome, p0, p1))
    if "/" in a.cod:
        return out
    for s in pj.SUBDIVISOES:
        if s["pai"] != a.cod:
            continue
        class R: pass
        r = R(); r.x, r.y, r.w, r.h = s["x"], s["y"], s["w"], s["h"]
        for nome, p0, p1 in _lados(r):
            m = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
            # face que coincide com o contorno do pai nao olha para o quarto
            if any(_dist_seg(m, l[1], l[2]) <= TOL for l in _lados(a)):
                continue
            if parede_de(pj, pav, *m) is None:
                continue
            out.append((_OPOSTO[nome], p1, p0))
    return out


def _lado_mais_proximo(a, x, y, pj=None):
    lados = _lados_uteis(pj, a) if pj is not None else _lados(a)
    if not lados:
        lados = _lados(a)
    return min(lados, key=lambda l: _dist_seg((x, y), l[1], l[2]))


def _dist_seg(p, a, b) -> float:
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _projetar(lado, x, y) -> float:
    """Parametro t (0..1) da projecao do ponto no lado."""
    nome, p0, p1 = lado
    if p0[1] == p1[1]:
        return (x - p0[0]) / (p1[0] - p0[0])
    return (y - p0[1]) / (p1[1] - p0[1])


def _rect_de(pj, cod: str):
    """Retangulo de um ambiente ou de uma subdivisao 'PAI/NOME'."""
    if "/" in cod:
        pai, nome = cod.split("/")
        s = next(s for s in pj.SUBDIVISOES if s["pai"] == pai and s["nome"] == nome)
        class R: pass
        r = R(); r.cod = cod; r.x, r.y, r.w, r.h = s["x"], s["y"], s["w"], s["h"]
        return r
    return _amb_pt(pj, cod)


def _subdivisao_de(pj, cod_amb: str, x: float, y: float) -> str | None:
    for s in pj.SUBDIVISOES:
        if s["pai"] == cod_amb and s["x"] <= x <= s["x"] + s["w"] and s["y"] <= y <= s["y"] + s["h"]:
            return f"{cod_amb}/{s['nome']}"
    return None


# ================================================================== tomadas
def tomadas(pj) -> list[dict]:
    prev = {p["amb"]: p for p in pj.previsao_iluminacao_tug()}
    pecas = pj.pecas_hidraulicas()
    out = []
    for a in _ambs_pt(pj):
        if a.cod not in prev:
            continue
        pav = a.pav
        n = prev[a.cod]["tugs"]
        pts = []
        # 1) bancadas
        for bc in pj.BANCADAS:
            if bc["amb"] != a.cod:
                continue
            lado = _lado_mais_proximo(a, bc["x"] + bc["w"] / 2, bc["y"] + bc["h"] / 2, pj)
            comp = max(bc["w"], bc["h"])
            k = max(1, math.ceil(comp / pj.TUG_PASSO_BANCADA))
            for i in range(k):
                if bc["w"] >= bc["h"]:
                    px, py = bc["x"] + bc["w"] * (i + 0.5) / k, bc["y"] + bc["h"] / 2
                else:
                    px, py = bc["x"] + bc["w"] / 2, bc["y"] + bc["h"] * (i + 0.5) / k
                x, y = _ponto_no_lado(lado, _projetar(lado, px, py))
                pts.append(dict(x=x, y=y, z=Z_TUG_BANCADA, uso=f"bancada {bc['cod']}", lado=lado[0]))
        # 2) TV
        for it in pj.LAYOUT:
            if it["amb"] == a.cod and it["tipo"] == "tv":
                lado = _lado_mais_proximo(a, it["x"] + it["w"] / 2, it["y"] + it["h"] / 2, pj)
                x, y = _ponto_no_lado(lado, _projetar(lado, it["x"] + it["w"] / 2, it["y"] + it["h"] / 2))
                pts.append(dict(x=x, y=y, z=Z_TV, uso="TV", lado=lado[0]))
        # 3) lavatorio: 350 mm ao lado, a 1.100, na parede do proprio recinto (subdivisao ou ambiente)
        for p in pecas:
            if p["amb"] == a.cod and p["tipo"] == "lavatorio":
                rec = _rect_de(pj, _subdivisao_de(pj, a.cod, p["x"], p["y"]) or a.cod)
                lado = _lado_mais_proximo(rec, p["x"], p["y"], pj)
                t = _projetar(lado, p["x"], p["y"])
                comp = abs(lado[2][0] - lado[1][0]) + abs(lado[2][1] - lado[1][1])
                t2 = t + AFAST_LAVATORIO / comp if t < 0.5 else t - AFAST_LAVATORIO / comp
                x, y = _ponto_no_lado(lado, min(max(t2, AFAST_CANTO / comp), 1 - AFAST_CANTO / comp))
                box = next((q for q in pecas if q["amb"] == a.cod and q["tipo"] == "box"), None)
                if box and math.hypot(box["x"] - x, box["y"] - y) < ZONA1_BOX:
                    t2 = t - AFAST_LAVATORIO / comp if t < 0.5 else t + AFAST_LAVATORIO / comp
                    x, y = _ponto_no_lado(lado, min(max(t2, AFAST_CANTO / comp), 1 - AFAST_CANTO / comp))
                pts.append(dict(x=x, y=y, z=Z_TUG_LAVATORIO, uso=f"lavatorio {p['cod']}", lado=lado[0], sub=rec.cod if "/" in rec.cod else None))
        # 4) o resto pelo perimetro, pulando vaos e subdivisoes
        resto = n - len(pts)
        if resto > 0:
            lados = _lados_uteis(pj, a)
            comps = [abs(l[2][0] - l[1][0]) + abs(l[2][1] - l[1][1]) for l in lados]
            per = sum(comps)
            ocup = [_intervalos_ocupados(pj, pav, a, l) for l in lados]
            passo = per / resto
            s = passo / 2
            colocados = 0
            andado = 0.0
            while colocados < resto and andado < 3 * per:
                sm = s % per
                acc = 0.0
                for k, l in enumerate(lados):
                    comp = comps[k]
                    if sm <= acc + comp:
                        t = (sm - acc) / comp
                        coord = l[1][0] + (l[2][0] - l[1][0]) * t if l[1][1] == l[2][1] else l[1][1] + (l[2][1] - l[1][1]) * t
                        livre = all(not (i0 <= coord <= i1) for i0, i1 in ocup[k]) and AFAST_CANTO <= t * comp <= comp - AFAST_CANTO
                        x, y = _ponto_no_lado(l, t)
                        ja = any(abs(q["x"] - x) + abs(q["y"] - y) < 300 for q in pts)
                        # o lado pode ter parede so em parte (corredor integrado ao hall):
                        # o ponto precisa de parede ONDE ele esta
                        if livre and not ja and not _ponto_em_subdivisao(pj, a.cod, x, y) and parede_de(pj, pav, x, y) is not None:
                            pts.append(dict(x=x, y=y, z=Z_TUG, uso="geral", lado=l[0]))
                            colocados += 1
                            s += passo; andado += passo
                        else:
                            s += 250; andado += 250
                        break
                    acc += comp
        # parede acabou antes da previsao (cozinha com uma parede so, gourmet
        # aberto para o estar): as tomadas restantes viram DUPLAS nos pontos
        # de bancada e depois nos gerais — a norma conta tomadas, nao caixas
        for p in pts:
            p["n"] = 1
        faltam = n - len(pts)
        for p in sorted(pts, key=lambda q: (0 if q["uso"].startswith("bancada") else 1)):
            if faltam <= 0:
                break
            p["n"] = 2; faltam -= 1
        for i, p in enumerate(pts, 1):
            w = parede_de(pj, pav, p["x"], p["y"])
            out.append(dict(cod=f"TUG-{a.cod}-{i}", amb=a.cod, pav=pav, x=round(p["x"]), y=round(p["y"]), z=p["z"],
                            uso=p["uso"], lado=p["lado"], parede=w["cod"] if w else None, circuito=f"TUG-{a.cod}",
                            sub=p.get("sub"), previstas=n, n=p["n"]))
    return out


# ================================================================== interruptores
def interruptores(pj) -> list[dict]:
    out = []
    ambs = _ambs_pt(pj)
    for pav in ("T", "S"):
        for v in _vaos(pj, pav):
            if not v["tipo"].startswith("P") or v["tipo"].startswith("PG"):
                continue
            # todo ambiente cujo contorno passa pela porta recebe um interruptor do lado de dentro
            for a in ambs:
                if a.pav != pav:
                    continue
                lado = next((l for l in _lados(a) if _dist_seg((v["x"], v["y"]), l[1], l[2]) <= TOL), None)
                if lado is None:
                    continue
                comp = abs(lado[2][0] - lado[1][0]) + abs(lado[2][1] - lado[1][1])
                t = _projetar(lado, v["x"], v["y"])
                # lado da fechadura: o lado do vao mais longe do canto mais proximo
                dt = (v["larg"] / 2 + AFAST_VAO) / comp
                t2 = t + dt if t < 0.5 else t - dt
                if not (AFAST_CANTO / comp <= t2 <= 1 - AFAST_CANTO / comp):
                    t2 = t - dt if t < 0.5 else t + dt
                x, y = _ponto_no_lado(lado, t2)
                if not (AFAST_CANTO / comp <= t2 <= 1 - AFAST_CANTO / comp) or parede_de(pj, pav, x, y) is None:
                    # a parede da porta e curta demais (despensa de 1,2 m com porta de 0,9):
                    # o interruptor vai para a parede adjacente, a 400 mm do canto da porta
                    outros = [l for l in _lados_uteis(pj, a) if l[0] != lado[0]]
                    if not outros:
                        continue
                    l2 = min(outros, key=lambda l: min(math.hypot(l[1][0] - v["x"], l[1][1] - v["y"]), math.hypot(l[2][0] - v["x"], l[2][1] - v["y"])))
                    c2 = abs(l2[2][0] - l2[1][0]) + abs(l2[2][1] - l2[1][1])
                    perto_p0 = math.hypot(l2[1][0] - v["x"], l2[1][1] - v["y"]) < math.hypot(l2[2][0] - v["x"], l2[2][1] - v["y"])
                    x, y = _ponto_no_lado(l2, AFAST_CANTO / c2 if perto_p0 else 1 - AFAST_CANTO / c2)
                if _ponto_em_subdivisao(pj, a.cod, x, y):
                    continue
                w = parede_de(pj, pav, x, y)
                out.append(dict(cod=f"INT-{a.cod}-{v['tipo']}", amb=a.cod, pav=pav, x=round(x), y=round(y), z=Z_INTERRUPTOR,
                                tipo="simples", porta=v["tipo"], parede=w["cod"] if w else None, circuito=f"ILU-{a.cod}"))
        # subdivisoes com porta: interruptor dentro, ao lado da porta
        for s in pj.SUBDIVISOES:
            if _pav_de(s["pai"]) != pav or not s.get("vao"):
                continue
            rec = _rect_de(pj, f"{s['pai']}/{s['nome']}")
            face = {"N": "norte", "S": "sul", "L": "leste", "O": "oeste"}[s["face"]]
            lado = next(l for l in _lados(rec) if l[0] == face)
            comp = abs(lado[2][0] - lado[1][0]) + abs(lado[2][1] - lado[1][1])
            t = _projetar(lado, *((s["x"] + s["w"] / 2, s["pos"]) if face in ("norte", "sul") else (s["pos"], s["y"] + s["h"] / 2)))
            dt = (s["vao"] / 2 + AFAST_VAO) / comp
            t2 = t + dt if t < 0.5 else t - dt
            t2 = min(max(t2, AFAST_CANTO / comp), 1 - AFAST_CANTO / comp)
            x, y = _ponto_no_lado(lado, t2)
            w = parede_de(pj, pav, x, y)
            out.append(dict(cod=f"INT-{s['pai']}-{s['nome']}", amb=s["pai"], pav=pav, x=round(x), y=round(y), z=Z_INTERRUPTOR,
                            tipo="simples", porta=f"{s['nome']} ({s['vao']})", parede=w["cod"] if w else None,
                            circuito=f"ILU-{s['pai']}", sub=f"{s['pai']}/{s['nome']}"))
    # paralelo na cabeceira dos dormitorios
    for it in pj.LAYOUT:
        if it["tipo"] != "cama":
            continue
        a = _amb_pt(pj, it["amb"])
        lado = _lado_mais_proximo(a, it["x"] + it["w"] / 2, it["y"] + it["h"] / 2, pj)
        x, y = _ponto_no_lado(lado, _projetar(lado, it["x"] + it["w"] / 2, it["y"] + it["h"] / 2))
        w = parede_de(pj, a.pav, x, y)
        out.append(dict(cod=f"INT-{a.cod}-PAR", amb=a.cod, pav=a.pav, x=round(x), y=round(y), z=Z_PARALELO,
                        tipo="paralelo", porta="cabeceira", parede=w["cod"] if w else None, circuito=f"ILU-{a.cod}"))
    return out


# ================================================================== luminarias
def luminarias(pj) -> list[dict]:
    import nucleo.luminotecnica as lm
    out = []
    ambs = _ambs_pt(pj)
    for i, q in enumerate(lm.pontos(pj), 1):
        if "seg" in q:
            x0, y0, x1, y1 = q["seg"]
            x, y = (x0 + x1) / 2, (y0 + y1) / 2
        else:
            x, y = q["p"]
        amb = q["cod"].split("/")[0] if q["cod"] in {a.cod for a in ambs} or "/" in q["cod"] else None
        if amb is None:
            amb = next((a.cod for a in ambs if a.pav == q["pav"] and a.x <= x <= a.x + a.w and a.y <= y <= a.y + a.h), None)
        out.append(dict(cod=f"LUM-{i:03d}", ref=q["cod"], amb=amb, pav=q["pav"], x=round(x), y=round(y), z=q["z"],
                        tipo=q["tipo"], circuito=f"ILU-{amb}" if amb else None, no_forro=q["tipo"] != "arandela"))
    return out


# ================================================================== TUE
def tue(pj) -> list[dict]:
    import nucleo.circuitos as ci
    pecas = pj.pecas_hidraulicas()
    tc = {t["cod"]: t for t in pj.TECNICOS}
    out = []

    def centro_tc(cod):
        t = tc[cod]
        return t["x"] + t["w"] / 2, t["y"] + t["h"] / 2

    def na_parede(a, px, py, z, desloc=0):
        lado = _lado_mais_proximo(a, px, py, pj)
        comp = abs(lado[2][0] - lado[1][0]) + abs(lado[2][1] - lado[1][1])
        t = _projetar(lado, px, py) + desloc / comp
        x, y = _ponto_no_lado(lado, min(max(t, 0.1), 0.9))
        return dict(x=x, y=y, z=z, lado=lado[0])

    for c in pj.CARGAS_ESPECIAIS:
        if c.get("reserva"):
            continue
        d = c["desc"].lower()
        amb = ci._amb_de(c)
        pts = []
        if "chuveiro" in d:
            box = next((p for p in pecas if p["amb"] == amb and p["tipo"] == "box"), None)
            if box:
                a = _rect_de(pj, _subdivisao_de(pj, amb, box["x"], box["y"]) or amb)
                pts.append(na_parede(a, box["x"], box["y"], pj.ALTURA_CHUVEIRO + 100) | dict(onde="box"))
        elif "split duto" in d:
            a = _amb_pt(pj, "T-SOC")
            pts.append(dict(x=a.x + a.w / 2, y=a.y + a.h / 2, z=pj.PE_DIREITO - 300, lado=None, onde="forro", forro=True))
        elif "split" in d:
            cl = next((k for k in pj.CLIMATIZACAO if k["amb"] == amb), None)
            a = _rect_de(pj, f"{amb}/OFFICE") if "office" in d else _amb_pt(pj, amb)
            if cl and cl.get("nicho") in tc:
                nx, ny = centro_tc(cl["nicho"])
                pts.append(na_parede(a, nx, ny, Z_SPLIT) | dict(onde=f"parede voltada para {cl['nicho']}"))
            else:
                pts.append(na_parede(a, a.x + a.w / 2, a.y, Z_SPLIT) | dict(onde="parede"))
        elif "secadora" in d or "lavadora" in d:
            lv = next((p for p in pecas if p["tipo"] == "lavadora"), None)
            a = _amb_pt(pj, lv["amb"]) if lv else _amb_pt(pj, amb)
            pts.append(na_parede(a, lv["x"], lv["y"], 1_100, 700 if "secadora" in d else 0) | dict(onde="lavanderia"))
            amb = a.cod
        elif "lava-loucas" in d:
            bc = next(b for b in pj.BANCADAS if b["amb"] == "T-COZ" and b["cubas"])
            a = _amb_pt(pj, "T-COZ")
            pts.append(na_parede(a, bc["x"] + bc["w"] / 2, bc["y"] + bc["h"] / 2 + 700, Z_TUE_PISO) | dict(onde=f"sob {bc['cod']}"))
            amb = "T-COZ"
        elif "forno" in d or "micro" in d:
            bc = next(b for b in pj.BANCADAS if b["amb"] == "T-COZ" and b["cooktop"])
            a = _amb_pt(pj, "T-COZ")
            pts.append(na_parede(a, bc["x"] + bc["w"] / 2, bc["y"] + bc["h"] / 2 - (0 if "forno" in d else 600), Z_FORNO if "forno" in d else 1_800)
                       | dict(onde=f"torre junto a {bc['cod']}"))
            amb = "T-COZ"
        elif "recalque" in d:
            x, y = centro_tc("TC-02"); pts.append(dict(x=x, y=y, z=Z_TUE_PISO, lado=None, onde="TC-02", externo=True))
        elif "pressurizador" in d:
            r = __import__("nucleo.agua", fromlist=["reservatorio"]).reservatorio(pj)
            pts.append(dict(x=r["x"], y=r["y"], z=pj.PISO_A_PISO + pj.PE_DIREITO + 300, lado=None, onde="atico, junto a caixa", forro=True))
            amb = "S-MAS"
        elif "piscina" in d:
            x, y = centro_tc("TC-13"); pts.append(dict(x=x, y=y, z=1_200, lado=None, onde="TC-13", externo=True))
        elif "ventilador" in d:
            for vt in pj.VENTILADORES:
                a = _amb_pt(pj, vt["amb"])
                for k in range(vt["qtd"]):
                    pts.append(dict(x=a.x + a.w * (k + 1) / (vt["qtd"] + 1), y=a.y + a.h / 2, z=pj.PE_DIREITO, lado=None,
                                    onde=f"forro {vt['amb']}", forro=True, amb=vt["amb"], sub=vt["cod"]))
        elif "exaust" in d or "coifa" in d:
            for ex in pj.EXAUSTAO:
                a = _amb_pt(pj, ex["amb"])
                bc = next((b for b in pj.BANCADAS if b["amb"] == ex["amb"]), None)
                px, py = (bc["x"] + bc["w"] / 2, bc["y"] + bc["h"] / 2) if bc else (a.x + a.w / 2, a.y + a.h / 2)
                pts.append(na_parede(a, px, py, Z_EXAUSTOR) | dict(onde=f"{ex['cod']} {ex['fonte']}", amb=ex["amb"], sub=ex["cod"]))
        elif "portao" in d:
            pg = pj.ACESSO_TESTADA
            # R83: o portao motorizado e o PG01, na linha da frente da garagem
            pts.append(dict(x=pg["veiculo_x"] + pg["veiculo_larg"] / 2 + 300, y=pj.RECUO_FRENTE + 300, z=Z_TUE_PISO, lado=None, onde="pilar do portao PG01, lado interno da garagem", externo=True))
            amb = "T-GAR"
        elif "rack" in d:
            x, y = centro_tc("TC-07"); pts.append(dict(x=x, y=y, z=Z_TUE_PISO, lado=None, onde="TC-07"))
            amb = "T-GAR"
        elif "carregador" in d:
            x, y = pj.EV_RESERVA["ponto"]; pts.append(dict(x=x, y=y, z=1_200, lado=None, onde="parede da garagem"))
            amb = "T-GAR"
        else:
            a = _amb_pt(pj, amb) if amb else _amb_pt(pj, "T-GAR")
            pts.append(dict(x=a.x + a.w / 2, y=a.y + a.h / 2, z=Z_TUE_PISO, lado=None, onde="centro do ambiente"))
        for k, p in enumerate(pts, 1):
            amb_k = p.get("amb", amb) or "EXT"
            pav = _pav_de(amb_k) if amb_k != "EXT" else "T"
            if p.get("externo"):
                pav = "T"
            w = parede_de(pj, pav, p["x"], p["y"])
            out.append(dict(cod=c["cod"] + (f"/{p['sub']}" if p.get("sub") else (f"/{k}" if len(pts) > 1 else "")),
                            circuito=c["cod"], amb=amb_k, pav=pav, x=round(p["x"]), y=round(p["y"]), z=round(p["z"]),
                            onde=p["onde"], parede=w["cod"] if w else None, forro=bool(p.get("forro")), externo=bool(p.get("externo")),
                            desc=c["desc"], va=c["va"], v=c["v"]))
    return out


# ================================================================== agua e esgoto
def agua(pj) -> list[dict]:
    from nucleo.agua import Z_PECA
    out = []
    for p in pj.pecas_hidraulicas():
        pav = _pav_de(p["amb"])
        rec = _rect_de(pj, _subdivisao_de(pj, p["amb"], p["x"], p["y"]) or p["amb"]) if p["amb"] in {a.cod for a in _ambs_pt(pj)} else None
        if rec is not None:
            lado = _lado_mais_proximo(rec, p["x"], p["y"], pj)
            x, y = _ponto_no_lado(lado, min(max(_projetar(lado, p["x"], p["y"]), 0.05), 0.95))
        else:
            x, y = p["x"], p["y"]
        w = parede_de(pj, pav, x, y)
        out.append(dict(cod=p["cod"], amb=p["amb"], pav=pav, tipo=p["tipo"], x=round(x), y=round(y), z=Z_PECA.get(p["tipo"], 600),
                        quente=p.get("quente", False), parede=w["cod"] if w else None, peca_xy=(p["x"], p["y"]),
                        externo=rec is None))
    return out


def esgoto(pj) -> list[dict]:
    out = []
    for p in pj.pecas_hidraulicas():
        out.append(dict(cod=p["cod"], amb=p["amb"], pav=_pav_de(p["amb"]), tipo=p["tipo"], x=p["x"], y=p["y"], uhc=p["uhc"]))
    for r in pj.RALOS:
        out.append(dict(cod=r["cod"], amb=r["amb"], pav=_pav_de(r["amb"]), tipo=r["tipo"], x=r["x"], y=r["y"], uhc=1, dn=r["dn"]))
    return out


def todos(pj) -> dict:
    return dict(tomadas=tomadas(pj), interruptores=interruptores(pj), luminarias=luminarias(pj), tue=tue(pj),
                agua=agua(pj), esgoto=esgoto(pj))


def resumo(pj) -> dict:
    t = todos(pj)
    return dict(tomadas=len(t["tomadas"]), interruptores=len(t["interruptores"]), luminarias=len(t["luminarias"]),
                tue=len(t["tue"]), agua=len(t["agua"]), esgoto=len(t["esgoto"]),
                bancada=sum(1 for x in t["tomadas"] if x["uso"].startswith("bancada")), duplas=sum(1 for x in t["tomadas"] if x["n"] == 2),
                altas=sum(1 for x in t["tomadas"] if x["z"] >= 1_100), paralelos=sum(1 for x in t["interruptores"] if x["tipo"] == "paralelo"))


def conferir(pj) -> list[tuple[str, str, bool]]:
    out = []
    t = todos(pj)
    prev = {p["amb"]: p for p in pj.previsao_iluminacao_tug()}
    por_amb: dict = {}
    for x in t["tomadas"]:
        por_amb[x["amb"]] = por_amb.get(x["amb"], 0) + x["n"]
    faltam = [f"{a} {por_amb.get(a, 0)}/{p['tugs']}" for a, p in prev.items() if por_amb.get(a, 0) < p["tugs"]]
    duplas = sum(1 for x in t["tomadas"] if x["n"] == 2)
    out.append(("toda tomada prevista tem lugar", ", ".join(faltam) if faltam else
                f"{sum(x['n'] for x in t['tomadas'])} tomadas em {len(t['tomadas'])} pontos ({duplas} duplos) em {len(por_amb)} ambientes", not faltam))
    sem = [x["cod"] for x in t["tomadas"] + t["interruptores"] if not x["parede"]]
    out.append(("tomadas e interruptores numa parede", ", ".join(sem[:6]) if sem else "todos a menos de 80 mm de uma parede", not sem))
    ambs = {a.cod: a for a in _ambs_pt(pj)}
    fora = [x["cod"] for x in t["tomadas"] if not (ambs[x["amb"]].x <= x["x"] <= ambs[x["amb"]].x + ambs[x["amb"]].w
                                                   and ambs[x["amb"]].y <= x["y"] <= ambs[x["amb"]].y + ambs[x["amb"]].h)]
    out.append(("toda tomada dentro do seu ambiente", ", ".join(fora[:6]) if fora else "todas", not fora))
    boxes = [p for p in pj.pecas_hidraulicas() if p["tipo"] == "box"]
    perto = [x["cod"] for x in t["tomadas"] for b in boxes if x["amb"] == b["amb"] and math.hypot(x["x"] - b["x"], x["y"] - b["y"]) < ZONA1_BOX]
    out.append(("nenhuma tomada na zona 1 do box (NBR 5410)", ", ".join(perto) if perto else f"{len(boxes)} boxes conferidos, minimo {ZONA1_BOX} mm", not perto))
    molh = [x["cod"] for x in t["tomadas"] if x["uso"].startswith("lavatorio") and x["z"] < Z_TUG_LAVATORIO]
    out.append(("tomada de lavatorio alta", ", ".join(molh) if molh else f"todas a {Z_TUG_LAVATORIO} mm", not molh))
    portas = {(v["tipo"], v["pav"] if "pav" in v else None) for v in []}
    com_porta = {a.cod for a in _ambs_pt(pj) for v in _vaos(pj, a.pav) if v["tipo"].startswith("P") and not v["tipo"].startswith("PG")
                 and any(_dist_seg((v["x"], v["y"]), l[1], l[2]) <= TOL for l in _lados(a))}
    com_int = {x["amb"] for x in t["interruptores"]}
    sem_int = sorted(com_porta - com_int)
    out.append(("todo ambiente com porta tem interruptor", ", ".join(sem_int) if sem_int else f"{len(com_int)} ambientes", not sem_int))
    dorm = [a.cod for a in _ambs_pt(pj) if pj.CATEGORIA.get(a.cod) == "intimo" and any(i["amb"] == a.cod and i["tipo"] == "cama" for i in pj.LAYOUT)]
    par = {x["amb"] for x in t["interruptores"] if x["tipo"] == "paralelo"}
    out.append(("paralelo na cabeceira de todo dormitorio com cama", ", ".join(sorted(set(dorm) - par)) if set(dorm) - par else f"{len(par)} dormitorios", set(dorm) <= par))
    sem_tue = [x["cod"] for x in t["tue"] if x["x"] is None]
    out.append(("todo TUE com coordenada", f"{len(t['tue'])} pontos de {len([c for c in pj.CARGAS_ESPECIAIS if not c.get('reserva')])} cargas", not sem_tue))
    return out
