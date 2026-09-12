"""
ETAPA 4 — FECHAMENTO E EMISSAO.

Acabamentos por ambiente, locacao de obra, paisagismo e irrigacao, e o quadro
final de emissao com o indice do caderno, o historico de revisoes e as
pendencias que permanecem abertas.
"""
from __future__ import annotations

import math

import projeto as pj
import elementos as el
import especificacao as ep
import auditoria as au
import anotacao as an
from core import P, Canvas, View, TXT, CINZA, PRETO
from pranchas import base, _tabela, TOTAL_PRANCHAS
from pranchas6 import _fundo


# =========================================================================
# PR-30 — ACABAMENTOS POR AMBIENTE
# =========================================================================
def acabamentos() -> Canvas:
    acab = pj.acabamentos()
    cv = base("ACABAMENTOS POR AMBIENTE", "s/ escala", "30", notas=[
        "Quadro DERIVADO das decisoes anteriores: zonas de paginacao, forros "
        "acusticos, alturas de revestimento e categoria de uso.",
        "Lista paralela de acabamento e a campea de divergencia em obra — e a "
        "ultima a ser feita e a primeira a ser esquecida quando algo muda.",
        f"Rodape {pj.RODAPE['h']} mm; em area molhada, recortado da propria peca "
        f"do piso.",
        f"Forro de banho rebaixado a {pj.FORRO_H['banho']} mm: e por ali que passam "
        f"dreno do ar, exaustao e luminaria embutida.",
    ])
    linhas = []
    for a in acab:
        linhas.append([a["amb"], a["nome"][:22], a["cat"],
                       f"{a['area']:.2f}".replace(".", ","), a["piso"][:44],
                       a["parede"][:54], a["forro"][:40], f"{a['forro_h']}",
                       a["rodape"][:30], a["zona"]])
    _tabela(cv, (35, 44), "QUADRO DE ACABAMENTOS",
            ["AMB", "AMBIENTE", "CATEGORIA", "AREA", "PISO", "PAREDE", "FORRO",
             "FORRO h", "RODAPE", "ZONA"], linhas,
            larguras=[16, 48, 24, 18, 86, 106, 80, 20, 58, 18])

    _tabela(cv, (35, 200), "DE ONDE VEM CADA ACABAMENTO",
            ["ACABAMENTO", "DERIVADO DE", "REGRA"],
            [["Piso ceramico", "ZONAS_PAGINACAO + CATEGORIA",
              f"{pj.PECA_PISO['tipo']}; antiderrapante R10 em molhado e R11 em servico"],
             ["Piso cimenticio", "zona de paginacao monolitica",
              "garagem e oficina: abrasao, oleo e carga de roda"],
             ["Revestimento de parede", "alturas_revestimento()",
              "altura multipla da peca, para a fiada do topo sair inteira"],
             ["Forro", "FORROS (desempenho acustico)",
              "forro absorvente so onde a reverberacao exige — 30,24 m2 no gourmet"],
             ["Forro rebaixado", f"FORRO_H = {pj.FORRO_H['banho']} mm no banho",
              "unico lugar onde dreno, exaustao e luminaria embutida cabem sem shaft"],
             ["Rodape", "condicao de umidade do ambiente",
              "em LSF o rodape de gesso nao perdoa respingo: em molhado, porcelanato"],
             ["Pintura", "PINTURA por exposicao",
              "acrilico com biocida em area umida; elastomerico na fachada"]],
            larguras=[48, 66, 160])

    _tabela(cv, (35, 270), "ESPECIFICACOES COMPLEMENTARES",
            ["ITEM", "ESPECIFICACAO"],
            [["Pintura interna", pj.PINTURA["interna"]],
             ["Pintura de area umida", pj.PINTURA["umida"]],
             ["Pintura externa", pj.PINTURA["externa"]],
             ["Pintura de forro", pj.PINTURA["forro"]],
             ["Rodape padrao", pj.RODAPE["tipo"]],
             ["Rodape de area molhada", pj.RODAPE["molhado"]],
             ["Soleira interna", pj.SOLEIRAS["interna"]],
             ["Soleira de area molhada", pj.SOLEIRAS["molhada"]],
             ["Soleira externa", pj.SOLEIRAS["externa"]],
             ["Peca de piso", pj.PECA_PISO["tipo"]],
             ["Peca de parede", pj.PECA_PAREDE["tipo"]],
             ["Junta de assentamento", f"{pj.PECA_PISO['junta']} mm, rejunte "
              f"epoxi em area molhada e acrilico nas demais"]],
            larguras=[56, 218])
    return cv


