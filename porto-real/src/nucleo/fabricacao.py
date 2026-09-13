"""FABRICACAO — CNC, linha, tempo e qualidade (secoes 67 a 75, 129, 130).

O arquivo de CNC e o unico documento do projeto que uma maquina le sozinha. Por
isso ele nao pode conter interpretacao: cada peca sai com comprimento, cortes,
furos, recortes e marcacao em coordenadas absolutas, na ordem em que a maquina
executa.

O formato NEUTRO (CSV/JSON) e o que fica no projeto; o dialeto de cada maquina e
uma traducao dele. Isso importa porque o dialeto e (H) — muda com o fabricante,
com o modelo e ate com a versao do firmware —, enquanto o neutro e verificavel:
reimportar tem de devolver a mesma geometria.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field

# --------------------------------------------------------------- maquinas (H)
@dataclass(frozen=True)
class Maquina:
    cod: str
    tipo: str
    perfis: tuple            # almas suportadas, mm
    esp_min: float
    esp_max: float
    comp_max: float          # mm
    operacoes: tuple
    velocidade_m_min: float
    setup_min: float = 0.0


# A serie de cada maquina lista montante E guia: a guia de um montante de 90 mm
# tem 92 mm de alma, porque ela o ABRACA. Esquecer isso faz toda guia sair como
# "perfil incompativel" — foi o que a auditoria apontou na primeira execucao.
MAQUINAS = [
    Maquina("RF-01", "perfiladeira", (75, 77, 90, 92, 140, 142), 0.80, 1.55, 12_000,
            ("corte", "furo redondo", "furo oblongo", "servico", "dimple",
             "marcacao inkjet"), 24.0, 12.0),
    Maquina("RF-02", "perfiladeira",
            (90, 92, 140, 142, 200, 202, 250, 252), 0.95, 3.00, 12_000,
            ("corte", "furo redondo", "servico", "notch"), 16.0, 20.0),
    Maquina("LS-01", "laser", (), 0.50, 6.00, 6_000,
            ("corte", "furo redondo", "furo oblongo", "notch", "marcacao laser"),
            6.0, 5.0),
    Maquina("PN-01", "puncionadeira",
            (75, 77, 90, 92, 140, 142, 200, 202), 0.80, 2.25, 6_000,
            ("furo redondo", "furo oblongo", "dimple"), 0.0, 8.0),
]
POR_MAQUINA = {m.cod: m for m in MAQUINAS}

OPERACOES = ("corte", "furo redondo", "furo oblongo", "servico", "notch",
             "dimple", "slot", "marcacao inkjet", "marcacao laser", "dobra")

# Estados de producao (secao 69). A ordem e a do processo: nao se pula etapa.
ESTADOS = ("DESIGN", "APPROVED", "RELEASED", "CUT", "PUNCHED", "ASSEMBLED",
           "QC", "PACKED", "SHIPPED", "DELIVERED", "INSTALLED")


def avancar(estado: str, novo: str) -> bool:
    """So se avanca para o estado imediatamente seguinte."""
    if estado not in ESTADOS or novo not in ESTADOS:
        raise KeyError(f"estado desconhecido: {estado} -> {novo}")
    return ESTADOS.index(novo) == ESTADOS.index(estado) + 1


# --------------------------------------------------------------- CNC neutro
def cnc_neutro(peca) -> dict:
    """Representacao neutra da peca para qualquer maquina."""
    ops = [dict(op="corte", x=0.0), dict(op="corte", x=peca.comp)]
    for f in peca.furos:
        ops.append(dict(op="furo redondo", x=round(f.x, 1), d=round(f.d, 1),
                        servico=f.servico))
    for r in getattr(peca, "recortes", []):
        ops.append(dict(op="notch", x=r.get("x", 0.0), l=r.get("l", 0.0)))
    ops.append(dict(op="marcacao inkjet", x=min(150.0, peca.comp / 2),
                    texto=peca.marcacao))
    ops.sort(key=lambda o: o["x"])
    return dict(id=peca.cod, perfil=peca.perfil, comp=round(peca.comp, 1),
                massa=round(peca.massa, 3), operacoes=ops)


def exportar_cnc(pecas: list, caminho: str = None) -> str:
    """Arquivo neutro. Reimportar tem de devolver a mesma geometria."""
    dados = dict(formato="PORTO-CNC/1", unidade="mm",
                 pecas=[cnc_neutro(p) for p in pecas])
    txt = json.dumps(dados, ensure_ascii=False, indent=1)
    if caminho:
        open(caminho, "w", encoding="utf-8").write(txt)
    return txt


def importar_cnc(txt: str) -> list[dict]:
    d = json.loads(txt)
    if d.get("formato") != "PORTO-CNC/1":
        raise ValueError(f"formato desconhecido: {d.get('formato')}")
    return d["pecas"]


def traduzir(peca_neutra: dict, maquina: str) -> list[str]:
    """(H) Dialeto de maquina. A traducao e trivial; o dialeto real e do fabricante."""
    m = POR_MAQUINA[maquina]
    linhas = [f"; {peca_neutra['id']} {peca_neutra['perfil']} "
              f"L={peca_neutra['comp']:.1f}"]
    for o in peca_neutra["operacoes"]:
        if o["op"] not in m.operacoes:
            linhas.append(f"; IGNORADO (maquina nao executa): {o['op']}")
            continue
        if o["op"] == "corte":
            linhas.append(f"CUT X{o['x']:.1f}")
        elif o["op"].startswith("furo"):
            linhas.append(f"PCH X{o['x']:.1f} D{o['d']:.1f}")
        elif o["op"] == "notch":
            linhas.append(f"NCH X{o['x']:.1f} L{o['l']:.1f}")
        elif o["op"].startswith("marcacao"):
            linhas.append(f"MRK X{o['x']:.1f} \"{o['texto']}\"")
    linhas.append("END")
    return linhas


def compativel(peca, maquina: str) -> dict:
    """A maquina consegue produzir esta peca? (secoes 129 e 130)."""
    m = POR_MAQUINA[maquina]
    alma = float(peca.perfil.split()[1].split("x")[0])
    esp = float(peca.perfil.split("x")[-1].replace(",", "."))
    faltas = []
    if m.perfis and alma not in m.perfis:
        faltas.append(f"alma de {alma:.0f} mm nao esta na serie da maquina "
                      f"{m.perfis}")
    if not (m.esp_min <= esp <= m.esp_max):
        faltas.append(f"espessura {esp:.2f} fora de {m.esp_min}-{m.esp_max} mm")
    if peca.comp > m.comp_max:
        faltas.append(f"comprimento {peca.comp:.0f} acima de {m.comp_max:.0f} mm")
    return dict(ok=not faltas, maquina=maquina, faltas=faltas)


# ------------------------------------------------------------------- tempos
def tempo_peca(peca, maquina: str) -> float:
    """Minutos por peca: avanco mais operacoes."""
    m = POR_MAQUINA[maquina]
    t = (peca.comp / 1000.0) / m.velocidade_m_min if m.velocidade_m_min else 0.0
    t += 0.08 * (2 + len(peca.furos))          # (H) 5 s por operacao
    return t


def balancear(estacoes: dict) -> dict:
    """Gargalo, ociosidade e tempo de ciclo (secoes 71 e 72).

    estacoes: {nome: minutos de carga}. O tempo de ciclo da linha e o da estacao
    mais lenta — nao a media. Somar tempos e o erro que faz uma fabrica prometer
    prazo que nao cumpre.
    """
    if not estacoes:
        return dict(ciclo=0.0, gargalo=None)
    ciclo = max(estacoes.values())
    total = sum(estacoes.values())
    ociosidade = {k: ciclo - v for k, v in estacoes.items()}
    return dict(ciclo=ciclo, gargalo=max(estacoes, key=estacoes.get),
                soma=total, n=len(estacoes),
                eficiencia=total / (ciclo * len(estacoes)),
                ociosidade=ociosidade,
                wip_maximo=sum(1 for v in estacoes.values() if v < ciclo * 0.8))


def oee(disponibilidade: float, performance: float, qualidade: float) -> dict:
    """OEE = D x P x Q (secao 73). Cada fator entre 0 e 1."""
    for n, v in (("disponibilidade", disponibilidade),
                 ("performance", performance), ("qualidade", qualidade)):
        if not 0 <= v <= 1:
            raise ValueError(f"{n} fora de [0,1]: {v}")
    o = disponibilidade * performance * qualidade
    return dict(oee=o, disponibilidade=disponibilidade, performance=performance,
                qualidade=qualidade,
                classe="classe mundial" if o >= 0.85 else
                       ("bom" if o >= 0.60 else "com perda relevante"))


# ---------------------------------------------------------------- qualidade
TOLERANCIAS = {
    "comprimento": 2.0,       # mm
    "posicao de furo": 1.0,
    "diametro de furo": 0.5,
    "esquadro": 1.5,          # mm em 1 m
    "empenamento": 2.0,       # mm em 3 m
    "espessura": 0.05,
    "revestimento": 0.0,      # conforme classe declarada
}


def inspecionar(medidas: dict, nominais: dict, tolerancias: dict = None) -> dict:
    """Compara medido com nominal, item a item."""
    tol = dict(TOLERANCIAS)
    tol.update(tolerancias or {})
    itens, reprovas = [], 0
    for k, medido in medidas.items():
        nom = nominais.get(k)
        if nom is None:
            itens.append(dict(item=k, status="sem nominal declarado"))
            continue
        t = tol.get(k, 1.0)
        d = medido - nom
        ok = abs(d) <= t
        reprovas += 0 if ok else 1
        itens.append(dict(item=k, nominal=nom, medido=medido, desvio=d,
                          tolerancia=t, status="OK" if ok else "REPROVA"))
    return dict(itens=itens, reprovas=reprovas,
                status="APROVADO" if reprovas == 0 else "REPROVADO")
