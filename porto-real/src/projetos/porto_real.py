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

import nucleo.cadastro as cd

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
    Amb("T-COZ", "COZINHA",              2_400, 19_200, 3_000, 7_200, molhado=True),
    Amb("T-GOU", "GOURMET",              5_400, 19_200, 4_200, 7_200, molhado=True),
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
    Amb("T-DKL", "DECK NORTE",          12_000, 13_200, 4_800, 3_600, aberto=True),
    # a laje do mini lounge avanca 600 mm para oeste e 1.200 para leste como
    # beiral, cobrindo a faixa inteira do deck: a porta PV01 do core passa a
    # desembocar em area coberta
    Amb("T-DKC", "DECK NORTE COBERTO",  12_000, 16_800, 4_800, 2_400,
        aberto=True, coberto=True),
    Amb("T-VRL", "VARAL COBERTO",       12_600, 19_200, 4_200, 4_200, aberto=True, coberto=True),   # 5,04 m2 sob a master + 12,60 m2 de telha translucida
    # o patio norte estava declarado como uma peca unica de 21,60 m2, metade
    # dela sob a laje da master e da sacada. Dividido conforme a cobertura
    # real: o trecho coberto e a sala de jantar externa do gourmet (a porta
    # PV02 abre exatamente nele); o descoberto e passagem e insolacao.
    Amb("T-PAT", "PATIO COBERTO DO GOURMET", 9_600, 23_400, 6_000, 3_600,
        aberto=True, coberto=True),   # todo sob a master e a varanda
    Amb("T-PT2", "PATIO DESCOBERTO",    15_600, 23_400, 1_200, 3_600, aberto=True),
    # R07 — de 4,20 x 1,20 (pingadeira) para 7,20 x 3,00: a varanda passa a
    # cobrir a largura INTEIRA de cozinha + gourmet e a ter profundidade de
    # permanencia. Com 1.200 mm nao se usa o espaco durante chuva, que era
    # justamente o objetivo declarado no briefing.
    Amb("T-ALP", "VARANDA GOURMET",      2_400, 26_400, 7_200, 3_000,
        aberto=True, coberto=True),
    Amb("T-DKP", "DECK DA PISCINA",      3_600, 29_400, 7_800, 5_400, aberto=True),
    # jardins: area aberta com funcao declarada, nao sobra
    Amb("T-JS2", "JARDIM SUL",           2_400, 29_400, 1_200, 5_400, aberto=True),
    Amb("T-JN2", "JARDIM NORTE",         9_600, 27_000, 1_800, 2_400, aberto=True),
    Amb("T-JN3", "JARDIM NORTE",        11_400, 27_000, 5_400, 7_800, aberto=True),
    Amb("T-JFU", "JARDIM DE FUNDO",      2_400, 34_800, 14_400, 4_800, aberto=True),
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
    # R06 — programa ampliado pelo YAML MASTER do proprietario (revisao 19 de
    # docs/DIVERGENCIAS.md). As suites 02 e 03 permanecem INTOCADAS como modulo
    # espelhado de 5.400 x 4.800; entram o mini lounge e a master
    # redimensionada de 28,80 para 46,80 m2.
    Amb("S-S02", "SUITE 02",          2_400, 13_200, 5_400, 4_800, pav="S"),
    Amb("S-S03", "SUITE 03",          2_400, 18_000, 5_400, 4_800, pav="S"),
    # o hall deixa de ser corredor: e chegada da escada, distribuicao para
    # quatro destinos e rouparia embutida
    # R46 — o hall vai ate 12.600, e nao ate 12.000. Entre ele e o mini lounge
    # havia uma faixa de 600 x 2.400 mm que nao pertencia a ambiente nenhum: o
    # painelizador via duas faces contra o exterior e erguia DUAS paredes
    # externas de 150 mm paralelas, com 600 mm de vazio entre elas, e a porta
    # do lounge abria para dentro desse poco. O lounge era o unico dos 17
    # comodos INACESSIVEL a partir da porta de entrada, e 517 verificacoes nao
    # perguntavam isso porque nenhuma delas caminhava pela casa.
    #
    # Estender o hall e a correcao mais barata das tres: REMOVE uma parede
    # externa em vez de acrescentar, nao mexe em fachada (mover o lounge 600 mm
    # deslocaria a janela leste) e devolve ao hall a funcao que o proprio
    # projeto lhe deu em R06 — "distribuicao para quatro destinos", que ate
    # aqui eram tres.
    Amb("S-HAL", "HALL E ROUPARIA",   7_800, 16_800, 4_800, 2_400, pav="S"),
    # mini lounge com 3.000 mm de profundidade porque e o que o televisor
    # exige. Com os 2.600 mm do YAML a distancia de visao cairia para 1,20 m.
    Amb("S-LOU", "MINI LOUNGE / TV", 12_600, 16_800, 3_000, 2_400, pav="S"),
    Amb("S-MAS", "SUITE MASTER",      7_800, 19_200, 7_800, 6_000, pav="S"),
]

SUPERIOR_ABERTO: list[Amb] = [
    Amb("S-BAL", "VARANDA MASTER",  7_800, 25_200, 7_800, 1_800,
        pav="S", nivel=NIVEL_SUPERIOR, aberto=True),   # 14,04 m2 (YAML)
]

# ---------------------------------------------------- conjugados (R44)
# A cozinha e o gourmet sao UM ambiente: 6.600 dos 7.200 mm de fronteira estao
# abertos, e a decisao esta escrita desde R07. Mas estava escrita em COMENTARIO
# — "iluminacao e ventilacao conferidas em conjunto com o gourmet, que e o
# mesmo ambiente" — e comentario nao e consultavel.
#
# A consequencia apareceu na primeira conferencia por comodo: a cozinha reprovou
# em iluminacao natural (1/15 contra 1/8) porque a conferencia enxergava dois
# retangulos onde o projeto ve um. O defeito nao era do projeto nem da regra: a
# decisao existia e nao era dado.
CONJUGADOS = [("T-COZ", "T-GOU")]


def conjugado_de(cod: str) -> tuple:
    """O grupo de ambientes que se conferem juntos, este inclusive."""
    for g in CONJUGADOS:
        if cod in g:
            return g
    return (cod,)


# ------------------------------------------- subdivisoes internas (1:50)
# (cod_pai, nome, x, y, w, h) — particoes dentro do modulo
SUBDIVISOES = [
    # face: onde fica a porta ("S"=-X, "N"=+X, "L"=-Y, "O"=+Y); pos: centro do vao
    # R39 — `molhado` na subdivisao. O flag existia so no ambiente inteiro, e
    # a suite e um retangulo unico: por isso o modelo "nao tinha" banheiro no
    # superior. A geometria do banho SEMPRE esteve aqui, exata; faltava o
    # flag, e quem o le. Nenhuma area foi arbitrada.
    dict(pai="S-S02", nome="BANHO",  x=2_400, y=13_200, w=1_800, h=2_400,
         face="N", pos=14_400, vao=800, molhado=True),
    dict(pai="S-S02", nome="CLOSET", x=2_400, y=15_600, w=600,   h=2_400,
         face="N", pos=16_800, vao=800),
    dict(pai="S-S03", nome="BANHO",  x=2_400, y=18_000, w=1_800, h=2_400,
         face="N", pos=19_200, vao=800, molhado=True),
    dict(pai="S-S03", nome="CLOSET", x=2_400, y=20_400, w=600,   h=2_400,
         face="N", pos=21_600, vao=800),
    # ---- R08: a despensa volta, mas na PONTA DE SERVICO da cozinha, nao
    # atravessada entre ela e a piscina. Ganha a melhor adjacencia possivel: a
    # porta de servico da loggia abre DENTRO dela, e a compra desce do carro
    # para a prateleira sem atravessar a cozinha. 3,78 m2 contra os 3,60 m2 da
    # despensa antiga, com prateleira nos dois lados e 1.200 mm de circulacao.
    dict(pai="T-COZ", nome="DESPENSA", x=2_400, y=19_200, w=1_800, h=2_100,
         face="O", pos=3_300, vao=800),
    # ---- master R06. O corredor de entrada de 1.200 mm (x 7.800 a 9.000) e a
    # unica circulacao exclusiva da suite: 3,60 m2 em 46,80, ou 7,7 %.
    # R09 — banho e closet TROCARAM de lugar. O banho estava sobre o varal
    # coberto, ou seja, sobre area aberta: a prumada de esgoto descia onde nao ha
    # parede para embuti-la. Agora o banho cai sobre a LAVANDERIA — molhado sobre
    # molhado, prumada de 3 m em vez de desvio horizontal em forro.
    dict(pai="S-MAS", nome="BANHO",  x=9_000,  y=19_200, w=3_000, h=3_000,
         face="O", pos=9_600, vao=800, molhado=True),
    dict(pai="S-MAS", nome="CLOSET", x=12_000, y=19_200, w=3_600, h=3_000,
         face="O", pos=12_900, vao=800),
    dict(pai="S-MAS", nome="OFFICE", x=13_800, y=22_200, w=1_800, h=3_000,
         face="S", pos=23_700, vao=800),
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
    # J02 ficou SEM USO em R47, quando o banho da suite 02 passou a J04 para
    # espelhar a 03. Mantida no catalogo e marcada: familia sem vao e a que
    # aparece no orcamento do fornecedor e nao aparece na obra.
    "J02":  (  600,   600, 1_500, "janela de banheiro, alta translucida "
                                  "(SEM USO desde R47)"),
    # J03 nunca teve vao: o office da master recebeu J01 (1.200 x 1.200 =
    # 1,44 m2), que e exatamente o vidro_m2 que a carga termica do office
    # declara. A familia ficou no catalogo sem nunca chegar ao desenho.
    "J03":  (  900, 1_500,   900, "janela de office/master, aluminio "
                                  "(SEM USO: o office leva J01)"),
    "J04":  (  800,   900, 1_500, "janela alta de banheiro, basculante"),
    "J05":  (1_800, 1_200, 1_100, "janela ampla de dormitorio, aluminio"),
    "PV01": (3_600, 2_400,     0, "vao social posterior"),
    "PV02": (2_400, 2_400,     0, "porta-balcao do estar (familia adicional — ver DIVERGENCIAS)"),
    # R07 — familia nova, e a unica que o projeto ganha desde o inicio. Nao e
    # porta de correr: e cortina de vidro, folhas soltas que correm no trilho e
    # giram 90 graus para estacionar em nicho lateral. O ganho e conceitual, nao
    # de conforto: quando aberta, NAO SOBRA MONTANTE NENHUM no meio da vista.
    "CV01": (7_200, 2_600,     0, "CORTINA DE VIDRO retratil, 8 folhas de 900 mm "
                                  "de vidro temperado 10 mm, sem montante vertical"),
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
    ("P04",   3_300, 19_200, "H", "T"),   # loggia sul -> DESPENSA (servico)
    ("J01",   2_400, 24_000, "V", "T"),   # janela da cozinha, sobre a cuba (sul)
    # R07 — a segunda janela sul da cozinha saiu: com 7,20 m de cortina de vidro
    # a tres metros, a parede vale mais como armario do que como vao. Iluminacao
    # e ventilacao conferidas em conjunto com o gourmet, que e o mesmo ambiente.
    # ---- lavanderia e deposito: porta para o varal coberto e o patio lateral
    ("P04",  12_600, 20_100, "V", "T"),   # lavanderia -> varal coberto
    ("J01",  12_600, 21_600, "V", "T"),   # janela da lavanderia (norte)
    ("P04",  12_600, 22_800, "V", "T"),   # deposito -> varal coberto
    ("P04",  10_800, 22_200, "H", "T"),   # lavanderia -> deposito (acesso interno)
    # R45 — o DML tinha 3,6 m2 e NENHUM vao externo, e a conferencia por comodo
    # achou. A solucao mais barata era tambem a melhor: a face norte (y=23.400)
    # e externa e estava livre. Basculante alta de 800 x 900 com peitoril 1.500
    # da 0,72 m2 contra os 0,45 que 1/8 de 3,6 exige, e ventila SEM tomar a
    # parede da prateleira — que e para o que um DML serve. Descartadas:
    # veneziana na porta (ventila e nao ilumina) e exaustor mecanico (custa
    # energia e manutencao para sempre, num comodo que tem fachada livre).
    ("J04",  11_100, 23_400, "H", "T"),   # DML: ventilacao e luz altas (norte)
    ("P04",  10_800, 19_200, "H", "T"),   # core -> lavanderia (acesso interno)
    # ---- faixa social
    ("P02",   9_000, 13_200, "H", "T"),   # hall -> estar/jantar
    ("PV01", 12_000, 16_200, "V", "T"),   # core envidracado -> deck norte
    ("PV02",  9_600, 24_600, "V", "T"),   # gourmet -> patio norte (trecho de 3.000 mm)
    # R07 — a abertura deixa de ser uma porta de 3.600 no meio de uma parede de
    # 4.200 e passa a ser a PAREDE INTEIRA: 7.200 mm de cortina de vidro
    # cobrindo cozinha e gourmet de uma vez, sem montante no meio da vista.
    ("CV01",  6_000, 26_400, "H", "T"),   # cozinha + gourmet -> varanda e piscina
    ("PV02",  5_400, 17_700, "V", "T"),   # estar -> loggia sul (ventilacao cruzada)
    # ---- superior (R06)
    ("P02",   7_800, 17_400, "V", "S"),   # hall -> suite 02
    ("P02",   7_800, 18_600, "V", "S"),   # hall -> suite 03
    ("P02",   8_400, 19_200, "H", "S"),   # hall -> master (corredor de entrada)
    ("P02",  12_600, 17_250, "V", "S"),   # hall -> mini lounge (na ponta da
                                          # parede, liberando 1.500 mm para o
                                          # painel de TV no restante dela)
    ("J01",  15_600, 18_000, "V", "S"),   # janela do lounge (norte), atras do sofa
    ("J05",   2_400, 16_800, "V", "S"),   # janela ampla suite 02 (sul)
    ("J01",   6_000, 13_200, "H", "S"),   # janela suite 02 (leste)
    # R47 — era J02 (600 x 600 = 0,36 m2) e passa a J04 (800 x 900 = 0,72 m2).
    # As suites 02 e 03 sao declaradas ESPELHADAS e intocadas desde R06, e os
    # banhos delas tinham esquadrias diferentes: 0,36 m2 num, 0,72 no outro. A
    # assimetria nao tinha justificativa escrita, e era justamente o banho da
    # 02 que ficava abaixo — 0,36 para 4,32 m2 de piso e 1/12, contra o minimo
    # (H) de 1/8 para area molhada. Uniformizar em J04 resolve norma e simetria
    # de uma vez, por ~R$ 300, e reduz o quadro de esquadrias em uma familia.
    ("J04",   3_600, 13_200, "H", "S"),   # janela banho suite 02 (espelha a 03)
    ("J05",   2_400, 21_600, "V", "S"),   # janela ampla suite 03 (sul)
    ("J01",   6_000, 22_800, "H", "S"),   # janela suite 03 (oeste)
    ("J04",   2_400, 18_600, "V", "S"),   # janela alta banho suite 03
    ("J05",   7_800, 24_000, "V", "S"),   # dormitorio master (sul)
    ("PV02",  9_600, 25_200, "H", "S"),   # dormitorio master -> varanda
    ("J05",  12_000, 25_200, "H", "S"),   # dormitorio master -> varanda
    ("J04",  15_600, 20_700, "V", "S"),   # janela alta do closet master (norte)
    ("J01",  15_600, 23_700, "V", "S"),   # janela do office master (norte)

]

# =========================================================================
# ELEMENTOS EXTERNOS
# =========================================================================
# R06 — o YAML do proprietario fixa 5,50 x 3,20 m (17,60 m2). Adotado
# 5,40 x 3,30 = 17,82 m2: mesma area util, mas sobre a malha de 300 mm. Meio
# metro fora de modulo em piscina custa recorte de pastilha em todo o perimetro
# e um recorte de deck que aparece a cada volta que se da em torno dela.
PISCINA = dict(x=4_800, y=30_600, w=5_400, h=3_300,
               prainha_w=1_200, prof_prainha=300, prof_principal=1_150,
               banco_w=450, banco_prof=450,
               lamina_m2=17.82, volume_m3=17.13,
               faixa_seca_min=900)
PISCINA_SISTEMA = dict(
    skimmers=1, drenos_fundo=2, antiaprisionamento=True, retornos=4, aspiracao=1,
    bomba="velocidade variavel 0,5 cv", filtro="areia DE 500 mm",
    renovacao_h=6, leds=3, led_k="2700-3000 K", led_w=18,
    tratamento="cloro convencional; sal em espera (HOLD no YAML)",
    aquecimento="nao instalado; bypass e espaco de trocador previstos",
    obs="dois drenos de fundo afastados 900 mm sao exigencia antiaprisionamento: "
        "com um unico dreno o corpo veda a succao")


def vazao_recirculacao_m3h() -> float:
    """Vazao de projeto = volume / tempo de renovacao."""
    return round(PISCINA["volume_m3"] / PISCINA_SISTEMA["renovacao_h"], 2)
# casa de maquinas da piscina = elemento tecnico TC-13 (ver TECNICOS).
# SEMI-enterrada: o piso fica 600 mm abaixo do deck, nao 1.200. Razao: a
# motobomba e o filtro precisam ficar ACIMA do nivel da agua de lavagem do
# filtro para a retrolavagem drenar por gravidade, e a tampa em grelha
# garante a ventilacao que um alcapao cego nao daria (motor de 1/2 cv
# dissipa ~300 W de calor em recinto confinado).
# R06 — o YAML manda concentrar TUDO na lateral tecnica, e tem razao: a casa
# semi-enterrada sob o deck resolvia o volume no jardim, mas punha uma tampa em
# grelha no meio do piso onde as pessoas andam descalcas, exigia descer para
# operar registro e deixava a retrolavagem drenando para uma vala isolada.
# Na faixa tecnica o equipamento fica em pe, ventilado, ao lado do ralo que ja
# existe, e a manutencao inteira da casa acontece num corredor so.
# Custo da mudanca: 6,2 m de linha de succao — dentro do limite de 10 m.
CASA_MAQUINAS = dict(x=17_000, y=29_400, w=1_500, h=2_000,
                     enterrada=False, semienterrada=False,
                     acesso="porta ripada de 800 mm na faixa tecnica",
                     ventilacao="veneziana inferior e superior, 0,20 m2 cada",
                     dreno="ralo sifonado DN75 ligado a drenagem da faixa",
                     nota="em pe na lateral tecnica: operacao sem agachar e sem "
                          "tampa no piso do deck")
