"""PADROES DA CASA, NORMAS E HIPOTESES — toda constante tem dono (R81).

O proprietario perguntou se "a logica de tudo e a padronizacao" e pediu que
as decisoes fossem tomadas por ele. A resposta esta aqui, em tres classes:

  PADRAO   — decisao da casa: vale em toda parte, e uniforme porque variar
             nao acrescenta valor (altura da tomada, cota do furo, cor da
             luz por zona, passo do clip). O caso pode fixar o valor; o
             modulo le do caso.
  NORMA    — limite de norma, tabela comercial ou fisica: ninguem aqui
             decide (queda de 4 %, zona 1 do box, diametro interno do tubo,
             Hazen-Williams). Muda quando a norma muda.
  HIPOTESE — numero que aguarda confirmacao de alguem de fora (fabricante,
             INMET, obra, fornecedor): potencia sonora da condensadora,
             rendimento do motor, vento dominante, equipe de pico. Cada uma
             tem DONO declarado.

O que nao esta em nenhuma classe e DERIVADO: posicao de ponto, secao de
cabo, DN, comprimento, quantidade. Nunca se digita; sai de outro numero.

A auditoria cobra: (1) toda constante numerica dos modulos governados esta
classificada; (2) toda classificacao aponta para uma constante que existe;
(3) o valor fixado pelo caso e o que o modulo usa; (4) toda hipotese tem
dono; (5) dois modulos que dizem a mesma coisa (altura da bancada) dizem o
mesmo numero.
"""
from __future__ import annotations

import importlib

MODULOS = ["nucleo.pontos", "nucleo.percurso", "nucleo.piscina", "nucleo.canteiro", "nucleo.gas", "nucleo.circuitos",
           "nucleo.agua", "nucleo.esgoto", "nucleo.luminotecnica", "nucleo.marcenaria", "nucleo.seguranca",
           "nucleo.detalhes_lsf", "nucleo.acabamento", "nucleo.eletrica", "nucleo.peca"]
CLASSES = ("padrao", "norma", "hipotese")
# pares que dizem a mesma coisa em modulos diferentes e precisam coincidir
GEMEOS = [("nucleo.marcenaria.BANCADA_ACABADA", "nucleo.acabamento.ALTURA_BANCADA"),
          ("nucleo.piscina.RHO_CU", "nucleo.circuitos.RHO")]


def inventario() -> list[dict]:
    """Toda constante numerica (int, float, tupla, dicionario) dos modulos governados."""
    out = []
    for m in MODULOS:
        mod = importlib.import_module(m)
        for k in sorted(dir(mod)):
            if not k.isupper() or k.startswith("_") or k.startswith("PRECO"):
                continue
            v = getattr(mod, k)
            if isinstance(v, bool) or not isinstance(v, (int, float, tuple, dict)):
                continue
            out.append(dict(modulo=m, nome=k, chave=f"{m}.{k}", valor=v))
    return out


def _entradas(pj) -> list[dict]:
    out = []
    for e in pj.PADROES_DA_CASA:
        modulo, nome, classe, texto = e[:4]
        valor = e[4] if len(e) > 4 else None
        un = e[5] if len(e) > 5 else ""
        out.append(dict(modulo=modulo, nome=nome, chave=f"{modulo}.{nome}", classe=classe, texto=texto, valor=valor, un=un))
    return out


def aplicar(pj) -> int:
    """O caso fixa o valor dos padroes: o modulo passa a ler do caso."""
    n = 0
    for e in _entradas(pj):
        if e["valor"] is None:
            continue
        mod = importlib.import_module(e["modulo"])
        if getattr(mod, e["nome"], None) != e["valor"]:
            setattr(mod, e["nome"], e["valor"]); n += 1
    return n


def catalogo(pj) -> list[dict]:
    inv = {i["chave"]: i for i in inventario()}
    out = []
    for e in _entradas(pj):
        i = inv.get(e["chave"])
        v = i["valor"] if i else None
        if isinstance(v, dict):
            vs = "; ".join(f"{a}: {b}" for a, b in list(v.items())[:6]) + (" …" if len(v) > 6 else "")
        elif isinstance(v, tuple):
            vs = ", ".join(str(a) for a in v[:8]) + (" …" if len(v) > 8 else "")
        else:
            vs = "" if v is None else (f"{v:g}" if isinstance(v, float) else str(v))
        out.append(dict(**e, valor_modulo=v, valor_txt=vs, existe=i is not None))
    return out


