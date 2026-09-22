"""OTIMIZACAO — a decisao global, nao a soma de decisoes locais (secoes 19 a 22,
124, 147 a 150).

Otimizar peca a peca produz a estrutura mais leve possivel e, quase sempre, a
mais CARA de construir. O perfil ideal de cada montante e diferente do vizinho;
a fabrica passa a estocar doze SKUs; o montador passa a escolher; o inspetor
passa a conferir. O aco economizado nao paga nada disso.

Por isso a otimizacao aqui e global e ponderada: custo, peso, numero de SKUs,
desperdicio, tempo de montagem e carbono entram juntos, com peso declarado. Uma
solucao 5 % mais pesada pode vencer — e o relatorio precisa dizer POR QUE.

Toda escolha sai com as alternativas rejeitadas e o motivo (secao 20). Sistema
que diz so o resultado e caixa-preta, e a especificacao proibe isso
explicitamente.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

OBJETIVOS = {
    "custo": "menor custo total",
    "peso": "menor massa de aco",
    "sku": "menor numero de perfis diferentes",
    "desperdicio": "menor perda no plano de corte",
    "montagem": "menor tempo de montagem",
    "fabricacao": "menor tempo de fabrica",
    "carbono": "menor CO2e incorporado",
    "repeticao": "maior repeticao de pecas iguais",
}
PESOS_PADRAO = dict(custo=0.35, peso=0.10, sku=0.20, desperdicio=0.15,
                    montagem=0.15, carbono=0.05)


@dataclass
class Solucao:
    cod: str
    descricao: str
    metricas: dict          # {objetivo: valor bruto}
    detalhe: dict = field(default_factory=dict)


def normalizar(solucoes: list, objetivo: str, menor_melhor=True) -> dict:
    """Escala 0..1 dentro do conjunto. Sem isso, kg competiria com reais."""
    vals = [s.metricas.get(objetivo, 0.0) for s in solucoes]
    lo, hi = min(vals), max(vals)
    if abs(hi - lo) < 1e-12:
        return {s.cod: 1.0 for s in solucoes}
    return {s.cod: (1 - (s.metricas[objetivo] - lo) / (hi - lo)) if menor_melhor
                   else ((s.metricas[objetivo] - lo) / (hi - lo))
            for s in solucoes}


def ranquear(solucoes: list, pesos: dict = None) -> list[dict]:
    """Ranking multiobjetivo ponderado, com a nota de cada objetivo aberta."""
    p = dict(PESOS_PADRAO)
    p.update(pesos or {})
    soma = sum(p.values())
    p = {k: v / soma for k, v in p.items()}
    notas = {}
    for obj in p:
        maior_melhor = obj == "repeticao"
        notas[obj] = normalizar(solucoes, obj, menor_melhor=not maior_melhor)
    out = []
    for s in solucoes:
        parciais = {o: notas[o][s.cod] for o in p}
        total = sum(parciais[o] * p[o] for o in p)
        out.append(dict(cod=s.cod, descricao=s.descricao, nota=total,
                        parciais=parciais, pesos=p, metricas=s.metricas))
    return sorted(out, key=lambda d: -d["nota"])


def pareto(solucoes: list, objetivos: list) -> list[str]:
    """Fronteira de Pareto: o que nao e dominado por ninguem."""
    frente = []
    for a in solucoes:
        dominado = False
        for b in solucoes:
            if a.cod == b.cod:
                continue
            melhor_ou_igual = all(b.metricas[o] <= a.metricas[o] for o in objetivos)
            estrita = any(b.metricas[o] < a.metricas[o] for o in objetivos)
            if melhor_ou_igual and estrita:
                dominado = True
                break
        if not dominado:
            frente.append(a.cod)
    return frente


def explicar(ranking: list) -> str:
    """Por que o primeiro venceu — em uma frase que um humano le (secao 20)."""
    if not ranking:
        return "nenhuma solucao valida"
    v, s = ranking[0], (ranking[1] if len(ranking) > 1 else None)
    if not s:
        return f"{v['cod']} e a unica solucao valida"
    ganhou = sorted(((v["parciais"][o] - s["parciais"][o]) * v["pesos"][o], o)
                    for o in v["parciais"])
    perdeu = [o for d, o in ganhou if d < -1e-9]
    venceu = [o for d, o in reversed(ganhou) if d > 1e-9]
    frase = (f"{v['cod']} vence {s['cod']} por {v['nota']-s['nota']:.3f} "
             f"ganhando em {venceu[:3]}")
    if perdeu:
        frase += (f", apesar de PERDER em {perdeu[:2]} — e a diferenca nesses "
                  f"nao compensa a vantagem nos demais")
    return frase


def padronizar(escolhas: dict, alternativas: dict, max_sku: int) -> dict:
    """Reduz a variedade de perfis substituindo pelo mais forte da familia.

    escolhas: {elemento: perfil}. alternativas: {elemento: [perfis validos]}.
    A substituicao so acontece por um perfil que TAMBEM passa na verificacao —
    padronizar nunca pode reduzir seguranca.
    """
    usados = {}
    for el, perf in escolhas.items():
        usados.setdefault(perf, []).append(el)
    if len(usados) <= max_sku:
        return dict(escolhas=dict(escolhas), skus=len(usados), trocas=[],
                    motivo=f"{len(usados)} SKUs ja esta dentro do limite")
    # os menos usados sao os candidatos a sumir
    ordem = sorted(usados, key=lambda p: len(usados[p]))
    novas, trocas = dict(escolhas), []
    for perf in ordem:
        if len(set(novas.values())) <= max_sku:
            break
        for el in usados[perf]:
            validos = [a for a in alternativas.get(el, [])
                       if a in set(novas.values()) and a != perf]
            if validos:
                escolhido = validos[0]
                novas[el] = escolhido
                trocas.append(dict(elemento=el, de=perf, para=escolhido,
                                   motivo="perfil ja usado em outro elemento e "
                                          "aprovado na verificacao deste"))
    return dict(escolhas=novas, skus=len(set(novas.values())), trocas=trocas,
                motivo=f"de {len(usados)} para {len(set(novas.values()))} SKUs, "
                       f"com {len(trocas)} trocas, todas por perfil que ja "
                       f"passava na verificacao do elemento")


def what_if(base: Solucao, mudanca: dict, recalcular) -> dict:
    """Simulacao de troca: o que muda em cada metrica (secao 149)."""
    nova = recalcular(mudanca)
    delta = {k: nova.metricas.get(k, 0) - base.metricas.get(k, 0)
             for k in set(base.metricas) | set(nova.metricas)}
    return dict(base=base.metricas, nova=nova.metricas, delta=delta,
                mudanca=mudanca,
                resumo={k: (f"{v:+.1f}" if abs(v) >= 1 else f"{v:+.3f}")
                        for k, v in sorted(delta.items())})
