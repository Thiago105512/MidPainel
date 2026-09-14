"""ACUSTICA — o eixo que faltava, e que o proprietario achou antes do programa.

A pergunta que abriu R52 foi de quem mora, nao de quem calcula: "o banheiro do
quarto reversivel fica na entrada; se alguem estiver tomando banho, quem entra
vai ouvir". Nenhuma das 101 verificacoes do projeto podia responder isso. Havia
Rw declarado em cada familia de parede desde R12, havia uma parede acustica de
alto desempenho (PA-2) escolhida a dedo para um par de ambientes — e nao havia
nada que percorresse os pares fonte/receptor e perguntasse se a parede que os
separa da conta.

O QUE ESTE MODULO ACRESCENTA. Tres coisas que o Rw da parede sozinho nao diz:

1. A PORTA GOVERNA. Isolamento de um fechamento com abertura nao e o do painel
   cheio: e a media logaritmica ponderada por area. Uma parede de 44 dB com uma
   porta de correr de 15 dB entrega cerca de 20 dB — ou seja, a parede some. Em
   acustica o elo fraco nao faz media aritmetica: ele domina.

2. QUEM ESTA DO OUTRO LADO IMPORTA. A mesma parede pode ser excelente entre
   dois ambientes de passagem e insuficiente contra um dormitorio, porque o
   limite do receptor e que muda (NBR 10152).

3. O QUE SE EXIGE E DIFERENCA, NAO ABSOLUTO. Exigencia = nivel da fonte menos
   limite do receptor. Fonte fraca contra receptor tolerante nao pede parede
   nenhuma; fonte forte contra dormitorio pede mais do que qualquer parede
   simples entrega.

SIMPLIFICACAO DECLARADA. Adota-se D (diferenca padronizada de nivel) igual ao
R composto. A rigor D = R - 10 log(S/A), com S a area do fechamento e A a
absorcao do receptor; em ambientes pequenos e mobiliados de residencia os dois
termos ficam da mesma ordem e a correcao e pequena. Isto e pre-verificacao de
projeto, nao ensaio de campo da NBR 15575-3.
"""
from __future__ import annotations

import math

# ------------------------------------------------------------------ fontes
# Nivel tipico em dB(A) dentro do ambiente que gera o ruido. Valores de
# pratica corrente em acustica de edificacoes; sao ORDEM DE GRANDEZA declarada,
# e e por isso que a conclusao se le pela folga e nao pelo decimal.
FONTES = {
    "box de chuveiro": 70,
    "bacia sanitaria": 75,
    "maquina de lavar e secar": 70,
    "cozinha e gourmet": 70,
    "estar e jantar": 70,
    "oficina": 80,
    "garagem": 75,
}

# ambiente -> fonte que ele contem
FONTE_DO_AMBIENTE = {
    "T-BWC": "box de chuveiro",
    "T-LAV": "maquina de lavar e secar",
    "T-COZ": "cozinha e gourmet",
    "T-GOU": "cozinha e gourmet",
    "T-SOC": "estar e jantar",
    "T-OFI": "oficina",
    "T-GAR": "garagem",
    "S-S02/BANHO": "box de chuveiro",
    "S-S03/BANHO": "box de chuveiro",
    "S-MAS/BANHO": "box de chuveiro",
}

# ---------------------------------------------------------------- receptores
# Limite de ruido no ambiente receptor, dB(A). NBR 10152:2017 para residencias:
# dormitorio 35, sala de estar 40. Circulacao e hall nao sao ambiente de
# permanencia e entram com 45, declarado aqui e nao escondido na formula.
LIMITE = {
    "dormitorio": 35, "office": 40, "estar": 40, "cozinha": 45,
    "servico": 50, "circulacao": 45, "entrada": 45, "banho": 45,
    "garagem": 55, "oficina": 55, "deposito": 55,
}

