"""FOTOVOLTAICA — geracao propria dimensionada do consumo do modelo, R61.

Ate R60 a fotovoltaica era "infraestrutura futura" e 0,15 kN/m2 de carga
reservada. Em Manaus — tarifa entre as mais altas do pais, 36 kVA de demanda,
oito splits, 184 m2 de cobertura plana com 4,6 kWh/m2.dia — deixa-la para
depois custa exatamente o que mais custa depois: abrir parede para o cabo,
achar lugar para o inversor, e conferir se a terca aguenta.

O consumo NAO e chute de "kWh por m2": e a soma do que o proprio modelo
declara — capacidade de cada split, potencia calculada da iluminacao,
chuveiros — com horas de uso declaradas (H). O sol (HSP) e a tarifa sao dados
de sitio (H): pendencia 15.
"""
from __future__ import annotations

import math

HSP = 4.6                  # (H) kWh/m2.dia, Atlas Brasileiro de Energia Solar (INPE), Manaus
PR = 0.78                  # performance ratio: temperatura, sujeira, inversor, cabos
SEER = 3.5                 # (H) kW termico / kW eletrico dos inverters
HORAS = {"intimo": 8.0, "social": 6.0, "office": 4.0, "lounge": 3.0, "oficina": 2.0}
SIMULTANEIDADE = 0.7       # nem todos os splits ligados as mesmas horas
HORAS_ILUM = 4.0
BANHOS_DIA, MIN_BANHO = 5, 8
BASE_KWH_DIA = 9.0         # (H) geladeira, eletrodomesticos, bombas, standby
TARIFA = 0.95              # (H) R$/kWh com impostos, Amazonas Energia
MODULO = dict(wp=550, larg=1_134, comp=2_278, massa_kg=27.5)
FOLGA_AREA = 1.15          # espaco entre fileiras e passagem
ESTRUTURA_KG_M2 = 5.0
INVERSORES_KW = (5, 8, 10, 12, 15)
PASSARELA_MM = 600
LIMITE_CC_CA = 1.35


def consumo_dia(pj) -> dict:
    import nucleo.luminotecnica as lu
    clima = 0.0
    for c in pj.CLIMATIZACAO:
        if c.get("reserva"):
            continue
        cod = c["amb"]
        uso = ("office" if c.get("compartimento") == "OFFICE" else
               "lounge" if cod == "S-LOU" else
               "oficina" if cod == "T-OFI" else
               "social" if cod in ("T-SOC", "T-GOU", "T-COZ") else "intimo")
        kwe = c["capacidade"] / 12_000.0 * 3.517 / SEER   # BTU/h -> kW frio -> kW eletrico
        clima += kwe * HORAS[uso]
    clima *= SIMULTANEIDADE
    ilum = lu.levantar(pj)["w_geral"] / 1000.0 * HORAS_ILUM
    aq = pj.AQUECIMENTO
    chuveiro = aq["potencia_un"] / 1000.0 * BANHOS_DIA * MIN_BANHO / 60.0
    total = clima + ilum + chuveiro + BASE_KWH_DIA
    return dict(clima=round(clima, 1), iluminacao=round(ilum, 1),
                chuveiro=round(chuveiro, 1), base=BASE_KWH_DIA, total=round(total, 1))


