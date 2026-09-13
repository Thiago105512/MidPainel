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


def montar(pecas: list, plano_corte: dict, area_m2: float,
           n_parafusos: int = None, area_placa_m2: float = None,
           precos: dict = None) -> list[ItemBOM]:
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
    if area_placa_m2 is None:
        area_placa_m2 = area_m2 * 2.4
    for sku, desc, k, preco in (
            ("OSB11", "OSB 11,1 mm estrutural", 0.45, p["osb_11mm_m2"]),
            ("PLCIM", "Placa cimenticia 8 mm", 0.55, p["placa_cimenticia_8mm_m2"]),
            ("GESSO", "Chapa de gesso 12,5 mm", 1.00, p["gesso_12.5mm_m2"]),
            ("LAROC", "La de rocha 50 mm", 0.90, p["la_rocha_50mm_m2"]),
            ("MEMB", "Membrana hidrofuga", 0.50, p["membrana_hidrofuga_m2"])):
        itens.append(ItemBOM(sku, desc, "m2", round(area_placa_m2 * k, 1),
                             preco, "vedacao"))

    h_fab = len(pecas) / PRODUTIVIDADE["pecas_por_hora_fabrica"]
    h_mont = area_placa_m2 / PRODUTIVIDADE["m2_painel_por_hora_montagem"]
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
