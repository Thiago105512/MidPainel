"""VENTILACAO NATURAL E PRIVACIDADE — janela a janela, do caso (R69).

Dois estudos que a lista de entregaveis pedia (itens 16, 17 e 25) e que o
modelo tinha os dados para fazer sem ter feito:

VENTILACAO. Em Manaus (ZB8) a NBR 15220-3 pede aberturas GRANDES para
ventilacao — mais de 40 % da area de piso — e a NBR 15575-4 exige, para a
regiao Norte, area de ventilacao de pelo menos 8 % do piso em dormitorio e
sala. Sao dois criterios de natureza diferente: o primeiro e recomendacao
bioclimatica, o segundo e requisito minimo. O estudo calcula os dois por
ambiente, e diz se o ambiente tem aberturas em faces distintas (cruzada) ou
numa face so (unilateral). Abertura de ventilacao e a parte da esquadria que
ABRE: porta-balcao e cortina abrem inteiras; janela de correr abre metade;
basculante abre um terco. As fracoes sao (H) por familia.

PRIVACIDADE. O Codigo Civil (art. 1.301) proibe janela a menos de 1,50 m da
divisa quando a visao incide sobre ela, e a menos de 0,75 m quando e
perpendicular. E regra legal, nao gosto. O estudo mede cada janela externa
contra a divisa que ela olha, registra o brise que a protege, e classifica.
"""
from __future__ import annotations

# fracao da esquadria que abre para ventilar, por prefixo de familia (H)
FRACAO_ABERTURA = {"CV": 1.0, "PV": 1.0, "J05": 0.5, "J01": 0.5, "J02": 0.5,
                   "J03": 0.5, "J04": 0.33, "P": 0.0, "PG": 0.0}
MINIMO_15575 = 0.08          # regiao Norte: area de ventilacao / area de piso
GRANDE_15220 = 0.40          # ZB8: "aberturas grandes"
DIVISA_FRONTAL = 1_500       # mm, art. 1.301 caput
DIVISA_PERPENDICULAR = 750   # mm, art. 1.301 par. 1
OLHO_VIZINHO = 1_600         # mm: peitoril acima disso nao expoe quem esta dentro


def _fracao(tipo: str) -> float:
    for k in sorted(FRACAO_ABERTURA, key=len, reverse=True):
        if tipo.startswith(k):
            return FRACAO_ABERTURA[k]
    return 0.0


def aberturas(pj) -> list[dict]:
    """Toda esquadria externa, com face, ambiente e area que abre."""
    out = []
    for tipo, x, y, ori, pav in pj.VAOS:
        if not pj.vao_externo(x, y, ori, pav):
            continue
        lg, al, pe, desc = pj.ESQUADRIAS[tipo]
        face = pj.face_do_vao(x, y, ori, pav)
        amb = pj.amb_do_vao(x, y, pav)
        out.append(dict(tipo=tipo, x=x, y=y, ori=ori, pav=pav, face=face, amb=amb,
                        larg=lg, alt=al, peitoril=pe, area=lg * al / 1e6,
                        fracao=_fracao(tipo), abre=lg * al / 1e6 * _fracao(tipo)))
    return out


def _faces_externas(pj, a) -> set:
    """Faces do ambiente sem ambiente fechado do outro lado — a mesma regra de
    projeto.paredes_externas_m2, para que a area util desconte a parede certa."""
    ambs = pj.TERREO if a.pav == "T" else pj.SUPERIOR
    def dentro(px, py):
        return any(q.x <= px < q.x + q.w and q.y <= py < q.y + q.h for q in ambs)
    ext = set()
    if not dentro(a.x + a.w / 2, a.y - 300): ext.add("L")
    if not dentro(a.x + a.w / 2, a.y + a.h + 300): ext.add("O")
    if not dentro(a.x - 300, a.y + a.h / 2): ext.add("S")
    if not dentro(a.x + a.w + 300, a.y + a.h / 2): ext.add("N")
    return ext


def volumes(pj) -> list[list[str]]:
    """Grupos de ambientes que sao um ar so: VOLUME_CONTINUO_SOCIAL e os `mais`
    da climatizacao. Ambiente fora de grupo e grupo de um."""
    grupos = [list(getattr(pj, "VOLUME_CONTINUO_SOCIAL", []))]
    for c in pj.CLIMATIZACAO:
        if c.get("mais"):
            grupos.append([c["amb"]] + list(c["mais"]))
    # une grupos que compartilham ambiente
    fundidos = []
    for g in grupos:
        g = set(g)
        for f in fundidos:
            if f & g:
                f |= g; break
        else:
            fundidos.append(g)
    cobertos = set().union(*fundidos) if fundidos else set()
    for a in pj.TERREO + pj.SUPERIOR:
        if a.cod not in cobertos:
            fundidos.append({a.cod})
    return [sorted(g) for g in fundidos]


