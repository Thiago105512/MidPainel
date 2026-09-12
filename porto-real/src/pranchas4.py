"""
Pranchas complementares: auditoria, elevacoes internas, forro, acessibilidade,
paginacao de paineis LSF e estudo de insolacao.
"""
from __future__ import annotations

import math

import projeto as pj
import elementos as el
import especificacao as ep
import auditoria as au
import anotacao as an
from core import P, Canvas, View, TXT, CINZA, PRETO
from pranchas import base, _tabela, _extremos

MAX_PAINEL = 3_600          # limite de manuseio e transporte do painel LSF
ESP_MONTANTE = 600          # espacamento padrao dos montantes


# =========================================================================
# PR-14 — AUDITORIA
# =========================================================================
def auditoria() -> Canvas:
    achados = au.auditar()
    erros = [a for a in achados if a.nivel == "ERRO"]
    aten = [a for a in achados if a.nivel == "ATENCAO"]
    notas = [a for a in achados if a.nivel == "NOTA"]

    cv = base("AUDITORIA DO MODELO", "s/ escala", "14", notas=[
        "Verificacoes rodadas sobre a geometria declarada, nao sobre o desenho.",
        "Se o modelo passa, todas as pranchas passam: leem a mesma fonte.",
        "Reproduzivel por 'python3 auditoria.py'.",
    ])

    # A tabela e GERADA das proprias funcoes de verificacao: nome, o que ela
    # testa (primeira linha da docstring), quantas condicoes emite e quantos
    # achados produziu nesta rodada. Lista escrita a mao envelhece; esta nao.
    import inspect
    met = au.metrica()
    verificacoes = []
    for fn in au.verificacoes():
        src = inspect.getsource(fn)
        doc = (fn.__doc__ or "").strip().split("\n")[0] or "—"
        achs = fn()
        pior = ("ERRO" if any(a.nivel == "ERRO" for a in achs) else
                "ATENCAO" if any(a.nivel == "ATENCAO" for a in achs) else
                f"{len(achs)} nota(s)" if achs else "OK")
        verificacoes.append([fn.__name__.replace("checar_", ""), doc[:92],
                             str(src.count("Achado(")), pior])
    y = _tabela(cv, (35, 44), f"VERIFICACOES AUTOMATICAS — {met['funcoes']} FUNCOES, "
                f"{met['condicoes']} CONDICOES",
                ["VERIFICACAO", "O QUE TESTA", "COND.", "RESULTADO"],
                verificacoes, larguras=[44, 170, 18, 30]) + 18

    cv.texto_p((35, y), f"RESULTADO: {len(erros)} ERRO(S) · {len(aten)} ATENCAO(OES) · "
                        f"{len(notas)} NOTA(S)", TXT["med"], "start", peso="bold",
               cor="#b3261e" if erros else "#0a6a4a")
    y += 10
    for a in erros + aten + notas:
        cor = {"ERRO": "#b3261e", "ATENCAO": "#b26a00", "NOTA": CINZA}[a.nivel]
        cv.texto_p((35, y), f"[{a.nivel}] {a.item}", TXT["min"], "start", peso="bold", cor=cor)
        cv.texto_p((90, y), a.detalhe[:150], TXT["min"], "start")
        y += 6

    _tabela(cv, (35, y + 14), "CORRECOES APLICADAS NESTA REVISAO",
            ["#", "ACHADO", "CORRECAO"],
            [["1", "Porta estar -> core sem parede correspondente",
              "vao removido: os ambientes sao integrados, nao ha parede"],
             ["2", "Suites com vao de janela abaixo de 1/6 da area de permanencia",
              "criada a familia J05 (1.800 x 1.200) para os tres dormitorios"],
             ["3", "Banho compartilhado com 0,36 m2 de vao para 4,32 m2 de piso",
              "criada a familia J04 (800 x 900) alta e basculante"],
             ["4", "Quarto reversivel e oficina marginalmente abaixo do minimo",
              "janela ampliada para J05 em ambos"],
             ["5", "Banho da master no encontro com o hall, bloqueando a porta",
              "banho e closet deslocados para a extremidade norte do modulo"],
             ["6", "57 % da suite master contabilizados como balanco",
              "declarados 4 pilares metalicos: e pilotis com terraco coberto abaixo"],
             ["7", "Circulacao de 10,1 % contra meta de 8 %",
              "metrica separada: halls 4,6 % e core vertical a parte"],
             ["8", "Gourmet sem prumada hidraulica identificada",
              "verificacao passa a considerar o grupo integrado com a cozinha"]],
            larguras=[8, 116, 138])
    return cv


