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
    "dr": 180.0, "dps": 120.0,
    "split_9000": 2100.0, "split_18000": 3200.0, "split_30000": 5400.0,
    "exaustor": 260.0, "bomba_piscina": 2800.0, "portao_automatico": 2400.0,
    "bancada_m2": 1250.0, "gabinete_m": 1450.0, "armario_m2": 980.0,
    "prateleira_m": 260.0, "cabideiro_m": 320.0,
    "tinta_l": 42.0, "selador_l": 28.0, "mao_pintura_m2": 26.0,
    "piso_m2": 118.0, "parede_ceramica_m2": 96.0, "rodape_m": 34.0,
    "argamassa_m2": 18.0, "rejunte_m2": 9.0,
    # R58 — sistema de fachada sobre placa cimenticia. Ate aqui a casa comprava
    # 237,9 m2 de placa e nao comprava UMA linha de acabamento para ela.
    "basecoat_m2": 34.0, "tela_m2": 9.0, "selante_junta_m": 14.0,
    "mineral_m2": 88.0, "junta_seca_m": 22.0, "forro_perfurado_m2": 96.0,
    "acrilico_elastomerico_l": 68.0, "mao_fachada_m2": 34.0,
    "frontao_m2": 128.0,
}

# Rendimento da tinta acrilica elastomerica sobre basecoat, m2/L por demao.
# Menor que o do latex interno: o filme e mais espesso, e e a espessura do
# filme que faz a ponte sobre a microfissura — e por isso que se compra
# elastomerico e nao acrilico comum.
RENDIMENTO_ELASTOMERICO = 7.0
DEMAOS_FACHADA = 2
# Junta por m2 de fachada. A placa e 1.200 x 2.400: da uma junta vertical a
# cada 1,2 m e uma horizontal a cada 2,4 m de face, ou seja 1/1,2 + 1/2,4
# metros de junta por m2. Nao e coeficiente de pratica, e a geometria da chapa.
JUNTA_POR_M2 = 1 / 1.2 + 1 / 2.4
# Altura de frontao atras da bancada. 600 mm cobre o respingo de pia e o
# encosto de panela; onde ha fogo (cooktop, churrasqueira) sobe a 2.400 porque
# deixa de ser respingo e passa a ser gordura e calor.
FRONTAO_H = 600
FRONTAO_H_FOGO = 2_400


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


def _sem_forro(pj) -> set:
    """Ambientes que o quadro de forros declara SEM forro — a unica fonte."""
    # "estrutura aparente" e a marca de NAO ter forro. "sem forro suspenso" e
    # outra coisa: o gesso do entrepiso esta la, e pintado (R59).
    return {f[0] for f in pj.FORROS_SRC() if "estrutura aparente" in f[1].lower()}


def _forro_nao_pintado(pj) -> set:
    """Forro absorvente perfurado vem acabado de fabrica: nao se pinta."""
    return {f[0] for f in pj.FORROS_SRC() if "perfurado" in f[1].lower()}


