"""
PROJETO PORTO REAL — modelo geometrico parametrico.

Fonte normativa: "Porto Real — Lista Consolidada de Parametros",
revisao pos-R32, que declara substituir os valores da R32 anterior.
Onde o "Guia Explicativo R32" diverge, prevalece a Lista Consolidada
(ver docs/DIVERGENCIAS.md).

Unidade: MILIMETRO. Origem (0,0) no canto frontal esquerdo do lote,
X para a direita (testada), Y para o fundo do lote.
Malha principal 600 / subgrid 300 / ajuste fino 150.

Itens marcados H no briefing permanecem hipoteses tecnicas: este modelo
os reproduz, nao os valida.
"""
from __future__ import annotations

from dataclasses import dataclass, field

GRID = 600
SUBGRID = 300

# ---------------------------------------------------------------- lote
LOTE_L = 20_000
LOTE_P = 40_000
LOTE_AREA_M2 = (LOTE_L * LOTE_P) / 1e6          # 800,00 m2

RECUO_FRENTE = 7_200
RECUO_ESQ = 2_400
RECUO_DIR_MIN = 3_000
RECUO_FUNDO_MIN = 5_000

# parametros urbanisticos didaticos (H) — SU16 Tarumã/Tarumã-Açu
TAXA_OCUP_MAX = 0.50
CAMT_MAX = 1.00
GABARITO_MAX = 4

# ------------------------------------------------------- alturas / niveis
PE_DIREITO = 2_600
PISO_A_PISO = 3_000
NIVEL_TERREO = 0
NIVEL_SUPERIOR = 3_000
TOPO_PLATIBANDA = 6_150          # H
ALT_MURO = 2_200
INCLIN_COBERTURA = 0.05          # 5 %
ESP_PAINEL_PIR = 75

# ------------------------------------------------------------- vedacoes
PAR_EXT = 150                     # H — externa / hidraulica / acustica
PAR_INT = 100                     # H — divisoria interna simples


@dataclass
class Amb:
    """Ambiente modular. x,y = canto inferior-esquerdo (eixo a eixo)."""
    cod: str
    nome: str
    x: int
    y: int
    w: int
    h: int
    pav: str = "T"
    piso: str = "porcelanato"
    nivel: int = 0
    aberto: bool = False          # nao computa como area fechada
    molhado: bool = False

    @property
    def area_mod(self) -> float:
        return (self.w * self.h) / 1e6

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    def area_util(self, ext: set[str]) -> float:
        """Area liquida descontando meia espessura de cada parede do contorno."""
        dx = sum((PAR_EXT if s in ext else PAR_INT) / 2 for s in ("O", "L"))
        dy = sum((PAR_EXT if s in ext else PAR_INT) / 2 for s in ("S", "N"))
        return ((self.w - dx) * (self.h - dy)) / 1e6


# =========================================================================
# PAVIMENTO TERREO — soma modular = 174,24 m2 (alvo do briefing: 174,24)
# =========================================================================
# pares de ambientes INTEGRADOS: nao ha parede entre eles (espaco unico).
# A derivacao de paredes consulta esta lista; integrar e uma decisao de
# projeto declarada aqui, nao um vao largo desenhado a mao.
INTEGRADOS = {
    frozenset(("T-COZ", "T-GOU")),   # cozinha + gourmet = espaco unico
    frozenset(("T-SOC", "T-GOU")),   # estar/jantar + gourmet = fita social continua
    frozenset(("T-SOC", "T-COR")),   # core/escada aberto para o social (poco de luz)
}