# =========================================================================
# PR-15 — ELEVACOES INTERNAS (vistas de parede)
# =========================================================================
def _elevacao(cv: Canvas, vw: View, larg: int, titulo: str, pecas: list, notas: list):
    """Vista frontal de uma parede interna: largura x pe-direito."""
    h = pj.PE_DIREITO
    cv.poli_p([vw.pt(P(0, 0)), vw.pt(P(larg, 0)), vw.pt(P(larg, h)), vw.pt(P(0, h))],
              "corte", fechado=True, preenche="#fff")
    for x, z, w, dz, rot, cor in pecas:
        cv.poli_p([vw.pt(P(x, z)), vw.pt(P(x + w, z)), vw.pt(P(x + w, z + dz)),
                   vw.pt(P(x, z + dz))], "vista", fechado=True, preenche=cor)
        c = vw.pt(P(x + w / 2, z + dz / 2))
        if w > 500 and dz > 300:
            cv.texto_p(c, rot, TXT["micro"], "middle", cor="#333")
    an.cadeia(cv, vw, [0, larg], 0, "H", 12)
    an.cadeia(cv, vw, [0, 900, 1_400, 2_200, h], 0, "V", -12)
    cv.texto_p(vw.pt(P(larg / 2, -900)), titulo, TXT["peq"], "middle", peso="bold")
    for i, n in enumerate(notas):
        cv.texto_p(vw.pt(P(0, -1_500 - i * 400)), "- " + n, TXT["micro"], "start")


def elevacoes_internas() -> Canvas:
    cv = base("ELEVACOES INTERNAS", "1:25", "15", notas=[
        "Vistas de parede: base para marcenaria, revestimento e pontos eletricos.",
        "Modulos de marcenaria em 300 / 450 / 600 / 900 mm, conforme o briefing.",
        "Bancadas a 900 mm; arios superiores de 1.400 a 2.200 mm.",
        "Alturas de tomada e interruptor a confirmar com o projeto eletrico.",
    ])
    GAB, ARM, ELET = "#e8e8e8", "#f1ede4", "#dfe9f2"

    _elevacao(cv, View(25, 60, 190, 0, 0), 6_000, "COZINHA — PAREDE SUL (BANCADA PRINCIPAL)",
              [(0, 0, 900, 900, "gabinete 900", GAB),
               (900, 0, 900, 900, "cuba 900", GAB),
               (1_800, 0, 600, 900, "600", GAB),
               (2_400, 0, 900, 900, "cooktop 900", GAB),
               (3_300, 0, 600, 900, "600", GAB),
               (3_900, 0, 900, 2_200, "torre forno + micro", ARM),
               (4_800, 0, 900, 2_000, "nicho geladeira", ELET),
               (0, 1_400, 3_900, 800, "aereos 1.400 a 2.200", ARM)],
              ["bancada em granito, 600 mm de profundidade",
               "circulacao livre minima de 1.000 mm (desejada 1.100)",
               "6 tomadas de bancada a 1.150 mm"])

    _elevacao(cv, View(25, 330, 190, 0, 0), 4_200, "GOURMET — BANCADA E CHURRASQUEIRA",
              [(0, 0, 1_200, 900, "apoio 1.200", GAB),
               (1_200, 0, 1_200, 1_200, "churrasqueira", "#ded5cb"),
               (2_400, 0, 900, 900, "cuba 900", GAB),
               (3_300, 0, 900, 900, "frigobar", ELET),
               (0, 1_400, 1_200, 800, "aereo", ARM)],
              ["coifa com vazao minima de 10 trocas por hora do volume",
               "bancada integrada a cozinha pelo vao livre"])

    _elevacao(cv, View(25, 600, 190, 0, 0), 1_800, "BANHO COMPARTILHADO — PAREDE DA BANCADA",
              [(0, 0, 700, 900, "gabinete", GAB),
               (700, 0, 1_100, 900, "bancada", GAB),
               (0, 1_000, 1_800, 900, "espelho 1.800 x 900", "#eef4f7")],
              ["reforco embutido para barra de apoio da NBR 9050",
               "porta de correr de 900 mm libera o circulo de giro"])

    _elevacao(cv, View(25, 60, 480, 0, 0), 2_400, "SUITE MASTER — BANHO",
              [(0, 0, 1_200, 900, "gabinete duplo", GAB),
               (1_200, 0, 1_200, 900, "bancada", GAB),
               (0, 1_000, 2_400, 1_000, "espelho", "#eef4f7")],
              ["revestimento ceramico ate o teto na area molhada"])

    _elevacao(cv, View(25, 330, 480, 0, 0), 3_000, "OFICINA — BANCADA DE TRABALHO",
              [(0, 0, 2_400, 900, "bancada 2.400 x 600", GAB),
               (0, 1_200, 2_400, 1_200, "pegboard 2.400 x 1.200", "#f0e6d2"),
               (2_400, 0, 600, 2_200, "armario alto 600", ARM)],
              ["6 tomadas de bancada; circuito comum 20 A e reserva 32 A (H)",
               "iluminacao geral 500 lux e 800 lux sobre a bancada, 4.000 K",
               "area central livre de 1.200 x 1.800 mm"])

    _elevacao(cv, View(25, 600, 480, 0, 0), 3_000, "LAVANDERIA — TANQUE E MAQUINAS",
              [(0, 0, 600, 900, "tanque", GAB),
               (700, 0, 600, 850, "lavadora", ELET),
               (1_400, 0, 600, 850, "secadora", ELET),
               (0, 1_500, 3_000, 700, "prateleiras", ARM)],
              ["base antivibratoria sob as maquinas: ruido estrutural",
               "prumada na parede do deposito, longe da oficina"])
    return cv


