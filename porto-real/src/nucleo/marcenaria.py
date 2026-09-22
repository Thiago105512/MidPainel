"""MARCENARIA — cada movel do caso vira modulos, pecas, furacao e ferragem (R71).

Ate R70 a marcenaria era um preco por metro quadrado de frente (MAR-ARM, MAR-GAB)
e uma elevacao desenhada a mao na PR-15. O preco e honesto como estimativa,
mas nao diz o que o marceneiro corta, fura e parafusa. Este modulo diz.

A regra e a mesma do steel frame: o movel nao e desenhado, e DERIVADO. Um
guarda-roupa de 2.400 mm de frente vira 4 modulos de 600, cada modulo vira
duas laterais, base, topo, fundo, prateleira, porta e cabideiro, cada peca
tem dimensao, espessura, fita de borda e furacao, e as pecas de 15 mm entram
num plano de corte de chapa 2.750 x 1.850 pelo mesmo nesting das placas de
fechamento. Se a largura do armario mudar no caso, tudo muda junto.

O que e (H) aqui esta no topo: alturas por familia, a folha de porta maxima
de 600 mm (peso na dobradica e giro na circulacao), o sistema 32 (fileiras a
37 mm da borda, furos de 5 mm a cada 32) e os precos unitarios de material.
O que sai daqui e conferido contra o preco sob medida que o BOM ja carrega:
o material nao pode ser mais que o servico inteiro, nem tao pouco que o
preco por m2 esteja pagando ar.
"""
from __future__ import annotations

import math

# ---- chapa e usinagem (H)
CHAPA = dict(larg=1_850.0, alt=2_750.0)       # MDF BP, medida comercial
ESP = 15                                       # caixa, portas, prateleiras
ESP_FUNDO = 6                                  # fundo encaixado em canal
ESP_TAMPO = 2 * 15                             # tampo de mesa: duas de 15 coladas
SERRA = 4.0                                    # mm por corte de esquadrejadeira
PORTA_MAX = 600                                # folha maxima: peso e giro
GAVETA_ALT = 200                               # frente de gaveta padrao
SISTEMA_32 = dict(passo=32, recuo=37, furo=5, profundidade=13,
                  primeiro=64, cup=35, cup_recuo=22.5, cup_borda=100)
CORREDICAS = (250, 300, 350, 400, 450, 500, 550)   # comprimentos comerciais
RODAPE_GABINETE = 100                          # sapata + rodape recuado
RECUO_RODAPE = 50
TAMPO_GRANITO = 30
BANCADA_ACABADA = 900                          # topo do tampo

# ---- familias: altura, o que tem dentro, como abre (H)
# portas: True = uma porta por modulo; gavetas: por modulo; prat_passo: uma
# prateleira a cada N mm de altura util; cabideiro: tubo no modulo
FAMILIAS = {
    "armario alto":  dict(alt=2_200, portas=True,  gavetas=0, prat_passo=400, cabideiro=False),
    "guarda-roupa":  dict(alt=2_200, portas=True,  gavetas=2, prat_passo=0,   cabideiro=True),
    "rouparia":      dict(alt=2_200, portas=True,  gavetas=0, prat_passo=350, cabideiro=False),
    "prateleiras":   dict(alt=2_200, portas=False, gavetas=0, prat_passo=350, cabideiro=False),
    "gaveteiro":     dict(alt=900,   portas=False, gavetas=4, prat_passo=0,   cabideiro=False),
    "closet":        dict(alt=2_200, portas=False, gavetas=2, prat_passo=0,   cabideiro=True),
    "gabinete":      dict(alt=BANCADA_ACABADA - TAMPO_GRANITO - RODAPE_GABINETE,
                          portas=True,  gavetas=0, prat_passo=400, cabideiro=False),
    "gabinete banho": dict(alt=500,  portas=False, gavetas=1, prat_passo=0,   cabideiro=False),
    "rack":          dict(alt=450,   portas=False, gavetas=1, prat_passo=0,   cabideiro=False),
    "mesa":          dict(alt=750,   portas=False, gavetas=3, prat_passo=0,   cabideiro=False),
    "painel tv":     dict(alt=1_800, portas=False, gavetas=0, prat_passo=0,   cabideiro=False),
    "cabeceira":     dict(alt=1_200, portas=False, gavetas=0, prat_passo=0,   cabideiro=False),
}
SOB_ESCADA_ALT = 1_200        # AR-05: altura livre de 1,34 m no fundo do vao
CABECEIRA_FOLGA = 300         # a cabeceira passa 300 mm de cada lado da cama
RIPA = dict(larg=40, esp=40, passo=80)   # painel ripado: ripa de 40 a cada 80

