"""
MODELO 3D — exporta a geometria do projeto para o visualizador.

Mesma fonte das 35 pranchas: paredes derivadas da malha, vaos recortados nelas,
lajes, platibanda, cobertura, piscina, deck e mobiliario. Nada e modelado duas
vezes — se a planta muda, o 3D muda junto, porque os dois leem projeto.py.

Sistema de coordenadas exportado (destro, para o visualizador):
    X = largura do lote  (0 na divisa sul, 20.000 na divisa norte)
    Y = profundidade     (0 na testada leste, 40.000 no fundo)
    Z = altura           (0 no piso do terreo)
Tudo em MILIMETROS, como o resto do projeto.
"""
from __future__ import annotations

import json
import os

import projeto as pj
import elementos as el
import especificacao as ep

# ---------------------------------------------------------------- niveis
LAJE_ESP = 300
PLATIBANDA = 250
Z = {
    "T": dict(piso=0, teto=pj.PE_DIREITO, laje_topo=pj.PE_DIREITO + LAJE_ESP),
    "S": dict(piso=pj.PISO_A_PISO, teto=pj.PISO_A_PISO + pj.PE_DIREITO,
              laje_topo=pj.PISO_A_PISO + pj.PE_DIREITO + LAJE_ESP),
}
# cotas de platibanda que os cortes ja declaravam: +3,150 e +6,150
TOPO_TERREO = Z["T"]["laje_topo"] + PLATIBANDA
TOPO_SUPERIOR = Z["S"]["laje_topo"] + PLATIBANDA

CORES = {
    "parede_ext": "#d9d4cb", "parede_int": "#e8e4dc", "laje": "#cfcac1",
    "platibanda": "#cdc7bd", "vidro": "#8fc4dd", "porta": "#9b7245",
    "piso_int": "#e6e1d8", "deck": "#b08a5e", "piscina": "#5aa7c8",
    "pilar": "#4a4f55", "viga": "#5b6169", "mob": "#b9b2a6",
    "bancada": "#8d8579", "louca": "#eceff1", "escada": "#c6c0b6",
    "brise": "#4a4f55", "tecnico": "#9a8f80", "terreno": "#cfd8cf",
}


def _cx(x0, x1):
    return (x0 + x1) / 2


def _box(t, x0, y0, z0, x1, y1, z1, cor, rot=None):
    return dict(t=t, p=[round(_cx(x0, x1)), round(_cx(y0, y1)), round(_cx(z0, z1))],
                s=[round(abs(x1 - x0)), round(abs(y1 - y0)), round(abs(z1 - z0))],
                c=cor, **({"amb": rot} if rot else {}))


