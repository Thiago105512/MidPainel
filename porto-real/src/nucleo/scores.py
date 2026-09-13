"""SCORES E LIBERACAO — o que o projeto vale e se pode sair (secoes 140 a 144,
121, 122).

Um score so serve se for AUDITAVEL: cada nota aqui sai de uma medida do modelo,
com a formula visivel, e nunca de julgamento. Score que ninguem consegue
reproduzir e propaganda.

E o checklist de liberacao nao tem caixa que se marque a mao. Cada item e uma
funcao que roda sobre o modelo e devolve verdadeiro ou falso — se fosse
marcavel, seria marcado.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

NIVEIS = ("CRITICO", "ERRO", "ATENCAO", "INFO")
NIVEL_DESC = {
    "CRITICO": "impede fabricacao",
    "ERRO": "precisa de correcao antes da liberacao",
    "ATENCAO": "revisar; pode seguir com registro",
    "INFO": "otimizacao possivel",
}

# (H) fatores de emissao. Vem de base de ACV — a ABNT NBR ISO 14040 exige
# origem declarada, e estes valores sao ordem de grandeza, nao medicao.
CO2E = dict(aco_virgem=2.30, aco_reciclado=0.68, osb=0.45, gesso=0.39,
            la_rocha=1.20, cimenticia=0.72, transporte_kg_km=0.00012)
RECICLADO_PADRAO = 0.30       # (H) fracao de sucata na carga do forno


def co2e(massa_aco: float, reciclado: float = RECICLADO_PADRAO,
         outros: dict = None, km: float = 0.0) -> dict:
    """CO2e incorporado, kg. Todo fator e (H) e esta declarado."""
    f = reciclado * CO2E["aco_reciclado"] + (1 - reciclado) * CO2E["aco_virgem"]
    aco = massa_aco * f
    demais = sum(m * CO2E.get(k, 0.0) for k, m in (outros or {}).items())
    transporte = (massa_aco + sum((outros or {}).values())) * km * \
        CO2E["transporte_kg_km"]
    return dict(aco=aco, outros=demais, transporte=transporte,
                total=aco + demais + transporte, fator_aco=f,
                reciclado=reciclado,
                nota="(H) fatores de emissao de base de ACV; origem a declarar")


def desmontabilidade(pecas: list, ligacoes_parafusadas: float = 1.0) -> dict:
    """Indice de desmontagem (secao 122): quanto se recupera inteiro.

    LSF parafusado e o sistema construtivo com maior desmontabilidade que
    existe em escala — o que perde essa vantagem e a colagem e a solda, nao o
    aco.
    """
    n = len(pecas) or 1
    padrao = {}
    for p in pecas:
        padrao[p.perfil] = padrao.get(p.perfil, 0) + 1
    repeticao = max(padrao.values()) / n if padrao else 0.0
    indice = 0.55 * ligacoes_parafusadas + 0.25 * repeticao + 0.20
    return dict(indice=min(1.0, indice), ligacoes_parafusadas=ligacoes_parafusadas,
                repeticao=repeticao, pecas=n, perfis=len(padrao),
                classe="alta" if indice > 0.75 else
                       ("media" if indice > 0.5 else "baixa"))


# ------------------------------------------------------------------ scores
def score_estrutural(utilizacoes: list, erros: int, atencoes: int) -> dict:
    """Uso alto demais e desperdicio; uso acima de 1 e falha."""
    if not utilizacoes:
        return dict(nota=0, motivo="sem verificacao estrutural rodada")
    acima = sum(1 for u in utilizacoes if u > 1.0)
    media = sum(utilizacoes) / len(utilizacoes)
    ociosos = sum(1 for u in utilizacoes if u < 0.30)
    nota = 100
    nota -= acima * 25
    nota -= erros * 15
    nota -= atencoes * 2
    nota -= (ociosos / len(utilizacoes)) * 20
    return dict(nota=max(0, min(100, round(nota))),
                media_utilizacao=media, acima_de_1=acima, ociosos=ociosos,
                formula="100 - 25 por peca acima de 1 - 15 por erro "
                        "- 2 por atencao - 20 x fracao de pecas ociosas")


def score_fabricacao(pecas: list, perfis_distintos: int,
                     aproveitamento: float, furos_por_peca: float) -> dict:
    n = len(pecas) or 1
    repeticao = n / max(1, perfis_distintos)
    nota = (35 * min(1.0, aproveitamento / 0.92)
            + 30 * min(1.0, repeticao / 60.0)
            + 20 * min(1.0, 6.0 / max(1.0, perfis_distintos))
            + 15 * min(1.0, 2.0 / max(0.5, furos_por_peca)))
    return dict(nota=round(nota), aproveitamento=aproveitamento,
                perfis=perfis_distintos, repeticao=repeticao,
                furos_por_peca=furos_por_peca,
                formula="35 aproveitamento + 30 repeticao + 20 poucos SKUs "
                        "+ 15 poucos furos")


def score_montagem(passos: int, massa_max: float, instabilidades: int,
                   horas: float, area: float) -> dict:
    h_m2 = horas / max(1.0, area)
    nota = 100
    nota -= instabilidades * 30
    nota -= max(0, (massa_max - 120) / 10)          # acima do icamento manual
    nota -= max(0, (h_m2 - 0.35) * 60)
    return dict(nota=max(0, min(100, round(nota))), passos=passos,
                massa_max=massa_max, h_por_m2=h_m2,
                instabilidades=instabilidades,
                formula="100 - 30 por instabilidade - 1 a cada 10 kg acima de "
                        "120 - 60 por h/m2 acima de 0,35")


def score_custo(custo_m2: float, referencia: float = 900.0) -> dict:
    nota = 100 * min(1.0, referencia / max(1.0, custo_m2))
    return dict(nota=round(nota), custo_m2=custo_m2, referencia=referencia,
                formula=f"100 x referencia/custo, com referencia (H) de "
                        f"R$ {referencia:.0f}/m2")


def score_logistica(uso_volume: float, uso_peso: float, rejeitados: int,
                    cg_desvio: float) -> dict:
    nota = (50 * min(1.0, max(uso_volume, uso_peso) / 0.85)
            + 30 * (1 - min(1.0, abs(cg_desvio) / 0.15))
            + 20 * (1 if rejeitados == 0 else 0))
    return dict(nota=round(nota), uso_volume=uso_volume, uso_peso=uso_peso,
                rejeitados=rejeitados, cg_desvio=cg_desvio,
                formula="50 ocupacao do container + 30 CG centrado "
                        "+ 20 nada rejeitado")


def score_sustentabilidade(co2_kg: float, area: float, desmont: float,
                           desperdicio: float) -> dict:
    kg_m2 = co2_kg / max(1.0, area)
    nota = (40 * min(1.0, 120.0 / max(1.0, kg_m2))
            + 35 * desmont
            + 25 * (1 - min(1.0, desperdicio / 0.15)))
    return dict(nota=round(nota), co2_por_m2=kg_m2, desmontabilidade=desmont,
                desperdicio=desperdicio,
                formula="40 CO2e por m2 + 35 desmontabilidade "
                        "+ 25 pouco desperdicio")


# ------------------------------------------------------- liberacao (140, 141)
CHECKLIST = (
    ("modelo conectado", "nenhum elemento solto no espaco"),
    ("cargas", "toda acao declarada com natureza e origem"),
    ("combinacoes", "ELU e ELS geradas, com permanente favoravel"),
    ("estabilidade", "contraventamento em cada direcao"),
    ("perfis aprovados", "nenhuma peca com utilizacao acima de 1"),
    ("ligacoes", "quantidade e espacamento verificados"),
    ("fundacao", "reacoes e chumbadores compativeis"),
    ("aberturas", "toda abertura com verga, king e jack stud"),
    ("MEP", "furacao dentro da zona util"),
    ("clashes", "nenhuma interferencia entre disciplinas"),
    ("painelizacao", "todo painel dentro do transporte ou com motivo"),
    ("fabricacao", "toda peca cabe em alguma maquina do parque"),
    ("nesting", "plano de corte fecha e nenhuma peca some"),
    ("BOM", "massa comprada fecha com a util e a perda"),
    ("revisao", "cadastro, emissao e pecas na mesma revisao"),
    ("documentacao", "memorial, lista de pecas e manual gerados"),
    # O decimo setimo item e de outra natureza: os dezesseis acima perguntam se
    # o que esta no modelo esta certo; este pergunta se o que precisa estar no
    # modelo esta la. A casa passou 31 revisoes sem vigamento com os dezesseis
    # verdes, porque nenhum deles sentia falta do que nunca foi escrito.
    ("completude", "todo sistema construtivo obrigatorio presente no modelo"),
)


def liberar(resultados: dict) -> dict:
    """Checklist de 17 itens. Nenhum se marca a mao (secao 140)."""
    itens, pendentes = [], []
    for cod, desc in CHECKLIST:
        v = resultados.get(cod)
        if v is None:
            itens.append(dict(item=cod, descricao=desc, status="NAO VERIFICADO"))
            pendentes.append(cod)
        elif v:
            itens.append(dict(item=cod, descricao=desc, status="OK"))
        else:
            itens.append(dict(item=cod, descricao=desc, status="REPROVA"))
            pendentes.append(cod)
    return dict(itens=itens, pendentes=pendentes,
                liberado=not pendentes,
                situacao="LIBERADO PARA FABRICACAO" if not pendentes else
                         f"NAO LIBERADO: {len(pendentes)} item(ns) pendente(s)")


def classificar(nivel: str, mensagem: str, solucoes: list = None) -> dict:
    """Motor de erros (secao 141) com auto-correcao sugerida (secao 35)."""
    if nivel not in NIVEIS:
        raise KeyError(f"nivel '{nivel}' nao existe: {NIVEIS}")
    return dict(nivel=nivel, efeito=NIVEL_DESC[nivel], mensagem=mensagem,
                solucoes=solucoes or [],
                bloqueia=nivel in ("CRITICO", "ERRO"))