# =========================================================================
# PR-31 — LOCACAO DE OBRA
# =========================================================================
def locacao() -> Canvas:
    cantos = pj.cantos_locacao()
    cv = base("LOCACAO DE OBRA E GABARITO", "1:100", "31", notas=[
        "Locacao e o unico desenho em que o erro nao tem conserto barato: a casa "
        "sai do lugar.",
        "Cada canto e cotado das DUAS divisas, nunca em cadeia acumulada — erro de "
        "cadeia soma, erro de referencia independente nao.",
        f"Conferencia obrigatoria pela diagonal: {cantos[0]['diagonal']:.1f} mm entre "
        f"A e C antes de concretar o radier.",
        pj.RN["descricao"],
    ])
    vw = View(100, 60, 150, 0, 0)
    an.titulo_desenho(cv, (50, 520), "1", "LOCACAO — EIXOS E COORDENADAS", "1:100")
    L, Pf = pj.LOTE_L, pj.LOTE_P
    cv.poli_p([vw.pt(P(0, 0)), vw.pt(P(L, 0)), vw.pt(P(L, Pf)), vw.pt(P(0, Pf))],
              "corte", fechado=True, preenche="#fdfdfd")
    # recuos
    pat = cv.hachura("rec31", espac=1.8, ang=45, w=0.05, cor="#e0a")
    cv.poli_p([vw.pt(P(0, 0)), vw.pt(P(L, 0)), vw.pt(P(L, pj.RECUO_FRENTE)),
               vw.pt(P(0, pj.RECUO_FRENTE))], "cota", fechado=True,
              preenche=f"url(#{pat})", cor="#e0a")
    # eixos de locacao
    for x in pj.EIXOS_LOCACAO["x"]:
        cv.linha_p(vw.pt(P(x, 0)), vw.pt(P(x, Pf)), "cota", cor="#9cf")
        c = vw.pt(P(x, 0))
        cv.circ_p((c[0], c[1] + 5), 2.4, "fino", preenche="#fff", cor="#06c")
        cv.texto_p((c[0], c[1] + 5.8), str(pj.EIXOS_LOCACAO["x"].index(x) + 1),
                   TXT["micro"], "middle", cor="#06c")
    for i, y in enumerate(pj.EIXOS_LOCACAO["y"]):
        cv.linha_p(vw.pt(P(0, y)), vw.pt(P(L, y)), "cota", cor="#9cf")
        c = vw.pt(P(0, y))
        cv.circ_p((c[0] - 5, c[1]), 2.4, "fino", preenche="#fff", cor="#06c")
        cv.texto_p((c[0] - 5, c[1] + 0.8), chr(65 + i), TXT["micro"], "middle",
                   cor="#06c")
    _fundo(cv, vw, "T")
    # gabarito
    g = pj.GABARITO["afastamento"]
    x0 = min(c["x"] for c in cantos) - g
    x1 = max(c["x"] for c in cantos) + g
    y0 = min(c["y"] for c in cantos) - g
    y1 = max(c["y"] for c in cantos) + g
    cv.poli_p([vw.pt(P(x0, y0)), vw.pt(P(x1, y0)), vw.pt(P(x1, y1)), vw.pt(P(x0, y1))],
              "oculto", fechado=True, preenche="none", cor="#b5651d")
    cv.texto_p(vw.pt(P((x0 + x1) / 2, y0 - 400)),
               f"GABARITO — {pj.GABARITO['afastamento']} mm de afastamento",
               TXT["micro"], "middle", cor="#b5651d")
    # cantos e diagonal
    for c in cantos:
        p = vw.pt(P(c["x"], c["y"]))
        cv.circ_p(p, 3.0, "corte", preenche="#fff", cor="#c00")
        cv.texto_p((p[0], p[1] + 0.9), c["canto"], TXT["min"], "middle", cor="#c00")
    cv.linha_p(vw.pt(P(cantos[0]["x"], cantos[0]["y"])),
               vw.pt(P(cantos[2]["x"], cantos[2]["y"])), "cota", cor="#c00")
    mid = vw.pt(P((cantos[0]["x"] + cantos[2]["x"]) / 2,
                  (cantos[0]["y"] + cantos[2]["y"]) / 2))
    cv.texto_p((mid[0] + 3, mid[1]), f"diagonal {cantos[0]['diagonal']:.1f}",
               TXT["micro"], "start", cor="#c00")
    # RN
    rn = vw.pt(P(pj.LOTE_L / 2, 600))
    cv.poli_p([(rn[0], rn[1]), (rn[0] - 3, rn[1] + 5), (rn[0] + 3, rn[1] + 5)],
              "corte", fechado=True, preenche="#000")
    cv.texto_p((rn[0] + 5, rn[1] + 4), "RN +0,00", TXT["micro"], "start")
    an.cadeia(cv, vw, [0, 2_400, 16_800, L], 0, "H", 14)
    an.cadeia(cv, vw, [0, 7_200, 27_600, Pf], 0, "V", -14)
    an.norte(cv, (280, 120), 8, pj.NORTE_EM_PLANTA)

    linhas = []
    for c in cantos:
        linhas.append([c["canto"], f"{c['x']}", f"{c['y']}",
                       f"{c['da_divisa_sul']}", f"{c['da_divisa_norte']}",
                       f"{c['da_testada']}", f"{c['do_fundo']}",
                       f"{c['diagonal']:.1f}".replace(".", ",")])
    _tabela(cv, (320, 150), "COORDENADAS DOS CANTOS (mm)",
            ["CANTO", "X", "Y", "DIVISA SUL", "DIVISA NORTE", "TESTADA", "FUNDO",
             "DIAGONAL"], linhas, larguras=[22, 24, 24, 32, 36, 28, 24, 30])

    _tabela(cv, (320, 210), "PROCEDIMENTO DE LOCACAO",
            ["#", "PASSO", "CRITERIO DE ACEITE"],
            [["1", "Conferir as divisas com a matricula e o memorial do lote",
              "divergencia acima de 50 mm interrompe a locacao"],
             ["2", f"Implantar o RN: {pj.RN['amarracao']}", "fora da area de obra"],
             ["3", f"Montar o gabarito a {pj.GABARITO['afastamento']} mm do contorno",
              pj.GABARITO["madeira"]],
             ["4", "Marcar os eixos X (1 a 8) e Y (A a H) no gabarito",
              "toda coordenada multipla de 300 mm"],
             ["5", "Cotar cada canto das DUAS divisas",
              "nunca em cadeia: erro de cadeia soma"],
             ["6", "Conferir a diagonal A-C", f"{cantos[0]['diagonal']:.1f} mm "
              "com tolerancia de 10 mm"],
             ["7", "Conferir esquadro por 3-4-5 em cada canto",
              "antes de qualquer concretagem"],
             ["8", "Registrar em ata com foto e medida", pj.GABARITO["obs"][:52]]],
            larguras=[12, 112, 106])

    _tabela(cv, (320, 290), "EIXOS MODULARES",
            ["DIRECAO", "EIXOS (mm)"],
            [["X (1 a 8)", "  ·  ".join(str(v) for v in pj.EIXOS_LOCACAO["x"])],
             ["Y (A a H)", "  ·  ".join(str(v) for v in pj.EIXOS_LOCACAO["y"])],
             ["Malha", f"principal {pj.GRID} mm · subgrid {pj.SUBGRID} mm"],
             ["Origem", pj.EMISSAO["origem"]],
             ["Unidade", pj.EMISSAO["unidade"]]],
            larguras=[30, 200])
    return cv


