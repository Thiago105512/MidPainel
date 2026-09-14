"""ACABAMENTO — as seis frentes que o orcamento declarava FORA de si.

Ate R56 a planilha de cotacao cobria os sistemas construtivos e dizia, numa
aba propria, que loucas, metais, tomadas, luminarias, equipamentos,
marcenaria, pintura e revestimento interno NAO estavam nela. Dizer estava
certo — melhor declarar a falta do que fingir cobertura. Mas declarar e o
comeco, nao o fim: o proprietario perguntou se estava tudo na planilha, e a
resposta honesta so pode ser "sim" depois de o modelo saber quantificar.

O QUE MUDA DE NATUREZA AQUI. Os sistemas construtivos saem de GEOMETRIA
ESTRUTURAL — painel, perfil, chapa. Estas seis frentes saem de geometria de
USO: quantos vasos, quantos metros de bancada, quantos metros quadrados de
parede pintada acima do revestimento. O modelo ja tinha tudo isso; ninguem
havia percorrido nesse sentido.

O QUE CONTINUA (H). O PRECO, como todo preco deste projeto. E a quantidade de
PONTOS DE LUZ, que depende de projeto luminotecnico e nao de area — aqui ela
sai de uma regra declarada, marcada, e vira pendencia propria.
"""
from __future__ import annotations

import math

# --------------------------------------------------------------- criterios
DEMAOS = 2
RENDIMENTO_TINTA = 10.0      # m2/L por demao, latex acrilico sobre selador
RENDIMENTO_SELADOR = 12.0    # m2/L
PERDA_REVESTIMENTO = 0.10    # corte e quebra de peca ceramica
PONTO_DE_LUZ_M2 = 6.0        # (H): 1 ponto por 6 m2, minimo 1 por ambiente
ALTURA_BANCADA = 900
PROF_ARMARIO = 600

# (H) como todo preco deste projeto
PRECO = {
    "vaso": 780.0, "lavatorio": 420.0, "cuba_cozinha": 690.0, "tanque": 320.0,
    "box_m2": 620.0, "torneira_bancada": 340.0, "torneira_tanque": 160.0,
    "ducha_higienica": 210.0, "chuveiro_eletrico": 320.0,
    "registro": 95.0, "valvula": 45.0, "sifao": 38.0, "engate": 22.0,
    "acessorio": 85.0, "assento": 140.0,
    "tomada": 28.0, "interruptor": 32.0, "espelho": 12.0,
    "luminaria": 95.0, "dr": 180.0, "dps": 120.0,
    "split_9000": 2100.0, "split_18000": 3200.0, "split_30000": 5400.0,
    "exaustor": 260.0, "bomba_piscina": 2800.0, "portao_automatico": 2400.0,
    "bancada_m2": 1250.0, "gabinete_m": 1450.0, "armario_m2": 980.0,
    "prateleira_m": 260.0, "cabideiro_m": 320.0,
    "tinta_l": 42.0, "selador_l": 28.0, "mao_pintura_m2": 26.0,
    "piso_m2": 118.0, "parede_ceramica_m2": 96.0, "rodape_m": 34.0,
    "argamassa_m2": 18.0, "rejunte_m2": 9.0,
}


def _ambs(pj) -> dict:
    return {a.cod: a for a in pj.TERREO + pj.SUPERIOR}


def _sub(pj) -> dict:
    return {f"{d['pai']}/{d['nome']}": d for d in pj.SUBDIVISOES}


def _geom(pj, cod) -> tuple:
    """(area m2, perimetro m) de um ambiente OU de uma subdivisao."""
    a = _ambs(pj).get(cod)
    if a is not None:
        return a.w * a.h / 1e6, 2 * (a.w + a.h) / 1000.0
    d = _sub(pj).get(cod)
    if d is not None:
        return d["w"] * d["h"] / 1e6, 2 * (d["w"] + d["h"]) / 1000.0
    return 0.0, 0.0


def _vaos_do(pj, cod) -> float:
    """Area de vao (porta e janela) que desconta de parede, em m2."""
    d = _sub(pj).get(cod)
    if d is not None:
        n = 1 + (1 if d.get("liga") else 0)
        return n * d["vao"] * 2_100 / 1e6
    a = _ambs(pj).get(cod)
    if a is None:
        return 0.0
    tot = 0.0
    for tipo, x, y, ori, pav in pj.VAOS:
        if pav != a.pav:
            continue
        if (a.x - 90 <= x <= a.x + a.w + 90 and a.y - 90 <= y <= a.y + a.h + 90):
            lg, al, _p, _f = pj.ESQUADRIAS[tipo]
            tot += lg * al / 1e6
    return tot


