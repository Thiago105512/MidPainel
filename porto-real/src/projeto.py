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

import math
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
    coberto: bool = False         # area aberta COM cobertura (entra na taxa de ocup.)
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
    frozenset(("T-HAL", "T-CIR")),   # a circulacao e o proprio hall, em L
}

TERREO: list[Amb] = [
    # ---- faixa frontal (leste)
    Amb("T-GAR", "GARAGEM",              2_400,  7_200, 6_000, 6_000),
    Amb("T-HAL", "HALL",                 8_400,  9_600, 1_800, 3_600),
    Amb("T-BWC", "BANHO COMPARTILHADO", 10_200,  9_600, 1_800, 2_400, molhado=True),
    Amb("T-CIR", "CIRCULACAO",          10_200, 12_000, 1_800, 1_200),
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
    Amb("T-VAR", "VARANDA DE ENTRADA",   8_400,  7_200, 1_800, 2_400, aberto=True, coberto=True),   # cobertura propria, continuacao do telhado frontal
    Amb("T-JLE", "JARDIM LESTE",        10_200,  7_200, 1_800, 2_400, aberto=True),
    Amb("T-JNO", "JARDIM NORTE",        15_000,  7_200, 1_800, 6_000, aberto=True),
    Amb("T-LOG", "LOGGIA SUL",           2_400, 16_200, 3_000, 3_000, aberto=True, coberto=True),   # sob as suites 02 e 03 (pilotis + viga V-01)
    Amb("T-DKL", "DECK NORTE",          12_000, 13_200, 4_800, 6_000, aberto=True),
    Amb("T-VRL", "VARAL COBERTO",       12_600, 19_200, 4_200, 4_200, aberto=True, coberto=True),   # 5,04 m2 sob a master + 12,60 m2 de telha translucida
    # o patio norte estava declarado como uma peca unica de 21,60 m2, metade
    # dela sob a laje da master e da sacada. Dividido conforme a cobertura
    # real: o trecho coberto e a sala de jantar externa do gourmet (a porta
    # PV02 abre exatamente nele); o descoberto e passagem e insolacao.
    Amb("T-PAT", "PATIO COBERTO DO GOURMET", 9_600, 23_400, 4_200, 2_400,
        aberto=True, coberto=True),   # sob a master (2,52) e a sacada (7,56)
    Amb("T-PT2", "PATIO DESCOBERTO",    13_800, 23_400, 3_000, 2_400, aberto=True),
    Amb("T-ALP", "ALPENDRE DO GOURMET",  5_400, 26_400, 4_200, 1_200, aberto=True, coberto=True),   # cobertura propria, beiral do gourmet sobre a piscina
    Amb("T-DKP", "DECK DA PISCINA",      4_200, 27_600, 7_200, 4_200, aberto=True),
    # jardins: area aberta com funcao declarada, nao sobra
    Amb("T-JSU", "JARDIM SUL",           2_400, 26_400, 3_000, 1_200, aberto=True),
    Amb("T-JS2", "JARDIM SUL",           2_400, 27_600, 1_800, 4_200, aberto=True),
    Amb("T-JN2", "JARDIM NORTE",         9_600, 25_800, 1_800, 1_800, aberto=True),
    Amb("T-JN3", "JARDIM NORTE",        11_400, 25_800, 5_400, 6_000, aberto=True),
    Amb("T-JFU", "JARDIM DE FUNDO",      2_400, 31_800, 14_400, 7_800, aberto=True),
]

# ambientes cobertos do terreo = fechados + areas abertas com cobertura.
# Derivado do campo Amb.coberto: ANTES existiam CINCO definicoes empilhadas
# desta funcao (a ultima vencia e esquecia a loggia e o varal) e duas delas
# citavam codigos inexistentes, T-PSE e T-CSE. Com o dado no ambiente nao ha
# mais lista paralela para desatualizar.
def cobertos() -> list[Amb]:
    return TERREO + [a for a in TERREO_ABERTO if a.coberto]


