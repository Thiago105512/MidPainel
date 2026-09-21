"""BOM E CUSTO — da peca ao metro quadrado (secoes 59, 60, 87, 91 a 95).

Todo preco aqui e (H). Nenhum deles foi consultado: sao ordens de grandeza para
que a ESTRUTURA do calculo exista e possa ser auditada. Quando o catalogo do
fornecedor chegar, troca-se a tabela e tudo o mais continua valendo — que e
exatamente o motivo de o custo ser derivado e nao digitado.

O que NAO e hipotese: as quantidades. Elas saem das 801 pecas, do plano de corte
e da painelizacao, e fecham com a massa do modelo.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

# (H) precos de referencia, BRL. Estrutura real, valores a confirmar.
PRECOS = {
    "aco_perfil_kg": 11.50,
    "aco_bobina_kg": 8.90,
    "osb_11mm_m2": 78.00,
    "osb_15mm_m2": 105.00,
    "placa_cimenticia_8mm_m2": 62.00,
    "gesso_12.5mm_m2": 24.00,
    "gesso_ru_12.5mm_m2": 34.00,
    "la_rocha_50mm_m2": 32.00,
    "membrana_hidrofuga_m2": 14.00,
    "parafuso_estrutural_un": 0.28,
    "parafuso_placa_un": 0.12,
    "chumbador_un": 18.00,
    "holddown_un": 145.00,
    "fita_contraventamento_m": 9.50,
    "mao_obra_montagem_h": 42.00,
    "mao_obra_fabrica_h": 38.00,
}
IMPOSTOS = dict(ipi=0.05, icms=0.18, pis_cofins=0.0925)
# (H) produtividade, para o custo de mao de obra existir
PRODUTIVIDADE = dict(pecas_por_hora_fabrica=22.0, m2_painel_por_hora_montagem=3.5)


@dataclass
class ItemBOM:
    sku: str
    descricao: str
    unidade: str
    quantidade: float
    preco_unit: float
    familia: str = ""
    fonte: str = "(H)"
    # O QUE SE COMPRA E O QUE SE PRODUZ nao sao a mesma linha, e some-los e
    # pagar duas vezes pela mesma materia. Em LSF compra-se BARRA (kg, com a
    # perda do plano de corte) e produz-se PECA cortada. As duas coisas
    # estavam no BOM, as duas com preco, e as duas entravam no total: R$ 71.654
    # de aco bruto mais R$ 62.664 das mesmas pecas em outra unidade.
    #
    # A dupla contagem em UNIDADES DIFERENTES e a que passa despercebida — o
    # proprio arquivo ja avisava disso tres linhas abaixo, ao recusar listar a
    # camada de aco em m2, enquanto a listava em pc. Ver docs/DIVERGENCIAS.md.
    compra: bool = True

    @property
    def total(self) -> float:
        return self.quantidade * self.preco_unit

    @property
    def total_compra(self) -> float:
        """O que entra no custo. Linha de producao informa, nao custa."""
        return self.total if self.compra else 0.0


def total(itens: list) -> float:
    """Custo do projeto: so o que se COMPRA.

    Existe como funcao, e nao como `sum(i.total ...)` espalhado, porque a
    regra de o que entra no total e uma decisao do BOM — e quando ela estava
    espalhada, cada consumidor tinha a sua, e um deles somava aco duas vezes.
    """
    return sum(i.total_compra for i in itens)


# Preco por m2 de cada material de camada. (H), como todos os precos: ordem de
# grandeza para a estrutura do calculo existir.
# Acessorio de junta: e 8 a 12 % do custo do fechamento em drywall e nao
# existia no modelo. Deriva do PERIMETRO, que a paginacao passou a conhecer.
PRECO_JUNTA = {          # (H), como todo preco deste arquivo
    "fita": 0.40,          # rolo de 150 m
    "massa": 2.50,         # balde de 30 kg rende 60 a 80 m de junta
    "cantoneira": 4.50,
    "parafuso_placa": 0.12,
}
PRECO_MEP = {            # (H)
    "tubo_agua_m": 18.00, "tubo_esgoto_m": 26.00, "conexao": 12.00,
    "eletroduto_m": 6.50, "cabo_m": 4.20, "caixa": 9.00, "disjuntor": 38.00,
    "linha_frigo_m": 62.00, "dreno_m": 9.00, "isolamento_m": 14.00,
}
PRECO_FUND = {           # (H)
    "concreto_m3": 520.00, "aco_kg": 9.80, "tela_m2": 28.00,
    "lastro_m3": 145.00, "lona_m2": 4.50, "forma_m2": 68.00,
    # terraplenagem de R52: a troca controlada dos 600 mm de aterro que o SPT
    # reprovou por uniformidade. Escavacao e bota-fora sao servico, nao
    # material, e por isso o preco e de hora de maquina rateada por m3.
    "escavacao_m3": 38.00, "bota_fora_m3": 46.00,
    "substituicao_m3": 128.00, "compactacao_m3": 22.00, "ensaio_un": 380.00,
}
PRECO_ESQ = {            # (H)
    "caixilho_m": 185.00, "vidro_m2": 310.00, "vidro_lowe_acrescimo_m2": 390.00,
    "roldana": 18.00, "fecho": 42.00, "trilho_m": 96.00,
    "dobradica": 26.00, "fechadura": 145.00, "batente": 210.00,
}
PRECO_BRISE = {          # (H)
    "ripa_m": 42.00, "travessa_m": 38.00, "fixacao": 6.50, "mecanismo": 2_400.00,
}
PRECO_FASCIA_M = 220.00  # (H) aluminio grafite dobrado 450 mm, rufo integrado, instalado
PRECO_COB = {            # (H)
    "calha_m": 118.00, "rufo_m": 62.00, "cumeeira_m": 74.00,
    "parafuso_un": 1.80, "impermeab_m2": 78.00,
}
PRECO_CAMADA = {
    "PLCIM": 62.00, "GESSO": 28.00, "GESSORU": 36.00, "LAROCHA": 34.00,
    "LAVIDRO": 22.00, "XPS": 41.00, "OSB": 58.00, "ACO": 0.0,
    "PIR": 132.00, "PUR": 126.00, "EPS": 18.00, "ACM": 210.00,
}
# (H) SPDA e fotovoltaica, como todo preco deste projeto
PRECO_SPDA = {"captor_m": 38.0, "descida_conexao_un": 260.0, "anel_m": 46.0,
              "haste_un": 95.0, "bep_un": 420.0, "dps_classe1_un": 890.0,
              "ensaio_un": 650.0}
PRECO_FV = {"modulo_un": 780.0, "inversor_kw": 620.0, "estrutura_m2": 95.0,
            "stringbox_un": 680.0, "cabo_m": 14.0, "instalacao_kwp": 550.0,
            "homologacao_un": 1_800.0}
# (H) perfilaria de forro, como todo preco deste projeto
PRECO_FORRO = {"perfil_m": 6.80, "tirante_un": 3.20, "tabica_m": 14.00}
NOME_CAMADA = {
    "PLCIM": "Placa cimenticia", "GESSO": "Chapa de gesso",
    "GESSORU": "Chapa de gesso RU", "LAROCHA": "La de rocha",
    "LAVIDRO": "La de vidro", "XPS": "XPS (ISO strip)", "OSB": "OSB estrutural",
    "ACO": "Perfil de aco (ja contado em massa)",
}


def montar(pecas: list, plano_corte: dict, area_m2: float,
           n_parafusos: int = None, area_placa_m2: float = None,
           precos: dict = None, camadas: dict = None,
           acabamento: dict = None) -> list[ItemBOM]:
    """BOM completo a partir das pecas e do plano de corte."""
    p = dict(PRECOS)
    p.update(precos or {})
    itens = []

    massa = sum(x.massa for x in pecas)
    # o aco comprado e o BRUTO das barras, nao o util: a perda foi paga
    massa_bruta = massa / plano_corte["aproveitamento"] if plano_corte["aproveitamento"] else massa
    itens.append(ItemBOM("ACO-PERF", "Perfil formado a frio, barras de 6 m",
                         "kg", round(massa_bruta, 1), p["aco_perfil_kg"], "estrutura"))

    por_perfil = {}
    for x in pecas:
        por_perfil.setdefault(x.perfil, [0, 0.0])
        por_perfil[x.perfil][0] += 1
        por_perfil[x.perfil][1] += x.massa
    # Quantidade por perfil: e o que a FABRICA precisa saber e o que o mapa de
    # cotacao oferece como rota alternativa (comprar peca cortada em vez de
    # barra). Nao entra no custo: o aco ja foi comprado em kg, logo acima, e em
    # regime de barra inteira, que e como o fornecedor de LSF vende.
    for perfil, (n, m) in sorted(por_perfil.items(), key=lambda kv: -kv[1][1]):
        itens.append(ItemBOM(f"PF-{perfil[:20]}", f"{perfil}", "pc", n,
                             p["aco_perfil_kg"] * m / n, "estrutura",
                             "producao: o aco ja esta em ACO-PERF, em kg",
                             compra=False))

    if n_parafusos is None:
        n_parafusos = int(len(pecas) * 8)
    itens.append(ItemBOM("PAR-EST", "Parafuso estrutural auto-brocante", "un",
                         n_parafusos, p["parafuso_estrutural_un"], "ligacao"))
    # ---- fechamento: da GEOMETRIA, nao de coeficiente.
    # Ate R33 esta secao inteira saia de `area_m2 * 2.4` vezes mais cinco
    # coeficientes (0,45 / 0,55 / 1,00 / 0,90 / 0,50). Seis numeros arbitrados
    # onde o modelo ja sabia o comprimento, a altura e as aberturas de cada um
    # dos 62 paineis. O coeficiente acertava por acaso — 710,2 m2 contra 718,6
    # de area real —, e acerto por cancelamento de dois erros grandes nao e
    # acerto: e a mesma coisa que o `len(pecas) * 8` dos parafusos.
    if camadas:
        for it in camadas["itens"]:
            mat, esp = it["material"], it["espessura"]
            # a camada estrutural JA esta no BOM, em kg, vinda do plano de
            # corte. Lista-la tambem em m2 seria contar o mesmo aco duas vezes
            # — e em duas unidades diferentes, que e como a dupla contagem
            # costuma passar despercebida
            if mat == "ACO":
                continue
            sku = f"{mat}-{esp:g}".replace(".", ",")
            preco = PRECO_CAMADA.get(mat, 0.0)
            itens.append(ItemBOM(
                sku, f"{NOME_CAMADA.get(mat, mat)} {esp:g} mm", "m2",
                it["area"], preco, "vedacao",
                fonte="derivado" if preco else "(H) sem preco"))
    elif area_placa_m2 is not None:
        # caminho de compatibilidade: so para quem ainda chama sem camadas
        for sku, desc, k, preco in (
                ("OSB11", "OSB 11,1 mm estrutural", 0.45, p["osb_11mm_m2"]),
                ("GESSO", "Chapa de gesso 12,5 mm", 1.00, p["gesso_12.5mm_m2"])):
            itens.append(ItemBOM(sku, desc, "m2", round(area_placa_m2 * k, 1),
                                 preco, "vedacao", fonte="(H) estimado"))

    h_fab = len(pecas) / PRODUTIVIDADE["pecas_por_hora_fabrica"]
    # acessorio de junta, quando a paginacao existir
    pg = (camadas or {}).get("paginacao")
    if pg:
        # placa INTEIRA: e a rota alternativa de compra — comprar por placa em
        # vez de por m2 — e nao um item a mais. O custo ja esta nas linhas de
        # m2 acima, e some-lo aqui seria a mesma dupla contagem do aco.
        itens.append(ItemBOM("PLACA", "Placa (gesso, RU e cimenticia)", "pc",
                             pg["placas"], 0.0, "vedacao",
                             fonte="rota alternativa: o custo esta em m2",
                             compra=False))
        itens.append(ItemBOM("FITA", "Fita de papel para junta", "m",
                             pg["junta_m"], PRECO_JUNTA["fita"], "vedacao",
                             fonte="derivado"))
        itens.append(ItemBOM("MASSA", "Massa para junta, 3 demaos", "m",
                             pg["junta_m"], PRECO_JUNTA["massa"], "vedacao",
                             fonte="derivado"))
        itens.append(ItemBOM("CANT", "Cantoneira de canto e arremate", "m",
                             pg["borda_m"], PRECO_JUNTA["cantoneira"],
                             "vedacao", fonte="derivado"))
        # parafuso de placa: espacamento de 250 mm no campo e 200 na borda
        n_pl = int(pg["area_util"] * 1e6 / (250 * 600))
        itens.append(ItemBOM("PAR-PLA", "Parafuso de placa 25 mm", "un",
                             n_pl, PRECO_JUNTA["parafuso_placa"], "vedacao",
                             fonte="derivado"))

    # ---- instalacoes: as pranchas 26 a 29 desenhavam tudo e o BOM tinha zero
    mep = (camadas or {}).get("instalacoes")
    if mep:
        h = mep["hidraulica"]
        for i in h["itens"]:
            agua = "agua" in i["sistema"]
            itens.append(ItemBOM(
                f"MEP-{i['sistema'][:4].upper()}{i['dn']}",
                f"Tubo {i['sistema']} DN{i['dn']}", "m", i["comp_m"],
                PRECO_MEP["tubo_agua_m" if agua else "tubo_esgoto_m"],
                "instalacao", fonte="derivado (percurso Manhattan x fator)"))
        itens.append(ItemBOM("MEP-CONEX", "Conexoes hidraulicas", "un",
                             h["conexoes"], PRECO_MEP["conexao"], "instalacao",
                             fonte="derivado"))
        e = mep["eletrica"]
        for sku, desc, q, pr, un in (
                ("MEP-ELET", "Eletroduto flexivel", e["eletroduto_m"],
                 PRECO_MEP["eletroduto_m"], "m"),
                ("MEP-CABO", "Cabo de cobre (fase, neutro e terra)",
                 e["cabo_m"], PRECO_MEP["cabo_m"], "m"),
                ("MEP-CAIXA", "Caixa de passagem e de tomada", e["caixas"],
                 PRECO_MEP["caixa"], "un"),
                ("MEP-DISJ", "Disjuntor", e["disjuntores"],
                 PRECO_MEP["disjuntor"], "un")):
            itens.append(ItemBOM(sku, desc, un, q, pr, "instalacao",
                                 fonte="derivado"))
        c = mep["climatizacao"]
        for sku, desc, q, pr in (
                ("MEP-FRIGO", "Linha frigorigena", c["linha_m"],
                 PRECO_MEP["linha_frigo_m"]),
                ("MEP-DRENO", "Dreno de condensado", c["dreno_m"],
                 PRECO_MEP["dreno_m"]),
                ("MEP-ISOL", "Isolamento de linha", c["isolamento_m"],
                 PRECO_MEP["isolamento_m"])):
            itens.append(ItemBOM(sku, desc, "m", q, pr, "instalacao",
                                 fonte="derivado"))

    # ---- fundacao: 8 a 15 % do custo, e era o ultimo sistema em zero
    fun = (camadas or {}).get("fundacao")
    if fun:
        for sku, desc, q, pr, un in (
                ("FUN-CONC", f"Concreto fck {fun['fck']} MPa",
                 fun["volume_m3"], PRECO_FUND["concreto_m3"], "m3"),
                ("FUN-ACO", f"Aco {fun['aco']} para radier",
                 fun["aco_kg"], PRECO_FUND["aco_kg"], "kg"),
                ("FUN-TELA", f"Tela soldada {fun['tela']}",
                 fun["tela_m2"], PRECO_FUND["tela_m2"], "m2"),
                ("FUN-LASTRO", "Lastro de brita graduada",
                 fun["lastro_m3"], PRECO_FUND["lastro_m3"], "m3"),
                ("FUN-LONA", "Lona plastica sob o radier",
                 fun["lona_m2"], PRECO_FUND["lona_m2"], "m2"),
                ("FUN-FORMA", "Forma de borda e engrossamento do perimetro",
                 fun["forma_m2"], PRECO_FUND["forma_m2"], "m2")):
            itens.append(ItemBOM(sku, desc, un, q, pr, "fundacao",
                                 fonte="derivado da secao conferida"))
        # terraplenagem: consequencia direta do SPT, e nao existia em zero
        t = fun["terraplenagem"]
        for sku, desc, q, pr, un in (
                ("FUN-ESCAV", "Escavacao do aterro superficial reprovado",
                 t["corte_m3"], PRECO_FUND["escavacao_m3"], "m3"),
                ("FUN-BOTA", "Bota-fora do material escavado (empolado 25 %)",
                 t["bota_fora_m3"], PRECO_FUND["bota_fora_m3"], "m3"),
                ("FUN-SUBST", "Substituicao: areia grossa com brita graduada",
                 t["substituicao_m3"], PRECO_FUND["substituicao_m3"], "m3"),
                ("FUN-COMP", "Compactacao controlada, camadas de 250 mm",
                 t["substituicao_m3"], PRECO_FUND["compactacao_m3"], "m3"),
                ("FUN-ENSAIO", "Ensaio de densidade in situ por camada",
                 t["ensaios"], PRECO_FUND["ensaio_un"], "un")):
            itens.append(ItemBOM(sku, desc, un, q, pr, "fundacao",
                                 fonte="derivado do SPT"))

    # ---- esquadria: 12 a 18 % do custo de uma residencia, e estava em zero
    esq = (camadas or {}).get("esquadrias")
    if esq:
        itens.append(ItemBOM("ESQ-CAIX", "Caixilho de aluminio", "m",
                             esq["caixilho_m"], PRECO_ESQ["caixilho_m"],
                             "esquadria", fonte="derivado"))
        itens.append(ItemBOM("ESQ-VIDRO", "Vidro (ver especificacao por vao)",
                             "m2", esq["area_vidro"], PRECO_ESQ["vidro_m2"],
                             "esquadria", fonte="derivado"))
        if esq.get("area_lowe"):
            # R61 — o acrescimo do low-e sobre o vidro base, so na area que o
            # recebe; somar vidro e low-e inteiros seria pagar o vidro duas vezes
            itens.append(ItemBOM("ESQ-VIDRO-LOWE", "Acrescimo: laminado low-e (g <= 0,35) "
                                 "sobre o vidro base", "m2", esq["area_lowe"],
                                 PRECO_ESQ["vidro_lowe_acrescimo_m2"], "esquadria",
                                 fonte="vaos com low-e no quadro de vidros"))
        for item, q in sorted(esq["ferragem"].items()):
            itens.append(ItemBOM(f"FER-{item[:6].upper()}",
                                 f"Ferragem: {item.replace('_m','')}",
                                 "m" if item.endswith("_m") else "un",
                                 round(q, 1), PRECO_ESQ.get(item, 0.0),
                                 "esquadria", fonte="derivado"))
    # ---- forro suspenso: chapa e la ja entraram pelas camadas; o que faltava
    # e o que segura a chapa — perfil, tirante e tabica (R59)
    fo = ((camadas or {}).get("planos") or {}).get("forro")
    if fo and fo.get("area"):
        for sku, desc, q, pr, un in (
                ("FOR-PERFIL", "Forro: canaleta e travessa F530 galvanizada",
                 fo["perfil_m"], PRECO_FORRO["perfil_m"], "m"),
                ("FOR-TIRANTE", "Forro: pendural regulavel com tirante",
                 fo["tirante_un"], PRECO_FORRO["tirante_un"], "un"),
                ("FOR-TABICA", "Forro: tabica perimetral de sombra",
                 fo["tabica_m"], PRECO_FORRO["tabica_m"], "m")):
            itens.append(ItemBOM(sku, desc, un, round(q, 1), pr, "vedacao",
                                 fonte=f"{fo['area']:.1f} m2 de forro suspenso "
                                       f"em {len(fo['regioes'])} regioes sob "
                                       f"cobertura, malha 600 x 1.200"))
    # ---- SPDA (R61): captor no perimetro da cobertura, descida pela
    # estrutura, anel de aterramento no radier
    sp = (camadas or {}).get("spda")
    if sp:
        for sku, desc, q, pr, un in (
                ("SPD-CAPTOR", "Captor: cabo de aluminio 70 mm2 no perimetro da cobertura",
                 sp["captor_m"], PRECO_SPDA["captor_m"], "m"),
                ("SPD-DESCIDA", "Descida natural pela estrutura LSF: conector de teste e ligacao",
                 sp["descidas"], PRECO_SPDA["descida_conexao_un"], "un"),
                ("SPD-ANEL", "Anel de aterramento: cobre nu 50 mm2 no perimetro do radier",
                 sp["anel_m"], PRECO_SPDA["anel_m"], "m"),
                ("SPD-HASTE", "Haste de aterramento 5/8 x 2.400 mm", sp["hastes"],
                 PRECO_SPDA["haste_un"], "un"),
                ("SPD-BEP", "Barramento de equipotencializacao principal", 1,
                 PRECO_SPDA["bep_un"], "un"),
                ("SPD-DPS1", "DPS classe I, 12,5 kA, 3F+N, na entrada", 1,
                 PRECO_SPDA["dps_classe1_un"], "un"),
                ("SPD-ENSAIO", "Ensaio de continuidade e resistencia de aterramento", 1,
                 PRECO_SPDA["ensaio_un"], "un")):
            itens.append(ItemBOM(sku, desc, un, round(q, 1), pr, "eletrica",
                                 fonte=f"NBR 5419-3 classe {sp['classe']}: "
                                       f"{sp['descidas']} descidas a <= {sp['espac_descida_m']:.0f} m"))
    # ---- fotovoltaica (R61)
    fv = (camadas or {}).get("fotovoltaica")
    if fv:
        for sku, desc, q, pr, un in (
                ("FV-MODULO", f"Modulo fotovoltaico {fv['modulo_wp']} Wp", fv["n_modulos"],
                 PRECO_FV["modulo_un"], "un"),
                ("FV-INVERSOR", f"Inversor string {fv['inversor_kw']:.0f} kW, trifasico 220 V",
                 fv["inversor_kw"], PRECO_FV["inversor_kw"], "kW"),
                ("FV-ESTRUTURA", "Estrutura de fixacao em aluminio sobre terca",
                 fv["area_modulos_m2"], PRECO_FV["estrutura_m2"], "m2"),
                ("FV-STRINGBOX", "String box CC com DPS e seccionadora", 1,
                 PRECO_FV["stringbox_un"], "un"),
                ("FV-CABO", "Cabo solar 6 mm2 e eletroduto ate o inversor", fv["cabo_m"],
                 PRECO_FV["cabo_m"], "m"),
                ("FV-INSTAL", "Instalacao e comissionamento", fv["kwp_instalado"],
                 PRECO_FV["instalacao_kwp"], "kWp"),
                ("FV-HOMOLOG", "Projeto e homologacao na concessionaria (REN 1.000)", 1,
                 PRECO_FV["homologacao_un"], "un")):
            itens.append(ItemBOM(sku, desc, un, round(q, 2), pr, "eletrica",
                                 fonte=f"{fv['consumo_kwh_dia']:.1f} kWh/dia, HSP {fv['hsp']} (H), "
                                       f"PR {fv['pr']}"))
    # ---- cobertura: o que fecha uma cobertura e o perimetro, nao a area
    cob = (camadas or {}).get("cobertura")
    if cob:
        for sku, desc, q, pr, un in (
                ("COB-CALHA", "Calha externa " + cob["calha_secao"],
                 cob["calha_m"], PRECO_COB["calha_m"], "m"),
                ("COB-RUFO", "Rufo e contrarrufo", cob["rufo_m"],
                 PRECO_COB["rufo_m"], "m"),
                ("COB-CUME", "Cumeeira", cob["cumeeira_m"],
                 PRECO_COB["cumeeira_m"], "m"),
                ("COB-PAR", "Parafuso de fixacao do painel",
                 cob["parafuso_un"], PRECO_COB["parafuso_un"], "un")):
            itens.append(ItemBOM(sku, desc, un, q, pr, "cobertura",
                                 fonte="derivado"))
    # ---- platibanda: 550 mm de parede em todo o perimetro, 243 kg de aco e
    # 71 m2 de placa que nao existiam. O aco dela NAO esta no plano de corte
    # nem em ACO-PERF — entra como linha propria, e a auditoria confere que a
    # dupla contagem nao voltou pela porta dos fundos.
    pb = (camadas or {}).get("platibanda")
    if pb and pb.get("altura"):
        itens.append(ItemBOM("PLA-MONT", f"Platibanda: montante "
                                         f"{pb['perfis']['montante']}", "m",
                             pb["montante_m"], p["aco_perfil_kg"]
                             * pb["perfis"]["massa_montante_m"], "cobertura",
                             fonte=f"{pb['n_montantes']} montantes a cada "
                                   f"{pb['espac']} mm"))
        itens.append(ItemBOM("PLA-GUIA", f"Platibanda: guia "
                                         f"{pb['perfis']['guia']}", "m",
                             pb["guia_m"], p["aco_perfil_kg"]
                             * pb["perfis"]["massa_guia_m"], "cobertura",
                             fonte="guia superior e inferior"))
        itens.append(ItemBOM("PLA-PLACA", "Platibanda: fechamento em placa "
                                          "cimenticia, duas faces", "m2",
                             pb["placa_m2"], PRECO_CAMADA["PLCIM"], "cobertura",
                             fonte="duas faces: a interna olha para a calha"))

    # ---- brise: 205 m de ripa de aluminio que existiam no desenho e no 3D e
    # nao existiam no orcamento nem na carga
    br = (camadas or {}).get("brises")
    if br:
        itens.append(ItemBOM("BRI-RIPA", f"Ripa de fachada: {br['ripa']['desc']}",
                             "m", br["ripa_m"], PRECO_BRISE["ripa_m"],
                             "fachada", fonte="derivado do comprimento e do passo"))
        itens.append(ItemBOM("BRI-TRAV", f"Travessa de brise: {br['travessa']['perfil']}",
                             "m", br["travessa_m"], PRECO_BRISE["travessa_m"],
                             "fachada", fonte="derivado"))
        itens.append(ItemBOM("BRI-FIX", "Fixacao de travessa no montante", "un",
                             br["fixacoes"], PRECO_BRISE["fixacao"], "fachada",
                             fonte="derivado do passo de 600 mm"))
        if br["moveis"]:
            itens.append(ItemBOM("BRI-MEC", "Mecanismo de brise movel: guia, "
                                            "roldana e trava", "cj",
                                 br["moveis"], PRECO_BRISE["mecanismo"],
                                 "fachada", fonte="(H) item de fornecedor"))

    # ---- fascia (R67): a linha escura no topo da platibanda, rufo integrado
    fc = (camadas or {}).get("fascia")
    if fc:
        itens.append(ItemBOM("FAC-FASCIA", f"Fascia de platibanda {fc['altura']} mm, {fc['material']}",
                             "m", fc["perimetro_m"], PRECO_FASCIA_M, "fachada",
                             fonte="perimetro das platibandas (fachada.volumes_platibanda)"))

    # ---- AREA EXTERNA: 286 m2 de projeto que nao existiam no orcamento.
    # Muro, piso, piscina e paisagismo estavam desenhados, decididos e
    # justificados — e em nenhuma linha de custo. Em residencia deste porte a
    # area externa e 10 a 20 % do total, e e onde o orcamento estoura,
    # justamente porque entra por ultimo e sem levantamento.
    ext = (camadas or {}).get("externo")
    if ext:
        import nucleo.externo as _ex
        P = _ex.PRECO
        m = ext["muro"]
        itens.append(ItemBOM("EXT-BLOCO", f"Muro: {m['material'][:44]}", "un",
                             m["blocos"], P["bloco_un"], "externo",
                             fonte=f"derivado de {m['comprimento_m']} m x "
                                   f"{m['altura'] / 1000:g} m"))
        itens.append(ItemBOM("EXT-GRAUTE", "Graute de cinta e pilarete do muro",
                             "m3", m["graute_m3"], P["graute_m3"], "externo",
                             fonte="derivado"))
        itens.append(ItemBOM("EXT-HIDROF", "Hidrofugante incolor no muro "
                                           "aparente", "m2", m["area"],
                             P["hidrofugante_m2"], "externo",
                             fonte="derivado — substitui pintura e repintura"))
        preco_piso = {"porcelanato externo claro R11": P["piso_porcelanato_m2"],
                      "WPC coextrudado claro": P["piso_wpc_m2"],
                      "piso drenante intertravado claro": P["piso_drenante_m2"]}
        for i, z in enumerate(ext["pisos"]["itens"], 1):
            itens.append(ItemBOM(
                f"EXT-PISO{i}", f"{z['zona']}: {z['material'][:36]}", "m2",
                z["area"], preco_piso.get(z["material"], 120.0), "externo",
                fonte="derivado das areas abertas da zona"))
        itens.append(ItemBOM("EXT-GRAMA", "Grama e canteiro", "m2",
                             ext["pisos"]["jardim"], P["grama_m2"], "externo",
                             fonte="derivado dos jardins declarados"))
        pc = ext["piscina"]
        itens.append(ItemBOM("EXT-PISC-REV", "Piscina: revestimento de fundo e "
                                             "paredes", "m2",
                             pc["revestimento_m2"], P["piscina_revest_m2"],
                             "externo", fonte="fundo + 4 paredes na "
                                              "profundidade media"))
        itens.append(ItemBOM("EXT-PISC-EST", f"Piscina: casca de concreto "
                                             f"armado {pc['espessura_casca']} mm",
                             "m3", pc["concreto_m3"], P["piscina_estrutura_m3"],
                             "externo", fonte="derivado da area molhada"))
        itens.append(ItemBOM("EXT-BORDA", "Borda de piscina", "m",
                             pc["borda_m"], P["borda_m"], "externo",
                             fonte="perimetro da lamina"))
        # R78 — o sistema da piscina (nucleo/piscina.itens_bom), peca a peca
        for it in ext.get("piscina_sistema", []):
            itens.append(ItemBOM(it["cod"], it["desc"], it["un"], it["qtd"],
                                 it["preco"], "externo", fonte=it["fonte"]))
        pa = ext["paisagismo"]
        itens.append(ItemBOM("EXT-ARV", "Arvore de porte", "un", pa["arvores"],
                             P["arvore_un"], "externo", fonte="derivado"))
        itens.append(ItemBOM("EXT-VASO", "Vaso e planta em vaso", "un",
                             pa["vasos"], P["vaso_un"], "externo",
                             fonte="derivado"))

    # ---- impermeabilizacao
    imp = (camadas or {}).get("impermeabilizacao")
    if imp:
        itens.append(ItemBOM("IMP-MANTA", "Impermeabilizacao de area molhada",
                             "m2", imp["area"], PRECO_COB["impermeab_m2"],
                             "vedacao",
                             fonte="derivado" + (" (lacuna declarada)"
                                                 if imp["lacuna"] else "")))

    area_fechamento = (camadas["area_total"] if camadas
                       else (area_placa_m2 or area_m2 * 2.4))
    h_mont = area_fechamento / PRODUTIVIDADE["m2_painel_por_hora_montagem"]
    itens.append(ItemBOM("MO-FAB", "Mao de obra de fabrica", "h",
                         round(h_fab, 1), p["mao_obra_fabrica_h"], "servico"))
    itens.append(ItemBOM("MO-MON", "Mao de obra de montagem", "h",
                         round(h_mont, 1), p["mao_obra_montagem_h"], "servico"))

    # ---- R57: as seis frentes que ate R56 eram ESCOPO DECLARADO FORA.
    # Revestimento interno, pintura, loucas e metais, eletrica de acabamento,
    # equipamentos e marcenaria. Declarar a falta era honesto; continuar
    # declarando depois de o modelo saber quantificar seria preguica.
    for frente, linhas in ((acabamento or {}).get("frentes") or {}).items():
        for it in linhas:
            itens.append(ItemBOM(it["sku"], it["descricao"], it["unidade"],
                                 it["quantidade"], it["preco"], frente,
                                 fonte="derivado do uso: " + it["origem"]))
    return itens


def landed_cost(valor_fob: float, frete: float, seguro_pct: float = 0.005,
                ii_pct: float = 0.0, despachante: float = 0.0,
                armazenagem: float = 0.0, transporte_interno: float = 0.0,
                impostos: dict = None) -> dict:
    """Custo posto, parcela a parcela (secao 91)."""
    imp = dict(IMPOSTOS)
    imp.update(impostos or {})
    seguro = valor_fob * seguro_pct
    cif = valor_fob + frete + seguro
    ii = cif * ii_pct
    base = cif + ii
    ipi = base * imp["ipi"]
    icms = (base + ipi) * imp["icms"]
    pis = base * imp["pis_cofins"]
    total = base + ipi + icms + pis + despachante + armazenagem + transporte_interno
    return dict(fob=valor_fob, frete=frete, seguro=seguro, cif=cif, ii=ii,
                ipi=ipi, icms=icms, pis_cofins=pis, despachante=despachante,
                armazenagem=armazenagem, transporte_interno=transporte_interno,
                total=total, fator=total / valor_fob if valor_fob else 0.0)


def curva_abc(itens: list) -> list:
    """Classifica por impacto financeiro acumulado (secao 93)."""
    ordenado = sorted(itens, key=lambda i: -i.total)
    total = sum(i.total for i in ordenado) or 1.0
    out, acum = [], 0.0
    for i in ordenado:
        acum += i.total
        f = acum / total
        out.append(dict(sku=i.sku, descricao=i.descricao, total=i.total,
                        participacao=i.total / total, acumulado=f,
                        classe="A" if f <= 0.80 else ("B" if f <= 0.95 else "C")))
    return out


def cenario(itens: list, nome: str, fatores: dict) -> dict:
    """Aplica fatores por familia e devolve o total (secao 94)."""
    t = sum(i.total * fatores.get(i.familia, 1.0) for i in itens)
    return dict(cenario=nome, total=t, fatores=fatores)


def monte_carlo(base: float, variaveis: dict, n: int = 5000,
                semente: int = 20260913) -> dict:
    """Risco por simulacao (secao 95). variaveis: {nome: (min, moda, max)}."""
    rnd = random.Random(semente)
    amostras = []
    for _ in range(n):
        f = 1.0
        for _, (a, m, b) in variaveis.items():
            f *= rnd.triangular(a, b, m)
        amostras.append(base * f)
    amostras.sort()
    def q(p):
        return amostras[min(n - 1, int(p * n))]
    media = sum(amostras) / n
    return dict(media=media, p05=q(0.05), p50=q(0.50), p80=q(0.80),
                p95=q(0.95), minimo=amostras[0], maximo=amostras[-1],
                n=n, variaveis=list(variaveis))
