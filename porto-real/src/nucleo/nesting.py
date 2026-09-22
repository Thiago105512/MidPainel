"""NESTING — aproveitamento de barra, chapa e bobina (secoes 61 a 63, 85, 86).

Aqui o desperdicio deixa de ser estimativa e vira consequencia de um plano de
corte. A diferenca nao e pequena: cortar 801 pecas de barras de 6 m sem plano
costuma perder de 12 a 18 % do aco; com plano, 3 a 6 %.

A regra que mais economiza nao e o algoritmo: e consultar a SOBRA antes de abrir
barra nova. Um deposito com 40 pontas de 1,2 m guardadas e meia tonelada de aco
que ja foi paga.

Primeiro-que-cabe com as pecas em ordem decrescente (FFD) e a heuristica
classica do problema de corte unidimensional. Nao e o otimo — o otimo e
NP-dificil —, mas tem garantia conhecida e, o que importa mais aqui, e
AUDITAVEL: o plano devolvido pode ser conferido peca a peca contra a soma dos
comprimentos.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

SERRA = 3.0          # mm consumidos por corte


@dataclass
class Sobra:
    cod: str
    perfil: str
    comp: float
    local: str = "deposito"


@dataclass
class Barra:
    cod: str
    perfil: str
    comp_bruto: float
    pecas: list = field(default_factory=list)   # (cod_peca, comprimento)
    origem: str = "nova"                        # nova ou sobra

    @property
    def usado(self) -> float:
        return sum(c for _, c in self.pecas) + SERRA * max(0, len(self.pecas) - 1)

    @property
    def perda(self) -> float:
        return self.comp_bruto - self.usado

    @property
    def aproveitamento(self) -> float:
        return self.usado / self.comp_bruto if self.comp_bruto else 0.0


def nestar_barras(pecas: list, comp_barra: float = 6000.0,
                  sobras: list = None) -> dict:
    """Plano de corte 1D por perfil. pecas: [(cod, perfil, comprimento)]."""
    sobras = list(sobras or [])
    por_perfil = {}
    for cod, perfil, comp in pecas:
        por_perfil.setdefault(perfil, []).append((cod, comp))

    barras, nao_cabem = [], []
    for perfil, itens in sorted(por_perfil.items()):
        itens.sort(key=lambda t: -t[1])
        disponiveis = [Barra(f"S-{s.cod}", perfil, s.comp, origem="sobra")
                       for s in sobras if s.perfil == perfil]
        abertas = []
        n = 0
        for cod, comp in itens:
            if comp > comp_barra:
                nao_cabem.append((cod, perfil, comp))
                continue
            alvo = None
            # 1) sobra do deposito primeiro — aco ja pago
            for b in disponiveis:
                if b.perda >= comp + (SERRA if b.pecas else 0):
                    alvo = b
                    break
            # 2) barra ja aberta
            if alvo is None:
                for b in abertas:
                    if b.perda >= comp + (SERRA if b.pecas else 0):
                        alvo = b
                        break
            # 3) barra nova
            if alvo is None:
                n += 1
                alvo = Barra(f"{perfil}#{n:03d}", perfil, comp_barra)
                abertas.append(alvo)
            alvo.pecas.append((cod, comp))
            if alvo.origem == "sobra" and alvo not in barras:
                pass
        barras += [b for b in disponiveis if b.pecas] + abertas

    usadas = [b for b in barras if b.pecas]
    bruto = sum(b.comp_bruto for b in usadas)
    usado = sum(b.usado for b in usadas)
    novas = [b for b in usadas if b.origem == "nova"]
    return dict(barras=usadas, n_barras=len(usadas), n_novas=len(novas),
                n_sobras=len(usadas) - len(novas),
                bruto=bruto, usado=usado, perda=bruto - usado,
                aproveitamento=usado / bruto if bruto else 0.0,
                nao_cabem=nao_cabem,
                sobras_geradas=[(b.cod, b.perda) for b in usadas if b.perda > 300])


def nestar_chapas(pecas: list, larg: float = 1200.0, alt: float = 2400.0,
                  serra: float = 4.0, girar: bool = True) -> dict:
    """Corte guilhotinado 2D em faixas. pecas: [(cod, larg, alt)].

    A primeira versao nao conferia se a peca CABIA na chapa: uma peca de
    1.200 x 2.600 entrava numa chapa de 1.200 x 2.400 e o aproveitamento dava
    108 %, que e impossivel. Agora a peca que nao cabe — nem girada — sai
    declarada, como no corte de barra.
    """
    itens, nao_cabem = [], []
    for cod, w, h in pecas:
        if w <= larg and h <= alt:
            itens.append((cod, w, h, False))
        elif girar and h <= larg and w <= alt:
            itens.append((cod, h, w, True))
        else:
            nao_cabem.append((cod, w, h))
    itens.sort(key=lambda t: -t[2])
    chapas = []
    for cod, w, h, rot in itens:
        posto = False
        for ch in chapas:
            for fx in ch["faixas"]:
                if fx["alt"] >= h and fx["livre"] >= w + serra:
                    fx["pecas"].append((cod, w, h, rot))
                    fx["livre"] -= w + serra
                    posto = True
                    break
            if posto:
                break
            if ch["alt_livre"] >= h + serra:
                ch["faixas"].append(dict(alt=h, livre=larg - w - serra,
                                         pecas=[(cod, w, h, rot)]))
                ch["alt_livre"] -= h + serra
                posto = True
                break
        if not posto:
            chapas.append(dict(cod=f"CH{len(chapas)+1:03d}",
                               alt_livre=alt - h - serra,
                               faixas=[dict(alt=h, livre=larg - w - serra,
                                            pecas=[(cod, w, h, rot)])]))
    area_bruta = len(chapas) * larg * alt
    area_util = sum(w * h for _, w, h, _ in itens)
    return dict(chapas=chapas, n=len(chapas), area_bruta=area_bruta,
                area_util=area_util, nao_cabem=nao_cabem,
                girados=sum(1 for _, _, _, r in itens if r),
                aproveitamento=area_util / area_bruta if area_bruta else 0.0)


def bobina(perfil_massa_m: float, metros: float, larg_bobina: float,
           esp: float, desenvolvimento: float) -> dict:
    """Consumo de bobina para produzir os metros de perfil (secao 63)."""
    tiras = math.floor(larg_bobina / desenvolvimento)
    if tiras < 1:
        raise ValueError(f"desenvolvimento de {desenvolvimento:.1f} mm nao cabe "
                         f"na bobina de {larg_bobina:.0f} mm")
    perda_larg = larg_bobina - tiras * desenvolvimento
    massa = metros * perfil_massa_m
    comp_bobina = metros / tiras
    massa_bobina = comp_bobina * larg_bobina * esp * 7.85e-6
    return dict(tiras=tiras, perda_largura_mm=perda_larg,
                perda_largura_pct=perda_larg / larg_bobina,
                massa_perfil=massa, massa_bobina=massa_bobina,
                comprimento_bobina_m=comp_bobina / 1000.0,
                aproveitamento=massa / massa_bobina if massa_bobina else 0.0)
