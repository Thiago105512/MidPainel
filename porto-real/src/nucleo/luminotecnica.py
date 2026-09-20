"""LUMINOTECNICA — o ponto de luz deixa de ser regra de area e vira calculo.

Ate R58 a luminaria entrava no orcamento por "um ponto a cada 6 m2, minimo um
por ambiente" — regra declarada, marcada (H), e a UNICA quantidade das sete
frentes de acabamento que nao era consequencia de geometria. A pendencia 13
existia para isso. Este modulo a fecha pelo METODO DOS LUMENS, que e o que
qualquer projetista faria antes de comprar uma luminaria:

    fluxo necessario = E . A / (CU . FM)

E e a iluminancia-alvo do uso, A a area, CU o coeficiente de utilizacao (quanto
do fluxo emitido chega ao plano de trabalho, funcao do indice do local e das
refletancias) e FM o fator de manutencao. O numero de luminarias e o fluxo
necessario dividido pelo fluxo de UMA luminaria declarada — e depois conferido
contra o espacamento maximo que garante uniformidade (SHR), porque uma sala
de 25 m2 com duas luminarias potentes tem os lumens certos e o teto errado.

O QUE E DADO E O QUE E HIPOTESE. A iluminancia por uso e norma: NBR ISO/CIE
8995-1 onde ha tarefa visual (cozinha, bancada, escritorio, oficina) e, para
os usos residenciais que a 8995-1 nao cobre, os valores consolidados da
antiga NBR 5413 — declarados um a um na tabela, com a origem ao lado. O CU
por indice do local e tabela tipica de downlight LED com refletancias 70/50/20
(teto claro, parede clara, piso medio): e hipotese (H) de catalogo, e esta
marcada. As luminarias sao tipos genericos com fluxo e potencia declarados,
nao produtos — produto e cotacao.

CONFORTO E ESTETICA NAO SAO ADJETIVO AQUI, SAO REGRA. Temperatura de cor por
uso: 2.700 K no intimo (melatonina nao negocia), 3.000 K no social, 4.000 K
onde se corta, cozinha ou trabalha — nunca 6.500 K numa casa. Onde o forro e
absorvente perfurado (gourmet), nao se embute downlight: fura-se o painel que
existe para nao ser furado. Vai pendente ou sobrepor. E tarefa tem luz
propria: bancada de cozinha, espelho de lavatorio e closet recebem linear
dedicado, porque luz geral de teto ilumina a cabeca de quem esta de costas
para a parede — e projeta a sombra dela exatamente onde a tarefa esta.
"""
from __future__ import annotations

import math

# ------------------------------------------------- iluminancia-alvo por uso
# (lux, origem). O uso vem da CATEGORIA do ambiente e do nome da subdivisao.
ALVO = {
    "intimo":     (150, "NBR 5413 tab. — dormitorio, iluminacao geral"),
    "social":     (200, "NBR 5413 tab. — sala de estar/jantar, geral"),
    "cozinha":    (300, "NBR ISO/CIE 8995-1 — cozinha, geral"),
    "bancada":    (500, "NBR ISO/CIE 8995-1 — area de preparo (tarefa)"),
    "banho":      (200, "NBR 5413 tab. — banheiro, geral"),
    "espelho":    (300, "NBR 5413 tab. — banheiro, espelho (tarefa)"),
    "closet":     (200, "NBR 5413 tab. — quarto de vestir"),
    "office":     (300, "NBR ISO/CIE 8995-1 — escritorio, geral (500 na tarefa, por luminaria de mesa)"),
    "servico":    (200, "NBR 5413 tab. — lavanderia / deposito"),
    "oficina":    (500, "NBR ISO/CIE 8995-1 — trabalho manual medio"),
    "circulacao": (100, "NBR 5413 tab. — corredor e hall"),
    "escada":     (150, "NBR 5413 tab. — escada, minimo com seguranca"),
    "apoio":      (75,  "NBR 5413 tab. — garagem residencial"),
}
# temperatura de cor por uso — regra de conforto, declarada
TCOR = {"intimo": 2700, "social": 3000, "cozinha": 4000, "bancada": 4000,
        "banho": 3000, "espelho": 4000, "closet": 3000, "office": 4000,
        "servico": 4000, "oficina": 4000, "circulacao": 3000, "escada": 3000,
        "apoio": 4000}

PLANO_TRABALHO = {"circulacao": 0.0, "escada": 0.0, "apoio": 0.0}  # demais 0,75 m
PLANO_PADRAO = 0.75
FM = 0.80                       # LED, ambiente limpo, manutencao anual
SHR_MAX = 1.20                  # espacamento/altura de montagem para uniformidade

