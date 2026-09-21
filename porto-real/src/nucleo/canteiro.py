"""CANTEIRO DE OBRAS — logistica, estoque, circulacao e drenagem provisoria (R79).

A matriz tinha "planta do canteiro" em FALTA desde R70, com a nota "canteiro
no recuo de frente e na faixa tecnica". Aqui o canteiro sai do que o modelo
ja sabe: o recuo de frente (7,2 x 20 m) e a faixa tecnica norte (3,2 m) sao
o unico chao que a obra nao ocupa; o portao veicular e o de pedestre ja tem
coordenada; os 62 paineis tem comprimento e massa; as placas tem paginacao;
a plataforma tem cota e a chuva de projeto e a mesma da calha.

  ZONAS. Pista de veiculos na linha do portao (5,4 m), do meio-fio ao pe da
  plataforma. Entrada de pedestres na linha da porta. Conteiner de escritorio
  e almoxarifado no canto sul do recuo; vestiario e refeitorio no canto norte;
  estoque de paineis em cavalete (em pe, 100 mm por painel) e placas
  paletizadas entre a pista e o vestiario; sanitario quimico e baias de
  residuos (CONAMA 307, classes A a D) na faixa tecnica norte, onde os
  elementos tecnicos definitivos so entram na ultima fase.
  MOVIMENTACAO. O painel mais pesado contra o que quatro montadores carregam
  (25 kg cada, H): acima disso o painel anda sobre o radier em carrinho e
  sobe ao superior por guincho de coluna. Munck do recuo nao alcanca o fundo
  da casa (26 m): nao se conta com ele.
  DRENAGEM PROVISORIA. O lote cai para a testada. Vala de pe de plataforma
  ao longo do recuo, caixa de sedimentacao antes da sarjeta, vazao pelo
  metodo racional com C = 0,50 de solo exposto (H) e a intensidade de
  projeto da cobertura. Sem ela, a chuva leva o solo da troca para a rua.
  FASES. O recuo muda de conteudo por fase: terraplenagem e radier, montagem
  do LSF, fechamentos e cobertura, instalacoes e acabamentos, externas.
"""
from __future__ import annotations

import math

# ---------------------------------------------------------------- (H)
EQUIPE = 8                       # pessoas em pico (4 montadores LSF + 4 acabamentos)
NR18 = dict(vaso_por=20, lavatorio_por=10, chuveiro_por=10, refeitorio_m2_pessoa=1.0, tapume_h=2_200)
CARGA_MANUAL_KG = 25             # por pessoa (H, NR-17 e pratica)
MONTADORES_POR_PAINEL = 4
CAVALETE_MM_POR_PAINEL = 100
PLACAS_POR_PALETE = 40
PALETE = (1_200, 2_400)
CONTEINER_20 = (5_898, 2_352)
SANITARIO_QUIMICO = (1_100, 1_100)
BAIA = (2_000, 2_000)
CLASSES_RESIDUO = ("A — solo, concreto, ceramica", "B — aco, madeira, gesso, plastico, papel",
                   "C — la mineral e outros sem reciclagem", "D — tintas, solventes, oleos")
C_SOLO_EXPOSTO = 0.50
VALA = dict(base=300, prof=300, talude=1.0, decliv=0.01, n_manning=0.025)
CAIXA_SEDIMENTACAO = dict(w=1_000, h=1_000, prof=800)
LIGACAO_PROVISORIA = dict(energia="padrao provisorio trifasico 220/127 V, 63 A (H): serras, parafusadeiras, "
                                  "guincho e bomba; no ponto do medidor definitivo (TC-08)",
                          agua="cavalete provisorio DN20 no mesmo ponto; caixa de 1.000 L elevada no canteiro")
PISTA_LARG_MIN = 3_500
FASES_OBRA = [
    ("1", "Terraplenagem, troca de solo e radier", "pista para caminhao betoneira e bomba; estoque vazio; vala e caixa ja abertas"),
    ("2", "Montagem do LSF (62 paineis, 2 lotes)", "cavalete do lote do terreo, depois do superior; carrinho sobre o radier; guincho de coluna"),
    ("3", "Fechamentos e cobertura", "placas paletizadas (OSB, cimenticia, gesso) no lugar do cavalete; telhas na pista"),
    ("4", "Instalacoes e acabamentos", "almoxarifado cheio; palete de piso e louças; baias em uso pleno"),
    ("5", "Externas: piscina, deck, paisagismo, muro", "escavacao da piscina pelo fundo; canteiro recua para o recuo; muro por ultimo, e o tapume sai"),
]