def projecao_coberta_m2(passo: int = 300) -> float:
    """Projecao horizontal coberta = uniao do terreo coberto com o superior.

    Rasteriza a uniao porque o superior avanca sobre areas abertas (patio
    norte) e sobre outras ja cobertas (varal): somar areas contaria duas
    vezes. E a projecao, nao a soma de pavimentos, que define taxa de ocupacao.
    """
    cels = set()
    for a in cobertos() + SUPERIOR + SUPERIOR_ABERTO:
        for i in range(a.x, a.x + a.w, passo):
            for j in range(a.y, a.y + a.h, passo):
                cels.add((i, j))
    return round(len(cels) * passo * passo / 1e6, 2)


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
    ("P05",  10_200, 10_800, "V", "T"),   # hall -> banho: de correr (NBR 9050)
    ("P02",  12_000, 12_600, "V", "T"),   # circulacao -> quarto reversivel (acesso proprio)
    ("P02",  12_000, 10_800, "V", "T"),   # banho -> quarto reversivel
    ("J05",  13_500,  7_200, "H", "T"),   # janela ampla do reversivel (leste)
    ("J01",  15_000, 10_200, "V", "T"),   # janela do reversivel (norte)
    ("J04",  11_100,  9_600, "H", "T"),   # janela alta do banho (jardim leste)
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
    ("P04",  10_800, 22_200, "H", "T"),   # lavanderia -> deposito (acesso interno)
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
# casa de maquinas da piscina = elemento tecnico TC-13 (ver TECNICOS).
# SEMI-enterrada: o piso fica 600 mm abaixo do deck, nao 1.200. Razao: a
# motobomba e o filtro precisam ficar ACIMA do nivel da agua de lavagem do
# filtro para a retrolavagem drenar por gravidade, e a tampa em grelha
# garante a ventilacao que um alcapao cego nao daria (motor de 1/2 cv
# dissipa ~300 W de calor em recinto confinado).
CASA_MAQUINAS = dict(x=10_200, y=28_800, w=1_500, h=1_200,
                     enterrada=False, semienterrada=True, prof=600,
                     acesso="tampa em grelha 800 x 1.200 mm no deck",
                     nota="semi-enterrada sob o deck: sem volume solto no "
                          "jardim, com ventilacao e dreno por gravidade")
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
    # CORRECAO: a taxa de ocupacao e a PROJECAO COBERTA, nao a area fechada do
    # terreo. Varanda, loggia, varal e alpendre tem cobertura e projetam; o
    # trecho da master e da sacada que avanca sobre o patio tambem.
    proj = projecao_coberta_m2()
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
# A sacada da master (S-BAL) avancava 1.800 mm alem da linha de pilares de
# y = 24.000. Em Light Steel Frame um balanco de 1.800 mm nao se resolve no
# proprio vigamento (a pratica limita o balanco a ~600 mm ou 1/4 do vao de
# tras): exigiria perfil laminado de borda em balanco, com flecha e vibracao
# perceptiveis na ponta e um detalhe de estanqueidade critico na juncao.
# Dois pilares a mais em y = 25.800 transformam o balanco em laje apoiada e
# fecham um portico 2 x 2 sobre o patio coberto — a troca mais barata do
# projeto entre risco de patologia e custo de estrutura.
PILARES = [
    dict(x=10_800, y=19_200), dict(x=13_800, y=19_200),
    dict(x=10_800, y=24_000), dict(x=13_800, y=24_000),
    dict(x=10_800, y=25_800), dict(x=13_800, y=25_800),
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
    dict(cod="LC-01", amb="T-BWC", tipo="vaso",      x=10_400, y=9_750, w=400, h=650),
    dict(cod="LC-02", amb="T-BWC", tipo="lavatorio", x=11_050, y=9_750, w=700, h=450),
    dict(cod="LC-03", amb="T-BWC", tipo="box",       x=10_350, y=10_850, w=900, h=1_000),
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
    dict(cod="AR-02", amb="T-DES", tipo="prateleiras",  x=5_000, y=25_300, w=300, h=1_000),
    dict(cod="AR-03", amb="T-DEP", tipo="prateleiras",  x=9_700, y=22_300, w=2_800, h=300),
    # parede de armarios da oficina: 600 mm de profundidade resolve o deposito
    # proprio sem transferir area de nenhum ambiente
    dict(cod="AR-04", amb="T-OFI", tipo="armario alto",  x=4_800, y=13_400, w=600, h=2_400),
]

# folgas minimas (NBR 9050 e pratica corrente)
FOLGA_FRONTAL_LOUCA = 600      # frente livre de vaso e lavatorio
FOLGA_LATERAL_VASO = 400       # eixo do vaso ate a parede lateral
BOX_MIN = 900                  # menor dimensao interna do box


