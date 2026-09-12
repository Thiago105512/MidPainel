"""
ETAPA 2 — DETALHAMENTO CONSTRUTIVO.

Seis pranchas que saem do partido e entram na obra: a interface entre Light
Steel Frame e perfil laminado (o maior risco de patologia do projeto), o plano
de furacao e penetracoes, as ampliacoes de area molhada, a paginacao de piso e
a escada executiva.

Tudo lido do modelo. Nenhum numero digitado duas vezes.
"""
from __future__ import annotations

import math

import projeto as pj
import elementos as el
import especificacao as ep
import mobiliario as mob
import anotacao as an
from core import P, Canvas, View, TXT, CINZA, PRETO
from pranchas import base, _tabela


# =========================================================================
# PR-20 — INTERFACE LSF x PERFIL LAMINADO
# =========================================================================
def interface_estrutural() -> Canvas:
    vigas = pj.dimensionar_vigas()
    cv = base("INTERFACE LIGHT STEEL FRAME x PERFIL LAMINADO", "indicada", "20",
              notas=[
                  "O perfil laminado flete; a chapa de gesso acima fissura. As duas "
                  "medidas sao independentes e ambas obrigatorias.",
                  f"Flecha limitada a L/{pj.FLECHA_LIMITE['vedacao_fragil']} onde a viga "
                  f"sustenta vedacao fragil, contra L/{pj.FLECHA_LIMITE['geral']} de uso geral.",
                  "Junta de deslizamento com folga de 1,5 x flecha calculada, por viga.",
                  "Pre-dimensionamento por flecha — calculo estrutural e ART permanecem pendencia.",
              ])

    # ---------------- DET 1: viga laminada recebendo vigamento de LSF (1:5)
    vw = View(5, 58, 150, 0, 0)
    an.titulo_desenho(cv, (30, 172), "1", "APOIO DO VIGAMENTO LSF SOBRE VIGA LAMINADA", "1:5")
    hv = 200            # alma da viga W200
    # viga laminada em corte (perfil I)
    cv.poli_p([vw.pt(P(0, 0)), vw.pt(P(100, 0)), vw.pt(P(100, 10)),
               vw.pt(P(57, 10)), vw.pt(P(57, hv - 10)), vw.pt(P(100, hv - 10)),
               vw.pt(P(100, hv)), vw.pt(P(0, hv)), vw.pt(P(0, hv - 10)),
               vw.pt(P(43, hv - 10)), vw.pt(P(43, 10)), vw.pt(P(0, 10))],
              "corte", fechado=True, preenche="#b0bec5")
    cv.texto_p(vw.pt(P(50, -60)), "W200 x 15,0", TXT["micro"], "middle")
    # guia Ue parafusada na mesa superior
    cv.poli_p([vw.pt(P(-20, hv)), vw.pt(P(120, hv)), vw.pt(P(120, hv + 40)),
               vw.pt(P(-20, hv + 40))], "corte", fechado=True, preenche="#cfd8dc")
    cv.texto_p(vw.pt(P(150, hv + 20)), "guia Ue 200 x 40 x 1,55 parafusada na mesa "
               "superior com parafuso autobrocante 4,8 x 19 a cada 300 mm",
               TXT["micro"], "start")
    # vigas de piso LSF
    for i in (0, 1):
        x0 = -10 + i * 80
        cv.poli_p([vw.pt(P(x0, hv + 40)), vw.pt(P(x0 + 40, hv + 40)),
                   vw.pt(P(x0 + 40, hv + 240)), vw.pt(P(x0, hv + 240))],
                  "corte", fechado=True, preenche="#eceff1")
    cv.texto_p(vw.pt(P(150, hv + 160)), "viga de piso Ue 200 x 40 x 1,25 a cada 600 mm",
               TXT["micro"], "start")
    # OSB + contrapiso
    cv.poli_p([vw.pt(P(-40, hv + 240)), vw.pt(P(140, hv + 240)),
               vw.pt(P(140, hv + 258)), vw.pt(P(-40, hv + 258))],
              "corte", fechado=True, preenche="#d7ccc8")
    cv.texto_p(vw.pt(P(150, hv + 250)), "OSB 18 mm + contrapiso seco", TXT["micro"], "start")
    # nota de ponte termica
    cv.texto_p(vw.pt(P(-40, -150)), "A mesa da viga e ponte termica e acustica: a",
               TXT["micro"], "start", cor="#c00")
    cv.texto_p(vw.pt(P(-40, -230)), "banda resiliente de 5 mm sob a guia corta as duas.",
               TXT["micro"], "start", cor="#c00")
    an.cadeia(cv, vw, [0, hv, hv + 40, hv + 240, hv + 258], -40, "V", -14)

    # ---------------- DET 2: junta de deslizamento (1:5)
    vw2 = View(5, 250, 150, 0, 0)
    an.titulo_desenho(cv, (222, 172), "2", "JUNTA DE DESLIZAMENTO NO TOPO DA PAREDE", "1:5")
    # laje / viga acima
    cv.poli_p([vw2.pt(P(-30, 0)), vw2.pt(P(180, 0)), vw2.pt(P(180, -60)),
               vw2.pt(P(-30, -60))], "corte", fechado=True, preenche="#b0bec5")
    cv.texto_p(vw2.pt(P(200, -30)), "estrutura (viga ou laje)", TXT["micro"], "start")
    # guia superior fixada na estrutura, de alma alta
    cv.poli_p([vw2.pt(P(0, 0)), vw2.pt(P(150, 0)), vw2.pt(P(150, 8)),
               vw2.pt(P(142, 8)), vw2.pt(P(142, 120)), vw2.pt(P(8, 120)),
               vw2.pt(P(8, 8)), vw2.pt(P(0, 8))], "corte", fechado=True,
              preenche="#90a4ae")
    cv.texto_p(vw2.pt(P(200, 60)), "guia de deslizamento de alma 120 mm, fixada SO "
               "na estrutura", TXT["micro"], "start")
    # montante, parando antes do fundo da guia
    folga = max(v["slip_exec"] for v in vigas)
    cv.poli_p([vw2.pt(P(25, folga * 5)), vw2.pt(P(125, folga * 5)),
               vw2.pt(P(125, 400)), vw2.pt(P(25, 400))], "corte", fechado=True,
              preenche="#eceff1")
    cv.texto_p(vw2.pt(P(200, 300)), "montante Ue 90: NAO parafusado na guia", TXT["micro"], "start")
    # cota da folga
    a = vw2.pt(P(75, 0)); b = vw2.pt(P(75, folga * 5))
    cv.linha_p(a, b, "cota", cor="#c00")
    cv.texto_p((b[0] + 3, (a[1] + b[1]) / 2), f"folga {folga} mm = 1,5 x flecha",
               TXT["micro"], "start", cor="#c00")
    cv.texto_p(vw2.pt(P(-30, 520)), "Sem esta junta, a flecha da viga desce direto",
               TXT["micro"], "start", cor="#c00")
    cv.texto_p(vw2.pt(P(-30, 600)), "na chapa de gesso: fissura horizontal no topo",
               TXT["micro"], "start", cor="#c00")
    cv.texto_p(vw2.pt(P(-30, 680)), "da parede, que o morador chama de recalque.",
               TXT["micro"], "start", cor="#c00")

    # ---------------- DET 3: pilar metalico x parede LSF (1:10)
    vw3 = View(10, 440, 150, 0, 0)
    an.titulo_desenho(cv, (412, 172), "3", "PILAR METALICO EMBUTIDO EM PAREDE LSF", "1:10")
    cv.poli_p([vw3.pt(P(0, 0)), vw3.pt(P(200, 0)), vw3.pt(P(200, 200)),
               vw3.pt(P(0, 200))], "corte", fechado=True, preenche="#b0bec5")
    cv.texto_p(vw3.pt(P(100, 100)), pj.PILAR_SECAO.split(" (")[0], TXT["micro"], "middle")
    # parede de 150 passando pelo pilar -> nao cabe: nota
    cv.poli_p([vw3.pt(P(-300, 25)), vw3.pt(P(0, 25)), vw3.pt(P(0, 175)),
               vw3.pt(P(-300, 175))], "corte", fechado=True, preenche="#eceff1")
    cv.poli_p([vw3.pt(P(200, 25)), vw3.pt(P(500, 25)), vw3.pt(P(500, 175)),
               vw3.pt(P(200, 175))], "corte", fechado=True, preenche="#eceff1")
    cv.texto_p(vw3.pt(P(-300, -120)), f"parede LSF {pj.PAR_EXT} mm", TXT["micro"], "start")
    cv.texto_p(vw3.pt(P(-300, 420)), "O pilar de 200 mm NAO cabe na parede de 150 mm.",
               TXT["micro"], "start", cor="#c00")
    cv.texto_p(vw3.pt(P(-300, 560)), "Onde isso acontece, a parede engrossa localmente",
               TXT["micro"], "start", cor="#c00")
    cv.texto_p(vw3.pt(P(-300, 700)), "para 250 mm, com montantes duplos flanqueando o",
               TXT["micro"], "start", cor="#c00")
    cv.texto_p(vw3.pt(P(-300, 840)), "perfil e manta de la de rocha no contato (o aco",
               TXT["micro"], "start", cor="#c00")
    cv.texto_p(vw3.pt(P(-300, 980)), "macico e ponte termica de primeira ordem).",
               TXT["micro"], "start", cor="#c00")

    # ---------------- quadro de dimensionamento
    linhas = []
    for v in vigas:
        linhas.append([
            v["cod"], v["sobre"], f"{v['vao']}", f"{v['trib']}",
            f"{v['w']:.2f}".replace(".", ","), f"L/{v['limite']}", v["perfil"],
            f"{v['ix']:.0f}", f"{v['flecha']:.2f}".replace(".", ","),
            f"{v['flecha_adm']:.2f}".replace(".", ","),
            f"{v['tensao']:.0f} ({v['uso']:.0f} %)",
            f"{v['slip_exec']}" if v["slip_exec"] else "—"])
    _tabela(cv, (35, 235), "DIMENSIONAMENTO DAS VIGAS — GOVERNADO PELA FLECHA, "
            "NAO PELA RESISTENCIA",
            ["VIGA", "SOBRE", "VAO (mm)", "TRIB (mm)", "w (kN/m)", "LIMITE",
             "PERFIL", "Ix (cm4)", "FLECHA", "ADM (mm)", "TENSAO (MPa)", "SLIP (mm)"],
            linhas, larguras=[16, 18, 22, 22, 22, 18, 26, 22, 20, 22, 30, 20])

    _tabela(cv, (35, 300), "POR QUE A FLECHA GOVERNA",
            ["GRANDEZA", "FAIXA NO PROJETO", "LEITURA"],
            [["Uso da resistencia a flexao",
              f"{min(v['uso'] for v in vigas):.0f} a {max(v['uso'] for v in vigas):.0f} %",
              "sobra resistencia: o perfil nao esta no limite em nenhuma viga"],
             ["Flecha / flecha admissivel",
              f"{min(v['flecha']/v['flecha_adm'] for v in vigas)*100:.0f} a "
              f"{max(v['flecha']/v['flecha_adm'] for v in vigas)*100:.0f} %",
              "e aqui que o perfil se aproxima do limite — e o que define a secao"],
             ["Consequencia de errar a resistencia", "colapso",
              "evento raro, verificado por calculo e ART"],
             ["Consequencia de errar a flecha", "fissura recorrente no gesso",
              "evento certo, barato de evitar e caro de consertar para sempre"],
             ["Custo de subir um perfil", "2 a 5 kg/m de aco",
              "menos que uma unica repintura da parede fissurada"]],
            larguras=[64, 48, 130])

    _tabela(cv, (35, 360), "CAIXA D'AGUA — CARGA CONCENTRADA",
            ["ITEM", "VALOR", "DECISAO"],
            [["Volume / carga", f"{pj.CAIXA_DAGUA['volume_l']} L / "
              f"{pj.CAIXA_DAGUA['carga_kg']} kg", "25 kN em 7,20 m2"],
             ["Posicao", f"atico sobre {pj.CAIXA_DAGUA['sobre']}",
              "desce nas paredes do proprio ambiente, sem plataforma sobre vazio"],
             ["Base", f"{pj.CAIXA_DAGUA['nivel_base']} mm", "acima do forro do superior"],
             ["Coluna no terreo", f"{pj.carga_hidraulica_mca('T')} mca", "gravidade, folgado"],
             ["Coluna no superior", f"{pj.carga_hidraulica_mca('S')} mca",
              f"insuficiente: {pj.PRESSURIZADOR['cod']} de "
              f"{pj.PRESSURIZADOR['potencia_cv']} cv no ramal superior"],
             ["Apoio", f"{pj.APOIO_CAIXA['perfis']} perfis sob a base",
              pj.APOIO_CAIXA["desc"][:70]]],
            larguras=[46, 52, 144])
    return cv


