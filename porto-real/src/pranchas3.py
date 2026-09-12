"""Detalhes ampliados e quadros gerais consolidados."""
from __future__ import annotations

import projeto as pj
import anotacao as an
from core import P, Canvas, View, TXT, CINZA, PRETO
from pranchas import base, _tabela


def _cam(cv, vw, x, y, w, h, cor, rotulo, hach=None):
    cv.poli_p([vw.pt(P(x, y)), vw.pt(P(x + w, y)), vw.pt(P(x + w, y + h)), vw.pt(P(x, y + h))],
              "vista", fechado=True, preenche=hach or cor)
    return rotulo


def detalhes() -> Canvas:
    cv = base("DETALHES CONSTRUTIVOS AMPLIADOS", "indicada", "10", notas=[
        "Detalhes de estudo — nao liberados para fabricacao ou corte (sem nesting codificado).",
        "Parede externa consolidada em 150 mm; divisoria interna em 100 mm (H).",
        "Escada reconciliar com estrutura, guarda-corpo e espessura de acabamento antes de definitiva.",
    ])

    # =================== DET 1 — parede externa LSF 150 mm (1:5)
    vw = View(5, 70, 160, 0, 0)
    an.titulo_desenho(cv, (60, 92), "1", "PAREDE EXTERNA EM LIGHT STEEL FRAME", "1:5")
    camadas = [
        (0, 10, "#9aa5b1", "Chapa cimenticia 10 mm (externa)"),
        (10, 90, "#f2f2f2", "Montante Steel Frame 90 mm @ 600 mm (400 mm onde exigido)"),
        (100, 12.5, "#e8e8e8", "Chapa de gesso 12,5 mm (RU em area umida)"),
        (112.5, 37.5, "#fff6d6", "Camara / la mineral 50 mm"),
    ]
    y = 0
    for i, (x0, esp, cor, txt) in enumerate(camadas):
        cv.poli_p([vw.pt(P(x0, 0)), vw.pt(P(x0 + esp, 0)),
                   vw.pt(P(x0 + esp, 1_200)), vw.pt(P(x0, 1_200))],
                  "corte", fechado=True, preenche=cor)
        py = vw.pt(P(x0 + esp / 2, 1_200))
        cv.linha_p(py, (py[0], py[1] - 8 - i * 5), "cota", cor=CINZA)
        cv.texto_p((py[0], py[1] - 10 - i * 5), txt, TXT["micro"], "start")
    # montantes
    for j in range(3):
        yy = 120 + j * 480
        cv.poli_p([vw.pt(P(10, yy)), vw.pt(P(100, yy)), vw.pt(P(100, yy + 40)),
                   vw.pt(P(10, yy + 40))], "corte", fechado=True, preenche="#b0bec5")
    an.cadeia(cv, vw, [0, 10, 100, 112.5, 150], 0, "H", 14)
    cv.texto_p(vw.pt(P(75, -400)), "esp. total 150 mm", TXT["min"], "middle")

    # =================== DET 2 — escada em U (1:25)
    e = pj.ESCADA
    vw2 = View(25, 230, 200, 0, 0)
    an.titulo_desenho(cv, (215, 92), "2", "ESCADA — CORTE ESQUEMATICO", "1:25")
    n = e["espelhos"]
    a_esp, p_piso = e["alt_espelho"], e["piso"]
    x = 0.0
    z = 0.0
    pts = [vw2.pt(P(0, 0))]
    for i in range(n):
        z += a_esp
        pts.append(vw2.pt(P(x, z)))
        x += p_piso
        pts.append(vw2.pt(P(x, z)))
    cv.poli_p(pts, "corte")
    cv.linha_p(vw2.pt(P(0, 0)), vw2.pt(P(x, 0)), "cota", cor=CINZA)
    cv.linha_p(vw2.pt(P(0, 0)), vw2.pt(P(x, z)), "eixo", cor="#c00")
    # guarda-corpo e corrimao
    cv.linha_p(vw2.pt(P(300, 1_100)), vw2.pt(P(x, z + 1_100)), "vista")
    cv.linha_p(vw2.pt(P(300, 920)), vw2.pt(P(x, z + 920)), "fino")
    an.cadeia(cv, vw2, [0, p_piso, 2 * p_piso], 0, "H", 12)
    an.cadeia(cv, vw2, [0, a_esp, 2 * a_esp, z], 0, "V", -12)
    for i, t in enumerate([
        f"{n} espelhos x {a_esp:.2f} mm",
        f"piso {p_piso} mm | Blondel {e['blondel']:.2f} mm",
        f"largura util {e['larg_lance']} mm | patamar {e['patamar']}x{e['patamar']} mm",
        "guarda-corpo 1.100 mm | corrimao 920 mm",
        "altura livre vertical minima 2.100 mm",
    ]):
        cv.texto_p((230, 214 + i * 4.4), "- " + t, TXT["micro"], "start")

    # =================== DET 3 — piscina (1:25)
    ps = pj.PISCINA
    vw3 = View(25, 460, 200, 0, 0)
    an.titulo_desenho(cv, (445, 92), "3", "PISCINA — CORTE", "1:25")
    prain, prof = ps["prainha_w"], ps["prof_principal"]
    cv.poli_p([vw3.pt(P(0, 0)), vw3.pt(P(ps["w"], 0)),
               vw3.pt(P(ps["w"], -prof)), vw3.pt(P(prain, -prof)),
               vw3.pt(P(prain, -ps["prof_prainha"])), vw3.pt(P(0, -ps["prof_prainha"]))],
              "corte", fechado=True, preenche="#dff0fa")
    cv.linha_p(vw3.pt(P(-1_200, 0)), vw3.pt(P(ps["w"] + 1_200, 0)), "corte")
    cv.texto_p(vw3.pt(P(prain / 2, -150)), "PRAINHA 300", TXT["micro"], "middle")
    cv.texto_p(vw3.pt(P((ps["w"] + prain) / 2, -600)),
               f"LAMINA {ps['lamina_m2']:.2f} m2 | V = {ps['volume_m3']:.2f} m3".replace(".", ","),
               TXT["micro"], "middle")
    cv.poli_p([vw3.pt(P(ps["w"] - 500, -prof)), vw3.pt(P(ps["w"], -prof)),
               vw3.pt(P(ps["w"], -prof + 450)), vw3.pt(P(ps["w"] - 500, -prof + 450))],
              "fino", fechado=True, preenche="#cfe7f5")
    cv.texto_p(vw3.pt(P(ps["w"] - 250, -prof + 700)), "BANCO 450 (H)", TXT["micro"], "middle")
    an.cadeia(cv, vw3, [0, prain, ps["w"]], 0, "H", 12)
    for i, t in enumerate([
        "bomba 0,50 cv | vazao 3,60 m3/h | renovacao 3 h",
        "filtro nominal 4,00 m3/h | succao/retorno DN50",
        "1 skimmer | 2 ralos de fundo | 2 retornos | 1 aspiracao",
        "deck antiderrapante min. 1.200 mm (lado principal)",
        "casa de maquinas 1.500 x 1.200 mm",
    ]):
        cv.texto_p((460, 214 + i * 4.4), "- " + t, TXT["micro"], "start")

    # =================== DET 4 — faixa tecnica lateral (1:25)
    vw4 = View(25, 660, 200, 0, 0)
    an.titulo_desenho(cv, (645, 92), "4", "FAIXA TECNICA LATERAL — CORTE", "1:25")
    cv.linha_p(vw4.pt(P(-200, 0)), vw4.pt(P(3_400, 0)), "corte")
    cv.poli_p([vw4.pt(P(0, 0)), vw4.pt(P(150, 0)), vw4.pt(P(150, 2_600)), vw4.pt(P(0, 2_600))],
              "corte", fechado=True, preenche="#e0e0e0")
    cv.texto_p(vw4.pt(P(75, 2_800)), "PAREDE", TXT["micro"], "middle", rot=90)
    cv.poli_p([vw4.pt(P(150, 200)), vw4.pt(P(950, 200)), vw4.pt(P(950, 1_100)),
               vw4.pt(P(150, 1_100))], "vista", fechado=True, preenche="#f0f0f0")
    cv.texto_p(vw4.pt(P(550, 650)), "CONDENSADORA", TXT["micro"], "middle")
    cv.linha_p(vw4.pt(P(1_000, 0)), vw4.pt(P(1_000, 1_800)), "vista")
    cv.texto_p(vw4.pt(P(1_000, 2_000)), "PAINEL VENTILADO h=1.800", TXT["micro"], "middle")
    an.cadeia(cv, vw4, [0, 150, 950, 1_000, 3_200], 0, "H", 12)
    for i, t in enumerate([
        "faixa livre minima 3.000 mm (projeto: 3.200 mm)",
        "equipamentos ocupam ate 800 mm",
        "corredor livre apos equipamentos >= 1.200 mm (desejavel 1.500)",
        "base 200 mm acima do piso | folga traseira 300 mm",
        "folga frontal de manutencao 1.000 mm",
    ]):
        cv.texto_p((660, 214 + i * 4.4), "- " + t, TXT["micro"], "start")
    return cv