def _paredes(pav: str) -> list[dict]:
    """Paredes do pavimento, recortadas nos vaos, com verga e peitoril."""
    ambs = pj.TERREO if pav == "T" else pj.SUPERIOR
    paredes = el.derivar_paredes(ambs)
    vaos = list(el.vaos_do_pavimento(pav))
    z0, z1 = Z[pav]["piso"], Z[pav]["teto"]
    out = []
    for par in paredes:
        cor = CORES["parede_ext"] if par.externa else CORES["parede_int"]
        e = par.esp
        cortes = el.recortes_na_parede(par, vaos)
        if par.horizontal:
            a, b = min(par.x1, par.x2), max(par.x1, par.x2)
            y = par.y1
            pos = a
            for ca, cb in cortes:
                if ca > pos:
                    out.append(_box("parede", pos, y - e / 2, z0, ca, y + e / 2, z1, cor))
                pos = max(pos, cb)
            if pos < b:
                out.append(_box("parede", pos, y - e / 2, z0, b, y + e / 2, z1, cor))
            # verga e peitoril de cada vao
            for v in vaos:
                if v["ori"] != "H" or abs(v["y"] - y) > 1:
                    continue
                if not (a <= v["x"] <= b):
                    continue
                vx0, vx1 = v["x"] - v["larg"] / 2, v["x"] + v["larg"] / 2
                topo = z0 + v["peitoril"] + v["alt"]
                if v["peitoril"] > 0:
                    out.append(_box("parede", vx0, y - e / 2, z0,
                                    vx1, y + e / 2, z0 + v["peitoril"], cor))
                if topo < z1:
                    out.append(_box("parede", vx0, y - e / 2, topo,
                                    vx1, y + e / 2, z1, cor))
                out.append(_box("vao", vx0, y - 25, z0 + v["peitoril"], vx1, y + 25, topo,
                                CORES["porta"] if v["tipo"].startswith("P")
                                and not v["tipo"].startswith("PV") else CORES["vidro"]))
        else:
            a, b = min(par.y1, par.y2), max(par.y1, par.y2)
            x = par.x1
            pos = a
            for ca, cb in cortes:
                if ca > pos:
                    out.append(_box("parede", x - e / 2, pos, z0, x + e / 2, ca, z1, cor))
                pos = max(pos, cb)
            if pos < b:
                out.append(_box("parede", x - e / 2, pos, z0, x + e / 2, b, z1, cor))
            for v in vaos:
                if v["ori"] != "V" or abs(v["x"] - x) > 1:
                    continue
                if not (a <= v["y"] <= b):
                    continue
                vy0, vy1 = v["y"] - v["larg"] / 2, v["y"] + v["larg"] / 2
                topo = z0 + v["peitoril"] + v["alt"]
                if v["peitoril"] > 0:
                    out.append(_box("parede", x - e / 2, vy0, z0,
                                    x + e / 2, vy1, z0 + v["peitoril"], cor))
                if topo < z1:
                    out.append(_box("parede", x - e / 2, vy0, topo,
                                    x + e / 2, vy1, z1, cor))
                out.append(_box("vao", x - 25, vy0, z0 + v["peitoril"], x + 25, vy1, topo,
                                CORES["porta"] if v["tipo"].startswith("P")
                                and not v["tipo"].startswith("PV") else CORES["vidro"]))
    return out


def _subdivisoes() -> list[dict]:
    out = []
    for sd in pj.SUBDIVISOES:
        pav = "S" if sd["pai"].startswith("S-") else "T"
        z0, z1 = Z[pav]["piso"], Z[pav]["teto"]
        e = pj.PAR_INT
        x0, y0 = sd["x"], sd["y"]
        x1, y1 = sd["x"] + sd["w"], sd["y"] + sd["h"]
        # so as duas faces internas (as outras ja sao parede do ambiente)
        if sd["face"] in ("S", "N"):
            fx = x1 if sd["face"] == "N" else x0
            out.append(_box("parede", fx - e / 2, y0, z0, fx + e / 2, y1, z1,
                            CORES["parede_int"]))
        else:
            fy = y1 if sd["face"] == "O" else y0
            out.append(_box("parede", x0, fy - e / 2, z0, x1, fy + e / 2, z1,
                            CORES["parede_int"]))
    return out


def _lajes() -> list[dict]:
    out = []
    for a in pj.cobertos():
        out.append(_box("piso", a.x, a.y, -100, a.x + a.w, a.y + a.h, 0,
                        CORES["piso_int"], a.cod))
    for a in pj.SUPERIOR + pj.SUPERIOR_ABERTO:
        out.append(_box("laje", a.x, a.y, Z["T"]["teto"], a.x + a.w, a.y + a.h,
                        Z["T"]["laje_topo"], CORES["laje"], a.cod))
    # cobertura: sobre o superior e sobre o terreo que nao tem superior em cima
    sup = [(a.x, a.y, a.x + a.w, a.y + a.h) for a in pj.SUPERIOR + pj.SUPERIOR_ABERTO]
    for a in pj.cobertos():
        coberto_por_sup = any(a.x >= s[0] and a.y >= s[1]
                              and a.x + a.w <= s[2] and a.y + a.h <= s[3] for s in sup)
        if not coberto_por_sup:
            out.append(_box("cobertura", a.x, a.y, Z["T"]["teto"],
                            a.x + a.w, a.y + a.h, Z["T"]["laje_topo"],
                            CORES["laje"], a.cod))
    for a in pj.SUPERIOR:
        out.append(_box("cobertura", a.x, a.y, Z["S"]["teto"],
                        a.x + a.w, a.y + a.h, Z["S"]["laje_topo"],
                        CORES["laje"], a.cod))
    return out