def por_ambiente(pj) -> list[dict]:
    """Ventilacao por ambiente: area que abre, fracao do piso, faces, cruzada.

    A NBR 15575-4 fala em area de piso do AMBIENTE; onde nao ha parede entre
    dois ambientes (VOLUME_CONTINUO_SOCIAL), o ar e um so e a conta e do
    volume. Cada ambiente do volume herda o resultado, marcado.
    """
    ab = aberturas(pj)
    todos = {a.cod: a for a in pj.TERREO + pj.SUPERIOR}
    out = []
    for grupo in volumes(pj):
        ambs = [todos[c] for c in grupo if c in todos]
        mine = [v for v in ab if v["amb"] in grupo]
        piso = sum(a.area_util(_faces_externas(pj, a)) for a in ambs)
        abre = sum(v["abre"] for v in mine)
        faces = sorted(set(v["face"] for v in mine if v["abre"] > 0))
        fr = abre / piso if piso else 0.0
        for a in ambs:
            cat = pj.CATEGORIA.get(a.cod, "apoio")
            exige = cat in ("intimo", "social")
            out.append(dict(cod=a.cod, nome=a.nome, pav=a.pav, categoria=cat,
                            volume=grupo if len(grupo) > 1 else None,
                            piso_m2=round(piso, 2), abre_m2=round(abre, 2),
                            fracao=round(fr, 3), faces=faces, n_faces=len(faces),
                            cruzada=len(faces) >= 2, exige_minimo=exige,
                            atende_15575=(fr >= MINIMO_15575) if (piso and exige) else None,
                            grande_15220=fr >= GRANDE_15220,
                            vaos=[v["tipo"] for v in mine]))
    ordem = {a.cod: i for i, a in enumerate(pj.TERREO + pj.SUPERIOR)}
    return sorted(out, key=lambda r: ordem[r["cod"]])


def privacidade(pj) -> list[dict]:
    """Cada janela externa contra a divisa que ela olha (art. 1.301 CC)."""
    brises = {b["face"]: b for b in pj.BRISES}
    out = []
    for v in aberturas(pj):
        if v["tipo"].startswith(("P", "PG")) and not v["tipo"].startswith("PV"):
            continue                              # porta opaca nao e janela
        f = v["face"]
        # distancia da janela a divisa para a qual a face olha
        if f == "S":
            dist = v["x"]
        elif f == "N":
            dist = pj.LOTE_L - v["x"]
        elif f == "L":
            dist = v["y"]                         # testada: rua, nao vizinho
        else:
            dist = pj.LOTE_P - v["y"]
        vizinho = f in ("S", "N", "O")            # leste e a rua
        minimo = DIVISA_FRONTAL                   # a janela olha a divisa
        brise = next((b["cod"] for b in pj.BRISES
                      if b["face"] == f and b.get("pav", "T") == v["pav"]
                      and b["x"] - 50 <= (v["x"] if f in ("L", "O") else v["y"]) <= b["x"] + b["w"] + 50),
                     None)
        alto = v["peitoril"] >= OLHO_VIZINHO
        legal = (not vizinho) or dist >= minimo
        exposta = vizinho and dist < 3_000 and not alto and not brise
        out.append(dict(tipo=v["tipo"], amb=v["amb"], pav=v["pav"], face=f,
                        distancia_divisa=dist, minimo_legal=minimo if vizinho else 0,
                        legal=legal, vizinho=vizinho, peitoril=v["peitoril"],
                        brise=brise, exposta=exposta,
                        leitura=("rua" if not vizinho else
                                 "protegida por brise" if brise else
                                 "peitoril alto" if alto else
                                 "exposta ao vizinho" if exposta else "distante")))
    return out


def conferir(pj) -> list[tuple[str, str, bool]]:
    out = []
    for r in por_ambiente(pj):
        if r["exige_minimo"]:
            out.append((f"ventilacao {r['cod']}",
                        f"{r['abre_m2']:.2f} m2 abrem para {r['piso_m2']:.2f} m2 de piso "
                        f"({r['fracao'] * 100:.0f} %, minimo {MINIMO_15575 * 100:.0f} %), "
                        f"faces {','.join(r['faces']) or 'nenhuma'}",
                        bool(r["atende_15575"])))
    for p in privacidade(pj):
        if p["vizinho"]:
            out.append((f"divisa {p['tipo']} em {p['amb']} face {p['face']}",
                        f"{p['distancia_divisa'] / 1000:.2f} m da divisa "
                        f"(minimo {p['minimo_legal'] / 1000:.2f} m), {p['leitura']}",
                        p["legal"]))
    return out
