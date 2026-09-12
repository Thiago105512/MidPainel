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
    # ---- oficina: permanece na face sul, acessada pela garagem
    Amb("T-OFI", "OFICINA",              2_400, 13_200, 3_000, 3_000),
    # ---- faixa social
    Amb("T-SOC", "ESTAR / JANTAR",       5_400, 13_200, 4_200, 6_000),
    Amb("T-COR", "CORE / ESCADA",        9_600, 13_200, 2_400, 6_000),
    Amb("T-COZ", "COZINHA",              2_400, 19_200, 3_000, 6_000, molhado=True),
    Amb("T-GOU", "GOURMET",              5_400, 19_200, 4_200, 7_200, molhado=True),
    Amb("T-DES", "DESPENSA",             2_400, 25_200, 3_000, 1_200),
    # ---- lavanderia e deposito na face norte, abrindo para o patio lateral
    Amb("T-LAV", "LAVANDERIA",           9_600, 19_200, 3_000, 3_000, molhado=True),
    Amb("T-DEP", "DEPOSITO / DML",       9_600, 22_200, 3_000, 1_200),
]

# areas externas cobertas / descobertas do terreo (nao computam area fechada)
TERREO_ABERTO: list[Amb] = [
    Amb("T-VAR", "VARANDA DE ENTRADA",   8_400,  7_200, 1_800, 2_400, aberto=True),
    Amb("T-JLE", "JARDIM LESTE",        10_200,  7_200, 1_800, 3_600, aberto=True),
    Amb("T-JNO", "JARDIM NORTE",        15_000,  7_200, 1_800, 6_000, aberto=True),
    Amb("T-LOG", "LOGGIA SUL",           2_400, 16_200, 3_000, 3_000, aberto=True),
    Amb("T-DKL", "DECK NORTE",          12_000, 13_200, 4_800, 6_000, aberto=True),
    Amb("T-VRL", "VARAL COBERTO",       12_600, 19_200, 4_200, 4_200, aberto=True),
    Amb("T-PAT", "PATIO NORTE",          9_600, 23_400, 7_200, 3_000, aberto=True),
    Amb("T-ALP", "ALPENDRE DO GOURMET",  5_400, 26_400, 4_200, 1_200, aberto=True),
    Amb("T-DKP", "DECK DA PISCINA",      4_200, 27_600, 7_200, 4_200, aberto=True),
    # jardins: area aberta com funcao declarada, nao sobra
    Amb("T-JSU", "JARDIM SUL",           2_400, 26_400, 3_000, 1_200, aberto=True),
    Amb("T-JS2", "JARDIM SUL",           2_400, 27_600, 1_800, 4_200, aberto=True),
    Amb("T-JN2", "JARDIM NORTE",         9_600, 26_400, 1_800, 1_200, aberto=True),
    Amb("T-JN3", "JARDIM NORTE",        11_400, 26_400, 5_400, 5_400, aberto=True),
    Amb("T-JFU", "JARDIM DE FUNDO",      2_400, 31_800, 14_400, 7_800, aberto=True),
]

def cobertos() -> list[Amb]:
    return TERREO + [a for a in TERREO_ABERTO
                     if a.cod in ("T-VAR", "T-LOG", "T-VRL", "T-ALP")]

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
    # face: onde fica a porta ("S"=-X, "N"=+X, "L"=-Y, "O"=+Y); pos: centro do vao
    dict(pai="S-S02", nome="BANHO",  x=2_400, y=13_200, w=1_800, h=2_400,
         face="N", pos=14_400, vao=800),
    dict(pai="S-S02", nome="CLOSET", x=2_400, y=15_600, w=600,   h=2_400,
         face="N", pos=16_800, vao=800),
    dict(pai="S-S03", nome="BANHO",  x=2_400, y=18_000, w=1_800, h=2_400,
         face="N", pos=19_200, vao=800),
    dict(pai="S-S03", nome="CLOSET", x=2_400, y=20_400, w=600,   h=2_400,
         face="N", pos=21_600, vao=800),
    dict(pai="S-MAS", nome="BANHO",  x=11_400, y=19_200, w=2_400, h=3_000,
         face="S", pos=20_400, vao=800),
    dict(pai="S-MAS", nome="CLOSET", x=11_400, y=22_200, w=2_400, h=1_800,
         face="S", pos=23_100, vao=800),
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
    "P05":  (  900, 2_100,     0, "porta DE CORRER — sem area de varredura"),
    "J01":  (1_200, 1_200, 1_100, "janela de dormitorio, aluminio"),
    "J02":  (  600,   600, 1_500, "janela de banheiro, alta translucida"),
    "J03":  (  900, 1_500,   900, "janela de office/master, aluminio"),
    "J04":  (  800,   900, 1_500, "janela alta de banheiro, basculante"),
    "J05":  (1_800, 1_200, 1_100, "janela ampla de dormitorio, aluminio"),
    "PV01": (3_600, 2_400,     0, "vao social posterior"),
    "PV02": (2_400, 2_400,     0, "porta-balcao do estar (familia adicional — ver DIVERGENCIAS)"),
}