# =========================================================================
# PR-32 — PAISAGISMO E IRRIGACAO
# =========================================================================
def paisagismo() -> Canvas:
    ir = pj.IRRIGACAO
    bal = pj.balanco_pluvial()
    cv = base("PAISAGISMO E IRRIGACAO", "1:100", "32", notas=[
        "Paisagismo aqui e a ultima camada do projeto termico: a arvore sombreia "
        "ANTES de o sol chegar na parede, e transpira em vez de reirradiar.",
        "Em faixa de 1.800 mm nao cabe arvore: a copa invade o vizinho e a raiz "
        "encontra o radier. Ali a sombra vem de trelica e sebe.",
        f"Irrigacao: {ir['sistema']}, {ir['setores']} setores, "
        f"{pj.demanda_irrigacao_ldia()} L/dia em media.",
        f"Fonte: {ir['fonte']}",
    ])
    vw = View(100, 60, 150, 0, 0)
    an.titulo_desenho(cv, (50, 520), "1", "PAISAGISMO — IMPLANTACAO", "1:100")
    L, Pf = pj.LOTE_L, pj.LOTE_P
    cv.poli_p([vw.pt(P(0, 0)), vw.pt(P(L, 0)), vw.pt(P(L, Pf)), vw.pt(P(0, Pf))],
              "fino", fechado=True, preenche="#fdfdfd", cor="#ccc")
    pat = cv.hachura("grama", espac=2.2, ang=0, w=0.05, cor="#0a6")
    for a in pj.TERREO_ABERTO:
        if not a.cod.startswith("T-J"):
            continue
        cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                   vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                  "fino", fechado=True, preenche=f"url(#{pat})", cor="#0a6")
    _fundo(cv, vw, "T")
    # especies
    for p in pj.PAISAGISMO:
        amb = next((a for a in pj.TERREO_ABERTO if a.cod == p["amb"]), None)
        if amb is None:
            continue
        porte = p["porte"]
        grande = any(t in porte for t in ("8 a", "6 a", "10 a"))
        r = vw.d(4_000 if grande else 1_200) / 2
        c = vw.pt(P(amb.cx, amb.cy))
        cv.circ_p(c, r, "vista" if grande else "cota", preenche="none",
                  cor="#0a6" if grande else "#6c6")
        cv.circ_p(c, 1.2, "corte", preenche="#0a6", cor="#0a6")
        cv.texto_p((c[0], c[1] - r - 1.5), p["cod"], TXT["micro"], "middle", cor="#064")
    # setores de irrigacao
    setores = [("S1", "T-JFU"), ("S2", "T-JS2"), ("S3", "T-JN3")]
    for nome, cod in setores:
        amb = next((a for a in pj.TERREO_ABERTO if a.cod == cod), None)
        if amb is None:
            continue
        c = vw.pt(P(amb.x + 400, amb.y + 400))
        cv.poli_p([(c[0] - 3, c[1] - 2.4), (c[0] + 3, c[1] - 2.4),
                   (c[0] + 3, c[1] + 2.4), (c[0] - 3, c[1] + 2.4)], "vista",
                  fechado=True, preenche="#e8f4fb", cor="#06c")
        cv.texto_p((c[0], c[1] + 0.8), nome, TXT["micro"], "middle", cor="#06c")
    # reservatorio de reuso
    tc = next(t for t in pj.TECNICOS if "pluvial" in t["nome"].lower())
    c = vw.pt(P(tc["x"] + tc["w"] / 2, tc["y"] + tc["h"] / 2))
    cv.circ_p(c, 3.4, "corte", preenche="#e8f4fb", cor="#06c")
    cv.texto_p((c[0], c[1] + 0.9), "TC-03", TXT["micro"], "middle", cor="#06c")
    an.norte(cv, (280, 120), 8, pj.NORTE_EM_PLANTA)

    linhas = []
    for p in pj.PAISAGISMO:
        amb = next((a for a in pj.TERREO_ABERTO if a.cod == p["amb"]), None)
        linhas.append([p["cod"], p["amb"], p["especie"][:38], p["porte"][:22],
                       str(p["qtd"]), p["funcao"][:56], p["raiz"][:34],
                       f"{p['afast_min']}",
                       f"{min(amb.w, amb.h)}" if amb else "—"])
    _tabela(cv, (320, 150), "ESPECIES E FUNCAO",
            ["COD", "AMB", "ESPECIE", "PORTE", "QTD", "FUNCAO", "RAIZ",
             "AFAST (mm)", "CANTEIRO"], linhas,
            larguras=[16, 18, 72, 44, 14, 104, 62, 26, 26])

    _tabela(cv, (320, 245), "IRRIGACAO",
            ["ITEM", "VALOR", "RAZAO"],
            [["Sistema", ir["sistema"], "autocompensante mantem vazao igual em "
              "toda a linha, inclusive em declive"],
             ["Setores", f"{ir['setores']} x {ir['vazao_setor_lh']} L/h",
              "setorizar permite regar sombra e sol em tempos diferentes"],
             ["Tempo e frequencia", f"{ir['tempo_min']} min, {ir['frequencia']}",
              "rega profunda e espacada cria raiz funda; rega diaria cria raiz rasa"],
             ["Demanda media", f"{pj.demanda_irrigacao_ldia()} L/dia",
              "antes era estimativa de 100 L/dia; agora e consequencia dos setores"],
             ["Fonte", ir["fonte"], "gravidade dispensa bomba; filtro evita entupir "
              "gotejador"],
             ["Por que gotejamento", ir["obs"][:72],
              "aspersao perderia metade para evaporacao e molharia a fachada"],
             ["Area de jardim", f"{pj.area_jardim_m2():.2f} m2",
              f"{pj.demanda_irrigacao_ldia()/pj.area_jardim_m2():.2f} L/m2 por dia"]],
            larguras=[38, 88, 134])

    _tabela(cv, (320, 325), "BALANCO DO REUSO — ATUALIZADO",
            ["ITEM", "VALOR"],
            [["Area de captacao (projecao coberta)", f"{bal['area']:.2f} m2"],
             ["Captacao anual liquida", f"{bal['captacao_m3']:.2f} m3"],
             ["Demanda diaria total", f"{bal['demanda_dia']:.1f} L/dia"],
             ["Demanda anual", f"{bal['demanda_ano']:.2f} m3"],
             ["Aproveitamento da chuva captada", f"{bal['aproveitamento']:.0%}"],
             ["Autonomia do reservatorio", f"{bal['autonomia_dias']:.1f} dias"],
             ["Volume adotado", f"{pj.PLUVIAL['volume_l']} L"],
             ["Restricao de uso", pj.PLUVIAL["nao_estender_a"]]],
            larguras=[74, 186])
    return cv


