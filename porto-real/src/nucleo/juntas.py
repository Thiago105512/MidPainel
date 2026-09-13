"""JUNTAS — cada parafuso do projeto, contado a partir de uma forca.

Ate R29 o checklist da liberacao trazia `"ligacoes": True`. Literal. Nenhum
parafuso era contado, nenhuma junta era verificada, e o item passava sempre —
o mesmo defeito do `min(0.99, ...)` da verificacao estrutural, na mesma lista,
uma linha abaixo. Um item que nao pode falhar nao verifica: assina.

Este modulo enumera TODA junta entre duas pecas do painel, e para cada uma diz:
quantos parafusos, qual parafuso, e — a parte que separa engenharia de praxe —
DE ONDE veio o numero. Ha tres origens possiveis e elas nao valem o mesmo:

  FORCA      a quantidade sai de um esforco calculado. E o unico caso em que o
             numero tem defesa tecnica.
  MINIMO     a quantidade e o minimo construtivo (dois por ligacao), porque a
             junta nao transfere esforco calculado — so posiciona.
  DECLARADO  a junta transfere esforco que o modelo AINDA nao calcula, e a
             quantidade desenvolve uma fracao declarada da capacidade da peca.
             Nao e um chute: e uma regra escrita, conservadora e contestavel.

Misturar as tres numa soma unica esconderia exatamente o que importa saber. Por
isso o resultado conta quantos parafusos vieram de cada origem.
"""
from __future__ import annotations

import math

import nucleo.ligacoes as lg
import nucleo.painel as pn

# Parafuso padrao da estrutura. Chapa de 0,95 a 2,00 mm fura com ponta broca;
# a escolha do 4,8 e de montagem, nao de calculo: e o que a parafusadeira de
# obra usa sem troca de bit entre a estrutura e o fechamento.
PADRAO = "AB 4,8x19 ponta broca"
PESADO = "AB 5,5x25 ponta broca"

# Fracao da capacidade da peca que uma emenda precisa desenvolver quando o
# esforco nela nao e calculado. 0,50 e regra de projeto declarada — pratica
# corrente para emenda de guia em parede nao-contraventante. Onde o esforco de
# diafragma for calculado, este numero sai de cena.
FRACAO_EMENDA = 0.50

# Forca de travamento que um blocking precisa transferir: fracao da carga axial
# do montante que ele trava. 2 % e a regra classica de bracing.
FRACAO_BRACING = 0.02


def _fu(perfil: str, aco) -> float:
    return aco.fu


def _t(perfil: str) -> float:
    """Espessura declarada na designacao: "Ue 90x40x12x0,95" -> 0,95 mm."""
    return float(perfil.split()[1].split("x")[-1].replace(",", "."))


def _cruzam(a, b) -> bool:
    """As duas pecas se encontram no plano do painel?

    Cada peca ocupa um retangulo: a vertical e larga como a alma e alta como o
    comprimento; a horizontal, o contrario. Onde os retangulos se cruzam ha
    junta — e a junta e onde vai parafuso.
    """
    def caixa(q):
        w = pn.bw(q.perfil) if q.vertical else q.comp
        h = q.comp if q.vertical else pn.bw(q.perfil)
        return q.x, q.x + w, q.z, q.z + h
    ax0, ax1, az0, az1 = caixa(a)
    bx0, bx1, bz0, bz1 = caixa(b)
    return (min(ax1, bx1) - max(ax0, bx0) > 1
            and min(az1, bz1) - max(az0, bz0) > 1)


def _n(forca_kn, par, t1, t2, fu, minimo=2):
    """Quantidade para a forca, nunca abaixo do minimo construtivo."""
    if forca_kn <= 0:
        return minimo, None
    r = lg.quantidade(forca_kn, par, t1, t2, fu, fu, "cisalhamento")
    return max(minimo, r["n"]), r