# ---- puxador por categoria de ambiente (H): a mesma paleta da fachada
PUXADOR = {"social": "perfil gola de aluminio grafite",
           "servico": "perfil gola de aluminio grafite",
           "oficina": "perfil gola de aluminio grafite",
           "circulacao": "perfil gola de aluminio grafite",
           "apoio": "perfil gola de aluminio grafite",
           "intimo": "cava usinada a 45 graus (sem ferragem)"}

# ---- precos de material (H), para conferir o preco sob medida do BOM
PRECO = {"chapa_15": 350.0, "chapa_6": 150.0,
         "dobradica": 9.0, "corredica_par": 45.0, "gola_m": 38.0,
         "fita_m": 1.2, "suporte": 0.4, "sapata": 2.5, "cabideiro_m": 60.0,
         "ripa_m": 8.0, "espuma_m2": 45.0}


def _cat(pj, amb: str) -> str:
    return pj.CATEGORIA.get(amb, "apoio")


def _n_dobradicas(alt: float) -> int:
    return 2 if alt <= 900 else 3 if alt <= 1_500 else 4 if alt <= 2_000 else 5


def _corredica(prof: float) -> int:
    cabe = [c for c in CORREDICAS if c <= prof - 100]
    return cabe[-1] if cabe else CORREDICAS[0]


PECA_UNICA = ("painel tv", "cabeceira", "mesa")   # nao modulam: nao tem porta


def _modulos(frente: float, familia: str = "") -> list[float]:
    """Modulos iguais, nenhum acima de PORTA_MAX: 2.100 vira 4 x 525.
    Painel, cabeceira e mesa sao uma peca so — a chapa e que limita."""
    if familia in PECA_UNICA:
        return [float(frente)]
    n = max(1, math.ceil(frente / PORTA_MAX))
    return [round(frente / n, 1)] * n


