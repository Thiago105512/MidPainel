"""PISO E COBERTURA — o vigamento que faltava, e a direcao que ele define.

Ate R30 a estrutura do modelo eram 805 pecas, e todas as 805 eram de PAREDE.
Nao havia vigamento de entrepiso, nao havia cobertura, nao havia
contraventamento. Uma casa em Light Steel Frame com paredes e sem vigas nao e
uma casa incompleta: e uma casa que nao existe. O piso do pavimento superior
nao se apoiava em nada, e a cobertura tambem nao.

A consequencia era maior que a lacuna visual. A descida de cargas precisava
saber em que direcao a laje vence, e nao sabia — sem vigamento nao ha direcao.
Por isso cada parede recebia carga dos dois lados e a area do pavimento descia
1,54 vezes. Com o vigamento no modelo a direcao passa a ser um dado: cada viga
entrega metade da sua carga em cada apoio, e os apoios sao paredes nomeadas.

REGRA DE VAO. A viga vence a MENOR dimensao do comodo. Nao e estetica: o
momento cresce com o quadrado do vao, entao vencer 3 m em vez de 5 m nao
economiza 40 % de aco, economiza 64 % de momento. Onde o comodo for maior que
o vao maximo do perfil, entra apoio intermediario — e isso e dito, nao
escondido.
"""
from __future__ import annotations

import nucleo.painel as pn
import nucleo.perfis as pf

# Espacamento do vigamento. Comeca na modulacao da parede pela razao que vale
# para tudo em LSF: montante, viga e placa na mesma malha fazem a carga descer
# em linha reta. Quando o vao exige, cai para 400 mm.
ESPACAMENTOS = (600, 400)

# Flecha admissivel do entrepiso. L/350 e o limite geral; piso que recebe
# revestimento fragil (porcelanato colado) pede L/500, e a diferenca decide o
# perfil com muito mais frequencia que o momento.
FLECHA_PISO = 500.0
FLECHA_COBERTURA = 250.0


def _regioes(ambientes, cobertos=False) -> list[dict]:
    """Cada comodo e uma regiao retangular de piso a vencer."""
    return [dict(cod=a.cod, nome=a.nome, x=a.x, y=a.y, w=a.w, h=a.h,
                 area=a.area_mod, molhado=a.molhado)
            for a in ambientes if cobertos or not a.aberto]


def dimensionar_viga(vao_mm: int, carga_kn_m: float, aco, flecha_div: float,
                     cfg: pn.Config = None) -> dict:
    """Perfil da viga pelo vao e pela carga, com as alternativas rejeitadas.

    Reusa a mesma funcao que dimensiona a verga: uma verga e uma viga
    biapoiada sob carga uniforme, e um vigamento de piso tambem. Escrever duas
    funcoes para o mesmo problema seria criar duas verdades que divergem na
    primeira correcao — foi assim que a flecha da verga ficou tres ordens de
    grandeza errada uma vez, e so um cruzamento a pegou.
    """
    cands = [p for p in pf.catalogo()
             if p.familia in ("montante", "viga") and p.bw >= 140]
    # o limite de flecha vai COMO PARAMETRO: filtrar por fora a lista que a
    # funcao devolve truncada foi como tres comodos apareceram invencíveis
    r = pn.verga_necessaria(vao_mm, carga_kn_m, aco, cfg, candidatos=cands,
                            flecha_div=flecha_div)
    lim = vao_mm / flecha_div
    validos = [t for t in r["testados"] if t["ok"]]
    if not validos:
        return dict(escolhido=None, alternativas=r["alternativas"],
                    flecha_lim=lim,
                    motivo=(f"nenhum perfil vence {vao_mm} mm com "
                            f"{carga_kn_m:.2f} kN/m dentro de L/{flecha_div:.0f} "
                            f"({lim:.1f} mm): o comodo exige apoio intermediario"))
    e = min(validos, key=lambda t: t["massa"])
    return dict(escolhido=e, alternativas=r["alternativas"], flecha_lim=lim,
                motivo=(f"{e['perfil']}: utilizacao {e['uso']*100:.0f} %, "
                        f"flecha {e['flecha']:.1f} de {lim:.1f} mm "
                        f"(L/{flecha_div:.0f}); {len(r['testados'])-len(validos)} "
                        f"alternativa(s) rejeitada(s)"))


