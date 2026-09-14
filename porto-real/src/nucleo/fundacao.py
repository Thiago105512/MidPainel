"""FUNDACAO — o radier, que era prosa no desenho e numero magico no codigo.

A espessura de 180 mm existia em dois lugares: um literal dentro do modulo de
desenho e uma copia dentro do dimensionamento de ancoragem. Nenhum dos dois era
dado do projeto. O desenho dizia 180 e a ancoragem acreditava — e se alguem
mudasse um, o outro continuaria certo de si.

Concreto, aco, lastro e impermeabilizacao de base nunca entraram no BOM. Num
sobrado em LSF a fundacao costuma ser 8 a 15 % do custo, e era o ultimo sistema
construtivo grande que estava em zero.

O QUE ESTE MODULO FAZ E O QUE NAO FAZ. Ele deriva QUANTIDADE a partir da
geometria que o modelo conhece e da secao que geotecnia.py verificou. Ate R51
espessura, fck e taxa de armadura eram (H) porque nao havia sondagem; em R52 o
proprietario entregou SP-01, SP-02 e SP-03, e nucleo/geotecnia.py passou a
CONFERIR a secao contra pressao de contato, recalque e distorcao angular.
Continua nao sendo projeto de fundacao com ART — isso e a pendencia 3 — mas
deixou de ser numero sem origem: agora existe contra o que conferir.
"""
from __future__ import annotations


def contorno(pj) -> dict:
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
    """Concreto, aco, lastro, lona e forma — da geometria e da secao verificada.

    Tres numeros deixaram de ser inventados aqui em R52. O VOLUME passou a
    somar o engrossamento do perimetro, que existia no desenho e nao no
    concreto. O ACO passou a vir da armadura real — duas telas e o reforco de
    borda — em vez de uma taxa por metro cubico: taxa virou resultado. E a
    TERRAPLENAGEM entrou, porque a decisao geotecnica de trocar 600 mm de
    aterro por material compactado e a maior despesa nova do sistema e nao
    existia em linha nenhuma.
    """
    import nucleo.geotecnia as gt
    R = pj.RADIER
    c = contorno(pj)
    esp_m = R["espessura"] / 1000.0
    vol = gt.volume_concreto(pj)
    arm = gt.armadura(pj)
    terra = gt.terraplenagem(pj)
    return dict(
        area=round(c["area"], 1), perimetro=round(c["perimetro"], 1),
        espessura=R["espessura"], fck=R["fck"], aco=R["aco"],
        volume_m3=vol["total"], volume_laje_m3=vol["laje"],
        volume_borda_m3=vol["borda"],
        borda=gt.BORDA,
        aco_kg=arm["total_kg"], taxa_kg_m3=arm["taxa_kg_m3"],
        tela_m2=arm["tela_m2"], tela=R["tela"],
        lastro_m3=terra["lastro_m3"],
        lona_m2=round(c["area"] * 1.10, 1),
        forma_m2=round(c["perimetro"] * gt.BORDA["altura"] / 1000.0, 1),
        consumo_m3_m2=round(vol["total"] / pj.CADASTRO.area_m2, 3),
        terraplenagem=terra,
        norma=R["norma"], pendencia=R["pendencia"],
        obs=c["obs"],
        hipoteses=[
            f"espessura {R['espessura']} mm CONFERIDA em geotecnia.py contra "
            f"pressao de contato, recalque e distorcao — nao mais (H)",
            f"taxa de {arm['taxa_kg_m3']:.1f} kg/m3 e RESULTADO da armadura "
            f"escolhida, nao dado de entrada",
            f"fck {R['fck']} MPa pela classe de agressividade II da NBR 6118, "
            f"nao por arbitrio",
            "nivel d'agua nao consta do boletim e segue (H)",
            "verificacao nao substitui projeto de fundacao com ART "
            "(pendencia 3)",
        ])