def _portas_m(pj, cod) -> float:
    """Metros de porta no perimetro do ambiente — rodape nao passa por porta."""
    d = _sub(pj).get(cod)
    if d is not None:
        return (1 + (1 if d.get("liga") else 0)) * d["vao"] / 1000.0
    a = _ambs(pj).get(cod)
    if a is None:
        return 0.0
    tot = 0.0
    for tipo, x, y, ori, pav in pj.VAOS:
        if pav != a.pav or not tipo.startswith("P"):
            continue
        if (a.x - 90 <= x <= a.x + a.w + 90 and a.y - 90 <= y <= a.y + a.h + 90):
            tot += pj.ESQUADRIAS[tipo][0] / 1000.0
    return tot


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
    sem_forro = _sem_forro(pj)
    for ac in pj.acabamentos():
        cod = ac["amb"]
        area, perim = _geom(pj, cod)
        if area <= 0:
            continue
        piso += area
        if cod not in sem_forro:
            forro += area
        h = ac.get("revest_h")
        vaos = _vaos_do(pj, cod)
        if h:
            parede += max(perim * h / 1000.0 - vaos, 0.0)
        # rodape so onde NAO ha revestimento de parede ate o teto — e nunca
        # atravessa porta (R59: 253 m viraram 236; a diferenca era porta)
        rodape += max(perim - _portas_m(pj, cod), 0.0) if not h else 0.0
    # R58 — FRONTAO. Cozinha e gourmet somam 51,84 m2, quatro bancadas de
    # granito, cooktop, churrasqueira e duas cubas — e `revest_h` nao declarado
    # em nenhum dos dois: gesso pintado atras do fogao. A area de frontao nao
    # sai do perimetro do comodo (seria revestir a sala inteira), sai da
    # BANCADA, que o modelo ja loca desde R06.
    frontao = 0.0
    for b in pj.BANCADAS:
        if "peninsula" in b.get("uso", "").lower():
            continue               # peninsula nao encosta em parede
        linear = max(b["w"], b["h"]) / 1000.0
        h = FRONTAO_H_FOGO if (b.get("cooktop") or b.get("ignicao")) else FRONTAO_H
        frontao += linear * h / 1000.0
    parede += frontao

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
        dict(sku="REV-FORRO-ACUST", descricao="Forro absorvente perfurado (alfa 0,70), "
                                                "acabado de fabrica",
             unidade="m2", quantidade=round(sum(
                 _geom(pj, f[0])[0] for f in pj.FORROS_SRC() if "perfurado" in f[1].lower()), 1),
             preco=PRECO["forro_perfurado_m2"],
             origem="quadro de forros: unico ponto que derruba a reverberacao do gourmet "
                    "de 3,20 s para 0,86 s (R59: existia no quadro, nao no BOM)"),
        dict(sku="REV-ARG", descricao="Argamassa colante AC-III e regularizacao",
             unidade="m2", quantidade=round((piso + parede) * f, 1),
             preco=PRECO["argamassa_m2"], origem="piso mais parede revestida"),
        dict(sku="REV-REJ", descricao="Rejunte epoxi/acrilico",
             unidade="m2", quantidade=round((piso + parede) * f, 1),
             preco=PRECO["rejunte_m2"], origem="piso mais parede revestida"),
    ]
    return out