DERIVADOS = [
    ("posicao de cada tomada, interruptor, luminaria e TUE", "nucleo/pontos: bancada, TV, lavatorio, porta, cama, perimetro"),
    ("percurso, comprimento e montantes atravessados de cada eletroduto e tubo", "nucleo/percurso: grafo das paredes"),
    ("secao de cada circuito e disjuntor", "nucleo/circuitos: corrente e queda no ponto mais longe"),
    ("DN de cada ramal de agua e esgoto, caimento, ventilacao", "nucleo/agua, nucleo/esgoto: pesos, UHC, comprimento real"),
    ("numero de degraus da escada da piscina, DN das linhas, altura da bomba", "nucleo/piscina: desnivel, vazao, perdas"),
    ("furos hidraulicos: em quais paineis", "nucleo/percurso.servicos_por_painel: so onde a agua passa"),
    ("quantidade de fixadores, caixas, buchas, clips", "nucleo/percurso.fixadores: trecho a trecho"),
    ("luminarias por ambiente e sua posicao", "nucleo/luminotecnica: lux-alvo, malha, forro"),
    ("modulos, pecas, chapas e ferragens de cada movel", "nucleo/marcenaria"),
    ("zonas do canteiro e a drenagem provisoria", "nucleo/canteiro: lote, portoes, paineis, chuva de projeto"),
    ("BOM, cotacao e curva ABC", "nucleo/bom: tudo acima, com preco (H)"),
]


def resumo(pj) -> dict:
    c = catalogo(pj)
    return dict(constantes=len(inventario()), classificadas=len(c), padroes=sum(1 for e in c if e["classe"] == "padrao"),
                normas=sum(1 for e in c if e["classe"] == "norma"), hipoteses=sum(1 for e in c if e["classe"] == "hipotese"),
                fixadas=sum(1 for e in c if e["valor"] is not None), derivados=len(DERIVADOS))


def conferir(pj) -> list[tuple[str, str, bool]]:
    out = []
    inv = {i["chave"]: i for i in inventario()}
    c = catalogo(pj)
    chaves = {e["chave"] for e in c}
    sem = [k for k in inv if k not in chaves]
    out.append(("toda constante dos modulos governados esta classificada", ", ".join(sem[:8]) + (f" (+{len(sem) - 8})" if len(sem) > 8 else "") if sem else f"{len(inv)} constantes", not sem))
    mortas = [e["chave"] for e in c if not e["existe"]]
    out.append(("toda classificacao aponta para uma constante que existe", ", ".join(mortas[:6]) if mortas else f"{len(c)} entradas", not mortas))
    ruins = [e["chave"] for e in c if e["classe"] not in CLASSES]
    out.append(("classe conhecida", ", ".join(ruins) if ruins else "padrao, norma ou hipotese", not ruins))
    dif = [f"{e['chave']} {e['valor_modulo']}!={e['valor']}" for e in c if e["valor"] is not None and e["existe"] and e["valor_modulo"] != e["valor"]]
    out.append(("o valor fixado pelo caso e o que o modulo usa", ", ".join(dif[:6]) if dif else f"{sum(1 for e in c if e['valor'] is not None)} valores fixados pelo caso", not dif))
    sem_dono = [e["chave"] for e in c if e["classe"] == "hipotese" and "dono:" not in e["texto"]]
    out.append(("toda hipotese tem dono", ", ".join(sem_dono[:6]) if sem_dono else f"{sum(1 for e in c if e['classe'] == 'hipotese')} hipoteses com dono", not sem_dono))
    dup = []
    for a, b in GEMEOS:
        va, vb = inv.get(a, {}).get("valor"), inv.get(b, {}).get("valor")
        if va != vb:
            dup.append(f"{a}={va} x {b}={vb}")
    out.append(("gemeos dizem o mesmo numero", ", ".join(dup) if dup else "; ".join(f"{a.split('.')[-1]}={inv[a]['valor']}" for a, _ in GEMEOS if a in inv), not dup))
    return out