def levantar(pj, planos: dict) -> dict:
    cons = consumo_dia(pj)
    kwp = cons["total"] / (HSP * PR)
    n_pedido = math.ceil(kwp * 1000 / MODULO["wp"])
    sup = [d for d in planos["detalhe"] if d["tipo"] == "cobertura" and d["composicao"] == "CB-1"
           and d["plano"].startswith("S-") and d["material"] == "PIR"]
    area_sup = sum(d["area"] for d in sup)
    xs = [a.x for a in pj.SUPERIOR]; xe = [a.x + a.w for a in pj.SUPERIOR]
    ys = [a.y for a in pj.SUPERIOR]; ye = [a.y + a.h for a in pj.SUPERIOR]
    perim = 2 * ((max(xe) - min(xs)) + (max(ye) - min(ys))) / 1000.0
    disponivel = max(area_sup - perim * PASSARELA_MM / 1000.0, 0.0)
    # O que cabe manda. A cobertura do superior e a unica sem sombra da propria
    # casa; a da garagem fica a leste do volume de dois pavimentos e perde o
    # sol da tarde. Instala-se o que o superior comporta e declara-se a fracao
    # do consumo coberta — em vez de desenhar modulos onde nao cabem.
    area_por_modulo = MODULO["larg"] * MODULO["comp"] / 1e6 * FOLGA_AREA
    n_cabe = int(disponivel // area_por_modulo)
    n = min(n_pedido, n_cabe)
    kwp_inst = n * MODULO["wp"] / 1000.0
    area_mod = n * MODULO["larg"] * MODULO["comp"] / 1e6
    area_com_folga = area_mod * FOLGA_AREA
    carga = (n * MODULO["massa_kg"] + ESTRUTURA_KG_M2 * area_mod) * 9.81 / 1000.0 / area_com_folga
    import nucleo.cargas as cg
    limite = cg.EQUIPAMENTOS["placa solar fotovoltaica"]
    inv = next((k for k in INVERSORES_KW if k >= kwp_inst / LIMITE_CC_CA), INVERSORES_KW[-1])
    geracao = kwp_inst * HSP * PR * 365
    consumo_ano = cons["total"] * 365
    tc = next((t for t in pj.TECNICOS if t["cod"] == "TC-17"), None)
    cx = (min(xs) + max(xe)) / 2; cy = (min(ys) + max(ye)) / 2
    cabo = 2 * (abs(cx - tc["x"]) + abs(cy - tc["y"]) + pj.TOPO_PLATIBANDA) / 1000.0 if tc else 0.0
    import nucleo.bom as bo
    custo = (n * bo.PRECO_FV["modulo_un"] + inv * bo.PRECO_FV["inversor_kw"]
             + area_com_folga * bo.PRECO_FV["estrutura_m2"] + bo.PRECO_FV["stringbox_un"]
             + cabo * bo.PRECO_FV["cabo_m"] + kwp_inst * bo.PRECO_FV["instalacao_kwp"]
             + bo.PRECO_FV["homologacao_un"])
    economia = min(geracao, consumo_ano) * TARIFA
    return dict(consumo_kwh_dia=cons["total"], consumo_kwh_mes=round(cons["total"] * 30.4, 0),
                consumo=cons, hsp=HSP, pr=PR, kwp=round(kwp, 2), n_modulos=n,
                n_pedido=n_pedido, n_cabe=n_cabe,
                modulo_wp=MODULO["wp"], kwp_instalado=round(kwp_inst, 2),
                area_modulos_m2=round(area_com_folga, 1), area_cobertura_m2=round(disponivel, 1),
                cabe=area_com_folga <= disponivel, carga_kn_m2=round(carga, 3),
                carga_limite_kn_m2=limite, carga_ok=carga <= limite,
                inversor_kw=float(inv), local_inversor=tc["cod"] if tc else "",
                cabo_m=round(cabo, 1), geracao_kwh_ano=round(geracao, 0),
                cobertura_consumo=round(min(geracao / consumo_ano, 1.0), 3) if consumo_ano else 0,
                custo=round(custo, 2), tarifa=TARIFA, economia_ano=round(economia, 0),
                payback_anos=round(custo / economia, 1) if economia else 0)


def conferir(pj, r: dict) -> list[tuple[str, str, bool]]:
    f = r["camadas"]["fotovoltaica"]
    return [
        ("os modulos cabem na cobertura do superior, fora da passarela",
         f"{f['area_modulos_m2']:.1f} m2 em {f['area_cobertura_m2']:.1f} m2", f["cabe"]),
        ("a carga dos modulos nao passa da reservada em cargas",
         f"{f['carga_kn_m2']:.3f} kN/m2 contra {f['carga_limite_kn_m2']:.2f}", f["carga_ok"]),
        ("o inversor tem lugar declarado na faixa tecnica",
         f"{f['local_inversor'] or 'sem local'}", bool(f["local_inversor"])),
        ("microgeracao: potencia abaixo de 75 kW", f"{f['kwp_instalado']:.2f} kWp",
         f["kwp_instalado"] <= 75),
        ("a geracao e da ordem do consumo, nem 3x nem 1/3",
         f"{f['geracao_kwh_ano'] / max(f['consumo_kwh_dia'] * 365, 1) * 100:.0f} % do consumo "
         f"estimado ({f['n_modulos']} de {f['n_pedido']} modulos pedidos cabem)",
         0.6 <= (f["geracao_kwh_ano"] / max(f["consumo_kwh_dia"] * 365, 1)) <= 1.6),
    ]