# =========================================================================
# PR-33 — EMISSAO: INDICE, REVISOES E PENDENCIAS
# =========================================================================
INDICE = [
    ("01", "Implantacao e situacao"), ("02", "Planta baixa — terreo"),
    ("03", "Planta baixa — superior"), ("04", "Planta de layout — terreo"),
    ("05", "Planta de cobertura"), ("06", "Cortes AA e BB"),
    ("07", "Fachadas"), ("08", "Croqui axonometrico"),
    ("09", "Quadros gerais e pendencias"), ("10", "Detalhes construtivos"),
    ("11", "Desempenho termico e acustico"), ("12", "Mapa de familias de vedacao"),
    ("13", "Especificacao por exigencia"), ("14", "Auditoria do modelo"),
    ("15", "Elevacoes internas"), ("16", "Planta de forro e iluminacao"),
    ("17", "Acessibilidade e fluxos"), ("18", "Paginacao de paineis LSF"),
    ("19", "Estudo de insolacao"), ("20", "Interface LSF x perfil laminado"),
    ("21", "Plano de furacao e penetracoes"), ("22", "Ampliacoes molhadas — terreo"),
    ("23", "Ampliacoes molhadas — superior"), ("24", "Paginacao de piso"),
    ("25", "Escada executiva"), ("26", "Instalacoes hidrossanitarias"),
    ("27", "Eletrica, iluminacao e dados"), ("28", "Climatizacao — linhas e dutos"),
    ("29", "Drenagem pluvial e de piso"), ("30", "Acabamentos por ambiente"),
    ("31", "Locacao de obra e gabarito"), ("32", "Paisagismo e irrigacao"),
    ("33", "Emissao: indice, revisoes e pendencias"),
]
ETAPA_DE = {**{n: "estudo (R00)" for n, _ in INDICE[:19]},
            **{n: "Etapa 2 (R03)" for n, _ in INDICE[19:25]},
            **{n: "Etapa 3 (R04)" for n, _ in INDICE[25:29]},
            **{n: "Etapa 4 (R05)" for n, _ in INDICE[29:]}}