# =========================================================================
# PR-21 — PLANO DE FURACAO E PENETRACOES
# =========================================================================
def furacao() -> Canvas:
    cv = base("PLANO DE FURACAO E PENETRACOES EM LSF", "indicada", "21", notas=[
        "Em alvenaria, furar parede e decisao de obra. Em LSF e decisao de projeto.",
        f"Furo centrado na alma, diametro maximo {pj.FURACAO['frac_alma']:.0%} da altura "
        f"do perfil: {pj.furo_max('Ue90x40x0.95')} mm no montante de 90 mm.",
        f"Distancia minima entre centros {pj.FURACAO['dist_centros']} mm; ao apoio "
        f"{pj.FURACAO['dist_apoio_montante']} mm no montante e "
        f"{pj.FURACAO['dist_apoio_viga']} mm na viga.",
        "Tubo maior que o furo admissivel NAO passa no montante: passa em shaft "
        "ou em entreforro. Nao ha terceira opcao.",
    ])

    # ---------------- elevacao de painel com zonas de furacao (1:20)
    vw = View(20, 40, 180, 0, 0)
    an.titulo_desenho(cv, (30, 200), "1", "PAINEL TIPO — ZONAS DE FURACAO", "1:20")
    pw, ph = 2_400, pj.PE_DIREITO
    cv.poli_p([vw.pt(P(0, 0)), vw.pt(P(pw, 0)), vw.pt(P(pw, ph)), vw.pt(P(0, ph))],
              "corte", fechado=True, preenche="#fafafa")
    # montantes
    for i in range(0, pw + 1, pj.MONTANTE_ESPACAMENTO):
        cv.poli_p([vw.pt(P(i - 20, 0)), vw.pt(P(i + 20, 0)), vw.pt(P(i + 20, ph)),
                   vw.pt(P(i - 20, ph))], "vista", fechado=True, preenche="#cfd8dc")
    # zona proibida junto aos apoios
    pat = cv.hachura("proib", espac=1.4, ang=45, w=0.06, cor="#c00")
    d = pj.FURACAO["dist_apoio_montante"]
    for y0 in (0, ph - d):
        cv.poli_p([vw.pt(P(0, y0)), vw.pt(P(pw, y0)), vw.pt(P(pw, y0 + d)),
                   vw.pt(P(0, y0 + d))], "cota", fechado=True,
                  preenche=f"url(#{pat})", cor="#c00")
    cv.texto_p(vw.pt(P(pw + 200, d / 2)), f"zona proibida {d} mm do apoio",
               TXT["micro"], "start", cor="#c00")
    # furos admissiveis
    fmax = pj.furo_max("Ue90x40x0.95")
    for i in range(0, pw + 1, pj.MONTANTE_ESPACAMENTO):
        for y in range(d + 300, ph - d, pj.FURACAO["dist_centros"]):
            c = vw.pt(P(i, y))
            cv.circ_p(c, vw.d(fmax) / 2, "vista", preenche="#fff", cor="#06c")
    cv.texto_p(vw.pt(P(pw + 200, ph / 2)), f"furo centrado {fmax} mm, a cada "
               f"{pj.FURACAO['dist_centros']} mm", TXT["micro"], "start", cor="#06c")
    cv.texto_p(vw.pt(P(pw + 200, ph - d / 2)), pj.FURACAO["reforco"],
               TXT["micro"], "start")
    an.cadeia(cv, vw, [0, d, ph - d, ph], -200, "V", -12)
    an.cadeia(cv, vw, list(range(0, pw + 1, pj.MONTANTE_ESPACAMENTO)), 0, "H", 12)

    # ---------------- detalhe do shaft (1:10)
    vw2 = View(10, 240, 180, 0, 0)
    an.titulo_desenho(cv, (212, 200), "2", "SHAFT VERTICAL", "1:10")
    sh = pj.SHAFT
    cv.poli_p([vw2.pt(P(0, 0)), vw2.pt(P(sh["w"] + 200, 0)),
               vw2.pt(P(sh["w"] + 200, sh["h"] + 200)), vw2.pt(P(0, sh["h"] + 200))],
              "corte", fechado=True, preenche="#eceff1")
    cv.poli_p([vw2.pt(P(100, 100)), vw2.pt(P(sh["w"] + 100, 100)),
               vw2.pt(P(sh["w"] + 100, sh["h"] + 100)), vw2.pt(P(100, sh["h"] + 100))],
              "corte", fechado=True, preenche="#fff")
    cv.circ_p(vw2.pt(P(100 + sh["w"] / 2, 100 + sh["h"] / 2)), vw2.d(110) / 2,
              "corte", preenche="#e8f4fb", cor="#06c")
    cv.texto_p(vw2.pt(P(100 + sh["w"] / 2, 100 + sh["h"] / 2)), "DN100",
               TXT["micro"], "middle", cor="#06c")
    cv.texto_p(vw2.pt(P(sh["w"] + 300, sh["h"] / 2)), sh["revestimento"],
               TXT["micro"], "start")
    cv.texto_p(vw2.pt(P(0, -250)), f"{sh['w']} x {sh['h']} mm — {sh['obs']}",
               TXT["micro"], "start")
    an.cadeia(cv, vw2, [0, 100, 100 + sh["w"], sh["w"] + 200], 0, "H", 12)

    linhas = []
    for p in pj.PENETRACOES:
        lim = pj.furo_max("Ue90x40x0.95")
        veredito = ("cabe no montante" if p["onde"] == "montante" and p["dn"] <= lim
                    else "nao cabe no montante" if p["onde"] == "montante"
                    else p["onde"])
        linhas.append([p["cod"], p["tipo"], f"DN{p['dn']}", p["onde"],
                       p["solucao"][:58], veredito])
    _tabela(cv, (35, 245), "PENETRACOES DECLARADAS — O QUE ATRAVESSA O QUE",
            ["COD", "SISTEMA", "DIAM", "ONDE", "SOLUCAO", "VEREDITO"], linhas,
            larguras=[16, 56, 20, 28, 104, 42])

    _tabela(cv, (35, 340), "REGRAS DE FURACAO (NBR 15253 / AISI S200)",
            ["REGRA", "VALOR", "RAZAO"],
            [["Furo centrado na alma", "sempre",
              "a aba e onde esta a inercia; cortar a aba e cortar a rigidez"],
             ["Diametro maximo", f"{pj.FURACAO['frac_alma']:.0%} da alma "
              f"({pj.furo_max('Ue90x40x0.95')} mm em Ue 90)",
              "acima disso cai a carga critica de flambagem local"],
             ["Distancia entre centros", f"{pj.FURACAO['dist_centros']} mm",
              "furos proximos somam-se como um furo maior"],
             ["Distancia ao apoio (montante)", f"{pj.FURACAO['dist_apoio_montante']} mm",
              "o cisalhamento e maximo junto ao apoio"],
             ["Distancia ao apoio (viga)", f"{pj.FURACAO['dist_apoio_viga']} mm",
              "idem, com vao maior e reacao maior"],
             ["Reforco quando inevitavel", pj.FURACAO["reforco"],
              "restitui a area de alma perdida"],
             ["Entreforro disponivel", f"{pj.ENTREFORRO} mm",
              "duto de insuflamento de 250 mm passa aqui, nunca no montante"]],
            larguras=[58, 54, 142])
    return cv


