"""ELETRICA — a decisao do proprietario virou circuito, fase e corrente.

R52 fechou a pendencia 7 com a frase do proprietario: trifasico, 127 V para a
maioria dos eletrodomesticos, 220 V para ar-condicionado e chuveiros. Isso
confere com a rede da concessionaria local, que em baixa tensao trifasica
fornece 220/127 V (estrela com neutro). Ate R51 o esquema estava no modelo
marcado (H): ninguem tinha confirmado, e havia projeto inteiro dependendo dele.

O QUE A CONFIRMACAO TROUXE DE TRABALHO NOVO. Um sistema 220/127 nao e "um so
sistema com duas tensoes": e uma estrela com neutro onde cargas de 127 V ficam
entre FASE e NEUTRO e cargas de 220 V entre DUAS FASES. Isso cria um problema
que nao existe em instalacao monofasica e que nenhuma verificacao do projeto
enxergava: o DESEQUILIBRIO. Se as cargas de 127 V se acumulam numa fase, essa
fase aquece, a tensao cai nela, o neutro conduz a diferenca — e o resto da casa
nao percebe nada ate a lampada piscar quando a secadora liga.

Equilibrar nao e detalhe de montagem: e projeto. E so da para fazer com a lista
de circuitos na mao, que e exatamente o que o modelo ja tinha e ninguem havia
percorrido nesse sentido.
"""
from __future__ import annotations

import math

FASES = ("A", "B", "C")
TENSAO_FN = 127
TENSAO_FF = 220
CONCESSIONARIA = "Amazonas Energia — NDEE-02, BT edificacoes individuais"
LIMITE_DESEQUILIBRIO = 0.10      # 10 % entre a fase mais e a menos carregada

# quanta corrente cada secao de cobre aguenta no ramal de entrada (B1, 3 cond.
# carregados, 30 C). E a mesma tabela que demanda_eletrica() ja usava; aqui ela
# ganha o disjuntor e a razao.
RAMAL = ((10, 50), (16, 68), (25, 89), (35, 111), (50, 134), (70, 171))
DISJUNTORES = (40, 50, 63, 80, 100, 125, 150)


def _pe(s: float) -> float:
    """Condutor de protecao pela Tabela 58 da NBR 5410.

    Nao e "metade da fase" nem "16 mm2 sempre": e uma tabela em degraus, e o
    degrau do meio — 16 < S <= 35, que da PE de 16 — e justamente onde este
    projeto cai. Dividir 35 por 2 daria 17,5 mm2, secao que nao existe.
    """
    if s <= 16:
        return s
    if s <= 35:
        return 16
    return s / 2


def circuitos(pj) -> list[dict]:
    """Todos os circuitos terminais, com tensao e VA.

    Iluminacao e TUG saem da previsao por ambiente (NBR 5410 9.5.2.1 e
    9.5.2.2); cada carga especial e um circuito proprio, como a norma manda
    para equipamento de mais de 1.500 VA.
    """
    out = []
    for p in pj.previsao_iluminacao_tug():
        if p["ilum_va"]:
            out.append(dict(cod=f"ILU-{p['amb']}", amb=p["amb"], tipo="iluminacao",
                            va=p["ilum_va"], v=TENSAO_FN))
        if p["tug_va"]:
            out.append(dict(cod=f"TUG-{p['amb']}", amb=p["amb"], tipo="tug",
                            va=p["tug_va"], v=TENSAO_FN))
    for c in pj.CARGAS_ESPECIAIS:
        out.append(dict(cod=c["cod"], amb=c.get("amb", ""), tipo="tue",
                        va=c["va"], v=c["v"], fd=c["fd"], grupo=c["grupo"],
                        desc=c["desc"]))
    return out


