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

# ------------------------------------------------------------- orientacao
# A testada (Y = 0) recebe sol da MANHA -> a frente do lote esta a LESTE.
# Consequencia do sistema de coordenadas: +Y aponta para OESTE (fundo),
# +X aponta para NORTE (lateral direita / faixa tecnica),
# X = 0 e a lateral SUL (recuo esquerdo).
AZIMUTE_TESTADA = 90          # graus: 90 = leste
NORTE_EM_PLANTA = -90         # rotacao do simbolo de norte (aponta para +X)
LATITUDE = -3.10              # Manaus
ZONA_BIOCLIMATICA = 8         # NBR 15220-3

# alturas solares criticas em Manaus (lat 3 S)
SOL = {
    "solsticio_jun_meiodia": (63.5, "N"),   # altitude, face iluminada
    "solsticio_dez_meiodia": (69.7, "S"),
    "equinocio_meiodia": (86.9, "zenital"),
    "leste_8h": (30.0, "L"),
    "oeste_16h": (30.0, "O"),
}

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
    # ---- faixa frontal (leste)
    Amb("T-GAR", "GARAGEM",              2_400,  7_200, 6_000, 6_000),
    Amb("T-HAL", "HALL",                 8_400,  9_600, 1_800, 3_600),
    Amb("T-BWC", "BANHO COMPARTILHADO", 10_200, 10_800, 1_800, 2_400, molhado=True),
    Amb("T-REV", "QUARTO REVERSIVEL",   12_000,  7_200, 3_000, 6_000),
    # ---- banda de servico interna, face sul: enfilade a partir da garagem
    Amb("T-OFI", "OFICINA",              2_400, 13_200, 3_000, 3_000),
    Amb("T-LAV", "LAVANDERIA",           2_400, 16_200, 3_000, 3_000, molhado=True),
    Amb("T-COZ", "COZINHA",              2_400, 19_200, 3_000, 6_000, molhado=True),
    Amb("T-DES", "DESPENSA",             2_400, 25_200, 3_000, 1_200),
    # ---- faixa social
    Amb("T-SOC", "ESTAR / JANTAR",       5_400, 13_200, 4_200, 6_000),
    Amb("T-COR", "CORE / ESCADA",        9_600, 13_200, 2_400, 6_000),
    Amb("T-GOU", "GOURMET",              5_400, 19_200, 4_200, 7_200, molhado=True),
    Amb("T-DEP", "DEPOSITO / DML",       9_600, 19_200, 1_200, 3_000),
]

# areas externas cobertas / descobertas do terreo (nao computam area fechada)
TERREO_ABERTO: list[Amb] = [
    Amb("T-VAR", "VARANDA DE ENTRADA",   8_400,  7_200, 1_800, 2_400, aberto=True),
    Amb("T-JLE", "JARDIM LESTE",        10_200,  7_200, 1_800, 3_600, aberto=True),
    Amb("T-JNO", "JARDIM NORTE",        15_000,  7_200, 1_800, 6_000, aberto=True),
    Amb("T-DKL", "DECK NORTE",          12_000, 13_200, 4_800, 6_000, aberto=True),
    Amb("T-PAT", "PATIO NORTE",         10_800, 19_200, 6_000, 7_200, aberto=True),
    Amb("T-ALP", "ALPENDRE DO GOURMET",  5_400, 26_400, 4_200, 2_400, aberto=True),
    Amb("T-DKP", "DECK DA PISCINA",      4_200, 28_800, 7_200, 4_800, aberto=True),
]

def cobertos() -> list[Amb]:
    return TERREO + [a for a in TERREO_ABERTO if a.cod in ("T-VAR", "T-ALP")]

# ambientes cobertos = fechados + areas com cobertura propria
def cobertos() -> list[Amb]:
    return TERREO + [a for a in TERREO_ABERTO
                     if a.cod in ("T-VAR", "T-LOG", "T-PSE", "T-ALP")]

# ambientes cobertos = fechados + areas com cobertura propria
def cobertos() -> list[Amb]:
    return TERREO + [a for a in TERREO_ABERTO
                     if a.cod in ("T-VAR", "T-LOG", "T-CSE")]

# ambientes cobertos = fechados + alpendre (para a planta de cobertura)
def cobertos() -> list[Amb]:
    return TERREO + [a for a in TERREO_ABERTO if a.cod in ("T-ALP", "T-VAR")]

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
    Amb("S-MAS", "SUITE MASTER", 7_800, 19_200, 6_000, 4_800, pav="S", nivel=NIVEL_SUPERIOR),
]

SUPERIOR_ABERTO: list[Amb] = [
    Amb("S-BAL", "VARANDA MASTER", 7_800, 24_000, 6_000, 1_800,
        pav="S", nivel=NIVEL_SUPERIOR, aberto=True),
]

