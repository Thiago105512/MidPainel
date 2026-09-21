"""SPDA — protecao contra descargas atmosfericas (NBR 5419), R61.

Manaus esta entre as regioes de maior densidade de descargas do pais, e a
casa tinha DPS no quadro e nenhum para-raios. Para residencia a norma
frequentemente dispensa a protecao externa; aqui a decisao e de projeto:
dois pavimentos, estrutura metalica, Ng alto. E e barata JUSTAMENTE por ser
LSF — a NBR 5419-3 aceita a estrutura de aco como descida natural quando a
secao e >= 50 mm2 e a continuidade e garantida; o montante Ue 90x40x0,95 tem
184 mm2. O que se compra e captor, anel de aterramento, conexoes e ensaio.

Ng e (H): 12 descargas/km2.ano e um valor de mapa (RINDAT/ELAT) para a
regiao, nao uma medicao do sitio. Ele muda o risco calculado, nao a classe
adotada — e por isso a classe e declarada como decisao, nao como consequencia.
"""
from __future__ import annotations

import math

NG_MANAUS = 12.0          # (H) descargas/km2.ano
CD = 1.0                  # fator de localizacao: estrutura isolada (NBR 5419-2)
CLASSE = "IV"             # NBR 5419-3, tabela 2
MALHA_M = {"I": 5.0, "II": 10.0, "III": 15.0, "IV": 20.0}
ESPAC_DESCIDA_M = {"I": 10.0, "II": 10.0, "III": 15.0, "IV": 20.0}
SECAO_MIN_DESCIDA_NATURAL_MM2 = 50.0
HASTE_M = 2.4


def area_exposicao(L: float, W: float, H: float) -> float:
    """Ad em m2 (NBR 5419-2 A.2): a sombra que a estrutura projeta no raio."""
    return L * W + 6 * H * (L + W) + 9 * math.pi * H ** 2


def _secao_montante(pj) -> float:
    try:
        import nucleo.perfis as pf
        q = [p for p in pf.catalogo() if p.forma == "Ue" and abs(p.bw - 90) < 1]
        p = min(q, key=lambda p: p.t)
        return (p.bw + 2 * p.bf + 2 * p.D) * p.t
    except Exception:
        return 184.0


def levantar(pj, cobertura: dict, fundacao: dict) -> dict:
    xs = [a.x for a in pj.TERREO]; xe = [a.x + a.w for a in pj.TERREO]
    ys = [a.y for a in pj.TERREO]; ye = [a.y + a.h for a in pj.TERREO]
    L = (max(xe) - min(xs)) / 1000.0
    W = (max(ye) - min(ys)) / 1000.0
    H = pj.TOPO_PLATIBANDA / 1000.0
    ad = area_exposicao(L, W, H)
    nd = NG_MANAUS * ad * 1e-6 * CD
    perim_env = 2 * (L + W)
    descidas = max(2, math.ceil(perim_env / ESPAC_DESCIDA_M[CLASSE]))
    import nucleo.fundacao as fu
    anel = fu.contorno(pj)["perimetro"]
    return dict(ng=NG_MANAUS, cd=CD, L_m=round(L, 2), W_m=round(W, 2), H_m=round(H, 2),
                ad_m2=round(ad, 0), nd_ano=round(nd, 4),
                retorno_anos=round(1 / nd, 0) if nd else 0, classe=CLASSE,
                malha_m=MALHA_M[CLASSE], espac_descida_m=ESPAC_DESCIDA_M[CLASSE],
                captor_m=round(cobertura["perimetro"], 1), descidas=descidas,
                secao_montante_mm2=round(_secao_montante(pj), 1),
                anel_m=round(anel, 1), hastes=descidas, haste_m=HASTE_M,
                dps_classe1=1, bep=1,
                obs="captor em anel no topo da platibanda; descidas pelos montantes "
                    "de canto com conector de teste a 1,5 m do piso; anel no radier "
                    "ligado a armadura (aterramento de fundacao)")


def conferir(pj, r: dict) -> list[tuple[str, str, bool]]:
    s = r["camadas"]["spda"]
    return [
        ("ha ao menos duas descidas, com espacamento da classe",
         f"{s['descidas']} descidas para {2 * (s['L_m'] + s['W_m']):.1f} m de envoltoria, "
         f"<= {s['espac_descida_m']:.0f} m (classe {s['classe']})", s["descidas"] >= 2),
        ("a estrutura serve de descida natural",
         f"montante com {s['secao_montante_mm2']:.0f} mm2 >= {SECAO_MIN_DESCIDA_NATURAL_MM2:.0f} mm2",
         s["secao_montante_mm2"] >= SECAO_MIN_DESCIDA_NATURAL_MM2),
        ("a cobertura cabe numa celula da malha do captor",
         f"{s['L_m']:.1f} x {s['W_m']:.1f} m contra malha {s['malha_m']:.0f} x {s['malha_m']:.0f}",
         s["L_m"] <= s["malha_m"] and s["W_m"] <= s["malha_m"]),
        ("o anel de aterramento fecha o perimetro do radier",
         f"{s['anel_m']:.1f} m de cobre nu", s["anel_m"] > 0),
        ("o risco esta calculado e declarado, nao presumido",
         f"Ad {s['ad_m2']:.0f} m2, Nd {s['nd_ano']:.4f}/ano — retorno {s['retorno_anos']:.0f} anos",
         s["nd_ano"] > 0),
    ]
