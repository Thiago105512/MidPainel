"""PISCINA EXECUTIVA — cortes, escada, borda, hidraulica e iluminacao (R78).

Ate R77 a piscina era um retangulo com um dicionario ao lado: PISCINA dizia a
lamina, PISCINA_SISTEMA contava "1 skimmer, 2 drenos, 4 retornos, 3 LEDs" e
a PR-34 punha simbolos em posicoes escolhidas pelo desenho. A PR-10 ainda
dizia "renovacao 3 h, 2 retornos, casa de maquinas 1.500 x 1.200" — tres
numeros que o caso ja nao tinha. Aqui tudo sai do caso, e o desenho so le.

  GEOMETRIA. Nivel da agua 100 mm abaixo da borda (skimmer). Prainha de
  300 mm, escada de praia na largura inteira ligando a prainha ao fundo:
  espelho <= 250 mm e piso >= 300 mm (H, NBR 10339 e pratica), degraus em
  numero inteiro derivado do desnivel. Banco na parede oposta, assento a
  PISCINA.banco_prof abaixo da agua. Casca de 150 mm (externo.piscina),
  lastro de 100 mm, impermeabilizacao por cristalizacao + argamassa
  polimerica (H), revestimento na familia do deck.
  BORDA. Peca de 30 mm com pingadeira, na mesma familia R11 da faixa seca;
  o deck cai 1 % PARA FORA da piscina (H, NBR 10339: o deck nao pode drenar
  para a agua). Perimetro = externo.piscina, para a BOM nao ter dois.
  HIDRAULICA. Q = volume / renovacao. Skimmer a sotavento (vento dominante
  de E/NE em Manaus, H INMET): parede OESTE; retornos na parede LESTE,
  opostos, varrendo a superficie para o skimmer; dois drenos de fundo
  afastados >= 900 mm (antiaprisionamento); aspiracao na parede norte,
  a mais perto da casa de maquinas. Cada linha: DN pela velocidade
  (succao <= 1,8 m/s, retorno <= 2,4 m/s, H NBR 10339), comprimento
  Manhattan ate TC-13 mais a descida, perda por Hazen-Williams (C = 150).
  Filtro: taxa = Q / area <= 36 m3/h/m2 (alta taxa, H); retrolavagem a
  36 m3/h/m2 por 3 min, para o ralo DN75 da casa de maquinas. Bomba: altura
  manometrica = geometrica + perdas + filtro sujo + acessorios; potencia
  eletrica = cv x 736 / rendimento / fator de potencia (H 0,72 e 0,85).
  ILUMINACAO. LEDs na parede LESTE (a mais perto do gourmet, que olha para
  oeste): quem esta na casa ve a agua acesa, nao a lampada. Nicho a 500 mm
  abaixo da agua (H 400-600), SELV 12 V (NBR 5410, zona 0), fonte na casa
  de maquinas, caixa de passagem estanque no deck, secao do cabo pela
  queda <= 5 % a 12 V. Potencia especifica 2 a 4 W/m2 (H).
"""
from __future__ import annotations

import math

from nucleo.esgoto import _manh