def quadros() -> Canvas:
    cv = base("QUADROS GERAIS E PENDENCIAS", "s/ escala", "09", notas=[
        "Itens marcados (H) sao hipoteses tecnicas de projeto, nao levantamento.",
        "Documento de coordenacao — nao substitui projeto legal, calculo ou ART/RRT.",
    ])
    t_area = pj.area_fechada("T")
    s_area = pj.area_fechada("S")

    _tabela(cv, (35, 40), "QUADRO GERAL DE AREAS",
            ["DESCRICAO", "PROJETO (m2)", "BRIEFING (m2)", "DELTA"],
            [["Lote", "800,00", "800,00", "0,00"],
             ["Area fechada — terreo", f"{t_area:.2f}".replace(".", ","), "174,24",
              f"{t_area-174.24:+.2f}".replace(".", ",")],
             ["Area fechada — superior", f"{s_area:.2f}".replace(".", ","), "84,96", "+1,44"],
             ["Area fechada total", f"{t_area+s_area:.2f}".replace(".", ","), "259,20", "+1,44"],
             ["Varanda master (aberta)", "10,80", "10,80", "0,00"],
             ["Areas externas cobertas/descobertas",
              f"{pj.area_aberta('T'):.2f}".replace(".", ","), "-", "-"],
             ["Lamina d'agua da piscina", "11,52", "11,52", "0,00"],
             ["Projecao coberta (terreo + avancos)",
              f"{pj.projecao_coberta_m2():.2f}".replace(".", ","), "-", "-"],
             ["Taxa de ocupacao (projecao coberta)",
              f"{pj.projecao_coberta_m2()/8:.2f} %".replace(".", ","), "max 50 %", "OK"],
             ["Coef. de aproveitamento",
              f"{(t_area+s_area)/800:.3f}".replace(".", ","), "max 1,00", "OK"]],
            larguras=[86, 34, 34, 22])

    linhas = []
    for t, (lg, al, pe, desc) in pj.ESQUADRIAS.items():
        q = sum(1 for v in pj.VAOS if v[0] == t)
        linhas.append([t, f"{lg} x {al}", str(pe), str(q),
                       f"{(lg*al)/1e6*q:.2f}".replace(".", ","), desc[:52]])
    _tabela(cv, (35, 130), "MAPA GERAL DE ESQUADRIAS",
            ["REF", "VAO (mm)", "PEIT.", "QTD", "AREA TOT (m2)", "TIPO"], linhas,
            larguras=[16, 30, 16, 14, 30, 110])

    _tabela(cv, (35, 215), "SISTEMAS PREDIAIS — PARAMETROS CONSOLIDADOS",
            ["SISTEMA", "PARAMETRO", "VALOR"],
            [["Reservacao", "Superior / cisterna / total", "2.000 L / 3.000 L / 5.000 L"],
             ["Reservacao", "Consumo e autonomia (6 pes., 200 L/dia)", "1.200 L/dia | 4,17 dias"],
             ["Recalque", "Motobomba / HMT", "0,50 cv | 2,40 m3/h | 15,00 mca"],
             ["Pluvial", "Vazao total / por descida", "8,2764 L/s | 2,0691 L/s (4 x DN100)"],
             ["Pluvial", "Retencao para reuso", "2.500 L — irrigacao e lavagem"],
             ["Esgoto", "Coletor / ventilacao / cx. gordura", "DN100 | DN50 | 30 L"],
             ["Agua quente", "Solucao adotada (FECHADA)", "4 chuveiros 4.500 W em 220 V (18,0 kW)"],
             ["Agua quente", "Circuito por chuveiro", "20,5 A | 4,0 mm2 | disjuntor 25 A"],
             ["Agua quente", "Demanda (fd 0,75)", "13,5 kW — era 27,2 kW instalados"],
             ["Pluvial reuso", "Decisao (FECHADA)", "2.500 L, dimensionado pela demanda"],
             ["Pluvial reuso", "Captacao x demanda", "371 m3/ano disponiveis | 98 m3/ano usados"],
             ["Pluvial reuso", "Autonomia", "9,3 dias | nao estender a vasos sanitarios"],
             ["Climatizacao", "Carga instalada (ver quadro proprio)",
              f"{pj.carga_instalada_btu():,} BTU/h".replace(",", ".")],
             ["Climatizacao", "Infraestrutura reservada",
              f"{pj.carga_instalada_btu(True)-pj.carga_instalada_btu():,} BTU/h"
              .replace(",", ".") + " (social + oficina)"],
             ["Eletrica", "Quadros", "geral 36 modulos | superior 24 modulos"],
             ["Eletrica", "Infraestrutura futura", "fotovoltaica + carregador de VE"],
             ["Dados", "CFTV / Wi-Fi / videoporteiro", "8 cameras | 3 APs | 1 unidade"],
             ["Estrutura", "Fundacao / vedacao", "radier 180 mm fck 30 (H) | LSF + perfis"],
             ["Solo", "Tensao admissivel / sondagem", "150 kPa (H) | 3 furos SPT, 12 m"]],
            larguras=[36, 96, 110])


    lin_cl = []
    for c in pj.CLIMATIZACAO:
        cg = pj.carga_termica(c["amb"], c["pessoas"], c["equip"], c.get("mais"))
        amb = next((a for a in pj.TERREO + pj.SUPERIOR if a.cod == c["amb"]), None)
        nome = amb.nome if amb else c["amb"]
        if c.get("mais"):
            nome += " + " + "+".join(c["mais"])
        lin_cl.append([
            c["amb"], nome[:30],
            f"{pj.area_condicionada(c['amb']):.2f}".replace(".", ","),
            f"{pj.area_vidro(c['amb']):.2f}".replace(".", ","),
            f"{cg:,}".replace(",", "."),
            f"{c['capacidade']:,}".replace(",", "."),
            c["nicho"],
            "RESERVA" if c.get("reserva") else "ATIVO"])
    _tabela(cv, (35, 375),
            f"CLIMATIZACAO — CARGA CALCULADA x EQUIPAMENTO (q = {pj.CLIMA_Q_M2} "
            f"BTU/h.m2, ZB8 com o pacote de sombreamento do projeto)",
            ["AMB", "AMBIENTE", "AREA (m2)", "VIDRO (m2)", "CARGA (BTU/h)",
             "EQUIP. (BTU/h)", "NICHO", "FASE"], lin_cl,
            larguras=[16, 62, 26, 26, 30, 30, 18, 22])

    lin_tc = []
    for t in pj.TECNICOS:
        n = len(pj.nicho_de(t["cod"]))
        pos = (f"interno a {t['amb']}" if t.get("zona") == "INT"
               else f"({t['x']}, {t['y']})")
        cond = ("enterrado" if t.get("prof") and t.get("zona") == "ENT"
                else "rasante" if t.get("rasante") else "aparente")
        lin_tc.append([t["cod"], t["nome"][:40], t.get("zona", "-"), pos,
                       f"{t['w']} x {t['h']}", cond,
                       f"{n} posicoes" if n else t["obs"][:44]])
    _tabela(cv, (35, 450), "AREAS TECNICAS LOCADAS",
            ["COD", "ELEMENTO", "ZONA", "POSICAO (mm)", "DIM (mm)",
             "CONDICAO", "OBSERVACAO"], lin_tc,
            larguras=[16, 76, 18, 38, 28, 22, 62])

    _tabela(cv, (35, 300), "PENDENCIAS — O QUE NAO ESTA LIBERADO",
            ["#", "PENDENCIA", "IMPACTO"],
            [["1", "Certidao oficial do SU16 (CAMT, taxa de ocupacao, gabarito) — Lei 1.838/2014",
              "Condiciona toda a implantacao"],
             ["2", "Sondagem real do solo e calculo definitivo do radier", "Fundacao"],
             ["3", "Calculo estrutural do sistema hibrido LSF + perfis + apoio da caixa d'agua",
              "Estrutura e balanco"],
             ["4", "Verificacao ambiental do reuso pluvial (Codigo Ambiental de Manaus)",
              "Licenciamento"],
             ["5", "Diametro de agua fria do chuveiro (DN50 na tabela — verificar troca de ramal)",
              "Hidraulica"],
             ["6", "Regulamento especifico do condominio", "Fachada, muros e recuos"],
             ["7", "Divergencia geometrica R32 x Lista Consolidada (ver prancha de divergencias)",
              "Coordenacao geral"],
             ["8", "Exigencia municipal de retencao pluvial no lote — se houver, volume separado",
              "Drenagem"]],
            larguras=[10, 156, 76])

    cv.texto_p((35, 380), "PRECEDENCIA DE DADOS", TXT["peq"], "start", peso="bold")
    for i, t in enumerate([
        "1. A Lista Consolidada (pos-R32) prevalece sobre o Guia Explicativo R32 em toda divergencia geometrica.",
        "2. Onde a Lista e omissa, adota-se a R32 e marca-se o item como (H).",
        "3. Onde ambas divergem de norma, prevalece a norma e registra-se a excecao.",
        "4. Nenhuma peca entra em nesting sem codigo, largura, altura, espessura, material e revisao.",
    ]):
        cv.texto_p((35, 388 + i * 5), t, TXT["min"], "start")
    return cv
