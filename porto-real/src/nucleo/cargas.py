"""CARGAS — acoes permanentes e variaveis (secao 12, NBR 6120:2019).

Uma carga aqui nao e um numero: e um objeto com origem, natureza, direcao e
distribuicao. A natureza importa porque e ela que decide o coeficiente de
ponderacao e o fator de reducao na combinacao — uma sobrecarga de piso e uma
carga de vento entram na mesma soma com pesos diferentes, e confundir as duas e
o erro que a combinacao automatica existe para impedir.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# natureza da acao -> como a NBR 8681 a trata
NATUREZAS = {
    "permanente": "peso proprio e tudo que nao sai do lugar",
    "permanente_var": "permanente de variabilidade grande (enchimento, revestimento)",
    "acidental": "uso e ocupacao",
    "vento": "acao do vento",
    "temperatura": "variacao uniforme de temperatura",
    "excepcional": "impacto, explosao, sismo",
}

TIPOS = ("pontual", "linear", "distribuida", "superficial", "trapezoidal", "momento")


@dataclass
class Carga:
    cod: str
    natureza: str
    tipo: str
    valor: float                 # kN, kN/m ou kN/m2 conforme o tipo
    direcao: str = "-Z"          # -Z = gravidade; +X, -X, +Y, -Y = horizontal
    onde: str = ""               # elemento, pavimento ou zona
    origem: str = ""             # de onde o numero veio
    valor_fim: float = None      # so para trapezoidal
    obs: str = ""

    def __post_init__(self):
        if self.natureza not in NATUREZAS:
            raise ValueError(f"natureza '{self.natureza}' desconhecida")
        if self.tipo not in TIPOS:
            raise ValueError(f"tipo '{self.tipo}' desconhecido")


# Sobrecargas da NBR 6120:2019, kN/m2. Sao valores de norma, nao de projeto.
SOBRECARGA_NBR6120 = {
    "dormitorio": 1.5, "sala": 1.5, "cozinha residencial": 1.5,
    "area de servico": 2.0, "despensa": 2.0, "sanitario": 1.5,
    "escada residencial": 2.5, "escada coletiva": 3.0,
    "corredor residencial": 2.0, "corredor coletivo": 3.0,
    "escritorio": 2.5, "sala de aula": 3.0, "biblioteca": 6.0,
    "loja": 4.0, "restaurante": 3.0, "consultorio": 2.0,
    "quarto de hotel": 1.5, "garagem leve": 3.0,
    "terraco sem acesso": 2.0, "terraco com acesso": 3.0,
    "cobertura manutencao": 0.5, "sacada": 3.0,
    "forro sem uso": 0.5, "atico acessivel": 1.5,
}

# Pesos especificos usuais, kN/m3 (NBR 6120 anexo)
PESO_ESPECIFICO = {
    "concreto armado": 25.0, "alvenaria ceramica": 13.0, "argamassa": 21.0,
    "aco": 78.5, "madeira": 5.0, "agua": 10.0, "brita": 18.0,
    "gesso": 12.5, "porcelanato": 23.0, "terra umida": 18.0,
}

# Cargas de equipamento e uso, kN (secao 12)
EQUIPAMENTOS = {
    "reservatorio 1000 L": 10.0, "reservatorio 2000 L": 20.0,
    "condensadora 9-18k": 0.6, "condensadora 24-36k": 1.0,
    "evaporadora duto": 0.5, "placa solar fotovoltaica": 0.15,
    "aquecedor solar 300 L": 3.5, "maquina de lavar": 1.0,
    "banheira 300 L": 3.5,
}


def sobrecarga(uso: str) -> float:
    """Sobrecarga normativa do ambiente, kN/m2. Erro explicito se nao houver."""
    if uso not in SOBRECARGA_NBR6120:
        raise KeyError(f"uso '{uso}' sem sobrecarga na NBR 6120 — declare a carga")
    return SOBRECARGA_NBR6120[uso]


def peso_camadas(camadas: list[tuple]) -> float:
    """Peso proprio de um pacote [(material, espessura_mm)], em kN/m2."""
    total = 0.0
    for mat, esp in camadas:
        if mat not in PESO_ESPECIFICO:
            raise KeyError(f"'{mat}' sem peso especifico declarado")
        total += PESO_ESPECIFICO[mat] * esp / 1000.0
    return total