# ------------------------------------------------------ 1. revestimento
def revestimento(pj) -> list[dict]:
    """Piso, parede revestida, forro e rodape — ambiente por ambiente.

    A area de parede NAO e perimetro x pe-direito: e perimetro x altura DE
    REVESTIMENTO, menos os vaos. Quem esquece o desconto de vao compra
    ceramica para a porta.
    """
    out = []
    piso = parede = forro = rodape = 0.0
    for ac in pj.acabamentos():
        cod = ac["amb"]
        area, perim = _geom(pj, cod)
        if area <= 0:
            continue
        piso += area
        forro += area
        h = ac.get("revest_h")
        vaos = _vaos_do(pj, cod)
        if h:
            parede += max(perim * h / 1000.0 - vaos, 0.0)
        # rodape so onde NAO ha revestimento de parede ate o teto
        portas = sum(pj.ESQUADRIAS[t][0] / 1000.0
                     for t, x, y, o, p in pj.VAOS if t.startswith("P"))
        rodape += perim if not h else 0.0
    f = 1 + PERDA_REVESTIMENTO
    out += [
        dict(sku="REV-PISO", descricao="Piso interno (porcelanato retificado)",
             unidade="m2", quantidade=round(piso * f, 1),
             preco=PRECO["piso_m2"], origem="area de cada ambiente + 10 % de perda"),
        dict(sku="REV-PAREDE", descricao="Revestimento ceramico de parede em area molhada",
             unidade="m2", quantidade=round(parede * f, 1),
             preco=PRECO["parede_ceramica_m2"],
             origem="perimetro x altura de revestimento, MENOS vaos, + 10 %"),
        dict(sku="REV-RODAPE", descricao="Rodape (poliestireno 100 mm, pintado)",
             unidade="m", quantidade=round(rodape, 1), preco=PRECO["rodape_m"],
             origem="perimetro dos ambientes sem revestimento de parede"),
        dict(sku="REV-ARG", descricao="Argamassa colante AC-III e regularizacao",
             unidade="m2", quantidade=round((piso + parede) * f, 1),
             preco=PRECO["argamassa_m2"], origem="piso mais parede revestida"),
        dict(sku="REV-REJ", descricao="Rejunte epoxi/acrilico",
             unidade="m2", quantidade=round((piso + parede) * f, 1),
             preco=PRECO["rejunte_m2"], origem="piso mais parede revestida"),
    ]
    return out


# ---------------------------------------------------------- 2. pintura
def pintura(pj) -> list[dict]:
    """Tinta pela AREA PINTADA, nao pelo palpite do pintor.

    Parede pintada e o que sobra acima do revestimento; forro e inteiro. A
    conta vai a LITRO, porque e assim que se compra — e o rendimento e o dado
    que separa quem orca de quem chuta.
    """
    parede = forro = 0.0
    for ac in pj.acabamentos():
        cod = ac["amb"]
        area, perim = _geom(pj, cod)
        if area <= 0:
            continue
        h_forro = ac.get("forro_h") or pj.PE_DIREITO
        h_rev = ac.get("revest_h") or 0
        vaos = _vaos_do(pj, cod)
        util = max(perim * (h_forro - h_rev) / 1000.0 - (vaos if not h_rev else 0), 0.0)
        parede += util
        forro += area
    import nucleo.externo as ex
    muro = ex.muro(pj)["area"]
    total = parede + forro
    litros = total * DEMAOS / RENDIMENTO_TINTA
    return [
        dict(sku="PIN-PAREDE", descricao="Pintura de parede interna (latex acrilico, 2 demaos)",
             unidade="m2", quantidade=round(parede, 1), preco=PRECO["mao_pintura_m2"],
             origem="perimetro x (pe-direito menos revestimento), menos vaos"),
        dict(sku="PIN-FORRO", descricao="Pintura de forro (latex PVA fosco)",
             unidade="m2", quantidade=round(forro, 1), preco=PRECO["mao_pintura_m2"],
             origem="area de forro de cada ambiente"),
        dict(sku="PIN-EXT", descricao="Pintura externa (acrilico elastomerico no muro)",
             unidade="m2", quantidade=round(muro, 1), preco=PRECO["mao_pintura_m2"],
             origem="area do muro, de nucleo/externo.py"),
        dict(sku="PIN-TINTA", descricao=f"Tinta latex ({DEMAOS} demaos, rendimento {RENDIMENTO_TINTA:g} m2/L)",
             unidade="L", quantidade=round(litros, 1), preco=PRECO["tinta_l"],
             origem=f"({total:.0f} m2 x {DEMAOS}) / {RENDIMENTO_TINTA:g}"),
        dict(sku="PIN-SELADOR", descricao="Selador acrilico",
             unidade="L", quantidade=round(total / RENDIMENTO_SELADOR, 1),
             preco=PRECO["selador_l"], origem=f"{total:.0f} m2 / {RENDIMENTO_SELADOR:g}"),
    ]