TERREO: list[Amb] = [
    Amb("T-GAR", "GARAGEM",            2_400,  7_200, 6_000, 6_000),
    Amb("T-HAL", "HALL",               8_400,  9_600, 1_800, 3_600),
    Amb("T-REV", "QUARTO REVERSIVEL", 10_200,  7_200, 3_000, 6_000),
    Amb("T-BWC", "BANHO",             13_200,  7_200, 1_800, 2_400, molhado=True),
    Amb("T-OFI", "OFICINA",            2_400, 13_200, 3_000, 3_000),
    Amb("T-LAV", "LAVANDERIA",         2_400, 16_200, 3_000, 3_000, molhado=True),
    Amb("T-SOC", "ESTAR / JANTAR",     5_400, 13_200, 4_200, 6_000),
    Amb("T-COR", "CORE / ESCADA",      9_600, 13_200, 2_400, 6_000),
    Amb("T-COZ", "COZINHA",            2_400, 19_200, 3_000, 6_000, molhado=True),
    Amb("T-GOU", "GOURMET",            5_400, 19_200, 4_200, 7_200, molhado=True),
    Amb("T-DML", "DESPENSA / DML",     2_400, 25_200, 3_000, 1_200),
]

# areas externas cobertas / descobertas do terreo (nao computam area fechada)
TERREO_ABERTO: list[Amb] = [
    Amb("T-VAR", "VARANDA DE ENTRADA", 8_400,  7_200, 1_800, 2_400, aberto=True),
    Amb("T-DKL", "DECK LATERAL",      12_000, 13_200, 4_800, 6_000, aberto=True),
    Amb("T-DKP", "DECK DA PISCINA",    9_600, 19_200, 4_800, 7_200, aberto=True),
]

# =========================================================================
# PAVIMENTO SUPERIOR
# briefing: 84,96 m2 fechados. Modelo: 86,40 m2 (delta +1,44 — ver nota 3
# de docs/DIVERGENCIAS.md: o hall de 4,32 m2 do briefing nao serve as tres
# suites sem corredor; adotado hall compacto de 5,76 m2, dentro da meta de
# 8 % de circulacao).
# =========================================================================
SUPERIOR: list[Amb] = [
    Amb("S-S02", "SUITE 02",  2_400, 13_200, 5_400, 4_800, pav="S", nivel=NIVEL_SUPERIOR),
    Amb("S-S03", "SUITE 03",  2_400, 18_000, 5_400, 4_800, pav="S", nivel=NIVEL_SUPERIOR),
    Amb("S-HAL", "HALL",      7_800, 16_800, 2_400, 2_400, pav="S", nivel=NIVEL_SUPERIOR),
    Amb("S-MAS", "SUITE MASTER", 10_200, 16_200, 6_000, 4_800, pav="S", nivel=NIVEL_SUPERIOR),
]

SUPERIOR_ABERTO: list[Amb] = [
    Amb("S-BAL", "VARANDA MASTER", 10_200, 21_000, 6_000, 1_800,
        pav="S", nivel=NIVEL_SUPERIOR, aberto=True),
]

# ------------------------------------------- subdivisoes internas (1:50)
# (cod_pai, nome, x, y, w, h) — particoes dentro do modulo
SUBDIVISOES = [
    # suites 2 e 3: banheiro 1800x2400 + closet 600 de profundidade
    ("S-S02", "BANHO",  2_400, 13_200, 1_800, 2_400),
    ("S-S02", "CLOSET", 2_400, 15_600,   600, 2_400),
    ("S-S03", "BANHO",  2_400, 18_000, 1_800, 2_400),
    ("S-S03", "CLOSET", 2_400, 20_400,   600, 2_400),
    # master 6000x4800: banho 2400x3000 + closet 2400x1800 + dormitorio
    ("S-MAS", "BANHO",  10_200, 16_200, 2_400, 3_000),
    ("S-MAS", "CLOSET", 10_200, 19_200, 2_400, 1_800),
]