# ---------------------------------------------------------------- (H) limites
NIVEL_AGUA = 100            # mm abaixo da borda: skimmer trabalha com essa lamina
DEGRAU_H_MAX = 250          # espelho maximo (H, NBR 10339)
DEGRAU_L_MIN = 300          # piso minimo
V_SUCCAO_MAX = 1.8          # m/s (H, NBR 10339)
V_RETORNO_MAX = 2.4         # m/s (H, NBR 10339)
TAXA_FILTRACAO_MAX = 36.0   # m3/h/m2, filtro de areia de alta taxa (H)
TAXA_RETROLAVAGEM = 36.0    # m3/h/m2 (H)
T_RETROLAVAGEM_MIN = 3      # minutos (H)
RALO_DN75_M3H = 14.0        # capacidade do ralo DN75 a 2 % (H, Manning n = 0,010)
DRENOS_AFAST_MIN = 900      # antiaprisionamento (H, NBR 10339)
SUCCAO_MAX_MM = 10_000      # limite declarado no caso (comentario de CASA_MAQUINAS)
CAIMENTO_DECK = 0.01        # para fora da piscina (H)
LASTRO = 100                # mm de brita sob a laje de fundo (H)
BORDA_ESP = 30              # peca de borda (H)
BORDA_PECA = 600            # comprimento da peca (H)
LED_PROF = 500              # mm abaixo da agua (H 400-600)
LED_LM_W = 85.0             # lm/W de LED subaquatico branco quente (H)
LED_W_M2 = (2.0, 4.0)       # potencia especifica recomendada (H)
LED_V = 12                  # SELV, zona 0 da NBR 5410
QUEDA_LED_MAX = 5.0         # % a 12 V (H)
REND_MOTOR, FP_MOTOR = 0.72, 0.85   # (H) motor monofasico de 0,5 cv
H_FILTRO_SUJO = 8.0         # m.c.a. (H) — limpo ~3 m; dimensiona-se pelo sujo
H_ACESSORIOS = 1.5          # m.c.a. (H) valvula seletora, registros, curvas
C_HW = 150                  # Hazen-Williams, PVC
RHO_CU = 0.0172             # ohm.mm2/m
SECOES = (1.5, 2.5, 4.0, 6.0, 10.0)
# PVC soldavel (diametro interno em mm), o usual em piscina
DI = {25: 21.6, 32: 27.8, 40: 35.2, 50: 46.4, 60: 55.6, 75: 69.4}
VENTO_DOMINANTE = "E/NE (H, normais climatologicas INMET para Manaus)"
IMPERMEABILIZACAO = ("cristalizante no concreto fresco + argamassa polimerica bicomponente em 2 demaos "
                     "(H); teste de estanqueidade de 72 h antes do revestimento")
CONCRETO = "concreto armado fck 30 MPa, casca de 150 mm, tela dupla 8 mm c/ 15 (H)"
# (H) precos
PRECO = {"bomba_vs_un": 2_850.0, "filtro_areia_500_un": 1_850.0, "areia_kg": 2.2,
         "skimmer_un": 180.0, "dreno_antiaprisionamento_un": 220.0, "retorno_un": 45.0,
         "aspiracao_un": 60.0, "tubo_pvc50_m": 28.0, "registro_esfera_50_un": 48.0,
         "led_18w_un": 390.0, "fonte_12v_un": 260.0, "caixa_passagem_un": 35.0,
         "cabo_12v_m": 4.2, "borda_peca_un": 62.0, "impermeab_m2": 58.0}


def _cm(pj):
    return next(t for t in pj.TECNICOS if t.get("casa_maquinas"))


# ================================================================== geometria
def geometria(pj) -> dict:
    p, dk = pj.PISCINA, pj.DECK
    ex = __import__("nucleo.externo", fromlist=["piscina"]).piscina(pj)
    casca = ex["espessura_casca"]
    faixa = dict(sul=p["x"] - dk["x"], norte=(dk["x"] + dk["w"]) - (p["x"] + p["w"]),
                 leste=p["y"] - dk["y"], oeste=(dk["y"] + dk["h"]) - (p["y"] + p["h"]))
    return dict(
        w=p["w"], h=p["h"], x=p["x"], y=p["y"], prainha_w=p["prainha_w"],
        prof_prainha=p["prof_prainha"], prof_principal=p["prof_principal"],
        nivel_agua=-NIVEL_AGUA, lamina_agua_principal=p["prof_principal"] - NIVEL_AGUA,
        banco_w=p["banco_w"], banco_assento=-p["banco_prof"],
        banco_altura=p["prof_principal"] - p["banco_prof"],
        casca=casca, lastro=LASTRO, fundo_escavacao=-(p["prof_principal"] + casca + LASTRO),
        faixa_seca=faixa, faixa_seca_min=p["faixa_seca_min"],
        concreto=CONCRETO, impermeabilizacao=IMPERMEABILIZACAO,
        revestimento_m2=ex["revestimento_m2"], concreto_m3=ex["concreto_m3"],
        perimetro_m=ex["borda_m"], lamina_m2=p["lamina_m2"], volume_m3=p["volume_m3"])