def _platibandas() -> list[dict]:
    """Faixa de 250 mm no contorno de cada volume — a linha reta da fachada."""
    out = []
    for lst, ztopo, zbase in ((pj.SUPERIOR, TOPO_SUPERIOR, Z["S"]["laje_topo"]),):
        if not lst:
            continue
        x0 = min(a.x for a in lst); x1 = max(a.x + a.w for a in lst)
        y0 = min(a.y for a in lst); y1 = max(a.y + a.h for a in lst)
        e = pj.PAR_EXT
        out += [_box("platibanda", x0, y0, zbase, x1, y0 + e, ztopo, CORES["platibanda"]),
                _box("platibanda", x0, y1 - e, zbase, x1, y1, ztopo, CORES["platibanda"]),
                _box("platibanda", x0, y0, zbase, x0 + e, y1, ztopo, CORES["platibanda"]),
                _box("platibanda", x1 - e, y0, zbase, x1, y1, ztopo, CORES["platibanda"])]
    # volume de um pavimento (garagem e frente)
    baixos = [a for a in pj.TERREO
              if not any(a.x >= s.x and a.y >= s.y and a.x + a.w <= s.x + s.w
                         and a.y + a.h <= s.y + s.h for s in pj.SUPERIOR)]
    if baixos:
        x0 = min(a.x for a in baixos); x1 = max(a.x + a.w for a in baixos)
        y0 = min(a.y for a in baixos); y1 = max(a.y + a.h for a in baixos)
        e = pj.PAR_EXT
        zb, zt = Z["T"]["laje_topo"], TOPO_TERREO
        out += [_box("platibanda", x0, y0, zb, x1, y0 + e, zt, CORES["platibanda"]),
                _box("platibanda", x0, y0, zb, x0 + e, y1, zt, CORES["platibanda"])]
    return out


