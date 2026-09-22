"""R71 — LOTE 2 DO BACKLOG: MARCENARIA (itens 124 a 145 da matriz).

Tudo o que esta aqui sai de nucleo/marcenaria, que deriva cada movel do caso
(ARMARIOS, BANCADAS, LOUCAS, LAYOUT, SUBDIVISOES). Nenhum modulo e digitado
nesta prancha: se um guarda-roupa mudar de largura, as cinco pranchas mudam.

  55  PLANTA DE MARCENARIA — os dois pavimentos com cada movel hachurado e
      codificado, e o quadro de moveis (124, 125, 137)
  56  DETALHAMENTO I — cozinha, gourmet, oficina, lavabo e banhos: gabinetes
      sob granito e suspensos, com a secao do apoio (126, 129, 130, 140)
  57  DETALHAMENTO II — dormitorios: roupeiros, closet, gaveteiro, cabeceiras,
      paineis de TV, rack e mesa de trabalho (127, 128, 131, 132, 135, 136,
      138, 139)
  58  PLANO DE CORTE E FURACAO — chapas nestadas e o sistema 32 (141, 142)
  59  FERRAGENS, PUXADORES E LISTA DE PECAS (143, 144, 145)
"""
from __future__ import annotations

import projeto as pj
import anotacao as an
import elementos as el
import nucleo.marcenaria as mc
from core import P, Canvas, View, TXT, CINZA, PRETO
from pranchas import base, _tabela, _desenhar_subdivisoes

COR = {"armario alto": "#e9dcc4", "guarda-roupa": "#e3d5c0", "rouparia": "#e3d5c0",
       "prateleiras": "#f1e9d8", "gaveteiro": "#d9cbb3", "closet": "#e3d5c0",
       "gabinete": "#d4dde6", "gabinete banho": "#c9d7e3", "rack": "#dcd0bd",
       "mesa": "#dcd0bd", "painel tv": "#b98a5a", "cabeceira": "#cbb9a6"}
PORTA, GAVETA, PRAT, CAIXA = "#f7f2ea", "#efe7da", "#c9b79c", "#a08c70"


def _mm(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".")


# =========================================================================
# PR-55 — PLANTA DE MARCENARIA
# =========================================================================
def planta_marcenaria() -> Canvas:
    cv = base("PLANTA DE MARCENARIA — TERREO E SUPERIOR", "1:75", "55", notas=[
        "Cada movel vem de nucleo/marcenaria: ARMARIOS, gabinete de cada BANCADA de granito, "
        "gabinete suspenso de cada lavatorio, rack, painel de TV e mesa do LAYOUT, cabeceira "
        "de cada cama e as duas paredes do CLOSET.",
        f"Modulo maximo {mc.PORTA_MAX} mm (folha de porta); alturas por familia (H).",
        "Frente e a dimensao ao longo da parede; profundidade e a outra. Elevacoes nas PR-56 e 57.",
        "Puxador por categoria de ambiente: gola de aluminio grafite nas areas sociais e de "
        "servico, cava a 45 graus nos dormitorios.",
    ])
    mv = mc.moveis(pj)
    pat = cv.hachura("marc", espac=1.0, ang=45, w=0.10, cor="#8a6d3b")

    def pavimento(pav, vw, titulo, num):
        fech = pj.TERREO if pav == "T" else pj.SUPERIOR
        for a in fech:
            with cv.escopo("ambiente", a.cod, rot=a.nome):
                cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)), vw.pt(P(a.x + a.w, a.y + a.h)),
                           vw.pt(P(a.x, a.y + a.h))], "fino", fechado=True, preenche="#fbfaf7", cor="#999")
                c = vw.pt(P(a.cx, a.cy))
                cv.texto_p((c[0], c[1] + 1.2), a.cod, TXT["micro"], "middle", cor="#aaa")
        paredes = el.derivar_paredes(fech)
        el.desenhar_paredes(cv, vw, paredes, list(el.vaos_do_pavimento(pav)))
        _desenhar_subdivisoes(cv, vw, pav)
        for m in mv:
            if m["amb"][0] != pav:
                continue
            with cv.escopo("marcenaria", m["cod"], amb=m["amb"], familia=m["familia"],
                           frente=str(m["frente"]), modulos=str(m["n_modulos"])):
                x, y, w, h = m["x"], m["y"], m["w"], m["h"]
                if m["familia"] in ("cabeceira", "painel tv"):
                    # peca de parede: desenha como faixa fina na frente declarada
                    if m["familia"] == "cabeceira":
                        lado = pj_layout_lado(m)
                        x, y, w, h = lado
                    else:
                        h = h if h > 60 else 60
                cv.poli_p([vw.pt(P(x, y)), vw.pt(P(x + w, y)), vw.pt(P(x + w, y + h)), vw.pt(P(x, y + h))],
                          "vista", fechado=True, preenche=f"url(#{pat})", cor="#8a6d3b")
                c = vw.pt(P(x + w / 2, y + h / 2))
                rot = 90 if h > w * 1.5 else 0
                cv.texto_p(c, m["cod"], TXT["micro"], "middle", peso="bold", cor="#5a4630", rot=rot)
        an.titulo_desenho(cv, (vw.ox, 500), num, titulo, "1:75")

    pavimento("T", View(75, 40, 470, pj.RECUO_ESQ, pj.RECUO_FRENTE), "TERREO — MARCENARIA", "1")
    pavimento("S", View(75, 260, 470, pj.RECUO_ESQ, pj.RECUO_FRENTE), "SUPERIOR — MARCENARIA", "2")

    # quadro de moveis
    linhas = [[m["cod"], m["amb"], m["familia"][:14], _mm(m["frente"]), _mm(m["prof"]), _mm(m["alt"]),
               str(m["n_modulos"]), str(m["n_portas"]), str(m["n_gavetas"]), f"{m['area_frente_m2']:.2f}"]
              for m in mv]
    y = _tabela(cv, (480, 40), "QUADRO DE MOVEIS — TUDO O QUE E MARCENARIA NA CASA",
                ["COD", "AMB", "FAMILIA", "FRENTE", "PROF", "ALT", "MOD", "PORTAS", "GAV", "m2 FR"],
                linhas, larguras=[24, 18, 34, 18, 14, 14, 12, 16, 12, 16], h_lin=4.4)
    r = mc.resumo(pj)
    tot = [["moveis", str(r["moveis"])], ["modulos", str(r["modulos"])], ["pecas", str(r["pecas"])],
           ["portas / gavetas", f"{r['portas']} / {r['gavetas']}"],
           ["frente total", f"{r['frente_m2']:.2f} m2"],
           ["chapas 15 / 6 mm", f"{r['chapas'][15]['n']} / {r['chapas'][6]['n']}"]]
    _tabela(cv, (480, y + 8), "TOTAIS", ["", ""], tot, larguras=[60, 60], h_lin=4.4)
    return cv


