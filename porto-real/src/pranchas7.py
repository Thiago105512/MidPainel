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
    vw = View(100, 60, 480, 0, 0)
    an.titulo_desenho(cv, (50, 512), "1", "LOCACAO — EIXOS E COORDENADAS", "1:100")
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
    an.cadeia(cv, vw, [0, pj.RECUO_ESQ, 16_800, L], 0, "H", 14)
    an.cadeia(cv, vw, [0, pj.RECUO_FRENTE, 27_600, Pf], 0, "V", -14)
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
    cv = base("PAISAGISMO E IRRIGACAO", "1:100", "32", notas=[
        "Paisagismo aqui e a ultima camada do projeto termico: a arvore sombreia "
        "ANTES de o sol chegar na parede, e transpira em vez de reirradiar.",
        "Em faixa de 1.800 mm nao cabe arvore: a copa invade o vizinho e a raiz "
        "encontra o radier. Ali a sombra vem de trelica e sebe.",
        f"Irrigacao: {ir['sistema']}, {ir['setores']} setores, "
        f"{pj.demanda_irrigacao_ldia()} L/dia em media.",
        f"Fonte: {ir['fonte']}",
    ])
    vw = View(100, 60, 480, 0, 0)
    an.titulo_desenho(cv, (50, 512), "1", "PAISAGISMO — IMPLANTACAO", "1:100")
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
    # reservatorio de retencao (era de reuso ate R51)
    tc = next(t for t in pj.TECNICOS if t["cod"] == "TC-03")
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

    import nucleo.pluvial as plv
    bl, gt_, vz, rt = (plv.balanco(pj), plv.gatilho_legal(pj),
                       plv.vazoes(pj), plv.retencao(pj))
    _tabela(cv, (320, 325), "RETENCAO PLUVIAL — R52 (o reuso foi encerrado)",
            ["ITEM", "VALOR"],
            [["Superficies declaradas do lote",
              f"{len(bl['superficies'])} classes somando {bl['total']:.2f} m2 "
              f"de {bl['lote']:.0f} m2"],
             ["Area impermeabilizada",
              f"{bl['impermeavel']:.2f} m2 "
              f"({bl['taxa_impermeabilizacao']*100:.2f} % do lote)"],
             ["Lei 1.192/2007 (Pro-Aguas)",
              f"obriga acima de {gt_['limite_m2']:.0f} m2 — "
              + ("OBRIGA" if gt_["obriga"] else
                 f"nao obriga (folga de {gt_['folga']:.2f} m2)")],
             ["C do terreno natural / construido",
              f"{bl['c_pre']:.2f} | {bl['c_ponderado']:.4f}"],
             ["Vazao para a rua antes / depois",
              f"{vz['q_pre_ls']:.2f} | {vz['q_pos_ls']:.2f} L/s "
              f"({vz['razao']:.2f}x)"],
             ["Volume de retencao",
              f"{rt['volume_m3']:.2f} m3 = excedente de "
              f"{vz['excedente_ls']:.2f} L/s durante "
              f"{rt['tempo_concentracao_min']:.0f} min"],
             ["Orificio de descarga",
              f"DN {rt['orificio_mm']:.0f} mm, calibrado na vazao de "
              f"pre-ocupacao; esvazia em {rt['esvaziamento_min']:.0f} min"],
             ["Por que nao ha mais reuso", pj.PLUVIAL["reuso"]]],
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
    ("34", "Piscina, deck e fachada (R06)"),
    ("35", "Eixo social e cortina de vidro (R07)"),
    ("36", "Catalogo tecnico de pecas (R51)"),
    ("37", "Sondagem SPT e fundacao (R52)"),
    ("38", "Retencao pluvial e superficies do lote (R52)"),
    ("39", "Desempenho acustico entre ambientes (R52)"),
    ("40", "Cargas, equilibrio de fases e mercado (R52)"),
    ("41", "Energia: fotovoltaica, SPDA e vidro solar (R61)"),
    ("42", "Planta de layout — superior (R65)"),
    ("43", "Perspectivas externas (R66)"),
    ("44", "Perspectivas internas — terreo (R66)"),
    ("45", "Perspectivas — areas abertas (R66)"),
    ("46", "Perspectivas internas — superior (R66)"),
    ("47", "Terreno: perfil, plataforma e cotas (R68)"),
    ("48", "Matriz de entregaveis — prancha mestre (R69)"),
    ("49", "Ventilacao natural e privacidade (R69)"),
]
ETAPA_DE = {**{n: "estudo (R00)" for n, _ in INDICE[:19]},
            **{n: "Etapa 2 (R03)" for n, _ in INDICE[19:25]},
            **{n: "Etapa 3 (R04)" for n, _ in INDICE[25:29]},
            **{n: "Etapa 4 (R05)" for n, _ in INDICE[29:33]},
            **{n: "R06" for n, _ in INDICE[33:34]},
            **{n: "R07" for n, _ in INDICE[34:]}}