def escada(pj) -> dict:
    """Escada de praia entre a prainha e o fundo, na largura inteira."""
    p = pj.PISCINA
    desnivel = p["prof_principal"] - p["prof_prainha"]
    n = math.ceil(desnivel / DEGRAU_H_MAX)
    espelho = desnivel / n
    degraus = []
    for i in range(n):
        z_topo = -(p["prof_prainha"] + espelho * i)          # cota do piso do degrau i (0 = prainha)
        degraus.append(dict(n=i + 1, x0=p["prainha_w"] + DEGRAU_L_MIN * i, piso=DEGRAU_L_MIN,
                            z=round(z_topo), espelho=round(espelho)))
    return dict(n=n, espelho=round(espelho, 1), piso=DEGRAU_L_MIN, largura=p["h"],
                desnivel=desnivel, avanco=DEGRAU_L_MIN * (n - 1), degraus=degraus,
                x_fim=p["prainha_w"] + DEGRAU_L_MIN * (n - 1),
                obs="faixa antiderrapante de 50 mm em cor contrastante no bordo de cada degrau; "
                    "sem corrimao: a escada tem a largura da piscina e a prainha e o patamar")


def bordas(pj) -> dict:
    g = geometria(pj)
    per_mm = g["perimetro_m"] * 1000
    n = math.ceil(per_mm / BORDA_PECA) + 4          # 4 pecas de canto em L
    return dict(perimetro_m=g["perimetro_m"], peca=f"{BORDA_PECA} x 300 x {BORDA_ESP} mm, porcelanato R11 (borda; o deck e WPC), "
                "bordo boleado e pingadeira", n_pecas=n, espessura=BORDA_ESP,
                caimento_deck=CAIMENTO_DECK, sentido="para fora da piscina",
                transicao="cantoneira de aluminio anodizado 25 x 25 entre o revestimento e a borda; junta de 5 mm "
                          "com selante poliuretano entre a borda e o piso do deck",
                nivel_agua=-NIVEL_AGUA, obs="a peca avanca 30 mm sobre a agua: o pingadeira corta a linha de sujeira "
                                             "e o boleado protege o joelho de quem sai")


# ================================================================== hidraulica
def vazao_m3h(pj) -> float:
    return pj.vazao_recirculacao_m3h()


def pontos(pj) -> list[dict]:
    """Skimmer, drenos, retornos, aspiracao e LEDs com coordenada e parede."""
    p, ps = pj.PISCINA, pj.PISCINA_SISTEMA
    x0, y0, w, h = p["x"], p["y"], p["w"], p["h"]
    pts = []
    # skimmer: parede OESTE (y = y0 + h), a sotavento do vento de E/NE; canto norte, perto de TC-13
    pts.append(dict(cod="SK-1", tipo="skimmer", parede="oeste", x=x0 + w - 450, y=y0 + h, z=-NIVEL_AGUA,
                    linha="succao"))
    # drenos de fundo, no eixo transversal do trecho fundo, afastados entre si
    xf0, xf1 = x0 + p["prainha_w"], x0 + w - p["banco_w"]
    for i in range(ps["drenos_fundo"]):
        pts.append(dict(cod=f"DF-{i + 1}", tipo="dreno de fundo antiaprisionamento", parede="fundo",
                        x=round(xf0 + (xf1 - xf0) * (0.3 + 0.4 * i)), y=y0 + h / 2, z=-p["prof_principal"],
                        linha="succao"))
    # retornos: parede LESTE (y = y0), opostos ao skimmer
    for i in range(ps["retornos"]):
        pts.append(dict(cod=f"RT-{i + 1}", tipo="dispositivo de retorno", parede="leste",
                        x=round(x0 + w * (i + 0.5) / ps["retornos"]), y=y0, z=-NIVEL_AGUA - 300, linha="retorno"))
    # aspiracao: parede NORTE (x = x0 + w), a mais perto da casa de maquinas
    pts.append(dict(cod="AS-1", tipo="tomada de aspiracao", parede="norte", x=x0 + w, y=y0 + h / 2,
                    z=-NIVEL_AGUA - 300, linha="succao"))
    # LEDs: parede LESTE, entre os retornos (1/4, 1/2, 3/4 contra 1/8, 3/8, 5/8, 7/8)
    for i in range(ps["leds"]):
        pts.append(dict(cod=f"LED-{i + 1}", tipo=f"LED {ps['led_w']} W {ps['led_k']}", parede="leste",
                        x=round(x0 + w * (i + 1) / (ps["leds"] + 1)), y=y0, z=-NIVEL_AGUA - LED_PROF, linha="12 V"))
    return pts