def _lote_canteiro(pj) -> dict:
    return dict(x0=0, y0=0, x1=pj.LOTE_L, y1=pj.LOTE_P, recuo=pj.RECUO_FRENTE, sul=pj.RECUO_ESQ)


def _plataforma(pj) -> dict:
    import nucleo.terreno as tr
    p = tr.plataforma(pj)
    return dict(x0=pj.RECUO_ESQ, y0=pj.RECUO_FRENTE, w=p["larg_mm"], h=p["prof_mm"], cota=p["cota_plataforma"])


def paineis_para_canteiro(pj) -> dict:
    import nucleo.detalhes_lsf as dl
    import nucleo.painel as pn
    pT, pS, _ = dl._paineis(pj)
    cat = pn._catalogo_massa()
    lotes = {}
    for nome, ps in (("terreo", pT), ("superior", pS)):
        ms = [p.massa(cat) for p in ps]
        lotes[nome] = dict(n=len(ps), comp_max=max(p.comp for p in ps), massa_max=round(max(ms), 1),
                           massa_total=round(sum(ms)), cavalete_mm=len(ps) * CAVALETE_MM_POR_PAINEL + 600)
    maior = max(lotes.values(), key=lambda l: l["n"])
    pesado = max(lotes.values(), key=lambda l: l["massa_max"])
    return dict(lotes=lotes, n=sum(l["n"] for l in lotes.values()), comp_max=max(l["comp_max"] for l in lotes.values()),
                massa_max=pesado["massa_max"], cavalete_larg=maior["cavalete_mm"], cavalete_comp=maior["comp_max"] + 1_000)


def placas_para_canteiro(pj) -> dict:
    import nucleo.detalhes_lsf as dl
    import nucleo.camadas as cd
    pT, pS, _ = dl._paineis(pj)
    todos = pT + pS
    import especificacao as ep   # paredes_classificadas, como em detalhes_lsf.paginacao_fachada
    segs = ep.paredes_classificadas(pj.TERREO) + ep.paredes_classificadas(pj.SUPERIOR)
    fam = cd.familia_por_painel(todos, segs)
    pg = cd.paginar(todos, fam["familia"])
    itens = [dict(material=i["material"], placas=i.get("placas", i.get("n", 0))) for i in pg["itens"]]
    n = sum(i["placas"] for i in itens)
    paletes = math.ceil(n / PLACAS_POR_PALETE) if n else 0
    return dict(itens=itens, placas=n, paletes=paletes, area_m2=round(paletes * PALETE[0] * PALETE[1] / 1e6 * 1.5, 1))