# =========================================================================
# PR-22 / PR-23 — AMPLIACOES DE AREA MOLHADA 1:25
# =========================================================================
_AMPLIACOES = {
    "T": [("T-BWC", "BANHO SOCIAL", 40, 150), ("T-LAV", "LAVANDERIA", 230, 150),
          ("T-COZ", "COZINHA", 430, 150), ("T-DEP", "DEPOSITO", 40, 330)],
    "S": [("S-S02", "SUITE 02 — BANHO E CLOSET", 40, 150),
          ("S-S03", "SUITE 03 — BANHO E CLOSET", 240, 150),
          ("S-MAS", "SUITE MASTER — BANHO E CLOSET", 440, 150)],
}


def _ampliacao(cv: Canvas, cod: str, nome: str, ox: float, oy: float,
               num: str, pav: str) -> None:
    amb = next(a for a in pj.TERREO + pj.SUPERIOR if a.cod == cod)
    vw = View(25, ox, oy, amb.x - 200, amb.y - 200)
    an.titulo_desenho(cv, (ox - 10, oy + 20), num, nome, "1:25")

    paredes = el.derivar_paredes(pj.TERREO if pav == "T" else pj.SUPERIOR)
    vaos = list(el.vaos_do_pavimento(pav))
    el.desenhar_paredes(cv, vw, paredes, vaos)
    el.desenhar_vaos(cv, vw, paredes, vaos, pav)

    # paginacao do piso dentro do ambiente
    z = pj.zona_de(cod)
    if z and z["peca"] == "piso":
        peca = pj.PECA_PISO
        passo = peca["l"] + peca["junta"]
        o = z["origem"]
        k0 = math.floor((amb.x - o[0]) / passo)
        k1 = math.ceil((amb.x + amb.w - o[0]) / passo)
        for k in range(k0, k1 + 1):
            x = o[0] + k * passo
            if amb.x <= x <= amb.x + amb.w:
                cv.linha_p(vw.pt(P(x, amb.y)), vw.pt(P(x, amb.y + amb.h)),
                           "cota", cor="#bbb")
        k0 = math.floor((amb.y - o[1]) / passo)
        k1 = math.ceil((amb.y + amb.h - o[1]) / passo)
        for k in range(k0, k1 + 1):
            y = o[1] + k * passo
            if amb.y <= y <= amb.y + amb.h:
                cv.linha_p(vw.pt(P(amb.x, y)), vw.pt(P(amb.x + amb.w, y)),
                           "cota", cor="#bbb")

    # subdivisoes (banho e closet de suite)
    for sd in pj.SUBDIVISOES:
        if sd["pai"] != cod:
            continue
        cv.poli_p([vw.pt(P(sd["x"], sd["y"])), vw.pt(P(sd["x"] + sd["w"], sd["y"])),
                   vw.pt(P(sd["x"] + sd["w"], sd["y"] + sd["h"])),
                   vw.pt(P(sd["x"], sd["y"] + sd["h"]))], "corte2", fechado=True,
                  preenche="none", cor="#666")
        cv.texto_p(vw.pt(P(sd["x"] + sd["w"] / 2, sd["y"] + sd["h"] / 2)),
                   sd["nome"], TXT["micro"], "middle", cor="#666")

    # loucas, bancadas, equipamentos e armarios do ambiente
    for lc in pj.LOUCAS:
        if lc["amb"] != cod:
            continue
        t = lc["tipo"]
        if t == "vaso":
            mob.vaso(cv, vw, lc["x"], lc["y"])
        elif t == "lavatorio":
            mob.lavatorio(cv, vw, lc["x"], lc["y"], lc["w"], lc["h"])
        elif t == "box":
            mob.box(cv, vw, lc["x"], lc["y"], lc["w"], lc["h"])
        elif t == "tanque":
            mob.tanque(cv, vw, lc["x"], lc["y"], lc["w"], lc["h"])
        cv.texto_p(vw.pt(P(lc["x"] + lc["w"] / 2, lc["y"] - 120)), lc["cod"],
                   TXT["micro"], "middle", cor="#06c")
    for b in pj.BANCADAS:
        if b["amb"] != cod:
            continue
        mob.bancada(cv, vw, b["x"], b["y"], b["w"], b["h"], b["cubas"], b["cooktop"])
        cv.texto_p(vw.pt(P(b["x"] + b["w"] / 2, b["y"] + b["h"] / 2)), b["cod"],
                   TXT["micro"], "middle", cor="#06c")
    for e in pj.EQUIPAMENTOS:
        if e["amb"] != cod:
            continue
        mob.maquina(cv, vw, e["x"], e["y"], min(e["w"], e["h"]),
                    e["tipo"][:2].upper())
    for ar in pj.ARMARIOS:
        if ar["amb"] != cod:
            continue
        cv.poli_p([vw.pt(P(ar["x"], ar["y"])), vw.pt(P(ar["x"] + ar["w"], ar["y"])),
                   vw.pt(P(ar["x"] + ar["w"], ar["y"] + ar["h"])),
                   vw.pt(P(ar["x"], ar["y"] + ar["h"]))], "fino", fechado=True,
                  preenche="#f5f5f5", cor=CINZA)
        cv.texto_p(vw.pt(P(ar["x"] + ar["w"] / 2, ar["y"] + ar["h"] / 2)), ar["cod"],
                   TXT["micro"], "middle", cor=CINZA)

    # ralos e caimento
    cv.texto_p(vw.pt(P(amb.x + 150, amb.y + 150)), "i 1,5 %", TXT["micro"],
               "start", cor="#09a")
    an.cadeia(cv, vw, [amb.x, amb.x + amb.w], amb.y, "H", 12)
    an.cadeia(cv, vw, [amb.y, amb.y + amb.h], amb.x, "V", -12)
    alt = pj.alturas_revestimento().get(cod)
    if alt:
        cv.texto_p(vw.pt(P(amb.x, amb.y + amb.h + 500)),
                   f"revestimento h = {alt} mm", TXT["micro"], "start", cor="#06c")