def pj_layout_lado(m: dict) -> tuple:
    """Faixa da cabeceira: o lado da cama para onde o caso aponta, com a folga."""
    cama = next(it for it in pj.LAYOUT if it["cod"] == m["cod"][:-2])
    lado = cama.get("cabeceira", "+X")
    f = mc.CABECEIRA_FOLGA
    if lado == "+X":
        return (cama["x"] + cama["w"], cama["y"] - f, 60, cama["h"] + 2 * f)
    if lado == "-X":
        return (cama["x"] - 60, cama["y"] - f, 60, cama["h"] + 2 * f)
    if lado == "+Y":
        return (cama["x"] - f, cama["y"] + cama["h"], cama["w"] + 2 * f, 60)
    return (cama["x"] - f, cama["y"] - 60, cama["w"] + 2 * f, 60)


# =========================================================================
# elevacao de um movel, derivada dos modulos
# =========================================================================
def _elevacao_movel(cv, vw, m: dict, num: str, titulo: str, secao: bool = False):
    fam = mc.FAMILIAS[m["familia"]]
    A, Pf = m["alt"], m["prof"]
    z0 = 0
    if m["familia"] == "gabinete":
        z0 = mc.RODAPE_GABINETE
    if m["familia"] == "gabinete banho":
        z0 = 850 - A                          # topo a 850: cuba de apoio a 900
    if m["familia"] == "painel tv":
        z0 = 450                              # sobre o rack
    if m["familia"] == "cabeceira":
        z0 = 300                              # do estrado para cima
    x = 0.0
    with cv.escopo("marcenaria", m["cod"], amb=m["amb"], familia=m["familia"]):
        for mod in m["modulos"]:
            L = mod["larg"]
            pts = [vw.pt(P(x, z0)), vw.pt(P(x + L, z0)), vw.pt(P(x + L, z0 + A)), vw.pt(P(x, z0 + A))]
            cv.poli_p(pts, "corte", fechado=True, preenche=CAIXA if m["familia"] == "painel tv" else "#fff")
            pecas = mod["pecas"]
            if m["familia"] == "painel tv":
                n = int(L // mc.RIPA["passo"])
                for k in range(n):
                    rx = x + 20 + k * mc.RIPA["passo"]
                    cv.poli_p([vw.pt(P(rx, z0)), vw.pt(P(rx + mc.RIPA["larg"], z0)),
                               vw.pt(P(rx + mc.RIPA["larg"], z0 + A)), vw.pt(P(rx, z0 + A))],
                              "fino", fechado=True, preenche="#c9a37a", cor="#8a6d3b")
                x += L
                continue
            if m["familia"] == "cabeceira":
                cv.poli_p(pts, "corte", fechado=True, preenche="#e8dccb")
                for k in range(1, 4):
                    cv.linha_p(vw.pt(P(x, z0 + A * k / 4)), vw.pt(P(x + L, z0 + A * k / 4)), "fino", cor="#b8a890")
                cv.texto_p(vw.pt(P(x + L / 2, z0 + A / 2)), "estofado", TXT["micro"], "middle", cor="#7a6a55")
                x += L
                continue
            if m["familia"] == "mesa":
                # tampo, paineis laterais e o gaveteiro de 450
                cv.poli_p([vw.pt(P(x, z0 + A - mc.ESP_TAMPO)), vw.pt(P(x + L, z0 + A - mc.ESP_TAMPO)),
                           vw.pt(P(x + L, z0 + A)), vw.pt(P(x, z0 + A))], "corte", fechado=True, preenche=CAIXA)
                for px_ in (x, x + L - mc.ESP):
                    cv.poli_p([vw.pt(P(px_, z0)), vw.pt(P(px_ + mc.ESP, z0)), vw.pt(P(px_ + mc.ESP, z0 + A - mc.ESP_TAMPO)),
                               vw.pt(P(px_, z0 + A - mc.ESP_TAMPO))], "corte", fechado=True, preenche=CAIXA)
                zg = z0 + A - mc.ESP_TAMPO
                for g in range(fam["gavetas"]):
                    zg -= mc.GAVETA_ALT + 4
                    cv.poli_p([vw.pt(P(x + L - mc.ESP - 450, zg)), vw.pt(P(x + L - mc.ESP, zg)),
                               vw.pt(P(x + L - mc.ESP, zg + mc.GAVETA_ALT)), vw.pt(P(x + L - mc.ESP - 450, zg + mc.GAVETA_ALT))],
                              "fino", fechado=True, preenche=GAVETA, cor="#777")
                x += L
                continue
            # caixa: laterais
            for px_ in (x, x + L - mc.ESP):
                cv.poli_p([vw.pt(P(px_, z0)), vw.pt(P(px_ + mc.ESP, z0)), vw.pt(P(px_ + mc.ESP, z0 + A)), vw.pt(P(px_, z0 + A))],
                          "fino", fechado=True, preenche=CAIXA, cor=CAIXA)
            # prateleiras (tracejadas: atras da porta) e cabideiro
            n_prat = sum(p["qtd"] for p in pecas if p["nome"] == "PRAT")
            if n_prat:
                passo = (A - 2 * mc.ESP) / (n_prat + 1)
                for k in range(1, n_prat + 1):
                    z = z0 + mc.ESP + k * passo
                    cv.linha_p(vw.pt(P(x + mc.ESP, z)), vw.pt(P(x + L - mc.ESP, z)), "fino",
                               cor=PRAT, dash="2 1" if fam["portas"] else None)
            if fam["cabideiro"]:
                z = z0 + A - 400
                cv.linha_p(vw.pt(P(x + mc.ESP, z)), vw.pt(P(x + L - mc.ESP, z)), "fino", cor="#555", dash="1 1")
                cv.linha_p(vw.pt(P(x + mc.ESP, z0 + A - mc.ESP - 300)), vw.pt(P(x + L - mc.ESP, z0 + A - mc.ESP - 300)),
                           "fino", cor=PRAT, dash="2 1" if fam["portas"] else None)
            # gavetas
            n_gav = fam["gavetas"]
            so_gav = n_gav and not fam["portas"] and not fam["cabideiro"]
            zg = z0 + mc.ESP
            for g in range(n_gav):
                ag = (A - 2 * mc.ESP) / n_gav - 4 if so_gav else mc.GAVETA_ALT
                cv.poli_p([vw.pt(P(x + 2, zg)), vw.pt(P(x + L - 2, zg)), vw.pt(P(x + L - 2, zg + ag)), vw.pt(P(x + 2, zg + ag))],
                          "fino", fechado=True, preenche=GAVETA if so_gav else "none", cor="#777",
                          )
                if not so_gav:
                    cv.linha_p(vw.pt(P(x + 2, zg)), vw.pt(P(x + L - 2, zg + ag)), "fino", cor="#bbb", dash="1 1")
                zg += ag + 4
            # porta: folha com o sentido de abertura
            if fam["portas"]:
                cv.poli_p([vw.pt(P(x + 2, z0 + 2)), vw.pt(P(x + L - 2, z0 + 2)), vw.pt(P(x + L - 2, z0 + A - 2)), vw.pt(P(x + 2, z0 + A - 2))],
                          "vista", fechado=True, preenche=PORTA, cor="#666")
                lado = mod["n"] % 2                   # portas em pares, abrindo para fora
                pa, pb = (x + 2, x + L - 2) if lado else (x + L - 2, x + 2)
                cv.linha_p(vw.pt(P(pa, z0 + 2)), vw.pt(P(pb, z0 + A / 2)), "fino", cor="#bbb")
                cv.linha_p(vw.pt(P(pa, z0 + A - 2)), vw.pt(P(pb, z0 + A / 2)), "fino", cor="#bbb")
            x += L
        # gabinete: rodape recuado e tampo de granito
        if m["familia"] == "gabinete":
            cv.poli_p([vw.pt(P(mc.RECUO_RODAPE, 0)), vw.pt(P(m["frente"] - mc.RECUO_RODAPE, 0)),
                       vw.pt(P(m["frente"] - mc.RECUO_RODAPE, z0)), vw.pt(P(mc.RECUO_RODAPE, z0))],
                      "fino", fechado=True, preenche="#ddd", cor="#999")
            cv.poli_p([vw.pt(P(-20, z0 + A)), vw.pt(P(m["frente"] + 20, z0 + A)),
                       vw.pt(P(m["frente"] + 20, z0 + A + mc.TAMPO_GRANITO)), vw.pt(P(-20, z0 + A + mc.TAMPO_GRANITO))],
                      "corte", fechado=True, preenche="#d8d3c8")
        if m["familia"] == "gabinete banho":
            cv.poli_p([vw.pt(P(-20, z0 + A)), vw.pt(P(m["frente"] + 20, z0 + A)),
                       vw.pt(P(m["frente"] + 20, z0 + A + 20)), vw.pt(P(-20, z0 + A + 20))],
                      "corte", fechado=True, preenche="#d8d3c8")
    an.cadeia(cv, vw, [0] + [sum(mm["larg"] for mm in m["modulos"][:k + 1]) for k in range(m["n_modulos"])], z0, "H", 8)
    topo = z0 + A + (mc.TAMPO_GRANITO if m["familia"] == "gabinete" else 0)
    an.cadeia(cv, vw, sorted({0, z0, topo}), m["frente"], "V", 8)
    an.titulo_desenho(cv, (vw.ox, vw.oy + 22), num, titulo, f"1:{int(vw.escala)}")
    cv.texto_p((vw.ox, vw.oy + 26), f"{m['n_modulos']} mod · {m['n_portas']} portas · {m['n_gavetas']} gav · "
               f"{m['n_pecas']} pecas · {m['puxador'][:28]}", TXT["micro"], "start", cor=CINZA)


def _secao_gabinete(cv, ox, oy):
    """Corte 1:10 do apoio: sapata, rodape recuado, caixa, tampo de granito."""
    vw = View(10, ox, oy, 0, 0)
    Pf, A, z0 = 580, mc.FAMILIAS["gabinete"]["alt"], mc.RODAPE_GABINETE

    def ret(x, z, w, h, cor, rot=None, estilo="corte"):
        cv.poli_p([vw.pt(P(x, z)), vw.pt(P(x + w, z)), vw.pt(P(x + w, z + h)), vw.pt(P(x, z + h))],
                  estilo, fechado=True, preenche=cor)
        if rot:
            cv.texto_p(vw.pt(P(x + w / 2, z + h / 2)), rot, TXT["micro"], "middle")
    ret(-150, -30, 900, 30, "#cfcac1", "piso")
    ret(Pf, 0, 150, 1_300, "#f7f5f0", "parede", "fino")
    ret(mc.RECUO_RODAPE, 0, Pf - mc.RECUO_RODAPE, z0, "#ddd", "rodape recuado 50")
    ret(0, z0, Pf, mc.ESP, CAIXA)                                   # base
    ret(Pf - mc.ESP - 8, z0, mc.ESP, A, CAIXA)                       # fundo/lateral
    ret(0, z0 + A - mc.ESP, Pf, mc.ESP, CAIXA)                       # topo
    ret(0, z0, mc.ESP, A, PORTA, "porta 15")                          # porta
    ret(mc.ESP + 10, z0 + A / 2, Pf - 60, mc.ESP, PRAT, "prateleira")
    ret(-20, z0 + A, Pf + 40, mc.TAMPO_GRANITO, "#d8d3c8", "granito 30")
    ret(-20, z0 + A + mc.TAMPO_GRANITO, 20, -60, "#d8d3c8")           # saia
    for z, rot in ((0, "+0"), (z0, f"+{z0}"), (z0 + A, f"+{z0 + A}"), (z0 + A + mc.TAMPO_GRANITO, f"+{z0 + A + mc.TAMPO_GRANITO} = topo")):
        p = vw.pt(P(Pf + 200, z))
        cv.linha_p(vw.pt(P(-200, z)), p, "cota", cor="#999", dash="2 2")
        cv.texto_p((p[0] + 2, p[1]), rot, TXT["micro"], "start", cor="#666")
    an.titulo_desenho(cv, (ox - 20, oy + 28), "A", "SECAO DO GABINETE SOB GRANITO — APOIO E RODAPE", "1:10")


# =========================================================================
# PR-56 — DETALHAMENTO I: cozinha, gourmet, oficina, lavabo e banhos
# =========================================================================
def detalhamento_1() -> Canvas:
    cv = base("MARCENARIA I — GABINETES DE COZINHA, GOURMET, OFICINA E BANHOS", "1:40 · 1:10", "56", notas=[
        "Gabinete sob granito: caixa de MDF 15 mm sobre sapatas, rodape recuado 50 mm, tampo "
        f"a {mc.BANCADA_ACABADA} mm. Modulo com cuba sem prateleira; modulo do cooktop com uma.",
        "Gabinete de lavatorio suspenso a 350 mm do piso, uma gaveta por modulo, cuba de apoio.",
        "Porta por modulo, dobradicas pela altura (2 ate 900, 3 ate 1.500, 4 ate 2.000, 5 acima).",
        "Prateleira tracejada e atras de porta. Puxador: perfil gola grafite nas areas sociais.",
    ])
    mv = {m["cod"]: m for m in mc.moveis(pj)}
    ordem = [c for c in ("BC-01-G", "BC-02-G", "BC-04-G", "BC-03-G", "BC-06-G", "AR-08", "AR-06", "AR-03",
                         "LC-02-G", "LC-15-G", "LC-05-G", "LC-11-G") if c in mv]
    pos = [(30, 110), (170, 110), (300, 110), (30, 200), (170, 200), (300, 200), (30, 330), (170, 330),
           (440, 110), (530, 110), (440, 200), (530, 200)]
    for i, cod in enumerate(ordem):
        m = mv[cod]
        ox, oy = pos[i]
        _elevacao_movel(cv, View(40, ox, oy, 0, 0), m, str(i + 1),
                        m["nome"].upper().replace("GABINETE SUSPENSO DO LAVATORIO", "GAB. LAVATORIO")[:34])
    _secao_gabinete(cv, 560, 440)
    return cv


# =========================================================================
# PR-57 — DETALHAMENTO II: dormitorios
# =========================================================================
def detalhamento_2() -> Canvas:
    cv = base("MARCENARIA II — ROUPEIROS, CLOSET, GAVETEIRO, CABECEIRAS E PAINEIS", "1:40", "57", notas=[
        "Guarda-roupa: por modulo, cabideiro a 400 mm do topo, prateleira sobre ele e duas "
        "gavetas internas de 200 mm; porta inteira.",
        "Closet: os mesmos modulos sem porta, nas duas paredes declaradas em SUBDIVISOES.",
        "Cabeceira estofada: lado da cama mais 300 mm de cada lado, 1.200 mm de altura, "
        "sobre painel de MDF 15 mm fixado na parede.",
        "Painel de TV ripado na largura do rack: ripas de 40 x 40 a cada 80 sobre fundo de 15 mm; "
        "cabo passa entre as ripas.",
        "Mesa de trabalho da alcova: tampo engrossado (2 x 15 mm), paineis laterais e gaveteiro de 450.",
    ])
    mv = {m["cod"]: m for m in mc.moveis(pj)}
    ordem = [c for c in ("AR-12", "AR-13", "AR-11", "AR-09", "CL-S-MAS-A", "CL-S-MAS-B",
                         "AR-14", "LY-12-C", "LY-10-C", "LY-15-M", "LY-03-P", "LY-04-M", "LY-13-M", "AR-04")
             if c in mv]
    pos = [(30, 130), (120, 130), (210, 130), (300, 130), (440, 130), (560, 130),
           (30, 270), (110, 270), (220, 270), (330, 270), (440, 270), (300, 420),
           (30, 420), (150, 420)]
    for i, cod in enumerate(ordem):
        m = mv[cod]
        ox, oy = pos[i]
        _elevacao_movel(cv, View(40, ox, oy, 0, 0), m, str(i + 1), m["nome"].upper()[:40])
    # secao 1:10 do modulo de guarda-roupa
    vw = View(10, 560, 440, 0, 0)
    m = mv.get("AR-12") or next(iter(mv.values()))
    A, Pf = m["alt"], m["prof"]

    def ret(x, z, w, h, cor, rot=None, estilo="corte"):
        cv.poli_p([vw.pt(P(x, z)), vw.pt(P(x + w, z)), vw.pt(P(x + w, z + h)), vw.pt(P(x, z + h))],
                  estilo, fechado=True, preenche=cor)
        if rot:
            cv.texto_p(vw.pt(P(x + w / 2, z + h / 2)), rot, TXT["micro"], "middle")
    ret(-150, -30, 900, 30, "#cfcac1", "piso")
    ret(Pf, 0, 150, A + 300, "#f7f5f0", "parede", "fino")
    ret(0, 0, Pf, mc.ESP, CAIXA)
    ret(0, A - mc.ESP, Pf, mc.ESP, CAIXA)
    ret(Pf - 8 - mc.ESP_FUNDO, mc.ESP, mc.ESP_FUNDO, A - 2 * mc.ESP, "#e8dccb")
    ret(0, 0, mc.ESP, A, PORTA, "porta")
    ret(mc.ESP + 5, A - mc.ESP - 300, Pf - 40, mc.ESP, PRAT, "prateleira")
    cv.circ_p(vw.pt(P(Pf / 2, A - 400)), 1.5, "vista")
    cv.texto_p(vw.pt(P(Pf / 2 + 60, A - 400)), "cabideiro oval 30x15", TXT["micro"], "start")
    zg = mc.ESP
    for g in range(2):
        ret(mc.ESP + 5, zg, Pf - 80, mc.GAVETA_ALT, GAVETA, "gaveta 200")
        zg += mc.GAVETA_ALT + 4
    an.cadeia(cv, vw, [0, mc.ESP, A - mc.ESP - 300, A - mc.ESP, A], Pf + 150, "V", 8)
    an.cadeia(cv, vw, [0, Pf], 0, "H", 8)
    an.titulo_desenho(cv, (540, 468), "A", "SECAO DO MODULO DE GUARDA-ROUPA — 600 x 2.200", "1:10")
    return cv


# =========================================================================
# PR-58 — PLANO DE CORTE E FURACAO
# =========================================================================
def plano_de_corte() -> Canvas:
    n = mc.nesting(pj)
    r15, r6 = n.get(15), n.get(6)
    cv = base("MARCENARIA — PLANO DE CORTE DE CHAPAS E FURACAO SISTEMA 32", "1:25 · 1:10", "58", notas=[
        f"Chapa MDF {int(mc.CHAPA['alt'])} x {int(mc.CHAPA['larg'])} mm; serra {mc.SERRA:.0f} mm; corte "
        "guilhotinado em faixas pelo mesmo nesting das placas de fechamento (nucleo/nesting).",
        f"15 mm: {r15['pecas']} pecas em {r15['n']} chapas, {r15['aproveitamento'] * 100:.0f} % de aproveitamento. "
        f"6 mm (fundos): {r6['pecas']} pecas em {r6['n']} chapas, {r6['aproveitamento'] * 100:.0f} %.",
        "As primeiras 12 chapas de 15 mm estao desenhadas; as demais seguem a mesma lista "
        "(engenharia.json e a lista de pecas da PR-59).",
        f"Sistema 32: fileiras a {mc.SISTEMA_32['recuo']} mm das bordas, furos de {mc.SISTEMA_32['furo']} mm "
        f"x {mc.SISTEMA_32['profundidade']} a cada {mc.SISTEMA_32['passo']} mm; caneco de {mc.SISTEMA_32['cup']} mm "
        f"a {mc.SISTEMA_32['cup_recuo']} mm da borda.",
    ])
    esc = 25
    W, H = mc.CHAPA["larg"] / esc, mc.CHAPA["alt"] / esc      # chapa em pe, como o nesting a le: 74 x 110 mm
    for i, ch in enumerate(r15["chapas"][:12]):
        ox = 30 + (i % 6) * (W + 6)
        oy = 36 + (i // 6) * (H + 12)
        with cv.escopo("chapa", ch["cod"], esp="15"):
            cv.poli_p([(ox, oy), (ox + W, oy), (ox + W, oy + H), (ox, oy + H)], "corte", fechado=True, preenche="#f4efe4")
            y = oy
            for fx in ch["faixas"]:
                x = ox
                fh = fx["alt"] / esc
                for cod, w, h, rot in fx["pecas"]:
                    pw = w / esc
                    cv.poli_p([(x, y), (x + pw, y), (x + pw, y + fh), (x, y + fh)], "fino", fechado=True,
                              preenche="#e3d5c0" if not rot else "#d4c5ad", cor="#8a6d3b")
                    if pw > 9 and fh > 4:
                        cv.texto_p((x + pw / 2, y + fh / 2 + 0.8), cod.split("#")[0][-12:], 1.6, "middle", cor="#5a4630")
                    x += pw + mc.SERRA / esc
                y += fh + mc.SERRA / esc
            usado = sum(w * h for fx in ch["faixas"] for _, w, h, _ in fx["pecas"])
            cv.texto_p((ox, oy + H + 4), f"{ch['cod']} — {sum(len(fx['pecas']) for fx in ch['faixas'])} pecas, "
                       f"{usado / (mc.CHAPA['larg'] * mc.CHAPA['alt']) * 100:.0f} %", TXT["micro"], "start", cor="#444")
    # tabela: chapas
    linhas = [[ch["cod"], str(sum(len(fx["pecas"]) for fx in ch["faixas"])),
               f"{sum(w * h for fx in ch['faixas'] for _, w, h, _ in fx['pecas']) / (mc.CHAPA['larg'] * mc.CHAPA['alt']) * 100:.0f} %"]
              for ch in r15["chapas"]]
    _tabela(cv, (30, 300), f"CHAPAS DE 15 mm — {r15['n']} CHAPAS", ["CHAPA", "PECAS", "APROV."],
            linhas[:40], larguras=[20, 16, 18], h_lin=3.6)
    _tabela(cv, (95, 300), "", ["CHAPA", "PECAS", "APROV."], linhas[40:80], larguras=[20, 16, 18], h_lin=3.6)
    linhas6 = [[ch["cod"], str(sum(len(fx["pecas"]) for fx in ch["faixas"])),
                f"{sum(w * h for fx in ch['faixas'] for _, w, h, _ in fx['pecas']) / (mc.CHAPA['larg'] * mc.CHAPA['alt']) * 100:.0f} %"]
               for ch in r6["chapas"]]
    _tabela(cv, (160, 300), f"CHAPAS DE 6 mm — {r6['n']}", ["CHAPA", "PECAS", "APROV."], linhas6[:40],
            larguras=[20, 16, 18], h_lin=3.6)
    # furacao: lateral tipica 1:10
    ox, oy = 250, 540
    vw = View(10, ox, oy, 0, 0)
    Pf, A = 600, 2_200
    s = mc.SISTEMA_32
    with cv.escopo("furacao", "LAT-600x2200", sistema="32"):
        cv.poli_p([vw.pt(P(0, 0)), vw.pt(P(Pf, 0)), vw.pt(P(Pf, A)), vw.pt(P(0, A))], "corte", fechado=True, preenche="#f4efe4")
        for xr in (s["recuo"], Pf - s["recuo"]):
            z = s["primeiro"]
            while z <= A - s["primeiro"]:
                cv.circ_p(vw.pt(P(xr, z)), 0.25, "fino")
                z += s["passo"]
            cv.linha_p(vw.pt(P(xr, 0)), vw.pt(P(xr, A)), "cota", cor="#bbb", dash="1 1")
        # canecos da porta de 2.200: 5 dobradicas
        n_dob = mc._n_dobradicas(A)
        for k in range(n_dob):
            z = s["cup_borda"] + k * (A - 2 * s["cup_borda"]) / (n_dob - 1)
            cv.circ_p(vw.pt(P(s["cup_recuo"], z)), s["cup"] / 2 / 10, "vista")
        an.cadeia(cv, vw, [0, s["recuo"], Pf - s["recuo"], Pf], A, "H", -8)
        an.cadeia(cv, vw, [0, s["primeiro"], s["primeiro"] + s["passo"], s["primeiro"] + 2 * s["passo"]], Pf, "V", 8)
    cv.texto_p((ox + 70, oy - 200), f"{2 * (int((A - 2 * s['primeiro']) // s['passo']) + 1)} furos de {s['furo']} mm "
               f"por lateral; {n_dob} canecos de {s['cup']} mm na porta", TXT["micro"], "start", cor="#444")
    an.titulo_desenho(cv, (ox - 10, oy + 30), "A", "LATERAL TIPICA 600 x 2.200 — FURACAO SISTEMA 32 E CANECOS", "1:10")
    # tabela de furacao
    fu = mc.furacao(pj)
    linhas = [[f["peca"][:16], f["tipo"][:22], f"{f['broca']:.0f}", str(f["n"]), f["posicao"][:70]] for f in fu]
    _tabela(cv, (400, 300), f"FURACAO POR PECA — {len(fu)} LINHAS (as primeiras)", ["PECA", "TIPO", "BROCA", "N", "POSICAO"],
            linhas[:50], larguras=[30, 40, 12, 10, 130], h_lin=3.6)
    return cv


# =========================================================================
# PR-59 — FERRAGENS, PUXADORES E LISTA DE PECAS
# =========================================================================
def ferragens_e_pecas() -> Canvas:
    cv = base("MARCENARIA — FERRAGENS, PUXADORES E LISTA DE PECAS", "s/ escala", "59", notas=[
        "Dobradica de caneco 35 mm com amortecedor; corredica telescopica no maior comprimento "
        "comercial que cabe na profundidade menos 100 mm; suporte de prateleira 5 mm; sapata "
        "niveladora; cabideiro oval 30 x 15.",
        "Puxador por categoria de ambiente (H): gola de aluminio grafite (a mesma cor da fachada) "
        "nas areas sociais e de servico; cava usinada a 45 graus nos dormitorios, sem ferragem.",
        "Lista de pecas: as 120 primeiras linhas; a lista inteira esta em engenharia.json e na "
        "vista Marcenaria do visualizador.",
        "Material pelo plano contra o servico sob medida do BOM: a razao tem de ficar entre 20 e 60 %.",
    ])
    f = mc.ferragens(pj)
    corr = ", ".join(f"{n} de {c} mm" for c, n in sorted(f["corredicas_por_comprimento"].items()))
    linhas = [["Dobradica caneco 35 mm", str(f["dobradicas"]), "un"],
              ["Corredica telescopica (par)", f"{f['corredicas_par']}  ({corr})", "par"],
              ["Perfil gola aluminio grafite", f"{f['gola_m']:.1f}", "m"],
              ["Puxadores (portas + gavetas)", str(f["puxadores"]), "un"],
              ["Suporte de prateleira", str(f["suportes"]), "un"],
              ["Sapata niveladora", str(f["sapatas"]), "un"],
              ["Cabideiro oval 30 x 15", f"{f['cabideiro_m']:.1f}", "m"],
              ["Ripa 40 x 40 (paineis de TV)", f"{f['ripas_m']:.1f}", "m"],
              ["Espuma + tecido (cabeceiras)", f"{f['espuma_m2']:.2f}", "m2"]]
    y = _tabela(cv, (30, 40), "FERRAGENS — TOTAIS DERIVADOS", ["ITEM", "QTD", "UN"], linhas,
                larguras=[70, 60, 12], h_lin=4.6)
    px = mc.puxadores(pj)
    linhas = [[p["movel"], p["amb"], p["categoria"], p["tipo"][:36], str(p["qtd"]), f"{p['gola_m']:.1f}"] for p in px]
    y = _tabela(cv, (30, y + 8), "MAPA DE PUXADORES — POR MOVEL", ["MOVEL", "AMB", "CATEG.", "PUXADOR", "QTD", "GOLA m"],
                linhas, larguras=[24, 18, 20, 66, 12, 16], h_lin=4.2)
    c = mc.custo_material(pj)
    linhas = [[l["item"], f"{l['qtd']:.1f}" if isinstance(l["qtd"], float) else str(l["qtd"]),
               f"{l['unit']:.2f}", f"{l['total']:,.2f}"] for l in c["linhas"]]
    linhas.append(["MATERIAL", "", "", f"{c['material']:,.2f}"])
    linhas.append(["servico sob medida (BOM MAR-*)", "", "", f"{c['servico_bom']:,.2f}"])
    linhas.append(["razao material / servico", "", "", f"{c['razao'] * 100:.0f} %"])
    _tabela(cv, (30, y + 8), "MATERIAL PELO PLANO x SERVICO DO BOM (H: precos)", ["ITEM", "QTD", "UNIT R$", "TOTAL R$"],
            linhas, larguras=[70, 24, 22, 30], h_lin=4.2)
    # lista de pecas
    pc = mc.pecas(pj)
    linhas = [[p["cod"][:20], p["nome"][:12], _mm(p["larg"]), _mm(p["alt"]), str(p["esp"]), str(p["qtd"]), f"{p['fita_m']:.1f}"]
              for p in pc]
    col = ["COD", "PECA", "LARG", "ALT", "ESP", "QTD", "FITA m"]
    lg = [34, 22, 12, 12, 8, 8, 12]
    _tabela(cv, (215, 40), f"LISTA DE PECAS — {len(pc)} LINHAS, {sum(p['qtd'] for p in pc)} PECAS", col, linhas[:118], larguras=lg, h_lin=3.6)
    _tabela(cv, (330, 40), "", col, linhas[118:236], larguras=lg, h_lin=3.6)
    _tabela(cv, (445, 40), "", col, linhas[236:354], larguras=lg, h_lin=3.6)
    _tabela(cv, (560, 40), "", col, linhas[354:472], larguras=lg, h_lin=3.6)
    return cv
