"""MONTAGEM — a ordem em que a casa sobe (secoes 32, 33, 55 a 58).

A sequencia de montagem nao e uma lista de tarefas: e uma ordem PARCIAL com
restricoes fisicas. Um painel so sobe se o piso onde ele apoia ja existe; uma
laje so fecha se as paredes que a sustentam estao travadas; um parafuso so se
instala se a peca que o esconde ainda nao chegou.

Por isso a ordem sai de uma ordenacao topologica, e nao de um cronograma
digitado. E por isso a DESMONTAGEM e a inversa exata: se a ordem foi derivada,
inverte-se; se foi digitada, alguem tem de digitar de novo e vai errar.

A verificacao que mais importa: em nenhum passo a estrutura pode ficar
instavel. Um painel de pe, sozinho, sem o de canto e sem o piso superior, e um
painel que cai — e essa e a causa mais comum de acidente em obra de LSF.
"""
from __future__ import annotations

from dataclasses import dataclass, field

FERRAMENTAS = {
    "guia": "parafusadeira comum", "montante": "parafusadeira comum",
    "painel": "guindaste ou 4 pessoas", "laje": "guindaste",
    "contraventamento": "parafusadeira e esquadro",
    "hold-down": "chave de torque", "chumbador": "furadeira e torquimetro",
}


@dataclass
class Etapa:
    cod: str
    tipo: str                  # fundacao, painel, laje, cobertura, fechamento
    descricao: str
    depende: tuple = ()        # codigos que precisam estar prontos
    massa: float = 0.0
    duracao_h: float = 0.0
    ferramenta: str = ""
    estabiliza: tuple = ()     # o que esta etapa passa a travar
    exige_travado: tuple = ()  # o que ja precisa estar travado


def ordenar(etapas: list) -> dict:
    """Ordenacao topologica com deteccao de ciclo (secao 56).

    Ciclo aqui nao e detalhe: significa que A precisa de B e B precisa de A, ou
    seja, a montagem e IMPOSSIVEL como projetada. Devolver uma ordem qualquer
    nesse caso seria esconder um erro de projeto.
    """
    por_cod = {e.cod: e for e in etapas}
    faltando = {d for e in etapas for d in e.depende if d not in por_cod}
    if faltando:
        return dict(ordem=[], erro=f"dependencias inexistentes: {sorted(faltando)}")
    entrada = {e.cod: 0 for e in etapas}
    saida = {e.cod: [] for e in etapas}
    for e in etapas:
        for d in e.depende:
            entrada[e.cod] += 1
            saida[d].append(e.cod)
    # entre os prontos, sobe primeiro o mais pesado: o guindaste ja esta la
    prontos = sorted([c for c, n in entrada.items() if n == 0],
                     key=lambda c: -por_cod[c].massa)
    ordem = []
    while prontos:
        c = prontos.pop(0)
        ordem.append(c)
        for s in saida[c]:
            entrada[s] -= 1
            if entrada[s] == 0:
                prontos.append(s)
                prontos.sort(key=lambda k: -por_cod[k].massa)
    if len(ordem) != len(etapas):
        ciclo = sorted(c for c, n in entrada.items() if n > 0)
        return dict(ordem=[], erro=f"ciclo de dependencia entre {ciclo}: a "
                                   f"montagem e impossivel como projetada")
    return dict(ordem=ordem, erro="")


def verificar_estabilidade(etapas: list, ordem: list) -> list[str]:
    """Em nenhum passo a estrutura pode ficar instavel."""
    por_cod = {e.cod: e for e in etapas}
    travado, falhas = set(), []
    for i, c in enumerate(ordem, 1):
        e = por_cod[c]
        falta = [t for t in e.exige_travado if t not in travado]
        if falta:
            falhas.append(f"passo {i} ({c}): exige {falta} travado(s), e nada "
                          f"trava isso ainda — a estrutura fica instavel")
        travado.update(e.estabiliza)
    return falhas


def passo_a_passo(etapas: list, ordem: list) -> list[dict]:
    """A instrucao que vai para o tablet do montador (secao 55)."""
    por_cod = {e.cod: e for e in etapas}
    out, acum = [], 0.0
    total = sum(e.duracao_h for e in etapas) or 1.0
    for i, c in enumerate(ordem, 1):
        e = por_cod[c]
        acum += e.duracao_h
        out.append(dict(passo=i, cod=c, tipo=e.tipo, descricao=e.descricao,
                        massa=e.massa, ferramenta=e.ferramenta or
                        FERRAMENTAS.get(e.tipo, "parafusadeira comum"),
                        duracao_h=e.duracao_h, acumulado_h=acum,
                        progresso=acum / total))
    return out


def desmontagem(ordem: list) -> list:
    """A inversa exata (secao 58). Se a ordem foi derivada, isto e de graca."""
    return list(reversed(ordem))


def marcos(passos: list) -> list[dict]:
    """Os marcos da timeline de montagem (secao 57)."""
    alvos = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
    out, i = [], 0
    for a in alvos:
        while i < len(passos) - 1 and passos[i]["progresso"] < a:
            i += 1
        out.append(dict(progresso=a, passo=passos[i]["passo"],
                        tipo=passos[i]["tipo"], cod=passos[i]["cod"]))
    return out


def etapas_do_projeto(paineis_por_pav: dict, cat_massa: dict) -> list[Etapa]:
    """Gera a sequencia a partir dos paineis reais, nao de um cronograma."""
    et = [Etapa("FUND", "fundacao", "Radier curado e nivelado, chumbadores "
                "posicionados", (), 0.0, 0.0, "furadeira e torquimetro",
                estabiliza=("radier",))]
    anterior_laje = "FUND"
    for pav, paineis in paineis_por_pav.items():
        cantos = [p for p in paineis if p.externa][:2]
        for p in paineis:
            dep = (anterior_laje,)
            if p not in cantos and cantos:
                dep = (anterior_laje, f"PA-{pav}-{cantos[0].cod}")
            et.append(Etapa(
                f"PA-{pav}-{p.cod}", "painel",
                f"Painel {p.cod}: {p.comp} x {p.altura} mm, "
                f"{len(p.pecas)} pecas", dep,
                p.massa(cat_massa), max(0.5, p.massa(cat_massa) / 60.0),
                estabiliza=(f"parede-{pav}",),
                exige_travado=("radier",) if pav == "T" else ("laje-T",)))
        et.append(Etapa(f"CV-{pav}", "contraventamento",
                        f"Contraventamento do pavimento {pav}",
                        tuple(f"PA-{pav}-{p.cod}" for p in paineis),
                        0.0, 4.0, estabiliza=(f"contraventado-{pav}",),
                        exige_travado=(f"parede-{pav}",)))
        et.append(Etapa(f"LA-{pav}", "laje", f"Laje sobre o pavimento {pav}",
                        (f"CV-{pav}",), 0.0, 8.0,
                        estabiliza=(f"laje-{pav}",),
                        exige_travado=(f"contraventado-{pav}",)))
        anterior_laje = f"LA-{pav}"
    et.append(Etapa("COB", "cobertura", "Cobertura e platibanda",
                    (anterior_laje,), 0.0, 16.0,
                    exige_travado=(anterior_laje.replace("LA-", "laje-"),),
                    estabiliza=("cobertura",)))
    et.append(Etapa("FECH", "fechamento", "Placas, isolamento e membranas",
                    ("COB",), 0.0, 40.0, estabiliza=("fechado",),
                    exige_travado=("cobertura",)))
    return et