PENDENCIAS = [
    ("1", "Certidao oficial do SU16 (CAMT, taxa de ocupacao, gabarito)",
     "Lei 1.838/2014", "Condiciona toda a implantacao", "ABERTA"),
    ("2", "Sondagem do solo e calculo definitivo do radier", "NBR 6122",
     "Fundacao", "ABERTA"),
    ("3", "Calculo estrutural do hibrido LSF + laminado, com ART",
     "NBR 8800 / 14762", "Estrutura; o pre-dimensionamento por flecha nao "
     "substitui verificacao de flambagem lateral", "ABERTA"),
    ("4", "Verificacao ambiental do reuso pluvial",
     "Codigo Ambiental de Manaus", "Licenciamento", "ABERTA"),
    ("5", "Exigencia municipal de retencao pluvial no lote",
     "a confirmar", "Se houver, volume separado do reuso", "ABERTA"),
    ("6", "Regulamento especifico do condominio", "—",
     "Fachada, muros, recuos e especie vegetal", "ABERTA"),
    ("7", "Padrao de entrada de energia trifasico", "NT Amazonas Energia",
     "Confirmar disponibilidade de trifasico no ramal", "ABERTA"),
    ("8", "Nesting codificado dos paineis LSF", "fabricante",
     "A paginacao atual e de estudo, nao de corte", "ABERTA"),
    ("9", "Divergencia geometrica R32 x Lista Consolidada", "briefing",
     "Documentada em docs/DIVERGENCIAS.md", "RESOLVIDA"),
    ("10", "Climatizacao da fita social", "decisao do proprietario",
     "Resolvida por zona com fronteira aerodinamica (R02)", "RESOLVIDA"),
]