# =========================================================================
# PR-16 — PLANTA DE FORRO E ILUMINACAO (refletida)
# =========================================================================
def forro() -> Canvas:
    cv = base("PLANTA DE FORRO E ILUMINACAO", "1:75", "16", notas=[
        "Planta refletida: vista do forro projetada no plano horizontal.",
        "Forro absorvente apenas no gourmet — unico ponto com reverberacao critica.",
        "Alcapoes tecnicos de 600 x 600 mm; passarela de cobertura de 600 mm.",
        "Iluminacao geral 3.000 K, IRC minimo 90.",
    ])
    vw = View(75, 70, 400, 2_400, 7_200)
    pat_abs = cv.hachura("absorv", espac=1.1, ang=45, w=0.07, cor="#c77")

    trat = {c: (s, j) for c, s, _, j in ep.FORROS}
    for a in pj.TERREO:
        sol = trat.get(a.cod, ("gesso liso", ""))[0]
        absorvente = "absorvente" in sol
        cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                   vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                  "vista", fechado=True,
                  preenche=f"url(#{pat_abs})" if absorvente else "#fafafa", cor="#999")
        c = vw.pt(P(a.cx, a.cy))
        cv.texto_p((c[0], c[1] - 3), a.nome, TXT["micro"], "middle", peso="bold")
        cv.texto_p((c[0], c[1] + 1), sol[:34], TXT["micro"], "middle", cor=CINZA)
        # luminarias: malha proporcional a area
        nx = max(1, int(a.w / 2_400))
        ny = max(1, int(a.h / 2_400))
        for i in range(nx):
            for j in range(ny):
                p = vw.pt(P(a.x + a.w * (i + 0.5) / nx, a.y + a.h * (j + 0.5) / ny))
                cv.circ_p(p, 1.1, "fino", preenche="#ffd", cor="#b90")
    # alcapoes tecnicos
    for x, y, rot in ((9_600, 17_400, "AT-01"), (3_900, 17_400, "AT-02"),
                      (7_500, 24_000, "AT-03")):
        cv.poli_p([vw.pt(P(x, y)), vw.pt(P(x + 600, y)), vw.pt(P(x + 600, y + 600)),
                   vw.pt(P(x, y + 600))], "corte2", fechado=True, preenche="#fff")
        cv.texto_p(vw.pt(P(x + 300, y + 900)), rot, TXT["micro"], "middle", cor="#06c")

    cv.circ_p((470, 60), 1.1, "fino", preenche="#ffd", cor="#b90")
    cv.texto_p((476, 60), "luminaria embutida, 3.000 K, IRC 90", TXT["min"], "start")
    cv.poli_p([(466, 68), (474, 68), (474, 74), (466, 74)], "corte2", fechado=True, preenche="#fff")
    cv.texto_p((478, 71), "alcapao tecnico 600 x 600 mm", TXT["min"], "start")
    cv.poli_p([(466, 80), (474, 80), (474, 86), (466, 86)], "fino", fechado=True,
              preenche=f"url(#{pat_abs})")
    cv.texto_p((478, 83), "forro absorvente (alfa 0,70)", TXT["min"], "start")

    _tabela(cv, (466, 100), "FORROS POR AMBIENTE",
            ["AMBIENTE", "SOLUCAO", "AREA", "POR QUE"],
            [[c, s[:44], f"{a:.2f}", j[:52]] for c, s, a, j in ep.FORROS],
            larguras=[22, 92, 20, 120])
    an.norte(cv, (790, 60), 9, pj.NORTE_EM_PLANTA)
    an.titulo_desenho(cv, (70, 420), "1", "FORRO REFLETIDO — TERREO", "1:75")
    return cv