def vigar_regiao(reg: dict, carga_perm: float, carga_acid: float, aco,
                 tipo: str = "piso", cfg: pn.Config = None) -> dict:
    """Vigamento de UMA regiao: vigas, bordas, travamento e a direcao de vao.

    A direcao nao e escolhida por conveniencia de desenho: a viga vence a MENOR
    dimensao, e por isso o vao e `min(w, h)` e as vigas se repetem ao longo da
    MAIOR. Dizer a direcao e o que permite, depois, saber qual parede recebe.
    """
    cfg = cfg or pn.Config()
    flecha_div = FLECHA_PISO if tipo == "piso" else FLECHA_COBERTURA
    # vence a menor dimensao; "horizontal" aqui quer dizer viga paralela a x
    vence_x = reg["w"] <= reg["h"]
    vao = reg["w"] if vence_x else reg["h"]
    corrido = reg["h"] if vence_x else reg["w"]

    escolha, esp = None, ESPACAMENTOS[0]
    for e in ESPACAMENTOS:
        q = (carga_perm + carga_acid) * (e / 1000.0)     # kN/m na viga
        r = dimensionar_viga(vao, q, aco, flecha_div, cfg)
        if r["escolhido"]:
            escolha, esp = r, e
            break
    if escolha is None:
        # ultimo espacamento tentado ja traz o motivo da recusa
        escolha = r
        esp = ESPACAMENTOS[-1]

    pecas, n = [], 0

    def add(familia, perfil, comp, x, y, ao_longo_x, obs=""):
        nonlocal n
        n += 1
        pecas.append(dict(cod=f"{reg['cod']}-{familia[:2].upper()}{n:03d}",
                          familia=familia, perfil=perfil, comp=int(comp),
                          x=int(x), y=int(y), ao_longo_x=bool(ao_longo_x),
                          obs=obs))

    perfil = escolha["escolhido"]["perfil"] if escolha["escolhido"] else "—"
    if escolha["escolhido"]:
        # vigas correntes, do primeiro ao ultimo eixo da modulacao
        pos = 0
        while pos <= corrido:
            p = min(pos, corrido)
            if vence_x:
                add("viga", perfil, vao, reg["x"], reg["y"] + p, True)
            else:
                add("viga", perfil, vao, reg["x"] + p, reg["y"], False)
            pos += esp
        # vigas de borda, perpendiculares: fecham o vigamento e recebem a ponta
        for lado in (0, vao):
            if vence_x:
                add("viga de borda", perfil, corrido, reg["x"] + lado, reg["y"],
                    False, "fecha o vigamento e trava a ponta da viga")
            else:
                add("viga de borda", perfil, corrido, reg["x"], reg["y"] + lado,
                    True, "fecha o vigamento e trava a ponta da viga")
        # travamento a meio vao: viga esbelta gira antes de romper
        if vao > 2_500:
            meio = vao / 2
            if vence_x:
                add("travamento", cfg.perfil_track, corrido, reg["x"] + meio,
                    reg["y"], False, "impede a rotacao da viga a meio vao")
            else:
                add("travamento", cfg.perfil_track, corrido, reg["x"],
                    reg["y"] + meio, True, "impede a rotacao da viga a meio vao")

    return dict(regiao=reg["cod"], nome=reg["nome"], tipo=tipo,
                vao=vao, corrido=corrido, vence_x=vence_x,
                espacamento=esp, perfil=perfil, pecas=pecas,
                dimensionamento=escolha,
                ok=escolha["escolhido"] is not None,
                carga_kn_m2=carga_perm + carga_acid)


def _sob_superior(a, superiores) -> bool:
    """Este comodo do terreo tem pavimento em cima?"""
    for s in superiores:
        if (min(a.x + a.w, s.x + s.w) - max(a.x, s.x) > 300
                and min(a.y + a.h, s.y + s.h) - max(a.y, s.y) > 300):
            return True
    return False