def programar(p: pn.Painel, nsd_montante: float, nsd_jamba: float, aco,
              cfg: pn.Config = None) -> dict:
    """Todas as juntas de um painel, com parafuso, quantidade e origem.

    As forcas entram de fora (da descida de cargas) porque quem sabe quanto
    desce e o modelo do edificio, nao o painel. O painel sabe QUAIS pecas se
    encontram — e e isso que ele resolve aqui.
    """
    cfg = cfg or pn.Config()
    par = lg.POR_PARAFUSO[PADRAO]
    pesado = lg.POR_PARAFUSO[PESADO]
    juntas = []

    def junta(tipo, a, b, n, origem, forca=0.0, parafuso=None, nota=""):
        juntas.append(dict(tipo=tipo, pecas=(a, b), n=n, origem=origem,
                           forca_kn=round(forca, 2),
                           parafuso=(parafuso or par).cod, nota=nota))

    verticais = [q for q in p.pecas
                 if q.familia in ("stud", "king stud", "jack stud",
                                  "cripple superior", "cripple inferior")]
    tracks = [q for q in p.pecas if q.familia == "track"]
    blocking = [q for q in p.pecas if q.familia == "blocking"]
    headers = [q for q in p.pecas if q.familia == "header"]
    sills = [q for q in p.pecas if q.familia == "sill"]

    # ---- 1. montante x guia: posiciona, nao transfere axial (a peca APOIA na
    # alma da guia). Minimo construtivo: 2 por aba, 2 abas, 2 extremidades.
    # O montante ATRAVESSA a guia — ele encaixa dentro dela, e essa e a propria
    # convencao de coordenada do modelo desde R25. Testar encosto em vez de
    # sobreposicao nao achava junta nenhuma: o primeiro painel saia com 14
    # parafusos onde precisa de 70.
    for q in verticais:
        for t in tracks:
            if not _cruzam(q, t):
                continue
            junta("montante x guia", q.cod, t.cod, 4, "MINIMO",
                  nota="2 por aba, nas duas abas; o montante apoia na alma "
                       "da guia e nao transfere axial por parafuso")

    # ---- 2. jack x king: AQUI ha forca. O jack recebe a reacao da verga e a
    # entrega ao king por cisalhamento ao longo do contato.
    jacks = [q for q in p.pecas if q.familia == "jack stud"]
    kings = [q for q in p.pecas if q.familia == "king stud"]
    for j in jacks:
        k = next((x for x in kings if abs(x.x - j.x) < 2), None)
        if k is None:
            continue
        t1 = _t(j.perfil)
        n, r = _n(nsd_jamba, pesado, t1, _t(k.perfil), aco.fu, minimo=4)
        junta("jack x king", j.cod, k.cod, n, "FORCA", nsd_jamba, pesado,
              nota=(f"reacao da verga entregue ao king por cisalhamento; "
                    f"{r['modo']}, {r['cap_unit']:.2f} kN por parafuso"
                    if r else ""))

    # ---- 3. verga x jamba: a reacao passa por aqui antes de chegar ao jack
    for h in headers:
        for lado, alvo in (("esq", min(jacks, key=lambda q: q.x, default=None)),
                           ("dir", max(jacks, key=lambda q: q.x, default=None))):
            if alvo is None:
                continue
            n, r = _n(nsd_jamba, pesado, _t(h.perfil), _t(alvo.perfil),
                      aco.fu, minimo=4)
            junta("verga x jamba", h.cod, alvo.cod, n, "FORCA", nsd_jamba,
                  pesado, nota=f"apoio {lado} da verga")

    # ---- 4. blocking x montante: forca de travamento, 2 % do axial travado
    f_brac = FRACAO_BRACING * nsd_montante
    for b in blocking:
        for q in verticais:
            if _cruzam(b, q):
                n, _ = _n(f_brac, par, _t(b.perfil), _t(q.perfil), aco.fu)
                junta("blocking x montante", b.cod, q.cod, n, "FORCA", f_brac,
                      nota=f"{FRACAO_BRACING*100:.0f} % da carga axial do "
                           f"montante que ele trava")

    # ---- 5. peitoril x jamba: minimo; o peitoril nao carrega gravidade
    for s in sills:
        for q in jacks[:2]:
            junta("peitoril x jamba", s.cod, q.cod, 2, "MINIMO")

    # ---- 6. emenda: o esforco de diafragma nao e calculado pelo modelo, entao
    # a emenda desenvolve uma fracao DECLARADA da capacidade da peca emendada
    for q in tracks + blocking:
        if "emenda em x" not in (q.obs or ""):
            continue
        area = pn.bw(q.perfil) * _t(q.perfil)          # aproximacao da alma
        cap = FRACAO_EMENDA * area * aco.fy / 1000.0
        n, r = _n(cap, pesado, _t(q.perfil), _t(q.perfil), aco.fu, minimo=4)
        sem = "SEM MONTANTE" in (q.obs or "")
        junta("emenda", q.cod, "talao", n, "DECLARADO", cap, pesado,
              nota=(f"desenvolve {FRACAO_EMENDA*100:.0f} % da capacidade da "
                    f"alma ({cap:.1f} kN) de cada lado da junta"
                    + ("; emenda SEM montante de apoio: o talao tambem vence "
                       "momento, e este numero NAO cobre isso" if sem else "")))

    por_origem = {}
    for j in juntas:
        por_origem[j["origem"]] = por_origem.get(j["origem"], 0) + j["n"]
    return dict(painel=p.cod, juntas=juntas,
                n_juntas=len(juntas),
                n_parafusos=sum(j["n"] for j in juntas),
                por_origem=por_origem,
                por_tipo={t: sum(j["n"] for j in juntas if j["tipo"] == t)
                          for t in {j["tipo"] for j in juntas}})