def _hf(q_m3h: float, dn: int, comp_mm: float) -> float:
    """Perda de carga (m.c.a.) por Hazen-Williams, PVC."""
    q = q_m3h / 3600.0
    d = DI[dn] / 1000.0
    return 10.67 * (comp_mm / 1000.0) * q ** 1.852 / (C_HW ** 1.852 * d ** 4.87)


def _dn_por_velocidade(q_m3h: float, v_max: float) -> int:
    q = q_m3h / 3600.0
    for dn in sorted(DI):
        if q / (math.pi * (DI[dn] / 2000.0) ** 2) <= v_max:
            return max(dn, 50)          # DN50 e o minimo pratico de piscina (H)
    return max(DI)


def linhas(pj) -> list[dict]:
    """Cada tubulacao entre um ponto e a casa de maquinas: Q, DN, v, L, hf."""
    q = vazao_m3h(pj)
    cm = _cm(pj)
    alvo = (cm["x"], cm["y"] + cm["h"] / 2)
    out = []
    for pt in pontos(pj):
        if pt["linha"] == "12 V":
            continue
        if pt["tipo"] == "skimmer":
            qi, papel = q, "100 % da vazao com os drenos fechados"
        elif pt["tipo"].startswith("dreno"):
            qi, papel = q / 2, "metade da vazao cada, em T (os dois sempre abertos)"
        elif pt["tipo"].startswith("tomada"):
            qi, papel = q, "so na aspiracao manual, com skimmer e drenos fechados"
        else:
            qi, papel = q / pj.PISCINA_SISTEMA["retornos"], "um quarto da vazao"
        v_max = V_RETORNO_MAX if pt["linha"] == "retorno" else V_SUCCAO_MAX
        dn = _dn_por_velocidade(qi, v_max)
        v = (qi / 3600.0) / (math.pi * (DI[dn] / 2000.0) ** 2)
        # descida ate 600 mm abaixo do deck (H: tubo sob a faixa seca), mais a subida na casa
        comp = _manh((pt["x"], pt["y"]), alvo) + abs(pt["z"]) + 600 + 600
        out.append(dict(cod=pt["cod"], tipo=pt["tipo"], linha=pt["linha"], q_m3h=round(qi, 2), dn=dn,
                        v_ms=round(v, 2), v_max=v_max, comp_mm=round(comp), hf_m=round(_hf(qi, dn, comp), 3),
                        papel=papel, ok=v <= v_max))
    return out


def filtro(pj) -> dict:
    ps = pj.PISCINA_SISTEMA
    de = int("".join(ch for ch in ps["filtro"] if ch.isdigit()))       # "areia DE 500 mm" -> 500
    area = math.pi * (de / 2000.0) ** 2
    q = vazao_m3h(pj)
    q_retro = TAXA_RETROLAVAGEM * area
    return dict(tipo=ps["filtro"], de_mm=de, area_m2=round(area, 3), taxa_m3h_m2=round(q / area, 1),
                taxa_max=TAXA_FILTRACAO_MAX, ok=q / area <= TAXA_FILTRACAO_MAX,
                retrolavagem_m3h=round(q_retro, 1), retrolavagem_min=T_RETROLAVAGEM_MIN,
                retrolavagem_m3=round(q_retro * T_RETROLAVAGEM_MIN / 60, 2),
                ralo_m3h=RALO_DN75_M3H, ralo_ok=q_retro <= RALO_DN75_M3H,
                areia_kg=round(area * 0.6 * 1_600),        # leito de 600 mm (H), 1.600 kg/m3
                valvula="seletora de 6 posicoes: filtrar, retrolavar, enxaguar, recircular, drenar, fechado")