DECK = dict(x=3_600, y=29_400, w=7_800, h=5_400,           # envolve a piscina
            faixa_seca={"sul": 1_200, "norte": 900, "oeste": 1_200, "leste": 1_200})
# YAML pede WPC predominante e manda VERIFICAR o aquecimento superficial. A
# verificacao condena o WPC escuro justamente onde ele seria mais usado: com
# albedo de 0,20 a superficie passa de 65 C sob sol de Manaus, contra ~45 C de
# um porcelanato claro (albedo 0,60). O limiar de dor ao pe descalco e 50 C.
# Solucao por zona, nao por material unico:
PISO_EXTERNO = [
    dict(zona="faixa seca da piscina", material="porcelanato externo claro R11",
         area_m2=None, razao="e onde se anda descalco no pico do sol"),
    dict(zona="lounge e circulacao do deck", material="WPC coextrudado claro",
         area_m2=None, razao="area de permanencia com mobiliario e sombra"),
    dict(zona="passeio e acesso", material="piso drenante intertravado claro",
         area_m2=None, razao="compensa a permeabilidade perdida pelo deck"),
    # R49 — a varanda da master era a unica area aberta sem zona de piso
    # declarada: 14,04 m2 no pavimento superior, expostos a chuva, sem material.
    # Leva o MESMO porcelanato externo R11 da faixa seca da piscina — nao e
    # material novo, e a familia continua em tres.
    dict(zona="varanda do pavimento superior",
         material="porcelanato externo claro R11", area_m2=None,
         razao="mesma exigencia de piso molhado e descalco da faixa da "
               "piscina, sem acrescentar familia"),
]
FAIXA_TECNICA = dict(x=16_800, y=0, w=3_200, h=LOTE_P)     # lateral direita
# A caixa estava sobre o VAZIO do core: 25 kN apoiados em uma plataforma de
# 2,4 m vencendo o poco de luz. Deslocada para o atico sobre o banho da master,
# onde desce direto nas paredes do proprio ambiente — vao curto, sem plataforma
# sobre vazio, e logo acima do maior consumo da casa.
#
# E uma conta que nao tem volta: com pe-direito de 2.600 mm, a base da caixa no
# atico fica a 5.600 mm e o chuveiro do pavimento superior a 5.100 mm. Sobram
# 500 mm de coluna — 0,5 mca. Chuveiro eletrico exige 1,5 a 2,0 mca para
# acionar o pressostato. Em casa de dois pavimentos com laje a 3.000 mm, caixa
# elevada NAO resolve a pressao do andar de cima: isso e aritmetica, nao opcao.
# Dai o pressurizador, servindo apenas o ramal superior. O terreo continua por
# gravidade, com 3,5 mca — folgado.
CAIXA_DAGUA = dict(x=11_400, y=19_200, w=2_400, h=3_000,
                   volume_l=2_000, pe_direito=2_100, carga_kg=2_500,
                   nivel_base=PISO_A_PISO + PE_DIREITO,      # 5.600 mm
                   sobre="S-MAS/BANHO", pav="atico")
PRESSURIZADOR = dict(cod="TC-14", potencia_cv=0.5, pressao_mca=12.0,
                     atende=["S-MAS", "S-S02", "S-S03"], vazao_m3h=1.8,
                     local="atico, junto a caixa",
                     obs="pressostato e vaso de expansao de 2 L; so o ramal "
                         "superior. Terreo por gravidade (3,5 mca)")
ALTURA_CHUVEIRO = 2_100
def carga_hidraulica_mca(pav: str) -> float:
    """Coluna disponivel entre a base da caixa e o chuveiro do pavimento."""
    base = CAIXA_DAGUA["nivel_base"]
    ponto = (PISO_A_PISO if pav == "S" else 0) + ALTURA_CHUVEIRO
    return round((base - ponto) / 1_000, 2)

# escada em U — 18 espelhos x 166,67 mm, piso 300, largura util 1.000
# A geometria da escada passa a ser DADO do modelo, com cada lance e o patamar
# em coordenada declarada. Antes existia so no codigo de desenho, e por isso
# nenhuma verificacao de altura livre era possivel: o patamar invadia 100 mm
# da projecao do hall superior e ficava com 1.500 mm de altura livre — uma
# quina exatamente na altura da cabeca de quem termina o primeiro lance.
# Correcao: o primeiro espelho sobe de y = 13.200 (rente a borda do core) e o
# patamar termina em 16.600, 200 mm antes da borda da laje do hall.
ESCADA = dict(x=9_600, y=13_200, w=2_400, h=6_000,
              espelhos=18, alt_espelho=3_000 / 18, piso=300,
              larg_lance=1_000, patamar=1_000, blondel=2 * (3_000 / 18) + 300,
              y0=13_400,            # inicio do patamar inferior
              y_chegada=16_800,     # onde o segundo lance encosta no hall
              folga_lances=100)     # vazio entre os dois lances


