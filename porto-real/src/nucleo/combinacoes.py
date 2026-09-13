"""COMBINACOES — ELU e ELS pela NBR 8681:2003 (secao 14).

Uma combinacao nao e uma soma de cargas: e uma hipotese sobre o que acontece ao
mesmo tempo. A norma trata isso com dois mecanismos que se confundem facilmente
e aqui ficam separados:

  gama  pondera a INCERTEZA da acao — quanto ela pode ser maior que o previsto;
  psi   pondera a SIMULTANEIDADE — a chance de duas variaveis estarem no maximo
        no mesmo instante.

Por isso o vento entra com gama 1,4 e psi0 0,6: pode ser 40 % maior que o
calculado, mas so 60 % dele coexiste com a sobrecarga maxima de piso.

Cada acao variavel toma a vez como PRINCIPAL, e o permanente entra como
favoravel e desfavoravel — quem alivia numa hipotese sobrecarrega em outra. E
por isso que o levantamento da cobertura pelo vento so aparece quando o peso
proprio entra minorado.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product

# Coeficientes de ponderacao das acoes (Tabela 1 da NBR 8681), combinacao normal
GAMA = {
    "permanente":     dict(desf=1.40, fav=1.00),
    "permanente_var": dict(desf=1.40, fav=0.90),
    "acidental":      dict(desf=1.40, fav=0.00),
    "vento":          dict(desf=1.40, fav=0.00),
    "temperatura":    dict(desf=1.20, fav=0.00),
    "excepcional":    dict(desf=1.00, fav=0.00),
}
# Fatores de combinacao e de utilizacao (Tabela 2 da NBR 8681)
PSI = {
    "acidental":   dict(psi0=0.5, psi1=0.4, psi2=0.3,
                        obs="local sem concentracao de pessoas"),
    "acidental_conc": dict(psi0=0.7, psi1=0.6, psi2=0.4,
                           obs="local com concentracao de pessoas"),
    "acidental_bib": dict(psi0=0.8, psi1=0.7, psi2=0.6,
                          obs="biblioteca, arquivo, oficina, garagem"),
    "vento":       dict(psi0=0.6, psi1=0.3, psi2=0.0,
                        obs="psi2 = 0: o vento nao tem parcela quase permanente"),
    "temperatura": dict(psi0=0.6, psi1=0.5, psi2=0.3),
    "excepcional": dict(psi0=1.0, psi1=1.0, psi2=1.0),
}
PERMANENTES = ("permanente", "permanente_var")


@dataclass
class Parcela:
    acao: str            # codigo da acao
    natureza: str
    fator: float         # gama . psi aplicado a esta acao nesta combinacao
    papel: str           # principal, secundaria, permanente-desf, permanente-fav


@dataclass
class Combinacao:
    cod: str
    tipo: str            # ELU, ELS-QP, ELS-F, ELS-R
    principal: str
    parcelas: list = field(default_factory=list)
    descricao: str = ""

    def fator(self, acao: str) -> float:
        for p in self.parcelas:
            if p.acao == acao:
                return p.fator
        return 0.0

    def __str__(self):
        t = " + ".join(f"{p.fator:.2f}·{p.acao}" for p in self.parcelas if p.fator)
        return f"{self.cod} [{self.tipo}] {t}"


def _psi(natureza: str, subclasse: str | None, qual: str) -> float:
    chave = subclasse or natureza
    if chave not in PSI:
        chave = natureza
    if chave not in PSI:
        raise KeyError(f"sem psi declarado para '{natureza}'")
    return PSI[chave][qual]


def gerar(acoes: list[tuple], subclasses: dict = None) -> list[Combinacao]:
    """Gera TODAS as combinacoes normativas.

    acoes: lista de (codigo, natureza). subclasses: {codigo: chave de PSI},
    para distinguir sobrecarga de local com e sem concentracao de pessoas.
    """
    subclasses = subclasses or {}
    perm = [(c, n) for c, n in acoes if n in PERMANENTES]
    vari = [(c, n) for c, n in acoes if n not in PERMANENTES]
    out, i = [], 0

    # ---- ELU: cada variavel como principal, permanente favoravel e desfavoravel
    for sinal in ("desf", "fav"):
        for pc, pn in (vari or [(None, None)]):
            i += 1
            parc = [Parcela(c, n, GAMA[n][sinal], f"permanente-{sinal}")
                    for c, n in perm]
            for c, n in vari:
                if c == pc:
                    parc.append(Parcela(c, n, GAMA[n]["desf"], "principal"))
                else:
                    psi0 = _psi(n, subclasses.get(c), "psi0")
                    parc.append(Parcela(c, n, GAMA[n]["desf"] * psi0, "secundaria"))
            out.append(Combinacao(
                f"ELU-{i:02d}", "ELU", pc or "—", parc,
                f"acao principal {pc or 'nenhuma'}, permanente "
                f"{'desfavoravel' if sinal == 'desf' else 'favoravel'}"))

    # ---- ELS
    for tipo, fp, fs in (("ELS-QP", "psi2", "psi2"),
                         ("ELS-F", "psi1", "psi2"),
                         ("ELS-R", None, "psi1")):
        for j, (pc, pn) in enumerate(vari or [(None, None)], 1):
            parc = [Parcela(c, n, 1.0, "permanente") for c, n in perm]
            for c, n in vari:
                if c == pc:
                    f = 1.0 if fp is None else _psi(n, subclasses.get(c), fp)
                else:
                    f = _psi(n, subclasses.get(c), fs)
                parc.append(Parcela(c, n, f, "principal" if c == pc else "secundaria"))
            out.append(Combinacao(f"{tipo}-{j:02d}", tipo, pc or "—", parc,
                                  f"servico, acao principal {pc or 'nenhuma'}"))
            if tipo == "ELS-QP":
                break        # quase permanente nao tem acao principal
    return out


def envelope(combs: list[Combinacao], esforcos: dict) -> dict:
    """Maximo e minimo por elemento sobre todas as combinacoes de um tipo.

    esforcos: {codigo_acao: {elemento: valor}}. Devolve {elemento: (min, max,
    comb_min, comb_max)} — e quem diz QUAL hipotese governa cada peca.
    """
    elems = {e for v in esforcos.values() for e in v}
    out = {}
    for e in elems:
        vals = []
        for c in combs:
            s = sum(c.fator(a) * esforcos[a].get(e, 0.0) for a in esforcos)
            vals.append((s, c.cod))
        lo, hi = min(vals), max(vals)
        out[e] = dict(min=lo[0], max=hi[0], comb_min=lo[1], comb_max=hi[1])
    return out