def bomba(pj) -> dict:
    ps = pj.PISCINA_SISTEMA
    cv = float(ps["bomba"].split("cv")[0].split()[-1].replace(",", "."))    # "velocidade variavel 0,5 cv"
    q = vazao_m3h(pj)
    ln = linhas(pj)
    hf_suc = max(x["hf_m"] for x in ln if x["linha"] == "succao")
    hf_ret = max(x["hf_m"] for x in ln if x["linha"] == "retorno")
    cm = _cm(pj)
    # geometrica: bomba 200 mm acima do piso da casa, no nivel do deck; agua 100 mm abaixo
    h_geo = (200 + NIVEL_AGUA) / 1000.0
    h_man = h_geo + hf_suc + hf_ret + H_FILTRO_SUJO + H_ACESSORIOS
    p_hid_w = 1000 * 9.81 * (q / 3600.0) * h_man
    p_el_w = cv * 736 / REND_MOTOR
    va = p_el_w / FP_MOTOR
    return dict(descricao=ps["bomba"], cv=cv, q_m3h=q, h_man_m=round(h_man, 2), h_geo_m=h_geo,
                hf_succao_m=round(hf_suc, 3), hf_retorno_m=round(hf_ret, 3),
                p_hidraulica_w=round(p_hid_w), p_eletrica_w=round(p_el_w), va=round(va),
                acima_da_agua=True, cota_eixo=200, casa=cm["cod"],
                pre_filtro="cesto na succao da bomba", comando="inversor da propria bomba: 3 velocidades, "
                "a mais baixa para as 6 h de renovacao; a alta so para retrolavagem e aspiracao")


def succao(pj) -> dict:
    p, cm = pj.PISCINA, _cm(pj)
    dist = cm["x"] - (p["x"] + p["w"])
    return dict(comp_mm=dist, max_mm=SUCCAO_MAX_MM, ok=dist <= SUCCAO_MAX_MM)


def diagrama(pj) -> list[dict]:
    """Os nos do diagrama hidraulico, na ordem do fluxo."""
    ps = pj.PISCINA_SISTEMA
    f, b = filtro(pj), bomba(pj)
    return [
        dict(no="SK-1", nome="skimmer", grupo="succao"),
        dict(no="DF", nome=f"{ps['drenos_fundo']} drenos de fundo em T", grupo="succao"),
        dict(no="AS-1", nome="tomada de aspiracao", grupo="succao"),
        dict(no="RG", nome="3 registros de esfera DN50 (um por linha de succao)", grupo="succao"),
        dict(no="PF", nome="pre-filtro de cesto", grupo="bomba"),
        dict(no="BM", nome=f"bomba {b['descricao']} — {b['q_m3h']} m3/h a {b['h_man_m']} m", grupo="bomba"),
        dict(no="VS", nome=f"valvula seletora — {f['valvula']}", grupo="filtro"),
        dict(no="FL", nome=f"filtro {f['tipo']} — {f['taxa_m3h_m2']} m3/h/m2", grupo="filtro"),
        dict(no="RL", nome=f"retrolavagem -> ralo DN75 da casa ({f['retrolavagem_m3h']} m3/h, {f['retrolavagem_min']} min)",
             grupo="filtro"),
        dict(no="BP", nome="bypass do aquecimento: 2 registros e espaco de trocador (nao instalado)", grupo="retorno"),
        dict(no="RT", nome=f"{ps['retornos']} dispositivos de retorno em anel DN50", grupo="retorno"),
    ]


