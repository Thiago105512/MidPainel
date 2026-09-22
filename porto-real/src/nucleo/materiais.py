"""MATERIAIS — acos, revestimentos e demais materiais (secao 10).

Tres coisas que ate R13 estavam implicitas viram dado aqui:

1. O aco. Ate agora o projeto usava E = 205 GPa e nada mais; nao havia fy, nao
   havia fu, e portanto nenhuma verificacao de resistencia era possivel — so de
   flecha. Sem fy nao existe NBR 14762.
2. O revestimento. "Galvanizado" nao e especificacao: Z275 e. E a massa de
   zinco tem consequencia dimensional — cerca de 20 micrometros por face —, de
   durabilidade e de soldabilidade.
3. A classe de corrosividade. Manaus e atmosfera tropical umida; a escolha do
   revestimento deixa de ser habito e passa a ser consequencia da classe.
"""
from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------- aco
E_ACO = 205_000.0        # MPa, NBR 14762
G_ACO = 78_850.0         # MPa
POISSON = 0.30
DENSIDADE_ACO = 7_850.0  # kg/m3
ALFA_TERMICO = 1.2e-5    # /C


@dataclass(frozen=True)
class Aco:
    cod: str
    fy: float            # MPa, escoamento
    fu: float            # MPa, ruptura
    along: float         # %, alongamento minimo em 50 mm
    norma: str
    processo: str        # formado a frio, laminado, etc.
    obs: str = ""

    @property
    def fyd(self) -> float:
        """Resistencia de calculo ao escoamento (gama = 1,10, NBR 14762)."""
        return self.fy / 1.10

    @property
    def fud(self) -> float:
        """Resistencia de calculo a ruptura (gama = 1,65 em ligacoes)."""
        return self.fu / 1.65


ACOS = [
    Aco("ZAR 230", 230, 310, 18, "NBR 7008 / NBR 15253", "formado a frio",
        "grau usual de montante e guia de LSF"),
    Aco("ZAR 250", 250, 330, 16, "NBR 7008", "formado a frio"),
    Aco("ZAR 280", 280, 360, 14, "NBR 7008", "formado a frio"),
    Aco("ZAR 345", 345, 430, 12, "NBR 7008", "formado a frio",
        "grau estrutural; reduz peso mas exige raio de dobra maior"),
    Aco("ASTM A653 Gr.33", 230, 310, 20, "ASTM A653", "formado a frio"),
    Aco("ASTM A653 Gr.50", 340, 450, 12, "ASTM A653", "formado a frio"),
    Aco("ASTM A36", 250, 400, 20, "ASTM A36", "laminado",
        "perfil laminado da interface hibrida"),
    Aco("ASTM A572 Gr.50", 345, 450, 18, "ASTM A572", "laminado"),
    Aco("AISI 304", 205, 515, 40, "ASTM A240", "inox",
        "so onde a corrosividade justifica: custo por kg e multiplo do galvanizado"),
]
POR_ACO = {a.cod: a for a in ACOS}

# --------------------------------------------------------------- revestimento
DENS_ZINCO = 7_140.0     # kg/m3
DENS_ALZN = 3_750.0      # kg/m3, liga 55 % Al - 43,4 % Zn - 1,6 % Si


@dataclass(frozen=True)
class Revestimento:
    cod: str
    massa_total: float   # g/m2, somando as DUAS faces
    liga: str
    classes_ok: tuple    # classes de corrosividade em que se admite

    @property
    def densidade(self) -> float:
        return DENS_ZINCO if self.liga == "Zn" else DENS_ALZN

    @property
    def espessura_face(self) -> float:
        """Micrometros por face: massa/2 dividida pela densidade da liga."""
        return (self.massa_total / 2) / self.densidade * 1000.0

    @property
    def acrescimo_dimensional(self) -> float:
        """mm somados a espessura do aco base, nas duas faces."""
        return 2 * self.espessura_face / 1000.0


REVESTIMENTOS = [
    Revestimento("Z120", 120, "Zn", ("C1", "C2")),
    Revestimento("Z180", 180, "Zn", ("C1", "C2", "C3")),
    Revestimento("Z275", 275, "Zn", ("C1", "C2", "C3", "C4")),
    Revestimento("Z350", 350, "Zn", ("C1", "C2", "C3", "C4")),
    Revestimento("AZ150", 150, "AlZn", ("C1", "C2", "C3", "C4")),
    Revestimento("AZ185", 185, "AlZn", ("C1", "C2", "C3", "C4", "C5")),
]
POR_REV = {r.cod: r for r in REVESTIMENTOS}