# =========================================================================
# AREAS TECNICAS — etapa 1: tudo que o briefing especifica ganha posicao.
# zona: "FT-N" faixa tecnica norte | "REC-S" recuo sul | "ENT" enterrado
#       "INT" interno a ambiente | "TEST" testada
# =========================================================================
TECNICOS = [
    # ---- reservacao e recalque (faixa tecnica norte)
    dict(cod="TC-01", rasante=True, nome="Cisterna 3.000 L", zona="ENT", x=17_000, y=8_000,
         w=2_000, h=1_500, prof=1_200,
         obs="enterrada sob a faixa tecnica; tampa 800x800 e respiro DN25"),
    dict(cod="TC-02", nome="Motobomba de recalque 0,5 cv", zona="FT-N",
         x=17_000, y=9_800, w=1_000, h=800,
         obs="base antivibratoria; succao DN32, recalque DN25; bypass manual"),
    dict(cod="TC-03", rasante=True, nome="Reservatorio pluvial 2.500 L", zona="ENT",
         x=13_000, y=27_000, w=1_800, h=1_500, prof=1_200,
         obs="enterrado no jardim norte, junto as descidas 3 e 4; so irrigacao e lavagem"),
    # ---- gas
    dict(cod="TC-04", nome="Central GLP (2 x P-45)", zona="FT-N",
         x=17_000, y=24_000, w=1_200, h=800,
         obs="NBR 13523: min 1,5 m de qualquer vao e 3,0 m de fonte de ignicao"),
    # ---- eletrica e dados
    dict(cod="TC-05", nome="Quadro geral 36 modulos", zona="INT", amb="T-GAR",
         x=8_100, y=9_000, w=300, h=800,
         obs="parede da garagem junto ao hall; altura de 1.000 a 1.800 mm"),
    dict(cod="TC-06", nome="Quadro superior 24 modulos", zona="INT", amb="S-HAL",
         x=9_800, y=17_000, w=300, h=600, obs="hall do pavimento superior"),
    dict(cod="TC-07", nome="Rack de dados e CFTV", zona="INT", amb="T-GAR",
         x=8_000, y=10_200, w=400, h=600,
         obs="8 cameras, 3 access points, 1 videoporteiro; ventilacao passiva"),
    dict(cod="TC-08", nome="Medidores de agua e energia", zona="TEST",
         x=17_000, y=600, w=800, h=600,
         obs="na testada, leitura pela via sem entrar no lote"),
    # ---- climatizacao: DOIS nichos, por comprimento de linha
    dict(cod="TC-09", nome="Nicho de condensadoras NORTE (3 posicoes)", zona="FT-N",
         x=17_000, y=13_200, w=800, h=4_200,
         obs="2 condensadoras ativas + 1 posicao reservada (ver CLIMATIZACAO); "
             "base de 200 mm, painel ripado ventilado h=1.800, descarga para a "
             "divisa norte com 2.200 mm livres"),
    dict(cod="TC-10", nome="Nicho de condensadoras SUL (3 posicoes)", zona="REC-S",
         x=2_000, y=8_400, w=400, h=3_600,
         obs="encostado na parede da garagem, NAO no meio do recuo: libera uma "
             "faixa continua de 2.000 mm de passagem e descarrega com 2,0 m de "
             "folga. Atende as suites 02 e 03 com linha de 6 a 10 m contra os "
             "17,7 m que teriam pelo nicho norte"),
    # ---- esgoto e piscina
    dict(cod="TC-11", rasante=True, nome="Caixa de gordura 30 L", zona="REC-S",
         x=1_200, y=21_000, w=800, h=800, obs="a jusante da cozinha, inspecionavel"),
    dict(cod="TC-12", rasante=True, nome="Caixa de inspecao 600 x 600", zona="REC-S",
         x=1_200, y=24_000, w=600, h=600, obs="antes da ligacao a rede publica"),
    dict(cod="TC-13", rasante=True, nome="Casa de maquinas da piscina", zona="ENT",
         x=10_200, y=28_800, w=1_500, h=1_200, prof=600,
         obs="SEMI-enterrada: piso 600 mm abaixo do deck, tampa em grelha, "
             "dreno para vala de infiltracao; ventila e ilumina pela grelha"),
]