# A lista mora no CASO desde R39. Aqui so se le: enquanto ela vivia neste
# modulo de desenho, o checklist de liberacao nao tinha como consulta-la — e
# por isso podia anunciar fabricacao liberada com duas pendencias trancando
# exatamente a fabricacao.
PENDENCIAS = [(d["n"], d["titulo"], d["norma"], d["impacto"], d["status"])
              for d in pj.PENDENCIAS]


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
            # R52 — o texto de revisao cresceu ate quebrar a folha: a tabela
            # partiu em duas colunas e a segunda caiu 804 mm fora da moldura.
            # O caderno mostra a LINHA da revisao; o texto inteiro vive em
            # REVISOES e chega ao leitor pelo visualizador, que rola.
            [[r, (c if len(c) <= 300 else c[:297].rsplit(" ", 1)[0] + " …")]
             for r, c in pj.REVISOES], larguras=[18, 242])

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


# =========================================================================
# PR-34 — PISCINA, DECK E FACHADA (revisao R06)
# =========================================================================
def piscina_deck_fachada() -> Canvas:
    p, ps, dk = pj.PISCINA, pj.PISCINA_SISTEMA, pj.DECK
    cv = base("PISCINA, DECK E FACHADA — REVISAO R06", "indicada", "34", notas=[
        f"Piscina {p['w']/1000:.2f} x {p['h']/1000:.2f} m = {p['lamina_m2']:.2f} m2 "
        f"de lamina, {p['volume_m3']:.2f} m3. O YAML fixa 5,50 x 3,20; adotado "
        f"modular sobre a malha de 300 mm.".replace(".", ","),
        f"Faixa seca perimetral minima {p['faixa_seca_min']} mm, verificada nos "
        f"quatro lados.",
        f"Recirculacao {pj.vazao_recirculacao_m3h()} m3/h para renovar o volume em "
        f"{ps['renovacao_h']} h.".replace(".", ","),
        "Fachada: tres familias de material, confirmadas pela referencia visual; "
        "a novidade e o rasgo de luz indireto.",
    ])

    # ---------------- planta da piscina 1:50
    vw = View(50, 45, 160, dk["x"] - 600, dk["y"] - 600)
    an.titulo_desenho(cv, (35, 290), "1", "PISCINA E DECK", "1:50")
    cv.poli_p([vw.pt(P(dk["x"], dk["y"])), vw.pt(P(dk["x"] + dk["w"], dk["y"])),
               vw.pt(P(dk["x"] + dk["w"], dk["y"] + dk["h"])),
               vw.pt(P(dk["x"], dk["y"] + dk["h"]))], "vista", fechado=True,
              preenche="#f3efe6", cor="#a89")
    cv.poli_p([vw.pt(P(p["x"], p["y"])), vw.pt(P(p["x"] + p["w"], p["y"])),
               vw.pt(P(p["x"] + p["w"], p["y"] + p["h"])),
               vw.pt(P(p["x"], p["y"] + p["h"]))], "corte", fechado=True,
              preenche="#e8f4fb", cor="#06c")
    # prainha e banco
    cv.poli_p([vw.pt(P(p["x"], p["y"])), vw.pt(P(p["x"] + p["prainha_w"], p["y"])),
               vw.pt(P(p["x"] + p["prainha_w"], p["y"] + p["h"])),
               vw.pt(P(p["x"], p["y"] + p["h"]))], "fino", fechado=True,
              preenche="#d6ecf8", cor="#06c")
    cv.texto_p(vw.pt(P(p["x"] + p["prainha_w"] / 2, p["y"] + p["h"] / 2)),
               f"PRAINHA {p['prof_prainha']}", TXT["micro"], "middle", rot=90, cor="#06c")
    cv.poli_p([vw.pt(P(p["x"] + p["w"] - p["banco_w"], p["y"])),
               vw.pt(P(p["x"] + p["w"], p["y"])),
               vw.pt(P(p["x"] + p["w"], p["y"] + p["h"])),
               vw.pt(P(p["x"] + p["w"] - p["banco_w"], p["y"] + p["h"]))],
              "oculto", fechado=True, preenche="none", cor="#06c")
    cv.texto_p(vw.pt(P(p["x"] + p["w"] - p["banco_w"] / 2, p["y"] + p["h"] / 2)),
               "BANCO", TXT["micro"], "middle", rot=90, cor="#06c")
    cv.texto_p(vw.pt(P(p["x"] + p["w"] / 2, p["y"] + p["h"] / 2)),
               f"{p['lamina_m2']:.2f} m2  ·  prof. {p['prof_principal']} mm"
               .replace(".", ","), TXT["min"], "middle", cor="#06c")
    # pontos hidraulicos
    for i in range(ps["retornos"]):
        x = p["x"] + p["w"] * (i + 0.5) / ps["retornos"]
        _simb(cv, vw, x, p["y"] + 80, "R", "#06c")
    for i in range(ps["drenos_fundo"]):
        x = p["x"] + p["prainha_w"] + (p["w"] - p["prainha_w"]) * (0.3 + 0.4 * i)
        _simb(cv, vw, x, p["y"] + p["h"] / 2, "D", "#039")
    _simb(cv, vw, p["x"] + p["w"] - 200, p["y"] + p["h"] - 200, "S", "#06c")
    for i in range(ps["leds"]):
        y = p["y"] + p["h"] * (i + 0.5) / ps["leds"]
        _simb(cv, vw, p["x"] + p["w"] - 80, y, "L", "#e0a")
    # faixa seca cotada
    an.cadeia(cv, vw, [dk["x"], p["x"], p["x"] + p["w"], dk["x"] + dk["w"]],
              dk["y"], "H", 12)
    an.cadeia(cv, vw, [dk["y"], p["y"], p["y"] + p["h"], dk["y"] + dk["h"]],
              dk["x"], "V", -12)
    # casa de maquinas na faixa tecnica
    cm = next(t for t in pj.TECNICOS if t.get("casa_maquinas"))
    cv.poli_p([vw.pt(P(cm["x"], cm["y"])), vw.pt(P(cm["x"] + cm["w"], cm["y"])),
               vw.pt(P(cm["x"] + cm["w"], cm["y"] + cm["h"])),
               vw.pt(P(cm["x"], cm["y"] + cm["h"]))], "corte", fechado=True,
              preenche="#fff3d6", cor="#b5651d")
    cv.texto_p(vw.pt(P(cm["x"] + cm["w"] / 2, cm["y"] + cm["h"] / 2)), "TC-13",
               TXT["micro"], "middle", rot=90, cor="#b5651d")
    cv.linha_p(vw.pt(P(p["x"] + p["w"], p["y"] + p["h"] / 2)),
               vw.pt(P(cm["x"], cm["y"] + cm["h"] / 2)), "cota", cor="#b5651d")
    meio = vw.pt(P((p["x"] + p["w"] + cm["x"]) / 2, p["y"] + p["h"] / 2 - 200))
    cv.texto_p(meio, f"succao {(cm['x']-(p['x']+p['w']))/1000:.1f} m"
               .replace(".", ","), TXT["micro"], "middle", cor="#b5651d")

    _tabela(cv, (300, 44), "PISCINA — GEOMETRIA E SISTEMA",
            ["ITEM", "PROJETO", "ORIGEM / RAZAO"],
            [["Dimensao da lamina", f"{p['w']} x {p['h']} mm",
              "YAML pede 5,50 x 3,20; adotado modular, mesma area util"],
             ["Area / volume", f"{p['lamina_m2']:.2f} m2 / {p['volume_m3']:.2f} m3"
              .replace(".", ","), "volume dentro da faixa de 17 a 19 m3 do YAML"],
             ["Profundidade", f"{p['prof_principal']} mm", "faixa 1,10 a 1,20 do YAML"],
             ["Prainha", f"{p['prainha_w']} mm a {p['prof_prainha']} mm",
              "entrada rasa, area de permanencia de crianca"],
             ["Banco submerso", f"{p['banco_w']} x {p['banco_prof']} mm",
              "borda oposta a prainha, sem reduzir o vao de nado"],
             ["Faixa seca", f"min {p['faixa_seca_min']} mm nos 4 lados",
              "exigencia do YAML, verificada pela auditoria"],
             ["Recirculacao", f"{pj.vazao_recirculacao_m3h()} m3/h em {ps['renovacao_h']} h"
              .replace(".", ","), "bomba de velocidade variavel: gasta menos rodando devagar mais tempo"],
             ["Drenos de fundo", f"{ps['drenos_fundo']} un., antiaprisionamento",
              ps["obs"][:62]],
             ["Retornos / skimmer / aspiracao",
              f"{ps['retornos']} / {ps['skimmers']} / {ps['aspiracao']}",
              "retornos opostos ao skimmer, para varrer a superficie"],
             ["Iluminacao", f"{ps['leds']} LED de {ps['led_w']} W, {ps['led_k']}",
              "luz quente: agua azul com luz fria fica esverdeada"],
             ["Aquecimento", ps["aquecimento"],
              "bypass custa dois registros hoje; abrir piso depois custa a obra"],
             ["Tratamento", ps["tratamento"],
              "sal exige material compativel em TODA a hidraulica; decisao em espera"]],
            larguras=[54, 62, 150])

    _tabela(cv, (300, 160), "DECK — PISO POR ZONA, NAO POR MATERIAL UNICO",
            ["ZONA", "MATERIAL", "RAZAO"],
            [[z["zona"], z["material"], z["razao"]] for z in pj.PISO_EXTERNO] +
            [["Verificacao do YAML", "aquecimento superficial",
              "WPC escuro passa de 65 C sob sol de Manaus (albedo 0,20); "
              "porcelanato claro fica em ~45 C (albedo 0,60); a dor ao pe "
              "descalco comeca em 50 C"]],
            larguras=[54, 62, 150])

    _tabela(cv, (300, 215), "FACHADA — TRES FAMILIAS E O RASGO DE LUZ",
            ["FAMILIA / ELEMENTO", "ESPECIFICACAO", "EFEITO"],
            [[n, d, "—"] for n, d in pj.FACHADA_MATERIAIS] +
            [[f"{i['cod']} — {i['onde']}", i["tipo"], i["efeito"]]
             for i in pj.ILUMINACAO_FACHADA],
            larguras=[54, 78, 134])

    _tabela(cv, (300, 300), "O QUE A REFERENCIA VISUAL CONFIRMOU E O QUE ACRESCENTOU",
            ["LEITURA", "SITUACAO NO PROJETO"],
            [["Composicao horizontal, volumes escalonados",
              "ja era o partido: garagem em um pavimento, portico recuado, corpo "
              "de dois pavimentos atras"],
             ["Revestimento mineral claro de grande formato",
              "familia 1 ja especificada; junta seca de 6 mm mantida"],
             ["Portao e brises ripados em metal escuro",
              "familia 2 ja especificada — e agora tambem sombreia o nicho de "
              "condensadoras, no lugar da trelica vegetal"],
             ["Porta pivotante alta em madeira",
              "familia 3; P01 de 1.100 x 2.800 mm ja previa a folha alta"],
             ["Rasgo de luz indireto sob cada plano",
              "ACRESCENTADO nesta revisao (IF-01 a IF-04): e o que constroi a "
              "horizontalidade a noite"],
             ["Palmeiras de grande porte na entrada",
              "compativel com o paisagismo sem poda; uplight IF-04 previsto"],
             ["Piso claro refletindo a iluminacao",
              "coincide com a decisao tomada por desempenho termico: albedo alto "
              "no piso externo"]],
            larguras=[72, 188])
    return cv