def _externos() -> list[dict]:
    out = []
    dk, p = pj.DECK, pj.PISCINA
    # O deck ENVOLVE a piscina (e o proprio DECK diz isso no comentario dele).
    # Exporta-lo como uma laje inteira tapava a agua: na cena "fundos" a piscina
    # simplesmente nao existia. Vai como quatro faixas em volta do espelho.
    dx0, dy0 = dk["x"], dk["y"]
    dx1, dy1 = dk["x"] + dk["w"], dk["y"] + dk["h"]
    px0, py0 = p["x"], p["y"]
    px1, py1 = p["x"] + p["w"], p["y"] + p["h"]
    envolve = dx0 <= px0 and dy0 <= py0 and dx1 >= px1 and dy1 >= py1
    faixas = ([(dx0, dy0, dx1, py0), (dx0, py1, dx1, dy1),
               (dx0, py0, px0, py1), (px1, py0, dx1, py1)]
              if envolve else [(dx0, dy0, dx1, dy1)])
    for fx0, fy0, fx1, fy1 in faixas:
        if fx1 - fx0 > 0 and fy1 - fy0 > 0:
            out.append(_box("deck", fx0, fy0, -60, fx1, fy1, 0, CORES["deck"]))
    out.append(_box("piscina", px0, py0, -p["prof_principal"], px1, py1, -100,
                    CORES["piscina"]))
    for a in pj.TERREO_ABERTO:
        if a.cod in ("T-DKP",):
            continue
        cor = CORES["deck"] if a.coberto else CORES["terreno"]
        out.append(_box("externo", a.x, a.y, -80, a.x + a.w, a.y + a.h, -20,
                        cor, a.cod))
    # varanda gourmet: laje em balanco
    alp = next((a for a in pj.TERREO_ABERTO if a.cod == "T-ALP"), None)
    if alp:
        out.append(_box("cobertura", alp.x, alp.y, Z["T"]["teto"],
                        alp.x + alp.w, alp.y + alp.h, Z["T"]["laje_topo"],
                        CORES["laje"], "T-ALP"))
    for pl in pj.PILARES:
        s = 200
        out.append(_box("pilar", pl["x"] - s / 2, pl["y"] - s / 2, 0,
                        pl["x"] + s / 2, pl["y"] + s / 2, Z["T"]["teto"],
                        CORES["pilar"]))
    for t in pj.TECNICOS:
        if t.get("zona") == "INT" or t.get("rasante"):
            continue
        h = 1_800 if "Nicho" in t["nome"] or "maquinas" in t["nome"].lower() else 900
        out.append(_box("tecnico", t["x"], t["y"], 0, t["x"] + t["w"],
                        t["y"] + t["h"], h, CORES["tecnico"], t["cod"]))
    for br in pj.BRISES:
        out.append(_box("brise", br["x"] - 60, br["y"], 900,
                        br["x"] + 60, br["y"] + br["w"], 2_400, CORES["brise"]))
    return out


def _mobiliario() -> list[dict]:
    out = []
    alturas = {"bancada": 900, "armario alto": 2_200, "prateleiras": 1_800,
               "geladeira": 1_900, "lavadora": 850, "secadora": 850,
               "lava-loucas": 850, "lixo": 600, "forno": 600, "micro-ondas": 400,
               "box": 2_000, "tanque": 900, "vaso": 400, "lavatorio": 850}
    def pav_de(cod):
        return "S" if cod.startswith("S-") else "T"
    for b in pj.BANCADAS:
        z0 = Z[pav_de(b["amb"])]["piso"]
        out.append(_box("mob", b["x"], b["y"], z0, b["x"] + b["w"], b["y"] + b["h"],
                        z0 + 900, CORES["bancada"], b["cod"]))
    for grupo, cor in ((pj.LOUCAS, CORES["louca"]), (pj.EQUIPAMENTOS, CORES["mob"]),
                       (pj.ARMARIOS, CORES["mob"])):
        for m in grupo:
            z0 = Z[pav_de(m["amb"])]["piso"]
            h = alturas.get(m["tipo"], 800)
            out.append(_box("mob", m["x"], m["y"], z0, m["x"] + m["w"],
                            m["y"] + m["h"], z0 + h, cor, m["cod"]))
    # camas, sofa e mesa: volume simples so para dar escala
    camas = [("S-S02", 4_200, 14_400), ("S-S03", 4_200, 19_200),
             ("S-MAS", 8_400, 23_100)]
    for cod, x, y in camas:
        out.append(_box("mob", x, y, Z["S"]["piso"], x + 1_600, y + 2_000,
                        Z["S"]["piso"] + 550, CORES["mob"], cod + "/cama"))
    out.append(_box("mob", 6_000, 14_400, 0, 8_400, 15_300, 750, CORES["mob"], "sofa"))
    out.append(_box("mob", 6_300, 21_600, 0, 8_700, 23_400, 750, CORES["mob"], "mesa"))
    out.append(_box("mob", 3_600, 27_600, 0, 6_000, 28_800, 750, CORES["mob"],
                    "mesa da varanda"))
    return out