# ------------------------------------------------------------ 1. inventario
def _inventario(pj) -> list[dict]:
    """Todo movel de marcenaria que o caso loca: ARMARIOS, gabinetes das
    BANCADAS, gabinetes de lavatorio, racks e paineis do LAYOUT, cabeceiras
    das camas, e o closet declarado em SUBDIVISOES."""
    out = []
    for a in pj.ARMARIOS:
        frente, prof = max(a["w"], a["h"]), min(a["w"], a["h"])
        fam = a["tipo"]
        alt = SOB_ESCADA_ALT if a.get("sob_escada") else FAMILIAS[fam]["alt"]
        out.append(dict(cod=a["cod"], origem="ARMARIOS", amb=a["amb"], familia=fam,
                        frente=frente, prof=prof, alt=alt, x=a["x"], y=a["y"],
                        w=a["w"], h=a["h"], suspenso=False, nome=f"{a['cod']} {fam}"))
    for b in pj.BANCADAS:
        if b.get("tipo") == "tanque":
            continue                              # tanque de louca, sem gabinete
        frente = max(b["w"], b["h"])
        out.append(dict(cod=b["cod"] + "-G", origem="BANCADAS", amb=b["amb"], familia="gabinete",
                        frente=frente, prof=b["prof"] - 20, alt=FAMILIAS["gabinete"]["alt"],
                        x=b["x"], y=b["y"], w=b["w"], h=b["h"], suspenso=False,
                        cuba=b.get("cubas", 0) > 0, cooktop=b.get("cooktop", False),
                        nome=f"{b['cod']} gabinete sob granito"))
    for l in pj.LOUCAS:
        if l["tipo"] == "lavatorio":
            frente, prof = max(l["w"], l["h"]), min(l["w"], l["h"])
            out.append(dict(cod=l["cod"] + "-G", origem="LOUCAS", amb=l["amb"], familia="gabinete banho",
                            frente=frente, prof=prof, alt=FAMILIAS["gabinete banho"]["alt"],
                            x=l["x"], y=l["y"], w=l["w"], h=l["h"], suspenso=True,
                            cuba=True, nome=f"{l['cod']} gabinete suspenso do lavatorio"))
    for it in pj.LAYOUT:
        if it["tipo"] == "rack":
            if "trabalho" in it.get("obs", ""):
                fam = "mesa"
            elif it["h"] <= 60:
                fam = "painel tv"
            else:
                fam = "rack"
            frente, prof = max(it["w"], it["h"]), min(it["w"], it["h"])
            if fam == "painel tv":
                prof = RIPA["esp"] + ESP
            out.append(dict(cod=it["cod"] + "-M", origem="LAYOUT", amb=it["amb"], familia=fam,
                            frente=frente, prof=prof, alt=FAMILIAS[fam]["alt"],
                            x=it["x"], y=it["y"], w=it["w"], h=it["h"],
                            suspenso=(fam == "painel tv"), nome=f"{it['cod']} {fam}"))
        if it["tipo"] == "tv":
            # painel ripado atras de cada TV de parede, na largura do rack
            rack = next((r for r in pj.LAYOUT if r["tipo"] == "rack" and r["amb"] == it["amb"]
                         and r["h"] > 60), None)
            if rack:
                frente = max(rack["w"], rack["h"])
                out.append(dict(cod=it["cod"] + "-P", origem="LAYOUT", amb=it["amb"], familia="painel tv",
                                frente=frente, prof=RIPA["esp"] + ESP, alt=FAMILIAS["painel tv"]["alt"],
                                x=it["x"], y=it["y"], w=it["w"], h=it["h"], suspenso=True,
                                nome=f"{it['cod']} painel ripado da TV"))
        if it["tipo"] == "cama":
            lado = it["h"] if it.get("cabeceira", "+X")[1] == "X" else it["w"]
            out.append(dict(cod=it["cod"] + "-C", origem="LAYOUT", amb=it["amb"], familia="cabeceira",
                            frente=lado + 2 * CABECEIRA_FOLGA, prof=ESP + 50,
                            alt=FAMILIAS["cabeceira"]["alt"],
                            x=it["x"], y=it["y"], w=it["w"], h=it["h"], suspenso=True,
                            nome=f"{it['cod']} cabeceira estofada"))
    for d in pj.SUBDIVISOES:
        if d["nome"] == "CLOSET":
            # duas paredes: a oposta a porta e uma lateral, descontado o canto
            out.append(dict(cod=f"CL-{d['pai']}-A", origem="SUBDIVISOES", amb=d["pai"], familia="closet",
                            frente=d["w"], prof=600, alt=FAMILIAS["closet"]["alt"],
                            x=d["x"], y=d["y"], w=d["w"], h=600, suspenso=False,
                            nome="closet — parede do fundo"))
            out.append(dict(cod=f"CL-{d['pai']}-B", origem="SUBDIVISOES", amb=d["pai"], familia="closet",
                            frente=d["h"] - 600, prof=600, alt=FAMILIAS["closet"]["alt"],
                            x=d["x"] + d["w"] - 600, y=d["y"] + 600, w=600, h=d["h"] - 600,
                            suspenso=False, nome="closet — parede lateral"))
    return out