def _simb(cv: Canvas, vw: View, x, y, letra: str, cor: str) -> None:
    c = vw.pt(P(x, y))
    cv.circ_p(c, 2.0, "vista", preenche="#fff", cor=cor)
    cv.texto_p((c[0], c[1] + 0.8), letra, TXT["micro"], "middle", cor=cor)


# =========================================================================
# PR-35 — EIXO SOCIAL: COZINHA, GOURMET, CORTINA DE VIDRO E PISCINA
# =========================================================================
def eixo_social() -> Canvas:
    cvd, vg, ev = pj.CORTINA_VIDRO, pj.VARANDA_GOURMET, pj.eixo_visual()
    cv = base("EIXO SOCIAL — COZINHA, GOURMET, CORTINA DE VIDRO E PISCINA",
              "indicada", "35", notas=[
        f"Cozinha e gourmet sao UM ambiente de {21.60 + 30.24:.2f} m2, sem parede "
        f"entre eles, abrindo por {cvd['largura']} mm de cortina de vidro."
        .replace(".", ","),
        f"Aberta, a cortina deixa {cvd['vao_livre_aberto']} mm livres: as folhas "
        f"giram 90 graus e estacionam de perfil nos nichos das duas pontas.",
        f"Varanda de {vg['prof']} mm em balanco — nenhum pilar entre a mesa e a agua.",
        f"Eixo continuo de {ev['profundidade_total']/1000:.1f} m do estar ao fim da "
        f"piscina, com {ev['desalinhamento']:.0f} mm de desalinhamento."
        .replace(".", ","),
    ])

    # ---------------- planta do eixo 1:75
    vw = View(75, 40, 440, 1_800, 12_600)
    an.titulo_desenho(cv, (30, 462), "1", "PLANTA DO EIXO SOCIAL", "1:75")
    for a in pj.TERREO:
        claro = a.cod in ("T-SOC", "T-COR", "T-GOU", "T-COZ")
        cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                   vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                  "vista", fechado=True,
                  preenche="#eaf4ee" if claro else "#f6f6f6",
                  cor="#0a6a4a" if claro else "#ccc")
        if claro:
            cv.texto_p(vw.pt(P(a.cx, a.cy)), a.nome[:14], TXT["micro"], "middle",
                       cor="#0a6a4a")
    for a in pj.TERREO_ABERTO:
        if a.cod not in ("T-ALP", "T-DKP"):
            continue
        cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                   vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                  "vista", fechado=True, preenche="#f3efe6", cor="#a89")
        cv.texto_p(vw.pt(P(a.cx, a.cy + 600)), a.nome[:16], TXT["micro"], "middle",
                   cor="#a89")
    p = pj.PISCINA
    cv.poli_p([vw.pt(P(p["x"], p["y"])), vw.pt(P(p["x"] + p["w"], p["y"])),
               vw.pt(P(p["x"] + p["w"], p["y"] + p["h"])),
               vw.pt(P(p["x"], p["y"] + p["h"]))], "corte", fechado=True,
              preenche="#e8f4fb", cor="#06c")
    # linha da cortina
    cv.linha_p(vw.pt(P(cvd["x"], cvd["y"])), vw.pt(P(cvd["x"] + cvd["largura"], cvd["y"])),
               "corte", cor="#06c")
    for xa in (cvd["x"], cvd["x"] + cvd["largura"] - cvd["nicho_w"]):
        cv.poli_p([vw.pt(P(xa, cvd["y"] - 100)), vw.pt(P(xa + cvd["nicho_w"], cvd["y"] - 100)),
                   vw.pt(P(xa + cvd["nicho_w"], cvd["y"] + 100)), vw.pt(P(xa, cvd["y"] + 100))],
                  "corte", fechado=True, preenche="#b5651d", cor="#b5651d")
    cv.texto_p(vw.pt(P(cvd["x"] + cvd["largura"] / 2, cvd["y"] - 500)),
               f"CORTINA DE VIDRO CV-01 — {cvd['largura']} mm", TXT["min"],
               "middle", cor="#06c")
    # eixo visual
    ex = ev["eixo_x_social"]
    cv.linha_p(vw.pt(P(ex, 13_200)), vw.pt(P(ex, p["y"] + p["h"])), "cota", cor="#c00")
    for yy, rot in ((19_000, "ESTAR"), (23_000, "GOURMET"), (27_900, "VARANDA"),
                    (32_200, "PISCINA")):
        cv.texto_p(vw.pt(P(ex + 200, yy)), rot, TXT["micro"], "start", cor="#c00")
    an.cadeia(cv, vw, [13_200, 19_200, 26_400, 29_400, 30_600, p["y"] + p["h"]],
              2_400, "V", -14)
    an.cadeia(cv, vw, [2_400, 5_400, 9_600], 13_200, "H", 12)
    an.norte(cv, (200, 120), 7, pj.NORTE_EM_PLANTA)

    # ---------------- corte longitudinal pelo eixo 1:75
    vw2 = View(75, 300, 260, 13_200, 0)
    an.titulo_desenho(cv, (290, 300), "2", "CORTE PELO EIXO — CONTINUIDADE", "1:75")
    piso, teto, laje = 0, pj.PE_DIREITO, pj.PISO_A_PISO
    # piso continuo do estar ate a borda da varanda
    cv.linha_p(vw2.pt(P(13_200, piso)), vw2.pt(P(29_400, piso)), "corte")
    cv.texto_p(vw2.pt(P(28_000, -400)), "PISO CONTINUO, MESMO NIVEL", TXT["micro"],
               "middle", cor="#c00")
    # forro continuo atravessando a cortina
    cv.linha_p(vw2.pt(P(13_200, teto)), vw2.pt(P(29_400, teto)), "vista", cor="#0a6a4a")
    cv.texto_p(vw2.pt(P(28_000, teto + 350)), "FORRO CONTINUO", TXT["micro"],
               "middle", cor="#0a6a4a")
    # laje do superior ate y = 25.200 (master) e cobertura da varanda em balanco
    cv.linha_p(vw2.pt(P(19_200, laje)), vw2.pt(P(25_200, laje)), "corte")
    cv.linha_p(vw2.pt(P(26_400, teto + 300)), vw2.pt(P(29_400, teto + 300)), "corte")
    cv.texto_p(vw2.pt(P(27_900, teto + 700)),
               f"BALANCO {vg['prof']} mm — sem pilar", TXT["micro"], "middle", cor="#b5651d")
    # a cortina em elevacao
    for i in range(cvd["folhas"] + 1):
        yy = 26_400
        cv.linha_p(vw2.pt(P(yy, piso)), vw2.pt(P(yy, cvd["altura"])), "cota", cor="#9cf")
    cv.linha_p(vw2.pt(P(26_400, piso)), vw2.pt(P(26_400, cvd["altura"])), "vista", cor="#06c")
    cv.texto_p(vw2.pt(P(26_400, cvd["altura"] + 350)), "CV-01", TXT["micro"],
               "middle", cor="#06c")
    # piscina em corte
    cv.linha_p(vw2.pt(P(29_400, piso)), vw2.pt(P(p["y"], piso)), "corte")
    cv.poli_p([vw2.pt(P(p["y"], piso)), vw2.pt(P(p["y"] + p["h"], piso)),
               vw2.pt(P(p["y"] + p["h"], -p["prof_principal"])),
               vw2.pt(P(p["y"], -p["prof_principal"]))], "corte", fechado=True,
              preenche="#e8f4fb", cor="#06c")
    an.cadeia(cv, vw2, [13_200, 26_400, 29_400, p["y"], p["y"] + p["h"]], -1_500, "H", 14)

    _tabela(cv, (35, 330), "CORTINA DE VIDRO CV-01",
            ["ITEM", "PROJETO", "RAZAO"],
            [["Largura do vao", f"{cvd['largura']} mm",
              "a parede inteira de cozinha + gourmet, nao um trecho dela"],
             ["Folhas", f"{cvd['folhas']} x {cvd['largura_folha']} mm",
              "soltas, sem montante vertical entre elas"],
             ["Vidro", cvd["vidro"], "sem caixilho aparente na vertical"],
             ["Seguranca", cvd["pelicula"],
              "vidro limpo e invisivel: alguem vai tentar atravessar"],
             ["Recolhimento", cvd["recolhimento"],
              f"aberta sobram {cvd['vao_livre_aberto']} mm livres — e isso que "
              f"separa cortina de porta de correr"],
             ["Nicho", f"{cvd['nicho_w']} x {cvd['nicho_prof']} mm em cada ponta",
              "embutido na parede, folhas estacionadas de perfil"],
             ["Trilho superior", cvd["trilho_sup"],
              "regulagem absorve a flecha residual da verga"],
             ["Trilho inferior", cvd["trilho_inf"],
              "drena para dentro do canal, nunca para o piso interno"],
             ["Verga", "V-10 W310x23,8 · L/700",
              "limite dado pelo TRILHO, nao pelo gesso: 13 mm de flecha travariam "
              "o sistema"],
             ["Uso padrao", cvd["uso_padrao"],
              "fecha em chuva com vento de sudoeste, ausencia e uso do estar "
              "climatizado com a casa vazia"]],
            larguras=[44, 62, 154])

    _tabela(cv, (35, 400), "O QUE A CORTINA NAO E",
            ["NAO SERVE PARA", "CONSEQUENCIA DE PROJETO"],
            [["Estanqueidade ao ar",
              "nao ha borracha de compressao: por isso a zona climatizada e o "
              "ESTAR, com a fronteira aerodinamica, e nao o gourmet"],
             ["Isolamento acustico",
              "vidro monolitico sem vedacao perimetral: o gourmet nunca foi "
              "contado como ambiente de silencio"],
             ["Barreira termica",
              "fechar a cortina nao transforma a varanda em ambiente interno; "
              "a carga termica do projeto nunca contou com isso"]],
            larguras=[54, 206])

    cont = pj.CONTINUIDADE_INTERNO_EXTERNO
    _tabela(cv, (300, 330), "AS TRES MEDIDAS QUE FAZEM A INTEGRACAO FUNCIONAR",
            ["MEDIDA", "PROJETO", "SE ERRAR"],
            [["Desnivel de piso na soleira", f"{cont['desnivel_piso']} mm",
              "qualquer degrau e lido como limite: o olho passa a ver dois "
              "ambientes, nao um"],
             ["Paginacao atravessando a linha",
              "sim — mesma malha ZP-1 dentro e fora",
              "junta desalinhada na soleira denuncia a costura exatamente onde "
              "nao ha parede para disfarcar"],
             ["Forro continuo sobre o trilho", "sim",
              "forro interrompido no vao devolve a leitura de porta"],
             ["Bancada fora da linha da vista",
              "BC-04 foi para a parede leste",
              "a bancada estava encostada no fundo ocupando 3.900 dos 4.200 mm: "
              "era ela, e nao a esquadria, o que tapava a piscina"],
             ["Profundidade da varanda", f"{vg['prof']} mm",
              "com 1.200 mm nao se usa o espaco durante chuva, que era o "
              "objetivo declarado"],
             ["Piscina no eixo", f"{ev['desalinhamento']:.0f} mm de desalinhamento",
              "piscina fora do eixo transforma a abertura em janela para o lado"]],
            larguras=[52, 54, 154])

    _tabela(cv, (300, 415), "O EIXO, EM NUMEROS",
            ["TRECHO", "COTA Y", "PROFUNDIDADE ACUMULADA"],
            [["Inicio do estar", f"{ev['origem_y']} mm", "0"],
             ["Cozinha e gourmet (integrados)", "19.200 mm", "6,00 m"],
             ["Cortina de vidro CV-01", f"{ev['cortina_y']} mm", "13,20 m"],
             ["Borda da varanda coberta", f"{ev['varanda_y']} mm", "16,20 m"],
             ["Borda da piscina", f"{ev['piscina_y']} mm", "17,40 m"],
             ["Fim da piscina", f"{ev['fim_piscina_y']} mm",
              f"{ev['profundidade_total']/1000:.2f} m".replace(".", ",")]],
            larguras=[74, 40, 146])
    return cv


