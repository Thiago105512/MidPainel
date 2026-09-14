"""CADASTRO — identidade do projeto, tipologia e unidades (secoes 01, 02, 127, 128).

Ate R12 nada disso existia como dado: o caderno sabia que era uma residencia
porque as pranchas diziam isso por escrito. Sobrecarga de piso, pe-direito e
numero de pavimentos estavam espalhados como literais. Aqui a tipologia passa a
ser uma escolha declarada, com as consequencias normativas penduradas nela.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ------------------------------------------------------------------ unidades
UNIDADES = dict(
    comprimento="mm", area="m2", volume="m3", massa="kg", forca="kN",
    momento="kNm", tensao="MPa", pressao="kN/m2", temperatura="C",
    energia="kWh", potencia="W", vazao="L/s",
    obs="milimetro e a unidade mestre do desenho; kN e kNm as do calculo",
)

MOEDAS = {"BRL": ("R$", 1.0), "USD": ("US$", None), "EUR": ("EUR", None),
          "CNY": ("CNY", None)}

# ------------------------------------------------------------------ tipologias
# sobrecarga em kN/m2 conforme NBR 6120:2019. "manutencao" e o valor de
# cobertura sem acesso de publico. O pe-direito e o MINIMO usual, nao o adotado.
@dataclass(frozen=True)
class Tipologia:
    cod: str
    nome: str
    uso: str
    sobrecarga: float            # kN/m2, piso do uso principal
    sobrecarga_circ: float       # kN/m2, circulacao e escada
    pe_direito_min: int          # mm
    pavimentos_tipicos: tuple
    obs: str = ""


TIPOLOGIAS = [
    Tipologia("CASA", "Casa terrea", "residencial", 1.5, 2.5, 2_500, (1,)),
    Tipologia("SOBRADO", "Sobrado", "residencial", 1.5, 2.5, 2_500, (2, 3)),
    Tipologia("EDIF", "Edificio", "residencial", 1.5, 3.0, 2_500, (3, 4, 5, 6, 7, 8),
              "acima de 5 pavimentos em LSF exige estudo especifico de estabilidade"),
    Tipologia("TINY", "Tiny house", "residencial", 1.5, 2.5, 2_300, (1, 2),
              "largura util limitada pelo transporte rodoviario, nao pelo programa"),
    Tipologia("MODHAB", "Modulo habitacional", "residencial", 1.5, 2.5, 2_400, (1, 2)),
    Tipologia("MODCOM", "Modulo comercial", "comercial", 4.0, 4.0, 2_700, (1, 2)),
    Tipologia("HOTEL", "Hotel", "hospedagem", 1.5, 3.0, 2_600, (2, 3, 4, 5),
              "dormitorio 1,5; corredor 3,0 — a circulacao governa a laje"),
    Tipologia("ESCOLA", "Escola", "institucional", 3.0, 3.0, 3_000, (1, 2, 3)),
    Tipologia("CLINICA", "Clinica", "saude", 3.0, 3.0, 2_800, (1, 2, 3),
              "sala de equipamento pesado exige carga declarada a parte"),
    Tipologia("ESCRIT", "Escritorio", "comercial", 2.5, 3.0, 2_700, (1, 2, 3, 4)),
    Tipologia("GALPAO", "Galpao", "industrial", 5.0, 5.0, 4_000, (1,),
              "sobrecarga real vem do processo; 5,0 e piso minimo de projeto"),
    Tipologia("MEZANINO", "Mezanino", "misto", 3.0, 3.0, 2_400, (1,)),
    Tipologia("COBERTURA", "Cobertura", "cobertura", 0.5, 0.5, 0, (1,),
              "0,5 kN/m2 e carga de manutencao, sem acesso de publico"),
    Tipologia("INDUSTRIAL", "Estrutura industrial", "industrial", 5.0, 5.0, 4_000, (1, 2)),
    Tipologia("FACHADA", "Fachada", "vedacao", 0.0, 0.0, 0, (1,),
              "nao recebe carga de piso; governada por vento e peso proprio"),
    Tipologia("RETROFIT", "Retrofit", "misto", 1.5, 3.0, 2_400, (1, 2, 3),
              "estrutura existente entra como condicao de contorno, nao como hipotese"),
    Tipologia("AMPLIACAO", "Ampliacao", "misto", 1.5, 3.0, 2_500, (1, 2)),
    Tipologia("HIBRIDA", "Estrutura hibrida", "misto", 2.0, 3.0, 2_600, (1, 2, 3),
              "LSF + laminado ou concreto: a interface e o ponto critico"),
    Tipologia("CONTAINER", "Estrutura container-like", "misto", 2.0, 3.0, 2_350, (1, 2, 3)),
    Tipologia("TEMP", "Estrutura temporaria", "temporaria", 2.0, 3.0, 2_400, (1,),
              "vida util reduzida NAO reduz coeficiente de seguranca de vento"),
]
POR_COD = {t.cod: t for t in TIPOLOGIAS}


@dataclass
class Cadastro:
    """Secao 02 — o que identifica o projeto, nao o que o descreve."""
    project_id: str
    nome: str
    cliente: str
    localizacao: str
    coordenadas: tuple           # (lat, lon) em graus decimais
    tipologia: str               # cod em TIPOLOGIAS
    pavimentos: int
    area_m2: float
    pe_direito: int              # mm, adotado
    sistema: str
    normas: tuple
    unidades: dict = field(default_factory=lambda: dict(UNIDADES))
    moeda: str = "BRL"
    empresa: str = ""
    engenheiro: str = ""
    arquiteto: str = ""
    responsaveis: tuple = ()
    status: str = "ESTUDO"
    revisao: str = "R00"
    data_inicio: str = ""
    data_emissao: str = ""
    observacoes: str = ""

    @property
    def tipo(self) -> Tipologia:
        return POR_COD[self.tipologia]

    def simbolo_moeda(self) -> str:
        return MOEDAS[self.moeda][0]


STATUS = ("ESTUDO", "ANTEPROJETO", "EXECUTIVO", "APROVADO",
          "LIBERADO PARA FABRICACAO", "EM OBRA", "CONCLUIDO")


def validar(c: Cadastro) -> list[str]:
    """Devolve os problemas do cadastro. Lista vazia = cadastro completo."""
    p = []
    if c.tipologia not in POR_COD:
        p.append(f"tipologia '{c.tipologia}' nao existe")
    else:
        t = c.tipo
        if c.pe_direito < t.pe_direito_min:
            p.append(f"pe-direito {c.pe_direito} mm abaixo do minimo "
                     f"{t.pe_direito_min} mm da tipologia {t.nome}")
        if t.pavimentos_tipicos and c.pavimentos not in t.pavimentos_tipicos:
            p.append(f"{c.pavimentos} pavimentos fora do usual "
                     f"{t.pavimentos_tipicos} para {t.nome} — exige justificativa")
    if c.status not in STATUS:
        p.append(f"status '{c.status}' fora da lista")
    if c.moeda not in MOEDAS:
        p.append(f"moeda '{c.moeda}' nao cadastrada")
    lat, lon = c.coordenadas
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        p.append(f"coordenadas {c.coordenadas} fora do globo")
    if not c.normas:
        p.append("nenhuma norma declarada")
    return p