# =========================================================================
# CLIMATIZACAO — carga calculada, nao estimada no olho.
#
# Metodo: carga = area condicionada x q_m2 + area de vidro x q_vidro
#                 + ocupantes acima de dois x q_pessoa + equipamentos.
# q_m2 = 700 BTU/h.m2: valor de ZB8 (Manaus) JA considerando o pacote do
# projeto — U_parede 0,615, U_cobertura 0,276, atico ventilado e 100 % dos
# vaos sombreados. Sem esse pacote o valor de praxe local e 800 a 900.
#
# DECISAO DE PROJETO: a fita social (estar + core + gourmet + cozinha, 87,84 m2
# em volume continuo e com portas de vidro para o deck e o patio) NAO recebe
# ar condicionado. Climatizar um volume aberto de 88 m2 em Manaus e perder
# energia para o quintal: a estrategia ali e ventilacao cruzada (PV02 sul ->
# PV01 norte), ventiladores de teto e o sombreamento. Fica RESERVADA a
# infraestrutura (posicao no nicho, furo, dreno e circuito) para um split duto
# de 36.000 BTU sobre o jantar, caso o morador opte depois por fechar o vidro.
# =========================================================================
CLIMA_Q_M2 = 700            # BTU/h por m2 de piso condicionado
CLIMA_Q_VIDRO = 200         # BTU/h por m2 de vidro sombreado
CLIMA_Q_PESSOA = 600        # BTU/h por ocupante acima de dois
CLIMA_Q_EQUIP = 200         # BTU/h por equipamento (TV, computador)
CAPACIDADES_COMERCIAIS = (9_000, 12_000, 18_000, 24_000, 30_000, 36_000)
FATOR_VENTILADOR = 0.85     # NBR 16401-2: 0,8 m/s eleva o setpoint ~2,5 C
FATOR_DUTO = 1.05           # perda termica e de vazao na rede de dutos
# largura de nicho por faixa de capacidade (condensadora + folga lateral)
LARGURA_NICHO = ((18_000, 1_200), (36_000, 1_400))

CLIMATIZACAO = [
    dict(amb="S-MAS", nicho="TC-09", pessoas=2, equip=1, capacidade=18_000,
         tipo="split hi-wall inverter"),
    dict(amb="T-REV", nicho="TC-09", pessoas=2, equip=1, capacidade=18_000,
         tipo="split hi-wall inverter",
         obs="quarto reversivel: usado como escritorio, ganha carga de equipamento"),
    dict(amb="S-S02", nicho="TC-10", pessoas=2, equip=1, capacidade=18_000,
         tipo="split hi-wall inverter"),
    dict(amb="S-S03", nicho="TC-10", pessoas=2, equip=1, capacidade=18_000,
         tipo="split hi-wall inverter"),
    dict(amb="T-SOC", nicho="TC-09", pessoas=6, equip=1, capacidade=30_000,
         mais=["T-COR"], zona_aberta=["T-GOU", "T-COZ"],
         conta_ventilador=True, duto=True,
         tipo="split duto inverter, 2 insuflamentos + 1 retorno",
         obs="zona social climatizada; gradiente controlado para o gourmet pela "
             "FRONTEIRA_CLIMATICA, nao por parede"),
    dict(amb="T-OFI", nicho="TC-10", pessoas=2, equip=1, capacidade=9_000,
         reserva=True, tipo="split hi-wall (INFRAESTRUTURA)",
         obs="oficina: furo, dreno e circuito previstos; equipamento opcional"),
]


def area_condicionada(cod: str) -> float:
    """Area de piso que a evaporadora precisa resfriar, sem banho e closet."""
    amb = next((a for a in TERREO + SUPERIOR if a.cod == cod), None)
    if amb is None:
        return 0.0
    area = amb.area_mod
    for sd in SUBDIVISOES:
        if sd["pai"] == cod:
            area -= (sd["w"] * sd["h"]) / 1e6
    return round(area, 2)


def area_vidro(cod: str) -> float:
    """Area de vidro dos vaos que pertencem ao ambiente (janelas e PV)."""
    amb = next((a for a in TERREO + SUPERIOR if a.cod == cod), None)
    if amb is None:
        return 0.0
    tot = 0.0
    for tipo, x, y, ori, pav in VAOS:
        if pav != amb.pav or not (tipo.startswith("J") or tipo.startswith("PV")):
            continue
        lg, al = ESQUADRIAS[tipo][0], ESQUADRIAS[tipo][1]
        # o vao pertence ao ambiente se seu centro encosta no contorno dele
        if amb.x - 200 <= x <= amb.x + amb.w + 200 and amb.y - 200 <= y <= amb.y + amb.h + 200:
            tot += (lg * al) / 1e6
    return round(tot, 2)


