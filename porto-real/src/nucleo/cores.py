"""CORES — a familia estrutural e um dado; a cor dela e UMA, em um lugar.

R53 — o proprietario perguntou pelo padrao de cores das pecas de LSF nas
plantas ("laranja, azul"). A resposta honesta tem duas partes.

1. NAO EXISTE NORMA. NBR 15253 e NBR 14762 nao definem cor de peca. Cada
   software de fabricacao (FrameCAD, Vertex BD, Scottsdale) tem a sua paleta,
   e o fabricante que fizer o nesting (pendencia 8) le pela dele.

2. ESTE PROJETO TINHA TRES PALETAS, e nenhuma delas era "a" paleta: uma no 3D
   (modelo3d.CORES_LSF), outra no visualizador de engenharia
   (engenharia.CORES_FAMILIA) e diferencas entre as duas — o diagonal era
   amarelo num lugar e roxo no outro. Tres fontes para o mesmo fato, o padrao
   que este projeto persegue desde R31.

A decisao: UMA tabela, aqui, com a convencao que o proprietario reconhece —
GUIA laranja, MONTANTE azul — e o resto da familia derivado dela: king e jack
sao azuis mais escuro e mais claro (sao montantes), verga e ombreira sao
laranjas mais escuro e mais claro (sao horizontais como a guia), bloqueio e
travamento cinza (sao pecas secundarias), diagonal magenta (e a unica peca
inclinada e tem de saltar aos olhos), viga verde (pertence ao piso, nao a
parede). Quando o fabricante for escolhido, troca-se ESTA tabela e o 3D, a
prancha e a tela mudam juntos.
"""
from __future__ import annotations

CORES_PECA = {
    # verticais — a familia do montante, em azul
    "stud": "#2f6fc4",
    "king stud": "#1b4a8f",
    "jack stud": "#6aa0e0",
    "cripple superior": "#9dc0ea",
    "cripple inferior": "#7fb0e6",
    # horizontais de parede — a familia da guia, em laranja
    "track": "#e8801a",
    "header": "#b85a0c",
    "sill": "#f2a65a",
    # secundarias
    "blocking": "#9aa3ad",
    "travamento": "#b3bac2",
    # a unica inclinada
    "diagonal": "#c2338f",
    # piso e escada: outra familia, outra cor
    "viga": "#2f7d4f",
    "viga de borda": "#1d5c38",
    "viga de escada": "#b0562f",
    "degrau": "#d98a5a",
}

LEGENDA = [
    ("guia (track)", "track"), ("montante (stud)", "stud"),
    ("king stud", "king stud"), ("jack stud", "jack stud"),
    ("verga (header)", "header"), ("ombreira (sill)", "sill"),
    ("cripple", "cripple superior"), ("bloqueio", "blocking"),
    ("diagonal", "diagonal"), ("viga de piso", "viga"),
]

CONVENCAO = ("guia laranja, montante azul; verga e ombreira na familia da "
             "guia, king e jack na do montante; diagonal magenta; vigas de "
             "piso verdes. Sem norma: e convencao declarada, trocavel numa "
             "tabela quando o fabricante do nesting for definido")


def cor(familia: str) -> str:
    return CORES_PECA.get(familia, "#8a94a6")