def equilibrar(pj) -> dict:
    """Distribui os circuitos entre as tres fases, do maior para o menor.

    Heuristica do maior primeiro: e a mesma da montagem de quadro na obra, e
    da resultado proximo do otimo com uma fracao do esforco. O que importa
    aqui nao e achar a melhor divisao possivel — e PROVAR que existe divisao
    dentro do limite, e deixar a atribuicao escrita no projeto em vez de
    delegar ao eletricista a decisao que muda a corrente de cada fase.
    """
    carga = {f: 0.0 for f in FASES}
    atrib = []
    for c in sorted(circuitos(pj), key=lambda q: -q["va"]):
        if c["v"] == TENSAO_FN:
            f = min(FASES, key=lambda k: carga[k])
            carga[f] += c["va"]
            atrib.append({**c, "fases": (f,)})
        else:
            # carga de 220 V ocupa DUAS fases, com metade em cada uma
            par = sorted(FASES, key=lambda k: carga[k])[:2]
            for f in par:
                carga[f] += c["va"] / 2
            atrib.append({**c, "fases": tuple(sorted(par))})
    vmax, vmin = max(carga.values()), min(carga.values())
    med = sum(carga.values()) / 3
    return dict(por_fase={k: round(v, 1) for k, v in carga.items()},
                circuitos=atrib, media=round(med, 1),
                desequilibrio=round((vmax - vmin) / med, 4) if med else 0.0,
                limite=LIMITE_DESEQUILIBRIO,
                corrente_por_fase={k: round(v / TENSAO_FN, 1)
                                   for k, v in carga.items()},
                obs="VA instalado por fase; a corrente de projeto aplica os "
                    "fatores de demanda em demanda_eletrica()")


def entrada(pj) -> dict:
    """Padrao de entrada: corrente, disjuntor, cabo e o que a norma exige."""
    d = pj.demanda_eletrica()
    i = d["corrente_a"]
    disj = next(x for x in DISJUNTORES if x >= i)
    secao = next(s for s, lim in RAMAL if lim >= disj)
    return dict(demanda_va=d["demanda_va"], corrente_a=i,
                disjuntor_a=disj, secao_mm2=secao,
                tipo="trifasico 220/127 V (estrela com neutro)",
                concessionaria=CONCESSIONARIA,
                neutro_mm2=secao,
                aterramento_mm2=_pe(secao),
                obs="o cabo e escolhido pelo DISJUNTOR e nao pela corrente de "
                    "demanda: quem protege o cabo e o disjuntor, e cabo que "
                    "so aguenta a demanda queima antes de o disjuntor abrir")


def conferir(pj) -> list[tuple[str, str, bool]]:
    eq = equilibrar(pj)
    en = entrada(pj)
    c220 = [c for c in eq["circuitos"] if c["v"] == TENSAO_FF]
    c127 = [c for c in eq["circuitos"] if c["v"] == TENSAO_FN]
    duas = [c for c in c220 if len(c["fases"]) != 2]
    uma = [c for c in c127 if len(c["fases"]) != 1]
    aquec = [c for c in eq["circuitos"] if c.get("grupo") == "aquecimento"]
    return [
        ("esquema confirmado pelo proprietario",
         f"{en['tipo']} — {pj.TENSAO['esquema']}",
         "(H)" not in pj.TENSAO["esquema"]),
        ("desequilibrio entre fases",
         f"{eq['desequilibrio']*100:.2f} % contra {eq['limite']*100:.0f} % "
         f"admitidos — A {eq['por_fase']['A']:.0f}, B {eq['por_fase']['B']:.0f}, "
         f"C {eq['por_fase']['C']:.0f} VA",
         eq["desequilibrio"] <= eq["limite"]),
        ("carga de 220 V entre duas fases",
         f"{len(c220)} circuitos de {TENSAO_FF} V, todos F-F"
         if not duas else f"{len(duas)} circuitos de 220 V mal atribuidos",
         not duas),
        ("carga de 127 V entre fase e neutro",
         f"{len(c127)} circuitos de {TENSAO_FN} V, todos F-N"
         if not uma else f"{len(uma)} circuitos de 127 V mal atribuidos",
         not uma),
        ("chuveiro e ar em 220 V",
         f"{len(aquec)} circuitos de aquecimento, todos em "
         f"{ {c['v'] for c in aquec} }",
         all(c["v"] == TENSAO_FF for c in aquec)),
        ("cabo dimensionado pelo disjuntor",
         f"disjuntor {en['disjuntor_a']} A e cabo {en['secao_mm2']} mm2 para "
         f"{en['corrente_a']:.1f} A de demanda",
         next(lim for s, lim in RAMAL if s == en["secao_mm2"])
         >= en["disjuntor_a"]),
        ("cada carga especial tem circuito proprio",
         f"{len(pj.CARGAS_ESPECIAIS)} circuitos terminais dedicados",
         len(pj.CARGAS_ESPECIAIS) == len([c for c in eq["circuitos"]
                                          if c["tipo"] == "tue"])),
    ]