def montar_casa(pj, aco, cfg: pn.Config = None) -> dict:
    """Entrepiso e cobertura da casa inteira, com nivel e direcao de vao.

    Devolve cada peca ja em coordenada do mundo — x, y, comprimento, direcao e
    nivel —, porque a conversao de coordenada e o tipo de coisa que, feita em
    dois lugares, vira duas verdades.
    """
    cfg = cfg or pn.Config()
    planos = []

    # ---- entrepiso: o piso do superior, que e o teto do terreo
    for r in _regioes(pj.SUPERIOR):
        v = vigar_regiao(r, pj.CARGAS["piso_lsf_perm"],
                         pj.CARGAS["piso_lsf_acid"], aco, "piso", cfg)
        v["nivel"] = pj.NIVEL_SUPERIOR - 250      # face inferior do vigamento
        planos.append(v)

    # ---- cobertura: sobre o superior, e sobre o terreo que nao tem superior
    for r in _regioes(pj.SUPERIOR):
        v = vigar_regiao(r, pj.CARGAS["cobertura_perm"],
                         pj.CARGAS["cobertura_acid"], aco, "cobertura", cfg)
        v["nivel"] = pj.NIVEL_SUPERIOR + cfg.altura
        planos.append(v)
    for a in pj.TERREO:
        if _sob_superior(a, pj.SUPERIOR):
            continue
        r = dict(cod=a.cod, nome=a.nome, x=a.x, y=a.y, w=a.w, h=a.h,
                 area=a.area_mod, molhado=a.molhado)
        v = vigar_regiao(r, pj.CARGAS["cobertura_perm"],
                         pj.CARGAS["cobertura_acid"], aco, "cobertura", cfg)
        v["nivel"] = pj.NIVEL_TERREO + cfg.altura
        planos.append(v)

    pecas = [dict(p, plano=v["regiao"], tipo=v["tipo"], nivel=v["nivel"])
             for v in planos for p in v["pecas"]]
    falhas = [v for v in planos if not v["ok"]]
    return dict(planos=planos, pecas=pecas, n=len(pecas),
                falhas=falhas, ok=not falhas,
                por_tipo={t: sum(1 for p in pecas if p["tipo"] == t)
                          for t in {p["tipo"] for p in pecas}},
                perfis=sorted({v["perfil"] for v in planos if v["ok"]}))


# ---------------------------------------------------------------------------
# CONTRAVENTAMENTO — as fitas em X que aparecem em toda obra de LSF
# ---------------------------------------------------------------------------
def contraventar(paineis, pj, aco, cfg: pn.Config = None) -> dict:
    """Escolhe quais paineis recebem fita em X, e confere se dao conta do vento.

    A fita em X nao vai em toda parede: vai onde ha parede cheia o bastante
    para que o triangulo funcione. Painel com abertura no meio nao contraventa,
    e painel muito estreito tem aspecto ruim — a diagonal fica tao proxima da
    vertical que a componente horizontal some.

    A quantidade nao e escolhida por gosto: as fitas escolhidas sao somadas e
    comparadas com a forca global de vento da NBR 6123, direcao por direcao.
    """
    import nucleo.contraventamento as cv
    import nucleo.vento as ve
    cfg = cfg or pn.Config()
    SISTEMA = "fita X 38x0,80 a 45 graus"

    escolhidos, pecas = [], []
    for p in paineis:
        if p.aberturas or p.comp < 1_200 or not p.externa:
            continue
        sw = cv.ShearWall(cod=p.cod, comp=p.comp, altura=p.altura,
                          tipo="fita X")
        cap = cv.capacidade(sw, SISTEMA)
        if cap["vrd"] <= 0:
            continue
        escolhidos.append(dict(painel=p.cod, comp=p.comp, vrd=cap["vrd"],
                               aspecto=round(cap["aspecto"], 2),
                               horizontal=p.horizontal, pav=p.pav))
        # duas diagonais, de canto a canto — e o X que se ve na obra
        for i, sinal in enumerate((+1, -1), 1):
            pecas.append(dict(cod=f"{p.cod}-DG{i:03d}", familia="diagonal",
                              perfil="Fita 38x0,80", painel=p.cod,
                              comp=round((p.comp ** 2 + p.altura ** 2) ** 0.5),
                              sinal=sinal, pav=p.pav))

    # demanda: forca global de vento nas duas direcoes. As dimensoes sao as da
    # EDIFICACAO, nao as do lote — vento nao age sobre terreno vazio, e usar o
    # lote inflaria a area de fachada em mais de duas vezes.
    xs = [a_.x for a_ in pj.TERREO] + [a_.x + a_.w for a_ in pj.TERREO]
    ys = [a_.y for a_ in pj.TERREO] + [a_.y + a_.h for a_ in pj.TERREO]
    a = (max(xs) - min(xs)) / 1000.0
    b = (max(ys) - min(ys)) / 1000.0
    h = (pj.NIVEL_SUPERIOR + cfg.altura) / 1000.0
    demanda = {}
    for nome, (aa, bb) in (("X", (b, a)), ("Y", (a, b))):
        av = ve.AcaoVento(v0=pj.V0_VENTO, categoria=pj.CATEGORIA_VENTO,
                          classe=pj.CLASSE_VENTO, grupo=2, s1=pj.S1_VENTO,
                          a=aa, b=bb, h=h)
        demanda[nome] = abs(av.forca_global())

    cap_por_dir = {
        "X": sum(e["vrd"] for e in escolhidos if e["horizontal"]),
        "Y": sum(e["vrd"] for e in escolhidos if not e["horizontal"]),
    }
    veredito = {d: dict(capacidade=round(cap_por_dir[d], 1),
                        demanda=round(demanda[d], 1),
                        folga=round(cap_por_dir[d] - demanda[d], 1),
                        ok=cap_por_dir[d] >= demanda[d])
                for d in ("X", "Y")}
    return dict(paineis=escolhidos, pecas=pecas, sistema=SISTEMA,
                n=len(pecas), veredito=veredito,
                ok=all(v["ok"] for v in veredito.values()))