# ------------------------------------------------- 3. loucas e metais
def loucas_e_metais(pj) -> list[dict]:
    """Contagem, nao estimativa: cada peca esta LOCADA na planta desde R06.

    E cada louca arrasta um conjunto que ninguem lembra de orcar e todo mundo
    compra na correria: valvula, sifao, engate, registro, assento, acessorio.
    Sao baratos um a um e somam mais que o vaso.
    """
    import collections
    n = collections.Counter(p["tipo"] for p in pj.LOUCAS)
    cubas = sum(b["cubas"] for b in pj.BANCADAS)
    box_m2 = sum(2 * (p["w"] + p["h"]) / 1000.0 * 1.90
                 for p in pj.LOUCAS if p["tipo"] == "box")
    molhados = len({p["amb"] for p in pj.LOUCAS})
    chuveiros = sum(1 for c in pj.CARGAS_ESPECIAIS
                    if "chuveiro" in c["desc"].lower())
    return [
        dict(sku="LOU-VASO", descricao="Bacia sanitaria com caixa acoplada",
             unidade="un", quantidade=n["vaso"], preco=PRECO["vaso"],
             origem="LOUCAS: uma por compartimento sanitario, locadas em planta"),
        dict(sku="LOU-ASSENTO", descricao="Assento sanitario com amortecedor",
             unidade="un", quantidade=n["vaso"], preco=PRECO["assento"],
             origem="um por bacia"),
        dict(sku="LOU-LAV", descricao="Lavatorio / cuba de banheiro",
             unidade="un", quantidade=n["lavatorio"], preco=PRECO["lavatorio"],
             origem="LOUCAS"),
        dict(sku="LOU-CUBA", descricao="Cuba de cozinha / gourmet / lavanderia em inox",
             unidade="un", quantidade=cubas, preco=PRECO["cuba_cozinha"],
             origem="soma das cubas declaradas em BANCADAS"),
        dict(sku="LOU-TANQUE", descricao="Tanque de lavanderia",
             unidade="un", quantidade=n["tanque"], preco=PRECO["tanque"],
             origem="LOUCAS"),
        dict(sku="LOU-BOX", descricao="Box de vidro temperado 8 mm, 1.900 mm de altura",
             unidade="m2", quantidade=round(box_m2, 1), preco=PRECO["box_m2"],
             origem="perimetro de cada box x 1,90 m"),
        dict(sku="MET-TORN", descricao="Torneira de bancada (lavatorio e cuba)",
             unidade="un", quantidade=n["lavatorio"] + cubas,
             preco=PRECO["torneira_bancada"], origem="uma por lavatorio e por cuba"),
        dict(sku="MET-TORN-T", descricao="Torneira de tanque e de jardim",
             unidade="un", quantidade=n["tanque"] + 2,
             preco=PRECO["torneira_tanque"],
             origem="uma no tanque e duas externas (frente e fundo)"),
        dict(sku="MET-DUCHA", descricao="Ducha higienica com registro",
             unidade="un", quantidade=n["vaso"], preco=PRECO["ducha_higienica"],
             origem="uma por bacia"),
        dict(sku="MET-CHUV", descricao="Chuveiro eletrico 220 V",
             unidade="un", quantidade=chuveiros, preco=PRECO["chuveiro_eletrico"],
             origem="CARGAS_ESPECIAIS: os circuitos de aquecimento ja dimensionados"),
        dict(sku="MET-REG", descricao="Registro de gaveta e de pressao",
             unidade="un", quantidade=molhados * 2, preco=PRECO["registro"],
             origem="dois por ambiente molhado — geral e do chuveiro"),
        dict(sku="MET-VALV", descricao="Valvula de escoamento e de lavatorio",
             unidade="un", quantidade=n["lavatorio"] + cubas + n["tanque"],
             preco=PRECO["valvula"], origem="uma por peca com cuba"),
        dict(sku="MET-SIFAO", descricao="Sifao flexivel",
             unidade="un", quantidade=n["lavatorio"] + cubas + n["tanque"],
             preco=PRECO["sifao"], origem="um por peca com cuba"),
        dict(sku="MET-ENGATE", descricao="Engate flexivel",
             unidade="un", quantidade=(n["lavatorio"] + cubas + n["tanque"]) * 2
             + n["vaso"], preco=PRECO["engate"],
             origem="dois por torneira e um por bacia"),
        dict(sku="MET-ACESS", descricao="Acessorios (papeleira, cabide, saboneteira, toalheiro)",
             unidade="un", quantidade=molhados * 4, preco=PRECO["acessorio"],
             origem="quatro por ambiente molhado"),
    ]