# Classes de corrosividade atmosferica (ISO 9223 / NBR 14643)
CORROSIVIDADE = {
    "C1": ("muito baixa", "interior seco e aquecido"),
    "C2": ("baixa", "rural, interior com condensacao ocasional"),
    "C3": ("media", "urbana e industrial leve, litoral distante"),
    "C4": ("alta", "industrial e litoral"),
    "C5": ("muito alta", "industrial pesado, litoral com salinidade alta"),
}
# NBR 15253: revestimento minimo do perfil estrutural de LSF
REVESTIMENTO_MINIMO_LSF = "Z275"

# --------------------------------------------------------------- outros
@dataclass(frozen=True)
class Material:
    cod: str
    nome: str
    densidade: float     # kg/m3
    E: float             # MPa (0 = nao estrutural)
    lambda_t: float      # W/mK, condutividade
    # Calor especifico [kJ/kg.K], NBR 15220-2 anexo B. Sem ele nao existe
    # capacidade termica, e sem capacidade termica nao existe atraso termico —
    # que e a metade da verificacao da ZB8 que o projeto nao fazia ate R58.
    calor_especifico: float = 1.00
    obs: str = ""
    # A norma pertence ao MATERIAL, nao a camada. Ela nasceu na camada em R34 e
    # durou uma revisao: duas fontes para o mesmo fato divergem na primeira
    # correcao, e foi exatamente esse o defeito 39 — dois codigos para a mesma
    # peca. Nao ha razao para repetir o erro dois dias depois de documenta-lo.
    norma: str = ""
    # Formato comercial: largura x altura em mm, ou 0 quando nao se compra em
    # chapa. Sem isto a quantidade fica em m2 abstratos, e ninguem compra m2.
    chapa: tuple = ()


MATERIAIS = [
    Material("ACO", "Aco estrutural", 7850, 205_000, 55.0, 0.46,
             norma="NBR 15253 / NBR 6355"),
    Material("ALU", "Aluminio", 2700, 70_000, 200.0, 0.88, "esquadria e ACM",
             norma="NBR 10821"),
    Material("MAD", "Madeira conifera", 500, 10_000, 0.13, 1.34, norma="NBR 7190"),
    Material("OSB", "OSB estrutural", 650, 3_500, 0.13, 1.34, "diafragma e substrato",
             norma="NBR 14810 / EN 300", chapa=(1220, 2440)),
    Material("PLY", "Compensado", 600, 7_000, 0.14, 1.34, norma="NBR 12498",
             chapa=(1220, 2440)),
    Material("CLT", "CLT", 480, 11_000, 0.12, 1.34, norma="EN 16351"),
    Material("CONC", "Concreto estrutural", 2500, 30_000, 1.75, 1.0, norma="NBR 6118"),
    Material("PLCIM", "Placa cimenticia", 1700, 6_000, 0.35, 0.84, "fechamento externo",
             norma="NBR 15498", chapa=(1200, 2400)),
    Material("GESSO", "Chapa de gesso", 750, 2_000, 0.35, 0.84, norma="NBR 14715",
             chapa=(1200, 2400)),
    Material("GESSORU", "Chapa de gesso RU", 800, 2_000, 0.35, 0.84, "area umida",
             norma="NBR 14715", chapa=(1200, 2400)),
    Material("LAROCHA", "La de rocha", 64, 0, 0.045, 0.75, "rolo ou painel",
             norma="NBR 11722", chapa=(1200, 25_000)),
    Material("LAVIDRO", "La de vidro", 20, 0, 0.040, 0.7, "rolo",
             norma="NBR 11722", chapa=(1200, 25_000)),
    Material("XPS", "XPS", 33, 0, 0.035, 1.42, "quebra termica da ISO strip",
             norma="NBR 11752", chapa=(600, 1250)),
    Material("EPS", "EPS", 20, 0, 0.040, 1.42, norma="NBR 11752", chapa=(1000, 2000)),
    Material("ACM", "ACM", 1600, 0, 0.50, 0.88, norma="NBR 15827", chapa=(1250, 3200)),
    Material("PIR", "Painel sandwich PIR", 40, 0, 0.023, 1.67, "cobertura",
             norma="NBR 16373", chapa=(1000, 12_000)),
    Material("PUR", "Painel sandwich PUR", 40, 0, 0.026, 1.67, norma="NBR 16373",
             chapa=(1000, 12_000)),
    Material("VIDRO", "Vidro", 2500, 70_000, 1.00, 0.84, norma="NBR 7199"),
]
POR_MATERIAL = {m.cod: m for m in MATERIAIS}


def revestimento_para(classe: str) -> list[str]:
    """Revestimentos admissiveis na classe de corrosividade."""
    return [r.cod for r in REVESTIMENTOS if classe in r.classes_ok]