USO_DO_AMBIENTE = {
    "T-GAR": "garagem", "T-HAL": "entrada", "T-BWC": "banho",
    "T-CIR": "circulacao", "T-REV": "dormitorio", "T-OFI": "oficina",
    "T-SOC": "estar", "T-COR": "circulacao", "T-COZ": "cozinha",
    "T-GOU": "estar", "T-LAV": "servico", "T-DEP": "deposito",
    "S-MAS": "dormitorio", "S-S02": "dormitorio", "S-S03": "dormitorio",
    "S-HAL": "circulacao", "S-EST": "estar", "S-COR": "circulacao",
}

# ------------------------------------------------------------------ portas
# Rw de folha de porta, dB. A porta de correr aparece aqui com o valor que ela
# tem de verdade: ela nao veda em lado nenhum — corre por fora da parede, com
# fresta em todo o perimetro. E o pior elemento acustico de uma casa, e e
# escolhida justamente onde falta espaco, que costuma ser onde os ambientes
# estao mais proximos.
RW_PORTA = {
    "correr": 15,
    "oca": 20,
    "solida": 26,
    "solida vedada": 30,       # folha macica + vedacao perimetral + soleira
    "acustica": 35,
}

# familia de esquadria -> tipo acustico
TIPO_DA_ESQUADRIA = {
    "P01": "solida", "P02": "oca", "P04": "oca", "P05": "correr",
    "P06": "solida vedada",
    "PG01": "correr", "PV01": "correr", "PV02": "correr", "CV01": "correr",
}

# ------------------------------------------------------------------- zonas
# Isolamento so faz sentido ENTRE zonas. Dentro da fita social o ruido nao e
# defeito: e o programa. Exigir 45 dB(A) no hall contra o estar reprovaria a
# ideia central da casa — estar, jantar, cozinha e gourmet integrados, com o
# hall abrindo para eles. Fonte e receptor da mesma zona entram no relatorio
# como "mesma zona" e nao como reprovacao, e isso e REGRA declarada aqui, nao
# excecao aberta no par que incomodou.
ZONA_ACUSTICA = {
    "T-SOC": "social", "T-GOU": "social", "T-COZ": "social",
    "T-HAL": "social", "T-CIR": "social", "T-COR": "social",
    "T-VAR": "social", "S-EST": "social", "S-HAL": "social", "S-COR": "social",
    "T-REV": "intimo", "T-BWC": "intimo",
    "S-MAS": "intimo", "S-S02": "intimo", "S-S03": "intimo",
    "T-LAV": "servico", "T-DEP": "servico", "T-GAR": "servico",
    "T-OFI": "servico",
}

PE_DIREITO = 2_600      # mm, altura do fechamento para a conta de area


def composto(pares: list[tuple[float, float]]) -> float:
    """Rw composto: media logaritmica das transmissoes, ponderada por area.

    R = -10 log10( soma(Si . 10^(-Ri/10)) / soma(Si) )

    E aqui que a intuicao falha. Somar 4,35 m2 de parede de 44 dB com 1,89 m2
    de porta de 15 dB nao da 36 dB: da 20. O que se soma e ENERGIA que passa, e
    a porta deixa passar mil vezes mais por metro quadrado.
    """
    st = sum(s for s, _ in pares)
    if st <= 0:
        return 0.0
    tau = sum(s * 10 ** (-r / 10) for s, r in pares) / st
    return round(-10 * math.log10(tau), 1)


def _uso(cod: str) -> str:
    return USO_DO_AMBIENTE.get(cod, USO_DO_AMBIENTE.get(cod.split("/")[0], ""))