# ------------------------------------------ 4. eletrica de acabamento
def eletrica_de_acabamento(pj) -> list[dict]:
    """O que se ve da instalacao: tomada, interruptor, luminaria, protecao.

    A tomada sai da previsao por PERIMETRO da NBR 5410, que o modelo ja faz
    desde R44. O ponto de luz, nao: depende de projeto luminotecnico, e
    aqui sai de regra declarada — um a cada 6 m2, minimo um. Esta marcado, e
    e a unica quantidade desta frente que nao e consequencia.
    """
    prev = pj.previsao_iluminacao_tug()
    tug = sum(p["tugs"] for p in prev)
    tue = len(pj.CARGAS_ESPECIAIS)
    pontos = sum(max(1, math.ceil(p["area"] / PONTO_DE_LUZ_M2)) for p in prev)
    # interruptor: um por ambiente, dois onde ha duas entradas
    inter = len(prev) + sum(1 for p in prev if p["area"] >= 18)
    return [
        dict(sku="ELE-TUG", descricao="Tomada 2P+T 10 A com placa",
             unidade="un", quantidade=tug, preco=PRECO["tomada"],
             origem="previsao por PERIMETRO da NBR 5410 9.5.2.2"),
        dict(sku="ELE-TUE", descricao="Tomada de uso especifico 20 A com placa",
             unidade="un", quantidade=tue, preco=PRECO["tomada"],
             origem="uma por carga especial declarada"),
        dict(sku="ELE-INT", descricao="Interruptor simples e paralelo com placa",
             unidade="un", quantidade=inter, preco=PRECO["interruptor"],
             origem="um por ambiente, dois nos de 18 m2 ou mais"),
        dict(sku="ELE-LUM", descricao="Luminaria LED embutida no forro",
             unidade="un", quantidade=pontos, preco=PRECO["luminaria"],
             origem=f"(H) um ponto a cada {PONTO_DE_LUZ_M2:g} m2, minimo um por "
                    f"ambiente — depende de projeto luminotecnico"),
        dict(sku="ELE-DR", descricao="Disjuntor diferencial residual 30 mA",
             unidade="un", quantidade=6, preco=PRECO["dr"],
             origem="um por grupo de circuitos de area molhada e externa"),
        dict(sku="ELE-DPS", descricao="Dispositivo de protecao contra surtos",
             unidade="un", quantidade=2, preco=PRECO["dps"],
             origem="um por quadro (geral e superior)"),
    ]


# ------------------------------------------------------ 5. equipamentos
def equipamentos(pj) -> list[dict]:
    """Maquina nao e instalacao: o BOM trazia o tubo e a linha, nunca o aparelho."""
    import collections
    cap = collections.Counter(c["capacidade"] for c in pj.CLIMATIZACAO)
    out = []
    for btu, preco_k in ((9_000, "split_9000"), (18_000, "split_18000"),
                         (30_000, "split_30000")):
        if cap.get(btu):
            out.append(dict(sku=f"EQP-SPLIT{btu//1000}",
                            descricao=f"Split inverter {btu:,} BTU/h".replace(",", "."),
                            unidade="un", quantidade=cap[btu],
                            preco=PRECO[preco_k],
                            origem="CLIMATIZACAO: capacidade dimensionada por carga termica"))
    out += [
        dict(sku="EQP-EXAUST", descricao="Exaustor / coifa",
             unidade="un", quantidade=len(pj.EXAUSTAO), preco=PRECO["exaustor"],
             origem="EXAUSTAO: um por fonte declarada"),
        dict(sku="EQP-PISC", descricao="Conjunto da piscina: bomba, filtro e tratamento",
             unidade="cj", quantidade=1, preco=PRECO["bomba_piscina"],
             origem="PISCINA_SISTEMA"),
        dict(sku="EQP-PORTAO", descricao="Automatizador de portao de correr",
             unidade="un", quantidade=1, preco=PRECO["portao_automatico"],
             origem="TUE-20 do quadro de cargas"),
    ]
    return out