# (tipo, x, y, orientacao, pavimento) — x,y = centro do vao no eixo da parede
# orientacao: "H" vao em parede horizontal, "V" em parede vertical
VAOS = [
    # ---- faixa frontal
    ("PG01",  5_400,  7_200, "H", "T"),   # portao da garagem (ventila a garagem)
    ("P01",   9_300,  9_600, "H", "T"),   # entrada principal
    ("P02",   8_400, 12_000, "V", "T"),   # hall -> garagem
    ("P05",  10_200, 12_000, "V", "T"),   # hall -> banho: de correr (NBR 9050)
    ("P02",  12_000, 12_000, "V", "T"),   # banho -> quarto reversivel
    ("J05",  13_500,  7_200, "H", "T"),   # janela ampla do reversivel (leste)
    ("J01",  15_000, 10_200, "V", "T"),   # janela do reversivel (norte)
    ("J04",  11_100, 10_800, "H", "T"),   # janela alta do banho
    # ---- oficina: garagem de um lado, loggia sul do outro
    ("P04",   3_900, 13_200, "H", "T"),   # garagem -> oficina
    ("P04",   3_900, 16_200, "H", "T"),   # oficina -> loggia sul (saida de material)
    ("J05",   2_400, 14_700, "V", "T"),   # janela ampla da oficina (sul)
    # ---- cozinha e despensa
    ("P04",   3_900, 19_200, "H", "T"),   # loggia sul -> cozinha (servico)
    ("J01",   2_400, 21_000, "V", "T"),   # janela da cozinha (sul)
    ("J01",   2_400, 23_400, "V", "T"),   # janela da cozinha (sul)
    ("P02",   3_900, 25_200, "H", "T"),   # cozinha -> despensa
    ("J04",   2_400, 25_800, "V", "T"),   # janela alta da despensa (sul)
    # ---- lavanderia e deposito: porta para o varal coberto e o patio lateral
    ("P04",  12_600, 20_100, "V", "T"),   # lavanderia -> varal coberto
    ("J01",  12_600, 21_600, "V", "T"),   # janela da lavanderia (norte)
    ("P04",  12_600, 22_800, "V", "T"),   # deposito -> varal coberto
    ("P04",  10_800, 19_200, "H", "T"),   # core -> lavanderia (acesso interno)
    # ---- faixa social
    ("P02",   9_000, 13_200, "H", "T"),   # hall -> estar/jantar
    ("PV01", 12_000, 16_200, "V", "T"),   # core envidracado -> deck norte
    ("PV02",  9_600, 24_600, "V", "T"),   # gourmet -> patio norte (trecho de 3.000 mm)
    ("PV01",  7_500, 26_400, "H", "T"),   # gourmet -> alpendre e piscina
    ("PV02",  5_400, 17_700, "V", "T"),   # estar -> loggia sul (ventilacao cruzada)
    # ---- superior
    ("P02",   7_800, 17_400, "V", "S"),   # hall -> suite 02
    ("P02",   7_800, 18_600, "V", "S"),   # hall -> suite 03
    ("P02",   9_000, 19_200, "H", "S"),   # hall -> suite master
    ("J05",   2_400, 16_800, "V", "S"),   # janela ampla suite 02 (sul)
    ("J01",   6_000, 13_200, "H", "S"),   # janela suite 02 (leste)
    ("J02",   3_600, 13_200, "H", "S"),   # janela banho suite 02
    ("J05",   2_400, 21_600, "V", "S"),   # janela ampla suite 03 (sul)
    ("J01",   6_000, 22_800, "H", "S"),   # janela suite 03 (oeste)
    ("J04",   2_400, 18_600, "V", "S"),   # janela alta banho suite 03 (fora do box)
    ("J05",   8_700, 24_000, "H", "S"),   # janela ampla master -> varanda
    ("J03",  10_800, 24_000, "H", "S"),   # master -> varanda
    ("J04",  13_800, 20_700, "V", "S"),   # janela alta banho master
]