# (H) CU por indice do local K, downlight LED, refletancias 70/50/20
CU_TABELA = [(0.6, 0.36), (0.8, 0.44), (1.0, 0.50), (1.25, 0.55), (1.5, 0.59),
             (2.0, 0.64), (2.5, 0.68), (3.0, 0.71), (4.0, 0.74), (5.0, 0.76)]

# Tipos genericos de luminaria: fluxo (lm), potencia (W), preco (H). Cada
# FAMILIA vai do menor ao maior fluxo: o calculo escolhe a MENOR luminaria
# que, na quantidade que a malha de uniformidade exige, entrega o fluxo — e
# nao a quantidade de luminarias fracas que o fluxo exigiria. A diferenca e
# entre um teto com seis pontos e um teto com doze, para os mesmos lux. Um
# teto de dormitorio com doze downlights e o "aeroporto" que todo projetista
# reconhece e nenhum morador pediu.
LUMINARIAS = {
    "downlight-7":  dict(nome="Downlight LED embutido 7 W", lm=650, w=7.0, preco=62.0),
    "downlight-12": dict(nome="Downlight LED embutido 12 W", lm=1_000, w=12.0, preco=95.0),
    "downlight-18": dict(nome="Downlight LED embutido 18 W", lm=1_700, w=18.0, preco=128.0),
    "downlight-24": dict(nome="Downlight LED embutido 24 W", lm=2_400, w=24.0, preco=165.0),
    "sobrepor-10":  dict(nome="Plafon LED de sobrepor 10 W", lm=900, w=10.0, preco=88.0),
    "sobrepor-18":  dict(nome="Plafon LED de sobrepor 18 W", lm=1_500, w=18.0, preco=140.0),
    "sobrepor-24":  dict(nome="Plafon LED de sobrepor 24 W", lm=2_400, w=24.0, preco=175.0),
    "pendente-40":  dict(nome="Pendente LED de pe-direito duplo, 40 W", lm=4_000, w=40.0, preco=420.0),
    "linear":       dict(nome="Perfil linear LED 18 W/m com difusor (tarefa)", lm=1_600,
                         w=18.0, preco=210.0),   # por metro
    "arandela":     dict(nome="Arandela LED IP44 de espelho, 8 W", lm=700, w=8.0, preco=160.0),
    "balizador":    dict(nome="Balizador LED de escada, 3 W", lm=120, w=3.0, preco=85.0),
}
FAMILIA = {"embutir": ("downlight-7", "downlight-12", "downlight-18", "downlight-24"),
           "sobrepor": ("sobrepor-10", "sobrepor-18", "sobrepor-24"),
           "pendente": ("pendente-40",)}
ALTURA_PENDENTE = 4.0           # m de forro acima disto, downlight nao chega: pendente
LARGURA_MIN_MALHA = 1.0         # m; abaixo disto nao e sala, e nicho: um linear
EFICACIA_MIN = 80.0             # lm/W — abaixo disto a luminaria nao e LED de linha
# Onde o forro e absorvente/perfurado, a luminaria geral e de sobrepor.
FORRO_SEM_EMBUTIR = ("perfurado", "aparente")


def _cu(k: float) -> float:
    if k <= CU_TABELA[0][0]:
        return CU_TABELA[0][1]
    for (k0, c0), (k1, c1) in zip(CU_TABELA, CU_TABELA[1:]):
        if k0 <= k <= k1:
            return c0 + (c1 - c0) * (k - k0) / (k1 - k0)
    return CU_TABELA[-1][1]


def _uso(pj, cod: str, cat: dict) -> str:
    if "/" in cod:
        nome = cod.split("/")[1].upper()
        for chave in ("BANHO", "LAVABO", "CLOSET", "OFFICE", "DESPENSA"):
            if chave in nome:
                return {"BANHO": "banho", "LAVABO": "banho", "CLOSET": "closet",
                        "OFFICE": "office", "DESPENSA": "servico"}[chave]
        return "servico"
    if cod == "T-COZ":
        return "cozinha"
    if cod == "T-COR":
        return "escada"
    return cat.get(cod, "apoio")


def _geom(pj, cod: str) -> tuple:
    a = next((x for x in pj.TERREO + pj.SUPERIOR if x.cod == cod), None)
    if a is not None:
        return a.w / 1000.0, a.h / 1000.0
    d = next((x for x in pj.SUBDIVISOES if f"{x['pai']}/{x['nome']}" == cod), None)
    return (d["w"] / 1000.0, d["h"] / 1000.0) if d else (0.0, 0.0)