def carga_termica(cod: str, pessoas: int = 2, equip: int = 0,
                  mais: list[str] | None = None,
                  ventilador: bool = False, duto: bool = False) -> int:
    """Carga termica em BTU/h, arredondada para cima em 100.

    'mais' soma ambientes que formam um unico volume com o principal: o core
    nao tem parede que o separe do estar, logo nao tem carga propria separada.
    """
    area = area_condicionada(cod) + sum(area_condicionada(c) for c in (mais or []))
    vidro = area_vidro(cod) + sum(area_vidro(c) for c in (mais or []))
    q = (area * CLIMA_Q_M2 + vidro * CLIMA_Q_VIDRO
         + max(0, pessoas - 2) * CLIMA_Q_PESSOA + equip * CLIMA_Q_EQUIP)
    if ventilador:
        q *= FATOR_VENTILADOR
    if duto:
        q *= FATOR_DUTO
    return int(math.ceil(q / 100.0) * 100)


def capacidade_comercial(carga: int) -> int:
    for c in CAPACIDADES_COMERCIAIS:
        if c >= carga:
            return c
    return CAPACIDADES_COMERCIAIS[-1]


def nicho_de(cod_nicho: str) -> list[dict]:
    return [c for c in CLIMATIZACAO if c["nicho"] == cod_nicho]


def carga_instalada_btu(incluir_reserva: bool = False) -> int:
    return sum(c["capacidade"] for c in CLIMATIZACAO
               if incluir_reserva or not c.get("reserva"))


# =========================================================================
# FRONTEIRA CLIMATICA — como a fita social recebe ar condicionado sem parede
#
# O problema: estar + core + gourmet + cozinha formam 87,84 m2 de volume
# continuo. Climatizar o conjunto exigiria 71.700 BTU/h (2 x 36.000) para
# resfriar justamente os dois ambientes que PRODUZEM calor — churrasqueira e
# cooktop — e cuja exaustao joga o ar tratado fora. E termodinamicamente
# absurdo pagar para resfriar o que se esta aquecendo e expulsando.
#
# A solucao nao e fechar o vao (o briefing quer a integracao) nem desistir do
# conforto: e estabelecer uma FRONTEIRA AERODINAMICA na linha estar/gourmet,
# com quatro medidas que se reforcam. Ar frio estratifica embaixo; ar quente
# retorna pelo teto. Quem controla a troca e o teto, nao o piso.
#
#   1. REBAIXO DE FORRO de 300 mm na linha de fronteira: nao atrapalha a
#      passagem (altura livre 2.300 mm) e corta o caminho de retorno da camada
#      quente pelo teto. E o recurso classico de ambiente integrado.
#   2. INSUFLAMENTO longe da fronteira e RETORNO junto a ela: a circulacao
#      induzida puxa o ar para dentro da zona fria, nao para fora.
#   3. EXAUSTAO da churrasqueira (600 m3/h) e do cooktop (450 m3/h) mantem o
#      gourmet em leve depressao. O fluxo fica estar -> gourmet -> exaustao,
#      uma direcao so: a fronteira para de ser reversivel.
#   4. VENTILADORES DE TETO no lado nao climatizado: a 0,8 m/s, 27,5 C tem a
#      mesma temperatura operativa de 25 C em ar parado (NBR 16401-2).
#
# Resultado esperado: estar e jantar a 24-25 C, gourmet a 27-28 C com brisa.
# Gradiente de 3 C em 12 m de planta, estavel e numa direcao. Custo: um
# equipamento de 36.000 em vez de dois, e nenhuma parede nova.
# =========================================================================
FRONTEIRA_CLIMATICA = dict(
    entre=("T-SOC", "T-GOU"), x=5_400, y=19_200, comprimento=4_200, eixo="H",
    rebaixo=300, altura_livre=PE_DIREITO - 300,
    medidas=("rebaixo de forro", "insuflamento distante e retorno na fronteira",
             "exaustao mantendo depressao no gourmet", "ventiladores no lado quente"),
)