def escada_lances() -> list[dict]:
    """Lances e patamar em coordenada absoluta, com nivel de inicio e fim."""
    e = ESCADA
    lar, piso, pat = e["larg_lance"], e["piso"], e["patamar"]
    n = (e["espelhos"] // 2) - 1                     # 8 pisos por lance
    h = e["alt_espelho"]
    y0 = e["y0"]
    x1 = e["x"] + 150
    x2 = x1 + lar + e["folga_lances"]
    fim1 = y0 + n * piso
    # R06: os dois lances invertem o sentido para a CHEGADA cair no hall
    # superior (y = 16.800). Antes o segundo lance terminava no meio do vazio,
    # onde nao havia laje nenhuma para pisar.
    yc = e["y_chegada"]
    yi = yc - n * piso                      # inicio dos lances
    return [
        dict(cod="L1", x=x1, y=yi, w=lar, h=n * piso, sentido="-Y",
             z_ini=0.0, z_fim=(n + 1) * h, espelhos=n + 1),
        dict(cod="PT", x=x1, y=y0, w=lar * 2 + e["folga_lances"], h=pat,
             sentido="patamar", z_ini=(n + 1) * h, z_fim=(n + 1) * h, espelhos=0),
        dict(cod="L2", x=x2, y=yi, w=lar, h=n * piso, sentido="+Y",
             z_ini=(n + 1) * h, z_fim=PISO_A_PISO, espelhos=n + 1),
    ]

# ---------------------------------------------------------------- cobertura
# planos de cobertura com 5 % de caimento e calha externa 150x100
# A area de contribuicao pluvial estava congelada em 174,24 m2 — o numero do
# briefing para a area FECHADA do terreo. Area de contribuicao nao e isso: e a
# projecao horizontal de TUDO o que tem telhado, mais os beirais que avancam
# alem dela. Calcular a chuva sobre 174 m2 quando caem 235 m2 de telhado e
# subdimensionar calha e descida em 35 %, justamente no lugar onde a falha se
# manifesta como infiltracao na parede, nao como transbordo visivel.
COBERTURA = dict(inclinacao=INCLIN_COBERTURA, calha_l=150, calha_h=100,
                 descidas=4, dn_descida=100, intensidade_mm_h=180,
                 coef_escoamento=0.95, rugosidade_calha=0.011,
                 decliv_calha=0.005, enchimento_calha=2 / 3)


def area_contribuicao_m2() -> float:
    """Projecao coberta mais a faixa de beiral no perimetro do conjunto.

    Simplificacao declarada: o beiral e somado como uma faixa no perimetro do
    retangulo envolvente dos ambientes cobertos, com a largura media dos quatro
    lados. Nao e exato no recorte da planta em L, mas erra para MAIS, que e o
    lado seguro em drenagem.
    """
    base = projecao_coberta_m2()
    cob = cobertos()
    x0 = min(a.x for a in cob); x1 = max(a.x + a.w for a in cob)
    y0 = min(a.y for a in cob); y1 = max(a.y + a.h for a in cob)
    perim = 2 * ((x1 - x0) + (y1 - y0)) / 1_000
    b_med = sum(BEIRAIS.values()) / len(BEIRAIS) / 1_000
    return round(base + perim * b_med, 2)


def vazao_pluvial_ls() -> float:
    """Q = C . i . A / 3600 (i em mm/h, A em m2, Q em L/s)."""
    return round(COBERTURA["coef_escoamento"] * COBERTURA["intensidade_mm_h"]
                 * area_contribuicao_m2() / 3_600, 4)


def capacidade_calha_ls() -> float:
    """Manning em calha retangular: Q = (1/n) A Rh^(2/3) S^(1/2)."""
    cb = COBERTURA
    b = cb["calha_l"] / 1_000
    h = cb["calha_h"] / 1_000 * cb["enchimento_calha"]
    a = b * h
    rh = a / (b + 2 * h)
    return round((1 / cb["rugosidade_calha"]) * a * rh ** (2 / 3)
                 * math.sqrt(cb["decliv_calha"]) * 1_000, 2)


# NBR 10844, condutores verticais: DN100 com 3 m de altura suporta cerca de
# 12,5 L/s. Adotado 8,0 L/s como limite de projeto, porque a tabela pressupoe
# curva suave na base e o valor cheio nao deixa margem para folha e detrito.
CAPACIDADE_DESCIDA = {75: 4.5, 100: 8.0, 125: 14.0, 150: 22.0}


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
# R48 — ALTURA e cota de base entram como DADO. Ate aqui o 3D desenhava o
# brise de z=900 a z=2.400 (altura 1.500) e com 120 mm de profundidade, tudo
# literal dentro de modelo3d.py, enquanto o dado declarava profundidade 150.
# Duas fontes para a mesma peca, e as duas dentro de modulos de DESENHO — o
# ripado nao existia como material, como massa nem como carga em lugar nenhum.
BRISES = [
    dict(cod="BR-O", face="O", x=5_400, y=27_600, w=4_200, h=150,
         tipo="ripado vertical MOVEL, recolhivel", passo=150,
         desc="alpendre do gourmet - recolhe totalmente para liberar a vista da piscina", z0=900, altura=1_500),
    dict(cod="BR-L", face="L", x=12_000, y=7_200, w=3_000, h=150,
         tipo="ripado vertical fixo", passo=150,
         desc="quarto reversivel - testada leste", z0=900, altura=1_500),
    # R09 — as duas janelas amplas das suites ficam a 2.400 mm da divisa sul com
    # peitoril de 1.100: altura de olho de quem passa no recuo do vizinho. Brise
    # ripado vertical fixo resolve privacidade e sol rasante de uma vez, na mesma
    # familia de aluminio grafite do portao e da fachada.
    dict(cod="BR-S2", face="S", x=2_400, y=15_900, w=1_800, h=150,
         tipo="ripado vertical fixo", passo=80,
         desc="janela ampla da suite 02 — privacidade contra a divisa sul", z0=900, altura=1_500),
    dict(cod="BR-S3", face="S", x=2_400, y=20_700, w=1_800, h=150,
         tipo="ripado vertical fixo", passo=80,
         desc="janela ampla da suite 03 — privacidade contra a divisa sul", z0=900, altura=1_500),
    dict(cod="BR-OS", face="O", x=10_200, y=22_800, w=6_000, h=150,
         tipo="ripado vertical movel", passo=150,
         desc="varanda master - pavimento superior", z0=900, altura=1_500),
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
          ("Irrigacao com paisagismo adaptado", None)],   # calculado: ver usos_pluviais()
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


def usos_pluviais() -> list[tuple[str, float]]:
    """Usos do reuso, com a irrigacao CALCULADA dos setores declarados.

    Os 100 L/dia de irrigacao eram estimativa. Com o paisagismo e os setores de
    gotejamento definidos na Etapa 4, o numero passa a ser consequencia:
    3 setores x 240 L/h x 20 min, 2 vezes por semana.
    """
    out = []
    for nome, v in PLUVIAL["usos"]:
        out.append((nome, demanda_irrigacao_ldia() if v is None else float(v)))
    return out


def balanco_pluvial() -> dict:
    area = projecao_coberta_m2()
    captacao = area * (PLUVIAL["precipitacao_mm_ano"] / 1000) * \
        PLUVIAL["coef_escoamento"] * (1 - PLUVIAL["descarte_inicial"])
    demanda_dia = sum(v for _, v in usos_pluviais())
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
PE_DIREITO_DUPLO = ["T-SOC", "T-COR"]     # ambientes com vazio sobre parte da area
LANTERNIM = dict(x=8_400, y=13_800, w=3_600, h=2_400,
                 altura_peitoril=PISO_A_PISO + PE_DIREITO,    # 5.600 mm
                 veneziana_h=500, faces=2, frac_livre=0.50,
                 vidro="laminado leitoso 6 mm, voltado ao sul (sem sol direto)",
                 obs="venezianas em duas faces: uma sempre a sotavento")
CHAMINE = dict(cd=0.60, dt_k=3.0, t_ext_k=303.0,
               centroide_entrada=1_700, centroide_saida=6_200)


def area_venezianas_m2() -> float:
    lt = LANTERNIM
    return round(lt["w"] * lt["veneziana_h"] * lt["faces"] * lt["frac_livre"] / 1e6, 2)


def vazao_chamine_m3h(a_entrada_m2: float | None = None) -> float:
    """Vazao por efeito chamine, com areas de entrada e saida em serie."""
    a_out = area_venezianas_m2()
    a_in = a_entrada_m2 if a_entrada_m2 else a_out
    a_ef = 1.0 / math.sqrt(1.0 / a_in ** 2 + 1.0 / a_out ** 2)
    dh = (CHAMINE["centroide_saida"] - CHAMINE["centroide_entrada"]) / 1_000
    v = math.sqrt(2 * 9.81 * dh * CHAMINE["dt_k"] / CHAMINE["t_ext_k"])
    return round(CHAMINE["cd"] * a_ef * v * 3_600, 0)


def volume_chamine_m3() -> float:
    """Volume servido: fita social no pe-direito simples + o vazio."""
    base = sum(a.area_mod for a in TERREO
               if a.cod in ("T-SOC", "T-COR", "T-GOU", "T-COZ"))
    return round(base * PE_DIREITO / 1_000, 2)


def trocas_por_hora(a_entrada_m2: float | None = None) -> float:
    return round(vazao_chamine_m3h(a_entrada_m2) / volume_chamine_m3(), 1)


# =========================================================================
# ESTRUTURA — INTERFACE LSF x PERFIL LAMINADO
#
# Este e o ponto de maior risco de patologia do projeto, e a razao e simples:
# os dois sistemas tem rigidez e comportamento incompativeis.
#
# O perfil laminado FLETE. Uma viga de aco dimensionada pela resistencia pode
# fletir L/300 sem nenhum problema estrutural. A parede de Light Steel Frame
# que se apoia nela, porem, e fechada com chapa de gesso e chapa cimenticia:
# material FRAGIL, que fissura com deformacao imposta muito antes de qualquer
# risco estrutural. O resultado classico e a fissura horizontal no topo da
# parede do pavimento superior, que o morador atribui a "recalque" e que na
# verdade e a viga trabalhando exatamente como foi calculada.
#
# Duas medidas resolvem, e sao independentes:
#   1. LIMITE DE FLECHA MAIS SEVERO: L/500 onde a viga suporta vedacao fragil,
#      contra L/350 de uso geral. Custa inercia, nao resistencia.
#   2. JUNTA DE DESLIZAMENTO (slip track) no topo da parede LSF: a guia
#      superior e fixada a estrutura e os montantes correm livres dentro dela,
#      com folga de 1,5 x flecha calculada. A parede deixa de receber a
#      deformacao da viga. Sem isso, o item 1 apenas atrasa a fissura.
#
# E = 200.000 MPa (aco estrutural). Carregamentos conforme NBR 6120.
# =========================================================================
E_ACO = 200_000             # MPa = N/mm2
# A verga de uma cortina de vidro nao e governada pelo gesso: e governada pelo
# TRILHO. As folhas sao placas rigidas de vidro temperado correndo num perfil
# continuo; 13 mm de flecha no meio do vao fazem o trilho fechar sobre as
# folhas e o sistema travar. Fabricante pede L/700, nao L/500.
FLECHA_LIMITE = {"vedacao_fragil": 500, "geral": 350, "balanco": 250,
                 "cortina_vidro": 700}
FOLGA_SLIP = 1.5            # folga da junta de deslizamento = 1,5 x flecha
BALANCO_MAX_LSF = 600       # balanco que o proprio vigamento de LSF resolve
FY_ACO = 250                # MPa — ASTM A572 / ASTM A36 (H)
GAMA_F = 1.4                # coeficiente de majoracao das acoes
GAMA_M = 1.1                # coeficiente de minoracao da resistencia

# cargas caracteristicas (kN/m2) — NBR 6120
# ------------------------------------------------------------------- vento
# Parametros da NBR 6123 para o caso. Sao (H) no sentido preciso do projeto: a
# leitura da isopleta e a classificacao de rugosidade sao interpretacao, nao
# medicao, e quem assina a ART pode ler diferente.
#
# V0 = 30 m/s — Manaus cai dentro da isopleta de 30 m/s da Figura 1 da NBR
#   6123, que cobre quase toda a Amazonia. E, nao por acaso, o menor valor da
#   carta: e por isso que vento raramente governa projeto residencial aqui, e
#   por isso mesmo que o valor precisa ser conferido em vez de assumido.
# Categoria IV — "obstaculos numerosos e pouco espacados, em zona florestal ou
#   urbanizada". O condominio no Taruma, com mata remanescente e lotes
#   ocupados, e IV. Quem considerar o lote mais aberto usa III, e a diferenca
#   em S2 e da ordem de 10 %.
# Classe B — maior dimensao da edificacao entre 20 e 50 m.
# ------------------------------------------------------------------ radier
# A espessura vivia como literal `RADIER = 180` dentro de pranchas2.py e, em
# copia, como `esp_radier = 180.0` dentro do dimensionamento de ancoragem. Dois
# lugares para o mesmo numero, e nenhum deles era dado do projeto — o desenho
# dizia 180 e a ancoragem acreditava.
#
# TUDO AQUI E (H) ATE A SONDAGEM. Radier e a peca que mais depende do solo, e
# a pendencia 2 do caderno e exatamente esta. O que este bloco permite e
# derivar QUANTIDADE para uma espessura declarada; ele nao dimensiona radier,
# e nao substitui o calculo com ART.
RADIER = dict(
    espessura=180,            # mm (H): sem sondagem, e pre-dimensionamento
    fck=30,                   # MPa (H)
    aco="CA-50",
    tela="Q196",              # malha soldada, 3,4 kg/m2 (H)
    taxa_armadura=45.0,       # kg de aco por m3 de concreto (H), radier leve
    cobrimento=30,            # mm, classe de agressividade II da NBR 6118
    lastro=100,               # mm de brita graduada sob o radier
    lona=1,                   # camada de lona plastica 150 micra
    balanco_borda=100,        # mm de radier alem da face externa da parede
    norma="NBR 6118 e NBR 6122",
    pendencia="sondagem SPT e calculo definitivo — pendencia 2 do caderno",
)

V0_VENTO = 30.0
CATEGORIA_VENTO = "IV"
CLASSE_VENTO = "B"
S1_VENTO = 1.00          # terreno plano ou fracamente acidentado
S3_VENTO = 1.00          # residencia: grupo 2 da Tabela 3

CARGAS = {
    "piso_lsf_perm": 1.20,       # vigamento + OSB + contrapiso seco + forro
    "piso_lsf_acid": 1.50,       # dormitorio e sala
    "cobertura_perm": 0.35,      # painel PIR 75 mm + estrutura
    "cobertura_acid": 0.25,      # manutencao
    "parede_lsf_m": 0.50,        # kN/m2 de parede (x altura = kN/m)
    "deck_acid": 3.00,           # varanda e sacada: NBR 6120
    "escada_perm": 0.60,         # degrau em chapa dobrada + revestimento
    "escada_acid": 2.50,         # NBR 6120: escada de uso privativo
}

# perfis laminados (Ix em cm4, massa em kg/m) — tabela Gerdau
PERFIS_LAMINADOS = {
    "W150x13.0": dict(ix=635,   h=148, bf=100, massa=13.0),
    "W200x15.0": dict(ix=1_305, h=200, bf=100, massa=15.0),
    "W200x19.3": dict(ix=1_686, h=203, bf=102, massa=19.3),
    "W250x17.9": dict(ix=2_291, h=251, bf=101, massa=17.9),
    "W250x22.3": dict(ix=2_939, h=254, bf=102, massa=22.3),
    "W310x23.8": dict(ix=4_346, h=305, bf=101, massa=23.8),
    "W310x28.3": dict(ix=5_410, h=309, bf=102, massa=28.3),
}

# perfis formados a frio do LSF (NBR 15253)
PERFIS_LSF = {
    "Ue90x40x0.95":  dict(ix=35.6,  h=90,  uso="montante de parede"),
    "Ue140x40x0.95": dict(ix=111.0, h=140, uso="montante de parede externa"),
    "Ue200x40x1.25": dict(ix=400.0, h=200, uso="viga de piso vao curto"),
    "Ue250x40x1.55": dict(ix=860.0, h=250, uso="viga de piso 5.400 mm"),
    "Ue300x40x1.55": dict(ix=1_420.0, h=300, uso="viga de piso vao longo"),
}
MONTANTE_ESPACAMENTO = 600
MONTANTE_ESPACAMENTO_REFORCADO = 400


def flecha_mm(w_kn_m: float, vao_mm: int, ix_cm4: float,
              apoio: str = "biapoiada") -> float:
    """Flecha no meio do vao para carga uniformemente distribuida.

    biapoiada: 5 w L^4 / (384 E I).  balanco: w L^4 / (8 E I).
    w em kN/m -> N/mm dividindo por 1.000 (1 kN/m = 1 N/mm).
    Ix em cm4 -> mm4 multiplicando por 1e4.
    """
    w = w_kn_m                      # kN/m == N/mm
    ix = ix_cm4 * 1e4
    if apoio == "balanco":
        return (w * vao_mm ** 4) / (8 * E_ACO * ix)
    return (5 * w * vao_mm ** 4) / (384 * E_ACO * ix)


def inercia_necessaria(w_kn_m: float, vao_mm: int, limite: int,
                       apoio: str = "biapoiada") -> float:
    """Ix minimo (cm4) para atender flecha <= vao/limite."""
    alvo = vao_mm / limite
    w = w_kn_m
    if apoio == "balanco":
        ix = (w * vao_mm ** 4) / (8 * E_ACO * alvo)
    else:
        ix = (5 * w * vao_mm ** 4) / (384 * E_ACO * alvo)
    return ix / 1e4


def escolher_perfil(w_kn_m: float, vao_mm: int, limite: int,
                    apoio: str = "biapoiada") -> tuple[str, float, float]:
    """Menor perfil laminado que atende a flecha. Retorna (perfil, ix, flecha)."""
    need = inercia_necessaria(w_kn_m, vao_mm, limite, apoio)
    for nome, p in sorted(PERFIS_LAMINADOS.items(), key=lambda kv: kv[1]["ix"]):
        if p["ix"] >= need:
            return nome, p["ix"], flecha_mm(w_kn_m, vao_mm, p["ix"], apoio)
    nome, p = max(PERFIS_LAMINADOS.items(), key=lambda kv: kv[1]["ix"])
    return nome, p["ix"], flecha_mm(w_kn_m, vao_mm, p["ix"], apoio)


# -------------------------------------------------------------------------
# PILARES — apoio do pavimento superior sobre areas abertas.
# Em Light Steel Frame um balanco de 1.800 mm nao se resolve no proprio
# vigamento (a pratica limita o balanco a ~600 mm ou 1/4 do vao de tras):
# exigiria perfil laminado de borda com flecha e vibracao perceptiveis na ponta
# e um detalhe de estanqueidade critico. Por isso tudo o que avanca sobre area
# aberta desce em pilar ou em viga entre apoios, nunca em balanco.
# R06 — portico ortogonal de 3.000 mm em duas linhas (x = 12.600 e 15.600),
# sustentando o mini lounge sobre o deck norte, a master sobre o varal e o
# patio, e a varanda. Substitui os seis pilares dispersos da revisao anterior:
# duas linhas continuas sao mais baratas de executar e deixam o terreo legivel.
PILARES = [
    dict(x=12_600, y=16_800), dict(x=15_600, y=16_800),
    dict(x=12_600, y=19_200), dict(x=15_600, y=19_200),
    dict(x=12_600, y=22_200), dict(x=15_600, y=22_200),
    dict(x=12_600, y=25_200), dict(x=15_600, y=25_200),
    dict(x=12_600, y=27_000), dict(x=15_600, y=27_000),
]
PILAR_SECAO = "perfil metalico 200 x 200 mm (H)"


# -------------------------------------------------------------------------
# VIGAS — cada uma com carga declarada, nao com perfil "escolhido no olho".
# trib = largura de influencia em mm. vedacao=True -> limite L/500 e slip track.
# -------------------------------------------------------------------------
VIGAS = [
    dict(cod="V-01", sobre="T-LOG", vao=3_000, trib=2_700, apoio="biapoiada",
         carrega="piso", parede_h=2_600, vedacao=True,
         desc="face aberta da loggia sul; sustenta a parede sul das suites 02 e 03"),
    dict(cod="V-02", sobre="T-GAR", vao=5_400, trib=3_000, apoio="biapoiada",
         carrega="cobertura", parede_h=0, vedacao=False,
         desc="verga do portao PG01 de 5.400 mm"),
    dict(cod="V-03", sobre="T-GAR", vao=6_000, trib=3_000, apoio="biapoiada",
         carrega="cobertura", parede_h=0, vedacao=False,
         desc="vao livre da garagem sem pilar intermediario"),
    dict(cod="V-04", sobre="T-DKL", vao=3_000, trib=1_200, apoio="biapoiada",
         carrega="piso", parede_h=2_600, vedacao=True,
         desc="portico sobre o deck norte; sustenta o mini lounge e cria o "
              "trecho coberto do deck"),
    dict(cod="V-05", sobre="T-VRL", vao=3_000, trib=3_000, apoio="biapoiada",
         carrega="piso", parede_h=2_600, vedacao=True,
         desc="portico sobre o varal coberto; sustenta o banho e o office da master"),
    dict(cod="V-06", sobre="T-PAT", vao=3_000, trib=3_000, apoio="biapoiada",
         carrega="piso", parede_h=2_600, vedacao=True,
         desc="portico sobre o patio coberto; sustenta o dormitorio da master"),
    dict(cod="V-07", sobre="T-PAT", vao=3_000, trib=1_800, apoio="biapoiada",
         carrega="deck", parede_h=0, vedacao=False,
         desc="borda da varanda master, entre os pilares de y = 25.200 e 27.000"),
    dict(cod="V-08", sobre="T-JN2", vao=3_000, trib=900, apoio="biapoiada",
         carrega="deck", parede_h=0, vedacao=False,
         desc="viga de borda da varanda entre a parede do gourmet (x = 9.600) e "
              "o pilar de x = 12.600"),
    dict(cod="V-09", sobre="T-JN3", vao=3_000, trib=900, apoio="biapoiada",
         carrega="deck", parede_h=0, vedacao=False,
         desc="viga de borda da varanda entre os pilares de x = 12.600 e 15.600"),
    # R07 — a viga que permite a abertura de 7.200 mm sem montante no meio.
    # E ela, e nao a esquadria, que decide se a vista existe: qualquer apoio
    # intermediario apareceria exatamente no eixo da piscina.
    dict(cod="V-10", sobre="T-ALP", vao=7_200, trib=3_000, apoio="biapoiada",
         carrega="cobertura", parede_h=0, vedacao=True, vao_max=9_000,
         limite_flecha="cortina_vidro",
         desc="verga da cortina de vidro CV01, entre a divisa sul (x = 2.400) e a "
              "parede do patio (x = 9.600); sustenta a cobertura da varanda"),
    dict(cod="V-11", sobre="T-ALP", vao=3_000, trib=1_200, apoio="balanco",
         carrega="cobertura", parede_h=0, vedacao=False,
         desc="vigas em balanco da cobertura da varanda, a cada 1.200 mm: 3.000 mm "
              "de beiral SEM pilar na frente, para nao haver coluna entre a mesa "
              "e a piscina"),
]
VAO_MAX_VIGA = 6_000


def carga_viga(v: dict) -> float:
    """Carga linear de servico (kN/m) da viga, a partir de CARGAS e trib."""
    trib_m = v["trib"] / 1_000
    if v["carrega"] == "piso":
        q = CARGAS["piso_lsf_perm"] + CARGAS["piso_lsf_acid"]
    elif v["carrega"] == "deck":
        q = CARGAS["piso_lsf_perm"] + CARGAS["deck_acid"]
    else:
        q = CARGAS["cobertura_perm"] + CARGAS["cobertura_acid"]
    w = q * trib_m
    if v.get("parede_h"):
        w += CARGAS["parede_lsf_m"] * (v["parede_h"] / 1_000)
    return round(w, 2)


def tensao_mpa(w_kn_m: float, vao_mm: int, perfil: str,
               apoio: str = "biapoiada") -> float:
    """Tensao de flexao de calculo. Wx aproximado por Ix / (h/2)."""
    p = PERFIS_LAMINADOS[perfil]
    wx = (p["ix"] * 1e4) / (p["h"] / 2)                      # mm3
    m = (GAMA_F * w_kn_m * (vao_mm / 1_000) ** 2 / (2 if apoio == "balanco" else 8))
    return (m * 1e6) / wx                                    # N/mm2


def dimensionar_vigas() -> list[dict]:
    """Resolve cada viga: carga, limite, perfil minimo, flecha, tensao e slip.

    O perfil e escolhido pela FLECHA, nao pela resistencia — em vao curto com
    vedacao fragil acima, e a flecha que governa, e por margem larga: as tensoes
    resultantes ficam em torno de 40 % da resistencia. Gastar aco em inercia e
    mais barato que reparar fissura em gesso pelo resto da vida do edificio.
    """
    out = []
    for v in VIGAS:
        w = carga_viga(v)
        lim = FLECHA_LIMITE[v.get("limite_flecha")
                            or ("vedacao_fragil" if v["vedacao"] else "geral")]
        perfil, ix, fl = escolher_perfil(w, v["vao"], lim, v["apoio"])
        sig = tensao_mpa(w, v["vao"], perfil, v["apoio"])
        slip = int(math.ceil(fl * FOLGA_SLIP)) if v["vedacao"] else 0
        out.append(dict(v, w=w, limite=lim, perfil=perfil, ix=ix,
                        flecha=round(fl, 2), flecha_adm=round(v["vao"] / lim, 2),
                        tensao=round(sig, 1), tensao_adm=round(FY_ACO / GAMA_M, 1),
                        uso=round(sig / (FY_ACO / GAMA_M) * 100, 1),
                        slip=slip,
                        slip_exec=max(10, int(math.ceil(slip / 5.0) * 5)) if slip else 0))
    return out


# caixa d'agua: carga CONCENTRADA, nao distribuida — 2.000 L sobre o core
APOIO_CAIXA = dict(
    peso_kg=CAIXA_DAGUA["carga_kg"], vao=CAIXA_DAGUA["w"], perfis=2,
    desc="dois perfis sob a base, transferindo para as paredes do core; a carga "
         "de 25 kN em 2,4 m de vao NAO pode descer em vigamento de LSF")



# =========================================================================
# FURACAO E PENETRACOES EM LIGHT STEEL FRAME
#
# Em alvenaria, furar parede e decisao de obra. Em LSF e decisao de PROJETO:
# o montante e uma chapa de 0,95 mm que trabalha a compressao, e um furo fora
# de lugar reduz a carga critica de flambagem local. Pior: o eletricista que
# descobre isso na obra resolve cortando a aba, que e exatamente onde esta a
# rigidez. Dai a necessidade de um plano de furacao desenhado.
#
# Regras (NBR 15253 e AISI S200):
#   - furo centrado na alma, nunca nas abas;
#   - diametro maximo 0,5 x altura da alma (montante 90 mm -> 45 mm);
#   - distancia minima entre centros de furos: 600 mm;
#   - distancia minima do furo ao apoio: 250 mm (montante) / 450 mm (viga);
#   - tubo maior que o furo admissivel NAO passa no montante: passa em shaft,
#     em forro rebaixado ou em parede de 150 mm com montante duplo.
# =========================================================================
FURACAO = dict(
    frac_alma=0.5, dist_centros=600, dist_apoio_montante=250,
    dist_apoio_viga=450, reforco="chapa de 1,55 mm parafusada no contorno",
)


def furo_max(perfil: str) -> int:
    """Diametro maximo de furo admissivel na alma do perfil."""
    return int(PERFIS_LSF[perfil]["h"] * FURACAO["frac_alma"])


# Posicao das prumadas. Ate R37 as coordenadas viviam dentro do modulo de
# desenho — `for sc, sx, sy in (("PN-01", 11_400, 19_200), ...)` — e por isso
# nao existia comprimento de tubo nenhum: sem saber ONDE esta a prumada, nao ha
# como medir o ramal ate ela. Mesmo padrao da espessura do radier, que era
# literal em pranchas2.py ate R37.
PRUMADAS = [
    dict(cod="PN-01", x=11_400, y=19_200, tipo="esgoto", dn=100,
         secao=(300, 300), onde="shaft do core"),
    dict(cod="PN-02", x=2_400, y=18_000, tipo="esgoto", dn=100,
         secao=(300, 300), onde="shaft da suite 02/03"),
    dict(cod="AF-01", x=11_700, y=19_200, tipo="agua fria", dn=32,
         secao=(150, 150), onde="junto ao shaft do core"),
]

# travessias declaradas: o que atravessa o que, e por onde
PENETRACOES = [
    dict(cod="PN-01", tipo="esgoto DN100", dn=100, onde="shaft do core",
         de="S-MAS", para="TC-12", solucao="shaft vertical 300 x 300 mm",
         obs="DN100 nao cabe em montante de 90 mm: exige shaft, por definicao"),
    dict(cod="PN-02", tipo="esgoto DN100", dn=100, onde="shaft da suite 02/03",
         de="S-S02", para="TC-11", solucao="shaft vertical 300 x 300 mm"),
    dict(cod="PN-03", tipo="agua fria DN25", dn=25, onde="montante",
         de="TC-02", para="CAIXA_DAGUA", solucao="furo centrado 45 mm"),
    dict(cod="PN-04", tipo="agua quente PEX DN20", dn=20, onde="montante",
         de="chuveiros", para="quadro", solucao="furo centrado 45 mm"),
    dict(cod="PN-05", tipo="linha frigorigena 1/4 + 1/2", dn=40, onde="montante",
         de="TC-09", para="S-MAS", solucao="furo centrado 45 mm com bucha de "
         "passagem; isolamento continuo, sem corte na travessia"),
    dict(cod="PN-06", tipo="duto de insuflamento 250 mm", dn=250,
         onde="entreforro", de="EVAPORADORA_DUTO", para="DF-01",
         solucao="entreforro de 400 mm no core e no estar",
         obs="duto nao atravessa montante em nenhuma hipotese"),
    dict(cod="PN-07", tipo="exaustao de churrasqueira DN150", dn=150,
         onde="cobertura", de="EX-01", para="acima da cobertura",
         solucao="duto em inox com colarinho e rufo; nao encosta em PIR"),
    dict(cod="PN-08", tipo="eletroduto 25 mm", dn=25, onde="montante",
         de="TC-05", para="todos", solucao="furo centrado 45 mm"),
    dict(cod="PN-09", tipo="dreno de condensado DN25", dn=25, onde="montante",
         de="evaporadoras", para="jardim", solucao="furo centrado com caimento "
         "minimo de 2 %; sifao antes da descida"),
]
ENTREFORRO = PISO_A_PISO - PE_DIREITO      # 400 mm
SHAFT = dict(w=300, h=300, revestimento="2 chapas RU + la de rocha 50 mm",
             obs="inspecionavel por alcapao a cada pavimento")


# =========================================================================
# PAGINACAO — piso e revestimento. Paginar no projeto e decidir onde fica o
# corte; nao paginar e deixar o corte aparecer no lugar mais visivel.
#
# Criterio adotado: partir do vao principal do ambiente (a porta ou a janela
# de maior destaque) e jogar o recorte para o canto menos visto. Recorte menor
# que 1/3 da peca e proibido: descola e quebra.
# =========================================================================
PECA_PISO = dict(l=900, c=900, junta=2, tipo="porcelanato retificado 900 x 900")
PECA_PAREDE = dict(l=300, c=600, junta=2, tipo="ceramico retificado 300 x 600")
RECORTE_MIN = 1 / 3          # abaixo disso o recorte desequilibra a leitura
RECORTE_CRITICO = 1 / 5      # abaixo disso descola e quebra

# ZONAS de paginacao: ambientes que nao tem parede entre si recebem UMA origem
# so. Paginar cada modulo a partir do proprio canto e o erro que produz a
# "costura" visivel no meio da sala integrada — duas malhas de junta que se
# encontram desalinhadas no exato ponto onde nao ha parede para disfarcar.
ZONAS_PAGINACAO = [
    dict(cod="ZP-1", peca="piso", origem=(5_400, 13_200),
         ambientes=["T-SOC", "T-COR", "T-GOU", "T-COZ"],
         obs="fita social inteira em uma malha: origem no eixo da porta do hall, "
             "recorte jogado para a parede sul da cozinha, atras da bancada"),
    dict(cod="ZP-2", peca="piso", origem=(7_800, 19_200), ambientes=["S-MAS"],
         obs="origem no eixo da porta da suite"),
    dict(cod="ZP-3", peca="piso", origem=(2_400, 13_200),
         ambientes=["S-S02", "S-S03"],
         obs="suites 02 e 03 na mesma malha: a parede entre elas e divisoria, mas "
             "o hall as percorre e a junta aparece na soleira"),
    # Zona de PAREDE nao compartilha origem: revestimento vertical e uma
    # superficie por parede, e a junta de uma parede nao continua na outra. Cada
    # ambiente pagina do proprio canto e joga o recorte para o canto menos visto.
    # O que importa na parede e a FIADA DO TOPO: ela e a que se ve na altura dos
    # olhos. Dai a altura de revestimento ser escolhida como multiplo da peca.
    dict(cod="ZP-7", peca="piso", origem=(12_600, 16_800), ambientes=["S-LOU"],
         obs="o lounge tem porta e nao e integrado a nada: pagina do proprio "
             "canto, com o recorte atras do sofa"),
    # R45 — os tres banhos do superior entram AQUI, e nao numa zona nova: a
    # altura de revestimento de um banho e uma decisao so, ja tomada para o
    # T-BWC, e duplica-la seria criar a segunda fonte que este projeto passou
    # quarenta revisoes eliminando. Eles sao subdivisao das suites, e por isso
    # nunca apareceram em lista nenhuma de ambiente.
    dict(cod="ZP-4", peca="parede", altura=2_400,
         ambientes=["T-BWC", "S-S02/BANHO", "S-S03/BANHO", "S-MAS/BANHO"],
         obs="ate o forro rebaixado de 2.400 (que ja existe para a exaustao): "
             "3 fiadas inteiras e a do topo com 594 de 600 — imperceptivel"),
    dict(cod="ZP-5", peca="parede", altura=1_800,
         ambientes=["T-LAV", "T-DEP"],
         obs="meia parede de 1.800 mm atras do tanque, das maquinas e das "
             "prateleiras: 3 fiadas, a do topo com 596 de 600"),
    dict(cod="ZP-6", peca="monolitico", origem=(2_400, 13_200),
         ambientes=["T-OFI", "T-GAR"],
         obs="piso cimenticio polido de alta resistencia: sem paginacao ceramica"),
]


def zona_de(amb_cod: str) -> dict | None:
    return next((z for z in ZONAS_PAGINACAO if amb_cod in z["ambientes"]), None)


def paginar(amb_cod: str) -> dict:
    """Layout de peca no ambiente a partir da origem da sua ZONA.

    Devolve, por eixo, quantas pecas inteiras cabem e o recorte em CADA ponta —
    porque a origem raramente coincide com a borda do ambiente, e o recorte do
    lado de ca tambem existe.
    """
    amb = next((a for a in TERREO + SUPERIOR if a.cod == amb_cod), None)
    if amb is None and "/" in amb_cod:
        # R45 — a subdivisao e ambiente para efeito de paginacao: ela tem
        # retangulo proprio, e e nela que a peca assenta. Enquanto so o comodo
        # inteiro era paginavel, os tres banhos do superior nao tinham
        # revestimento paginado em lugar nenhum.
        pai_cod, nome = amb_cod.split("/", 1)
        d = next((x for x in SUBDIVISOES
                  if x["pai"] == pai_cod and x["nome"] == nome), None)
        if d is not None:
            amb = Amb(amb_cod, nome, d["x"], d["y"], d["w"], d["h"],
                      pav=pai_cod[0], molhado=bool(d.get("molhado")))
    z = zona_de(amb_cod)
    if amb is None or z is None or z["peca"] == "monolitico":
        return {}
    peca = PECA_PISO if z["peca"] == "piso" else PECA_PAREDE
    res = {"zona": z["cod"], "peca": z["peca"]}
    # piso: uma malha para a zona toda. parede: uma malha por ambiente.
    orig = z["origem"] if z["peca"] == "piso" else (amb.x, amb.y)
    for eixo, dim, o, ini, fim in (
            ("x", peca["l"], orig[0], amb.x, amb.x + amb.w),
            ("y", peca["c"], orig[1], amb.y, amb.y + amb.h)):
        passo = dim + peca["junta"]
        # a malha e infinita a partir da origem, nos dois sentidos
        k_ini = math.floor((ini - o) / passo)
        k_fim = math.ceil((fim - o) / passo)
        borda_ini = o + k_ini * passo
        borda_fim = o + k_fim * passo
        rec_ini = int(round(ini - borda_ini))
        rec_fim = int(round(borda_fim - fim))
        rec_ini = 0 if rec_ini == 0 else dim - rec_ini
        rec_fim = 0 if rec_fim == 0 else dim - rec_fim
        inteiras = (k_fim - k_ini) - sum(1 for r in (rec_ini, rec_fim) if r)
        piores = [r for r in (rec_ini, rec_fim) if r]
        res[eixo] = dict(inteiras=inteiras, recorte_ini=rec_ini, recorte_fim=rec_fim,
                         pior=min(piores) if piores else dim,
                         ok=not piores or min(piores) >= dim * RECORTE_MIN,
                         critico=bool(piores) and min(piores) < dim * RECORTE_CRITICO)
    if z["peca"] == "parede":
        dim = PECA_PAREDE["c"]
        passo = dim + PECA_PAREDE["junta"]
        n = int(z["altura"] // passo)
        topo = z["altura"] - n * passo
        res["altura"] = dict(altura=z["altura"], fiadas=n, fiada_topo=int(topo),
                             ok=(topo == 0 or topo >= dim * 0.5))
    return res


def alturas_revestimento() -> dict[str, int]:
    """Altura de revestimento por ambiente, a partir das zonas de parede."""
    return {c: z["altura"] for z in ZONAS_PAGINACAO if z["peca"] == "parede"
            for c in z["ambientes"]}


# =========================================================================
# ESCADA — verificacao executiva
# 18 espelhos de 166,67 mm e piso de 300 mm. Blondel: 2h + p = 633,3 mm,
# dentro da faixa 600-650 recomendada. Altura livre e o que ninguem verifica.
# =========================================================================
ESCADA_EXEC = dict(
    lances=2, espelhos_lance=9, patamar_l=1_000, patamar_c=2_200,
    altura_livre_min=2_100,        # NBR 9077
    guarda_corpo=1_100,            # NBR 14718 para pavimento elevado
    corrimao_h=(920, 700),         # duas alturas: adulto e crianca (NBR 9050)
    bocel=0, espelho_fechado=True,
    estrutura="dois perfis U 200 laterais com degraus em chapa dobrada 3 mm",
    acabamento="degrau em porcelanato 900 x 300 com faixa antiderrapante",
)

# =========================================================================
# BANCADAS E PONTOS DE AGUA — declarados no MODELO, nao so no desenho.
# O que nao esta no modelo a auditoria nao verifica.
#
# REVISAO: a cozinha e o gourmet sao um unico ambiente integrado. Manter duas
# bancadas molhadas grandes a 6 m de distancia, mais uma cuba na peninsula,
# e triplicar o ponto de agua dentro da mesma sala.
# =========================================================================
BANCADAS = [
    # R08 — a cuba vai para o FUNDO da bancada, sob a janela e de frente para a
    # cortina: quem lava louca olha para a piscina. Era o unico posto de trabalho
    # fixo da casa que ainda ficava de costas para a vista.
    dict(cod="BC-01", amb="T-COZ", x=2_500, y=23_100, w=600, h=2_100,
         prof=600, cubas=1, cooktop=False, tipo="granito",
         uso="cuba e preparo, sob a janela e de frente para a cortina"),
    # a coccao migrou da parede de servico para a mesma parede da cuba: um unico
    # plano de trabalho continuo de 3.900 mm, com a coifa subindo pela fachada
    # sul e o duto fora de qualquer montante
    dict(cod="BC-02", amb="T-COZ", x=2_500, y=21_300, w=600, h=1_800,
         prof=600, cubas=0, cooktop=True, tipo="granito",
         uso="coccao — cooktop e apoio, junto a despensa"),
    # R10 — era uma ILHA chamada de peninsula: atravessava a fronteira
    # cozinha/gourmet (x = 5.400) com 600 mm de cada lado e nao encostava em
    # nada, a 1.700 mm da bancada de trabalho. Ficava exatamente na area de
    # transicao, que e o unico lugar onde ela NAO deveria estar.
    # Agora e peninsula de verdade: encostada na ponta da fila da cozinha e
    # avancando 1.500 mm para DENTRO do gourmet, perpendicular a fronteira.
    # Custa 600 mm da linha de fronteira em vez de 2.400, deixa 4.500 dos
    # 7.200 mm de fronteira abertos, e para 600 mm antes do eixo visual da
    # piscina (x = 7.500), que nao pode ser tocado.
    dict(cod="BC-03", amb="T-GOU", x=5_400, y=23_400, w=1_500, h=600,
         prof=600, cubas=0, cooktop=False, tipo="granito",
         uso="peninsula SECA: passa-pratos da cozinha, apoio de servico do "
             "gourmet e refeicao rapida — banquetas pelo lado do gourmet"),
    # R07 — a bancada estava encostada na parede do FUNDO, ocupando 3.900 dos
    # 4.200 mm que deveriam abrir para a piscina: era ela, e nao a esquadria, o
    # que tapava a vista. Vai para a parede LESTE, de costas para o patio, onde
    # a coifa sobe pela face tecnica e o cozinheiro fica de frente para a agua.
    # R10 — o cooktop do gourmet SAIU. Havia duas bocas de coccao a 6,7 m uma da
    # outra dentro do mesmo ambiente integrado, e o briefing ja dizia
    # "segunda_cozinha_completa_no_gourmet: false". Bancada de 3,60 m com cooktop
    # e cuba E uma segunda cozinha, por mais que a legenda diga o contrario.
    # O gourmet cozinha na CHURRASQUEIRA; o cooktop e da cozinha, a 6,7 m dali,
    # na mesma sala e sem parede no caminho. A cuba de apoio fica: enxaguar mao e
    # utensilio junto a grelha e uso real, e evita atravessar a sala pingando.
    dict(cod="BC-04", amb="T-GOU", x=9_000, y=19_800, w=600, h=3_600,
         prof=600, cubas=1, cooktop=False, ignicao=True, tipo="granito",
         cuba_apoio=True,
         uso="churrasqueira e cuba de apoio (400 x 340) — o gourmet assa, nao "
             "cozinha; a coccao e uma so, na cozinha"),
    dict(cod="BC-05", amb="T-LAV", x=9_750, y=19_350, w=600, h=550,
         prof=600, cubas=1, cooktop=False, tipo="tanque",
         uso="tanque de lavanderia"),
    dict(cod="BC-06", amb="T-OFI", x=2_500, y=13_500, w=600, h=2_400,
         prof=600, cubas=0, cooktop=False, tipo="granito",
         uso="bancada de trabalho da oficina, sob a janela — granito em vez de "
             "MDF: a oficina e o ambiente de maior abrasao e umidade da casa, e "
             "unificar o material derruba uma familia do quadro de compras"),
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
    # R09 — seguem o banho, que passou a cair sobre a lavanderia
    dict(cod="LC-10", amb="S-MAS", tipo="vaso",      x=9_200,  y=19_400, w=400, h=650),
    dict(cod="LC-11", amb="S-MAS", tipo="lavatorio", x=9_900,  y=19_300, w=1_800, h=500),
    dict(cod="LC-12", amb="S-MAS", tipo="box",       x=10_300, y=20_700, w=1_400, h=1_400),
    # lavanderia
    dict(cod="LC-13", amb="T-LAV", tipo="tanque",    x=9_750, y=19_350, w=600, h=550),
]

EQUIPAMENTOS = [
    dict(cod="EQ-01", amb="T-COZ", tipo="geladeira", x=4_650, y=22_500, w=750, h=900,
         abertura=900, uso="nicho de 900 mm; encostada na despensa, formando uma zona de estoque unica junto a porta de servico"),
    # R09 — quatro equipamentos apareciam no quadro de cargas eletricas e NAO
    # tinham posicao no modelo. Sem posicao nao ha verificacao de circulacao, de
    # tomada, de sifao nem de porta batendo neles. Locados:
    dict(cod="EQ-04", amb="T-COZ", tipo="lava-loucas", x=2_500, y=23_100, w=600,
         h=600, abertura=600, uso="embutido sob a bancada, ao lado da cuba: a "
         "mangueira de descarga usa o mesmo sifao"),
    dict(cod="EQ-05", amb="T-COZ", tipo="lixo", x=2_500, y=24_600, w=600, h=450,
         abertura=450, uso="cesto duplo em gaveta sob a cuba — seco e organico"),
    dict(cod="EQ-06", amb="T-COZ", tipo="forno", x=4_800, y=21_300, w=600, h=600,
         abertura=600, uso="torre quente junto a despensa, fora do triangulo de "
         "trabalho e fora da circulacao da cuba"),
    dict(cod="EQ-07", amb="T-COZ", tipo="micro-ondas", x=4_800, y=21_900, w=600,
         h=600, abertura=600, uso="na mesma torre do forno, a 1.400 mm do piso"),
    dict(cod="EQ-02", amb="T-LAV", tipo="lavadora",  x=9_750, y=20_050, w=600, h=600,
         abertura=600, uso="base antivibratoria"),
    dict(cod="EQ-03", amb="T-LAV", tipo="secadora",  x=9_750, y=20_750, w=600, h=600,
         abertura=600, uso="base antivibratoria"),
]

ARMARIOS = [
    # o triangulo sob o segundo lance tem altura livre entre 0 e 1.500 mm: nao e
    # circulacao nem espaco morto, e armario. Declarado para a auditoria saber.
    dict(cod="AR-05", amb="T-COR", tipo="prateleiras", x=10_800, y=14_400,
         w=1_200, h=2_100, sob_escada=True),
    # a despensa de 3,60 m2 virou parede de armarios de 600 mm de profundidade:
    # 1,80 m de frente com prateleira funda rende mais que 3,00 m de prateleira
    # rasa, e devolve a cozinha a parede do fundo, que e o que interessa aqui
    dict(cod="AR-06", amb="T-COZ", tipo="prateleiras", x=2_400, y=19_200,
         w=300, h=2_100),
    dict(cod="AR-07", amb="T-COZ", tipo="prateleiras", x=3_900, y=19_200,
         w=300, h=2_100),
    # torre quente: marcenaria alta de 600 mm que abriga forno e micro-ondas e
    # alinha a face leste da cozinha em x = 5.400, junto com a geladeira
    # R10 — a torre tem 750 mm de profundidade, nao 600: e a profundidade da
    # geladeira que vem a seguir na fila. Forno e micro-ondas embutidos tem
    # ~560 mm e montam rentes a frente do armario, entao o alinhamento sai de
    # graca. Alinhar a frente de uma fila e o que separa marcenaria de movel.
    dict(cod="AR-08", amb="T-COZ", tipo="armario alto", x=4_650, y=21_300,
         w=750, h=1_200),
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
         x=17_200, y=24_000, w=1_200, h=800,
         obs="NBR 13523: min 1,5 m de qualquer vao e 3,0 m de fonte de ignicao"),
    # ---- eletrica e dados
    dict(cod="TC-05", nome="Quadro geral 36 modulos", zona="INT", amb="T-GAR",
         x=8_100, y=9_000, w=300, h=800,
         obs="parede da garagem junto ao hall; altura de 1.000 a 1.800 mm"),
    dict(cod="TC-06", nome="Quadro superior 24 modulos", zona="INT", amb="S-HAL",
         x=9_800, y=18_600, w=300, h=600, obs="hall do pavimento superior"),
    dict(cod="TC-07", nome="Rack de dados e CFTV", zona="INT", amb="T-GAR",
         x=8_000, y=10_200, w=400, h=600,
         obs="8 cameras, 3 access points, 1 videoporteiro; ventilacao passiva"),
    dict(cod="TC-08", nome="Medidores de agua e energia", zona="TEST",
         x=17_000, y=600, w=800, h=600,
         obs="na testada, leitura pela via sem entrar no lote"),
    # ---- climatizacao: DOIS nichos, por comprimento de linha
    # R47 — o nome e a obs NAO contam mais unidades. Diziam "3 posicoes" e
    # "2 ativas + 1 reservada" enquanto a lista de CLIMATIZACAO mandava CINCO
    # equipamentos para ca. Prosa nao roda e nao reprova: envelhece em silencio
    # enquanto a lista muda. A ocupacao agora e derivada por
    # instalacoes.ocupacao_de_nicho() e conferida contra estes 6.600 mm — cabem
    # as cinco com 1.050 mm de sobra.
    dict(cod="TC-09", nome="Nicho de condensadoras NORTE", zona="FT-N",
         x=17_200, y=13_200, w=800, h=6_600,
         obs="comprimento util de 6.600 mm; base de 200 mm, painel ripado "
             "ventilado h=1.800, descarga para a divisa norte com 2.200 mm "
             "livres. A ocupacao vem da lista de CLIMATIZACAO, nao deste texto"),
    dict(cod="TC-10", nome="Nicho de condensadoras SUL", zona="REC-S",
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
    dict(cod="TC-13", casa_maquinas=True, nome="Casa de maquinas da piscina", zona="FT-N",
         x=17_000, y=29_400, w=1_500, h=2_000,
         obs="em pe na lateral tecnica (YAML): bomba de velocidade variavel, "
             "filtro, quadro estanque e bypass de aquecimento; succao de 6,2 m"),
    dict(cod="TC-15", nome="Deposito externo de apoio a piscina", zona="FT-N",
         x=17_000, y=26_400, w=1_500, h=2_000,
         obs="boias, materiais de limpeza, cadeiras e itens de manutencao — "
             "tira do deposito interno o que e de area externa"),
    dict(cod="TC-16", nome="Ducha externa", zona="FT-N",
         x=16_800, y=31_800, w=800, h=1_000,
         obs="na borda da faixa tecnica junto ao deck: ramal curto, ralo proprio "
             "e nenhum volume solto no meio do jardim"),
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
    dict(amb="S-LOU", nicho="TC-09", pessoas=2, equip=1, capacidade=9_000,
         tipo="split hi-wall inverter",
         obs="7,20 m2 com TV e frigobar. O YAML pede para nao inventar sistema "
             "complexo para 6 m2 — um hi-wall de 9.000 e o oposto de complexo"),
    dict(amb="S-MAS", nicho="TC-09", pessoas=2, equip=1, capacidade=9_000,
         compartimento="OFFICE", area_m2=5.40, vidro_m2=1.44,
         tipo="split hi-wall inverter",
         obs="o office e fechavel, entao tem carga propria; o closet NAO recebe "
             "equipamento, recebe grelha de transferencia do dormitorio"),
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
                  ventilador: bool = False, duto: bool = False,
                  area_m2: float | None = None,
                  vidro_m2: float | None = None) -> int:
    """Carga termica em BTU/h, arredondada para cima em 100.

    'mais' soma ambientes que formam um unico volume com o principal: o core
    nao tem parede que o separe do estar, logo nao tem carga propria separada.
    """
    if area_m2 is not None:
        area, vidro = area_m2, (vidro_m2 or 0.0)
    else:
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


def climatizados() -> list[tuple[str, int, int]]:
    """(rotulo, carga, capacidade) de cada equipamento, reserva inclusa."""
    out = []
    for c in CLIMATIZACAO:
        rot = c["amb"] + ("/" + c["compartimento"] if c.get("compartimento") else "")
        cg = carga_termica(c["amb"], c["pessoas"], c["equip"], c.get("mais"),
                           c.get("conta_ventilador", False), c.get("duto", False),
                           c.get("area_m2"), c.get("vidro_m2"))
        out.append((rot, cg, c["capacidade"]))
    return out


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
         obs="coifa de parede sobre BC-02, duto subindo pela fachada sul"),
    dict(cod="EX-03", amb="T-BWC", fonte="banho social", vazao_m3h=90, dn=100),
    dict(cod="EX-04", amb="T-LAV", fonte="lavanderia", vazao_m3h=120, dn=100,
         obs="retira umidade da secadora e do tanque"),
    dict(cod="EX-05", amb="S-MAS", fonte="banho master", vazao_m3h=120, dn=100),
    # closet fechado em cidade com 80 % de umidade relativa e incubadora de
    # mofo: 40 m3/h continuos custam 8 W e salvam a roupa
    dict(cod="EX-06", amb="S-MAS", fonte="closet master", vazao_m3h=40, dn=75,
         obs="exaustao continua de baixa vazao, com grelha de transferencia"),
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


# =========================================================================
# ETAPA 3 — COORDENACAO DE INSTALACOES
# =========================================================================

# ------------------------------------------------------------- HIDRAULICA
# NBR 5626: metodo dos pesos relativos. Q = 0,30 . raiz(soma dos pesos).
# O peso do chuveiro ELETRICO e 0,1, nao 0,4 — ele trabalha com 3 L/min, nao
# com 12. Essa diferenca sozinha derruba o diametro do ramal de 32 para 25 mm
# em toda a casa, e e a consequencia hidraulica da decisao ja tomada no
# aquecimento. Decisao em um sistema reaparece como economia em outro.
PESOS_NBR5626 = {
    "vaso": 0.30,          # com caixa acoplada
    "lavatorio": 0.30,
    "box": 0.10,           # chuveiro ELETRICO (3 L/min)
    "tanque": 0.70,
    "pia": 0.70,
    "lavadora": 1.00,
    "ducha_externa": 0.40,
}
# UHC — unidades Hunter de contribuicao (NBR 8160)
UHC = {"vaso": 6, "lavatorio": 1, "box": 2, "tanque": 3, "pia": 3, "lavadora": 3}
# diametro interno util (mm) de PVC soldavel e vazao maxima a 3 m/s
TUBOS_AGUA = ((25, 21.6), (32, 27.8), (40, 35.2), (50, 44.0), (60, 53.4))
VEL_MAX_AGUA = 3.0          # limite normativo (NBR 5626)
VEL_CONFORTO = 2.0          # limite de ruido: acima disso o tubo assobia e
                            # o golpe de ariete fica audivel na casa toda
# ramal de esgoto por UHC acumulada (NBR 8160)
RAMAIS_ESGOTO = ((40, 3), (50, 6), (75, 20), (100, 160))


def pecas_hidraulicas() -> list[dict]:
    """Todas as pecas de utilizacao do modelo, com peso e UHC."""
    out = []
    for lc in LOUCAS:
        out.append(dict(cod=lc["cod"], amb=lc["amb"], tipo=lc["tipo"],
                        x=lc["x"], y=lc["y"],
                        peso=PESOS_NBR5626.get(lc["tipo"], 0.3),
                        uhc=UHC.get(lc["tipo"], 1),
                        quente=lc["tipo"] == "box"))
    for b in BANCADAS:
        if not b["cubas"]:
            continue
        out.append(dict(cod=b["cod"], amb=b["amb"], tipo="pia",
                        x=b["x"], y=b["y"], peso=PESOS_NBR5626["pia"],
                        uhc=UHC["pia"], quente=False))
    for e in EQUIPAMENTOS:
        if e["tipo"] != "lavadora":
            continue
        out.append(dict(cod=e["cod"], amb=e["amb"], tipo="lavadora",
                        x=e["x"], y=e["y"], peso=PESOS_NBR5626["lavadora"],
                        uhc=UHC["lavadora"], quente=False))
    out.append(dict(cod="DX-01", amb="T-DKP", tipo="ducha_externa",
                    x=DECK["x"] + 300, y=DECK["y"] + 300,
                    peso=PESOS_NBR5626["ducha_externa"], uhc=2, quente=False))
    return out


def vazao_ls(pesos: float) -> float:
    return round(0.30 * math.sqrt(pesos), 3)


def dn_agua(q_ls: float, conforto: bool = False) -> int:
    """Diametro pelo limite de velocidade. conforto=True usa 2,0 m/s.

    O alimentador e as prumadas usam o limite de conforto: 2,17 m/s em DN25
    atende a norma e produz uma casa que assobia quando alguem abre a torneira.
    Subir para DN32 custa alguns metros de tubo.
    """
    lim = VEL_CONFORTO if conforto else VEL_MAX_AGUA
    for dn, di in TUBOS_AGUA:
        area_m2 = math.pi * (di / 1_000) ** 2 / 4
        if (q_ls / 1_000) / area_m2 <= lim:
            return dn
    return TUBOS_AGUA[-1][0]


def velocidade_ms(q_ls: float, dn: int) -> float:
    di = next(d for n, d in TUBOS_AGUA if n == dn)
    return round((q_ls / 1_000) / (math.pi * (di / 1_000) ** 2 / 4), 2)


def dn_esgoto(uhc: int) -> int:
    for dn, lim in RAMAIS_ESGOTO:
        if uhc <= lim:
            return dn
    return RAMAIS_ESGOTO[-1][0]


def prumadas_hidraulicas() -> list[dict]:
    """Ramais por pavimento e por grupo, com vazao e diametro."""
    pecas = pecas_hidraulicas()
    grupos = {}
    for p in pecas:
        pav = "S" if p["amb"].startswith("S-") else "T"
        grupos.setdefault(pav, []).append(p)
    out = []
    for pav, lst in sorted(grupos.items()):
        pesos = sum(p["peso"] for p in lst)
        uhc = sum(p["uhc"] for p in lst)
        q = vazao_ls(pesos)
        dn = dn_agua(q, conforto=True)
        out.append(dict(pav=pav, pecas=len(lst), pesos=round(pesos, 2), q=q,
                        dn_agua=dn, v=velocidade_ms(q, dn), uhc=uhc,
                        dn_esgoto=dn_esgoto(uhc), pressurizado=pav == "S"))
    pesos = sum(p["peso"] for p in pecas)
    uhc = sum(p["uhc"] for p in pecas)
    q = vazao_ls(pesos)
    dn = dn_agua(q, conforto=True)
    out.append(dict(pav="GERAL", pecas=len(pecas), pesos=round(pesos, 2), q=q,
                    dn_agua=dn, v=velocidade_ms(q, dn), uhc=uhc,
                    dn_esgoto=dn_esgoto(uhc), pressurizado=False))
    return out


# --------------------------------------------------------------- ELETRICA
# NBR 5410. O ponto onde a norma precisa ser lida com cabeca local:
#
# As tabelas de fator de demanda foram construidas sobre media nacional, onde o
# ar condicionado e intermitente. Em Manaus ele e CONTINUO — os cinco
# equipamentos funcionam juntos todas as tardes do ano. Aplicar fd de 0,7 ao ar
# condicionado aqui nao e economia, e subdimensionamento: o ramal de entrada
# aquece, o disjuntor geral desliga na hora de maior calor, e o proprietario
# troca o disjuntor por um maior em vez do cabo. Adotado fd = 1,00 para
# climatizacao, com justificativa escrita.
TENSAO = dict(fn=127, ff=220, fases=3, esquema="trifasico 127/220 V (H)")
ILUM_VA_BASE = 100          # primeiros 6 m2
ILUM_VA_EXTRA = 100         # a cada 4 m2 adicionais
TUG_VA_SECA = 100
TUG_VA_MOLHADA = 600        # primeiras 3 tomadas de area molhada
TUG_PERIM_SECA = 5_000      # 1 tomada a cada 5 m de perimetro
TUG_PERIM_MOLHADA = 3_500
MOLHADAS_ELETRICA = {"T-COZ", "T-LAV", "T-BWC", "T-DEP", "T-GOU"}

CARGAS_ESPECIAIS = [
    dict(cod="TUE-1", desc="Chuveiro eletrico suite master", va=4_500, v=220,
         grupo="aquecimento", fd=0.75),
    dict(cod="TUE-2", desc="Chuveiro eletrico suite 02", va=4_500, v=220,
         grupo="aquecimento", fd=0.75),
    dict(cod="TUE-3", desc="Chuveiro eletrico suite 03", va=4_500, v=220,
         grupo="aquecimento", fd=0.75),
    dict(cod="TUE-4", desc="Chuveiro eletrico banho social", va=4_500, v=220,
         grupo="aquecimento", fd=0.75),
    dict(cod="TUE-5", desc="Split duto 30.000 BTU (zona social)", va=2_300, v=220,
         grupo="climatizacao", fd=1.00),
    dict(cod="TUE-6", desc="Split 18.000 BTU suite master", va=1_400, v=220,
         grupo="climatizacao", fd=1.00),
    dict(cod="TUE-7", desc="Split 18.000 BTU suite 02", va=1_400, v=220,
         grupo="climatizacao", fd=1.00),
    dict(cod="TUE-8", desc="Split 18.000 BTU suite 03", va=1_400, v=220,
         grupo="climatizacao", fd=1.00),
    dict(cod="TUE-9", desc="Split 18.000 BTU quarto reversivel", va=1_400, v=220,
         grupo="climatizacao", fd=1.00),
    dict(cod="TUE-23", desc="Split 9.000 BTU mini lounge", va=800, v=220,
         grupo="climatizacao", fd=1.00),
    dict(cod="TUE-24", desc="Split 9.000 BTU office da master", va=800, v=220,
         grupo="climatizacao", fd=1.00),
    dict(cod="TUE-10", desc="Secadora de roupa", va=2_700, v=220,
         grupo="servico", fd=0.50),
    dict(cod="TUE-11", desc="Lavadora de roupa", va=1_000, v=127,
         grupo="servico", fd=0.50),
    dict(cod="TUE-12", desc="Lava-loucas", va=1_500, v=127, grupo="servico", fd=0.50),
    dict(cod="TUE-13", desc="Forno eletrico embutido", va=3_000, v=220,
         grupo="cozinha", fd=0.60),
    dict(cod="TUE-14", desc="Micro-ondas", va=1_500, v=127, grupo="cozinha", fd=0.60),
    dict(cod="TUE-15", desc="Motobomba de recalque (TC-02)", va=500, v=220,
         grupo="motores", fd=1.00),
    dict(cod="TUE-16", desc="Pressurizador do superior (TC-14)", va=500, v=220,
         grupo="motores", fd=1.00),
    dict(cod="TUE-17", desc="Bomba e filtro da piscina (TC-13)", va=500, v=220,
         grupo="motores", fd=0.80),
    dict(cod="TUE-18", desc="Ventiladores de teto (10 un.)", va=1_000, v=127,
         grupo="ventilacao", fd=0.70),
    dict(cod="TUE-19", desc="Exaustores e coifas", va=450, v=127,
         grupo="ventilacao", fd=0.60),
    dict(cod="TUE-20", desc="Portao automatico", va=500, v=220, grupo="diversos", fd=0.30),
    dict(cod="TUE-21", desc="Rack, CFTV e rede", va=300, v=127, grupo="diversos", fd=1.00),
    # YAML: EV_futuro = eletroduto e espaco de quadro reservados, sem carga hoje.
    # Um carregador de 7,4 kW entra depois como TUE de 32 A; reservar o
    # eletroduto de 32 mm e quatro modulos custa quase nada agora e evita quebrar
    # piso de garagem depois.
    dict(cod="TUE-22", desc="Carregador de veiculo eletrico (INFRAESTRUTURA)",
         va=7_400, v=220, grupo="reserva", fd=0.00, reserva=True),
]
EV_RESERVA = dict(eletroduto="32 mm do quadro geral ate a parede da garagem",
                  modulos_quadro=4, disjuntor_futuro=32, secao_futura=6.0,
                  ponto=(8_100, 8_400), obs="carregador monofasico 220 V, 7,4 kW")
# fator de demanda de iluminacao e TUG por faixa de potencia (NBR 5410)
FD_ILUM_TUG = ((1_000, 0.86), (2_000, 0.75), (3_000, 0.66), (4_000, 0.59),
               (5_000, 0.52), (6_000, 0.45), (7_000, 0.40), (8_000, 0.35),
               (9_000, 0.31), (10_000, 0.27), (10 ** 9, 0.24))


def _perimetro(a: Amb) -> int:
    return 2 * (a.w + a.h)


def previsao_iluminacao_tug() -> list[dict]:
    """Previsao de carga por ambiente conforme NBR 5410 9.5.2."""
    out = []
    for a in TERREO + SUPERIOR:
        area = a.area_mod
        ilum = ILUM_VA_BASE + max(0, math.ceil((area - 6) / 4)) * ILUM_VA_EXTRA \
            if area > 6 else ILUM_VA_BASE
        molhada = a.cod in MOLHADAS_ELETRICA
        passo = TUG_PERIM_MOLHADA if molhada else TUG_PERIM_SECA
        n = max(1, math.ceil(_perimetro(a) / passo))
        if molhada:
            va = min(n, 3) * TUG_VA_MOLHADA + max(0, n - 3) * TUG_VA_SECA
        else:
            va = n * TUG_VA_SECA
        out.append(dict(amb=a.cod, nome=a.nome, area=area, perim=_perimetro(a),
                        ilum_va=ilum, tugs=n, tug_va=va, molhada=molhada))
    return out


def fd_ilum_tug(total_va: float) -> float:
    for lim, f in FD_ILUM_TUG:
        if total_va <= lim:
            return f
    return FD_ILUM_TUG[-1][1]


def demanda_eletrica() -> dict:
    """Carga instalada e demanda provavel, grupo por grupo."""
    prev = previsao_iluminacao_tug()
    ilum = sum(p["ilum_va"] for p in prev)
    tug = sum(p["tug_va"] for p in prev)
    base = ilum + tug
    fd_base = fd_ilum_tug(base)
    grupos = {}
    for c in CARGAS_ESPECIAIS:
        g = grupos.setdefault(c["grupo"], dict(instalada=0, demanda=0, fd=c["fd"]))
        g["instalada"] += c["va"]
        g["demanda"] += c["va"] * c["fd"]
        g["fd"] = round(g["demanda"] / g["instalada"], 2)
    instalada = base + sum(g["instalada"] for g in grupos.values())
    demanda = base * fd_base + sum(g["demanda"] for g in grupos.values())
    i_a = demanda / (math.sqrt(3) * TENSAO["ff"])
    return dict(ilum_va=ilum, tug_va=tug, base_va=base, fd_base=fd_base,
                grupos=grupos, instalada_va=int(instalada),
                demanda_va=int(demanda), corrente_a=round(i_a, 1),
                padrao_a=next(p for p in (40, 50, 63, 80, 100, 125) if p >= i_a),
                secao_mm2=next(s for s, lim in ((10, 50), (16, 68), (25, 89),
                                                (35, 111), (50, 134))
                               if lim >= i_a))


# --------------------------------------------- LINHAS FRIGORIGENAS E DRENOS
BITOLA_FRIG = {9_000: ("1/4", "3/8"), 12_000: ("1/4", "1/2"),
               18_000: ("1/4", "1/2"), 24_000: ("3/8", "5/8"),
               30_000: ("3/8", "5/8"), 36_000: ("3/8", "5/8")}
DRENO_DN = 25
DRENO_CAIMENTO = 0.02


def linhas_frigorigenas() -> list[dict]:
    """Uma linha por equipamento, com percurso, bitola, dreno e carga extra."""
    out = []
    for c in CLIMATIZACAO:
        nicho = next(t for t in TECNICOS if t["cod"] == c["nicho"])
        amb = next((a for a in TERREO + SUPERIOR if a.cod == c["amb"]), None)
        if amb is None:
            continue
        dx = max(nicho["x"] - (amb.x + amb.w), amb.x - (nicho["x"] + nicho["w"]), 0)
        dy = max(nicho["y"] - (amb.y + amb.h), amb.y - (nicho["y"] + nicho["h"]), 0)
        subida = (PISO_A_PISO + 600) if amb.pav == "S" else PE_DIREITO
        comp = dx + dy + subida + 1_500
        suc, liq = BITOLA_FRIG[c["capacidade"]]
        rot = c["amb"] + ("/" + c["compartimento"] if c.get("compartimento") else "")
        out.append(dict(cod=f"LF-{rot}", amb=c["amb"], nicho=c["nicho"],
                        capacidade=c["capacidade"], comp=comp,
                        horizontal=dx + dy, subida=subida,
                        suc=suc, liq=liq, dreno=DRENO_DN,
                        carga_extra_g=max(0, int((comp - 7_500) / 1_000) * 20),
                        reserva=bool(c.get("reserva"))))
    return out


# ------------------------------------------------------ DRENAGEM E RALOS
RALOS = [
    dict(cod="RL-01", amb="T-BWC", tipo="ralo linear 600", x=10_350, y=10_850, dn=50),
    dict(cod="RL-02", amb="S-S02", tipo="ralo linear 600", x=2_550, y=14_500, dn=50),
    dict(cod="RL-03", amb="S-S03", tipo="ralo linear 600", x=2_550, y=19_300, dn=50),
    dict(cod="RL-04", amb="S-MAS", tipo="ralo linear 900", x=11_550, y=20_900, dn=50),
    dict(cod="RL-05", amb="T-LAV", tipo="ralo sifonado 150", x=10_800, y=20_400, dn=50),
    dict(cod="RL-06", amb="T-COZ", tipo="ralo sifonado 100", x=3_600, y=22_200, dn=50),
    dict(cod="RL-07", amb="T-GAR", tipo="ralo linear 6.000", x=2_400, y=7_300, dn=75),
    dict(cod="RL-08", amb="T-DKP", tipo="canaleta com grelha", x=3_700, y=29_500, dn=75),
    # o trilho inferior da cortina de vidro e o ponto de entrada de agua mais
    # provavel da casa: 7,20 m de fresta rente ao piso, voltada para o vento de
    # chuva. Ralo linear continuo sob ele, com o trilho drenando para dentro do
    # canal e nao para o piso interno.
    dict(cod="RL-11", amb="T-ALP", tipo="ralo linear 7.200 sob a cortina",
         x=2_400, y=26_450, dn=75),
    # R45 — o gourmet e area molhada declarada, tem cuba (BC-04) e nao tinha
    # ralo. Nao e detalhe: ele e contiguo a varanda e a piscina, o piso ja tem
    # caimento de 1,5 % e a lavagem semanal de churrasqueira escoa para algum
    # lugar. Sem ralo, esse lugar e o estar. Sifonado de 150 junto da cuba, que
    # e o ponto baixo e onde a agua de fato cai.
    dict(cod="RL-12", amb="T-GOU", tipo="ralo sifonado 150", x=9_000, y=19_950,
         dn=50),
    dict(cod="RL-09", amb="T-VRL", tipo="ralo sifonado 150", x=12_700, y=19_300, dn=50),
    dict(cod="RL-10", amb="T-LOG", tipo="ralo sifonado 150", x=2_500, y=16_300, dn=50),
]
CAIMENTO_AREA_MOLHADA = 0.015
CAIMENTO_AREA_EXTERNA = 0.01
SOLEIRA_BOX = 15            # mm de desnivel na soleira do box
IMPERMEABILIZACAO = dict(sistema="manta liquida poliuretanica, 2 demaos",
                         subida_parede=300, subida_box=1_800,
                         teste="estanqueidade com lamina de 50 mm por 72 h")


def area_drenada_externa_m2() -> float:
    return round(sum(a.area_mod for a in TERREO_ABERTO if not a.coberto
                     and a.cod in ("T-DKP", "T-DKL", "T-PT2")), 2)


# =========================================================================
# CORTINA DE VIDRO — o fechamento posterior de cozinha e gourmet
#
# Nao e porta de correr com outro nome. A diferenca esta no que sobra quando
# se abre: a porta de correr empilha folhas sobre folhas e deixa montantes
# verticais no meio do vao; a cortina de vidro tem folhas SOLTAS que correm no
# trilho e giram 90 graus para estacionar de perfil num nicho lateral. Aberta,
# o vao fica limpo dos 7.200 mm inteiros.
#
# O preco disso e tecnico e precisa estar escrito:
#   1. NAO e esquadria de desempenho. Cortina de vidro nao tem borracha de
#      compressao nem estanqueidade classificada — ela veda chuva de cima e
#      vento, nao veda ar. Por isso a fita social nunca dependeu dela para
#      climatizacao: a zona fria e o estar, com a fronteira aerodinamica, e o
#      gourmet e area ventilada por definicao.
#   2. O trilho inferior e o ponto de entrada de agua mais provavel da casa:
#      7,20 m de fresta rente ao piso, voltada para o vento de chuva. Dai o
#      ralo linear RL-11 continuo sob ele, e o trilho drenando PARA DENTRO do
#      canal, nunca para o piso interno.
#   3. A verga e governada pelo trilho, nao pelo gesso: L/700 em vez de L/500
#      (ver V-10). Com 13 mm de flecha o perfil fecha sobre as folhas e o
#      sistema trava.
#   4. Vidro temperado de 10 mm sem caixilho exige pelicula de seguranca ou
#      laminado nas folhas de circulacao, e sinalizacao a altura dos olhos —
#      vidro limpo e invisivel e alguem vai tentar atravessar.
# =========================================================================
CORTINA_VIDRO = dict(
    cod="CV-01", vao="CV01", x=2_400, y=26_400, largura=7_200, altura=2_600,
    folhas=8, largura_folha=900, vidro="temperado 10 mm, incolor",
    pelicula="de seguranca nas duas folhas centrais, com faixa fosca a 1.500 mm",
    recolhimento="90 graus em nicho lateral, 4 folhas para cada lado",
    nicho_w=200, nicho_prof=950,
    trilho_sup="perfil estrutural fixado na viga V-10, com regulagem de 10 mm",
    trilho_inf="perfil drenado, embutido no contrapiso, caimento para RL-11",
    vao_livre_aberto=7_200 - 2 * 200,      # descontados os dois nichos
    uso_padrao="ABERTA",
    fecha_quando=("chuva com vento de sudoeste", "ausencia prolongada",
                  "uso do estar climatizado com a casa vazia"),
    nao_serve_para=("estanqueidade ao ar", "isolamento acustico",
                    "barreira termica de ambiente climatizado"),
)
VARANDA_GOURMET = dict(
    prof=3_000, largura=7_200, pe_direito=2_600,
    cobertura="laje em balanco de 3.000 mm (V-11 a cada 1.200 mm), sem pilar "
              "na frente — nenhuma coluna entre a mesa e a piscina",
    forro="laminas de madeira composita ventiladas, continuas com o forro "
          "interno atravessando a linha da cortina",
    piso="continuo com o interno, no MESMO nivel e na mesma paginacao: e a "
         "continuidade do piso que faz o olho ler um ambiente so",
    caimento=0.01, ralo="RL-11 sob a cortina e canaleta na borda externa",
    iluminacao="perfil linear embutido no forro, paralelo a cortina",
)
# A continuidade que faz a integracao funcionar, em tres medidas concretas:
CONTINUIDADE_INTERNO_EXTERNO = dict(
    desnivel_piso=0,            # mm — soleira no mesmo nivel
    junta_alinhada=True,        # a paginacao atravessa a linha da cortina
    forro_continuo=True,        # o forro passa por cima do trilho
    obs="degrau, junta desalinhada ou forro interrompido na soleira sao os tres "
        "erros que fazem uma abertura de 7 m continuar parecendo uma porta")


def eixo_visual() -> dict:
    """Eixo estar -> gourmet -> cortina -> varanda -> piscina, em numeros."""
    estar = next(a for a in TERREO if a.cod == "T-SOC")
    cv = CORTINA_VIDRO
    return dict(
        origem_y=estar.y, cortina_y=cv["y"],
        varanda_y=cv["y"] + VARANDA_GOURMET["prof"],
        piscina_y=PISCINA["y"], fim_piscina_y=PISCINA["y"] + PISCINA["h"],
        profundidade_total=PISCINA["y"] + PISCINA["h"] - estar.y,
        eixo_x_social=estar.x + estar.w / 2,
        eixo_x_piscina=PISCINA["x"] + PISCINA["w"] / 2,
        desalinhamento=abs((estar.x + estar.w / 2) - (PISCINA["x"] + PISCINA["w"] / 2)),
        vao_livre=cv["vao_livre_aberto"])


# =========================================================================
# FACHADA FRONTAL — leitura da referencia visual enviada pelo proprietario
#
# A imagem confirma a linguagem que o projeto ja adotava e acrescenta um
# recurso que faltava: o RASGO DE LUZ. Na foto, o que constroi a horizontalidade
# a noite nao e o volume, e a linha continua de luz rasante sob cada plano — no
# reentrancia do portico de entrada, sob o beiral do volume superior e na base
# dos muros. E iluminacao INDIRETA: nenhuma fonte aparece, so a superficie
# iluminada. Custa pouco, nao exige manutencao em altura e e o que separa uma
# fachada contemporanea de uma fachada meramente lisa.
#
# As tres familias de material do projeto ja coincidem com a referencia:
#   mineral claro de grande formato (o plano de fundo),
#   aluminio grafite ripado (o portao e os brises),
#   madeira (a folha da porta de entrada, sob o portico).
# O YAML limita a tres familias; a referencia usa exatamente tres. Nada a mudar.
# =========================================================================
ILUMINACAO_FACHADA = [
    dict(cod="IF-01", onde="reentrancia do portico de entrada",
         tipo="perfil linear LED IP65, 2.700 K, 8 W/m, embutido no forro",
         comprimento_m=9.6, efeito="lava a folha de madeira da porta e marca a "
         "profundidade do portico"),
    dict(cod="IF-02", onde="sob o beiral do volume superior",
         tipo="perfil linear LED IP65, 2.700 K, 8 W/m",
         comprimento_m=14.4, efeito="risco horizontal continuo: e ele que faz a "
         "casa parecer baixa e longa a noite"),
    dict(cod="IF-03", onde="base do muro e do portao ripado",
         tipo="balizador embutido no piso, 3 W, feixe rasante",
         comprimento_m=8.4, efeito="revela a textura do ripado por raspagem"),
    dict(cod="IF-04", onde="uplight nas palmeiras da entrada",
         tipo="projetor de solo 7 W, 2.700 K, feixe 15 graus",
         comprimento_m=0, efeito="profundidade: a copa iluminada recua o plano "
         "de fundo"),
]
FACHADA_MATERIAIS = [
    ("Mineral claro de grande formato", "placa cimenticia com revestimento "
     "mineral 1.200 x 2.400, junta seca de 6 mm"),
    ("Aluminio grafite ripado", "portao de correr, brises e guarda-corpo"),
    ("Madeira", "folha da porta de entrada e forro do portico"),
]
FACHADA_REGRAS = dict(
    familias_max=3, vidro="controlado, concentrado na fachada posterior",
    ornamento="nenhum sem funcao termica ou de composicao",
    manutencao="nenhuma superficie que exija pintura em altura",
)


# =========================================================================
# ETAPA 4 — FECHAMENTO: ACABAMENTOS, LOCACAO, PAISAGISMO E EMISSAO
# =========================================================================

# ----------------------------------------------------------- ACABAMENTOS
# Nao e uma lista nova: e DERIVADA do que ja foi decidido em outras pranchas
# (zonas de paginacao, forros acusticos, alturas de revestimento, categoria de
# uso). Lista paralela de acabamento e a campea de divergencia em obra, porque
# e a ultima a ser feita e a primeira a ser esquecida quando algo muda.
PISOS_PADRAO = {
    "intimo": "porcelanato retificado 900 x 900, acetinado",
    "social": "porcelanato retificado 900 x 900, acetinado",
    "molhado": "porcelanato retificado 900 x 900, antiderrapante R10",
    "servico": "porcelanato 600 x 600 antiderrapante R11",
    "circulacao": "porcelanato retificado 900 x 900, acetinado",
    "apoio": "cimenticio polido com endurecedor de superficie",
    "oficina": "cimenticio polido com endurecedor de superficie",
}
FORRO_H = {"padrao": PE_DIREITO, "banho": 2_400}
# banho recebe forro rebaixado para 2.400 mm: e onde passam o dreno do ar, o
# duto de exaustao e a luminaria embutida. O rebaixo nao e perda de pe-direito,
# e o unico lugar onde essa instalacao cabe sem shaft adicional.
RODAPE = dict(h=100, tipo="poliestireno 100 x 15 mm, pintado",
              molhado="em porcelanato recortado da mesma peca do piso")
SOLEIRAS = dict(interna="sem soleira — piso continuo na mesma cota",
                molhada=f"granito cinza 150 mm, desnivel de {15} mm",
                externa="granito cinza 150 mm com pingadeira")
# R48 — a regra de fachada declarada em R06 diz "nenhuma superficie que exija
# pintura em altura", e o acabamento externo declarado era pintura acrilica
# sobre base cimenticia, num volume de 6,15 m. Contradicao entre duas decisoes
# do proprio projeto.
#
# Quem tinha razao era a fachada: FACHADA_MATERIAIS ja especifica "placa
# cimenticia com revestimento MINERAL de grande formato, junta seca" — que e
# acabamento de fabrica e nao se repinta. A pintura externa passa a valer so
# onde se alcanca do chao, e isso agora esta escrito e e conferido.
#
# Custo de ciclo: repintar 150 m2 de fachada a 6 m de altura custa a pintura
# MAIS o andaime, a cada cinco anos, para sempre. O revestimento mineral custa
# mais uma vez.
PINTURA = dict(interna="latex acrilico acetinado, 2 demaos sobre selador",
               umida="latex acrilico premium com biocida, 2 demaos",
               externa="acrilico elastomerico sobre base cimenticia",
               externa_onde="muro, face interna de platibanda e rodape de "
                            "fachada ate 2.600 mm — tudo alcancavel do chao. A "
                            "fachada do volume superior NAO e pintada: leva o "
                            "revestimento mineral de fabrica da FACHADA_MATERIAIS",
               forro="latex PVA fosco branco")


def acabamentos() -> list[dict]:
    """Acabamento por ambiente, derivado das decisoes ja tomadas."""
    import especificacao as ep
    forros = {f[0]: f[1] for f in FORROS_SRC()}
    out = []
    # R45 — as subdivisoes MOLHADAS entram na lista. Ate aqui acabamentos()
    # enumerava AMBIENTES, e o banho da suite e subdivisao: os tres banhos do
    # superior nao tinham piso, revestimento nem rodape declarado em lugar
    # nenhum. Nada e arbitrado aqui — aplica-se a MESMA regra que ja vale para
    # area molhada, que e o que esses comodos sempre foram.
    alt_rev = alturas_revestimento()
    subs_molhadas = [d for d in SUBDIVISOES if d.get("molhado")]
    for d in subs_molhadas:
        pai = next((x for x in TERREO + SUPERIOR if x.cod == d["pai"]), None)
        chave = f"{d['pai']}/{d['nome']}"
        h_sub = alt_rev.get(chave, 2_400)
        out.append(dict(
            amb=chave, nome=f"{d['nome']} da {pai.nome if pai else d['pai']}",
            cat="molhado", area=round(d["w"] * d["h"] / 1e6, 2),
            piso=PISOS_PADRAO["molhado"],
            parede=f"{PECA_PAREDE['tipo']} ate {h_sub} mm + "
                   f"{PINTURA['umida']} acima",
            forro="gesso acartonado liso, branco, resistente a umidade",
            forro_h=FORRO_H["banho"], rodape=RODAPE["molhado"],
            revest_h=h_sub, zona="ZP-4", subdivisao=True))
    for a in TERREO + SUPERIOR:
        cat = ep.CATEGORIA.get(a.cod, "apoio")
        z = zona_de(a.cod)
        if z and z["peca"] == "monolitico":
            piso = "cimenticio polido com endurecedor de superficie"
        elif a.cod in ep.MOLHADOS or a.cod in alt_rev:
            piso = PISOS_PADRAO["molhado"]
        else:
            piso = PISOS_PADRAO.get(cat, PISOS_PADRAO["social"])
        h = alt_rev.get(a.cod)
        parede = (f"{PECA_PAREDE['tipo']} ate {h} mm + {PINTURA['umida']} acima"
                  if h else
                  PINTURA["umida"] if a.cod in ep.MOLHADOS else PINTURA["interna"])
        forro = forros.get(a.cod, "gesso acartonado liso, branco")
        rod = RODAPE["molhado"] if (h or a.cod in ep.MOLHADOS) else RODAPE["tipo"]
        fh = FORRO_H["banho"] if a.cod in ("T-BWC",) else FORRO_H["padrao"]
        out.append(dict(amb=a.cod, nome=a.nome, cat=cat, area=a.area_mod,
                        piso=piso, parede=parede, forro=forro, forro_h=fh,
                        rodape=rod, revest_h=h, zona=z["cod"] if z else "padrao",
                        subdivisao=False))
    return out


def FORROS_SRC():
    import especificacao as ep
    return ep.FORROS


# -------------------------------------------------------------- LOCACAO
# Locacao de obra e o unico desenho em que o erro nao tem conserto barato: a
# casa sai do lugar. Por isso ela e cotada a partir de DUAS referencias
# independentes (as duas divisas), nunca em cadeia de cotas acumuladas.
RN = dict(cota_local=0, descricao="RN no eixo da testada, alinhado ao medidor "
          "TC-08; cota 0,00 = piso acabado do terreo",
          amarracao="marco de concreto 200 x 200 x 500 mm, fora da area de obra")
EIXOS_LOCACAO = dict(
    x=[2_400, 5_400, 8_400, 9_600, 12_000, 13_800, 15_000, 16_800],
    y=[7_200, 9_600, 13_200, 16_200, 19_200, 23_400, 26_400, 31_800],
)
GABARITO = dict(afastamento=1_000, madeira="pontalete 75 x 75 e tabua 25 x 150",
                obs="gabarito continuo nos dois lados da obra; conferencia por "
                    "diagonal antes de concretar o radier")


def cantos_locacao() -> list[dict]:
    """Cantos da edificacao cotados das DUAS divisas, sem cadeia acumulada."""
    cob = cobertos()
    x0 = min(a.x for a in cob); x1 = max(a.x + a.w for a in cob)
    y0 = min(a.y for a in cob); y1 = max(a.y + a.h for a in cob)
    out = []
    for nome, x, y in (("A", x0, y0), ("B", x1, y0), ("C", x1, y1), ("D", x0, y1)):
        out.append(dict(canto=nome, x=x, y=y, da_divisa_sul=x,
                        da_divisa_norte=LOTE_L - x, da_testada=y,
                        do_fundo=LOTE_P - y))
    d1 = math.hypot(x1 - x0, y1 - y0)
    for o in out:
        o["diagonal"] = round(d1, 1)
    return out


def afastamentos_especie(p: dict) -> dict:
    """Distancias da muda ate as divisas e ate a area coberta mais proxima.

    Substitui a regra anterior, que exigia canteiro com o DOBRO do afastamento —
    criterio que so vale para muda plantada no centro do canteiro. O que importa
    de fato e onde a muda esta, e dai ate onde a raiz e a copa podem chegar.
    """
    if not p.get("x"):
        return {}
    d = {"divisa sul": p["x"], "divisa norte": LOTE_L - p["x"],
         "testada": p["y"], "fundo": LOTE_P - p["y"]}
    perto = 1e9
    for a in cobertos():
        dx = max(a.x - p["x"], p["x"] - (a.x + a.w), 0)
        dy = max(a.y - p["y"], p["y"] - (a.y + a.h), 0)
        perto = min(perto, math.hypot(dx, dy))
    d["edificacao"] = perto
    return d


# ----------------------------------------------------------- PAISAGISMO
# Paisagismo aqui nao e decoracao: e a ultima camada do projeto termico. A
# arvore certa na posicao certa faz o que nenhum brise faz — sombreia ANTES de
# o sol chegar na parede, transpira (resfriamento evaporativo) e nao aquece por
# reirradiacao, porque a folha nao acumula calor como a alvenaria.
#
# Criterio de escolha, nesta ordem:
#   1. porte compativel com o afastamento (raiz e copa);
#   2. funcao termica: sombra de copa ALTA a oeste e a norte;
#   3. especie nativa ou adaptada a Manaus, sem irrigacao permanente;
#   4. nada de raiz agressiva perto de radier, piscina ou tubulacao.
# R06 — o YAML impoe "nada que exija poda rotineira" e elimina gramado extenso,
# cerca viva e arbustos de poda. Isso derruba duas especies que eu havia
# proposto na Etapa 4: a sebe de murta (poda a cada 60 dias para manter forma) e
# a trelica com Thunbergia (trepadeira vigorosa, poda de contencao 3x por ano).
#
# Mas ha um custo termico nessa exigencia que precisa ficar escrito: vegetacao
# e o unico elemento do projeto que sombreia ANTES do sol chegar na superficie e
# que resfria por transpiracao em vez de reirradiar. Trocar tudo por piso e
# transferir calor para dentro da casa. A compensacao adotada, item a item:
#   - piso drenante e porcelanato CLAROS (albedo 0,60 contra 0,20 do escuro);
#   - brise metalico sombreando o nicho de condensadoras, no lugar da trelica —
#     mesma sombra, zero poda, e a mesma linguagem ripada da fachada;
#   - as duas arvores do fundo permanecem: arvore de copa alta nao e "arbusto
#     com poda"; jabuticabeira e ipe nao pedem conducao depois de formados.
PAISAGISMO = [
    dict(cod="PA-01", x=7_200, y=36_900, amb="T-JFU", especie="Ipe-amarelo (Handroanthus)",
         porte="8 a 12 m", funcao="sombra alta no fundo e floracao de estacao",
         qtd=1, raiz="pivotante, nao agressiva", afast_min=3_000,
         poda="apenas formacao nos 3 primeiros anos"),
    dict(cod="PA-02", x=12_600, y=36_900, amb="T-JFU", especie="Jabuticabeira (Plinia cauliflora)",
         porte="6 a 9 m", funcao="sombra densa e fruto no proprio tronco",
         qtd=1, raiz="nao agressiva, crescimento lento", afast_min=3_000,
         poda="nenhuma",
         obs="escolhida em lugar de mangueira: a manga cai de 12 m de altura no "
             "telhado do vizinho; a jabuticaba nasce no tronco"),
    dict(cod="PA-03", x=3_000, y=32_100, amb="T-JS2", especie="Vasos com Sansevieria e Zamioculca",
         porte="0,8 a 1,2 m", funcao="massa verde na faixa sul de 1.800 mm, "
         "sem canteiro corrido e sem raiz junto ao radier",
         qtd=9, raiz="em vaso", afast_min=300, poda="nenhuma",
         obs="substitui a sebe de murta da Etapa 4, que exigia poda a cada 60 dias"),
    dict(cod="PA-04", x=14_400, y=30_600, amb="T-JN3", especie="Palmeira-acai (Euterpe oleracea)",
         porte="10 a 15 m", funcao="verticalidade e sombra pontual no jardim norte",
         qtd=3, raiz="fasciculada, proxima ao tronco", afast_min=1_500,
         poda="retirada de folha seca, 1x por ano"),
    dict(cod="PA-05", x=11_100, y=8_400, amb="T-JLE", especie="Vasos com Formio e Agave",
         porte="0,6 a 1,0 m", funcao="jardim de inverno leste, visto do banho",
         qtd=6, raiz="em vaso", afast_min=300, poda="nenhuma"),
    dict(cod="PA-06", x=3_000, y=27_900, amb="T-ALP", especie="Horta aromatica em vasos elevados",
         porte="0,4 a 0,8 m", funcao="alecrim, manjericao e capim-limao na varanda, "
         "a dois passos da bancada e sob cobertura",
         qtd=6, raiz="em vaso", afast_min=300, poda="colheita, nao poda"),
    dict(cod="PA-07", x=10_500, y=28_200, amb="T-JN2", especie="Seixo rolado claro e vasos",
         porte="—", funcao="acabamento permeavel sob a varanda, onde nao chega "
         "chuva nem sol suficiente para planta de solo",
         qtd=3, raiz="em vaso", afast_min=0, poda="nenhuma"),
    dict(cod="PA-08", x=0, y=0, amb="T-DKP", especie="Piso drenante claro",
         porte="rasteira", funcao="permeabilidade e albedo alto no entorno do "
         "deck, no lugar do gramado",
         qtd=0, raiz="—", afast_min=0, poda="nenhuma",
         obs="o YAML elimina gramado extenso; o drenante devolve a infiltracao "
             "que a grama fazia"),
]
IRRIGACAO = dict(
    sistema="gotejamento em linha autocompensante, 2 L/h por gotejador",
    setores=3, vazao_setor_lh=240, tempo_min=20, frequencia="2 x por semana",
    fonte="reservatorio pluvial TC-03, por gravidade com filtro de 130 mesh",
    obs="gotejamento e nao aspersao: evapora menos, nao molha fachada e nao "
        "lava o solo. Em cidade com 2.300 mm de chuva, irrigacao e para a "
        "estiagem curta, nao para o ano inteiro",
)


def area_jardim_m2() -> float:
    return round(sum(a.area_mod for a in TERREO_ABERTO
                     if a.cod.startswith("T-J")), 2)


def demanda_irrigacao_ldia() -> float:
    """Demanda media diaria da irrigacao, a partir dos setores declarados."""
    ir = IRRIGACAO
    por_evento = ir["setores"] * ir["vazao_setor_lh"] * (ir["tempo_min"] / 60)
    return round(por_evento * 2 / 7, 1)


# -------------------------------------------------------------- EMISSAO
REVISOES = [
    ("R00", "Modelo parametrico inicial: 19 pranchas de estudo"),
    ("R01", "Etapa 1 — areas tecnicas locadas; projecao coberta corrigida"),
    ("R02", "Fita social climatizada por zona, com fronteira aerodinamica"),
    ("R03", "Etapa 2 — detalhamento construtivo; auditoria em tres dimensoes"),
    ("R04", "Etapa 3 — coordenacao de instalacoes; vazao pluvial recalculada"),
    ("R05", "Etapa 4 — acabamentos, locacao, paisagismo e emissao"),
    ("R06", "YAML MASTER do proprietario: master de 46,80 m2, mini lounge, "
            "piscina de 17,82 m2, casa de maquinas na lateral tecnica, "
            "paisagismo sem poda e rasgos de luz na fachada"),
    ("R07", "Eixo social: cozinha alcanca o fundo, cortina de vidro de 7.200 mm, "
            "varanda gourmet de 3.000 mm em balanco e piscina no eixo"),
    ("R08", "Despensa volta na ponta de servico, com a porta da loggia abrindo "
            "dentro dela; cuba para o fundo, de frente para a cortina"),
    ("R09", "Programa de 63 auditorias: segundo bloco de verificacoes e seis "
            "defeitos corrigidos, entre eles a prumada da master e a "
            "privacidade das suites"),
    ("R10", "Coccao unica: o cooktop do gourmet sai; a peninsula deixa a area de "
            "transicao e a fila leste da cozinha alinha a frente em x = 5.400"),
    ("R11", "Visualizador auditado: zoom 2D por degraus fixos que redesenham o "
            "vetor, modelo 3D navegavel com oito cenas, sol real, corte "
            "horizontal e camadas; deck deixa de tapar a piscina"),
    ("R12", "Procedencia no traco: cada elemento do SVG declara de onde veio, e "
            "a prancha vira documento navegavel. A folha entra na auditoria e "
            "14 das 35 pranchas desenhavam fora da moldura — PR-22 era ilegivel"),
    ("R13", "E0 — motor separado do caso: a obra vai para projetos/porto_real.py "
            "e nucleo/ passa a existir. Cadastro, 20 tipologias e unidades viram "
            "dado; as 35 pranchas saem identicas byte a byte"),
    ("R14", "E1 — perfis formados a frio: um solver de linha media no lugar de "
            "formula por forma, validado contra solucao fechada do U simples. "
            "Catalogo de 81 perfis; o labio de 12 mm nao se forma a 3,00 mm"),
    ("R15", "E2 — materiais e normas: 9 acos com fy e fu, 6 revestimentos com "
            "espessura de camada calculada, 6 sistemas normativos selecionaveis "
            "e o TRRF da NBR 14432. Sem fy nao existia NBR 14762"),
    ("R16", "E3 e E4 — cargas, vento e combinacoes: NBR 6123 completa (S1, S2, "
            "S3, Cpe, Cpi) e NBR 8681 com o permanente favoravel, que e o que "
            "revela o levantamento da cobertura pelo vento"),
    ("R17", "E5 — solver de porticos espaciais por rigidez direta, com algebra "
            "propria (LDL^T em perfil) e segunda ordem. Seis solucoes fechadas "
            "reproduzidas com precisao de maquina"),
    ("R18", "E6 — NBR 14762 pelo Metodo da Resistencia Direta: global, local e "
            "distorcional competindo. O travamento da parede deixa de ser habito "
            "e passa a ser +216 % de resistencia medidos"),
    ("R19", "E7 — painelizacao: 801 pecas e 2.411 kg de aco em paineis "
            "fabricaveis. Cinco paineis nao podem ser partidos porque a abertura "
            "ocupa a parede inteira, e isso passa a ser declarado"),
    ("R20", "E8 e E9 — contraventamento, shear wall, 7 tipos de trelica, "
            "ligacoes pelos cinco modos da NBR 14762, chumbadores e a "
            "verificacao geometrica de que a parafusadeira entra"),
    ("R21", "E10 a E12 — peca com codigo estavel e passaporte, clash entre "
            "disciplinas, plano de corte com 87,2 % de aproveitamento e BOM com "
            "quantidades derivadas e precos declarados (H)"),
    ("R22", "E13 e E14 — CNC em formato neutro verificado por ida e volta, "
            "balanceamento de linha, OEE, tolerancias, centro de gravidade por "
            "soma de momentos, icamento e carregamento de container"),
    ("R23", "E15 e E16 — sequencia de montagem por ordenacao topologica com "
            "estabilidade em cada passo, e otimizacao global ponderada que "
            "prefere a solucao mais pesada quando ela custa menos para montar"),
    ("R24", "E17 e E18 — diff entre revisoes, analise de impacto que separa o "
            "que ja foi cortado, congelamento, DXF, IFC4, OBJ, STL, CSV, XML e "
            "banco de 28 entidades"),
    ("R25", "E20, E21 e E22 — documentos gerados do modelo em tres modos de "
            "leitura, checklist de liberacao de 16 itens com motor de erros, e "
            "scores com a formula exposta, inclusive CO2e e desmontabilidade"),
    ("R26", "E19 — aba de engenharia no visualizador: sete vistas do motor, "
            "painel de parede desenhado a partir da coordenada da propria peca. "
            "Desenhar expos tres defeitos: 138 pecas fora do envelope do "
            "painel, dois vaos mais altos que a parede emitidos em silencio e "
            "o codigo de peca que se dizia estavel e carregava o contador de "
            "geracao"),
    ("R27", "E23 — contrato executavel para as 20 secoes bloqueadas: esquema "
            "de dados com tipo e unidade, adaptador que levanta SemFonteDeDados "
            "dizendo o que falta e como suprir, validador que ja recusa dado "
            "malformado hoje, e o criterio de aceite do dia em que o dado "
            "existir. O visualizador ganhou a oitava vista: o que o sistema "
            "nao faz, com o mesmo rigor do que faz"),
    ("R28", "Emenda de peca horizontal: guia, blocking, verga e peitoril acima "
            "de 6.000 mm saem em trechos emendados sobre apoio real, "
            "escalonados entre si. Onde a abertura nao deixa apoio, a emenda "
            "sai marcada e vira item aberto — tres em TP27"),
    ("R29", "Descida de cargas real e verificacao dos 415 montantes, um a um. "
            "A trava min(0,99) que impedia o checklist de reprovar caiu, e com "
            "a carga que de fato desce 12 pecas reprovavam — todas jamba de "
            "abertura larga, a pior com 2,03. Jamba dimensionada pela carga, "
            "com alvo de projeto de 0,95 separado do limite normativo de 1,00; "
            "custou 10 kg de aco em 2.424"),
    ("R30", "Programa de parafusos: 1.520 juntas e 5.266 parafusos, cada um "
            "com a origem declarada — forca calculada, minimo construtivo ou "
            "regra escrita. O checklist trazia \"ligacoes\": True literal e o "
            "BOM estimava pecas x 8, 22 % a mais. E a estrutura inteira entrou "
            "no 3D: 805 pecas, cada familia numa cor, cada peca clicavel"),
    ("R31", "Vigamento de entrepiso, cobertura e contraventamento: as 805 "
            "pecas da estrutura eram TODAS de parede, e o piso do superior nao "
            "se apoiava em nada. Entram 178 pecas de vigamento e 28 fitas em X "
            "conferidas contra o vento da NBR 6123. O consumo de aco vai de "
            "9,4 para 21,0 kg/m2 — faltava mais da metade"),
    ("R32", "Duas classes novas de verificacao: PLAUSIBILIDADE (a grandeza e "
            "possivel? nove faixas com fonte declarada) e COMPLETUDE (o "
            "sistema esta presente? treze exigencias do sistema construtivo). "
            "A segunda disparou na primeira execucao e achou duas ausencias "
            "reais: ancoragem a fundacao, que era True literal, e a estrutura "
            "da escada, cujos 18 degraus apoiavam no ar"),
    ("R33", "Quatro correcoes de codigo, e duas acharam defeito: a fixture "
            "unica expos que a auditoria via 805 pecas de 1.033 e que o "
            "vigamento tinha 60 codigos repetidos; a coerencia de modelo expos "
            "que o 3D nao desenhava a escada. Os atributos enxertados em "
            "Painel viraram contexto explicito e o except generico que "
            "transformava bug em reprovacao saiu"),
    ("R34", "Composicao de parede como dado: camada, espessura, funcao e "
            "norma, transcritas da PR-12. O fechamento saia de seis "
            "coeficientes e passa a sair da geometria de cada painel, "
            "descontada a abertura. A transcricao permitiu conferir a "
            "justificativa da PH-1: a cavidade e a alma do montante, 90 mm, e "
            "o DN100 tem 110 de diametro externo"),
    ("R35", "Paginacao de placa: 696 placas inteiras com 79,3 % de "
            "aproveitamento, retalho reagrupado pelo mesmo nesting das barras. "
            "Norma e formato comercial voltam para o material, fonte unica. "
            "Piso, forro e cobertura ganham composicao, e fita, massa e "
            "cantoneira passam a existir, derivadas do perimetro"),
    ("R36", "Esquadria, cobertura e impermeabilizacao passam de zero a "
            "material: 311 m de caixilho, 62 m2 de vidro com especificacao por "
            "vao, calha, rufo e cumeeira do perimetro, e manta das areas "
            "molhadas. O cruzamento entre quadro de esquadrias e quadro de "
            "ambientes achou 3 banheiros no superior que existem no desenho e "
            "nao no dado — a area deles nao foi arbitrada"),
    ("R37", "Fundacao entra no BOM: 33,5 m3 de concreto, 1.509 kg de aco, "
            "tela, lastro, lona e forma, derivados da projecao. A espessura de "
            "180 mm era literal no desenho e copia dentro da ancoragem, e "
            "agora e dado do caso — o embutimento do chumbador so cabe se os "
            "dois falarem do mesmo radier. Espessura, fck e taxa sao (H) ate a "
            "sondagem: o modulo deriva quantidade, nao dimensiona radier"),
    ("R38", "Instalacoes passam de tracado a quantidade: 408,8 m de tubo em "
            "sete diametros, 745 m de eletroduto para 96 pontos, 56 m de linha "
            "frigorigena e 187 conexoes, por percurso Manhattan vezes fator "
            "declarado — limite INFERIOR, nunca o percurso do instalador. Com "
            "percurso existindo, o item 'clashes' do checklist deixa de ser "
            "True literal e confronta 844 volumes: acusou que a posicao "
            "declarada de tres prumadas cai dentro de linha de parede, e um "
            "shaft de 300 x 300 nao cabe em parede de 150. O modelo nao tem a "
            "informacao que resolve isso e nao a arbitra"),
    ("R39", "As tres decisoes que faltavam, e a que o sistema nao podia tomar "
            "sozinho. O shaft deixa de ser conflito: regra declarada — caixa na "
            "face da parede, do lado molhado, parede continua — e afastamento "
            "PROCURADO, o menor que tira a caixa da estrutura sem sair do "
            "ambiente; clash de 26 para 0, com contrafactual que exige os 26 de "
            "volta na posicao declarada. Os 3 banhos do superior entram na "
            "impermeabilizacao com a geometria que a subdivisao ja tinha desde "
            "R06: a lacuna era de leitura, nao de dado, e a conta vai de 91,4 "
            "para 123,1 m2. E o checklist ganha o 18o item: dezessete "
            "verificacoes de coerencia interna anunciavam LIBERADO PARA "
            "FABRICACAO com a ART e o nesting abertos no proprio caderno — "
            "consistencia interna nao e autorizacao. As pendencias saem de "
            "dentro de duas pranchas, onde ja divergiam entre si, e viram dado "
            "do caso com o portao que cada uma tranca"),
    ("R40", "Cotacao: o mapa que vai ao fornecedor, a porta por onde o preco "
            "entra e o defeito que a pergunta achou. Montar o mapa obrigou a "
            "responder o que exatamente se compra, e o aco estava no orcamento "
            "DUAS VEZES, em duas unidades: 6.230,8 kg de barra e 1.033 pecas "
            "cortadas, as duas com preco, as duas somadas. R$ 62.664 de "
            "inflacao, +15,6 %, e o custo por m2 cai de 1.571 para 1.359. "
            "Nenhuma faixa pegaria — a de custo vai de 600 a 1.800 e os dois "
            "cabem dentro: o que pega e identidade, e a massa util sobre o "
            "aproveitamento da exatamente a bruta comprada. O mapa expos ainda "
            "12 linhas sem especificacao suficiente para virar pergunta. "
            "Nenhum preco foi inventado: 100 % continuam (H), e a cobertura "
            "cotada — 0 % — passa a ser mostrada em vez de omitida"),
    ("R41", "Navegacao, responsividade e dinamismo, medidos em vez de "
            "supostos. A 390 px o caderno tinha 476 de largura e rolava de "
            "lado: a culpa nao era do indice de pranchas, que ja rolava "
            "sozinho, e sim da barra de 8 botoes sem flex-wrap — medir disse "
            "qual dos dois era. O endereco passa a descrever o que se esta "
            "vendo (#2d/PR-22, #eng/cotacao): um caderno existe para ser "
            "CITADO, e ate aqui o link caia na capa. O botao Voltar desfaz o "
            "ultimo passo dentro do caderno. Toda tabela ordena, com numero "
            "ordenando como numero — o cursor ja prometia isso em dez tabelas "
            "e so uma cumpria. E a lista de pecas sai em lotes: 8.218 nos por "
            "render viraram 1.470, preservando a rolagem do leitor"),
    ("R42", "Busca global e impressao. O sistema nao tinha busca, tinha "
            "filtros: cada vista enxergava a propria lista, e quem procurava "
            "TP23 precisava saber ANTES em que aba TP23 mora — que e "
            "exatamente o que quem procura nao sabe. Indice unico de 1.247 "
            "entradas em 10 tipos, montado do que ja existe, com ranking (o "
            "codigo exato vem antes de quem so o menciona) e, sobretudo, com "
            "DESTINO: escolher um material abre a vista de cotacao ja filtrada "
            "nele. So foi possivel depois da rota de R41 — resultado de busca "
            "sem endereco e eco. E o Ctrl+P, que levava trilho, barra e "
            "minimapa para o papel e cortava o desenho porque o palco tem "
            "altura em vh, passa a imprimir o DOCUMENTO, com o endereco da "
            "vista carimbado no rodape"),
    ("R43", "Graficos: distribuicao de utilizacao dos 415 montantes com a "
            "fronteira do limite normativo, concentracao de custo com os dois "
            "eixos em percentual — uma escala, nunca duas — e curva de horas "
            "acumuladas de montagem. Ate aqui todo grafico era uma div com "
            "largura percentual: compara magnitude e nao responde onde a coisa "
            "passa de aceitavel. Desenhar expos um erro proprio: o alvo de "
            "projeto 0,95 estava marcado DENTRO de uma faixa, e o eixo do "
            "histograma e categorico — valor continuo em eixo categorico finge "
            "uma escala que nao existe. A soma das faixas e conferida contra o "
            "numero de montantes verificados: o desenho mostra o que o motor "
            "calculou, nao uma conta refeita no navegador"),
    ("R44", "Verificacao por COMODO, o eixo que nao existia: as 510 condicoes "
            "anteriores olham por sistema, e defeito se concentra onde dois "
            "sistemas se encontram — dentro de um comodo. O dossie reune "
            "acabamento, vao, tomada, peca hidraulica, ralo, clima e as "
            "paredes que cercam cada um dos 17 comodos. Achou 24 divergencias "
            "na primeira execucao: 14 de um defeito real — o levantamento de "
            "instalacoes contava tomada por AREA e a NBR 5410 conta PERIMETRO, "
            "71 contra 55, faltando 3 na lavanderia e sobrando 3 na master — e "
            "10 de grossura da propria conferencia, que classificava vao por "
            "prefixo de codigo e somava a area do banho na conta da janela do "
            "quarto. A conjugacao cozinha-gourmet, decidida em R07 e escrita em "
            "COMENTARIO, virou dado. Sobraram tres achados reais: o DML sem "
            "vao, o gourmet molhado sem ralo e os tres banhos do superior sem "
            "acabamento declarado"),
    ("R45", "Os tres achados por comodo, resolvidos. O DML ganha basculante "
            "alta na face norte, que estava livre: 0,72 m2 contra os 0,45 "
            "exigidos, ilumina E ventila sem tomar a parede da prateleira — "
            "veneziana na porta nao ilumina e exaustor cobra energia para "
            "sempre. O gourmet ganha ralo sifonado junto da cuba: area "
            "molhada, contigua a piscina, e sem ralo a lavagem escoa para o "
            "estar. Os tres banhos do superior entram na MESMA zona de "
            "revestimento do banho do terreo, e nao numa zona nova — a altura "
            "de um banho e uma decisao so. Duas verificacoes existentes "
            "acusaram a mudanca e acusaram certo: o universo de codigos "
            "validos nao conhecia o codigo qualificado da subdivisao, e o "
            "cruzamento da impermeabilizacao contava janela de banheiro pelo "
            "CODIGO da esquadria — premissa que aguentou ate a primeira janela "
            "alta que nao e de banheiro"),
    ("R46", "O mini lounge nao tinha como ser alcancado. 517 verificacoes "
            "conferem PROPRIEDADES de comodo e nenhuma perguntava se da para "
            "chegar nele: o lounge tinha porta, janela, clima, piso e tomadas, "
            "e nenhum vizinho. Entre ele e o hall havia uma faixa de 600 x "
            "2.400 mm sem ambiente, e o painelizador, vendo exterior dos dois "
            "lados, ergueu DUAS paredes externas paralelas com a porta abrindo "
            "para o vazio entre elas. Estender o hall ate 12.600 REMOVE uma "
            "parede em vez de acrescentar, nao mexe em fachada e devolve ao "
            "hall a distribuicao para quatro destinos que R06 lhe deu. A casa "
            "ganhou 1,44 m2 e ficou mais barata: 1.028 pecas contra 1.033, 60 "
            "paineis contra 62. Entra conectividade(), que caminha a pe a "
            "partir da entrada — relacao entre comodos e grafo, nao tabela. E "
            "o lounge deixa de ser categoria APOIO, que lhe dava piso de "
            "garagem e o excluia da conta de ruido a dois metros da cabeceira "
            "de duas suites"),
    ("R47", "Catalogo tecnico com o desenho de cada peca — perfil, parafuso, "
            "chapa e tubo — gerado da PROPRIA peca: a mesma poligonal de linha "
            "media que o solver da NBR 14762 integra para achar A, Ix e Wx. "
            "Imagem de catalogo seria de um perfil generico, com marca de "
            "terceiro, e continuaria igual depois de a auditoria mudar uma "
            "espessura: passaria a mentir em silencio. A designacao ja E a "
            "dimensao. Zero imagens buscadas fora, e o teste confere que a "
            "cota desenhada e a dimensao que alimenta o calculo. Mais as duas "
            "decisoes do superior: o banho da suite 02 passa de J02 para J04 e "
            "espelha a 03 — a assimetria deixava o lado menor abaixo do minimo "
            "de area molhada — e a ocupacao do nicho de condensadora passa a "
            "ser derivada da lista, porque o texto dizia 2 ativas enquanto a "
            "lista mandava 5"),
    ("R48", "Fachada auditada contra o que foi COMBINADO. A regra declarada em "
            "R06 diz 'nenhuma superficie que exija pintura em altura', e o "
            "acabamento externo especificado era pintura acrilica num volume "
            "de 6,15 m: duas decisoes do mesmo projeto, uma negando a outra. "
            "Quem tinha razao era a fachada — FACHADA_MATERIAIS ja especifica "
            "revestimento mineral de fabrica, que nao se repinta — e a pintura "
            "externa passa a declarar ONDE se aplica: so o que se alcanca do "
            "chao. Repintar 150 m2 a 6 m custa tinta MAIS andaime, a cada cinco "
            "anos, para sempre. E os cinco brises, 16,8 m de ripado e 145,9 kg, "
            "existiam no desenho e no 3D sem material, sem massa e sem carga: "
            "205,5 m de ripa, 33,6 de travessa e 66 fixacoes entram no "
            "orcamento. A altura e a profundidade do brise viviam como literal "
            "em modelo3d.py — 1.500 e 120 — contra os 150 declarados no dado: "
            "duas fontes, as duas em modulo de desenho"),
    ("R49", "Area externa e platibanda, os dois ultimos blocos que existiam so "
            "no desenho. 286 m2 de area aberta — muro de 113,4 m, quatro zonas "
            "de piso, piscina com revestimento e casca, jardim e paisagismo — "
            "somam R$ 88.125, 17 % do custo, exatamente a faixa de pratica "
            "para residencia deste porte, e a propria faixa virou verificacao: "
            "e o unico sinal de que o levantamento nao esquece um bloco "
            "inteiro. O muro e bloco APARENTE com hidrofugante, nao alvenaria "
            "pintada: a regra que barrou a pintura da fachada em R48 vale para "
            "250 m2 de muro repintado a cada cinco anos. E a platibanda — 550 "
            "mm de parede em 64,8 m de perimetro, visivel nas quatro fachadas "
            "— ganha 109 montantes, 129,6 m de guia, 71,3 m2 de placa nas DUAS "
            "faces (a interna olha para a calha e recebe chuva) e 243,6 kg de "
            "aco em linha propria, sem voltar a ser contada em ACO-PERF"),
]
# --------------------------------------------------------- pendencias (R39)
# Ate R38 esta lista vivia dentro de pranchas7.py — modulo de DESENHO — e em
# copia parcial dentro de pranchas3.py. Mesmo padrao da espessura do radier
# (R37) e da posicao das prumadas (R38): dado do caso morando no desenho.
#
# E a consequencia era pior que a duplicacao. O checklist de liberacao nao
# tinha como consultar a lista, e por isso podia anunciar "LIBERADO PARA
# FABRICACAO" com oito pendencias abertas, duas delas bloqueando exatamente a
# fabricacao. Um checklist que ignora o que o proprio caderno declara em voz
# alta nao esta verificando: esta carimbando.
#
# `bloqueia` diz QUAL portao a pendencia tranca. Nao e todo item aberto que
# impede fabricar — a certidao do SU16 condiciona a implantacao, nao o corte do
# perfil — e tratar todos como iguais tornaria o campo inutil.
PENDENCIAS = [
    dict(n="1", titulo="Certidao oficial do SU16 (CAMT, taxa de ocupacao, "
                       "gabarito)", norma="Lei 1.838/2014",
         impacto="Condiciona toda a implantacao",
         status="ABERTA", bloqueia="obra"),
    dict(n="2", titulo="Sondagem do solo e calculo definitivo do radier",
         norma="NBR 6122", impacto="Fundacao",
         status="ABERTA", bloqueia="obra"),
    dict(n="3", titulo="Calculo estrutural do hibrido LSF + laminado, com ART",
         norma="NBR 8800 / 14762",
         impacto="Estrutura e balanco; inclui o apoio da caixa d'agua. O "
                 "pre-dimensionamento por flecha nao substitui verificacao de "
                 "flambagem lateral",
         status="ABERTA", bloqueia="fabricacao"),
    dict(n="4", titulo="Verificacao ambiental do reuso pluvial",
         norma="Codigo Ambiental de Manaus", impacto="Licenciamento",
         status="ABERTA", bloqueia="obra"),
    dict(n="5", titulo="Exigencia municipal de retencao pluvial no lote",
         norma="a confirmar", impacto="Se houver, volume separado do reuso",
         status="ABERTA", bloqueia="obra"),
    dict(n="6", titulo="Regulamento especifico do condominio", norma="—",
         impacto="Fachada, muros, recuos e especie vegetal",
         status="ABERTA", bloqueia="obra"),
    dict(n="7", titulo="Padrao de entrada de energia trifasico",
         norma="NT Amazonas Energia",
         impacto="Confirmar disponibilidade de trifasico no ramal",
         status="ABERTA", bloqueia="obra"),
    dict(n="8", titulo="Nesting codificado dos paineis LSF", norma="fabricante",
         impacto="A paginacao atual e de estudo, nao de corte",
         status="ABERTA", bloqueia="fabricacao"),
    dict(n="9", titulo="Divergencia geometrica R32 x Lista Consolidada",
         norma="briefing", impacto="Documentada em docs/DIVERGENCIAS.md",
         status="RESOLVIDA", bloqueia=""),
    dict(n="10", titulo="Climatizacao da fita social",
         norma="decisao do proprietario",
         impacto="Resolvida por zona com fronteira aerodinamica (R02)",
         status="RESOLVIDA", bloqueia=""),
    # A PR-09 mantinha uma SEGUNDA lista de pendencias, com conteudo
    # divergente: oito itens, numeracao propria e um assunto que a lista da
    # PR-33 nunca teve. Unificar as duas nao pode significar perder o que so
    # uma delas sabia — e este item so existia na copia da PR-09.
    dict(n="11", titulo="Diametro de agua fria do ramal do chuveiro",
         norma="NBR 5626",
         impacto="Hidraulica: a tabela da PR-09 trazia DN50 no ramal; "
                 "verificar se a troca de ramal acompanhou a decisao do "
                 "chuveiro eletrico (peso 0,10 em vez de 0,40)",
         status="ABERTA", bloqueia=""),
    # R40 — a pendencia que sempre existiu e nunca estava na lista. Os precos
    # do BOM sao (H) desde a primeira revisao e sempre estiveram marcados como
    # tal; o que faltava era o item que diz que isso TRANCA alguma coisa. Nao
    # tranca fabricar — tranca contratar.
    dict(n="12", titulo="Cotacao dos materiais: 100 % dos precos sao (H)",
         norma="Lei 14.133 art. 23 (parametro de 3 propostas)",
         impacto="O mapa de cotacao existe e esta pronto para sair; enquanto "
                 "nao voltar, o custo e ordem de grandeza para auditar "
                 "quantidade, nunca base de contrato",
         status="ABERTA", bloqueia="contrato"),
]


def pendencias_abertas(portao: str = "") -> list:
    """Pendencias abertas, opcionalmente so as que trancam um portao."""
    return [p for p in PENDENCIAS if p["status"] == "ABERTA"
            and (not portao or p["bloqueia"] == portao)]


# ------------------------------------------------------------- cadastro (R13)
# Ate R12 a identidade do projeto so existia por escrito no carimbo. Agora e
# dado: a tipologia carrega a sobrecarga normativa e o pe-direito minimo, e a
# auditoria confere o conjunto.
CADASTRO = cd.Cadastro(
    project_id="PR-2026-001",
    nome="Residencia Porto Real",
    cliente="(H) proprietario — nome nao declarado no briefing",
    localizacao="Condominio Porto Real, Taruma, Manaus/AM",
    coordenadas=(-3.10, -60.05),
    tipologia="SOBRADO",
    pavimentos=2,
    # R46 — 297,36 m2: os 295,92 anteriores mais os 1,44 m2 da faixa que o hall
    # absorveu. O numero e literal aqui e derivado na auditoria, que o confere
    # contra a soma dos ambientes a cada execucao — foi assim que a diferenca
    # apareceu no mesmo instante em que o hall cresceu.
    area_m2=297.36,
    pe_direito=2_600,
    sistema="Light Steel Frame sobre radier",
    normas=("NBR 15575", "NBR 15253", "NBR 14762", "NBR 6355", "NBR 6120",
            "NBR 6123", "NBR 8681", "NBR 9050", "NBR 9077", "NBR 5410",
            "NBR 5626", "NBR 8160", "NBR 10844", "NBR 13523", "NBR 16401-2",
            "NBR 15220-3", "NBR 10068", "NBR 10582", "NBR 8403", "NBR 8402",
            "NBR 6492", "NBR 14718", "NBR 6122"),
    moeda="BRL",
    engenheiro="(H) sem ART emitida",
    arquiteto="(H) sem RRT emitida",
    status="ESTUDO",
    revisao="R49",
    data_emissao="2026-09-13",
    observacoes="Itens marcados (H) sao hipoteses tecnicas, nao levantamento.",
)

EMISSAO = dict(
    revisao="R49", finalidade="COORDENACAO E APROVACAO PRELIMINAR",
    nao_serve_para=("execucao de fundacao sem sondagem", "fabricacao de painel "
                    "sem nesting codificado", "aprovacao legal sem ART/RRT"),
    unidade="milimetro", origem="canto frontal esquerdo do lote",
)