# =========================================================================
# ESQUADRIAS — familia unificada da Lista Consolidada
# tipo: (largura, altura, peitoril, familia)
# =========================================================================
ESQUADRIAS = {
    "PG01": (5_400, 2_400,     0, "portao de correr, aluminio ripado"),
    "P01":  (1_100, 2_800,     0, "porta principal, alta opaca"),
    "P02":  (  900, 2_100,     0, "porta interna (familia unificada)"),
    "P04":  (  900, 2_100,     0, "porta de servico, resistente a umidade"),
    "J01":  (1_200, 1_200, 1_100, "janela de dormitorio, aluminio"),
    "J02":  (  600,   600, 1_500, "janela de banheiro, alta translucida"),
    "J03":  (  900, 1_500,   900, "janela de office/master, aluminio"),
    "PV01": (3_600, 2_400,     0, "vao social posterior"),
    "PV02": (2_400, 2_400,     0, "porta-balcao do estar (familia adicional — ver DIVERGENCIAS)"),
}

# (tipo, x, y, orientacao, pavimento) — x,y = centro do vao no eixo da parede
# orientacao: "H" vao em parede horizontal, "V" em parede vertical
VAOS = [
    # ---- terreo: faixa frontal
    ("PG01",  5_400,  7_200, "H", "T"),   # portao da garagem (testada)
    ("P01",   9_300,  9_600, "H", "T"),   # entrada principal
    ("P02",   8_400, 12_000, "V", "T"),   # hall -> garagem
    ("P02",  10_200, 10_800, "V", "T"),   # hall -> quarto reversivel
    ("P02",  13_200,  8_400, "V", "T"),   # quarto reversivel -> banho
    ("J01",  11_700,  7_200, "H", "T"),   # janela quarto reversivel
    ("J02",  14_100,  7_200, "H", "T"),   # janela banho
    # ---- terreo: faixa social
    ("P02",   9_000, 13_200, "H", "T"),   # hall -> estar/jantar
    ("P02",   6_900, 13_200, "H", "T"),   # garagem -> estar/jantar
    ("PV01", 12_000, 16_200, "V", "T"),   # core envidracado -> deck lateral
    ("PV01",  7_500, 26_400, "H", "T"),   # gourmet -> deck e piscina
    ("PV01",  9_600, 22_800, "V", "T"),   # gourmet -> deck lateral
    # ---- terreo: prumada de servico na face oeste
    ("P04",   3_900, 13_200, "H", "T"),   # garagem -> oficina (fora da vista social)
    ("P04",   3_900, 16_200, "H", "T"),   # oficina -> lavanderia
    ("P04",   3_900, 19_200, "H", "T"),   # lavanderia -> cozinha
    ("P04",   3_900, 25_200, "H", "T"),   # cozinha -> despensa/DML
    ("J01",   2_400, 14_700, "V", "T"),   # janela oficina
    ("J01",   2_400, 17_700, "V", "T"),   # janela lavanderia
    ("J01",   2_400, 21_000, "V", "T"),   # janela cozinha
    ("J01",   2_400, 23_400, "V", "T"),   # janela cozinha (bancada)
    # ---- superior
    ("P02",   7_800, 17_400, "V", "S"),   # hall -> suite 02
    ("P02",   7_800, 18_600, "V", "S"),   # hall -> suite 03
    ("P02",  10_200, 18_000, "V", "S"),   # hall -> suite master
    ("J01",   2_400, 15_600, "V", "S"),   # janela suite 02
    ("J01",   2_400, 20_400, "V", "S"),   # janela suite 03
    ("J02",   3_600, 13_200, "H", "S"),   # janela banho suite 02
    ("J03",  13_200, 21_000, "H", "S"),   # master -> varanda
    ("J01",  16_200, 18_600, "V", "S"),   # janela master (lateral direita)
    ("J02",  11_400, 16_200, "H", "S"),   # janela banho master
]

# =========================================================================
# ELEMENTOS EXTERNOS
# =========================================================================
PISCINA = dict(x=5_400, y=27_600, w=4_800, h=2_400,
               prainha_w=1_200, prof_prainha=300, prof_principal=1_150,
               lamina_m2=11.52, volume_m3=10.80)