def _escada() -> list[dict]:
    out = []
    e = pj.ESCADA
    for l in pj.escada_lances():
        n = max(1, l["espelhos"])
        if l["sentido"] == "patamar":
            out.append(_box("escada", l["x"], l["y"], l["z_ini"] - 150,
                            l["x"] + l["w"], l["y"] + l["h"], l["z_ini"],
                            CORES["escada"]))
            continue
        for i in range(n):
            frac = i / n
            if l["sentido"] == "-Y":
                y0 = l["y"] + l["h"] - (i + 1) * e["piso"]
            else:
                y0 = l["y"] + i * e["piso"]
            z = l["z_ini"] + (l["z_fim"] - l["z_ini"]) * frac
            out.append(_box("escada", l["x"], y0, z - 150, l["x"] + l["w"],
                            y0 + e["piso"], z + e["alt_espelho"], CORES["escada"]))
    return out


def _ambientes() -> list[dict]:
    out = []
    for a in pj.TERREO + pj.SUPERIOR:
        pav = a.pav
        out.append(dict(cod=a.cod, nome=a.nome, pav=pav,
                        p=[round(a.cx), round(a.cy), Z[pav]["piso"] + 1_400],
                        area=round(a.area_mod, 2)))
    return out


CENAS = [
    dict(id="perspectiva", nome="Perspectiva geral",
         alvo=[10_000, 20_000, 1_500], dist=34_000, azim=-38, elev=24,
         hora=10,
         mostra=["cobertura", "superior", "terreo", "externo", "mob"],
         nota="Volumetria inteira: garagem em um pavimento na frente, portico "
              "recuado, corpo de dois pavimentos atras."),
    dict(id="chegada", nome="Chegada — fachada leste",
         alvo=[9_000, 9_000, 1_800], dist=22_000, azim=-90, elev=8,
         hora=8.5,
         mostra=["cobertura", "superior", "terreo", "externo"],
         nota="O que se ve da rua: portao ripado, portico recuado e o volume "
              "superior emergindo atras."),
    dict(id="fita", nome="Fita social sem cobertura",
         alvo=[7_500, 20_000, 1_200], dist=24_000, azim=-55, elev=40,
         corte=1_500,
         hora=12,
         mostra=["terreo", "externo", "mob", "escada"],
         nota="Estar, core, cozinha e gourmet sem uma parede entre eles, "
              "abrindo pela cortina de vidro."),
    # A camera em altura de olho (elev 6) caia DENTRO do volume da frente e a
    # cena mostrava uma parede. O eixo so se le de cima, com a casa cortada
    # acima do peitoril: dai o corte em +2,20 m.
    dict(id="eixo", nome="Eixo da piscina",
         alvo=[7_500, 24_000, 1_000], dist=33_000, azim=-90, elev=19,
         corte=2_200,
         hora=12,
         mostra=["terreo", "externo", "mob", "superior", "cobertura"],
         nota="Os 20,70 m do estar ate o fim da agua, com a casa cortada em "
              "+2,20 m: o eixo atravessa cozinha, cortina, varanda e piscina "
              "com 0 mm de desalinhamento."),
    dict(id="superior", nome="Pavimento superior",
         alvo=[8_000, 19_000, 3_500], dist=26_000, azim=-50, elev=45,
         hora=12,
         mostra=["superior", "terreo", "mob", "escada", "externo"],
         nota="Duas suites espelhadas, hall com rouparia, mini lounge e a master "
              "de 46,80 m2."),
    dict(id="fundos", nome="Fachada oeste — piscina",
         alvo=[8_000, 30_000, 1_500], dist=24_000, azim=90, elev=10,
         hora=16,
         mostra=["cobertura", "superior", "terreo", "externo", "mob"],
         nota="A varanda de 3.000 mm em balanco, sem pilar entre a mesa e a agua."),
    dict(id="tecnica", nome="Faixa tecnica norte",
         alvo=[16_000, 20_000, 1_200], dist=26_000, azim=0, elev=14,
         hora=11,
         mostra=["cobertura", "superior", "terreo", "externo"],
         nota="A espinha de manutencao: cisterna, bomba, GLP, nichos de "
              "condensadoras, casa de maquinas e deposito, tudo num corredor so."),
    dict(id="topo", nome="Implantacao de cima",
         alvo=[10_000, 20_000, 0], dist=42_000, azim=-90, elev=88,
         hora=12,
         mostra=["cobertura", "superior", "terreo", "externo"],
         nota="Taxa de ocupacao, recuos e a relacao entre construido e livre."),
]