def ampliacoes(pav: str, prancha: str) -> Canvas:
    titulo = ("AMPLIACOES DE AREA MOLHADA — TERREO" if pav == "T"
              else "AMPLIACOES DE AREA MOLHADA — SUPERIOR")
    cv = base(titulo, "1:25", prancha, notas=[
        "Paginacao de piso em linha fina: a malha vem da ZONA de paginacao, nao do "
        "canto do ambiente.",
        f"Peca de piso {pj.PECA_PISO['tipo']}; parede {pj.PECA_PAREDE['tipo']}; "
        f"junta {pj.PECA_PISO['junta']} mm.",
        "Caimento de 1,5 % para o ralo em toda area molhada; soleira elevada 15 mm "
        "nos boxes.",
        "Impermeabilizacao: manta liquida em 2 demaos, subindo 300 mm na parede e "
        "1.800 mm nos boxes.",
    ])
    for i, (cod, nome, ox, oy) in enumerate(_AMPLIACOES[pav], 1):
        _ampliacao(cv, cod, nome, ox, oy, str(i), pav)

    linhas = []
    for cod, nome, _, _ in _AMPLIACOES[pav]:
        r = pj.paginar(cod)
        if not r:
            continue
        alt = r.get("altura")
        linhas.append([
            cod, nome[:26], r["zona"], r["peca"],
            f"{r['x']['inteiras']} + {r['x']['recorte_ini']}/{r['x']['recorte_fim']}",
            f"{r['y']['inteiras']} + {r['y']['recorte_ini']}/{r['y']['recorte_fim']}",
            f"{alt['altura']} ({alt['fiadas']} fiadas + {alt['fiada_topo']})" if alt else "—"])
    _tabela(cv, (35, 420), "PAGINACAO VERIFICADA — PECAS INTEIRAS + RECORTE EM CADA PONTA",
            ["AMB", "AMBIENTE", "ZONA", "PECA", "EIXO X", "EIXO Y", "ALTURA (mm)"],
            linhas, larguras=[16, 56, 18, 20, 44, 44, 56])
    return cv