CASA_MAQUINAS = dict(x=10_800, y=27_600, w=1_500, h=1_200)
DECK = dict(x=4_200, y=26_400, w=7_200, h=4_800)          # envolve a piscina
FAIXA_TECNICA = dict(x=16_800, y=0, w=3_200, h=LOTE_P)     # lateral direita
CAIXA_DAGUA = dict(x=10_200, y=16_200, w=2_400, h=2_400,
                   volume_l=2_000, pe_direito=2_100, carga_kg=2_500)

# escada em U — 18 espelhos x 166,67 mm, piso 300, largura util 1.000
ESCADA = dict(x=9_600, y=13_200, w=2_400, h=6_000,
              espelhos=18, alt_espelho=3_000 / 18, piso=300,
              larg_lance=1_000, patamar=1_000, blondel=2 * (3_000 / 18) + 300)

# ---------------------------------------------------------------- cobertura
# planos de cobertura com 5 % de caimento e calha externa 150x100
COBERTURA = dict(inclinacao=INCLIN_COBERTURA, calha_l=150, calha_h=100,
                 descidas=4, dn_descida=100,
                 area_contrib_m2=174.24, intensidade_mm_h=180,
                 coef_escoamento=0.95, vazao_total_ls=8.2764)


# =========================================================================
# quadros derivados
# =========================================================================
def area_fechada(pav: str) -> float:
    lst = TERREO if pav == "T" else SUPERIOR
    return round(sum(a.area_mod for a in lst), 2)


def area_aberta(pav: str) -> float:
    lst = TERREO_ABERTO if pav == "T" else SUPERIOR_ABERTO
    return round(sum(a.area_mod for a in lst), 2)


def verificacao_urbanistica() -> list[tuple[str, str, str, bool]]:
    proj = area_fechada("T")
    total = area_fechada("T") + area_fechada("S")
    to = proj / LOTE_AREA_M2
    ca = total / LOTE_AREA_M2
    return [
        ("Taxa de ocupacao", f"{to*100:.2f} %", f"max {TAXA_OCUP_MAX*100:.0f} %", to <= TAXA_OCUP_MAX),
        ("Coef. de aproveitamento", f"{ca:.3f}", f"max {CAMT_MAX:.2f}", ca <= CAMT_MAX),
        ("Gabarito", "2 pavimentos", f"max {GABARITO_MAX}", True),
        ("Recuo frontal", f"{RECUO_FRENTE} mm", "conforme SU16 (H)", True),
        ("Recuo lateral esq.", f"{RECUO_ESQ} mm", "sem parede na divisa", True),
        ("Faixa tecnica dir.", f"{FAIXA_TECNICA['w']} mm", f"min {RECUO_DIR_MIN} mm", FAIXA_TECNICA["w"] >= RECUO_DIR_MIN),
        ("Recuo de fundo", f"{LOTE_P - 26_400} mm", f"min {RECUO_FUNDO_MIN} mm", (LOTE_P - 26_400) >= RECUO_FUNDO_MIN),
    ]


if __name__ == "__main__":
    print(f"lote ............ {LOTE_AREA_M2:.2f} m2")
    print(f"terreo fechado .. {area_fechada('T'):.2f} m2   (briefing 174,24)")
    print(f"superior fechado  {area_fechada('S'):.2f} m2   (briefing  84,96)")
    print(f"total fechado ... {area_fechada('T')+area_fechada('S'):.2f} m2   (briefing 259,20)")
    print(f"terreo aberto ... {area_aberta('T'):.2f} m2")
    print(f"varanda master .. {area_aberta('S'):.2f} m2   (briefing  10,80)")
    for nome, val, lim, ok in verificacao_urbanistica():
        print(f"  [{'OK ' if ok else 'NAO'}] {nome:<24} {val:<14} {lim}")