def exportar(caminho: str | None = None) -> dict:
    dados = dict(
        meta=dict(lote=[pj.LOTE_L, pj.LOTE_P], norte=pj.NORTE_EM_PLANTA,
                  pe_direito=pj.PE_DIREITO, piso_a_piso=pj.PISO_A_PISO,
                  topo_terreo=TOPO_TERREO, topo_superior=TOPO_SUPERIOR,
                  revisao=pj.EMISSAO["revisao"],
                  areas=dict(terreo=pj.area_fechada("T"),
                             superior=pj.area_fechada("S"),
                             coberta=pj.projecao_coberta_m2())),
        terreo=_paredes("T") + _subdivisoes(),
        superior=_paredes("S"),
        lajes=_lajes(), platibandas=_platibandas(),
        externo=_externos(), mob=_mobiliario(), escada=_escada(),
        ambientes=_ambientes(), cenas=CENAS, cores=CORES,
        lsf=_estrutura_lsf(), cores_lsf=CORES_LSF)
    # separa o que e do superior para permitir ligar/desligar
    dados["superior"] = [b for b in dados["superior"]]
    if caminho:
        with open(caminho, "w") as f:
            json.dump(dados, f, separators=(",", ":"))
    return dados


# ---------------------------------------------------------------------------
# ESTRUTURA LSF — as 805 pecas, cada uma no seu lugar
# ---------------------------------------------------------------------------
# Ate R29 o 3D mostrava o EDIFICIO: paredes como blocos macicos de 150 mm. Isso
# serve para verificar altura livre e sombra, e nao serve para ver a estrutura:
# a parede de LSF nao e um bloco, sao 13 pecas de chapa de 0,95 mm. Quem quer
# conferir montante, verga e travamento precisa ver a peca, nao o volume que ela
# preenche.
CORES_LSF = {
    "track": "#8a94a6", "stud": "#3f6fb5", "king stud": "#1f4e96",
    "jack stud": "#4d8fd6", "cripple superior": "#9fc0e8",
    "cripple inferior": "#7ba7dc", "header": "#c4491f",
    "sill": "#d98324", "blocking": "#6fae7c",
    # vigamento e contraventamento, que ate R30 nao existiam no modelo
    "viga": "#2f7d4f", "viga de borda": "#1d5c38", "travamento": "#7fb08f",
    "diagonal": "#e0a32e",
}