def _rect(pj, cod: str) -> tuple:
    """(x, y, w, h) em mm do ambiente ou da subdivisao."""
    a = next((x for x in pj.TERREO + pj.SUPERIOR if x.cod == cod), None)
    if a is not None:
        return a.x, a.y, a.w, a.h
    d = next((x for x in pj.SUBDIVISOES if f"{x['pai']}/{x['nome']}" == cod), None)
    return (d["x"], d["y"], d["w"], d["h"]) if d else (0, 0, 0, 0)


def _dentro_de_subdivisao(pj, cod: str, x: float, y: float) -> bool:
    for d in pj.SUBDIVISOES:
        if d["pai"] == cod and d["x"] <= x <= d["x"] + d["w"] and d["y"] <= y <= d["y"] + d["h"]:
            return True
    return False


def _malha(pj, cod: str, s_max: float, minimo: int = 0) -> list:
    """Pontos da malha de luminarias sobre a geometria REAL do ambiente.

    Colunas e linhas saem do espacamento maximo de uniformidade; os pontos que
    caem dentro de uma subdivisao (banho, closet, office) sao descartados —
    eles pertencem a subdivisao, que tem malha propria. Se o fluxo pedir mais
    pontos do que a malha tem, a malha adensa no eixo maior ate caber.
    """
    x, y, w, h = _rect(pj, cod)
    if w <= 0 or h <= 0:
        return []
    cols = max(1, math.ceil(w / 1000.0 / s_max))
    rows = max(1, math.ceil(h / 1000.0 / s_max))
    pai = "/" not in cod
    for _ in range(12):
        pts = []
        for i in range(cols):
            for j in range(rows):
                px = x + w * (i + 0.5) / cols
                py = y + h * (j + 0.5) / rows
                if pai and _dentro_de_subdivisao(pj, cod, px, py):
                    continue
                pts.append((px, py))
        if len(pts) >= max(minimo, 1):
            return pts
        if w / cols >= h / rows:
            cols += 1
        else:
            rows += 1
    return pts


def _forro_h(pj, cod: str, acab: dict) -> float:
    if cod == "T-COR":
        # o core e aberto ate a cobertura: a luminaria pendura do pe-direito
        # duplo, nao do forro que o quadro de acabamentos lhe atribui
        return (pj.PISO_A_PISO + pj.PE_DIREITO) / 1000.0
    ac = acab.get(cod)
    if ac and ac.get("forro_h"):
        return ac["forro_h"] / 1000.0
    return pj.PE_DIREITO / 1000.0


def _subdiv_area(pj, cod: str) -> float:
    return sum(d["w"] * d["h"] for d in pj.SUBDIVISOES if d["pai"] == cod) / 1e6


def _escolher(familia: str, fluxo: float, n_malha: int) -> tuple:
    """A menor luminaria da familia que, em n_malha pontos, entrega o fluxo."""
    tipos = FAMILIA[familia]
    for t in tipos:
        if n_malha * LUMINARIAS[t]["lm"] >= fluxo:
            return t, n_malha
    t = tipos[-1]
    return t, max(n_malha, math.ceil(fluxo / LUMINARIAS[t]["lm"]))