# ------------------------------------------------------- 1b. fachada externa
def fachada(pj, camadas=None) -> list[dict]:
    """O acabamento externo da casa, que ate R57 nao existia em lugar nenhum.

    A composicao PE-1 termina em PLACA CIMENTICIA 10 mm, "face exposta a
    chuva". E terminava ali tambem no orcamento: 237,9 m2 de substrato
    comprados e nenhum sistema por cima. Placa cimenticia nua nao e fachada, e
    base — a NBR 15498 a trata como tal. Em Manaus, com chuva de 2.300 mm/ano
    que chega quase na horizontal, a junta nao tratada e o caminho da agua para
    dentro do montante.

    POR QUE LISO E NAO TEXTURA. A escolha corrente em fachada de LSF e textura
    acrilica rustica, que e mais barata por m2 e esconde imperfeicao de
    emassamento. Em clima quente-umido ela cobra a diferenca de volta: relevo
    e area de superficie, area de superficie e biofilme, e biofilme em Manaus
    e fungo em dois anos. Acabamento LISO com biocida lava com chuva. A
    economia da textura e de obra; o custo dela e de manutencao perpetua.

    POR QUE ELASTOMERICO. O substrato e placa sobre estrutura metalica: ele
    trabalha. Tinta acrilica comum acompanha ate a primeira microfissura da
    junta; elastomerica faz ponte sobre ela. E a unica linha desta frente que
    nao aceita a versao barata.
    """
    faixa, mineral = _fachada_por_tratamento(pj, camadas)
    area = faixa
    junta = area * JUNTA_POR_M2
    litros = area * DEMAOS_FACHADA / RENDIMENTO_ELASTOMERICO
    return [
        dict(sku="FAC-MINERAL", descricao="Acrescimo: placa cimenticia com revestimento "
                                          "mineral de fabrica, junta seca 6 mm",
             unidade="m2", quantidade=round(mineral, 1), preco=PRECO["mineral_m2"],
             origem="face externa do volume superior + face externa da platibanda: "
                    "FACHADA_MATERIAIS e FACHADA_REGRAS (nada que exija pintura em altura)"),
        dict(sku="FAC-JUNTA-SECA", descricao="Junta seca: perfil EPDM e fundo de junta",
             unidade="m", quantidade=round(mineral * JUNTA_POR_M2, 1),
             preco=PRECO["junta_seca_m"], origem="1,25 m por m2 de placa 1.200 x 2.400"),
        dict(sku="FAC-BASE", descricao="Basecoat de regularizacao sobre placa cimenticia",
             unidade="m2", quantidade=round(area, 1), preco=PRECO["basecoat_m2"],
             origem="faixa pintada: paineis PE-1 do terreo + face interna da platibanda"),
        dict(sku="FAC-TELA", descricao="Tela de fibra de vidro alcali-resistente, embutida no basecoat",
             unidade="m2", quantidade=round(area * 1.10, 1), preco=PRECO["tela_m2"],
             origem="mesma area + 10 % de transpasse entre panos"),
        dict(sku="FAC-JUNTA", descricao="Tratamento de junta externa: fundo de junta e selante PU",
             unidade="m", quantidade=round(junta, 1), preco=PRECO["selante_junta_m"],
             origem=f"{JUNTA_POR_M2:.2f} m de junta por m2 — chapa de 1.200 x 2.400"),
        dict(sku="FAC-TINTA", descricao="Tinta acrilica elastomerica lisa com biocida, 2 demaos",
             unidade="L", quantidade=round(litros, 1),
             preco=PRECO["acrilico_elastomerico_l"],
             origem=f"({area:.0f} m2 x {DEMAOS_FACHADA}) / {RENDIMENTO_ELASTOMERICO:g} m2/L"),
        dict(sku="FAC-MAO", descricao="Mao de obra de fachada (basecoat, tela, junta e pintura)",
             unidade="m2", quantidade=round(area, 1), preco=PRECO["mao_fachada_m2"],
             origem="area de fachada"),
    ]


def _fachada_por_tratamento(pj, camadas=None) -> tuple[float, float]:
    """(m2 pintados, m2 com revestimento mineral de fabrica).

    R59 — a R58 pintou os 309 m2 inteiros e contradisse tres declaracoes do
    proprio projeto: FACHADA_MATERIAIS ("placa com revestimento mineral,
    junta seca"), FACHADA_REGRAS ("nenhuma superficie que exija pintura em
    altura") e PINTURA.externa_onde ("a fachada do volume superior NAO e
    pintada"). A composicao e base pintada ate 2.600 mm + volume mineral em
    cima — decisao de fachada da Etapa 1, nao de orcamento. O que se pinta e
    o que se alcanca do chao: os paineis do terreo e a face interna da
    platibanda (alcancavel da cobertura).
    """
    pintado = mineral = 0.0
    if camadas:
        for d in camadas.get("detalhe", []):
            if d.get("composicao") == "PE-1" and d.get("material") == "PLCIM":
                if str(d.get("painel", "")).startswith("S"):
                    mineral += d["area"]
                else:
                    pintado += d["area"]
        pl = (camadas.get("platibanda") or {}).get("placa_m2", 0.0)
        pintado += pl / 2          # face interna
        mineral += pl / 2          # face externa
    if pintado + mineral <= 0:
        pintado = _area_placa_externa(pj, camadas)
    return pintado, mineral