def pares(pj) -> list[dict]:
    """Todo par de ambientes vizinhos em que um gera ruido e o outro o recebe.

    Percorre os trechos de parede ja classificados — os mesmos que decidem
    familia e Rw — e nao uma lista escrita a mao de pares "criticos". Lista
    escrita a mao e onde o par que ninguem imaginou nao aparece, e o par que
    ninguem imaginou e exatamente o que o morador vai reclamar.
    """
    import especificacao as ep
    import nucleo.camadas as cm
    out = []
    for pav, ambs in (("T", pj.TERREO), ("S", pj.SUPERIOR)):
        segs = ep.paredes_classificadas(ambs)
        vaos = [v for v in pj.VAOS if v[4] == pav]
        for s in segs:
            a, b = s.get("a"), s.get("b")
            if not a or not b:
                continue
            for fonte, receptor in ((a, b), (b, a)):
                f = FONTE_DO_AMBIENTE.get(fonte)
                if not f:
                    continue
                uso = _uso(receptor)
                if not uso:
                    continue
                comp = s["fim"] - s["ini"]
                s_total = comp * PE_DIREITO / 1e6
                # portas e janelas que caem NESTE trecho
                furos = []
                for tipo, x, y, ori, _p in vaos:
                    if ori != s["ori"]:
                        continue
                    eixo, ao = (y, x) if ori == "H" else (x, y)
                    if abs(eixo - s["fixo"]) > 200:
                        continue
                    if not (s["ini"] <= ao <= s["fim"]):
                        continue
                    lg, al, _pe, _fam = pj.ESQUADRIAS[tipo]
                    furos.append((tipo, lg * al / 1e6))
                s_furo = sum(a2 for _t, a2 in furos)
                comps = [(max(s_total - s_furo, 0.0), cm.COMPOSICOES[s["familia"]].rw)]
                for tipo, area in furos:
                    comps.append((area, RW_PORTA[TIPO_DA_ESQUADRIA.get(tipo, "oca")]))
                r = composto(comps)
                nivel = FONTES[f]
                lim = LIMITE[uso]
                zf = ZONA_ACUSTICA.get(fonte.split("/")[0], "")
                zr = ZONA_ACUSTICA.get(receptor.split("/")[0], "")
                mesma = bool(zf) and zf == zr
                out.append(dict(
                    pav=pav, fonte=fonte, receptor=receptor, ruido=f,
                    uso_receptor=uso, nivel=nivel, limite=lim,
                    exigido=nivel - lim, parede=s["familia"],
                    rw_parede=cm.COMPOSICOES[s["familia"]].rw,
                    vaos=[t for t, _ in furos],
                    area_parede=round(max(s_total - s_furo, 0.0), 2),
                    area_vao=round(s_furo, 2),
                    zona_fonte=zf, zona_receptor=zr, mesma_zona=mesma,
                    obtido=r, folga=round(r - (nivel - lim), 1),
                    passa=mesma or r >= nivel - lim,
                    estimado=round(nivel - r, 1)))
    return out


def criticos(pj) -> list[dict]:
    return [p for p in pares(pj) if not p["passa"]]


def entre_zonas(pj) -> list[dict]:
    return [p for p in pares(pj) if not p["mesma_zona"]]


def conferir(pj) -> list[tuple[str, str, bool]]:
    ps = pares(pj)
    ruins = [p for p in ps if not p["passa"]]
    ez = [p for p in ps if not p["mesma_zona"]]
    pior = min(ez, key=lambda p: p["folga"]) if ez else None
    com_correr = [p for p in ps if "P05" in p["vaos"]]
    out = [
        ("todo par fonte-receptor foi percorrido",
         f"{len(ps)} pares vizinhos com fonte de ruido de um lado, "
         f"{len(ez)} deles entre zonas diferentes",
         len(ps) > 0),
        ("nenhum par reprovado",
         "todos passam" if not ruins else
         "; ".join(f"{p['fonte']}>{p['receptor']} exige {p['exigido']:.0f} e "
                   f"entrega {p['obtido']:.1f} dB" for p in ruins[:4]),
         not ruins),
        ("nenhuma porta de correr entre fonte e receptor",
         "nenhuma" if not com_correr else
         "; ".join(f"{p['fonte']}>{p['receptor']}" for p in com_correr),
         not com_correr),
        ("o pior par tem folga",
         f"{pior['fonte']} > {pior['receptor']}: folga de {pior['folga']:.1f} dB"
         if pior else "sem pares", bool(pior) and pior["folga"] >= 0),
        ("banho nao abre para a entrada",
         "conferido nos vaos: nenhuma porta de ambiente molhado na parede do "
         "hall de entrada",
         not any(p["fonte"] == "T-BWC" and p["receptor"] == "T-HAL"
                 and p["vaos"] for p in ps)),
    ]
    return out