# ------------------------------------------- subdivisoes internas (1:50)
# (cod_pai, nome, x, y, w, h) — particoes dentro do modulo
SUBDIVISOES = [
    ("S-S02", "BANHO",  2_400, 13_200, 1_800, 2_400),
    ("S-S02", "CLOSET", 2_400, 15_600,   600, 2_400),
    ("S-S03", "BANHO",  2_400, 18_000, 1_800, 2_400),
    ("S-S03", "CLOSET", 2_400, 20_400,   600, 2_400),
    ("S-MAS", "BANHO",   7_800, 19_200, 2_400, 3_000),
    ("S-MAS", "CLOSET",  7_800, 22_200, 2_400, 1_800),
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
    # ---- faixa frontal
    ("PG01",  5_400,  7_200, "H", "T"),   # portao da garagem (testada leste)
    ("P01",   9_300,  9_600, "H", "T"),   # entrada principal
    ("P02",   8_400, 12_000, "V", "T"),   # hall -> garagem
    ("P02",  10_200, 12_000, "V", "T"),   # hall -> banho compartilhado
    ("P02",  12_000, 12_000, "V", "T"),   # banho -> quarto reversivel
    ("J01",  13_500,  7_200, "H", "T"),   # janela reversivel (leste)
    ("J01",  15_000, 10_200, "V", "T"),   # janela reversivel (norte)
    ("J02",  11_100, 10_800, "H", "T"),   # janela banho
    # ---- enfilade de servico: garagem -> oficina -> lavanderia -> cozinha
    ("P04",   3_900, 13_200, "H", "T"),   # garagem -> oficina (invisivel do social)
    ("P04",   3_900, 16_200, "H", "T"),   # oficina -> lavanderia
    ("P04",   3_900, 19_200, "H", "T"),   # lavanderia -> cozinha
    ("P02",   3_900, 25_200, "H", "T"),   # cozinha -> despensa
    ("J01",   2_400, 14_700, "V", "T"),   # janela oficina (sul)
    ("J01",   2_400, 17_700, "V", "T"),   # janela lavanderia (sul)
    ("J01",   2_400, 21_000, "V", "T"),   # janela cozinha (sul)
    ("J01",   2_400, 23_400, "V", "T"),   # janela cozinha (sul)
    ("J02",   2_400, 25_800, "V", "T"),   # janela despensa (sul)
    # ---- faixa social
    ("P02",   9_000, 13_200, "H", "T"),   # hall -> estar/jantar
    ("P02",   9_600, 16_200, "V", "T"),   # estar -> core/escada
    ("PV01", 12_000, 16_200, "V", "T"),   # core envidracado -> deck norte
    ("P04",   9_600, 20_700, "V", "T"),   # gourmet -> deposito/DML
    ("PV01",  9_600, 24_000, "V", "T"),   # gourmet -> patio norte
    ("PV01",  7_500, 26_400, "H", "T"),   # gourmet -> alpendre e piscina
    # ---- superior
    ("P02",   7_800, 17_400, "V", "S"),   # hall -> suite 02
    ("P02",   7_800, 18_600, "V", "S"),   # hall -> suite 03
    ("P02",   9_000, 19_200, "H", "S"),   # hall -> suite master
    ("J01",   2_400, 15_600, "V", "S"),   # janela suite 02 (sul)
    ("J01",   2_400, 21_000, "V", "S"),   # janela suite 03 (sul)
    ("J02",   3_600, 13_200, "H", "S"),   # janela banho suite 02
    ("J03",  10_800, 24_000, "H", "S"),   # master -> varanda
    ("J01",  13_800, 21_600, "V", "S"),   # janela master (norte)
]

# =========================================================================
# ELEMENTOS EXTERNOS
# =========================================================================
PISCINA = dict(x=5_400, y=28_800, w=4_800, h=2_400,
               prainha_w=1_200, prof_prainha=300, prof_principal=1_150,
               lamina_m2=11.52, volume_m3=10.80)
CASA_MAQUINAS = dict(x=11_400, y=28_800, w=1_500, h=1_200)
DECK = dict(x=4_200, y=28_800, w=7_200, h=4_800)          # envolve a piscina
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


# =========================================================================
# BRISES — sombreamento externo por face
# Em latitude 3 S o sol de leste (8 h) e de oeste (16 h) chega a 30 graus de
# altitude: sombreamento HORIZONTAL nao funciona nessas faces, so VERTICAL.
# Nas faces norte e sul o sol e alto (63 a 87 graus) e o beiral resolve.
# =========================================================================
BRISES = [
    dict(cod="BR-O", face="O", x=5_400, y=28_800, w=4_200, h=150,
         tipo="ripado vertical movel", passo=150,
         desc="face oeste do gourmet - sol das 16h sobre a fita social"),
    dict(cod="BR-L", face="L", x=12_000, y=7_200, w=3_000, h=150,
         tipo="ripado vertical fixo", passo=150,
         desc="quarto reversivel - testada leste"),
    dict(cod="BR-OS", face="O", x=10_200, y=22_800, w=6_000, h=150,
         tipo="ripado vertical movel", passo=150,
         desc="varanda master - pavimento superior"),
]

BEIRAIS = {"N": 1_200, "S": 1_200, "L": 600, "O": 600}