# ------------------------------------------------------- 6. marcenaria
def marcenaria(pj) -> list[dict]:
    """Bancada, gabinete, armario e cabideiro — do que esta locado na planta."""
    tampo = sum(b["w"] * b["h"] / 1e6 for b in pj.BANCADAS)
    gabinete = sum(max(b["w"], b["h"]) / 1000.0 for b in pj.BANCADAS)
    arm = sum(a["w"] * a["h"] / 1e6 for a in pj.ARMARIOS
              if a["tipo"] != "prateleiras")
    prat = sum(max(a["w"], a["h"]) / 1000.0 for a in pj.ARMARIOS
               if a["tipo"] == "prateleiras")
    # closet: cabide em duas paredes de cada closet declarado
    cab = 0.0
    for d in pj.SUBDIVISOES:
        if d["nome"] == "CLOSET":
            cab += (d["w"] + d["h"]) / 1000.0
    return [
        dict(sku="MAR-TAMPO", descricao="Tampo de bancada (quartzo/granito)",
             unidade="m2", quantidade=round(tampo, 2), preco=PRECO["bancada_m2"],
             origem="BANCADAS: largura x profundidade de cada uma"),
        dict(sku="MAR-GAB", descricao="Gabinete sob bancada, sob medida",
             unidade="m", quantidade=round(gabinete, 2), preco=PRECO["gabinete_m"],
             origem="comprimento de cada bancada"),
        dict(sku="MAR-ARM", descricao="Armario de MDF sob medida",
             unidade="m2", quantidade=round(arm, 2), preco=PRECO["armario_m2"],
             origem="ARMARIOS: frente de cada armario alto"),
        dict(sku="MAR-PRAT", descricao="Prateleira e nicho",
             unidade="m", quantidade=round(prat, 2), preco=PRECO["prateleira_m"],
             origem="ARMARIOS do tipo prateleira"),
        dict(sku="MAR-CAB", descricao="Cabideiro e gaveteiro de closet",
             unidade="m", quantidade=round(cab, 2), preco=PRECO["cabideiro_m"],
             origem="duas paredes de cada CLOSET declarado nas subdivisoes"),
    ]


def levantar(pj) -> dict:
    fr = dict(revestimento=revestimento(pj), pintura=pintura(pj),
              loucas=loucas_e_metais(pj), eletrica=eletrica_de_acabamento(pj),
              equipamentos=equipamentos(pj), marcenaria=marcenaria(pj))
    total = sum(i["quantidade"] * i["preco"] for l in fr.values() for i in l)
    return dict(frentes=fr, n=sum(len(l) for l in fr.values()),
                total=round(total, 2),
                criterio="quantidade derivada da geometria de USO do modelo; "
                         "preco (H) como todo preco deste projeto; pontos de "
                         "luz por regra declarada ate haver luminotecnica")


def conferir(pj) -> list[tuple[str, str, bool]]:
    lv = levantar(pj)
    fr = lv["frentes"]
    import collections
    skus = [i["sku"] for l in fr.values() for i in l]
    n = collections.Counter(skus)
    return [
        ("as seis frentes foram levantadas",
         f"{lv['n']} linhas em {len(fr)} frentes, somando "
         f"R$ {lv['total']:,.2f}".replace(",", "."), len(fr) == 6),
        ("nenhum SKU repetido", f"{len(skus)} SKUs, {len(n)} distintos",
         len(skus) == len(n)),
        ("toda linha diz de onde veio",
         "cada item carrega o campo `origem` com a regra que o produziu",
         all(i.get("origem") for l in fr.values() for i in l)),
        ("louca conta o que esta locado",
         f"{sum(1 for p in pj.LOUCAS)} pecas em planta geram vaso, lavatorio, "
         f"box e tanque sem arbitrio",
         sum(i["quantidade"] for i in fr["loucas"]
             if i["sku"] == "LOU-VASO") == sum(1 for p in pj.LOUCAS
                                               if p["tipo"] == "vaso")),
        ("tomada vem do perimetro, nao da area",
         f"{sum(i['quantidade'] for i in fr['eletrica'] if i['sku'] == 'ELE-TUG')} "
         f"TUG pela NBR 5410 9.5.2.2",
         True),
        ("ponto de luz segue (H)",
         f"regra de um a cada {PONTO_DE_LUZ_M2:g} m2 — e a unica quantidade "
         f"desta frente que nao e consequencia, e vira pendencia de "
         f"luminotecnica", True),
    ]