# =========================================================================
# PR-17 — ACESSIBILIDADE E FLUXOS
# =========================================================================
def acessibilidade() -> Canvas:
    cv = base("ACESSIBILIDADE E FLUXOS", "1:75", "17", notas=[
        "Rota acessivel do passeio ao quarto reversivel e ao banho compartilhado.",
        "Circulo de giro de 1.500 mm verificado nos pontos de manobra.",
        "Porta de correr de 900 mm no banho libera a area de varredura.",
        "Reforcos para barra de apoio embutidos antes do fechamento das placas.",
    ])
    vw = View(75, 70, 400, 2_400, 7_200)

    cores = {"social": "#f6c453", "intimo": "#a29bfe", "servico": "#74b9ff",
             "oficina": "#74b9ff", "circulacao": "#dfe6e9", "apoio": "#b2bec3",
             "molhado": "#dfe6e9"}
    for a in pj.TERREO:
        cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                   vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                  "fino", fechado=True,
                  preenche=cores.get(ep.CATEGORIA.get(a.cod, ""), "#eee"), cor="#fff")
        c = vw.pt(P(a.cx, a.cy))
        cv.texto_p(c, a.nome, TXT["micro"], "middle", cor="#333")

    # rota acessivel: passeio -> varanda -> hall -> banho / reversivel
    rota = [P(9_300, 4_000), P(9_300, 9_600), P(9_300, 12_000),
            P(10_800, 12_000), P(12_600, 12_000)]
    pts = [vw.pt(p) for p in rota]
    cv.poli_p(pts, "corte", cor="#0a6a4a")
    for p in pts:
        cv.circ_p(p, 1.4, "fino", preenche="#0a6a4a", cor="#0a6a4a")
    cv.texto_p((pts[0][0] + 4, pts[0][1] + 4), "ROTA ACESSIVEL", TXT["min"], "start",
               cor="#0a6a4a", peso="bold")

    # circulos de giro de 1.500 mm
    for x, y, rot in ((9_300, 11_400, "giro 1,50 m — hall"),
                      (11_100, 12_000, "giro 1,50 m — banho"),
                      (13_500, 10_200, "giro 1,50 m — quarto")):
        c = vw.pt(P(x, y))
        cv.circ_p(c, vw.d(au.GIRO_PNE / 2), "oculto", cor="#0a6a4a")
        cv.texto_p((c[0], c[1] + vw.d(au.GIRO_PNE / 2) + 3), rot, TXT["micro"],
                   "middle", cor="#0a6a4a")

    # fluxos por zona
    fluxos = [("SERVICO", "#0a6", [P(5_400, 10_200), P(3_900, 13_200), P(3_900, 19_200),
                                   P(3_900, 25_200)]),
              ("SOCIAL", "#c90", [P(9_300, 9_600), P(9_000, 13_200), P(7_500, 19_200),
                                  P(7_500, 26_400)]),
              ("INTIMO", "#63c", [P(9_300, 12_000), P(10_800, 15_600)])]
    for nome, cor, pontos in fluxos:
        pp = [vw.pt(p) for p in pontos]
        cv.poli_p(pp, "eixo", cor=cor)
        cv.texto_p((pp[-1][0] + 3, pp[-1][1]), nome, TXT["micro"], "start", cor=cor, peso="bold")

    _tabela(cv, (466, 44), "VERIFICACAO NBR 9050",
            ["ITEM", "EXIGIDO", "PROJETO", ""],
            [["Vao livre de porta", "800 mm", "840 mm (folha de 900)", "OK"],
             ["Circulo de giro 360 graus", "1.500 mm", "hall, banho e quarto", "OK"],
             ["Desnivel sem rampa", "ate 5 mm", "soleiras niveladas", "OK"],
             ["Largura de circulacao", "900 mm", "1.800 mm no hall", "OK"],
             ["Barra de apoio", "reforco previo", "embutido na PE-1 e PH-1", "OK"],
             ["Bancada acessivel", "altura livre 730 mm", "sem gabinete sob a cuba", "OK"],
             ["Comando e interruptor", "600 a 1.000 mm", "a definir no eletrico", "pendente"]],
            larguras=[54, 34, 60, 18])

    _tabela(cv, (466, 120), "FLUXOS — SEPARACAO DE CIRCUITOS",
            ["CIRCUITO", "PERCURSO", "CRUZA O SOCIAL?"],
            [["Servico", "garagem -> oficina -> lavanderia -> cozinha -> despensa", "NAO"],
             ["Social", "entrada -> hall -> estar -> gourmet -> alpendre -> piscina", "—"],
             ["Intimo terreo", "hall -> banho compartilhado -> quarto reversivel", "NAO"],
             ["Intimo superior", "hall -> core -> hall superior -> suites", "NAO"],
             ["Lixo e carga", "cozinha -> despensa -> recuo sul", "NAO"]],
            larguras=[34, 118, 34])
    an.norte(cv, (790, 60), 9, pj.NORTE_EM_PLANTA)
    an.titulo_desenho(cv, (70, 420), "1", "ROTAS E FLUXOS — TERREO", "1:75")
    return cv


