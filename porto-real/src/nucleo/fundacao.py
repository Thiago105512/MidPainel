"""FUNDACAO — o radier, que era prosa no desenho e numero magico no codigo.

A espessura de 180 mm existia em dois lugares: um literal dentro do modulo de
desenho e uma copia dentro do dimensionamento de ancoragem. Nenhum dos dois era
dado do projeto. O desenho dizia 180 e a ancoragem acreditava — e se alguem
mudasse um, o outro continuaria certo de si.

Concreto, aco, lastro e impermeabilizacao de base nunca entraram no BOM. Num
sobrado em LSF a fundacao costuma ser 8 a 15 % do custo, e era o ultimo sistema
construtivo grande que estava em zero.

O QUE ESTE MODULO FAZ E O QUE NAO FAZ. Ele deriva QUANTIDADE a partir de uma
espessura declarada e da projecao que o modelo ja conhece. Ele NAO dimensiona
radier: espessura, taxa de armadura e fck dependem de sondagem, e a pendencia 2
do caderno e exatamente essa. Derivar quantidade de uma espessura (H) e
legitimo e util; apresentar a espessura como resultado seria fraude.
"""
from __future__ import annotations


def _contorno(pj) -> dict:
    """Projecao do radier: envoltoria dos ambientes do terreo mais o balanco.

    A area nao e a area util nem a projecao coberta: e o que se concreta. Um
    radier acompanha a face EXTERNA da parede e ainda avanca alguns
    centimetros, e essa diferenca paga concreto.
    """
    b = pj.RADIER["balanco_borda"]
    xs = [a.x for a in pj.TERREO] + [a.x + a.w for a in pj.TERREO]
    ys = [a.y for a in pj.TERREO] + [a.y + a.h for a in pj.TERREO]
    # area real dos ambientes, nao do retangulo envolvente: a casa tem recorte
    area = sum(a.w * a.h for a in pj.TERREO) / 1e6
    # perimetro externo aproximado pela envoltoria, declarado como tal
    perim = 2 * ((max(xs) - min(xs)) + (max(ys) - min(ys))) / 1000.0
    return dict(area=area + perim * b / 1000.0, perimetro=perim,
                area_ambientes=area, balanco=b,
                obs="area = soma dos ambientes mais uma faixa de balanco ao "
                    "longo do perimetro; o perimetro vem da envoltoria, o que "
                    "e conservador numa planta recortada")


def levantar(pj) -> dict:
    """Concreto, aco, lastro, lona e forma — da geometria e da espessura (H)."""
    R = pj.RADIER
    c = _contorno(pj)
    esp_m = R["espessura"] / 1000.0
    volume = c["area"] * esp_m
    aco_kg = volume * R["taxa_armadura"]
    # a tela cobre a area em duas direcoes; a taxa acima ja inclui reforco de
    # borda e de apoio, entao a tela e a parcela dela que se compra em rolo
    tela_m2 = c["area"] * 1.10          # 10 % de traspasse
    return dict(
        area=round(c["area"], 1), perimetro=round(c["perimetro"], 1),
        espessura=R["espessura"], fck=R["fck"], aco=R["aco"],
        volume_m3=round(volume, 2),
        aco_kg=round(aco_kg, 1), tela_m2=round(tela_m2, 1), tela=R["tela"],
        lastro_m3=round(c["area"] * R["lastro"] / 1000.0, 2),
        lona_m2=round(c["area"] * 1.10, 1),
        forma_m2=round(c["perimetro"] * esp_m, 1),
        consumo_m3_m2=round(volume / pj.CADASTRO.area_m2, 3),
        norma=R["norma"], pendencia=R["pendencia"],
        obs=c["obs"],
        hipoteses=[
            f"espessura {R['espessura']} mm e (H): sem sondagem e "
            f"pre-dimensionamento, nao calculo",
            f"taxa de armadura {R['taxa_armadura']:.0f} kg/m3 e (H) de radier "
            f"leve; solo mole ou carga concentrada elevam",
            f"fck {R['fck']} MPa e (H)",
            "este modulo deriva QUANTIDADE de uma espessura declarada; nao "
            "dimensiona radier",
        ])
