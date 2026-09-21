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
    # R60 — a fachada tem DOIS tratamentos (R59): base pintada ate 2.600 mm e
    # volume superior em mineral claro de fabrica. A cena mostra os dois.
    "parede_ext": "#ebe7e0", "parede_base": "#cfc8bc", "parede_int": "#e8e4dc",
    "laje": "#cfcac1",
    "luz_2700": "#ffb865", "luz_3000": "#ffd27a", "luz_4000": "#dff0ff",
    "platibanda": "#cdc7bd", "vidro": "#8fc4dd", "porta": "#9b7245",
    "piso_int": "#e6e1d8", "deck": "#b08a5e", "piscina": "#5aa7c8",
    "pilar": "#4a4f55", "viga": "#5b6169", "mob": "#b9b2a6",
    "bancada": "#8d8579", "louca": "#eceff1", "escada": "#c6c0b6",
    "brise": "#4a4f55", "tecnico": "#9a8f80", "terreno": "#cfd8cf",
    # R52 — o muro existia no modelo, no orcamento e no desenho desde R49, e
    # nunca na cena. 113 m de bloco aparente de 2,20 m de altura: o elemento
    # que mais define o que se ve da rua, ausente justamente da vista que
    # existe para mostrar o que se ve.
    "muro": "#b4ada3", "drenante": "#c9c4bb", "brita": "#bcb8b0",
    "radier": "#a9a49b",
    "grama": "#b7c9a8", "reservatorio": "#7f8c99",
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
        cor = ((CORES["parede_base"] if pav == "T" else CORES["parede_ext"])
               if par.externa else CORES["parede_int"])
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
        # R48 — do DADO: a altura e a profundidade eram literais aqui (1.500 de
        # altura desenhada como 900 a 2.400, e 120 de profundidade contra os
        # 150 declarados). O 3D convencia com uma medida que o dado nao tinha.
        pr = br["h"] / 2
        z0 = br.get("z0", 900)
        out.append(_box("brise", br["x"] - pr, br["y"], z0,
                        br["x"] + pr, br["y"] + br["w"],
                        z0 + br.get("altura", 1_500), CORES["brise"]))
    return out


def _lote() -> list[dict]:
    """Muro, superficies do terreno e reservatorio de retencao.

    Tudo aqui ja existia no modelo e no orcamento; nada existia na cena. Era o
    mesmo padrao que R31, R37, R38, R48 e R49 ja tinham acusado em outros
    sistemas — "existe no desenho, nao existe no 3D" — sobrevivendo no unico
    lugar onde ninguem tinha ido procurar: o terreno.
    """
    import nucleo.pluvial as pl
    out = []
    L, P = pj.LOTE_L, pj.LOTE_P
    import nucleo.externo as ex
    e = ex.MURO["espessura"]
    h = ex.MURO["altura"]
    pt = pj.PORTAO_TESTADA
    # tres divisas fechadas
    for x0, y0, x1, y1 in ((0, 0, e, P), (L - e, 0, L, P), (0, P - e, L, P)):
        out.append(_box("muro", x0, y0, 0, x1, y1, h, CORES["muro"]))
    # testada: os vaos dos dois portoes saem da MESMA declaracao que o
    # comprimento do muro desconta
    vaos = sorted([(pt["veiculo_x"] - pt["veiculo_larg"] / 2,
                    pt["veiculo_x"] + pt["veiculo_larg"] / 2),
                   (pt["pedestre_x"] - pt["pedestre_larg"] / 2,
                    pt["pedestre_x"] + pt["pedestre_larg"] / 2)])
    cur = 0
    for a, b in vaos + [(L, L)]:
        if a > cur:
            out.append(_box("muro", cur, 0, 0, a, e, h, CORES["muro"]))
        cur = b
    # superficies do terreno que nao sao ambiente: acesso, passeio, faixa
    # tecnica e recuos. A cor diz a classe, e a classe e a mesma que entra no
    # calculo da retencao.
    xs = [a.x for a in pj.TERREO + pj.TERREO_ABERTO]
    xe = [a.x + a.w for a in pj.TERREO + pj.TERREO_ABERTO]
    ys = [a.y for a in pj.TERREO + pj.TERREO_ABERTO]
    ye = [a.y + a.h for a in pj.TERREO + pj.TERREO_ABERTO]
    x0, x1, y0, y1 = min(xs), max(xe), min(ys), max(ye)
    faixas = [
        ("drenante", pt["veiculo_x"] - pt["veiculo_larg"] / 2, 0,
         pt["veiculo_x"] + pt["veiculo_larg"] / 2, y0),
        ("drenante", pt["pedestre_x"] - pt["pedestre_larg"] / 2, 0,
         pt["pedestre_x"] + pt["pedestre_larg"] / 2, y0),
        ("brita", x1, 0, L, P),
        ("grama", 0, 0, x0, P),
        ("grama", x0, y1, x1, P),
    ]
    # o recuo frontal ajardinado e o que sobra da faixa da frente
    for cor, fx0, fy0, fx1, fy1 in faixas:
        if fx1 > fx0 and fy1 > fy0:
            out.append(_box("lote", fx0, fy0, -40, fx1, fy1, 0, CORES[cor]))
    out.append(_box("lote", x0, 0, -40, x1, y0, 0, CORES["grama"]))
    # radier: o sistema mais caro depois da estrutura, e a cena nunca o teve.
    # Vai com a espessura e a projecao reais, e com o engrossamento de borda
    # que R52 acrescentou — quem olha a cena de baixo tem de ver a mesma peca
    # que o orcamento paga.
    import nucleo.fundacao as fu
    import nucleo.geotecnia as gt
    c = fu.contorno(pj)
    rx = [a.x for a in pj.TERREO]
    rxe = [a.x + a.w for a in pj.TERREO]
    ry = [a.y for a in pj.TERREO]
    rye = [a.y + a.h for a in pj.TERREO]
    bal = pj.RADIER["balanco_borda"]
    out.append(_box("radier", min(rx) - bal, min(ry) - bal,
                    -pj.RADIER["espessura"], max(rxe) + bal, max(rye) + bal, 0,
                    CORES["radier"], f"radier {pj.RADIER['espessura']} mm"))
    # reservatorio de retencao: enterrado, aparece a tampa e o volume em
    # transparencia — e o unico jeito de um enterrado existir numa cena
    tc = next((t for t in pj.TECNICOS if t["cod"] == "TC-03"), None)
    if tc:
        r = pl.retencao(pj)
        out.append(_box("reservatorio", tc["x"], tc["y"],
                        -tc.get("prof", 1_400), tc["x"] + tc["w"],
                        tc["y"] + tc["h"], -100, CORES["reservatorio"],
                        f"TC-03 {r['volume_m3']:.1f} m3"))
    return out


