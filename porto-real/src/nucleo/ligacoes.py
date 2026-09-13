"""LIGACOES — parafusos, chumbadores e o que impede parafusar (secoes 30 a 33, 37).

Em LSF a ligacao nao e detalhe: e o item mais repetido da obra e o que mais
falha. Um montante de 2,60 m leva 8 parafusos; uma casa leva dezenas de milhares.
E a falha quase nunca e do parafuso — e da CHAPA em volta dele, que tem 0,95 mm.

Por isso a NBR 14762 verifica cinco modos, e nenhum deles e a resistencia do
parafuso: arrancamento do rosqueamento, arrancamento por sobre a cabeca,
esmagamento da chapa mais fina, esmagamento da mais grossa e rasgamento ate a
borda. A resistencia do parafuso em si vem do fabricante e entra (H).

E ha um sexto modo que nenhuma norma verifica e toda obra encontra: o parafuso
que nao pode ser instalado porque a parafusadeira nao entra. Isso e geometria,
e esta verificado aqui.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

GAMA_RUPTURA = 1.65          # NBR 14762, ligacoes
GAMA_ESC = 1.10


@dataclass(frozen=True)
class Parafuso:
    cod: str
    d: float             # mm, diametro nominal da rosca
    dw: float            # mm, diametro da cabeca ou da arruela
    tipo: str
    rv_fab: float = 0.0  # kN, resistencia ao cisalhamento do parafuso (H)
    rt_fab: float = 0.0  # kN, resistencia a tracao do parafuso (H)


PARAFUSOS = [
    Parafuso("AB 4,2x13 ponta broca", 4.2, 8.0, "auto-brocante", 5.2, 6.8),
    Parafuso("AB 4,8x19 ponta broca", 4.8, 9.5, "auto-brocante", 6.8, 8.9),
    Parafuso("AB 5,5x25 ponta broca", 5.5, 11.0, "auto-brocante", 9.1, 11.5),
    Parafuso("AA 4,2x32 ponta agulha", 4.2, 8.0, "auto-atarraxante", 5.2, 6.8),
    Parafuso("AA 4,8x38 ponta agulha", 4.8, 9.5, "auto-atarraxante", 6.8, 8.9),
]
POR_PARAFUSO = {p.cod: p for p in PARAFUSOS}

ESPACAMENTO_MIN = 3.0        # x diametro, entre parafusos
BORDA_MIN = 3.0              # x diametro, ate a borda da chapa


def tracao(par: Parafuso, t1: float, t3: float, fu1: float, fu3: float) -> dict:
    """Arrancamento: do rosqueamento (pull-out) e por sobre a cabeca (pull-over).

    t1 = chapa sob a cabeca; t3 = chapa que recebe a rosca.
    """
    pull_out = 0.85 * t3 * par.d * fu3 / 1000.0            # kN
    pull_over = 1.5 * t1 * par.dw * fu1 / 1000.0           # kN
    modos = {"arrancamento do rosqueamento": pull_out,
             "arrancamento sobre a cabeca": pull_over}
    if par.rt_fab:
        modos["ruptura do parafuso (H)"] = par.rt_fab
    critico = min(modos, key=modos.get)
    return dict(ntrd=modos[critico] / GAMA_RUPTURA, modo=critico, modos=modos)


def cisalhamento(par: Parafuso, t1: float, t2: float, fu1: float, fu2: float) -> dict:
    """Esmagamento e rasgamento (NBR 14762, item 8.4).

    t1 e a chapa mais fina em contato, t2 a mais grossa. A razao entre elas
    muda o modo: chapas parecidas basculam o parafuso, chapas muito diferentes
    nao.
    """
    if t1 > t2:
        t1, t2 = t2, t1
        fu1, fu2 = fu2, fu1
    r = t2 / t1
    esm1 = 2.7 * t1 * par.d * fu1 / 1000.0
    esm2 = 2.7 * t2 * par.d * fu2 / 1000.0
    if r <= 1.0:
        bascula = 4.2 * math.sqrt(t2 ** 3 * par.d) * fu2 / 1000.0
        modos = {"basculamento do parafuso": bascula,
                 "esmagamento da chapa fina": esm1,
                 "esmagamento da chapa grossa": esm2}
    elif r >= 2.5:
        modos = {"esmagamento da chapa fina": esm1,
                 "esmagamento da chapa grossa": esm2}
    else:
        bascula = 4.2 * math.sqrt(t2 ** 3 * par.d) * fu2 / 1000.0
        f = (2.5 - r) / 1.5
        modos = {"basculamento interpolado": bascula + (esm1 - bascula) * (1 - f),
                 "esmagamento da chapa fina": esm1,
                 "esmagamento da chapa grossa": esm2}
    if par.rv_fab:
        modos["ruptura do parafuso (H)"] = par.rv_fab
    critico = min(modos, key=modos.get)
    return dict(nvrd=modos[critico] / GAMA_RUPTURA, modo=critico, modos=modos,
                razao=r)


def quantidade(forca_kn: float, par: Parafuso, t1: float, t2: float,
               fu1: float, fu2: float, tipo: str = "cisalhamento") -> dict:
    """Quantos parafusos, e com que espacamento minimo (secao 31)."""
    r = (cisalhamento(par, t1, t2, fu1, fu2) if tipo == "cisalhamento"
         else tracao(par, t1, t2, fu1, fu2))
    cap = r.get("nvrd") or r.get("ntrd")
    n = max(2, math.ceil(forca_kn / cap))
    return dict(n=n, cap_unit=cap, modo=r["modo"],
                espacamento_min=ESPACAMENTO_MIN * par.d,
                borda_min=BORDA_MIN * par.d,
                uso=forca_kn / (n * cap))


def verificar_geometria(posicoes: list, largura: float, par: Parafuso) -> list:
    """Espacamento e distancia de borda. Posicoes em mm ao longo da peca."""
    fora = []
    e_min, b_min = ESPACAMENTO_MIN * par.d, BORDA_MIN * par.d
    for a, b in zip(sorted(posicoes), sorted(posicoes)[1:]):
        if b - a < e_min:
            fora.append(f"parafusos a {b-a:.1f} mm, minimo {e_min:.1f}")
    for p in posicoes:
        if p < b_min or largura - p < b_min:
            fora.append(f"parafuso a {min(p, largura-p):.1f} mm da borda, "
                        f"minimo {b_min:.1f}")
    return fora


# ------------------------------------------------------- acessibilidade (32)
FERRAMENTAS = {
    "parafusadeira comum": dict(diametro=55, comprimento=180, folga_lateral=30),
    "parafusadeira angular": dict(diametro=45, comprimento=95, folga_lateral=18),
    "chave catraca": dict(diametro=35, comprimento=60, folga_lateral=12),
}


def acessivel(folga_mm: float, ferramenta: str = "parafusadeira comum") -> dict:
    """O parafuso pode ser instalado? Verificacao geometrica, nao normativa.

    Nenhuma norma verifica isso e toda obra encontra: o parafuso perfeitamente
    dimensionado, na posicao onde a parafusadeira nao entra.
    """
    f = FERRAMENTAS[ferramenta]
    ok = folga_mm >= f["comprimento"]
    alt = [k for k, v in FERRAMENTAS.items() if v["comprimento"] <= folga_mm]
    return dict(ok=ok, ferramenta=ferramenta, precisa=f["comprimento"],
                folga=folga_mm, alternativas=alt,
                motivo="" if ok else
                (f"{folga_mm:.0f} mm de folga nao comportam a {ferramenta} "
                 f"({f['comprimento']} mm). " +
                 (f"Cabe: {alt}." if alt else
                  "Nenhuma ferramenta cabe: mudar a sequencia de montagem ou "
                  "a ligacao.")))


# ------------------------------------------------------------- chumbadores
@dataclass(frozen=True)
class Chumbador:
    cod: str
    d: float             # mm
    embutimento: float   # mm
    tipo: str
    borda_min: float     # mm
    espac_min: float     # mm
    trd_fab: float = 0.0  # kN (H), do fabricante


CHUMBADORES = [
    Chumbador("expansao M10", 10, 80, "mecanico", 100, 150, 12.0),
    Chumbador("expansao M12", 12, 100, "mecanico", 120, 180, 18.0),
    Chumbador("quimico M12", 12, 110, "quimico", 90, 130, 28.0),
    Chumbador("quimico M16", 16, 150, "quimico", 120, 170, 48.0),
    Chumbador("barra rosqueada M16 chumbada", 16, 300, "pre-instalado", 120, 200, 55.0),
]


def ancoragem(uplift_kn: float, esp_radier: float,
              candidatos=None) -> dict:
    """Escolhe o chumbador do hold-down, com o motivo e o que foi rejeitado."""
    cands = candidatos or CHUMBADORES
    testados = []
    for c in cands:
        ok_emb = c.embutimento <= esp_radier - 30      # cobrimento minimo
        ok_f = c.trd_fab >= uplift_kn
        testados.append(dict(chumbador=c.cod, trd=c.trd_fab,
                             embutimento=c.embutimento, ok=ok_emb and ok_f,
                             motivo="" if ok_emb and ok_f else
                             ("embutimento nao cabe no radier" if not ok_emb
                              else "resistencia insuficiente")))
    validos = [t for t in testados if t["ok"]]
    if not validos:
        return dict(escolhido=None, alternativas=testados,
                    motivo=f"nenhum chumbador do catalogo resiste a "
                           f"{uplift_kn:.1f} kN num radier de {esp_radier:.0f} mm")
    e = min(validos, key=lambda t: t["trd"])
    return dict(escolhido=e, alternativas=testados,
                motivo=f"menor chumbador que resiste a {uplift_kn:.1f} kN "
                       f"({e['trd']:.1f} kN) com embutimento de "
                       f"{e['embutimento']:.0f} mm num radier de "
                       f"{esp_radier:.0f} mm (H: resistencia do fabricante)")