# ================================================================== iluminacao
def iluminacao(pj) -> dict:
    p, ps = pj.PISCINA, pj.PISCINA_SISTEMA
    cm = _cm(pj)
    leds = []
    for pt in pontos(pj):
        if pt["linha"] != "12 V":
            continue
        # cabo: do nicho ate a caixa de passagem no deck (600 mm) e dela ate a fonte em TC-13
        comp = _manh((pt["x"], pt["y"]), (cm["x"], cm["y"] + cm["h"] / 2)) + abs(pt["z"]) + 600 + 600
        i_a = ps["led_w"] / LED_V
        sec, queda = None, None
        for s in SECOES:
            queda = 2 * RHO_CU * (comp / 1000.0) * i_a / s / LED_V * 100
            if queda <= QUEDA_LED_MAX:
                sec = s
                break
        leds.append(dict(cod=pt["cod"], x=pt["x"], y=pt["y"], z=pt["z"], parede=pt["parede"], w=ps["led_w"],
                         lm=round(ps["led_w"] * LED_LM_W), i_a=round(i_a, 2), cabo_mm=round(comp),
                         secao_mm2=sec, queda_pct=round(queda, 2), ok=queda <= QUEDA_LED_MAX))
    w_total = ps["leds"] * ps["led_w"]
    w_m2 = w_total / p["lamina_m2"]
    return dict(leds=leds, w_total=w_total, w_m2=round(w_m2, 2), faixa_w_m2=LED_W_M2,
                ok_w_m2=LED_W_M2[0] <= w_m2 <= LED_W_M2[1], tensao=LED_V, prof_mm=LED_PROF,
                fonte=f"fonte SELV {LED_V} V, {math.ceil(w_total * 1.25 / 10) * 10} VA, no quadro estanque de {cm['cod']}, "
                      "protegida por DR de 30 mA; comando pela cena 'gourmet' da automacao",
                nicho="nicho de PVC embutido na casca, com caixa de passagem estanque no deck a 600 mm da borda "
                      "(cabo sem emenda entre o LED e a caixa)",
                lado="parede leste: a mais perto do gourmet, que olha para oeste — a lampada fica de costas para quem olha",
                cor=ps["led_k"])


# ================================================================== resumo / conferencia
def circuito_piscina(pj) -> dict | None:
    return next((c for c in pj.CARGAS_ESPECIAIS if "piscina" in c["desc"].lower()), None)


