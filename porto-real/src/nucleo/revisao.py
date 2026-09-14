"""REVISAO — diferenca, impacto e congelamento (secoes 79 a 83, 135).

Comparar duas revisoes de um projeto de CAD e trabalho manual: alguem abre as
duas plantas lado a lado e procura. Aqui e computavel, e por um motivo
estrutural — tudo e funcao do modelo. Mudar a posicao de uma janela e mudar um
numero; o resto se recalcula, e a diferenca entre os dois resultados E o
impacto.

O congelamento existe pela razao oposta: quando uma peca ja foi FABRICADA, o
modelo deixa de ser livre. Alterar a revisao depois disso nao e revisar, e
sucatear — e o sistema precisa dizer quanto, antes de a alteracao ser aprovada.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

NIVEIS_CONGELAMENTO = {
    "DESIGN": "livre",
    "APPROVED": "livre com registro",
    "RELEASED": "congelado para fabricacao",
    "CUT": "peca cortada: alteracao gera sucata",
    "PUNCHED": "peca furada: alteracao gera sucata",
    "ASSEMBLED": "painel montado: alteracao gera retrabalho",
    "PACKED": "embalado: alteracao gera reembalagem e frete",
    "SHIPPED": "em transito: alteracao gera frete de retorno",
    "INSTALLED": "instalado: alteracao gera demolicao parcial",
}


def diff_pecas(antes: list, depois: list) -> dict:
    """Verde, vermelho, amarelo (secao 83), por codigo estavel de peca."""
    a = {p.cod: p for p in antes}
    b = {p.cod: p for p in depois}
    add = sorted(set(b) - set(a))
    rem = sorted(set(a) - set(b))
    alt = []
    for c in sorted(set(a) & set(b)):
        x, y = a[c], b[c]
        campos = {}
        for k in ("perfil", "comp", "x", "z", "painel"):
            if getattr(x, k) != getattr(y, k):
                campos[k] = (getattr(x, k), getattr(y, k))
        if len(x.furos) != len(y.furos):
            campos["furos"] = (len(x.furos), len(y.furos))
        if campos:
            alt.append(dict(cod=c, campos=campos))
    massa_a = sum(p.massa for p in antes)
    massa_b = sum(p.massa for p in depois)
    return dict(adicionadas=add, removidas=rem, alteradas=alt,
                n_add=len(add), n_rem=len(rem), n_alt=len(alt),
                massa_antes=massa_a, massa_depois=massa_b,
                delta_massa=massa_b - massa_a,
                inalteradas=len(set(a) & set(b)) - len(alt))


def impacto(diff: dict, estados: dict = None, custo_kg: float = 11.50) -> dict:
    """O que a alteracao alcanca, inclusive o que ja foi fabricado (secao 81).

    estados: {cod_peca: estado de producao}. E isto que separa uma revisao
    barata de uma cara: a mesma mudanca geometrica custa zero em DESIGN e custa
    sucata em CUT.
    """
    estados = estados or {}
    afetadas = set(diff["removidas"]) | {a["cod"] for a in diff["alteradas"]}
    sucata, retrabalho, livres = [], [], []
    for c in sorted(afetadas):
        e = estados.get(c, "DESIGN")
        if e in ("CUT", "PUNCHED"):
            sucata.append(c)
        elif e in ("ASSEMBLED", "PACKED", "SHIPPED", "INSTALLED"):
            retrabalho.append(c)
        else:
            livres.append(c)
    return dict(
        afetadas=sorted(afetadas), n_afetadas=len(afetadas),
        sucata=sucata, retrabalho=retrabalho, livres=livres,
        custo_sucata=len(sucata) * 0.0,      # preenchido por quem tiver a massa
        delta_massa=diff["delta_massa"],
        delta_custo=diff["delta_massa"] * custo_kg,
        gravidade=("alta" if sucata or retrabalho else
                   ("media" if len(afetadas) > 20 else "baixa")),
        nota=NIVEIS_CONGELAMENTO.get(
            max((estados.get(c, "DESIGN") for c in afetadas),
                key=lambda e: list(NIVEIS_CONGELAMENTO).index(e))
            if afetadas else "DESIGN"))


def pode_fabricar(rev_peca: str, rev_atual: str, ordem_revisoes: list) -> dict:
    """Freeze: nao se fabrica revisao vencida (secao 80)."""
    if rev_peca not in ordem_revisoes or rev_atual not in ordem_revisoes:
        return dict(pode=False, motivo=f"revisao desconhecida: "
                                       f"{rev_peca} ou {rev_atual}")
    i, j = ordem_revisoes.index(rev_peca), ordem_revisoes.index(rev_atual)
    if i == j:
        return dict(pode=True, motivo=f"peca em {rev_peca}, que e a revisao atual")
    if i > j:
        return dict(pode=False, motivo=f"peca em {rev_peca}, a frente da atual "
                                       f"{rev_atual}: dado corrompido")
    return dict(pode=False, atraso=j - i,
                motivo=f"peca desenhada em {rev_peca} e o projeto esta em "
                       f"{rev_atual}: {j-i} revisao(oes) de atraso. Fabricar "
                       f"assim produz peca que nao serve")


@dataclass
class ChangeOrder:
    """Secao 82 — o documento que transforma uma alteracao em decisao."""
    cod: str
    solicitante: str
    descricao: str
    diff: dict
    impacto: dict
    prazo_dias: float = 0.0
    aprovado_por: str = ""
    data: str = ""

    def resumo(self) -> dict:
        return dict(
            ordem=self.cod, solicitante=self.solicitante,
            descricao=self.descricao,
            pecas=dict(adicionadas=self.diff["n_add"],
                       removidas=self.diff["n_rem"],
                       alteradas=self.diff["n_alt"],
                       inalteradas=self.diff["inalteradas"]),
            massa_kg=round(self.diff["delta_massa"], 1),
            custo=round(self.impacto["delta_custo"], 2),
            prazo_dias=self.prazo_dias,
            gravidade=self.impacto["gravidade"],
            sucata=len(self.impacto["sucata"]),
            retrabalho=len(self.impacto["retrabalho"]),
            aprovacao=self.aprovado_por or "PENDENTE")