def _mobiliario() -> list[dict]:
    out = []
    alturas = {"bancada": 900, "armario alto": 2_200, "prateleiras": 1_800,
               "geladeira": 1_900, "lavadora": 850, "secadora": 850,
               "lava-loucas": 850, "lixo": 600, "forno": 600, "micro-ondas": 400,
               "box": 2_000, "tanque": 900, "vaso": 400, "lavatorio": 850,
               "guarda-roupa": 2_200, "gaveteiro": 900, "rouparia": 2_200}
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
    # R60 — camas, sofa, mesa e TV vem do LAYOUT do modelo, nao de tres
    # coordenadas escritas aqui. Ate R59 a cama da suite 02 estava na cena em
    # (4.200, 14.400) e no modelo em (5.725, 14.000); a da master a 2,6 m de
    # onde a planta de layout a desenha. "Existe no modelo, o 3D desenha
    # outra coisa" — a mesma doenca que R31 achou na escada.
    alt_layout = {"cama": 550, "sofa": 750, "poltrona": 750, "mesa": 750,
                  "rack": 450, "carro": 1_450, "tapete": 15}
    for l in pj.LAYOUT:
        pav = pav_de(l["amb"])
        z0 = Z[pav]["piso"]
        if l["tipo"] == "tv":
            # painel de TV: na parede, a 900 mm do piso, nao no chao
            out.append(_box("mob", l["x"], l["y"], z0 + 900, l["x"] + l["w"],
                            l["y"] + l["h"], z0 + 1_700, "#2b2f33", l["cod"]))
            continue
        out.append(_box("mob", l["x"], l["y"], z0, l["x"] + l["w"], l["y"] + l["h"],
                        z0 + alt_layout.get(l["tipo"], 600),
                        "#8e959c" if l["tipo"] == "carro" else CORES["mob"], l["cod"]))
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


def _luz() -> list[dict]:
    """Luminarias na cota do forro — da luminotecnica, o mesmo que a PR-16."""
    import nucleo.luminotecnica as lu
    out = []
    for q in lu.pontos(pj):
        z0 = Z[q["pav"]]["piso"]
        cor = CORES.get(f"luz_{q['tcor']}", CORES["luz_3000"])
        if "seg" in q:
            x0, y0, x1, y1 = q["seg"]
            hz = y0 == y1
            out.append(_box("luz", min(x0, x1) - (0 if hz else 40), min(y0, y1) - (40 if hz else 0),
                            z0 + q["z"] - 40, max(x0, x1) + (0 if hz else 40),
                            max(y0, y1) + (40 if hz else 0), z0 + q["z"], cor, q["cod"]))
        else:
            x, y = q["p"]
            r = 70 if q["tipo"] != "balizador" else 40
            z = z0 + q["z"]
            out.append(_box("luz", x - r, y - r, z - 20, x + r, y + r, z, cor, q["cod"]))
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
        externo=_externos() + _lote(), mob=_mobiliario(), escada=_escada(),
        ambientes=_ambientes(), cenas=CENAS, cores=CORES,
        luz=_luz(),
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
# R53 — a paleta saiu daqui: vive em nucleo/cores.py, a mesma que a tela e a
# prancha leem. Havia tres tabelas para o mesmo fato.
from nucleo.cores import CORES_PECA as CORES_LSF


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

    cfg = pn.Config(altura=pj.PE_DIREITO)
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

    # ---- escada: vigas de lance e degraus. Foram esquecidas aqui quando
    # entraram na cadeia de pecas, e a verificacao de coerencia de modelo pegou
    # na primeira execucao: 22 pecas que o produto tinha e o desenho nao.
    esc = ps.estruturar_escada(pj, aco, cfg)
    for q in esc["pecas"]:
        bw = pn.bw(q["perfil"])
        z0 = q["nivel"]
        if q["familia"] == "degrau":
            x0, x1 = q["x"], q["x"] + q["comp"]
            y0, y1 = q["y"], q["y"] + pj.ESCADA["piso"]
            alt = 50
        else:
            x0, x1 = q["x"], q["x"] + 50
            y0, y1 = q["y"], q["y"] + q["comp"]
            alt = bw
        b = _box("lsf", x0, y0, z0, x1, y1, z0 + alt,
                 CORES_LSF.get(q["familia"], "#b0562f"))
        b.update(cod=q["cod"], fam=q["familia"], perf=q["perfil"],
                 painel=q["plano"], pav="E", comp=q["comp"])
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