def itens_bom(pj) -> list[dict]:
    """Itens do sistema da piscina para a BOM: o que a lista externa nao tinha."""
    ps, f, b, il, br, g = pj.PISCINA_SISTEMA, filtro(pj), bomba(pj), iluminacao(pj), bordas(pj), geometria(pj)
    ln = linhas(pj)
    tubo = sum(x["comp_mm"] for x in ln) / 1000.0
    return [
        dict(cod="EXT-PISC-BOMBA", desc=f"Piscina: bomba {b['descricao']} com pre-filtro", un="un", qtd=1,
             preco=PRECO["bomba_vs_un"], fonte="PISCINA_SISTEMA.bomba"),
        dict(cod="EXT-PISC-FILTRO", desc=f"Piscina: filtro de {f['tipo']} com valvula seletora", un="un", qtd=1,
             preco=PRECO["filtro_areia_500_un"], fonte="PISCINA_SISTEMA.filtro"),
        dict(cod="EXT-PISC-AREIA", desc="Piscina: areia filtrante (leito de 600 mm)", un="kg", qtd=f["areia_kg"],
             preco=PRECO["areia_kg"], fonte="area do filtro x leito"),
        dict(cod="EXT-PISC-SKIM", desc="Piscina: skimmer de embutir", un="un", qtd=ps["skimmers"],
             preco=PRECO["skimmer_un"], fonte="PISCINA_SISTEMA"),
        dict(cod="EXT-PISC-DRENO", desc="Piscina: dreno de fundo antiaprisionamento", un="un", qtd=ps["drenos_fundo"],
             preco=PRECO["dreno_antiaprisionamento_un"], fonte="PISCINA_SISTEMA"),
        dict(cod="EXT-PISC-RET", desc="Piscina: dispositivo de retorno", un="un", qtd=ps["retornos"],
             preco=PRECO["retorno_un"], fonte="PISCINA_SISTEMA"),
        dict(cod="EXT-PISC-ASP", desc="Piscina: tomada de aspiracao", un="un", qtd=ps["aspiracao"],
             preco=PRECO["aspiracao_un"], fonte="PISCINA_SISTEMA"),
        dict(cod="EXT-PISC-TUBO", desc="Piscina: tubo PVC soldavel DN50 com conexoes", un="m", qtd=round(tubo, 1),
             preco=PRECO["tubo_pvc50_m"], fonte="soma das linhas (piscina.linhas)"),
        dict(cod="EXT-PISC-REG", desc="Piscina: registro de esfera DN50", un="un", qtd=3 + 2,
             preco=PRECO["registro_esfera_50_un"], fonte="3 linhas de succao + 2 do bypass"),
        dict(cod="EXT-PISC-LED", desc=f"Piscina: LED subaquatico {ps['led_w']} W {ps['led_k']}", un="un", qtd=ps["leds"],
             preco=PRECO["led_18w_un"], fonte="PISCINA_SISTEMA.leds"),
        dict(cod="EXT-PISC-FONTE", desc=f"Piscina: fonte SELV {LED_V} V com DR", un="un", qtd=1,
             preco=PRECO["fonte_12v_un"], fonte="iluminacao"),
        dict(cod="EXT-PISC-CXP", desc="Piscina: caixa de passagem estanque no deck", un="un", qtd=len(il["leds"]),
             preco=PRECO["caixa_passagem_un"], fonte="uma por LED"),
        dict(cod="EXT-PISC-CABO", desc="Piscina: cabo 12 V dos LEDs", un="m",
             qtd=round(sum(l["cabo_mm"] for l in il["leds"]) / 1000.0, 1), preco=PRECO["cabo_12v_m"],
             fonte="soma dos cabos (piscina.iluminacao)"),
        dict(cod="EXT-PISC-IMP", desc="Piscina: impermeabilizacao (cristalizante + polimerica)", un="m2",
             qtd=g["revestimento_m2"], preco=PRECO["impermeab_m2"], fonte="area molhada (externo.piscina)"),
    ]


def resumo(pj) -> dict:
    e, f, b, il, br, s = escada(pj), filtro(pj), bomba(pj), iluminacao(pj), bordas(pj), succao(pj)
    ln = linhas(pj)
    return dict(q_m3h=vazao_m3h(pj), degraus=e["n"], espelho=e["espelho"], linhas=len(ln),
                v_max_succao=max(x["v_ms"] for x in ln if x["linha"] == "succao"),
                taxa_filtracao=f["taxa_m3h_m2"], h_man_m=b["h_man_m"], bomba_va=b["va"],
                leds=len(il["leds"]), w_m2=il["w_m2"], pecas_borda=br["n_pecas"], succao_m=s["comp_mm"] / 1000.0,
                tubo_m=round(sum(x["comp_mm"] for x in ln) / 1000.0, 1),
                custo_sistema=round(sum(i["qtd"] * i["preco"] for i in itens_bom(pj)), 2))