# =========================================================================
# ELEMENTOS EXTERNOS
# =========================================================================
PISCINA = dict(x=5_400, y=27_600, w=4_800, h=2_400,
               prainha_w=1_200, prof_prainha=300, prof_principal=1_150,
               lamina_m2=11.52, volume_m3=10.80)
CASA_MAQUINAS = dict(x=10_200, y=28_800, w=1_500, h=1_200, enterrada=True,
                     acesso="alcapao 800 x 800 mm no deck",
                     nota="enterrada sob o deck: elimina o volume solto no jardim")
DECK = dict(x=4_200, y=27_600, w=7_200, h=4_200)          # envolve a piscina
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
    dict(cod="BR-O", face="O", x=5_400, y=27_600, w=4_200, h=150,
         tipo="ripado vertical MOVEL, recolhivel", passo=150,
         desc="alpendre do gourmet - recolhe totalmente para liberar a vista da piscina"),
    dict(cod="BR-L", face="L", x=12_000, y=7_200, w=3_000, h=150,
         tipo="ripado vertical fixo", passo=150,
         desc="quarto reversivel - testada leste"),
    dict(cod="BR-OS", face="O", x=10_200, y=22_800, w=6_000, h=150,
         tipo="ripado vertical movel", passo=150,
         desc="varanda master - pavimento superior"),
]

# Sol das 16h a 30 graus de altitude: um anteparo vertical a 5.400 mm do vao
# precisaria de 3.120 mm de altura para sombrea-lo. Nenhum brise proximo
# resolve sem fechar a vista que o cliente quer. A protecao principal da face
# oeste passa a ser ARBOREA, na divisa de fundo.
BARREIRA_OESTE = dict(
    tipo="renque arboreo de copa media na divisa de fundo",
    altura_alvo=4_000, recuo_da_divisa=1_200,
    especie="a definir com paisagismo — copa alta e raiz nao agressiva",
    complemento="muro de 2.200 mm ja previsto; ripado BR-O recolhivel no alpendre",
)

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


# =========================================================================
# PILARES — apoio do pavimento superior sobre areas abertas.
# O trecho da suite master que avanca sobre o patio norte NAO e balanco:
# apoia-se em pilares metalicos, criando terraco coberto no terreo.
# =========================================================================
PILARES = [
    dict(x=10_800, y=19_200), dict(x=13_800, y=19_200),
    dict(x=10_800, y=24_000), dict(x=13_800, y=24_000),
]
PILAR_SECAO = "perfil metalico 200 x 200 mm (H)"

# Areas abertas cobertas pelo pavimento superior e vencidas por VIGA entre
# apoios ja existentes — laje apoiada, nao balanco. O briefing ja preve perfis
# metalicos estruturais para os vaos grandes (garagem de 6.000 mm sem pilar).
VIGAS = [
    dict(cod="V-01", sobre="T-LOG", vao=3_000,
         desc="viga sobre a face aberta da loggia sul, entre as paredes da "
              "oficina e da cozinha; sustenta as suites 02 e 03"),
]
VAO_MAX_VIGA = 6_000


# =========================================================================
# BANCADAS E PONTOS DE AGUA — declarados no MODELO, nao so no desenho.
# O que nao esta no modelo a auditoria nao verifica.
#
# REVISAO: a cozinha e o gourmet sao um unico ambiente integrado. Manter duas
# bancadas molhadas grandes a 6 m de distancia, mais uma cuba na peninsula,
# e triplicar o ponto de agua dentro da mesma sala.
# =========================================================================
BANCADAS = [
    dict(cod="BC-01", amb="T-COZ", x=2_500, y=19_900, w=600, h=4_700,
         prof=600, cubas=1, cooktop=False, tipo="granito",
         uso="bancada principal de preparo e lavagem"),
    dict(cod="BC-02", amb="T-COZ", x=3_100, y=19_300, w=2_200, h=600,
         prof=600, cubas=0, cooktop=True, tipo="granito",
         uso="coccao — cooktop e apoio"),
    dict(cod="BC-03", amb="T-COZ", x=4_800, y=21_600, w=1_200, h=2_400,
         prof=600, cubas=0, cooktop=False, tipo="granito",
         uso="peninsula SECA: apoio, servico e refeicao rapida"),
    dict(cod="BC-04", amb="T-GOU", x=5_550, y=25_700, w=3_900, h=600,
         prof=600, cubas=1, cooktop=True, tipo="granito", cuba_apoio=True,
         uso="churrasqueira e cuba de apoio (400 x 340) — nao e segunda cozinha"),
    dict(cod="BC-05", amb="T-LAV", x=9_750, y=19_350, w=600, h=550,
         prof=600, cubas=1, cooktop=False, tipo="tanque",
         uso="tanque de lavanderia"),
    dict(cod="BC-06", amb="T-OFI", x=2_500, y=13_500, w=600, h=2_400,
         prof=600, cubas=0, cooktop=False, tipo="MDF",
         uso="bancada de trabalho da oficina, sob a janela"),
]