def geral(pj, cat: dict, acab: dict) -> list[dict]:
    """Iluminacao GERAL, ambiente a ambiente e subdivisao a subdivisao."""
    out = []
    ambientes = [(a.cod, a.nome) for a in pj.TERREO + pj.SUPERIOR]
    subs = [(f"{d['pai']}/{d['nome']}", f"{d['nome']} da {d['pai']}")
            for d in pj.SUBDIVISOES]
    for cod, nome in ambientes + subs:
        L, W = _geom(pj, cod)
        bruta = L * W
        area = bruta - (_subdiv_area(pj, cod) if "/" not in cod else 0.0)
        if area <= 0:
            continue
        if area < bruta:
            # o pai perde a area das filhas; a malha usa um retangulo
            # EQUIVALENTE de mesma proporcao, nao as dimensoes brutas — senao
            # a suite master e iluminada como se o banho e o closet fossem
            # dormitorio
            f = math.sqrt(area / bruta)
            L, W = L * f, W * f
        uso = _uso(pj, cod, cat)
        E, origem = ALVO[uso]
        h_forro = _forro_h(pj, cod, acab)
        h_m = h_forro - PLANO_TRABALHO.get(uso, PLANO_PADRAO)
        k = (L * W) / (h_m * (L + W)) if h_m > 0 else 1.0
        cu = _cu(k)
        fluxo = E * area / (cu * FM)
        forro_txt = (acab.get(cod) or {}).get("forro", "").lower()
        familia = "sobrepor" if any(t in forro_txt for t in FORRO_SEM_EMBUTIR) else "embutir"
        if h_forro > ALTURA_PENDENTE:
            familia = "pendente"
        if min(L, W) < LARGURA_MIN_MALHA:
            # nicho (closet de 600 mm, despensa estreita): um linear no
            # comprimento, nao uma malha de pontos
            # o linear tem o comprimento que o FLUXO pede, nao o do nicho
            # inteiro: 2,4 m de perfil num guarda-roupa de 600 mm sao 770 lux
            # onde 200 bastam. Arredonda a 300 mm, minimo 600.
            lum = LUMINARIAS["linear"]
            m = min(max(L, W), max(0.6, math.ceil(fluxo / lum["lm"] / 0.3) * 0.3))
            E_ob = m * lum["lm"] * cu * FM / area
            rx, ry, rw, rh = _rect(pj, cod)
            horizontal = rw >= rh
            cx, cy = rx + rw / 2, ry + rh / 2
            seg = ((cx - m * 500, cy, cx + m * 500, cy) if horizontal
                   else (cx, cy - m * 500, cx, cy + m * 500))
            out.append(dict(cod=cod, nome=nome, uso=uso, area=round(area, 2),
                            E_alvo=E, origem=origem, k=round(k, 2), cu=round(cu, 3),
                            h_m=round(h_m, 2), fluxo_lm=round(fluxo), tipo="linear",
                            luminaria=lum["nome"], n=1, m=round(m, 2),
                            segmento=[round(v) for v in seg],
                            n_malha=1, E_obtido=round(E_ob), w=round(m * lum["w"], 1),
                            w_m2=round(m * lum["w"] / area, 2), tcor=TCOR[uso],
                            preco=lum["preco"]))
            continue
        # pendente a 5,6 m: a malha e pelo VAO, nao pela altura (um pendente
        # por lance de escada e um no patamar e o que se pendura de verdade)
        s_max = SHR_MAX * h_m if familia != "pendente" else max(L, W) / 2
        # R60 — a malha deixa de ser uma CONTA (cols x rows) e vira PONTOS
        # sobre a geometria real do ambiente, descontadas as subdivisoes.
        # E a mesma lista que a prancha de forro desenha e que a cena 3D
        # mostra: um ponto que nao existe aqui nao existe em lugar nenhum.
        pts = _malha(pj, cod, s_max)
        n_malha = max(1, len(pts))
        tipo, n = _escolher(familia, fluxo, n_malha)
        if n > len(pts):
            pts = _malha(pj, cod, s_max, minimo=n)
            n = len(pts)
        lum = LUMINARIAS[tipo]
        E_ob = n * lum["lm"] * cu * FM / area
        out.append(dict(cod=cod, nome=nome, uso=uso, area=round(area, 2),
                        E_alvo=E, origem=origem, k=round(k, 2), cu=round(cu, 3),
                        h_m=round(h_m, 2), fluxo_lm=round(fluxo), tipo=tipo,
                        luminaria=lum["nome"], n=n, m=0.0, n_malha=n_malha,
                        pontos=[(round(x), round(y)) for x, y in pts],
                        E_obtido=round(E_ob), w=round(n * lum["w"], 1),
                        w_m2=round(n * lum["w"] / area, 2), tcor=TCOR[uso],
                        preco=lum["preco"]))
    return out