def conferir(pj) -> list[tuple[str, str, bool]]:
    out = []
    g, e, f, b, il, s = geometria(pj), escada(pj), filtro(pj), bomba(pj), iluminacao(pj), succao(pj)
    out.append(("escada: espelho", f"{e['n']} degraus de {e['espelho']} mm (max {DEGRAU_H_MAX})", e["espelho"] <= DEGRAU_H_MAX))
    out.append(("escada: piso", f"{e['piso']} mm (min {DEGRAU_L_MIN})", e["piso"] >= DEGRAU_L_MIN))
    out.append(("escada cabe no trecho fundo", f"avanca {e['avanco']} mm; banco comeca a {g['w'] - g['banco_w'] - g['prainha_w']} mm",
                e["avanco"] < g["w"] - g["banco_w"] - g["prainha_w"]))
    for lado, v in g["faixa_seca"].items():
        out.append((f"faixa seca {lado}", f"{v} mm (min {g['faixa_seca_min']})", v >= g["faixa_seca_min"]))
    decl = pj.DECK["faixa_seca"]
    out.append(("faixa seca declarada por lado confere com a geometria",
                "; ".join(f"{k} {decl.get(k)}/{g['faixa_seca'][k]}" for k in g["faixa_seca"]),
                all(decl.get(k) == g["faixa_seca"][k] for k in g["faixa_seca"])))
    for x in linhas(pj):
        out.append((f"velocidade {x['cod']}", f"{x['v_ms']} m/s em DN{x['dn']} (max {x['v_max']})", x["ok"]))
    dr = [p for p in pontos(pj) if p["tipo"].startswith("dreno")]
    if len(dr) >= 2:
        d = min(_manh((a["x"], a["y"]), (c["x"], c["y"])) for a in dr for c in dr if a is not c)
        out.append(("drenos afastados (antiaprisionamento)", f"{d:.0f} mm (min {DRENOS_AFAST_MIN})", d >= DRENOS_AFAST_MIN))
    sk = next(p for p in pontos(pj) if p["tipo"] == "skimmer")
    rt = {p["parede"] for p in pontos(pj) if p["tipo"].startswith("dispositivo")}
    opostos = {"leste": "oeste", "oeste": "leste", "norte": "sul", "sul": "norte"}
    out.append(("retornos opostos ao skimmer", f"skimmer {sk['parede']}, retornos {sorted(rt)}", rt == {opostos[sk["parede"]]}))
    out.append(("taxa de filtracao", f"{f['taxa_m3h_m2']} m3/h/m2 (max {f['taxa_max']})", f["ok"]))
    out.append(("retrolavagem cabe no ralo DN75", f"{f['retrolavagem_m3h']} m3/h contra {f['ralo_m3h']}", f["ralo_ok"]))
    out.append(("succao", f"{s['comp_mm'] / 1000:.1f} m (max {s['max_mm'] / 1000:.0f})", s["ok"]))
    out.append(("bomba acima da lamina d'agua", f"eixo a +{b['cota_eixo']} mm, agua a {-NIVEL_AGUA} mm", b["acima_da_agua"]))
    out.append(("bomba vence a altura manometrica", f"{b['h_man_m']} m com filtro sujo; hidraulica {b['p_hidraulica_w']} W "
                f"contra {b['p_eletrica_w']} W eletricos", b["p_hidraulica_w"] < b["p_eletrica_w"] * 0.5))
    c = circuito_piscina(pj)
    va_nec = b["va"] + math.ceil(il["w_total"] * 1.25 / 10) * 10
    out.append(("circuito da piscina cobre bomba e LEDs", f"{c['cod'] if c else '?'} {c['va'] if c else 0} VA contra "
                f"{va_nec} VA (bomba {b['va']} + fonte dos LEDs)", bool(c) and c["va"] >= va_nec))
    out.append(("potencia de luz por m2", f"{il['w_m2']} W/m2 (faixa {LED_W_M2[0]}-{LED_W_M2[1]})", il["ok_w_m2"]))
    for l in il["leds"]:
        out.append((f"queda a 12 V {l['cod']}", f"{l['queda_pct']} % em {l['secao_mm2']} mm2 x {l['cabo_mm'] / 1000:.1f} m", l["ok"]))
    out.append(("LEDs na parede voltada para a casa", f"parede {set(l['parede'] for l in il['leds'])}",
                all(l["parede"] == "leste" for l in il["leds"])))
    ex = __import__("nucleo.externo", fromlist=["piscina"]).piscina(pj)
    out.append(("perimetro da borda = o da BOM", f"{bordas(pj)['perimetro_m']} m / {ex['borda_m']} m",
                abs(bordas(pj)["perimetro_m"] - ex["borda_m"]) < 0.01))
    return out