def como_pecas(casa: dict, contra: dict, cat_massa: dict, revisao: str,
               escada: dict = None) -> list:
    """Vigamento e contraventamento como pecas de fabrica.

    Sem esta conversao o vigamento seria uma imagem bonita e nada mais: nao
    entraria no plano de corte, nao entraria no BOM, nao entraria na massa e
    nao entraria na montagem. Aco que aparece no 3D e some no orcamento e a
    pior especie de desenho — o que convence sem comprometer.
    """
    import nucleo.peca as pe
    out = []
    for q in casa["pecas"]:
        if q["perfil"] not in cat_massa:
            continue
        out.append(pe.PecaDetalhada(
            cod=q["cod"], familia=q["familia"], perfil=q["perfil"],
            comp=q["comp"], massa=cat_massa[q["perfil"]] * q["comp"] / 1000.0,
            painel=q["plano"], pav=("S" if q["tipo"] == "piso" else "C"),
            x=q["x"], z=q["nivel"], vertical=False, revisao=revisao))
    for q in (escada or {}).get("pecas", []):
        if q["perfil"] not in cat_massa:
            continue
        out.append(pe.PecaDetalhada(
            cod=q["cod"], familia=q["familia"], perfil=q["perfil"],
            comp=q["comp"], massa=cat_massa[q["perfil"]] * q["comp"] / 1000.0,
            painel=q["plano"], pav="E", x=q["x"], z=q["nivel"],
            vertical=False, revisao=revisao))
    for q in contra["pecas"]:
        # a fita nao vem do catalogo de perfis: e chapa cortada em tira, e a
        # massa sai da propria tira (38 mm x 0,80 mm x 7.850 kg/m3)
        massa_m = 38 * 0.80 * 7.85e-6 * 1000
        out.append(pe.PecaDetalhada(
            cod=q["cod"], familia=q["familia"], perfil=q["perfil"],
            comp=q["comp"], massa=massa_m * q["comp"] / 1000.0,
            painel=q["painel"], pav=q["pav"], x=0, z=0, vertical=False,
            revisao=revisao))
    for p in out:
        p.marcacao = p.carga_marcacao()
    return out


# ---------------------------------------------------------------------------
# ANCORAGEM — o que impede a casa de subir
# ---------------------------------------------------------------------------
def ancorar(contra: dict, paineis, cat_massa: dict, pj, cfg: pn.Config = None) -> dict:
    """Chumbador em cada painel contraventado, dimensionado pelo arrancamento.

    O item "fundacao" do checklist trazia `True` literal ate R31. Em estrutura
    leve isso e o oposto de inocuo: o peso proprio de um painel de LSF e da
    ordem de 1 kN/m2, e a succao de vento sobre a cobertura e da mesma ordem.
    Uma casa pesada resiste ao arrancamento por gravidade; uma casa leve sobe.

    O arrancamento vem do TOMBAMENTO do painel contraventado — o momento V.h e
    equilibrado por um binario cujo bracо e o comprimento do painel. Por isso
    painel curto arranca mais: metade do comprimento, dobro da tracao.
    """
    import nucleo.contraventamento as cv
    import nucleo.ligacoes as lg
    cfg = cfg or pn.Config()
    por_cod = {p.cod: p for p in paineis}
    esp_radier = 180.0        # mm, declarado no projeto (PR-06)

    saida, problemas = {}, []
    for e in contra["paineis"]:
        p = por_cod.get(e["painel"])
        if p is None:
            continue
        direcao = "X" if e["horizontal"] else "Y"
        # a forca horizontal deste painel e a fracao da demanda que ele carrega,
        # proporcional a sua capacidade dentro da direcao
        total = sum(x["vrd"] for x in contra["paineis"]
                    if x["horizontal"] == e["horizontal"]) or 1.0
        v = contra["veredito"][direcao]["demanda"] * e["vrd"] / total
        sw = cv.ShearWall(cod=p.cod, comp=p.comp, altura=p.altura,
                          tipo="fita X", peso_permanente=p.massa(cat_massa) * 9.81e-3)
        t = cv.tombamento(sw, v)
        anc = lg.ancoragem(t["uplift"], esp_radier) if t["precisa_holddown"] else None
        if anc and anc["escolhido"] is None:
            problemas.append(f"{p.cod}: {anc['motivo']}")
        saida[p.cod] = dict(
            painel=p.cod, direcao=direcao, v_kn=round(v, 2),
            uplift=round(t["uplift"], 2),
            compressao=round(t["compressao"], 2),
            peso_kn=round(sw.peso_permanente, 2),
            precisa=t["precisa_holddown"],
            chumbador=(anc["escolhido"]["chumbador"] if anc and anc["escolhido"]
                       else ("nao exige hold-down: o peso proprio equilibra"
                             if not t["precisa_holddown"] else "SEM SOLUCAO")),
            motivo=anc["motivo"] if anc else
                   (f"momento estabilizante {t['m_estabilizante']:.1f} kNm "
                    f"supera o de tombamento {t['m_tombamento']:.1f} kNm"))
    com_hd = sum(1 for v in saida.values() if v["precisa"])
    return dict(paineis=saida, n=len(saida), com_holddown=com_hd,
                problemas=problemas, ok=not problemas,
                uplift_max=round(max((v["uplift"] for v in saida.values()),
                                     default=0.0), 2))