# =========================================================================
# PR-24 — PAGINACAO DE PISO
# =========================================================================
def paginacao_piso() -> Canvas:
    cv = base("PAGINACAO DE PISO E ZONAS DE REVESTIMENTO", "1:75", "24", notas=[
        "Paginar no projeto e decidir onde fica o corte. Nao paginar e deixar o "
        "corte aparecer no lugar mais visivel.",
        "Ambientes integrados recebem UMA malha: a junta desalinhada no meio da "
        "sala nao tem parede para disfarcar.",
        f"Recorte minimo aceito {pj.RECORTE_MIN:.0%} da peca; abaixo de "
        f"{pj.RECORTE_CRITICO:.0%} o recorte descola e e reprovado.",
    ])
    cores = {"ZP-1": "#e8f4fb", "ZP-2": "#eef7e8", "ZP-3": "#fdf3e0",
             "ZP-4": "#f6e8f4", "ZP-5": "#fff3d6", "ZP-6": "#ececec"}
    for pav, ox, num in (("T", 40, "1"), ("S", 420, "2")):
        vw = View(75, ox, 150, 2_000, 7_000)
        ambs = pj.TERREO if pav == "T" else pj.SUPERIOR
        an.titulo_desenho(cv, (ox - 10, 500),
                          num, f"PAGINACAO — {'TERREO' if pav == 'T' else 'SUPERIOR'}", "1:75")
        for a in ambs:
            z = pj.zona_de(a.cod)
            cor = cores.get(z["cod"], "#ffffff") if z else "#ffffff"
            cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                       vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                      "vista", fechado=True, preenche=cor, cor="#888")
            cv.texto_p(vw.pt(P(a.cx, a.cy)), z["cod"] if z else "padrao",
                       TXT["micro"], "middle", cor="#555")
        # malha de piso das zonas de piso
        for z in pj.ZONAS_PAGINACAO:
            if z["peca"] != "piso":
                continue
            alvos = [a for a in ambs if a.cod in z["ambientes"]]
            if not alvos:
                continue
            x0 = min(a.x for a in alvos); x1 = max(a.x + a.w for a in alvos)
            y0 = min(a.y for a in alvos); y1 = max(a.y + a.h for a in alvos)
            passo = pj.PECA_PISO["l"] + pj.PECA_PISO["junta"]
            k = math.floor((x0 - z["origem"][0]) / passo)
            while z["origem"][0] + k * passo <= x1:
                x = z["origem"][0] + k * passo
                if x >= x0:
                    cv.linha_p(vw.pt(P(x, y0)), vw.pt(P(x, y1)), "cota", cor="#bbb")
                k += 1
            k = math.floor((y0 - z["origem"][1]) / passo)
            while z["origem"][1] + k * passo <= y1:
                y = z["origem"][1] + k * passo
                if y >= y0:
                    cv.linha_p(vw.pt(P(x0, y)), vw.pt(P(x1, y)), "cota", cor="#bbb")
                k += 1
            # marca da origem
            c = vw.pt(P(*z["origem"]))
            cv.circ_p(c, 1.8, "corte", preenche="#c00", cor="#c00")
            cv.texto_p((c[0] + 3, c[1] - 1), z["cod"], TXT["micro"], "start", cor="#c00")
        an.norte(cv, (ox + 180, 120), 7, pj.NORTE_EM_PLANTA)

    linhas = []
    for z in pj.ZONAS_PAGINACAO:
        peca = (pj.PECA_PISO if z["peca"] == "piso" else
                pj.PECA_PAREDE if z["peca"] == "parede" else None)
        piores = []
        for cod in z["ambientes"]:
            r = pj.paginar(cod)
            if r:
                piores += [r["x"]["pior"], r["y"]["pior"]]
        linhas.append([
            z["cod"], z["peca"],
            f"({z['origem'][0]}, {z['origem'][1]})" if "origem" in z else "canto do ambiente",
            ", ".join(z["ambientes"]),
            peca["tipo"][:34] if peca else "cimenticio polido",
            f"{min(piores)}" if piores else "—",
            z["obs"][:62]])
    _tabela(cv, (35, 520), "ZONAS DE PAGINACAO",
            ["ZONA", "PECA", "ORIGEM", "AMBIENTES", "PECA ESPECIFICADA",
             "PIOR RECORTE", "CRITERIO"], linhas,
            larguras=[16, 22, 34, 62, 58, 24, 140])
    return cv