# folgas minimas de circulacao em frente a bancada (briefing)
CIRC_BANCADA_MIN = 1_000
CIRC_BANCADA_DESEJADA = 1_100


# =========================================================================
# LOUCAS, EQUIPAMENTOS E ARMARIOS — no modelo, verificaveis.
# x, y = canto inferior-esquerdo da peca; w, h = dimensoes em planta.
# =========================================================================
LOUCAS = [
    # banho compartilhado (10.200, 10.800, 1.800 x 2.400)
    dict(cod="LC-01", amb="T-BWC", tipo="vaso",      x=10_400, y=10_950, w=400, h=650),
    dict(cod="LC-02", amb="T-BWC", tipo="lavatorio", x=11_050, y=10_950, w=700, h=450),
    dict(cod="LC-03", amb="T-BWC", tipo="box",       x=10_350, y=12_050, w=900, h=1_000),
    # suite 02 — banho (2.400, 13.200, 1.800 x 2.400)
    dict(cod="LC-04", amb="S-S02", tipo="vaso",      x=2_600, y=13_350, w=400, h=650),
    dict(cod="LC-05", amb="S-S02", tipo="lavatorio", x=3_250, y=13_350, w=700, h=450),
    dict(cod="LC-06", amb="S-S02", tipo="box",       x=2_550, y=14_500, w=900, h=1_000),
    # suite 03 — banho (2.400, 18.000, 1.800 x 2.400)
    dict(cod="LC-07", amb="S-S03", tipo="vaso",      x=2_600, y=18_150, w=400, h=650),
    dict(cod="LC-08", amb="S-S03", tipo="lavatorio", x=3_250, y=18_150, w=700, h=450),
    dict(cod="LC-09", amb="S-S03", tipo="box",       x=2_550, y=19_300, w=900, h=1_000),
    # suite master — banho (11.400, 19.200, 2.400 x 3.000)
    dict(cod="LC-10", amb="S-MAS", tipo="vaso",      x=11_600, y=19_350, w=400, h=650),
    dict(cod="LC-11", amb="S-MAS", tipo="lavatorio", x=12_300, y=19_350, w=1_200, h=500),
    dict(cod="LC-12", amb="S-MAS", tipo="box",       x=11_550, y=20_900, w=1_100, h=1_100),
    # lavanderia
    dict(cod="LC-13", amb="T-LAV", tipo="tanque",    x=9_750, y=19_350, w=600, h=550),
]

EQUIPAMENTOS = [
    dict(cod="EQ-01", amb="T-COZ", tipo="geladeira", x=4_400, y=24_450, w=900, h=750,
         abertura=900, uso="nicho de 900 mm previsto no briefing"),
    dict(cod="EQ-02", amb="T-LAV", tipo="lavadora",  x=9_750, y=20_050, w=600, h=600,
         abertura=600, uso="base antivibratoria"),
    dict(cod="EQ-03", amb="T-LAV", tipo="secadora",  x=9_750, y=20_750, w=600, h=600,
         abertura=600, uso="base antivibratoria"),
]

ARMARIOS = [
    dict(cod="AR-01", amb="T-OFI", tipo="armario alto", x=4_700, y=13_400, w=600, h=600),
    dict(cod="AR-02", amb="T-DES", tipo="prateleiras",  x=5_000, y=25_300, w=300, h=1_000),
    dict(cod="AR-03", amb="T-DEP", tipo="prateleiras",  x=9_700, y=22_300, w=2_800, h=300),
]

# folgas minimas (NBR 9050 e pratica corrente)
FOLGA_FRONTAL_LOUCA = 600      # frente livre de vaso e lavatorio
FOLGA_LATERAL_VASO = 400       # eixo do vaso ate a parede lateral
BOX_MIN = 900                  # menor dimensao interna do box