# ---------------------------------------------------------------------------
# ESCADA — a estrutura que a geometria nao tinha
# ---------------------------------------------------------------------------
def estruturar_escada(pj, aco, cfg: pn.Config = None) -> dict:
    """Vigas inclinadas e degraus dos lances, dimensionados pela carga real.

    A geometria da escada e dado do modelo desde R06 — lances, patamar, altura
    de espelho e Blondel conferido. O que nao existia era ESTRUTURA: os 18
    degraus apoiavam no ar. A verificacao de completude acusou na primeira
    execucao, e acusou com a frase certa: "nao ha acesso ao pavimento superior".

    A viga de lance e inclinada, e o vao que ela vence e a HIPOTENUSA, nao a
    projecao horizontal. Dimensionar pela projecao subestima o vao em cerca de
    18 % num lance de 30 graus — e o momento, que cresce com o quadrado, em
    39 %.
    """
    cfg = cfg or pn.Config()
    lances = [l for l in pj.escada_lances() if l["sentido"] != "patamar"]
    larg = pj.ESCADA["larg_lance"] / 1000.0
    q = (pj.CARGAS["escada_perm"] + pj.CARGAS["escada_acid"]) * (larg / 2)

    pecas, planos = [], []
    for l in lances:
        horizontal = l["h"]
        subida = l["z_fim"] - l["z_ini"]
        vao = (horizontal ** 2 + subida ** 2) ** 0.5      # hipotenusa
        r = dimensionar_viga(int(vao), q, aco, FLECHA_PISO, cfg)
        perfil = r["escolhido"]["perfil"] if r["escolhido"] else "—"
        planos.append(dict(lance=l["cod"], vao=round(vao), projecao=horizontal,
                           subida=round(subida), inclinacao=round(
                               __import__("math").degrees(
                                   __import__("math").atan2(subida, horizontal)), 1),
                           perfil=perfil, dimensionamento=r,
                           ok=r["escolhido"] is not None))
        if not r["escolhido"]:
            continue
        for lado, dx in (("esq", 0), ("dir", pj.ESCADA["larg_lance"] - 50)):
            pecas.append(dict(cod=f"ESC-{l['cod']}-VG{lado[:1].upper()}",
                              familia="escada", perfil=perfil,
                              comp=int(vao), x=l["x"] + dx, y=l["y"],
                              nivel=int(l["z_ini"]), plano=f"ESC-{l['cod']}",
                              tipo="escada",
                              obs=f"viga de lance {lado}, vence a hipotenusa "
                                  f"de {vao:.0f} mm"))
        for i in range(l["espelhos"]):
            pecas.append(dict(cod=f"ESC-{l['cod']}-DG{i+1:02d}",
                              familia="escada", perfil=cfg.perfil_track,
                              comp=pj.ESCADA["larg_lance"],
                              x=l["x"], y=l["y"] + i * pj.ESCADA["piso"],
                              nivel=int(l["z_ini"] + i * pj.ESCADA["alt_espelho"]),
                              plano=f"ESC-{l['cod']}", tipo="escada",
                              obs=f"degrau {i+1} de {l['espelhos']}"))
    return dict(planos=planos, pecas=pecas, n=len(pecas),
                ok=all(p["ok"] for p in planos),
                carga_kn_m=q)
