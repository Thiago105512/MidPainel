"""NORMAS — sistema normativo selecionavel por pais (secoes 11 e 44).

O projeto cita 23 normas, mas ate R13 elas eram citacao: texto na prancha. Aqui
viram escolha estrutural. Trocar o pais troca, de uma vez, a norma de perfil
formado a frio, a de cargas, a de vento, a de combinacoes e os coeficientes —
e a auditoria passa a exigir que o conjunto seja coerente, porque misturar
combinacao do Eurocode com resistencia da NBR e um erro que nao aparece no
desenho.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Sistema:
    cod: str
    pais: str
    formado_frio: str      # dimensionamento de perfil formado a frio
    laminado: str
    cargas: str
    vento: str
    combinacoes: str
    perfis: str            # padronizacao dimensional
    gama_a1: float         # coef. de ponderacao da resistencia, escoamento
    gama_a2: float         # idem, ruptura
    obs: str = ""


SISTEMAS = [
    Sistema("BR", "Brasil", "NBR 14762:2010", "NBR 8800:2008", "NBR 6120:2019",
            "NBR 6123:1988", "NBR 8681:2003", "NBR 6355:2012", 1.10, 1.65,
            "NBR 15253 cobre o perfil de LSF; NBR 15575 o desempenho"),
    Sistema("US", "Estados Unidos", "AISI S100-16", "AISC 360-16", "ASCE 7-22",
            "ASCE 7-22", "ASCE 7-22", "AISI S240", 1.0, 1.0,
            "LRFD usa fator de resistencia phi, nao coeficiente divisor"),
    Sistema("EU", "Uniao Europeia", "EN 1993-1-3", "EN 1993-1-1", "EN 1991-1-1",
            "EN 1991-1-4", "EN 1990", "EN 10162", 1.00, 1.25),
    Sistema("AUNZ", "Australia e Nova Zelandia", "AS/NZS 4600", "AS 4100",
            "AS/NZS 1170.1", "AS/NZS 1170.2", "AS/NZS 1170.0", "AS 1397", 1.0, 1.0),
    Sistema("UK", "Reino Unido", "BS EN 1993-1-3", "BS EN 1993-1-1",
            "BS EN 1991-1-1", "BS EN 1991-1-4", "BS EN 1990", "BS 2994", 1.00, 1.25),
    Sistema("CN", "China", "GB 50018", "GB 50017", "GB 50009", "GB 50009",
            "GB 50068", "GB/T 6723", 1.0, 1.0),
]
POR_SISTEMA = {s.cod: s for s in SISTEMAS}
PADRAO = "BR"

# Normas de apoio que nao mudam o dimensionamento mas mudam o projeto
APOIO = {
    "BR": {
        "desempenho": "NBR 15575", "LSF": "NBR 15253", "incendio": "NBR 14432",
        "protecao_incendio": "NBR 14323", "acessibilidade": "NBR 9050",
        "escadas": "NBR 9077", "termica": "NBR 15220-3", "acustica": "NBR 10152",
        "eletrica": "NBR 5410", "agua_fria": "NBR 5626", "esgoto": "NBR 8160",
        "pluvial": "NBR 10844", "gas": "NBR 13523", "hvac": "NBR 16401-2",
        "guarda_corpo": "NBR 14718", "fundacao": "NBR 6122",
        "corrosividade": "NBR 14643", "desenho": "NBR 10068 / 10582 / 8403 / 8402 / 6492",
    },
}

# --------------------------------------------------------------- incendio
# TRRF (tempo requerido de resistencia ao fogo), NBR 14432, em minutos.
# (H): a resistencia efetiva de cada composicao depende de ENSAIO do fabricante.
# Nenhuma tabela substitui o relatorio de ensaio — por isso entra declarada.
TRRF = {
    ("residencial", 6): 30, ("residencial", 12): 30, ("residencial", 23): 60,
    ("residencial", 30): 90, ("comercial", 6): 30, ("comercial", 12): 60,
    ("comercial", 23): 60, ("comercial", 30): 90,
    ("institucional", 6): 30, ("institucional", 12): 60,
    ("saude", 6): 30, ("saude", 12): 60,
    ("hospedagem", 6): 30, ("hospedagem", 12): 60, ("hospedagem", 23): 60,
    ("industrial", 6): 30, ("industrial", 12): 60,
}
# Protecao por chapa de gesso: minutos por camada de 12,5 mm em cada face (H)
PROTECAO_GESSO = {1: 30, 2: 60, 3: 90, 4: 120}


def trrf(uso: str, altura_m: float) -> int:
    """TRRF em minutos por uso e altura da edificacao (NBR 14432)."""
    faixas = [6, 12, 23, 30]
    for f in faixas:
        if altura_m <= f and (uso, f) in TRRF:
            return TRRF[(uso, f)]
    return max((v for (u, _), v in TRRF.items() if u == uso), default=120)


def camadas_para_trrf(minutos: int) -> int:
    """Quantas camadas de gesso de 12,5 mm por face o TRRF exige (H)."""
    for n in sorted(PROTECAO_GESSO):
        if PROTECAO_GESSO[n] >= minutos:
            return n
    return max(PROTECAO_GESSO) + 1