def emissao() -> Canvas:
    met = au.metrica()
    achados = au.auditar()
    n = {k: sum(1 for a in achados if a.nivel == k)
         for k in ("ERRO", "ATENCAO", "NOTA")}
    em = pj.EMISSAO
    cv = base("EMISSAO — INDICE, REVISOES E PENDENCIAS", "s/ escala", "33", notas=[
        f"Revisao {em['revisao']} — finalidade: {em['finalidade']}.",
        f"Auditoria: {met['funcoes']} verificacoes e {met['condicoes']} condicoes; "
        f"{n['ERRO']} erro(s), {n['ATENCAO']} atencao(oes), {n['NOTA']} nota(s).",
        "NAO serve para: " + "; ".join(em["nao_serve_para"]) + ".",
        "Reproduzivel integralmente por 'python3 build.py' a partir do modelo.",
    ])
    meio = len(INDICE) // 2 + 1
    for col, (ox, bloco) in enumerate(((35, INDICE[:meio]), (300, INDICE[meio:]))):
        _tabela(cv, (ox, 44), "INDICE DO CADERNO" if col == 0 else "INDICE (cont.)",
                ["PR", "PRANCHA", "ETAPA"],
                [[num, nome, ETAPA_DE[num]] for num, nome in bloco],
                larguras=[14, 130, 44])

    _tabela(cv, (35, 200), "HISTORICO DE REVISOES",
            ["REV", "CONTEUDO"],
            [[r, c] for r, c in pj.REVISOES], larguras=[18, 242])

    _tabela(cv, (35, 260), "PENDENCIAS",
            ["#", "PENDENCIA", "REFERENCIA", "IMPACTO", "SITUACAO"],
            [list(p) for p in PENDENCIAS],
            larguras=[10, 104, 46, 118, 26])

    linhas = []
    for fn in au.verificacoes():
        achs = fn()
        linhas.append([fn.__name__.replace("checar_", ""),
                       str(len(achs)),
                       str(sum(1 for a in achs if a.nivel == "ERRO")),
                       str(sum(1 for a in achs if a.nivel == "ATENCAO")),
                       str(sum(1 for a in achs if a.nivel == "NOTA"))])
    _tabela(cv, (35, 350), f"AUDITORIA FINAL — {met['funcoes']} VERIFICACOES, "
            f"{met['condicoes']} CONDICOES",
            ["VERIFICACAO", "ACHADOS", "ERRO", "ATENCAO", "NOTA"], linhas,
            larguras=[56, 24, 18, 24, 18])

    _tabela(cv, (300, 350), "O QUE ESTE CADERNO E, E O QUE NAO E",
            ["AFIRMACAO", "DESENVOLVIMENTO"],
            [["E um modelo, nao um conjunto de desenhos",
              "as 33 pranchas sao vistas de uma unica fonte: mudar o modelo muda "
              "todas as pranchas, e a auditoria roda sobre a fonte, nao sobre o traco"],
             ["E auditavel por construcao",
              f"{met['condicoes']} condicoes verificaveis; o que nao esta no modelo a "
              f"auditoria nao alcanca, e foi exatamente assim que os 9 defeitos "
              f"documentados apareceram"],
             ["Especifica por demanda, nao por catalogo",
              "7,80 m2 de parede acustica premium na casa inteira; 2 de 29 vaos com "
              "vidro acustico; forro absorvente so no gourmet"],
             ["NAO e projeto legal",
              "nao substitui ART/RRT, calculo estrutural, sondagem nem aprovacao "
              "municipal"],
             ["NAO libera fabricacao",
              "a paginacao de paineis e de estudo: falta nesting codificado do "
              "fabricante"],
             ["Hipoteses estao marcadas (H)",
              "parametros urbanisticos do SU16, tensao admissivel do solo e "
              "intensidade pluviometrica de projeto seguem como hipotese"]],
            larguras=[58, 202])
    return cv