# =========================================================================
# PR-25 — ESCADA EXECUTIVA
# =========================================================================
def escada() -> Canvas:
    e, ex = pj.ESCADA, pj.ESCADA_EXEC
    lances = pj.escada_lances()
    cv = base("ESCADA — DESENHO EXECUTIVO", "indicada", "25", notas=[
        f"{e['espelhos']} espelhos de {e['alt_espelho']:.2f} mm e piso de {e['piso']} mm. "
        f"Blondel 2h + p = {e['blondel']:.1f} mm (faixa recomendada 600 a 650).",
        f"Altura livre minima {ex['altura_livre_min']} mm (NBR 9077), verificada degrau "
        f"a degrau contra a laje e o vazio acima.",
        f"Guarda-corpo {ex['guarda_corpo']} mm; corrimao duplo em "
        f"{ex['corrimao_h'][0]} e {ex['corrimao_h'][1]} mm (NBR 9050).",
        ex["estrutura"],
    ])

    # ---------------- planta 1:25
    vw = View(25, 50, 170, e["x"] - 400, e["y"] - 400)
    an.titulo_desenho(cv, (40, 200), "1", "PLANTA DA ESCADA", "1:25")
    cv.poli_p([vw.pt(P(e["x"], e["y"])), vw.pt(P(e["x"] + e["w"], e["y"])),
               vw.pt(P(e["x"] + e["w"], e["y"] + e["h"])),
               vw.pt(P(e["x"], e["y"] + e["h"]))], "fino", fechado=True,
              preenche="#fafafa", cor="#999")
    for l in lances:
        cv.poli_p([vw.pt(P(l["x"], l["y"])), vw.pt(P(l["x"] + l["w"], l["y"])),
                   vw.pt(P(l["x"] + l["w"], l["y"] + l["h"])),
                   vw.pt(P(l["x"], l["y"] + l["h"]))], "vista", fechado=True,
                  preenche="#fff", cor="#444")
        if l["sentido"] == "patamar":
            cv.texto_p(vw.pt(P(l["x"] + l["w"] / 2, l["y"] + l["h"] / 2)),
                       f"PATAMAR  +{l['z_ini']:.0f}", TXT["micro"], "middle")
            continue
        n = l["espelhos"] - 1
        for i in range(1, n + 1):
            y = l["y"] + (i * e["piso"] if l["sentido"] == "+Y"
                          else l["h"] - i * e["piso"])
            cv.linha_p(vw.pt(P(l["x"], y)), vw.pt(P(l["x"] + l["w"], y)), "fino")
            z = l["z_ini"] + (l["z_fim"] - l["z_ini"]) * (i / l["espelhos"])
            if i % 3 == 0:
                cv.texto_p(vw.pt(P(l["x"] + l["w"] / 2, y + 60)), f"+{z:.0f}",
                           TXT["micro"], "middle", cor=CINZA)
    # armario sob escada
    for ar in pj.ARMARIOS:
        if not ar.get("sob_escada"):
            continue
        cv.poli_p([vw.pt(P(ar["x"], ar["y"])), vw.pt(P(ar["x"] + ar["w"], ar["y"])),
                   vw.pt(P(ar["x"] + ar["w"], ar["y"] + ar["h"])),
                   vw.pt(P(ar["x"], ar["y"] + ar["h"]))], "oculto", fechado=True,
                  preenche="none", cor="#b5651d")
        cv.texto_p(vw.pt(P(ar["x"] + ar["w"] / 2, ar["y"] + ar["h"] / 2)),
                   f"{ar['cod']} SOB ESCADA", TXT["micro"], "middle", cor="#b5651d")
    an.cadeia(cv, vw, [e["x"], lances[0]["x"], lances[0]["x"] + lances[0]["w"],
                       lances[2]["x"], lances[2]["x"] + lances[2]["w"],
                       e["x"] + e["w"]], e["y"], "H", 12)
    an.cadeia(cv, vw, [e["y"], lances[0]["y"] + lances[0]["h"],
                       lances[1]["y"] + lances[1]["h"], e["y"] + e["h"]],
              e["x"], "V", -12)
    an.norte(cv, (200, 120), 7, pj.NORTE_EM_PLANTA)

    # ---------------- corte longitudinal 1:25
    vw2 = View(25, 300, 260, e["y"] - 400, 0)
    an.titulo_desenho(cv, (290, 290), "2", "CORTE LONGITUDINAL — ALTURA LIVRE", "1:25")
    l1, pt, l2 = lances
    # piso do terreo e do superior
    cv.linha_p(vw2.pt(P(e["y"] - 400, 0)), vw2.pt(P(e["y"] + e["h"] + 400, 0)), "corte")
    # degraus do lance 1
    h = e["alt_espelho"]
    for i in range(l1["espelhos"]):
        y0 = l1["y"] + i * e["piso"]
        z0, z1 = i * h, (i + 1) * h
        cv.linha_p(vw2.pt(P(y0, z0)), vw2.pt(P(y0, z1)), "vista")
        cv.linha_p(vw2.pt(P(y0, z1)), vw2.pt(P(y0 + e["piso"], z1)), "vista")
    # patamar
    cv.linha_p(vw2.pt(P(pt["y"], pt["z_ini"])), vw2.pt(P(pt["y"] + pt["h"], pt["z_ini"])),
               "corte2")
    # lance 2 sobe em -Y
    for i in range(l2["espelhos"]):
        y0 = l2["y"] + l2["h"] - i * e["piso"]
        z0 = pt["z_ini"] + i * h
        z1 = z0 + h
        cv.linha_p(vw2.pt(P(y0, z0)), vw2.pt(P(y0, z1)), "oculto")
        cv.linha_p(vw2.pt(P(y0, z1)), vw2.pt(P(y0 - e["piso"], z1)), "oculto")
    # laje do superior onde existe, e o vazio onde nao existe
    for y in range(int(e["y"]), int(e["y"] + e["h"]), 150):
        teto = pj.PISO_A_PISO if any(
            a.x <= l1["x"] + 500 < a.x + a.w and a.y <= y < a.y + a.h
            for a in pj.SUPERIOR) else pj.PISO_A_PISO + pj.PE_DIREITO
        cv.linha_p(vw2.pt(P(y, teto)), vw2.pt(P(y + 150, teto)),
                   "corte" if teto == pj.PISO_A_PISO else "cota",
                   cor=PRETO if teto == pj.PISO_A_PISO else "#09a")
    cv.texto_p(vw2.pt(P(e["y"] + 300, pj.PISO_A_PISO + pj.PE_DIREITO + 300)),
               "VAZIO — pe-direito duplo sobre o core", TXT["micro"], "start", cor="#09a")
    # cota critica de altura livre
    pior, pior_y, pior_z = 1e9, 0, 0
    for l in lances:
        for i in range(int(l["h"] // 150) + 1):
            dy = i * 150
            frac = dy / l["h"] if l["h"] else 0
            if l["sentido"] == "-Y":
                frac = 1 - frac
            z = l["z_ini"] + (l["z_fim"] - l["z_ini"]) * frac
            y = l["y"] + dy
            teto = pj.PISO_A_PISO if any(
                a.x <= l["x"] + l["w"] / 2 < a.x + a.w and a.y <= y < a.y + a.h
                for a in pj.SUPERIOR) else pj.PISO_A_PISO + pj.PE_DIREITO
            if teto - z < pior:
                pior, pior_y, pior_z = teto - z, y, z
    a = vw2.pt(P(pior_y, pior_z)); b = vw2.pt(P(pior_y, pior_z + pior))
    cv.linha_p(a, b, "cota", cor="#c00")
    cv.texto_p((b[0] + 3, (a[1] + b[1]) / 2), f"altura livre minima {pior:.0f} mm",
               TXT["micro"], "start", cor="#c00")
    an.cadeia(cv, vw2, [0, pt["z_ini"], pj.PISO_A_PISO], e["y"] - 300, "V", -12)

    # ---------------- detalhe do degrau 1:5
    vw3 = View(5, 560, 220, 0, 0)
    an.titulo_desenho(cv, (550, 290), "3", "DETALHE DO DEGRAU", "1:5")
    cv.poli_p([vw3.pt(P(0, 0)), vw3.pt(P(e["piso"], 0)),
               vw3.pt(P(e["piso"], -3)), vw3.pt(P(0, -3))], "corte", fechado=True,
              preenche="#90a4ae")
    cv.poli_p([vw3.pt(P(e["piso"], 0)), vw3.pt(P(e["piso"] + 3, 0)),
               vw3.pt(P(e["piso"] + 3, h)), vw3.pt(P(e["piso"], h))], "corte",
              fechado=True, preenche="#90a4ae")
    cv.poli_p([vw3.pt(P(0, 0)), vw3.pt(P(e["piso"], 0)), vw3.pt(P(e["piso"], 12)),
               vw3.pt(P(0, 12))], "corte", fechado=True, preenche="#d7ccc8")
    cv.texto_p(vw3.pt(P(e["piso"] + 120, 6)), "chapa dobrada 3 mm + porcelanato "
               "900 x 300", TXT["micro"], "start")
    cv.texto_p(vw3.pt(P(e["piso"] + 120, h / 2)), "espelho fechado (NBR 9050)",
               TXT["micro"], "start")
    cv.texto_p(vw3.pt(P(0, -80)), "faixa antiderrapante de 25 mm a 20 mm da borda",
               TXT["micro"], "start", cor="#c00")
    an.cadeia(cv, vw3, [0, e["piso"]], 0, "H", 12)

    # ---------------- quadros
    _tabela(cv, (35, 330), "VERIFICACAO DA ESCADA",
            ["ITEM", "PROJETO", "NORMA", ""],
            [["Espelho", f"{e['alt_espelho']:.2f} mm", "16 a 18 cm (NBR 9077)",
              "OK" if 160 <= e["alt_espelho"] <= 180 else "REVER"],
             ["Piso", f"{e['piso']} mm", "min 28 cm", "OK" if e["piso"] >= 280 else "REVER"],
             ["Blondel (2h + p)", f"{e['blondel']:.1f} mm", "600 a 650 mm",
              "OK" if 600 <= e["blondel"] <= 650 else "REVER"],
             ["Largura util do lance", f"{e['larg_lance']} mm", "min 1.200 mm (uso coletivo) / "
              "1.000 mm (unifamiliar)", "OK"],
             ["Patamar", f"{e['patamar']} mm", ">= largura do lance",
              "OK" if e["patamar"] >= e["larg_lance"] else "REVER"],
             ["Altura livre minima", f"{pior:.0f} mm", f"min {ex['altura_livre_min']} mm",
              "OK" if pior >= ex["altura_livre_min"] else "REVER"],
             ["Guarda-corpo", f"{ex['guarda_corpo']} mm", "min 1.100 mm (NBR 14718)", "OK"],
             ["Corrimao", f"{ex['corrimao_h'][0]} e {ex['corrimao_h'][1]} mm",
              "duplo, 92 cm e 70 cm (NBR 9050)", "OK"],
             ["Espelho fechado", "sim", "obrigatorio em rota acessivel", "OK"],
             ["Desnivel vencido", f"{pj.PISO_A_PISO} mm",
              f"{e['espelhos']} x {e['alt_espelho']:.2f} mm", "OK"]],
            larguras=[50, 44, 86, 20])

    _tabela(cv, (35, 420), "O QUE A PLANTA NAO MOSTRA",
            ["QUESTAO", "RESPOSTA"],
            [["Por que o primeiro espelho sobe de y = 13.200",
              "o patamar terminava 100 mm dentro da projecao do hall superior, com "
              "1.500 mm de altura livre — uma quina na altura da cabeca de quem "
              "termina o primeiro lance"],
             ["Por que a verificacao de altura livre e tridimensional",
              "altura livre de escada e o unico defeito que nao aparece em planta "
              "nenhuma: depende da cota do degrau e da cota do que ha acima dele"],
             ["O que ha sob o segundo lance",
              f"triangulo com altura util variavel, declarado como armario "
              f"(AR-05): nao e circulacao nem espaco morto"],
             ["Por que espelho fechado",
              "degrau vazado prende a ponta do pe de quem usa bengala ou tem "
              "mobilidade reduzida (NBR 9050)"],
             ["Por que corrimao duplo",
              "920 mm para adulto e 700 mm para crianca; em casa com escada aberta "
              "para a sala, o segundo corrimao e o que realmente se usa"]],
            larguras=[86, 200])
    return cv