def tarefa(pj) -> list[dict]:
    """Luz de tarefa: bancada, espelho, closet, escada — de onde a tarefa esta."""
    out = []
    for b in pj.BANCADAS:
        if b.get("tipo") == "tanque":
            continue
        m = max(b["w"], b["h"]) / 1000.0
        cx, cy = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
        seg = ((b["x"], cy, b["x"] + b["w"], cy) if b["w"] >= b["h"]
               else (cx, b["y"], cx, b["y"] + b["h"]))
        out.append(dict(cod=f"LT-{b['cod']}", onde=f"bancada {b['cod']} ({b['amb']})",
                        amb=b["amb"], segmento=[round(v) for v in seg],
                        tipo="linear", m=round(m, 2), n=1, tcor=4000,
                        regra="perfil sob o armario superior, todo o comprimento da bancada"))
    for l in pj.LOUCAS:
        if l["tipo"] == "lavatorio":
            larg = max(l["w"], l["h"]) / 1000.0
            n = 2 if larg >= 1.2 else 1
            out.append(dict(cod=f"LT-{l['cod']}", onde=f"espelho do lavatorio {l['cod']} ({l['amb']})",
                            amb=l["amb"], pontos=[(round(l["x"] + l["w"] / 2), round(l["y"] + l["h"] / 2))] * n,
                            tipo="arandela", n=n, m=0.0, tcor=4000,
                            regra="uma arandela por lado do espelho; duas em cuba dupla"))
    for d in pj.SUBDIVISOES:
        if "CLOSET" in d["nome"].upper() and d["w"] * d["h"] >= 4e6:
            cx, cy = d["x"] + d["w"] / 2, d["y"] + d["h"] / 2
            seg = ((d["x"], cy, d["x"] + d["w"], cy) if d["w"] >= d["h"]
                   else (cx, d["y"], cx, d["y"] + d["h"]))
            out.append(dict(cod=f"LT-{d['pai']}-CLOSET", onde=f"closet da {d['pai']}",
                            amb=f"{d['pai']}/{d['nome']}", segmento=[round(v) for v in seg],
                            tipo="linear", m=round(max(d["w"], d["h"]) / 1000.0, 2), n=1,
                            tcor=3000, regra="linear sobre o cabideiro, IRC >= 90 para cor de roupa"))
    for d in pj.SUBDIVISOES:
        if "OFFICE" in d["nome"].upper():
            cx, cy = d["x"] + d["w"] / 2, d["y"] + d["h"] / 2
            out.append(dict(cod=f"LT-{d['pai']}-OFFICE", onde=f"mesa do office da {d['pai']}",
                            amb=f"{d['pai']}/{d['nome']}",
                            segmento=[round(cx - 600), round(cy), round(cx + 600), round(cy)],
                            tipo="linear", m=1.2, n=1, tcor=4000,
                            regra="linear sobre a mesa: os 500 lux da 8995-1 sao na TAREFA, "
                                  "nao no comodo inteiro"))
    esc = pj.ESCADA_EXEC
    degraus = esc["lances"] * esc["espelhos_lance"]
    core = next((a for a in pj.TERREO if a.cod == "T-COR"), None)
    nb = max(2, degraus // 3)
    pts = []
    if core is not None:
        for i in range(nb):
            t = (i + 0.5) / nb
            pts.append((round(core.x + 150), round(core.y + core.h * t)))
    out.append(dict(cod="LT-ESCADA", onde="escada (balizadores)", tipo="balizador",
                    amb="T-COR", pontos=pts,
                    n=nb, m=0.0, tcor=3000,
                    regra="um balizador a cada tres degraus, aceso por sensor a noite"))
    return out


def levantar(pj) -> dict:
    import especificacao as _ep     # so a categoria; o dado esta em pj
    cat = _ep.CATEGORIA
    acab = {a["amb"]: a for a in pj.acabamentos()}
    g = geral(pj, cat, acab)
    t = tarefa(pj)
    w_geral = sum(x["w"] for x in g)
    area = sum(x["area"] for x in g)
    return dict(geral=g, tarefa=t, n_geral=sum(x["n"] for x in g),
                w_geral=round(w_geral, 1), w_m2=round(w_geral / area, 2),
                area=round(area, 1))


def compras(pj) -> list[dict]:
    """Linhas de BOM: uma por tipo de luminaria, contadas do calculo."""
    lv = levantar(pj)
    por_tipo: dict = {}
    metros = 0.0
    for x in lv["geral"]:
        if x["tipo"] == "linear":
            metros += x["m"]
        else:
            por_tipo[x["tipo"]] = por_tipo.get(x["tipo"], 0) + x["n"]
    for t in lv["tarefa"]:
        if t["tipo"] == "linear":
            metros += t["m"]
        else:
            por_tipo[t["tipo"]] = por_tipo.get(t["tipo"], 0) + t["n"]
    out = []
    for tipo, n in por_tipo.items():
        lum = LUMINARIAS[tipo]
        out.append(dict(sku=f"LUM-{tipo.upper().replace('-', '')}", descricao=lum["nome"], unidade="un",
                        quantidade=n, preco=lum["preco"],
                        origem="metodo dos lumens por ambiente + malha de uniformidade "
                               "(SHR 1,2) + luz de tarefa contada das pecas"))
    if metros:
        lum = LUMINARIAS["linear"]
        out.append(dict(sku="LUM-LINEAR", descricao=lum["nome"], unidade="m",
                        quantidade=round(metros, 1), preco=lum["preco"],
                        origem="comprimento de bancada e de closet, do modelo"))
    return out


def conferir(pj) -> list[tuple[str, str, bool]]:
    lv = levantar(pj)
    g = lv["geral"]
    abaixo = [x["cod"] for x in g if x["E_obtido"] < x["E_alvo"]]
    # eficacia: a potencia instalada nao pode passar do que o fluxo pede a
    # 80 lm/W — e o que separa "ambiente de tarefa" de "luminaria ruim"
    densos = [x["cod"] for x in g
              if x["w"] > (x["m"] * LUMINARIAS["linear"]["lm"] if x["tipo"] == "linear"
                           else x["n"] * LUMINARIAS[x["tipo"]]["lm"]) / EFICACIA_MIN * 1.05]
    # a previsao da NBR 5410 (VA por area) tem de cobrir a potencia calculada
    prev = {p["amb"]: p["ilum_va"] for p in pj.previsao_iluminacao_tug()}
    w_por_amb: dict = {}
    for x in g:
        w_por_amb[x["cod"].split("/")[0]] = w_por_amb.get(x["cod"].split("/")[0], 0) + x["w"]
    curto = [c for c, w in w_por_amb.items() if prev.get(c, 0) and w > prev[c]]
    perf = [x["cod"] for x in g if x["tipo"].startswith("sobrepor")]
    return [
        ("todo ambiente atinge a iluminancia-alvo",
         f"{len(g)} ambientes e subdivisoes; abaixo do alvo: {abaixo or 'nenhum'}",
         not abaixo),
        ("eficacia de LED de linha em toda luminaria",
         f"{lv['w_m2']} W/m2 medio; abaixo de {EFICACIA_MIN:.0f} lm/W: {densos or 'nenhum'}",
         not densos),
        ("a previsao de carga da NBR 5410 cobre a potencia calculada",
         f"ambientes com W calculado acima do VA previsto: {curto or 'nenhum'}", not curto),
        ("forro perfurado nao recebe embutido",
         f"sobrepor em: {perf or 'nenhum'}", True),
        ("luz de tarefa existe onde ha tarefa",
         f"{len(lv['tarefa'])} pontos de tarefa (bancada, espelho, closet, escada)",
         len(lv["tarefa"]) > 0),
    ]


def pontos(pj) -> list[dict]:
    """Toda luminaria com posicao: a prancha de forro e a cena 3D leem daqui.

    Cada item: cod (ambiente ou LT-xxx), pav, tipo, tcor, z (cota em mm acima
    do piso do pavimento), e ou `p` [x, y] (ponto) ou `seg` [x0, y0, x1, y1].
    """
    acab = {a["amb"]: a for a in pj.acabamentos()}
    lv = levantar(pj)
    out = []
    def pav_de(cod):
        return "S" if cod.startswith("S-") else "T"
    for x in lv["geral"]:
        z = round(_forro_h(pj, x["cod"], acab) * 1000)
        if x["tipo"] == "linear":
            out.append(dict(cod=x["cod"], pav=pav_de(x["cod"]), tipo="linear",
                            tcor=x["tcor"], z=z, seg=x["segmento"], geral=True))
        else:
            for px, py in x["pontos"]:
                out.append(dict(cod=x["cod"], pav=pav_de(x["cod"]), tipo=x["tipo"],
                                tcor=x["tcor"], z=z, p=[px, py], geral=True))
    for t in lv["tarefa"]:
        amb = t.get("amb", "")
        z = round(_forro_h(pj, amb.split("/")[0] if amb else "T-SOC", acab) * 1000)
        if t["tipo"] == "linear":
            out.append(dict(cod=t["cod"], pav=pav_de(amb), tipo="linear", tcor=t["tcor"],
                            z=z, seg=t["segmento"], geral=False))
        elif t["tipo"] == "arandela":
            for px, py in t["pontos"]:
                out.append(dict(cod=t["cod"], pav=pav_de(amb), tipo="arandela",
                                tcor=t["tcor"], z=1900, p=[px, py], geral=False))
        elif t["tipo"] == "balizador":
            for px, py in t["pontos"]:
                out.append(dict(cod=t["cod"], pav="T", tipo="balizador", tcor=t["tcor"],
                                z=300, p=[px, py], geral=False))
    return out