def zonas(pj) -> list[dict]:
    """Cada zona com retangulo no referencial do modelo (x norte, y oeste)."""
    L = _lote_canteiro(pj)
    pl = _plataforma(pj)
    pg = pj.ACESSO_TESTADA
    pn_ = paineis_para_canteiro(pj)
    pc = placas_para_canteiro(pj)
    rec = L["recuo"]
    z = []
    z.append(dict(cod="CT-PISTA", nome="Pista de veiculos e descarga", x=pg["veiculo_x"] - pg["veiculo_larg"] / 2, y=0,
                  w=pg["veiculo_larg"], h=rec, fase="1-5", obs="na linha do portao veicular; betoneira, bomba e carreta descarregam aqui"))
    z.append(dict(cod="CT-PED", nome="Entrada de pedestres", x=pg["pedestre_x"] - pg["pedestre_larg"] / 2 - 300, y=0,
                  w=pg["pedestre_larg"] + 600, h=rec, fase="1-5", obs="na linha do portao de pedestre e da porta P01; separada da pista"))
    # canto sul do recuo: conteiner escritorio + almoxarifado, longitudinal
    z.append(dict(cod="CT-ESC", nome="Conteiner 20': escritorio e almoxarifado", x=200, y=600, w=CONTEINER_20[1], h=CONTEINER_20[0],
                  fase="1-5", obs="porta para a pista; ferramenta eletrica e fixacao trancadas"))
    # norte do recuo: cavalete de paineis deitado ao longo de x (o painel de
    # 7,2 m nao cabe em pe no recuo de 7,2 m com folga), vestiario junto a
    # testada, a oeste do medidor TC-08
    x = pg["pedestre_x"] + pg["pedestre_larg"] / 2 + 600
    med = next((t for t in pj.TECNICOS if "medidores" in t["nome"].lower()), None)
    z.append(dict(cod="CT-CAV", nome=f"Cavalete de paineis ({pn_['n']} em 2 lotes)", x=x, y=rec - pn_["cavalete_larg"],
                  w=pn_["cavalete_comp"], h=pn_["cavalete_larg"], fase="2",
                  obs=f"paineis em pe, {CAVALETE_MM_POR_PAINEL} mm cada, comprimento ao longo da testada; o maior tem {pn_['comp_max'] / 1000:.1f} m"))
    # nas fases 3 e 4 o cavalete ja esta vazio: as placas ocupam o mesmo chao
    n_por_vez = int((pn_["cavalete_comp"] // (PALETE[1] + 300)) * (pn_["cavalete_larg"] // (PALETE[0] + 300)))
    z.append(dict(cod="CT-PLA", nome=f"Placas paletizadas ({pc['paletes']} paletes, {n_por_vez} por vez)", x=x, y=rec - pn_["cavalete_larg"],
                  w=pn_["cavalete_comp"], h=pn_["cavalete_larg"], fase="3-4",
                  obs=f"no chao do cavalete; entregas em lotes de {n_por_vez} paletes; OSB, cimenticia e gesso sob lona, gesso sobre estrado"))
    x_vest = (med["x"] - 300 - CONTEINER_20[0]) if med else L["x1"] - 300 - CONTEINER_20[0]
    z.append(dict(cod="CT-VES", nome="Conteiner 20': vestiario e refeitorio", x=x_vest, y=300, w=CONTEINER_20[0], h=CONTEINER_20[1],
                  fase="1-5", obs=f"{EQUIPE} pessoas: {NR18['refeitorio_m2_pessoa'] * EQUIPE:.0f} m2 de refeitorio; armarios; ao lado do medidor"))
    # faixa tecnica norte: sanitario e baias (os elementos tecnicos so entram na fase 5)
    ft_x = L["x1"] - 300 - BAIA[0]
    z.append(dict(cod="CT-SAN", nome="Sanitario quimico", x=ft_x + BAIA[0] - SANITARIO_QUIMICO[0], y=rec + 3_000,
                  w=SANITARIO_QUIMICO[0], h=SANITARIO_QUIMICO[1], fase="1-5",
                  obs=f"{math.ceil(EQUIPE / NR18['vaso_por'])} para {EQUIPE} pessoas (1 por {NR18['vaso_por']}); lavatorio no vestiario"))
    y = rec + 3_000 + SANITARIO_QUIMICO[1] + 1_500
    for i, cl in enumerate(CLASSES_RESIDUO):
        z.append(dict(cod=f"CT-RES-{cl[0]}", nome=f"Baia de residuos classe {cl}", x=ft_x, y=y + i * (BAIA[1] + 300),
                      w=BAIA[0], h=BAIA[1], fase="1-5", obs="CONAMA 307; caçamba de 5 m3 na pista quando a baia enche"))
    # circulacao de trabalhadores: faixa tecnica norte e recuo sul, ate o fundo
    z.append(dict(cod="CT-CIRC-N", nome="Circulacao de trabalhadores (norte)", x=pl["x0"] + pl["w"], y=rec, w=L["x1"] - (pl["x0"] + pl["w"]) - BAIA[0] - 600,
                  h=L["y1"] - rec, fase="1-5", obs="faixa tecnica; 1,20 m livres ao lado das baias", circulacao=True))
    z.append(dict(cod="CT-CIRC-S", nome="Circulacao de trabalhadores (sul)", x=0, y=rec, w=L["sul"], h=L["y1"] - rec, fase="1-5",
                  obs="recuo sul de 2,40 m; acesso ao fundo e a piscina na fase 5", circulacao=True))
    z.append(dict(cod="CT-TAP", nome="Tapume da testada", x=0, y=-200, w=L["x1"], h=200, fase="1-4",
                  obs=f"{NR18['tapume_h'] / 1000:.1f} m (NR-18) ate o muro da fase 5; portoes provisorios nas duas linhas"))
    for q in z:
        q["area_m2"] = round(q["w"] * q["h"] / 1e6, 1)
        a, _, b_ = q["fase"].partition("-")
        q["fases"] = list(range(int(a), int(b_ or a) + 1))
    return z


def movimentacao(pj) -> dict:
    p = paineis_para_canteiro(pj)
    lim = CARGA_MANUAL_KG * MONTADORES_POR_PAINEL
    pesados = p["massa_max"] > lim
    return dict(massa_max=p["massa_max"], limite_manual=lim, montadores=MONTADORES_POR_PAINEL,
                veredito=("carrinho de painel sobre o radier e guincho de coluna para o superior (H)"
                          if pesados else f"a mao, {MONTADORES_POR_PAINEL} montadores"),
                munck="nao: do recuo nao alcanca o fundo da casa (26 m); descarga da carreta a mao, no cavalete",
                comp_max=p["comp_max"], lotes=p["lotes"])


def drenagem(pj) -> dict:
    import nucleo.pluvial as pl
    pla = _plataforma(pj)
    L = _lote_canteiro(pj)
    i = pj.COBERTURA["intensidade_mm_h"]
    a_lote = L["x1"] * L["y1"] / 1e6
    a_plat = pla["w"] * pla["h"] / 1e6
    a_exp = a_lote - a_plat
    q_ls = C_SOLO_EXPOSTO * i * a_exp / 3600
    # vala trapezoidal: Manning
    b, hh, m, s, n = VALA["base"] / 1000, VALA["prof"] / 1000, VALA["talude"], VALA["decliv"], VALA["n_manning"]
    area = (b + m * hh) * hh
    per = b + 2 * hh * math.sqrt(1 + m * m)
    q_vala = area * (area / per) ** (2 / 3) * math.sqrt(s) / n * 1000
    cx = CAIXA_SEDIMENTACAO
    vol = cx["w"] * cx["h"] * cx["prof"] / 1e9
    # tracado: pe da plataforma (y = recuo) de x = pista ate o canto norte, depois ate a caixa junto a sarjeta
    x_caixa = L["x1"] - 300 - cx["w"] - 3_000
    tracado = [(pla["x0"], L["recuo"] + 300), (L["x1"] - 600, L["recuo"] + 300), (L["x1"] - 600, 900), (x_caixa + cx["w"], 900)]
    comp = sum(abs(tracado[k + 1][0] - tracado[k][0]) + abs(tracado[k + 1][1] - tracado[k][1]) for k in range(len(tracado) - 1))
    return dict(intensidade=i, c=C_SOLO_EXPOSTO, area_exposta_m2=round(a_exp, 1), q_ls=round(q_ls, 1),
                vala=VALA, q_vala_ls=round(q_vala, 1), ok=q_vala >= q_ls, comp_mm=round(comp), tracado=tracado,
                caixa=dict(x=x_caixa, y=300, **cx), volume_m3=round(vol, 2), tempo_s=round(vol / (q_ls / 1000)),
                sentido=pj.DECLIVIDADE_SENTIDO,
                obs="a vala corre no pe da plataforma e leva a agua do lote a caixa de sedimentacao antes da sarjeta; "
                    "limpeza da caixa apos cada chuva forte")


def ligacoes(pj) -> dict:
    med = next((t for t in pj.TECNICOS if "medidores" in t["nome"].lower()), None)
    return dict(ponto=med["cod"] if med else "?", x=med["x"] if med else 0, y=med["y"] if med else 0, **LIGACAO_PROVISORIA)


def resumo(pj) -> dict:
    z = zonas(pj)
    m = movimentacao(pj)
    d = drenagem(pj)
    return dict(zonas=len(z), area_canteiro_m2=round(sum(q["area_m2"] for q in z if not q.get("circulacao")), 1),
                equipe=EQUIPE, paineis=m["lotes"]["terreo"]["n"] + m["lotes"]["superior"]["n"], massa_max=m["massa_max"],
                paletes=placas_para_canteiro(pj)["paletes"], q_ls=d["q_ls"], q_vala_ls=d["q_vala_ls"], fases=len(FASES_OBRA))


def _sobrepoe(a, b) -> bool:
    return not (a["x"] + a["w"] <= b["x"] or b["x"] + b["w"] <= a["x"] or a["y"] + a["h"] <= b["y"] or b["y"] + b["h"] <= a["y"])


def conferir(pj) -> list[tuple[str, str, bool]]:
    out = []
    L, pla = _lote_canteiro(pj), _plataforma(pj)
    z = [q for q in zonas(pj) if q["cod"] != "CT-TAP"]
    fixas = [q for q in z if not q.get("circulacao")]
    dentro = [q["cod"] for q in z if q["x"] < 0 or q["y"] < 0 or q["x"] + q["w"] > L["x1"] or q["y"] + q["h"] > L["y1"]]
    out.append(("toda zona dentro do lote", f"{len(z)} zonas" + (": fora " + ", ".join(dentro) if dentro else ""), not dentro))
    sob = [f"{a['cod']}/{b['cod']}" for i, a in enumerate(fixas) for b in fixas[i + 1:]
           if _sobrepoe(a, b) and set(a["fases"]) & set(b["fases"])]
    out.append(("zonas fixas nao se sobrepoem na mesma fase", ", ".join(sob) if sob else f"{len(fixas)} zonas fixas", not sob))
    med = next((t for t in pj.TECNICOS if "medidores" in t["nome"].lower()), None)
    if med:
        sobre = [q["cod"] for q in fixas if _sobrepoe(q, med)]
        out.append(("o medidor (ponto de ligacao) fica livre", ", ".join(sobre) if sobre else f"{med['cod']} livre", not sobre))
    casa = dict(x=pla["x0"], y=pla["y0"], w=pla["w"], h=pla["h"])
    na_casa = [q["cod"] for q in fixas if _sobrepoe(q, casa)]
    out.append(("nenhuma zona sobre a plataforma da casa", ", ".join(na_casa) if na_casa else "recuo e faixa tecnica apenas", not na_casa))
    dk = dict(x=pj.DECK["x"], y=pj.DECK["y"], w=pj.DECK["w"], h=pj.DECK["h"])
    no_deck = [q["cod"] for q in fixas if _sobrepoe(q, dk)]
    out.append(("nenhuma zona sobre a piscina e o deck", ", ".join(no_deck) if no_deck else "fundo livre para a fase 5", not no_deck))
    pista = next(q for q in z if q["cod"] == "CT-PISTA")
    out.append(("pista de veiculos", f"{pista['w'] / 1000:.1f} m na linha do portao (min {PISTA_LARG_MIN / 1000:.1f})", pista["w"] >= PISTA_LARG_MIN))
    cav = next(q for q in z if q["cod"] == "CT-CAV")
    m = movimentacao(pj)
    out.append(("o painel mais longo cabe no cavalete", f"{m['comp_max'] / 1000:.1f} m em {cav['w'] / 1000:.1f} m", cav["w"] >= m["comp_max"]))
    out.append(("movimentacao do painel mais pesado decidida", f"{m['massa_max']} kg contra {m['limite_manual']} kg a mao: {m['veredito'][:44]}", True))
    san = [q for q in z if q["cod"] == "CT-SAN"]
    out.append(("sanitarios pela NR-18", f"{len(san)} para {EQUIPE} pessoas (1 por {NR18['vaso_por']})", len(san) >= math.ceil(EQUIPE / NR18["vaso_por"])))
    res = [q for q in z if q["cod"].startswith("CT-RES")]
    out.append(("baias de residuos por classe", f"{len(res)} baias para {len(CLASSES_RESIDUO)} classes (CONAMA 307)", len(res) == len(CLASSES_RESIDUO)))
    d = drenagem(pj)
    out.append(("vala provisoria vence a chuva de projeto", f"{d['q_vala_ls']} L/s de capacidade contra {d['q_ls']} L/s "
                f"(C {d['c']}, {d['intensidade']} mm/h, {d['area_exposta_m2']} m2 expostos)", d["ok"]))
    out.append(("caixa de sedimentacao antes da sarjeta", f"{d['volume_m3']} m3, {d['tempo_s']} s de retencao na vazao de projeto", d["tempo_s"] >= 30))
    lg = ligacoes(pj)
    out.append(("ligacoes provisorias no ponto do medidor definitivo", f"{lg['ponto']} em ({lg['x']}, {lg['y']})", lg["ponto"] != "?"))
    circ = [q for q in z if q.get("circulacao")]
    out.append(("circulacao de trabalhadores ate o fundo pelos dois lados", f"{len(circ)} faixas, a mais estreita com {min(q['w'] for q in circ) / 1000:.2f} m",
                len(circ) == 2 and min(q["w"] for q in circ) >= 1_200))
    return out
