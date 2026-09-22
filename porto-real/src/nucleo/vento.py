"""VENTO — geracao completa da acao do vento (secao 13, NBR 6123:1988).

Nada aqui e tabelado como resultado. Vk sai de V0.S1.S2.S3 e q de 0,613.Vk2; os
coeficientes de forma saem das tabelas da norma por interpolacao declarada. A
diferenca pratica: mudar a altura da casa, a rugosidade do terreno ou a cidade
refaz a acao inteira, inclusive a distribuicao por zona de fachada.

O que NAO esta implementado e dito em voz alta: forma nao retangular, efeito de
vizinhanca e vento em partes exigem tunel de vento ou tabela especifica. A
funcao levanta erro em vez de devolver numero plausivel.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# Velocidade basica V0 (m/s) das isopletas da NBR 6123. (H): valores de leitura
# do mapa — a cota exata do local deve ser confirmada na carta oficial.
V0_CIDADES = {
    "Manaus": 30.0, "Belem": 30.0, "Fortaleza": 35.0, "Recife": 35.0,
    "Salvador": 30.0, "Brasilia": 35.0, "Goiania": 35.0, "Belo Horizonte": 30.0,
    "Rio de Janeiro": 35.0, "Sao Paulo": 40.0, "Curitiba": 40.0,
    "Florianopolis": 43.0, "Porto Alegre": 45.0, "Campo Grande": 40.0,
    "Cuiaba": 33.0, "Palmas": 30.0, "Macapa": 30.0, "Boa Vista": 30.0,
    "Rio Branco": 30.0, "Porto Velho": 30.0,
}

# Tabela 1 da NBR 6123 — fator S2 = b . Fr . (z/10)^p
# categoria: (classe A, classe B, classe C) com (b, p)
S2_TABELA = {
    "I":   {"A": (1.10, 0.06),  "B": (1.11, 0.065), "C": (1.12, 0.07)},
    "II":  {"A": (1.00, 0.085), "B": (1.00, 0.09),  "C": (1.00, 0.10)},
    "III": {"A": (0.94, 0.10),  "B": (0.94, 0.105), "C": (0.93, 0.115)},
    "IV":  {"A": (0.86, 0.12),  "B": (0.85, 0.125), "C": (0.84, 0.135)},
    "V":   {"A": (0.74, 0.15),  "B": (0.73, 0.16),  "C": (0.71, 0.175)},
}
FR = {"A": 1.00, "B": 0.98, "C": 0.95}

CATEGORIAS = {
    "I": "mar calmo, lago, pantano — sem obstaculos",
    "II": "terreno aberto e plano, obstaculos ate 1,0 m",
    "III": "terreno plano com obstaculos ate 3,0 m — casas esparsas, sebes",
    "IV": "terreno com obstaculos numerosos ate 10 m — cidade, subúrbio, mata",
    "V": "obstaculos grandes, altos e pouco espacados — centro de cidade alta",
}
CLASSES = {
    "A": "maior dimensao horizontal ou vertical ate 20 m",
    "B": "entre 20 m e 50 m",
    "C": "acima de 50 m",
}
S3_GRUPOS = {
    1: (1.10, "edificacao essencial: hospital, quartel, central de comunicacao"),
    2: (1.00, "edificacao residencial, comercial ou industrial de uso normal"),
    3: (0.95, "edificacao com baixo fator de ocupacao: deposito, silo"),
    4: (0.88, "vedacao: telha, vidro, painel de vedacao"),
    5: (0.83, "edificacao temporaria e estrutura em construcao"),
}


def classe_por_dimensao(maior_dim_m: float) -> str:
    return "A" if maior_dim_m <= 20 else ("B" if maior_dim_m <= 50 else "C")


def s1_talude(theta_graus: float, z: float, d: float) -> float:
    """S1 em talude e morro (item 5.2 da NBR 6123). Terreno plano da 1,0."""
    if theta_graus <= 3:
        return 1.0
    if theta_graus >= 45:
        p = 0.31
    elif theta_graus >= 17:
        p = 2.5 - theta_graus / 17 * 0.0        # patamar da norma
        p = 0.31 * math.tan(math.radians(min(theta_graus, 45)) - 0.05) / \
            math.tan(math.radians(45) - 0.05)
    else:
        p = 0.0
    if theta_graus < 17:
        # interpolacao linear entre 3 e 17 graus
        f = (theta_graus - 3) / (17 - 3)
        p = f * 0.31 * math.tan(math.radians(17) - 0.05) / \
            math.tan(math.radians(45) - 0.05)
    return max(1.0, 1.0 + (2.5 - z / d) * p) if d else 1.0


def s2(z: float, categoria: str = "III", classe: str = "A") -> float:
    """Fator de rugosidade, dimensoes e altura. z em metros."""
    if categoria not in S2_TABELA:
        raise ValueError(f"categoria '{categoria}' nao existe (I a V)")
    if classe not in FR:
        raise ValueError(f"classe '{classe}' nao existe (A, B, C)")
    b, p = S2_TABELA[categoria][classe]
    return b * FR[classe] * (max(z, 1.0) / 10.0) ** p


def s3(grupo: int = 2) -> float:
    if grupo not in S3_GRUPOS:
        raise ValueError(f"grupo estatistico {grupo} nao existe (1 a 5)")
    return S3_GRUPOS[grupo][0]


def vk(v0: float, z: float, categoria="III", classe="A", grupo=2, s1=1.0) -> float:
    """Velocidade caracteristica do vento, m/s."""
    return v0 * s1 * s2(z, categoria, classe) * s3(grupo)


def pressao(vk_ms: float) -> float:
    """Pressao dinamica q = 0,613 Vk2, em kN/m2 (Vk em m/s)."""
    return 0.613 * vk_ms ** 2 / 1000.0


# ------------------------------------------------------- coeficientes de forma
# Tabela 4 da NBR 6123, paredes de edificacao retangular. Chaves: faixa de h/b.
# Zonas: A e B sao as paredes paralelas ao vento (dividas em 1 e 2 na
# profundidade), C e D as perpendiculares (C barlavento, D sotavento).
_CPE_PAREDE = {
    # (a/b faixa, h/b faixa): {zona: Cpe}
    ("1/2-3/2", "0-1/2"): {"A1": -0.8, "A2": -0.5, "B1": -0.8, "B2": -0.5,
                           "C": 0.7, "D": -0.4},
    ("1/2-3/2", "1/2-3/2"): {"A1": -0.9, "A2": -0.5, "B1": -0.9, "B2": -0.5,
                             "C": 0.7, "D": -0.5},
    ("1/2-3/2", "3/2-6"): {"A1": -1.0, "A2": -0.6, "B1": -1.0, "B2": -0.6,
                           "C": 0.8, "D": -0.6},
    ("2-4", "0-1/2"): {"A1": -0.8, "A2": -0.4, "B1": -0.8, "B2": -0.4,
                       "C": 0.7, "D": -0.3},
    ("2-4", "1/2-3/2"): {"A1": -0.9, "A2": -0.5, "B1": -0.9, "B2": -0.5,
                         "C": 0.7, "D": -0.4},
    ("2-4", "3/2-6"): {"A1": -1.0, "A2": -0.5, "B1": -1.0, "B2": -0.5,
                       "C": 0.8, "D": -0.5},
}
# Tabela 5, cobertura de baixa inclinacao (ate 10 graus), vento a 0 e 90 graus
_CPE_COBERTURA = {
    "0-1/2": {"EF": -0.8, "GH": -0.4, "EF_alt": -0.4, "GH_alt": -0.4},
    "1/2-3/2": {"EF": -0.9, "GH": -0.4, "EF_alt": -0.5, "GH_alt": -0.4},
    "3/2-6": {"EF": -1.0, "GH": -0.5, "EF_alt": -0.6, "GH_alt": -0.5},
}
# Coeficiente de pressao INTERNA (item 6.2)
CPI_CASOS = {
    "impermeavel": (0.0, -0.2, "quatro faces impermeaveis; usar o mais desfavoravel"),
    "permeavel_igual": (0.2, -0.3, "faces igualmente permeaveis"),
    "abertura_barlavento": (0.8, -0.3, "abertura dominante a barlavento"),
    "abertura_sotavento": (-0.5, -0.5, "abertura dominante a sotavento"),
    "abertura_lateral": (-0.9, -0.9, "abertura dominante em face lateral"),
}


def _faixa_ab(a, b):
    """Faixa de a/b, ou o par a interpolar.

    A Tabela 4 tabela 1/2 <= a/b <= 3/2 e 2 <= a/b <= 4, e deixa um VAO entre
    3/2 e 2 — que e exatamente onde caem muitas casas. Interpolar linearmente
    entre as duas faixas e pratica aceita, mas o resultado deixa de ser valor de
    norma e passa a ser valor interpolado: quem le tem de saber disso, e por
    isso a interpolacao e devolvida declarada, nao escondida.
    """
    r = a / b
    if 0.5 <= r <= 1.5:
        return ("1/2-3/2", None, 0.0)
    if 2 <= r <= 4:
        return ("2-4", None, 0.0)
    if 1.5 < r < 2:
        return ("1/2-3/2", "2-4", (r - 1.5) / 0.5)
    raise ValueError(f"a/b = {r:.2f} fora da Tabela 4 da NBR 6123 (0,5 a 4,0) — "
                     f"forma alongada assim exige tabela especifica ou tunel")


def _faixa_hb(h, b):
    r = h / b
    if r <= 0.5:
        return "0-1/2"
    if r <= 1.5:
        return "1/2-3/2"
    if r <= 6:
        return "3/2-6"
    raise ValueError(f"h/b = {r:.2f} acima de 6 — fora da Tabela 4")


def cpe_paredes(a: float, b: float, h: float) -> dict:
    """Coeficientes de pressao externa das paredes (NBR 6123, Tabela 4)."""
    f1, f2, t = _faixa_ab(a, b)
    hb = _faixa_hb(h, b)
    c1 = _CPE_PAREDE[(f1, hb)]
    if f2 is None:
        return dict(c1)
    c2 = _CPE_PAREDE[(f2, hb)]
    return {k: c1[k] + (c2[k] - c1[k]) * t for k in c1}


def origem_cpe(a: float, b: float, h: float) -> str:
    """De onde veio cada Cpe — valor de tabela ou interpolacao declarada."""
    f1, f2, t = _faixa_ab(a, b)
    hb = _faixa_hb(h, b)
    if f2 is None:
        return f"NBR 6123 Tabela 4, a/b em {f1} e h/b em {hb}: valor tabelado"
    return (f"NBR 6123 Tabela 4: a/b = {a/b:.2f} cai no vao entre as faixas "
            f"{f1} e {f2}; valor INTERPOLADO linearmente ({t*100:.0f} % da "
            f"segunda), com h/b em {hb}")


def cpe_cobertura(b: float, h: float, inclinacao_graus: float = 0.0) -> dict:
    """Cobertura de ate 10 graus. Acima disso a Tabela 5 muda de coluna."""
    if inclinacao_graus > 10:
        raise ValueError(f"inclinacao de {inclinacao_graus} graus exige a coluna "
                         f"correspondente da Tabela 5 — nao implementada")
    return dict(_CPE_COBERTURA[_faixa_hb(h, b)])


@dataclass
class AcaoVento:
    """A acao do vento inteira, gerada de uma vez (secao 13)."""
    v0: float
    categoria: str
    classe: str
    grupo: int
    s1: float
    a: float          # dimensao paralela ao vento, m
    b: float          # dimensao perpendicular, m
    h: float          # altura, m
    cpi_caso: str = "impermeavel"

    def vk(self, z=None) -> float:
        return vk(self.v0, z if z is not None else self.h,
                  self.categoria, self.classe, self.grupo, self.s1)

    def q(self, z=None) -> float:
        return pressao(self.vk(z))

    def zonas(self) -> list[dict]:
        """Pressao liquida por zona: (Cpe - Cpi) . q, em kN/m2."""
        q = self.q()
        cpi_pos, cpi_neg, _ = CPI_CASOS[self.cpi_caso]
        out = []
        for nome, cpe in list(cpe_paredes(self.a, self.b, self.h).items()) + \
                         list(cpe_cobertura(self.b, self.h).items()):
            for cpi in {cpi_pos, cpi_neg}:
                out.append(dict(zona=nome, cpe=cpe, cpi=cpi,
                                c=cpe - cpi, p=(cpe - cpi) * q,
                                efeito="pressao" if cpe - cpi > 0 else "succao"))
        return out

    def critica(self) -> dict:
        """A zona de maior succao — a que arranca o telhado."""
        return min(self.zonas(), key=lambda z: z["p"])

    def origem(self) -> str:
        return origem_cpe(self.a, self.b, self.h)

    def forca_global(self) -> float:
        """Forca de arrasto pela diferenca barlavento-sotavento, kN."""
        cpe = cpe_paredes(self.a, self.b, self.h)
        return (cpe["C"] - cpe["D"]) * self.q() * self.b * self.h
