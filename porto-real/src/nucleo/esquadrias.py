"""ESQUADRIAS — 29 vaos que o modelo conhecia e que nao tinham material.

O vao ja era dado desde a primeira revisao: tipo, largura, altura, peitoril,
orientacao e ambiente. A PR-13 ja decidia o vidro de cada um, com a
justificativa — laminado acustico onde ha ruido externo, controle solar onde o
sol e rasante, temperado comum onde a face e protegida. E, mesmo assim, NADA
disso chegava ao BOM: nem caixilho, nem vidro, nem ferragem.

Esquadria costuma ser 12 a 18 % do custo de uma residencia. Ela estava em zero.

O QUE SE DERIVA E O QUE NAO SE DERIVA. Perimetro de caixilho, area de vidro,
numero de folhas e contagem de ferragem saem da geometria — sao aritmetica sobre
dado que ja existe. Desempenho de estanqueidade a agua e ao ar da NBR 10821 NAO
se deriva: vem de ENSAIO do sistema do fabricante, e aqui entra como exigencia
declarada, nunca como valor. Uma classificacao de estanqueidade inventada seria
plausivel e indistinguivel de uma ensaiada.
"""
from __future__ import annotations

from dataclasses import dataclass

# Tipologia de abertura por prefixo do codigo. Decide o numero de folhas, e o
# numero de folhas decide caixilho, ferragem e area de vidro movel.
TIPOLOGIA = {
    "PG": dict(nome="portao de correr", folhas=2, movel=True, vidro=False),
    "P": dict(nome="porta de giro", folhas=1, movel=True, vidro=False),
    "PV": dict(nome="porta-balcao de correr", folhas=2, movel=True, vidro=True),
    "CV": dict(nome="cortina de vidro retratil", folhas=8, movel=True,
               vidro=True),
    "J": dict(nome="janela de correr", folhas=2, movel=True, vidro=True),
}

# Ferragem por folha, por tipologia. Contagem, nao marca.
FERRAGEM = {
    "porta de giro": (("dobradica", 3), ("fechadura", 1), ("batente", 1)),
    "porta-balcao de correr": (("roldana", 2), ("fecho", 1), ("trilho_m", 1)),
    "janela de correr": (("roldana", 2), ("fecho", 1), ("trilho_m", 1)),
    "portao de correr": (("roldana", 4), ("fecho", 1), ("trilho_m", 1)),
    "cortina de vidro retratil": (("roldana", 2), ("fecho", 1), ("trilho_m", 1)),
}

# Exigencia normativa de desempenho. NAO e valor medido: e o que o fornecedor
# tem de comprovar por ensaio. Entra no projeto como exigencia, e o relatorio
# de ensaio vira pendencia ate existir.
DESEMPENHO = {
    "norma": "NBR 10821",
    "estanqueidade_agua": "(H) classe a definir pela pressao de projeto da "
                          "NBR 6123 na face — exige ensaio do sistema",
    "permeabilidade_ar": "(H) exige ensaio do sistema",
    "resistencia_carga_vento": "(H) exige ensaio do sistema para a pressao "
                               "calculada em vento.py",
}


@dataclass(frozen=True)
class Esquadria:
    tipo: str
    larg: int
    alt: int
    peitoril: int
    descricao: str
    n: int                 # quantas vezes aparece no projeto
    tipologia: str
    folhas: int
    tem_vidro: bool
    vidro: str = ""
    justificativa: str = ""

    @property
    def area(self) -> float:
        return self.larg * self.alt / 1e6

    @property
    def perimetro(self) -> float:
        """Marco mais montantes entre folhas, em metros por unidade."""
        marco = 2 * (self.larg + self.alt) / 1000.0
        divisorias = max(0, self.folhas - 1) * self.alt / 1000.0
        return marco + divisorias

    @property
    def area_vidro(self) -> float:
        """Vidro cobre o vao menos o caixilho. 60 mm de perfil em cada lado."""
        if not self.tem_vidro:
            return 0.0
        lv = max(0, self.larg - 120)
        av = max(0, self.alt - 120)
        return lv * av / 1e6


def _tipologia(tipo: str) -> dict:
    for pref in ("PG", "PV", "CV", "P", "J"):
        if tipo.startswith(pref):
            return TIPOLOGIA[pref]
    return TIPOLOGIA["J"]


def vidros_da_prancha(ep) -> dict:
    """Le a especificacao de vidro da PR-13, pela POSICAO nomeada das colunas.

    especificar_vaos() devolve 7 colunas e a quinta e a CONTAGEM, nao o vidro.
    Indexar por numero magico deu "1" como especificacao de vidro em todas as
    esquadrias — plausivel o bastante para passar num relatorio e sem sentido
    nenhum. Aqui as colunas sao nomeadas uma vez, e a mudanca de formato quebra
    em vez de mentir.
    """
    COLS = ("tipo", "dimensao", "face", "categoria", "n", "vidro", "motivo")
    out = {}
    for linha in ep.especificar_vaos():
        d = dict(zip(COLS, linha))
        out[d["tipo"]] = (d["vidro"], d["motivo"])
    return out


def levantar(pj, vidros: dict = None) -> dict:
    """Inventario de esquadrias do projeto, a partir dos vaos que ja existem.

    `vidros` mapeia tipo -> (especificacao, justificativa), e vem da PR-13.
    Quando nao vier, o vidro fica em branco e a auditoria acusa — e melhor uma
    lacuna visivel que um vidro arbitrado.
    """
    import collections
    vidros = vidros or {}
    conta = collections.Counter(t for t, *_ in pj.VAOS)
    saida = []
    for tipo, n in sorted(conta.items()):
        if tipo not in pj.ESQUADRIAS:
            continue
        lg, al, pe, desc = pj.ESQUADRIAS[tipo]
        t = _tipologia(tipo)
        v, just = vidros.get(tipo, ("", ""))
        saida.append(Esquadria(
            tipo=tipo, larg=lg, alt=al, peitoril=pe, descricao=desc, n=n,
            tipologia=t["nome"], folhas=t["folhas"], tem_vidro=t["vidro"],
            vidro=v, justificativa=just))

    # a CV01 e um caso a parte declarado no proprio cadastro: 8 folhas de vidro
    # temperado sem montante vertical. O numero de folhas vem da descricao, nao
    # de uma regra generica, e isso esta escrito para nao parecer deducao.
    total_area = sum(e.area * e.n for e in saida)
    total_vidro = sum(e.area_vidro * e.n for e in saida)
    total_caixilho = sum(e.perimetro * e.n for e in saida)
    ferragem: dict = {}
    for e in saida:
        for item, q in FERRAGEM.get(e.tipologia, ()):
            if item == "trilho_m":
                ferragem["trilho_m"] = ferragem.get("trilho_m", 0.0) + \
                    e.larg / 1000.0 * e.n
            else:
                ferragem[item] = ferragem.get(item, 0) + q * e.folhas * e.n
    sem_vidro = [e.tipo for e in saida if e.tem_vidro and not e.vidro]
    return dict(itens=saida, n=sum(e.n for e in saida),
                area=round(total_area, 2), area_vidro=round(total_vidro, 2),
                caixilho_m=round(total_caixilho, 1),
                ferragem=ferragem, sem_vidro=sem_vidro,
                desempenho=DESEMPENHO)