# =========================================================================
# PR-36 — CATALOGO TECNICO: PERFIL, PARAFUSO, CHAPA E TUBO
#
# R51 — o catalogo nasceu em R47 como VISTA DE TELA, e a fabrica recebe o PDF,
# nao a tela. Era o unico sistema levantado no modelo sem prancha que o
# mostrasse — a conferencia de completude do desenho achou exatamente isso.
#
# A secao e desenhada em escala 1:2 a partir da MESMA poligonal de linha media
# que o solver da NBR 14762 integra para achar A, Ix e Wx. Nao existe estado em
# que a prancha e o calculo discordem, porque sao a mesma fonte.
# =========================================================================
def catalogo_tecnico() -> Canvas:
    import fixture as fx
    import nucleo.catalogo as cg
    import nucleo.perfis as pf
    r = fx.liberacao()
    cat = cg.montar(pj, r)

    cv = base("CATALOGO TECNICO — PERFIL, PARAFUSO, CHAPA E TUBO", "1:2", "36",
              notas=[
        f"{cat['n']} pecas desenhadas a partir das PROPRIAS dimensoes: a mesma "
        f"poligonal de linha media que o solver da NBR 14762 integra.",
        "Nenhuma imagem de catalogo de fabricante foi usada. A designacao ja e "
        "a dimensao: Ue 90x40x12x0,95 diz alma 90, aba 40, labio 12, esp 0,95.",
        "Desenho de PROJETO, nao de fabricacao: sem tolerancia de dobra, sem "
        "raio de ferramenta real, sem detalhe de cabeca de fabricante.",
        "A quantidade de cada peca vem do modelo, e e a mesma que alimenta o "
        "plano de corte e o orcamento.",
    ])

    # 1:4, e nao 1:2. A escala tem de servir a MAIOR secao: o Ue 250 a 1:2
    # ocupa 125 mm de papel e transborda a celula, colidindo com a linha de
    # baixo. Escala mista num catalogo seria pior — o leitor compara secoes
    # lado a lado, e comparacao exige a mesma escala.
    ESC = 0.25
    an.titulo_desenho(cv, (30, 58), "1", "SECOES DOS PERFIS EM USO", "1:4")
    col_w, lin_h = 150.0, 104.0
    x0, y0 = 40.0, 72.0
    for i, p in enumerate(cat["perfis"]):
        cx = x0 + (i % 5) * col_w
        cy = y0 + (i // 5) * lin_h
        perf = next((q for q in pf.catalogo() if q.cod == p["cod"]), None)
        if perf is None:
            continue
        pts, fech = pf.linha_media(perf.forma, perf.bw, perf.bf, perf.D,
                                   perf.t, perf.r)
        xs = [q[0] for q in pts]
        ys = [q[1] for q in pts]
        # a secao e centrada na celula, com a alma na vertical
        larg = (max(xs) - min(xs)) * ESC
        alt = (max(ys) - min(ys)) * ESC
        ox = cx + (col_w - 30 - larg) / 2
        oy = cy + 10 + alt
        pl = [(ox + (q[0] - min(xs)) * ESC, oy - (q[1] - min(ys)) * ESC)
              for q in pts]
        cv.poli_p(pl, "corte", fechado=fech)
        # cotas: alma na vertical, aba na horizontal
        cv.texto_p((ox - 5, oy - alt / 2), f"{perf.bw:g}", TXT["micro"],
                   "middle", rot=-90, cor="#b3261e")
        cv.texto_p((ox + larg / 2, oy + 5), f"{perf.bf:g}", TXT["micro"],
                   "middle", cor="#b3261e")
        mx = cx + (col_w - 30) / 2
        cv.texto_p((mx, cy + 4), p["cod"], TXT["peq"], "middle", peso="bold")
        cv.texto_p((mx, oy + 11),
                   f"A {p['area']:.0f} mm²   Ix {p['ix']:.1f} cm⁴   "
                   f"{p['massa_m']:.3f} kg/m", TXT["micro"], "middle")
        cv.texto_p((mx, oy + 16), f"{p['n']} pecas · "
                   + ", ".join(p["familias"])[:38], TXT["micro"], "middle",
                   cor="#5c666f")

    y = y0 + ((len(cat["perfis"]) - 1) // 5 + 1) * lin_h + 4
    _tabela(cv, (34, y), "PARAFUSOS — TIPO, DIAMETRO E QUANTIDADE",
            ["CODIGO", "⌀ ROSCA", "⌀ CABECA", "COMP", "PONTA", "Rv (H)",
             "QUANTIDADE"],
            [[p["cod"], f"{p['d']:g} mm", f"{p['dw']:g} mm",
              f"{p['comp']:g} mm",
              "broca" if "broc" in p["tipo"] else "agulha",
              f"{p['rv']:g} kN", f"{p['n']:,}".replace(",", ".")]
             for p in cat["parafusos"]],
            larguras=[52, 24, 26, 22, 22, 22, 34])

    _tabela(cv, (216, y), "CHAPAS — FORMATO COMERCIAL E NORMA",
            ["MATERIAL", "ESP", "FORMATO", "NORMA", "AREA"],
            [[c["nome"][:26], f"{c['espessura']:g} mm",
              f"{c['formato'][0]}x{c['formato'][1]}", c["norma"],
              f"{c['area']:.1f} m²"] for c in cat["chapas"]],
            larguras=[62, 20, 34, 32, 26])

    _tabela(cv, (420, y), "TUBOS — DIAMETRO EXTERNO E NORMA",
            ["DN", "⌀ EXTERNO", "SISTEMA", "NORMA", "COMP", "CONEXOES"],
            [[t["cod"], f"{t['de']:g} mm", t["sistema"][:18], t["norma"],
              f"{t['comp']:.1f} m", str(t["conexoes"])]
             for t in cat["tubos"]],
            larguras=[20, 26, 42, 30, 24, 26])

    cv.texto_p((34, cv.alt - cv.marg - 10),
               "O diametro EXTERNO e o que precisa caber no furo do montante: "
               "DN100 tem 110 mm, e a alma de 90 admite furo de 45.",
               TXT["micro"], "start", cor="#5c666f")
    return cv