def _estrutura_lsf() -> list[dict]:
    """Cada peca de cada painel, em coordenada do mundo.

    A peca vive em coordenada LOCAL do painel: x ao longo da parede, z a partir
    da base. O painel vive em coordenada do pavimento. A conversao e so uma, e
    esta aqui — em qualquer outro lugar ela seria uma segunda verdade.
    """
    import elementos as el
    import nucleo.painel as pn
    import nucleo.perfis as pf
    import nucleo.materiais as mt
    import nucleo.descida as ds

    cfg = pn.Config()
    aco = mt.POR_ACO["ZAR 230"]
    pais = {pav: pn.painelizar(el.derivar_paredes(amb),
                               list(el.vaos_do_pavimento(pav)), cfg, f"{pav}P")
            for pav, amb in (("T", pj.TERREO), ("S", pj.SUPERIOR))}
    ds.dimensionar(pais, aco, pj.CARGAS, cfg, list(pf.catalogo()))

    base = {"T": pj.NIVEL_TERREO, "S": pj.NIVEL_SUPERIOR}
    out = []
    for pav, lista in pais.items():
        z0 = base[pav]
        for p in lista:
            for q in p.pecas:
                bw = pn.bw(q.perfil)
                # medida ao longo da parede e altura da peca no plano do painel
                ao_longo = bw if q.vertical else q.comp
                alto = q.comp if q.vertical else bw
                if p.horizontal:
                    x0, x1 = p.x + q.x, p.x + q.x + ao_longo
                    y0, y1 = p.y, p.y + p.esp
                else:
                    x0, x1 = p.x, p.x + p.esp
                    y0, y1 = p.y + q.x, p.y + q.x + ao_longo
                b = _box("lsf", x0, y0, z0 + q.z, x1, y1, z0 + q.z + alto,
                         CORES_LSF.get(q.familia, "#8a94a6"))
                b.update(cod=q.cod, fam=q.familia, perf=q.perfil,
                         painel=p.cod, pav=pav, comp=q.comp)
                out.append(b)

    # ---- vigamento de entrepiso e de cobertura
    import nucleo.piso as ps
    casa = ps.montar_casa(pj, aco, cfg)
    for q in casa["pecas"]:
        bw = pn.bw(q["perfil"]) if q["perfil"] != "—" else 200
        z0 = q["nivel"]
        if q["ao_longo_x"]:
            x0, x1 = q["x"], q["x"] + q["comp"]
            y0, y1 = q["y"], q["y"] + 45
        else:
            x0, x1 = q["x"], q["x"] + 45
            y0, y1 = q["y"], q["y"] + q["comp"]
        b = _box("lsf", x0, y0, z0, x1, y1, z0 + bw,
                 CORES_LSF.get(q["familia"], "#2f7d4f"))
        b.update(cod=q["cod"], fam=q["familia"], perf=q["perfil"],
                 painel=q["plano"], pav=q["tipo"], comp=q["comp"])
        out.append(b)

    # ---- contraventamento: as fitas em X, que precisam de rotacao de verdade.
    # Em vez de deduzir angulo e eixo aqui e de novo no navegador, a peca leva
    # as DUAS PONTAS e o navegador monta a transformacao a partir delas. Uma
    # rotacao deduzida em dois lugares diverge no primeiro sinal trocado.
    todos = [p for v in pais.values() for p in v]
    contra = ps.contraventar(todos, pj, aco, cfg)
    por_cod = {p.cod: p for p in todos}
    for q in contra["pecas"]:
        p = por_cod.get(q["painel"])
        if p is None:
            continue
        z0 = base[p.pav]
        ini, fim = (0, p.comp) if q["sinal"] > 0 else (p.comp, 0)
        if p.horizontal:
            a0 = [p.x + ini, p.y + p.esp / 2, z0]
            a1 = [p.x + fim, p.y + p.esp / 2, z0 + p.altura]
        else:
            a0 = [p.x + p.esp / 2, p.y + ini, z0]
            a1 = [p.x + p.esp / 2, p.y + fim, z0 + p.altura]
        out.append(dict(t="lsf", de=[round(v) for v in a0],
                        ate=[round(v) for v in a1], esp=38,
                        c=CORES_LSF["diagonal"], cod=q["cod"],
                        fam="diagonal", perf=q["perfil"],
                        painel=q["painel"], pav=p.pav, comp=q["comp"]))
    return out


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "out", "modelo3d.json")
    d = exportar(out)
    n = sum(len(d[k]) for k in ("terreo", "superior", "lajes", "platibandas",
                                "externo", "mob", "escada"))
    print(f"  {n} solidos exportados")
    for k in ("terreo", "superior", "lajes", "platibandas", "externo", "mob", "escada"):
        print(f"    {k:12} {len(d[k]):4}")
    print(f"  {len(d['ambientes'])} ambientes rotulados, {len(d['cenas'])} cenas")
    print(f"  {os.path.getsize(out)/1024:.0f} KB")