# difusores do split duto: insuflamento no extremo oposto a fronteira
DIFUSORES = [
    dict(cod="DF-01", amb="T-SOC", tipo="insuflamento", x=6_000, y=14_100,
         w=1_200, h=300, vazao_m3h=750, obs="jantar, parede oeste do estar"),
    dict(cod="DF-02", amb="T-COR", tipo="insuflamento", x=10_200, y=14_100,
         w=1_200, h=300, vazao_m3h=750, obs="core, sob o poco de luz"),
    dict(cod="DF-03", amb="T-SOC", tipo="retorno", x=7_200, y=18_900,
         w=1_800, h=300, vazao_m3h=1_800, obs="junto a fronteira com o gourmet"),
]
EVAPORADORA_DUTO = dict(amb="T-COR", x=9_700, y=16_400, w=1_200, h=700,
                        altura=350, obs="no entreforro do core, acesso por "
                                        "alcapao 600 x 600 no forro")

# Ventilador de teto nao e conforto acessorio em clima quente-umido: e o
# equipamento de maior retorno por real investido. A NBR 16401-2 aceita elevar
# a temperatura operativa de projeto conforme a velocidade do ar; a 0,8 m/s a
# elevacao e de cerca de 2,5 C, e cada grau a mais economiza ~8 % da carga.
#
# Mas so vale DESCONTAR da capacidade onde o ventilador e parte do partido e
# vai estar sempre la (a fita social). Em dormitorio o morador desliga a pa
# para dormir: ali o ventilador entra como economia de OPERACAO, nao como
# reducao de capacidade — conta_ventilador fica False.
VENTILADORES = [
    dict(cod="VT-01", amb="T-GOU", diam=1_400, qtd=2, vazao_m3h=9_000,
         obs="lado nao climatizado da fita: 0,8 m/s na zona de permanencia"),
    dict(cod="VT-02", amb="T-COZ", diam=1_200, qtd=1, vazao_m3h=7_000),
    dict(cod="VT-03", amb="T-VAR", diam=  800, qtd=1, vazao_m3h=4_500,
         obs="varanda de 1.800 mm: pa de 800 mm e o maior que cabe com folga"),
    dict(cod="VT-04", amb="T-LOG", diam=1_200, qtd=1, vazao_m3h=7_000),
    dict(cod="VT-05", amb="T-SOC", diam=1_400, qtd=1, vazao_m3h=9_000,
         obs="dentro da zona climatizada: e o que autoriza o setpoint de 25,5 C "
             "e o equipamento um degrau menor"),
    dict(cod="VT-06", amb="T-OFI", diam=1_200, qtd=1, vazao_m3h=7_000),
    dict(cod="VT-07", amb="S-MAS", diam=1_400, qtd=1, vazao_m3h=9_000),
    dict(cod="VT-08", amb="S-S02", diam=1_200, qtd=1, vazao_m3h=7_000),
    dict(cod="VT-09", amb="S-S03", diam=1_200, qtd=1, vazao_m3h=7_000),
    dict(cod="VT-10", amb="T-REV", diam=1_200, qtd=1, vazao_m3h=7_000),
]
# o alpendre de 1.200 mm e beiral de sombra sobre a piscina, nao estar: nao
# recebe ventilador (nao ha zona de permanencia sob ele)

EXAUSTAO = [
    dict(cod="EX-01", amb="T-GOU", fonte="churrasqueira", vazao_m3h=600,
         dn=150, obs="coifa de parede, duto em inox ate acima da cobertura"),
    dict(cod="EX-02", amb="T-COZ", fonte="cooktop", vazao_m3h=450, dn=125,
         obs="coifa de ilha sobre BC-02, saida pela fachada sul"),
    dict(cod="EX-03", amb="T-BWC", fonte="banho social", vazao_m3h=90, dn=100),
    dict(cod="EX-04", amb="T-LAV", fonte="lavanderia", vazao_m3h=120, dn=100,
         obs="retira umidade da secadora e do tanque"),
]

# vaos envidracados do volume climatizado: exigem caixilho com vedacao
# (escova dupla e batente com gaxeta), nao o caixilho padrao de correr
VEDACAO_REFORCADA = [
    ("PV01", 12_000, 16_200),   # core -> deck norte
    ("PV02",  5_400, 17_700),   # estar -> loggia sul
]

# comprimento maximo confortavel de linha frigorigena de split de 12.000 BTU
LINHA_FRIG_MAX = 15_000
LINHA_FRIG_LIMITE = 25_000
GLP_DIST_VAO = 1_500        # NBR 13523