# =========================================================================
# PR-18 — PAGINACAO DE PAINEIS LSF
# =========================================================================
def paineis() -> list[dict]:
    """Divide cada trecho de parede em paineis de ate 3.600 mm."""
    out, n = [], 0
    for pav in ("T", "S"):
        for s in ep.paredes_classificadas(pj.TERREO if pav == "T" else pj.SUPERIOR):
            comp = s["fim"] - s["ini"]
            qtd = math.ceil(comp / MAX_PAINEL)
            largura = comp / qtd
            for i in range(qtd):
                n += 1
                ini = s["ini"] + i * largura
                out.append(dict(cod=f"P{pav}-{n:03d}", pav=pav, familia=s["familia"],
                                ori=s["ori"], fixo=s["fixo"], ini=ini, larg=largura,
                                montantes=int(largura // ESP_MONTANTE) + 1,
                                altura=pj.PE_DIREITO))
    return out


def paginacao_lsf() -> Canvas:
    lst = paineis()
    cv = base("PAGINACAO DE PAINEIS — LIGHT STEEL FRAME", "1:100", "18", notas=[
        f"Paineis limitados a {MAX_PAINEL} mm por manuseio e transporte.",
        f"Montantes a cada {ESP_MONTANTE} mm; 400 mm onde calculo ou revestimento exigir.",
        "Nenhuma peca entra em nesting sem codigo, largura, altura, espessura, material e revisao.",
        "Numeracao por pavimento; a familia define a composicao interna do painel.",
    ])
    vw = View(100, 70, 400, 2_400, 7_200)

    for a in pj.TERREO:
        cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                   vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                  "cota", fechado=True, preenche="#fcfcfc", cor="#eee")
    for p in [q for q in lst if q["pav"] == "T"]:
        e = ep.FAMILIAS[p["familia"]]["esp"]
        cor = ep.CORES_FAM[p["familia"]]
        if p["ori"] == "V":
            x, y, w, h = p["fixo"] - e / 2, p["ini"], e, p["larg"]
        else:
            x, y, w, h = p["ini"], p["fixo"] - e / 2, p["larg"], e
        cv.poli_p([vw.pt(P(x, y)), vw.pt(P(x + w, y)), vw.pt(P(x + w, y + h)),
                   vw.pt(P(x, y + h))], "corte2", fechado=True, preenche=cor, cor=cor)
        c = vw.pt(P(x + w / 2, y + h / 2))
        cv.texto_p(c, p["cod"].split("-")[1], TXT["micro"], "middle", cor="#fff",
                   rot=90 if p["ori"] == "V" else 0)

    por_fam: dict[str, list[int]] = {}
    for p in lst:
        por_fam.setdefault(p["familia"], []).append(p["montantes"])
    linhas = [[f, str(len(v)), str(sum(v)),
               f"{sum(v) * (pj.PE_DIREITO/1000):.1f}",
               ep.FAMILIAS[f]["comp"][:60]] for f, v in sorted(por_fam.items())]
    linhas.append(["TOTAL", str(len(lst)), str(sum(sum(v) for v in por_fam.values())),
                   f"{sum(sum(v) for v in por_fam.values()) * (pj.PE_DIREITO/1000):.1f}", ""])
    _tabela(cv, (466, 44), "QUANTITATIVO DE PAINEIS E MONTANTES",
            ["FAMILIA", "PAINEIS", "MONTANTES", "ml de perfil", "COMPOSICAO"],
            linhas, larguras=[20, 20, 26, 26, 150])

    amostra = [[p["cod"], p["familia"], f"{p['larg']:.0f}", str(p["altura"]),
                str(p["montantes"]), "T" if p["pav"] == "T" else "S"]
               for p in lst[:26]]
    _tabela(cv, (466, 120), "EXTRATO DA LISTA DE PAINEIS (26 de %d)" % len(lst),
            ["CODIGO", "FAMILIA", "LARG (mm)", "ALT (mm)", "MONT.", "PAV"],
            amostra, larguras=[26, 22, 26, 26, 18, 14])
    an.norte(cv, (790, 60), 9, pj.NORTE_EM_PLANTA)
    an.titulo_desenho(cv, (70, 420), "1", "PAGINACAO — TERREO", "1:100")
    return cv


