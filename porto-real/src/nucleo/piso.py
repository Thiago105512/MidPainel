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


def como_pecas(casa: dict, contra: dict, cat_massa: dict, revisao: str) -> list:
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