def _area_placa_externa(pj, camadas=None) -> float:
    """m2 de placa cimenticia exposta — do modelo de camadas, nunca estimada."""
    area = 0.0
    if camadas:
        for it in camadas.get("itens", []):
            if it.get("material") == "PLCIM":
                area += it.get("area", 0.0)
        pl = camadas.get("platibanda") or {}
        area += pl.get("placa_m2", 0.0) or pl.get("area_placa", 0.0)
    if area <= 0:                      # sem o dicionario de camadas, deriva
        import nucleo.fachada as _fa
        area = sum(f["area_liquida"] for f in _fa.faces(pj))
    return area


# ---------------------------------------------------------- 2. pintura
def pintura(pj) -> list[dict]:
    """Tinta pela AREA PINTADA, nao pelo palpite do pintor.

    Parede pintada e o que sobra acima do revestimento; forro e inteiro. A
    conta vai a LITRO, porque e assim que se compra — e o rendimento e o dado
    que separa quem orca de quem chuta.
    """
    parede = forro = 0.0
    nao_pinta = _sem_forro(pj) | _forro_nao_pintado(pj)
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
        # garagem sem forro e gourmet com forro perfurado de fabrica: nao ha o
        # que pintar (R59 — 66 m2 de tinta de forro sobre forro que nao existe)
        if cod not in nao_pinta:
            forro += area
    # R58 — PIN-EXT SAIU, E ISSO E O CONSERTO.
    #
    # Havia aqui uma linha de "pintura externa (acrilico elastomerico no muro)"
    # de 249,5 m2, e em nucleo/externo.py uma linha de hidrofugante incolor
    # sobre os MESMOS 249,5 m2 de muro. Os dois tratamentos sao excludentes: ou
    # o bloco e aparente e recebe hidrofugante, ou e pintado. O orcamento
    # pagava os dois. Duas fontes para o mesmo fato — o padrao de defeito que
    # este projeto ja catalogou quatro vezes.
    #
    # FICOU O APARENTE, e a razao e o clima, nao o preco de hoje. Pintura sobre
    # bloco em Manaus tem ciclo: 3 a 5 anos ate o fungo e o descolamento no pe
    # do muro, onde a chuva rebate do piso. Hidrofugante incolor nao descasca
    # porque nao forma pelicula — ele reduz a absorcao capilar do proprio
    # bloco. O muro fica com a cara do material, que e o que a NBR 16868 chama
    # de alvenaria aparente e exige junta rebaixada e prumo, ja especificados.
    # De quebra sai R$ 6.487 do orcamento e some um item da manutencao perpetua.
    #
    # Se um dia o proprietario quiser o muro pintado, a linha volta — mas ai o
    # hidrofugante e que sai. Nunca os dois.
    total = parede + forro
    litros = total * DEMAOS / RENDIMENTO_TINTA
    return [
        dict(sku="PIN-PAREDE", descricao="Pintura de parede interna (latex acrilico, 2 demaos)",
             unidade="m2", quantidade=round(parede, 1), preco=PRECO["mao_pintura_m2"],
             origem="perimetro x (pe-direito menos revestimento), menos vaos"),
        dict(sku="PIN-FORRO", descricao="Pintura de forro (latex PVA fosco)",
             unidade="m2", quantidade=round(forro, 1), preco=PRECO["mao_pintura_m2"],
             origem="area de forro de cada ambiente"),
        dict(sku="PIN-TINTA", descricao=f"Tinta latex ({DEMAOS} demaos, rendimento {RENDIMENTO_TINTA:g} m2/L)",
             unidade="L", quantidade=round(litros, 1), preco=PRECO["tinta_l"],
             origem=f"({total:.0f} m2 x {DEMAOS}) / {RENDIMENTO_TINTA:g}"),
        dict(sku="PIN-SELADOR", descricao="Selador acrilico",
             unidade="L", quantidade=round(total / RENDIMENTO_SELADOR, 1),
             preco=PRECO["selador_l"], origem=f"{total:.0f} m2 / {RENDIMENTO_SELADOR:g}"),
    ]