# ------------------------------------------------------------ 2. detalhar
def _pecas_modulo(m: dict, mov: dict, i: int) -> list[dict]:
    """As pecas de um modulo: caixa, fundo, prateleiras, porta, gavetas."""
    fam = FAMILIAS[mov["familia"]]
    L, A, Pf = m["larg"], mov["alt"], mov["prof"]
    pre = f"{mov['cod']}-M{i + 1}"
    Li = L - 2 * ESP
    pc = []

    def peca(sub, w, h, esp=ESP, fita=0.0, qtd=1, furos=None):
        pc.append(dict(cod=f"{pre}-{sub}", movel=mov["cod"], modulo=i + 1, nome=sub,
                       larg=round(w, 1), alt=round(h, 1), esp=esp, qtd=qtd,
                       fita_m=round(fita / 1000.0 * qtd, 2), furos=furos or {}))

    if mov["familia"] == "painel tv":
        peca("FUNDO", L, A, ESP, fita=2 * (L + A))
        n_ripas = int(L // RIPA["passo"])
        peca("RIPA", RIPA["larg"], A, RIPA["esp"], fita=0, qtd=n_ripas)
        return pc
    if mov["familia"] == "cabeceira":
        peca("PAINEL", L, A, ESP, fita=0)
        return pc
    if mov["familia"] == "mesa":
        # tampo engrossado: duas chapas de 15 coladas (30 mm) em vez de uma
        # chapa de 25 mm aberta para um tampo so, que seria 82 % de perda
        peca("TAMPO", L, Pf, ESP, fita=2 * (L + Pf), qtd=2)
        peca("PAINEL-LAT", Pf, A - ESP_TAMPO, ESP, fita=A, qtd=2)
        peca("TRAVESSA", L - 2 * ESP, 120, ESP, fita=L)
        # gaveteiro de 450 sob o tampo
        for g in range(fam["gavetas"]):
            peca(f"GAV{g + 1}-FRENTE", 450, GAVETA_ALT, ESP, fita=2 * (450 + GAVETA_ALT))
            peca(f"GAV{g + 1}-LAT", Pf - 80, GAVETA_ALT - 40, ESP, fita=GAVETA_ALT - 40, qtd=2)
            peca(f"GAV{g + 1}-TRAS", 450 - 2 * ESP - 26, GAVETA_ALT - 40, ESP)
            peca(f"GAV{g + 1}-FUNDO", 450 - 26, Pf - 80, ESP_FUNDO)
        return pc

    # caixa
    furos_lat = dict(sistema32=2 * (int((A - 2 * SISTEMA_32["primeiro"]) // SISTEMA_32["passo"]) + 1))
    peca("LAT", Pf, A, ESP, fita=A, qtd=2, furos=furos_lat)
    peca("BASE", Li, Pf, ESP, fita=Li)
    peca("TOPO", Li, Pf, ESP, fita=Li)
    peca("FUNDO", L - 2 * (ESP - 8), A - 2 * (ESP - 8), ESP_FUNDO)
    # prateleiras
    n_prat = int((A - 2 * ESP) // fam["prat_passo"]) - 1 if fam["prat_passo"] else 0
    if mov["familia"] in ("guarda-roupa", "closet"):
        n_prat = 1                                   # a prateleira sobre o cabideiro
    if mov.get("cuba") or mov.get("cooktop"):
        n_prat = 0 if mov.get("cuba") else min(n_prat, 1)
    if n_prat > 0:
        peca("PRAT", Li - 2, Pf - 20, ESP, fita=Li - 2, qtd=n_prat)
    # porta
    if fam["portas"]:
        n_dob = _n_dobradicas(A)
        peca("PORTA", L - 4, A - 4, ESP, fita=2 * (L + A - 8),
             furos=dict(cup35=n_dob))
    # gavetas
    so_gavetas = fam["gavetas"] and not fam["portas"] and not fam["cabideiro"]
    for g in range(fam["gavetas"]):
        # familia so de gaveta (gaveteiro, rack, gabinete de banho) divide a
        # altura entre as frentes; gaveta interna de armario e closet tem 200
        ag = round((A - 2 * ESP) / fam["gavetas"] - 4, 1) if so_gavetas else GAVETA_ALT
        peca(f"GAV{g + 1}-FRENTE", L - 4, ag, ESP, fita=2 * (L + ag - 8))
        peca(f"GAV{g + 1}-LAT", Pf - 80, ag - 40, ESP, fita=ag - 40, qtd=2)
        peca(f"GAV{g + 1}-TRAS", Li - 26, ag - 40, ESP)
        peca(f"GAV{g + 1}-FUNDO", Li - 26, Pf - 80, ESP_FUNDO)
    return pc


def _ferragens_modulo(m: dict, mov: dict, pj) -> dict:
    fam = FAMILIAS[mov["familia"]]
    A, Pf, L = mov["alt"], mov["prof"], m["larg"]
    f = dict(dobradicas=0, corredicas_par=0, corredica_mm=0, puxadores=0,
             gola_m=0.0, suportes=0, sapatas=0, cabideiro_m=0.0, ripas_m=0.0, espuma_m2=0.0)
    cat = _cat(pj, mov["amb"])
    gola = "gola" in PUXADOR[cat]
    if mov["familia"] == "painel tv":
        f["ripas_m"] = round(int(L // RIPA["passo"]) * A / 1000.0, 2)
        return f
    if mov["familia"] == "cabeceira":
        f["espuma_m2"] = round(L * A / 1e6, 2)
        return f
    if fam["portas"]:
        f["dobradicas"] = _n_dobradicas(A)
        f["puxadores"] = 1
        if gola:
            f["gola_m"] = round(L / 1000.0, 2)
    ng = fam["gavetas"]
    if ng:
        f["corredicas_par"] = ng
        f["corredica_mm"] = _corredica(Pf)
        f["puxadores"] += ng
        if gola:
            f["gola_m"] = round(f["gola_m"] + ng * (450 if mov["familia"] == "mesa" else L) / 1000.0, 2)
    n_prat = sum(p["qtd"] for p in m["pecas"] if p["nome"] == "PRAT")
    f["suportes"] = 4 * n_prat
    if not mov["suspenso"] and mov["familia"] not in ("mesa",):
        f["sapatas"] = 4
    if fam["cabideiro"]:
        f["cabideiro_m"] = round(L / 1000.0, 2)
    f["puxador"] = PUXADOR[cat] if f["puxadores"] else "—"
    return f


def moveis(pj) -> list[dict]:
    """Cada movel com modulos, pecas e ferragens. E a raiz de tudo o mais."""
    out = []
    for mov in _inventario(pj):
        mods = []
        for i, larg in enumerate(_modulos(mov["frente"], mov["familia"])):
            m = dict(n=i + 1, larg=larg)
            m["pecas"] = _pecas_modulo(m, mov, i)
            m["ferragens"] = _ferragens_modulo(m, mov, pj)
            mods.append(m)
        mov = dict(mov, modulos=mods,
                   n_modulos=len(mods),
                   n_portas=sum(1 for m in mods for p in m["pecas"] if p["nome"] == "PORTA"),
                   n_gavetas=sum(1 for m in mods for p in m["pecas"] if p["nome"].endswith("FRENTE")),
                   n_pecas=sum(p["qtd"] for m in mods for p in m["pecas"]),
                   area_frente_m2=round(mov["frente"] * mov["alt"] / 1e6, 2),
                   puxador=PUXADOR[_cat(pj, mov["amb"])],
                   mdf15_m2=round(sum(p["larg"] * p["alt"] * p["qtd"] for m in mods for p in m["pecas"]
                                      if p["esp"] == ESP) / 1e6, 2),
                   fita_m=round(sum(p["fita_m"] for m in mods for p in m["pecas"]), 1))
        out.append(mov)
    return out


def pecas(pj) -> list[dict]:
    return [dict(p, amb=mv["amb"], familia=mv["familia"])
            for mv in moveis(pj) for m in mv["modulos"] for p in m["pecas"]]


# ------------------------------------------------------------ 3. plano de corte
def nesting(pj) -> dict:
    """Chapas de 15, 6 e 25 mm pelo nesting guilhotinado de nucleo/nesting."""
    import nucleo.nesting as ne
    por_esp = {}
    for p in pecas(pj):
        if p["nome"] == "RIPA":
            continue                                  # ripa e barra, nao chapa
        for k in range(p["qtd"]):
            por_esp.setdefault(p["esp"], []).append((f"{p['cod']}#{k + 1}", p["larg"], p["alt"]))
    out = {}
    for esp, lista in sorted(por_esp.items()):
        out[esp] = ne.nestar_chapas(lista, larg=CHAPA["larg"], alt=CHAPA["alt"], serra=SERRA)
        out[esp]["pecas"] = len(lista)
    return out


# ------------------------------------------------------------ 4. furacao
def furacao(pj) -> list[dict]:
    """Sistema 32 por peca: onde, quantos e com que broca."""
    s = SISTEMA_32
    out = []
    for mv in moveis(pj):
        for m in mv["modulos"]:
            for p in m["pecas"]:
                if p["nome"] == "LAT":
                    n_lin = p["furos"].get("sistema32", 0) // 2
                    out.append(dict(peca=p["cod"], qtd=p["qtd"], tipo="fileira sistema 32",
                                    broca=s["furo"], prof=s["profundidade"],
                                    n=p["furos"]["sistema32"],
                                    posicao=f"2 fileiras a {s['recuo']} mm das bordas; "
                                            f"{n_lin} furos a cada {s['passo']} mm a partir de {s['primeiro']}"))
                if p["nome"] == "PORTA":
                    n = p["furos"].get("cup35", 0)
                    A = p["alt"]
                    pos = [s["cup_borda"]] if n == 1 else [
                        round(s["cup_borda"] + k * (A - 2 * s["cup_borda"]) / (n - 1)) for k in range(n)]
                    out.append(dict(peca=p["cod"], qtd=1, tipo="caneco de dobradica",
                                    broca=s["cup"], prof=12.5, n=n,
                                    posicao=f"centro a {s['cup_recuo']} mm da borda, em "
                                            + ", ".join(str(z) for z in pos) + " mm"))
    return out


# ------------------------------------------------------------ 5. totais
def ferragens(pj) -> dict:
    tot = dict(dobradicas=0, corredicas_par=0, puxadores=0, gola_m=0.0, suportes=0,
               sapatas=0, cabideiro_m=0.0, ripas_m=0.0, espuma_m2=0.0)
    corr = {}
    for mv in moveis(pj):
        for m in mv["modulos"]:
            f = m["ferragens"]
            for k in tot:
                tot[k] += f.get(k, 0)
            if f["corredicas_par"]:
                corr[f["corredica_mm"]] = corr.get(f["corredica_mm"], 0) + f["corredicas_par"]
    tot = {k: round(v, 2) for k, v in tot.items()}
    tot["corredicas_por_comprimento"] = corr
    return tot


def puxadores(pj) -> list[dict]:
    out = []
    for mv in moveis(pj):
        n = sum(m["ferragens"]["puxadores"] for m in mv["modulos"])
        if n:
            out.append(dict(movel=mv["cod"], amb=mv["amb"], categoria=_cat(pj, mv["amb"]),
                            tipo=mv["puxador"], qtd=n,
                            gola_m=round(sum(m["ferragens"]["gola_m"] for m in mv["modulos"]), 2)))
    return out


def custo_material(pj) -> dict:
    """Material pelo plano, contra o servico sob medida que o BOM ja carrega."""
    n = nesting(pj)
    f = ferragens(pj)
    fita = sum(mv["fita_m"] for mv in moveis(pj))
    itens = {
        "chapa 15 mm": (n.get(15, {}).get("n", 0), PRECO["chapa_15"]),
        "chapa 6 mm": (n.get(6, {}).get("n", 0), PRECO["chapa_6"]),
        "dobradicas": (f["dobradicas"], PRECO["dobradica"]),
        "corredicas (par)": (f["corredicas_par"], PRECO["corredica_par"]),
        "perfil gola (m)": (f["gola_m"], PRECO["gola_m"]),
        "fita de borda (m)": (round(fita, 1), PRECO["fita_m"]),
        "suportes": (f["suportes"], PRECO["suporte"]),
        "sapatas": (f["sapatas"], PRECO["sapata"]),
        "cabideiro (m)": (f["cabideiro_m"], PRECO["cabideiro_m"]),
        "ripas (m)": (f["ripas_m"], PRECO["ripa_m"]),
        "espuma (m2)": (f["espuma_m2"], PRECO["espuma_m2"]),
    }
    linhas = [dict(item=k, qtd=q, unit=p, total=round(q * p, 2)) for k, (q, p) in itens.items()]
    material = round(sum(l["total"] for l in linhas), 2)
    import nucleo.acabamento as ac
    bom = [l for l in ac.marcenaria(pj) if l["sku"] in ("MAR-GAB", "MAR-ARM", "MAR-PRAT", "MAR-PAINEL", "MAR-CABEC")]
    servico = round(sum(l["quantidade"] * l["preco"] for l in bom), 2)
    return dict(linhas=linhas, material=material, servico_bom=servico,
                razao=round(material / servico, 3) if servico else None)


def resumo(pj) -> dict:
    mv = moveis(pj)
    n = nesting(pj)
    return dict(moveis=len(mv), modulos=sum(m["n_modulos"] for m in mv),
                pecas=sum(m["n_pecas"] for m in mv),
                portas=sum(m["n_portas"] for m in mv), gavetas=sum(m["n_gavetas"] for m in mv),
                frente_m2=round(sum(m["area_frente_m2"] for m in mv), 2),
                chapas={esp: dict(n=v["n"], aproveitamento=round(v["aproveitamento"], 3),
                                  nao_cabem=len(v["nao_cabem"]))
                        for esp, v in n.items()},
                ferragens=ferragens(pj), custo=custo_material(pj))


# ------------------------------------------------------------ 6. conferir
def conferir(pj) -> list[tuple[str, str, bool]]:
    out = []
    mv = moveis(pj)
    ambs = {a.cod: a for a in pj.TERREO + pj.SUPERIOR}
    for m in mv:
        a = ambs.get(m["amb"])
        if a:
            maior = max(a.w, a.h)
            out.append((f"{m['cod']} cabe na parede",
                        f"frente {m['frente']:.0f} mm em ambiente de {maior:.0f} mm",
                        m["frente"] <= maior))
        if FAMILIAS[m["familia"]]["portas"] or FAMILIAS[m["familia"]]["gavetas"] and m["familia"] not in PECA_UNICA:
            folha = max((mm["larg"] for mm in m["modulos"]), default=0)
            out.append((f"{m['cod']} folha de porta", f"modulo de {folha:.0f} mm (maximo {PORTA_MAX})",
                        folha <= PORTA_MAX + 0.5))
    n = nesting(pj)
    for esp, v in n.items():
        out.append((f"chapa {esp} mm: tudo cabe", f"{v['pecas']} pecas em {v['n']} chapas, "
                    f"{len(v['nao_cabem'])} nao cabem", not v["nao_cabem"]))
        out.append((f"chapa {esp} mm: aproveitamento",
                    f"{v['aproveitamento'] * 100:.0f} % (minimo aceitavel 60 %)",
                    v["aproveitamento"] >= 0.60))
    c = custo_material(pj)
    out.append(("material dentro do preco sob medida",
                f"material R$ {c['material']:,.0f} = {c['razao'] * 100:.0f} % do servico "
                f"R$ {c['servico_bom']:,.0f} (faixa 20 a 60 %)",
                c["razao"] is not None and 0.20 <= c["razao"] <= 0.60))
    codigos = {a["cod"] for a in pj.ARMARIOS}
    cobertos = {m["cod"] for m in mv}
    out.append(("todo ARMARIO tem plano", f"{len(codigos & cobertos)} de {len(codigos)}",
                codigos <= cobertos))
    return out
