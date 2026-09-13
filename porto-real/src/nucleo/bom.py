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

    @property
    def total(self) -> float:
        return self.quantidade * self.preco_unit


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
}
PRECO_ESQ = {            # (H)
    "caixilho_m": 185.00, "vidro_m2": 310.00,
    "roldana": 18.00, "fecho": 42.00, "trilho_m": 96.00,
    "dobradica": 26.00, "fechadura": 145.00, "batente": 210.00,
}
PRECO_COB = {            # (H)
    "calha_m": 118.00, "rufo_m": 62.00, "cumeeira_m": 74.00,
    "parafuso_un": 1.80, "impermeab_m2": 78.00,
}
PRECO_CAMADA = {
    "PLCIM": 62.00, "GESSO": 28.00, "GESSORU": 36.00, "LAROCHA": 34.00,
    "LAVIDRO": 22.00, "XPS": 41.00, "OSB": 58.00, "ACO": 0.0,
    "PIR": 132.00, "PUR": 126.00, "EPS": 18.00, "ACM": 210.00,
}
NOME_CAMADA = {
    "PLCIM": "Placa cimenticia", "GESSO": "Chapa de gesso",
    "GESSORU": "Chapa de gesso RU", "LAROCHA": "La de rocha",
    "LAVIDRO": "La de vidro", "XPS": "XPS (ISO strip)", "OSB": "OSB estrutural",
    "ACO": "Perfil de aco (ja contado em massa)",
}


def montar(pecas: list, plano_corte: dict, area_m2: float,
           n_parafusos: int = None, area_placa_m2: float = None,
           precos: dict = None, camadas: dict = None) -> list[ItemBOM]:
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
    for perfil, (n, m) in sorted(por_perfil.items(), key=lambda kv: -kv[1][1]):
        itens.append(ItemBOM(f"PF-{perfil[:20]}", f"{perfil}", "pc", n,
                             p["aco_perfil_kg"] * m / n, "estrutura",
                             "derivado"))

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
        itens.append(ItemBOM("PLACA", "Placa (gesso, RU e cimenticia)", "pc",
                             pg["placas"], 0.0, "vedacao", fonte="derivado"))
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
                ("FUN-FORMA", "Forma de borda", fun["forma_m2"],
                 PRECO_FUND["forma_m2"], "m2")):
            itens.append(ItemBOM(sku, desc, un, q, pr, "fundacao",
                                 fonte="derivado de espessura (H)"))

    # ---- esquadria: 12 a 18 % do custo de uma residencia, e estava em zero
    esq = (camadas or {}).get("esquadrias")
    if esq:
        itens.append(ItemBOM("ESQ-CAIX", "Caixilho de aluminio", "m",
                             esq["caixilho_m"], PRECO_ESQ["caixilho_m"],
                             "esquadria", fonte="derivado"))
        itens.append(ItemBOM("ESQ-VIDRO", "Vidro (ver especificacao por vao)",
                             "m2", esq["area_vidro"], PRECO_ESQ["vidro_m2"],
                             "esquadria", fonte="derivado"))
        for item, q in sorted(esq["ferragem"].items()):
            itens.append(ItemBOM(f"FER-{item[:6].upper()}",
                                 f"Ferragem: {item.replace('_m','')}",
                                 "m" if item.endswith("_m") else "un",
                                 round(q, 1), PRECO_ESQ.get(item, 0.0),
                                 "esquadria", fonte="derivado"))
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