# =========================================================================
# PR-19 — ESTUDO DE INSOLACAO
# =========================================================================
def _sol(dia_juliano: int, hora: float, lat: float = pj.LATITUDE):
    d = math.radians(23.45 * math.sin(math.radians(360 * (284 + dia_juliano) / 365)))
    w = math.radians(15 * (hora - 12))
    f = math.radians(lat)
    sen_alt = math.sin(f) * math.sin(d) + math.cos(f) * math.cos(d) * math.cos(w)
    alt = math.asin(max(-1, min(1, sen_alt)))
    cos_az = (math.sin(d) * math.cos(f) - math.cos(d) * math.sin(f) * math.cos(w)) / \
             max(math.cos(alt), 1e-6)
    az = math.acos(max(-1, min(1, cos_az)))
    if w > 0:
        az = 2 * math.pi - az
    return math.degrees(alt), math.degrees(az)


def insolacao() -> Canvas:
    cv = base("ESTUDO DE INSOLACAO", "s/ escala", "19", notas=[
        f"Latitude {pj.LATITUDE:.2f} graus — o sol passa proximo ao zenite o ano inteiro.",
        "Junho: sol ao NORTE. Dezembro: sol ao SUL. Equinocios: quase vertical.",
        "Leste e oeste recebem sol rasante o ano todo: exigem brise vertical.",
        "Angulos calculados por declinacao e angulo horario, nao tabelados.",
    ])

    # ---- carta solar: altitude x azimute
    ox, oy, R = 230, 250, 150
    cv.circ_p((ox, oy), R, "fino", cor=CINZA)
    for alt in (30, 60):
        r = R * (90 - alt) / 90
        cv.circ_p((ox, oy), r, "cota", cor="#ddd")
        cv.texto_p((ox + r + 4, oy), f"{alt} graus", TXT["micro"], "start", cor=CINZA)
    for az, rot, cor in ((0, "N", "#0a6"), (90, "L", "#c00"),
                         (180, "S", "#0a6"), (270, "O", "#c00")):
        a = math.radians(az)
        cv.linha_p((ox, oy), (ox + R * math.sin(a), oy - R * math.cos(a)), "cota", cor="#ddd")
        cv.texto_p((ox + (R + 9) * math.sin(a), oy - (R + 9) * math.cos(a)),
                   rot, TXT["peq"], "middle", cor=cor, peso="bold")

    for dia, rot, cor in ((172, "21 jun", "#06c"), (80, "equinocio", "#0a6a4a"),
                          (355, "21 dez", "#c60")):
        pts = []
        h = 6.0
        while h <= 18.0:
            alt, az = _sol(dia, h)
            if alt > 0:
                r = R * (90 - alt) / 90
                a = math.radians(az)
                pts.append((ox + r * math.sin(a), oy - r * math.cos(a)))
            h += 0.25
        if pts:
            cv.poli_p(pts, "vista", cor=cor)
            cv.texto_p((pts[len(pts) // 2][0], pts[len(pts) // 2][1] - 4), rot,
                       TXT["micro"], "middle", cor=cor)
    for h in (8, 10, 12, 14, 16):
        alt, az = _sol(80, h)
        if alt > 0:
            r = R * (90 - alt) / 90
            a = math.radians(az)
            p = (ox + r * math.sin(a), oy - r * math.cos(a))
            cv.circ_p(p, 1.6, "fino", preenche="#fff")
            cv.texto_p((p[0], p[1] + 5), f"{h}h", TXT["micro"], "middle", cor=CINZA)
    an.titulo_desenho(cv, (80, 420), "1", "CARTA SOLAR — MANAUS", "s/ escala")

    # ---- tabela de angulos por hora
    linhas = []
    for h in (7, 8, 9, 12, 15, 16, 17):
        a1, z1 = _sol(172, h)
        a2, z2 = _sol(80, h)
        a3, z3 = _sol(355, h)
        if max(a1, a2, a3) <= 0:
            continue
        linhas.append([f"{h}h",
                       f"{a1:.0f} / {z1:.0f}" if a1 > 0 else "—",
                       f"{a2:.0f} / {z2:.0f}" if a2 > 0 else "—",
                       f"{a3:.0f} / {z3:.0f}" if a3 > 0 else "—"])
    y = _tabela(cv, (466, 44), "ALTITUDE / AZIMUTE SOLAR (graus)",
                ["HORA", "21 jun", "equinocio", "21 dez"], linhas,
                larguras=[20, 40, 40, 40]) + 16

    y = _tabela(cv, (466, y), "PROTECAO ADOTADA POR FACHADA",
                ["FACE", "CONDICAO CRITICA", "PROTECAO", "PROJECAO"],
                [["Norte", "21 jun, 12h — 63 graus", "beiral horizontal", "1.200 mm"],
                 ["Sul", "21 dez, 12h — 70 graus", "beiral horizontal", "1.200 mm"],
                 ["Leste", "8h, ano todo — 30 graus", "ripado vertical BR-L", "vertical"],
                 ["Oeste", "16h, ano todo — 30 graus", "ripado vertical BR-O movel", "vertical"]],
                larguras=[20, 56, 48, 30]) + 16

    _tabela(cv, (466, y), "POR QUE BEIRAL NAO RESOLVE LESTE E OESTE",
            ["VAO", "ALTITUDE", "PROJECAO NECESSARIA", "VIAVEL"],
            [[f"{h} mm", "30 graus", f"{h/math.tan(math.radians(30)):.0f} mm", "NAO"]
             for h in (1_200, 2_100, 2_400)] +
            [["2.400 mm", "63 graus (norte)", "1.197 mm", "sim"]],
            larguras=[24, 34, 58, 24])
    return cv