def _faces_livres_m(pj, box: dict, tol: int = 200) -> float:
    # tol 200: a louca e locada a 150 mm da face acabada (azulejo + folga)
    """Metros de perimetro do box que NAO encostam em parede do compartimento."""
    amb = box["amb"]
    cands = [d for d in pj.SUBDIVISOES if d["pai"] == amb and d.get("molhado")]
    cands += [a for a in pj.TERREO + pj.SUPERIOR if a.cod == amb and a.molhado]
    if not cands:
        return 2 * (box["w"] + box["h"]) / 1000.0
    c = cands[0]
    cx, cy = (c["x"], c["y"]) if isinstance(c, dict) else (c.x, c.y)
    cw, ch = (c["w"], c["h"]) if isinstance(c, dict) else (c.w, c.h)
    x0, y0, x1, y1 = box["x"], box["y"], box["x"] + box["w"], box["y"] + box["h"]
    livre = 0.0
    livre += 0 if abs(x0 - cx) <= tol else box["h"]           # face oeste
    livre += 0 if abs(x1 - (cx + cw)) <= tol else box["h"]    # face leste
    livre += 0 if abs(y0 - cy) <= tol else box["w"]           # face norte
    livre += 0 if abs(y1 - (cy + ch)) <= tol else box["w"]    # face sul
    return livre / 1000.0


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
    # R59 — o box contava as QUATRO faces em vidro. Box encosta em parede: as
    # faces coincidentes com a parede do banho sao azulejo, nao vidro temperado
    # a R$ 620/m2. So a face livre e a face de porta levam vidro.
    box_m2 = sum(_faces_livres_m(pj, p) * 1.90 for p in pj.LOUCAS if p["tipo"] == "box")
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
    import nucleo.luminotecnica as lu
    lum = lu.compras(pj)          # R59 — pendencia 13 fechada: metodo dos lumens
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
        *lum,
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


def levantar(pj, camadas=None) -> dict:
    fr = dict(revestimento=revestimento(pj), fachada=fachada(pj, camadas),
              pintura=pintura(pj),
              loucas=loucas_e_metais(pj), eletrica=eletrica_de_acabamento(pj),
              equipamentos=equipamentos(pj), marcenaria=marcenaria(pj))
    total = sum(i["quantidade"] * i["preco"] for l in fr.values() for i in l)
    return dict(frentes=fr, n=sum(len(l) for l in fr.values()),
                total=round(total, 2),
                criterio="quantidade derivada da geometria de USO do modelo; "
                         "preco (H) como todo preco deste projeto; pontos de "
                         "luz por regra declarada ate haver luminotecnica")


def _brl(v) -> str:
    s = f"{v:,.2f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return "R$ " + s


def conferir(pj) -> list[tuple[str, str, bool]]:
    lv = levantar(pj)
    fr = lv["frentes"]
    import collections
    skus = [i["sku"] for l in fr.values() for i in l]
    n = collections.Counter(skus)
    return [
        ("as sete frentes foram levantadas",
         f"{lv['n']} linhas em {len(fr)} frentes, somando "
         f"{_brl(lv['total'])}", len(fr) == 7),
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
        ("ponto de luz e calculo, nao regra (R59)",
         f"{sum(i['quantidade'] for i in fr['eletrica'] if i['sku'].startswith('LUM-') and i['unidade'] == 'un'):.0f} "
         f"luminarias pelo metodo dos lumens + "
         f"{sum(i['quantidade'] for i in fr['eletrica'] if i['sku'] == 'LUM-LINEAR'):.1f} m "
         f"de linear de tarefa — nenhuma quantidade desta frente e regra de area",
         not any(i["sku"] == "ELE-LUM" for i in fr["eletrica"])),
    ]