# =========================================================================
# DESEMPENHO — camadas construtivas para calculo de U, R e FSo
# lambda em W/(m.K); espessura em mm. Camada de ar entra como resistencia.
# =========================================================================
CAMADAS = {
    "parede_externa": [
        ("Rse (resistencia superficial externa)", None, 0.040),
        ("Chapa cimenticia", 10, 0.95),
        ("Camara de ar nao ventilada", 40, 0.160),
        ("La mineral", 50, 0.040),
        ("Chapa de gesso acartonado", 12.5, 0.350),
        ("Rsi (resistencia superficial interna)", None, 0.130),
    ],
    "parede_interna": [
        ("Rsi", None, 0.130),
        ("Chapa de gesso acartonado", 12.5, 0.350),
        ("La mineral", 50, 0.040),
        ("Camara de ar", 25, 0.160),
        ("Chapa de gesso acartonado", 12.5, 0.350),
        ("Rsi", None, 0.130),
    ],
    "cobertura": [
        ("Rse", None, 0.040),
        ("Chapa de aco", 0.5, 55.0),
        ("Nucleo PIR", 75, 0.022),
        ("Chapa de aco", 0.5, 55.0),
        ("Rsi (fluxo descendente)", None, 0.170),
    ],
}

ABSORTANCIA = 0.30            # cor clara (alvo: <= 0,40 na ZB8)

# limites normativos — NBR 15220-3, Zona Bioclimatica 8
LIMITES_ZB8 = {
    "parede_externa": dict(U=3.60, atraso=4.3, FSo=4.0, rotulo="parede leve refletora"),
    "cobertura": dict(U=2.30, atraso=3.3, FSo=6.5, rotulo="cobertura leve refletora"),
}

# NBR 15575 — desempenho acustico (residencia unifamiliar)
ACUSTICA = {
    "fachada_dormitorio": dict(minimo=30, intermediario=35, superior=40, unidade="Rw (dB)"),
    "parede_entre_ambientes": dict(minimo=40, intermediario=45, superior=50, unidade="Rw (dB)"),
    "piso_entre_pavimentos": dict(minimo=80, intermediario=66, superior=65, unidade="L'nT,w (dB)"),
}

ESQUADRIA_ACUSTICA = {
    "correr aluminio comum, vidro temperado 8 mm": 25,
    "correr com vedacao por compressao, laminado 6+6": 33,
    "de abrir com vedacao dupla, laminado 6+6 PVB acustico": 38,
}


# =========================================================================
# DECISOES DE INSTALACAO — fechadas com o cliente
# =========================================================================
AQUECIMENTO = dict(
    solucao="chuveiro eletrico individual, 220 V",
    tensao=220, potencia_un=4_500, quantidade=4,
    corrente_un=4_500 / 220,
    secao_mm2=4.0, disjuntor_a=25,
    instalada_w=4 * 4_500,
    fator_demanda=0.75,
    temp_entrada=27.0, temp_banho=38.0, vazao_ls=0.05,
    justificativa=(
        "A agua da rede chega a 27 C em Manaus. Para 3 L/min a 38 C basta "
        "P = m.c.dT = 0,05 x 4186 x 11 = 2,3 kW. Os 6.800 W do briefing "
        "aquecem agua que ja esta quente. Adotado 4.500 W (menor potencia "
        "comercial corrente) em 220 V, que ainda entrega dT de 21 K."),
)

PLUVIAL = dict(
    decisao="REUSO — reservatorio dimensionado pela DEMANDA, nao pela oferta",
    volume_l=2_500,
    precipitacao_mm_ano=2_300,
    coef_escoamento=0.95,
    descarte_inicial=0.10,
    usos=[("Lavagem de deck, calcada e veiculos", 21),
          ("Ducha externa do deck", 90),
          ("Reposicao da piscina por evaporacao", 58),
          ("Irrigacao com paisagismo adaptado", 100)],
    nao_estender_a="vasos sanitarios",
    porque_nao=(
        "Descarga com agua de chuva renderia ~55 m3/ano, mas exige tubulacao "
        "dupla permanentemente identificada, tratamento e bomba. Payback de 15 "
        "a 30 anos e risco permanente de conexao cruzada. A agua em Manaus e "
        "abundante e barata: o item nao se paga nem em dinheiro nem em risco."),
    retencao=(
        "Funcao DIFERENTE e de dimensionamento OPOSTO: reuso quer o reservatorio "
        "cheio, retencao quer vazio antes da chuva. So sera dimensionada se o "
        "Codigo Ambiental de Manaus a exigir — e entao como volume separado, ou "
        "como zona superior do mesmo reservatorio com descarga lenta por orificio."),
)


def balanco_pluvial() -> dict:
    area = sum(a.area_mod for a in cobertos())
    captacao = area * (PLUVIAL["precipitacao_mm_ano"] / 1000) * \
        PLUVIAL["coef_escoamento"] * (1 - PLUVIAL["descarte_inicial"])
    demanda_dia = sum(v for _, v in PLUVIAL["usos"])
    return dict(area=area, captacao_m3=captacao,
                demanda_dia=demanda_dia,
                demanda_ano=demanda_dia * 365 / 1000,
                autonomia_dias=PLUVIAL["volume_l"] / demanda_dia,
                aproveitamento=(demanda_dia * 365 / 1000) / captacao)
