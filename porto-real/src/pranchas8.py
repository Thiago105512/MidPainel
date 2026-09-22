"""
R52 — O QUE A DECISAO DO PROPRIETARIO TROUXE PARA O PAPEL.

Quatro pranchas novas, e nenhuma delas e desenho decorativo: cada uma existe
porque um sistema saiu da hipotese e virou dado, e a regra que R51 estabeleceu
diz que o que esta no modelo tem de chegar ao caderno.

  37  SONDAGEM E FUNDACAO — tres furos, o perfil medio, as tres correlacoes de
      tensao admissivel, o recalque por camadas e a troca de 600 mm de aterro.
  38  RETENCAO PLUVIAL — as superficies do lote inteiro, o gatilho da lei
      municipal e o reservatorio com o orificio que faz o trabalho.
  39  DESEMPENHO ACUSTICO — o mapa de pares fonte/receptor que o proprietario
      obrigou a existir.
  40  CARGAS, FASES E MERCADO — o 220/127 confirmado, o equilibrio entre fases
      e de quem se compra cada familia.
"""
from __future__ import annotations

import math
import os

import projeto as pj
import anotacao as an
import fixture as fx
from core import num_br, P, Canvas, View, TXT, CINZA, PRETO
from pranchas import base, _tabela, TOTAL_PRANCHAS

import nucleo.geotecnia as gt
import nucleo.pluvial as pl
import nucleo.acustica as ac
import nucleo.eletrica as el
import nucleo.mercado as mk
import nucleo.fundacao as fu


# =========================================================================
# PR-37 — SONDAGEM E FUNDACAO
# =========================================================================
def sondagem() -> Canvas:
    r = fx.liberacao()
    d = gt.dimensionar(pj, r)
    cg = gt.carga_na_fundacao(pj, r)
    f = fu.levantar(pj)
    t = f["terraplenagem"]
    cv = base("SONDAGEM SPT E FUNDACAO", "1:50 / esquematico", "37", notas=[
        "Tres sondagens a percussao entregues pelo proprietario: SP-01, SP-02 "
        "e SP-03, NSPT metro a metro ate 8 m.",
        "A tensao admissivel sai de TRES correlacoes e adota-se a MENOR: "
        "nenhuma delas nasceu deste solo, e usar correlacao fora do universo "
        "que a gerou so e honesto pelo lado conservador.",
        "O solo nao reprovou por capacidade e sim por UNIFORMIDADE: aterro "
        "pouco compacto e fraco em manchas, e mancha sob radier vira fissura.",
        "Esta prancha NAO substitui projeto de fundacao com ART (pendencia 3).",
    ])

    # --- perfil das sondagens, em escala vertical
    an.titulo_desenho(cv, (30, 58), "1", "PERFIL DO SUBSOLO — SP-01/02/03",
                      "1:50")
    x0, y0 = 46.0, 74.0
    esc = 11.0          # mm de papel por metro de profundidade
    nmax = 34.0
    larg = 92.0
    cv.texto_p((x0 - 8, y0 - 4), "prof.", TXT["micro"], "middle")
    cv.texto_p((x0 + larg / 2, y0 - 4), "NSPT", TXT["micro"], "middle")
    for k in range(0, 35, 5):
        xx = x0 + larg * k / nmax
        cv.linha_p((xx, y0), (xx, y0 + 8 * esc), "eixo")
        cv.texto_p((xx, y0 - 1), f"{k}", TXT["micro"], "middle", cor="#8a9199")
    for faixa in gt.perfil():
        ya = y0 + faixa["z0"] * esc
        yb = y0 + faixa["z1"] * esc
        cv.linha_p((x0 - 6, ya), (x0 + larg, ya), "fino")
        cv.texto_p((x0 - 8, (ya + yb) / 2 + 1.2),
                   f"{faixa['z0']}-{faixa['z1']}", TXT["micro"], "end")
        # barra do N medio
        cv.poli_p([(x0, ya + 1.5), (x0 + larg * faixa["medio"] / nmax, ya + 1.5),
                   (x0 + larg * faixa["medio"] / nmax, yb - 1.5),
                   (x0, yb - 1.5)], "vista", fechado=True,
                  preenche="#dbe6f3", cor="#3f6fb5")
        # dispersao entre os tres furos
        cv.linha_p((x0 + larg * faixa["minimo"] / nmax, (ya + yb) / 2),
                   (x0 + larg * faixa["maximo"] / nmax, (ya + yb) / 2), "corte")
        cv.texto_p((x0 + larg * faixa["medio"] / nmax + 3, (ya + yb) / 2 + 1.2),
                   f"{faixa['medio']:.1f}", TXT["micro"], "start",
                   cor="#3f6fb5")
        cv.texto_p((x0 + larg + 8, (ya + yb) / 2 + 1.2),
                   f"{faixa['solo']}", TXT["micro"], "start", cor="#5c666f")
    cv.linha_p((x0, y0), (x0, y0 + 8 * esc), "corte")
    cv.texto_p((x0, y0 + 8 * esc + 6),
               f"investigado ate {gt.PROF_INVESTIGADA:.0f} m; o acrescimo de "
               f"tensao cai a 10 % da tensao do terreno em "
               f"{d['investigacao']['z_critico']:.1f} m",
               TXT["micro"], "start", cor="#5c666f")

    # --- secao do radier tratado
    an.titulo_desenho(cv, (300, 58), "2", "SECAO DO RADIER E TRATAMENTO", "1:20")
    bx, by = 320.0, 84.0
    L = 190.0
    esp = pj.RADIER["espessura"] / 20.0
    alt_b = gt.BORDA["altura"] / 20.0
    larg_b = gt.BORDA["largura"] / 20.0
    lastro = pj.RADIER["lastro"] / 20.0
    subst = (gt.TRATAMENTO["remover_mm"] - pj.RADIER["lastro"]) / 20.0
    # laje
    cv.poli_p([(bx, by), (bx + L, by), (bx + L, by + esp), (bx, by + esp)],
              "corte", fechado=True, preenche="#e4e0d8")
    # borda engrossada nas duas pontas
    for xx in (bx, bx + L - larg_b):
        cv.poli_p([(xx, by), (xx + larg_b, by), (xx + larg_b, by + alt_b),
                   (xx, by + alt_b)], "corte", fechado=True, preenche="#d6d1c8")
    # lastro e substituicao
    cv.poli_p([(bx - 6, by + alt_b), (bx + L + 6, by + alt_b),
               (bx + L + 6, by + alt_b + lastro), (bx - 6, by + alt_b + lastro)],
              "fino", fechado=True, preenche="#efece6")
    cv.poli_p([(bx - 6, by + alt_b + lastro), (bx + L + 6, by + alt_b + lastro),
               (bx + L + 6, by + alt_b + lastro + subst),
               (bx - 6, by + alt_b + lastro + subst)],
              "fino", fechado=True, preenche="#f6f4f0")
    for txt, yy in ((f"radier {pj.RADIER['espessura']} mm, tela "
                     f"{pj.RADIER['tela']} dupla", by + esp / 2 + 1),
                    (f"borda {gt.BORDA['largura']}x{gt.BORDA['altura']} mm, "
                     f"{gt.BORDA['barras']} x {gt.BORDA['bitola']:.0f} mm",
                     by + alt_b - 3),
                    (f"lastro de brita {pj.RADIER['lastro']} mm",
                     by + alt_b + lastro / 2 + 1),
                    (f"substituicao compactada "
                     f"{gt.TRATAMENTO['remover_mm'] - pj.RADIER['lastro']} mm, "
                     f"GC >= {gt.TRATAMENTO['grau_compactacao']*100:.0f} % PN",
                     by + alt_b + lastro + subst / 2 + 1)):
        cv.texto_p((bx + L + 12, yy), txt, TXT["micro"], "start",
                   cor="#5c666f")
    cv.texto_p((bx, by + alt_b + lastro + subst + 8),
               "solo natural — argila arenosa a partir de 1,00 m",
               TXT["micro"], "start", cor="#5c666f")

    _tabela(cv, (30, 190), "VERIFICACAO GEOTECNICA",
            ["GRANDEZA", "VALOR", "LIMITE", "SITUACAO"],
            [["Pressao de contato (servico)",
              f"{d['pressao_kpa']:.2f} kPa",
              f"{d['admissivel']['adotada_kpa']:.1f} kPa "
              f"({d['admissivel']['governa']})",
              f"fator {d['fator']:.2f} contra {d['fator_minimo']:.0f}"],
             ["Correlacoes calculadas",
              " | ".join(f"{k} {v:.1f}" for k, v in
                         d["admissivel"]["candidatas"].items()),
              "adota-se a MENOR", "conservador por construcao"],
             ["Recalque total",
              f"{d['recalque']['total_mm']:.2f} mm",
              f"{d['recalque']['limite_total_mm']:.0f} mm",
              "ok" if d["recalque_ok"] else "REPROVA"],
             ["Distorcao angular",
              f"{d['recalque']['distorcao']:.6f}",
              f"{d['recalque']['limite_distorcao']:.5f} (1/300)",
              "ok" if d["distorcao_ok"] else "REPROVA"],
             ["Profundidade investigada",
              f"{d['investigacao']['investigada']:.0f} m",
              f"critica em {d['investigacao']['z_critico']:.1f} m",
              "suficiente" if d["investigacao"]["suficiente"] else "RASA"],
             ["Nivel d'agua", "nao consta do boletim", "—",
              "(H): pode mudar impermeabilizacao de base"]],
            larguras=[74, 96, 72, 74])

    _tabela(cv, (30, 250), "CARGA QUE CHEGA AO SOLO",
            ["PARCELA", "kN"],
            [[k, f"{v:.1f}"] for k, v in cg["por_parcela"].items()]
            + [["TOTAL de servico (G + Q)", f"{cg['servico']:.1f}"],
               ["Area do radier", f"{cg['area']:.1f} m2"],
               ["Pressao media", f"{cg['pressao_kpa']:.2f} kPa"]],
            larguras=[150, 60])

    _tabela(cv, (250, 250), "TERRAPLENAGEM — A DESPESA QUE O SPT CRIOU",
            ["ITEM", "QUANTIDADE"],
            [["Area tratada (projecao + bordadura)",
              f"{t['area_tratada']:.1f} m2"],
             ["Profundidade de troca", f"{t['profundidade']*1000:.0f} mm"],
             ["Corte", f"{t['corte_m3']:.1f} m3"],
             ["Bota-fora (empolamento 25 %)", f"{t['bota_fora_m3']:.1f} m3"],
             ["Substituicao compactada", f"{t['substituicao_m3']:.1f} m3"],
             ["Camadas de 250 mm", f"{t['camadas']}"],
             ["Ensaios de densidade in situ", f"{t['ensaios']}"],
             ["Armadura total do radier", f"{f['aco_kg']:.1f} kg "
              f"({f['taxa_kg_m3']:.1f} kg/m3)"],
             ["Concreto (laje + borda)",
              f"{f['volume_m3']:.2f} m3 = {f['volume_laje_m3']:.2f} + "
              f"{f['volume_borda_m3']:.2f}"]],
            larguras=[130, 80])
    return cv


# =========================================================================
# PR-38 — RETENCAO PLUVIAL E SUPERFICIES DO LOTE
# =========================================================================
def retencao_pluvial() -> Canvas:
    b = pl.balanco(pj)
    g = pl.gatilho_legal(pj)
    v = pl.vazoes(pj)
    rt = pl.retencao(pj)
    cv = base("RETENCAO PLUVIAL E SUPERFICIES DO LOTE", "1:200", "38", notas=[
        "R52 trocou REUSO por RETENCAO a pedido do proprietario. Nao e o mesmo "
        "reservatorio menor: sao sistemas de dimensionamento OPOSTO — um quer "
        "cheio antes da seca, o outro vazio antes da chuva.",
        "Para dimensionar qualquer um dos dois faltava a superficie do LOTE "
        "inteiro: 333,44 m2 do terreno nao tinham classe declarada.",
        f"Lei 1.192/2007 (Pro-Aguas, Manaus): obriga acima de "
        f"{g['limite_m2']:.0f} m2 impermeabilizados. O lote tem "
        f"{g['impermeavel']:.2f} m2 — nao obriga, e a retencao foi adotada "
        f"assim mesmo.",
        "Quem faz o trabalho e o ORIFICIO, nao o volume: ele limita a saida a "
        "vazao que o terreno natural ja mandava para a rua.",
    ])

    # --- planta das superficies
    vw = View(200, 60, 470, 0, 0)
    an.titulo_desenho(cv, (50, 50), "1", "SUPERFICIES DO LOTE", "1:200")
    cores = {"cobertura": "#c9c2b6", "piso rigido descoberto": "#ddd6c9",
             "lamina de piscina": "#9fc9de", "piso drenante": "#d9d4c8",
             "brita solta": "#cfcabf", "jardim e grama": "#cfe0c2"}
    L, Pf = pj.LOTE_L, pj.LOTE_P
    cv.poli_p([vw.pt(P(0, 0)), vw.pt(P(L, 0)), vw.pt(P(L, Pf)), vw.pt(P(0, Pf))],
              "corte", fechado=True, preenche="#fdfdfd")
    # legenda por classe, com area
    yy = 70.0
    for s in b["superficies"]:
        cv.poli_p([(300, yy - 3), (307, yy - 3), (307, yy + 1.5), (300, yy + 1.5)],
                  "fino", fechado=True, preenche=cores.get(s["classe"], "#eee"))
        cv.texto_p((311, yy), f"{s['nome'][:40]}", TXT["micro"], "start")
        cv.texto_p((432, yy), f"{s['area']:8.2f} m2", TXT["micro"], "end")
        cv.texto_p((452, yy), f"C {s['c']:.2f}", TXT["micro"], "end")
        yy += 6.4
    cv.linha_p((300, yy - 3), (452, yy - 3), "fino")
    cv.texto_p((311, yy + 1), "SOMA — tem de dar o lote", TXT["micro"],
               "start", peso="bold")
    cv.texto_p((432, yy + 1), f"{b['total']:8.2f} m2", TXT["micro"], "end",
               peso="bold")
    cv.texto_p((452, yy + 1), f"C {b['c_ponderado']:.2f}", TXT["micro"], "end",
               peso="bold")

    # --- esquema do reservatorio
    an.titulo_desenho(cv, (300, 200), "2", "RESERVATORIO DE RETENCAO", "1:25")
    rx, ry = 320.0, 224.0
    w = rt["lado_equivalente"] * 1000 / 25.0
    h = (rt["altura_util"] + rt["borda_livre"]) / 25.0
    cv.poli_p([(rx, ry), (rx + w, ry), (rx + w, ry + h), (rx, ry + h)],
              "corte", fechado=True, preenche="#eef4f8")
    nivel = ry + rt["borda_livre"] / 25.0
    cv.linha_p((rx, nivel), (rx + w, nivel), "eixo")
    cv.texto_p((rx + w + 4, nivel + 1), "nivel maximo", TXT["micro"], "start",
               cor="#3f6fb5")
    cv.texto_p((rx + w + 4, ry + 3), f"borda livre {rt['borda_livre']} mm",
               TXT["micro"], "start", cor="#5c666f")
    cv.texto_p((rx + w + 4, ry + h - 2),
               f"lamina util {rt['altura_util']} mm", TXT["micro"], "start",
               cor="#5c666f")
    cv.circ_p((rx, ry + h - 2), 1.6, "corte", preenche="#fff", cor="#b3261e")
    cv.texto_p((rx - 4, ry + h + 5),
               f"orificio {rt['orificio_mm']:.0f} mm", TXT["micro"], "start",
               cor="#b3261e")
    cv.texto_p((rx, ry + h + 12),
               f"{rt['lado_equivalente']:.2f} x {rt['lado_equivalente']:.2f} m "
               f"uteis = {rt['volume_m3']:.2f} m3", TXT["micro"], "start")

    _tabela(cv, (30, 300), "DA CHUVA AO VOLUME",
            ["ETAPA", "VALOR", "DE ONDE VEM"],
            [["Intensidade de projeto",
              f"{v['intensidade']:.0f} mm/h",
              "a MESMA que dimensiona calha e descida"],
             ["C do terreno natural", f"{b['c_pre']:.2f}",
              "lote com vegetacao, antes da obra"],
             ["C do lote construido", f"{b['c_ponderado']:.4f}",
              "ponderado pelas superficies declaradas"],
             ["Vazao antes / depois",
              f"{v['q_pre_ls']:.2f} | {v['q_pos_ls']:.2f} L/s",
              f"metodo racional; a obra multiplicou por {v['razao']:.2f}"],
             ["Excedente a reter", f"{v['excedente_ls']:.2f} L/s",
              "so a DIFERENCA: o terreno natural tambem escoava"],
             ["Tempo de concentracao",
              f"{rt['tempo_concentracao_min']:.0f} min", "lote pequeno"],
             ["VOLUME", f"{rt['volume_m3']:.2f} m3",
              "excedente acumulado no tempo de concentracao"],
             ["Orificio de saida",
              f"{rt['orificio_mm']:.1f} mm ({rt['orificio_area_cm2']:.1f} cm2)",
              f"calibrado para soltar {rt['vazao_de_saida_ls']:.2f} L/s com "
              f"lamina cheia"],
             ["Esvaziamento",
              f"{rt['esvaziamento_min']:.1f} min",
              "carga variavel; volta a estar vazio antes da proxima chuva"],
             ["Destino", rt["fundo"][:60],
              "a lei prefere infiltracao a descarga na rede"]],
            larguras=[70, 74, 166])
    return cv


# =========================================================================
# PR-39 — DESEMPENHO ACUSTICO
# =========================================================================
def acustica() -> Canvas:
    ps = sorted(ac.entre_zonas(pj), key=lambda q: q["folga"])
    cv = base("DESEMPENHO ACUSTICO ENTRE AMBIENTES", "s/ escala", "39", notas=[
        "Esta prancha existe porque o proprietario perguntou o que 101 "
        "verificacoes nao sabiam responder: quem entra na casa ouve o chuveiro "
        "do banho da entrada?",
        "Ouvia. A parede era boa (PH-1, Rw 44) e a porta era de correr (Rw 15): "
        "o conjunto entregava 20 dB. Em acustica o elo fraco DOMINA — nao se "
        "faz media aritmetica de isolamento, se soma energia que passa.",
        "Isolamento so se exige ENTRE zonas. Dentro da fita social o ruido nao "
        "e defeito, e o programa.",
        "D adotado igual ao R composto (simplificacao declarada). Isto e "
        "pre-verificacao de projeto, nao ensaio de campo da NBR 15575-3.",
    ])

    an.titulo_desenho(cv, (30, 54), "1", "PARES FONTE / RECEPTOR", "s/ escala")
    y = 74.0
    esc = 3.4      # mm por dB
    base_x = 150.0
    cv.texto_p((base_x, y - 8), "0", TXT["micro"], "middle", cor="#8a9199")
    for k in (10, 20, 30, 40, 50):
        cv.linha_p((base_x + k * esc, y - 6), (base_x + k * esc, y + len(ps) * 9),
                   "eixo")
        cv.texto_p((base_x + k * esc, y - 8), f"{k}", TXT["micro"], "middle",
                   cor="#8a9199")
    cv.texto_p((base_x + 60 * esc, y - 8), "dB", TXT["micro"], "start",
               cor="#8a9199")
    for p in ps:
        cv.texto_p((base_x - 6, y + 3), f"{p['fonte']} > {p['receptor']}",
                   TXT["micro"], "end")
        cv.poli_p([(base_x, y), (base_x + p["obtido"] * esc, y),
                   (base_x + p["obtido"] * esc, y + 4),
                   (base_x, y + 4)], "vista", fechado=True,
                  preenche="#dbe6f3" if p["passa"] else "#f6dcd9",
                  cor="#3f6fb5" if p["passa"] else "#d03b3b")
        cv.linha_p((base_x + p["exigido"] * esc, y - 1),
                   (base_x + p["exigido"] * esc, y + 5), "corte")
        cv.texto_p((base_x + p["obtido"] * esc + 3, y + 3),
                   f"{p['obtido']:.1f} | exige {p['exigido']:.0f} | folga "
                   f"{p['folga']:+.1f}", TXT["micro"], "start",
                   cor="#5c666f" if p["passa"] else "#d03b3b")
        y += 9
    cv.texto_p((base_x - 6, y + 6),
               "barra = isolamento obtido; traco vertical = exigido "
               "(nivel da fonte menos limite do receptor, NBR 10152)",
               TXT["micro"], "end", cor="#5c666f")

    _tabela(cv, (30, 230), "O QUE MUDOU EM R52",
            ["ONDE", "ANTES", "DEPOIS", "POR QUE"],
            [["Banho compartilhado > hall de entrada",
              "porta de correr (Rw 15) — conjunto de 20,2 dB",
              "parede CEGA, 44 dB",
              "o acesso de visita passou para a circulacao"],
             ["Banho compartilhado > quarto reversivel",
              "porta oca (Rw 20) — conjunto de 25,1 dB, exigia 35",
              "parede CEGA, 44 dB",
              "era a pior passagem da casa, e nao era a visivel"],
             ["Hall > garagem",
              "porta oca — 26,8 dB, exigia 30",
              "P06 solida vedada — 35,8 dB",
              "porta entre garagem e casa tem outra razao para ser macica"],
             ["Banho compartilhado > circulacao",
              "nao havia porta",
              "P06 solida vedada — 33,7 dB, exige 25",
              "unico acesso do banho, e abre para fora"],
             ["Box do chuveiro",
              "encostado na parede do hall",
              "canto nordeste, sob a janela alta",
              "consequencia da porta nova; a regra dos 900 mm de box "
              "reprovou a primeira tentativa"]],
            larguras=[76, 92, 76, 116])

    _tabela(cv, (30, 300), "TABELAS ADOTADAS",
            ["ITEM", "VALOR", "FONTE"],
            [[f"Fonte: {k}", f"{v} dB(A)", "pratica corrente de acustica"]
             for k, v in sorted(ac.FONTES.items())]
            + [[f"Limite: {k}", f"{v} dB(A)",
                "NBR 10152:2017 (circulacao e entrada adotados)"]
               for k, v in sorted(ac.LIMITE.items())]
            + [[f"Porta: {k}", f"Rw {v} dB", "faixa de mercado declarada"]
               for k, v in sorted(ac.RW_PORTA.items())],
            larguras=[100, 60, 200])
    return cv


# =========================================================================
# PR-40 — CARGAS, FASES E MERCADO
# =========================================================================
def cargas_e_mercado() -> Canvas:
    r = fx.liberacao()
    eq = el.equilibrar(pj)
    en = el.entrada(pj)
    d = pj.demanda_eletrica()
    cb = mk.cobertura_de_fornecedores(r)
    ad = mk.aderencia(pj, r)
    cv = base("QUADRO DE CARGAS, EQUILIBRIO DE FASES E MERCADO", "s/ escala",
              "40", notas=[
        "A pendencia 7 fechou com a decisao do proprietario: trifasico, 127 V "
        "para os eletrodomesticos correntes, 220 V para ar e chuveiro.",
        "Confirmar o esquema abriu trabalho em vez de fechar: num 220/127 a "
        "carga de 127 fica entre fase e neutro e a de 220 entre duas fases, e "
        "aparece o DESEQUILIBRIO — que instalacao monofasica nao tem.",
        "A atribuicao de fase esta escrita no projeto. Deixa-la para o dia da "
        "montagem e entregar ao eletricista uma decisao que muda a corrente de "
        "cada fase.",
        "Precos seguem (H): a pesquisa devolveu fornecedor e indice publico, "
        "nao preco unitario por fornecedor.",
    ])

    an.titulo_desenho(cv, (30, 54), "1", "CARGA POR FASE", "s/ escala")
    bx, by = 60.0, 76.0
    esc = 0.0042
    for fase in el.FASES:
        va = eq["por_fase"][fase]
        cv.texto_p((bx - 6, by + 4), f"Fase {fase}", TXT["peq"], "end")
        cv.poli_p([(bx, by), (bx + va * esc, by), (bx + va * esc, by + 6),
                   (bx, by + 6)], "vista", fechado=True,
                  preenche="#dbe6f3", cor="#3f6fb5")
        cv.texto_p((bx + va * esc + 4, by + 4),
                   f"{num_br(va)} VA  ({eq['corrente_por_fase'][fase]:.1f} A)",
                   TXT["micro"], "start", cor="#5c666f")
        by += 11
    cv.texto_p((bx, by + 6),
               f"desequilibrio de {eq['desequilibrio']*100:.2f} % contra "
               f"{eq['limite']*100:.0f} % admitidos — "
               f"{len(eq['circuitos'])} circuitos distribuidos do maior para o "
               f"menor", TXT["micro"], "start", cor="#5c666f")

    _tabela(cv, (250, 54), "PADRAO DE ENTRADA",
            ["ITEM", "VALOR"],
            [["Esquema", en["tipo"]],
             ["Concessionaria (referencia)", en["concessionaria"]],
             ["Carga instalada", f"{d['instalada_va']:,} VA".replace(",", ".")],
             ["Demanda provavel", f"{d['demanda_va']:,} VA".replace(",", ".")],
             ["Corrente de projeto", f"{en['corrente_a']:.1f} A"],
             ["Disjuntor geral", f"{en['disjuntor_a']} A"],
             ["Ramal de entrada", f"{en['secao_mm2']} mm2"],
             ["Neutro", f"{en['neutro_mm2']} mm2"],
             ["Condutor de protecao", f"{en['aterramento_mm2']} mm2 "
              f"(Tabela 58 da NBR 5410, nao metade da fase)"],
             ["Cargas em 127 V", pj.TENSAO["cargas_127"]],
             ["Cargas em 220 V", pj.TENSAO["cargas_220"]]],
            larguras=[70, 140])

    linhas = []
    for c in sorted(eq["circuitos"], key=lambda q: (-q["va"]))[:26]:
        linhas.append([c["cod"][:16], c["tipo"], f"{c['v']}",
                       f"{c['va']:,}".replace(",", "."),
                       "-".join(c["fases"])])
    _tabela(cv, (30, 150), "CIRCUITOS — OS 26 MAIORES, COM A FASE ATRIBUIDA",
            ["CIRCUITO", "TIPO", "V", "VA", "FASE"], linhas,
            larguras=[60, 40, 22, 34, 30])

    _tabela(cv, (250, 150), "DE QUEM SE COMPRA",
            ["FAMILIA", "% CUSTO", "FORN.", "MANAUS", "NOMES"],
            [[l["familia"], f"{l['fracao']*100:.1f}", str(l["fornecedores"]),
              str(l["manaus"]), ", ".join(f[0] for f in l["lista"])[:78]]
             for l in cb["linhas"]],
            larguras=[36, 26, 20, 24, 104])

    _tabela(cv, (250, 260), "CONFERENCIA DE CIMA PARA BAIXO",
            ["ITEM", "VALOR"],
            [["Orcamento dos sistemas modelados",
              f"R$ {ad['total']:,.2f}".replace(",", "@").replace(".", ",")
              .replace("@", ".")],
             ["Por m2 de area fechada", f"R$ {ad['por_m2']:.2f}/m2"],
             ["Extrapolado para obra entregue",
              f"R$ {ad['obra_entregue_m2']:.2f}/m2 "
              f"(parcela de material {ad['parcela_material']:.0%})"],
             ["Indice steel frame popular / medio / alto",
              f"R$ {mk.INDICES[2]['valor']:.2f} | "
              f"{mk.INDICES[3]['valor']:.2f} | "
              f"{mk.INDICES[4]['valor']:.2f} por m2 (Sudeste, 2026-04)"],
             ["CUB Amazonas R8-N",
              f"R$ {mk.INDICES[1]['valor']:.2f}/m2 (2026)"],
             ["Posicao",
              f"{abs(ad['distancia_do_popular'])*100:.1f} % abaixo do popular "
              f"— e tem de ficar abaixo, porque o escopo daqui e menor"],
             ["Risco de praca",
              f"fator {ad['fator_praca']:.2f}: precos (H) de tabela do Sudeste "
              f"levariam o total a R$ "
              + f"{ad['se_praca_sudeste']:,.2f}".replace(",", "@")
              .replace(".", ",").replace("@", ".")]],
            larguras=[76, 134])

    _tabela(cv, (30, 300), "O QUE NAO ESTA NESTE ORCAMENTO",
            ["ESCOPO", "SITUACAO NO MODELO"],
            [[k, v] for k, v in mk.FORA_DO_ORCAMENTO],
            larguras=[90, 190])
    return cv


# =========================================================================
# PR-41 — ENERGIA: FOTOVOLTAICA, SPDA E VIDRO SOLAR (R61)
# =========================================================================
def energia() -> Canvas:
    import nucleo.spda as sp
    import nucleo.fotovoltaica as fv
    r = fx.liberacao()
    s = r["camadas"]["spda"]
    f = r["camadas"]["fotovoltaica"]
    cv = base("ENERGIA — FOTOVOLTAICA, SPDA E VIDRO SOLAR", "s/ escala", "41", notas=[
        "Tres decisoes que ficam caras depois da estrutura: o vidro da cortina, o "
        "para-raios e a geracao propria.",
        f"Manaus: Ng = {sp.NG_MANAUS:g} descargas/km2.ano (H) — entre as maiores do pais; "
        f"irradiacao {fv.HSP:g} kWh/m2.dia (H).",
        "A estrutura de aco do LSF e descida natural (NBR 5419-3): a protecao custa "
        "captor, anel e conexao, nao cobre pela fachada.",
        "Valores (H) de sitio e de preco: pendencia 15.",
    ])
    vaos = pj.vaos_envidracados()
    linhas = [[v["tipo"], v["face"], v["amb"], f"{v['area']:.2f}", v["vidro"][:44],
               f"{v['g']:.2f}", f"{v['area'] * v['g'] / pj.G_REF:.1f}",
               "OK" if not (v["face"] in ("L", "O") and v["g"] > pj.G_MAX_SOL) else "REVER"]
              for v in vaos]
    y = _tabela(cv, (35, 44), f"VIDRO POR VAO — FATOR SOLAR (g <= {pj.G_MAX_SOL:.2f} nas faces L e O)",
                ["VAO", "FACE", "AMB", "m2", "VIDRO", "g", "m2 equiv.", ""],
                linhas, larguras=[18, 14, 20, 14, 96, 12, 20, 16]) + 8
    cv.texto_p((35, y), "m2 equiv. = area x g / g_ref: e o que entra na carga termica "
                        "(CLIMA_Q_VIDRO vale para g = 0,35).", TXT["min"], "start", cor=CINZA)
    soc = next(c for c in pj.CLIMATIZACAO if c["amb"] == "T-SOC")
    q = pj.carga_termica("T-SOC", soc["pessoas"], soc["equip"], soc.get("mais"),
                         soc.get("conta_ventilador", False), soc.get("duto", False))
    extra = int(18.72 * (0.80 - 0.35) / pj.G_REF * pj.CLIMA_Q_VIDRO)
    cv.texto_p((35, y + 5), f"Zona social: carga {q} BTU/h com low-e na cortina, contra "
                            f"{soc['capacidade']} BTU/h instalados. Com temperado comum (g 0,80) "
                            f"a mesma cortina somaria {extra} BTU/h.", TXT["min"], "start")
    y2 = _tabela(cv, (35, y + 16), "SPDA — NBR 5419: AVALIACAO E COMPONENTES",
                 ["ITEM", "VALOR", "ORIGEM"],
                 [["Densidade de descargas Ng", f"{sp.NG_MANAUS:g} /km2.ano", "(H) RINDAT/ELAT — pendencia 15"],
                  ["Area de exposicao equivalente Ad", f"{s['ad_m2']:.0f} m2",
                   "L.W + 6H(L+W) + 9.pi.H2, com H = topo da platibanda"],
                  ["Frequencia de descargas diretas Nd", f"{s['nd_ano']:.4f} /ano",
                   f"Ng . Ad . Cd (Cd = {s['cd']:g}, estrutura isolada)"],
                  ["Periodo de retorno", f"{s['retorno_anos']:.0f} anos", "1 / Nd"],
                  ["Classe de protecao adotada", s["classe"], "decisao de projeto: Manaus, dois pavimentos, aco"],
                  ["Captor", f"anel de {s['captor_m']:.1f} m no perimetro da cobertura",
                   f"malha {s['malha_m']:.0f} x {s['malha_m']:.0f} m: a cobertura cabe numa celula"],
                  ["Descidas", f"{s['descidas']} pela estrutura LSF (naturais)",
                   f"espacamento <= {s['espac_descida_m']:.0f} m; montante {s['secao_montante_mm2']:.0f} mm2 >= 50"],
                  ["Aterramento", f"anel de {s['anel_m']:.1f} m + {s['hastes']} hastes",
                   "cobre nu 50 mm2 no perimetro do radier"],
                  ["Protecao interna", "BEP + DPS classe I na entrada + DPS classe II nos quadros",
                   "NBR 5419-4 / NBR 5410"]],
                 larguras=[60, 90, 120]) + 8
    y3 = _tabela(cv, (35, y2), "FOTOVOLTAICA — DIMENSIONAMENTO",
                 ["ITEM", "VALOR", "ORIGEM"],
                 [["Consumo estimado", f"{f['consumo_kwh_dia']:.1f} kWh/dia · {f['consumo_kwh_mes']:.0f} kWh/mes",
                   "splits por capacidade e horas (H), iluminacao calculada, chuveiro, base"],
                  ["Irradiacao (HSP)", f"{f['hsp']:g} kWh/m2.dia", "(H) Atlas INPE — pendencia 15"],
                  ["Potencia necessaria", f"{f['kwp']:.2f} kWp", f"consumo / (HSP x PR {f['pr']})"],
                  ["Modulos", f"{f['n_modulos']} x {f['modulo_wp']} Wp = {f['kwp_instalado']:.2f} kWp",
                   f"{f['area_modulos_m2']:.1f} m2 com folga; o consumo pediria {f['n_pedido']}, "
                   f"cabem {f['n_cabe']} — instala-se o que cabe"],
                  ["Cobertura disponivel", f"{f['area_cobertura_m2']:.1f} m2 (superior, menos passarela)",
                   "OK" if f["cabe"] else "NAO CABE"],
                  ["Carga na cobertura", f"{f['carga_kn_m2']:.3f} kN/m2",
                   f"limite declarado em cargas: {f['carga_limite_kn_m2']:.2f} kN/m2 — "
                   + ("OK" if f["carga_ok"] else "REVER")],
                  ["Inversor", f"{f['inversor_kw']:.0f} kW em {f['local_inversor']} (faixa tecnica norte)",
                   f"relacao CC/CA {f['kwp_instalado'] / f['inversor_kw']:.2f}"],
                  ["Geracao anual", f"{f['geracao_kwh_ano']:.0f} kWh",
                   f"cobre {f['cobertura_consumo'] * 100:.0f} % do consumo estimado"],
                  ["Economia e retorno", f"R$ {f['economia_ano']:.0f}/ano · payback {f['payback_anos']:.1f} anos",
                   f"tarifa R$ {f['tarifa']:.2f}/kWh (H); custo (H) do BOM"]],
                 larguras=[60, 90, 120]) + 6
    cv.texto_p((35, y3), "Microgeracao distribuida (REN ANEEL 1.000/2021): compensacao de creditos; "
                         "a rede continua sendo a bateria.", TXT["min"], "start", cor=CINZA)
    an.titulo_desenho(cv, (450, 54), "1", "PERFIL DE INSOLACAO NA FACHADA OESTE", "s/ escala")
    ox, oy = 470, 230
    cv.linha_p((ox, oy), (ox + 300, oy), "vista")
    cv.texto_p((ox + 300, oy + 5), "horizonte oeste", TXT["micro"], "end", cor=CINZA)
    for hora, cor in ((14, "#c9a227"), (16, "#e08a1e"), (17, "#b5541a")):
        alt = math.degrees(math.asin(math.cos(math.radians(3.1)) * math.cos(math.radians((hora - 12) * 15))))
        L = 150
        x1, y1 = ox + L * math.cos(math.radians(alt)), oy - L * math.sin(math.radians(alt))
        cv.linha_p((ox, oy), (x1, y1), "eixo", cor=cor)
        cv.texto_p((x1 + 2, y1), f"{hora}h · {alt:.0f}°", TXT["micro"], "start", cor=cor)
    cv.poli_p([(ox - 4, oy), (ox, oy), (ox, oy - 78), (ox - 4, oy - 78)], "corte", fechado=True, preenche="#8fc4dd")
    cv.texto_p((ox - 6, oy - 40), "cortina CV-01  2,60 m", TXT["micro"], "end", rot=90)
    cv.texto_p((450, oy + 16), "Equinocio, latitude 3 S: as 16 h o sol esta a 30 graus, de frente para a "
                              "cortina. Beiral de 1 m sombreia so os 58 cm de cima; o que resolve e o "
                              "vidro (g) e o brise vertical.", TXT["min"], "start")
    cv.texto_p((450, oy + 21), "Com g = 0,80 entram ~600 W/m2 x 0,80 = 480 W/m2; com low-e g = 0,35, "
                              "210 W/m2. Sao 18,7 m2: 5,0 kW contra 2,2 kW de calor no estar.",
               TXT["min"], "start")
    return cv


# =========================================================================
# PR-43 a PR-46 — PERSPECTIVAS (R66)
# =========================================================================
GRUPOS_PERSP = {
    "externa": ("PERSPECTIVAS EXTERNAS — OITO AZIMUTES E DUAS AEREAS", "43"),
    "terreo": ("PERSPECTIVAS INTERNAS — TERREO", "44"),
    "abertas": ("PERSPECTIVAS — AREAS ABERTAS DO TERREO", "45"),
    "superior": ("PERSPECTIVAS INTERNAS — SUPERIOR", "46"),
}


def _planta_chave(cv, box, v, pav_ambs, extra=()):
    """Mini planta com a camera e o cone de visao: onde a foto foi tirada."""
    import perspectivas as pp
    x0, y0, w, h = box
    xs = [a.x for a in pav_ambs] + [a.x + a.w for a in pav_ambs] + [v["pos"][0]]
    ys = [a.y for a in pav_ambs] + [a.y + a.h for a in pav_ambs] + [v["pos"][1]]
    for (ex0, ey0, ex1, ey1) in extra:
        xs += [ex0, ex1]; ys += [ey0, ey1]
    mx0, mx1, my0, my1 = min(xs) - 500, max(xs) + 500, min(ys) - 500, max(ys) + 500
    k = min(w / (my1 - my0), h / (mx1 - mx0))   # papel x <- modelo y; papel y <- modelo x
    # modelo: +x = norte (para cima no papel), +y = oeste (para a esquerda)
    def pt(px, py):
        return (x0 + w / 2 - (py - (my0 + my1) / 2) * k, y0 + h / 2 - (px - (mx0 + mx1) / 2) * k)
    cv.poli_p([(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)], "fino",
              fechado=True, preenche="#fcfcfb", cor="#ddd")
    for (ex0, ey0, ex1, ey1) in extra:
        cv.poli_p([pt(ex0, ey0), pt(ex1, ey0), pt(ex1, ey1), pt(ex0, ey1)], "fino",
                  fechado=True, preenche="none", cor="#bbb")
    for a in pav_ambs:
        cv.poli_p([pt(a.x, a.y), pt(a.x + a.w, a.y), pt(a.x + a.w, a.y + a.h), pt(a.x, a.y + a.h)],
                  "fino", fechado=True, preenche="#f2f0ec" if a.cod == v["amb"] else "none", cor="#999")
    if v["amb"] != "-" and "/" in v["amb"]:
        d = next(x for x in pj.SUBDIVISOES if f"{x['pai']}/{x['nome']}" == v["amb"])
        cv.poli_p([pt(d["x"], d["y"]), pt(d["x"] + d["w"], d["y"]), pt(d["x"] + d["w"], d["y"] + d["h"]),
                   pt(d["x"], d["y"] + d["h"])], "fino", fechado=True, preenche="#f2f0ec", cor="#666")
    px, py = v["pos"][0], v["pos"][1]
    tx, ty = v["alvo"][0], v["alvo"][1]
    ang = math.atan2(ty - py, tx - px)
    L = (mx1 - mx0 + my1 - my0) / 8
    c = pt(px, py)
    for da in (-v["fov"] / 2, v["fov"] / 2):
        a = ang + math.radians(da)
        cv.linha_p(c, pt(px + math.cos(a) * L, py + math.sin(a) * L), "fino", cor="#c00")
    cv.circ_p(c, 0.7, "fino", preenche="#c00", cor="#c00")


def perspectivas(grupo: str) -> Canvas:
    """Fotos da maquete eletronica, cada uma com a planta-chave da camera.

    As posicoes sao DERIVADAS (perspectivas.py): porta ou canto de onde o olhar
    vai mais longe, olho a 1.550 mm. Nao e render fotorrealista — e a cena do
    visualizador, com o sol de Manaus na hora indicada. O que se confere aqui e
    proporcao, altura, vao e vista, nao acabamento.
    """
    import perspectivas as pp
    titulo, num = GRUPOS_PERSP[grupo]
    m = pp.manifesto()
    cv = base(titulo, "s/ escala", num, notas=[
        "Maquete eletronica do modelo: caixas com cor, sol de Manaus por hora, sombra e vidro "
        "translucido. Nao e render fotorrealista: nao ha textura nem material.",
        f"Camera derivada do caso: olho a {pp.OLHO} mm do piso; dentro do comodo, "
        f"{pp.RECUO_PORTA} mm para dentro da porta ou no canto de onde o olhar vai mais longe.",
        "Planta-chave ao lado de cada foto: ponto vermelho = camera, cone = campo de visao.",
        "Para render com materiais: out/porto-real.obj (Blender, SketchUp, Twinmotion).",
    ])
    if m is None:
        cv.texto_p((300, 250), "PERSPECTIVAS NAO RENDERIZADAS — rode build.py com o Chromium "
                   "disponivel (playwright)", TXT["med"], "middle", cor="#c00")
        return cv
    vistas = [v for v in m["vistas"] if v["grupo"] == grupo]
    cols, cw, ch = 5, 156.0, 148.0
    img_w, img_h = cw - 6, (cw - 6) * 661 / 1130
    x_ini, y_ini = 26.0, 24.0
    lote = [(0, 0, pj.LOTE_L, pj.LOTE_P)]
    for i, v in enumerate(vistas):
        cx0 = x_ini + (i % cols) * cw
        cy0 = y_ini + (i // cols) * ch
        caminho = os.path.join(pp.OUT, f"persp-{v['id']}.png")
        with cv.escopo("perspectiva", v["id"], amb=v["amb"], origem=v["origem"]):
            ok = cv.imagem_p((cx0, cy0), img_w, img_h, caminho)
            cv.poli_p([(cx0, cy0), (cx0 + img_w, cy0), (cx0 + img_w, cy0 + img_h), (cx0, cy0 + img_h)],
                      "fino", fechado=True, preenche="none" if ok else "#f6f6f6", cor="#888")
            if not ok:
                cv.texto_p((cx0 + img_w / 2, cy0 + img_h / 2), "sem foto", TXT["peq"], "middle", cor="#c00")
            ty = cy0 + img_h + 4
            cv.texto_p((cx0, ty), f"{i + 1}. {v['titulo'].upper()}", TXT["micro"], "start", peso="bold")
            hh = int(v["hora"]); mm = int(round((v["hora"] - hh) * 60))
            cv.texto_p((cx0, ty + 3.2), f"{v['amb']} · {v['origem']} · sol {hh:02d}:{mm:02d} · "
                       f"fov {v['fov']:.0f}°", TXT["micro"], "start", cor=CINZA)
            cv.texto_p((cx0, ty + 6.4), f"camera ({v['pos'][0] / 1000:.1f}; {v['pos'][1] / 1000:.1f}; "
                       f"+{v['pos'][2] / 1000:.2f}) m".replace(".", ","), TXT["micro"], "start", cor=CINZA)
            if grupo == "externa":
                ambs = pj.TERREO + pj.SUPERIOR
                _planta_chave(cv, (cx0 + img_w - 46, ty + 9, 46, 40), v, ambs, extra=lote)
            else:
                ambs = (pj.TERREO + pj.TERREO_ABERTO) if v["pav"] == "T" else pj.SUPERIOR
                _planta_chave(cv, (cx0 + img_w - 46, ty + 9, 46, 40), v, ambs)
    an.titulo_desenho(cv, (x_ini, y_ini + ((len(vistas) - 1) // cols + 1) * ch + 6), "1",
                      titulo.title(), "s/ escala")
    return cv


# =========================================================================
# PR-47 — TERRENO: PERFIL NATURAL, PLATAFORMA E COTAS (R68)
# =========================================================================
def terreno() -> Canvas:
    """O perfil do lote com a plataforma, as cotas e o que a declividade custa.

    Ate R67 o lote era plano por omissao e o RN da implantacao era um "+0,00"
    desenhado. Com a declividade confirmada (1 % a 2 % para a rua), esta
    prancha responde quatro perguntas que nenhuma outra respondia: em que cota
    apoia o radier, quanto custa regularizar, se a rampa cabe, e se a agua sai
    por gravidade. A resposta da segunda e a que surpreende: zero.

    Exagero vertical DECLARADO, e moderado de proposito. A primeira versao usou
    20x: o desnivel ficou legivel e a camada de reposicao de 600 mm virou um
    bloco de 60 mm no papel, mais espesso que um terco do lote. Exagero que
    distorce a peca que o desenho existe para mostrar nao e recurso, e erro.
    5x mostra a queda e mantem a proporcao da camada.
    """
    import nucleo.terreno as tr
    import nucleo.geotecnia as gt

    EXAG = 5.0
    ESC_H = 100.0
    p2 = tr.plataforma(pj, pj.DECLIVIDADE_MAX)
    p1 = tr.plataforma(pj, pj.DECLIVIDADE_MIN)
    a2 = tr.acessos(pj, pj.DECLIVIDADE_MAX)
    a1 = tr.acessos(pj, pj.DECLIVIDADE_MIN)
    g = tr.gravidade(pj)
    trat = gt.TRATAMENTO

    cv = base("TERRENO — PERFIL NATURAL, PLATAFORMA E COTAS",
              f"H 1:{ESC_H:.0f} · V 1:{ESC_H / EXAG:.0f}", "47", notas=[
        "Perfil longitudinal do lote, da testada (leste, RN +0,00) ao fundo (oeste).",
        f"Declividade confirmada pelo proprietario: {pj.DECLIVIDADE_MIN * 100:.0f} % a "
        f"{pj.DECLIVIDADE_MAX * 100:.0f} % no sentido da rua. O desenho mostra o caso de "
        f"{pj.DECLIVIDADE_MAX * 100:.0f} %, que e o pior para volume de terra.",
        f"EXAGERO VERTICAL DE {EXAG:.0f}x — horizontal 1:{ESC_H:.0f}, vertical "
        f"1:{ESC_H / EXAG:.0f}. Sem exagero, {g['queda_terreno_mm']:.0f} mm em "
        f"{pj.LOTE_P / 1000:.0f} m nao se le no papel.",
        "A plataforma fica na cota MEDIA sob a casa: corte e aterro se compensam, e os "
        "dois cabem dentro da troca de 600 mm que o SPT ja obrigou.",
    ])

    ox, oy = 60.0, 116.0
    kx = 1000.0 / ESC_H / 1000.0            # mm de modelo -> mm de papel
    kz = kx * EXAG

    def pt(y_mm, cota_mm):
        return (ox + y_mm * kx, oy - cota_mm * kz)

    ambs = pj.TERREO + pj.SUPERIOR
    f_y0 = min(a.y for a in ambs)
    f_y1 = max(a.y + a.h for a in ambs)
    D = pj.DECLIVIDADE_MAX

    # ---- macico de terra sob o natural de 2 %
    cv.poli_p([pt(0, 0), pt(pj.LOTE_P, pj.cota_natural(pj.LOTE_P, D)),
               pt(pj.LOTE_P, -1_200), pt(0, -1_200)], "fino", fechado=True,
              preenche="#f2ece0", cor="#cbbfa6")
    for i_ in range(0, int(pj.LOTE_P) + 1, 2_000):
        cv.linha_p(pt(i_, pj.cota_natural(i_, D)), pt(i_, -1_200), "cota", cor="#ddd2ba")

    # ---- terreno natural nas duas pontas da faixa declarada
    for d, estilo, cor, rot in ((D, "corte", "#8a6d3b", f"natural {D * 100:.0f} %"),
                                (pj.DECLIVIDADE_MIN, "vista", "#b8a078",
                                 f"natural {pj.DECLIVIDADE_MIN * 100:.0f} %")):
        cv.linha_p(pt(0, 0), pt(pj.LOTE_P, pj.cota_natural(pj.LOTE_P, d)), estilo, cor=cor)
        c = pt(pj.LOTE_P, pj.cota_natural(pj.LOTE_P, d))
        cv.texto_p((c[0] + 2, c[1] + 1), rot, TXT["micro"], "start", cor=cor)

    # ---- RN da testada
    cv.linha_p(pt(-2_500, 0), pt(pj.LOTE_P, 0), "cota", cor="#999", dash="4 2")
    cv.texto_p((pt(-2_500, 0)[0], pt(0, 0)[1] - 2), "RN +0,00 = testada",
               TXT["micro"], "start", cor="#666")

    # ---- escavacao, reposicao e radier (caso de 2 %)
    plat = p2["cota_plataforma"]
    esc0 = pj.cota_natural(f_y0, D) - trat["remover_mm"]
    esc1 = pj.cota_natural(f_y1, D) - trat["remover_mm"]
    cv.poli_p([pt(f_y0, esc0), pt(f_y1, esc1), pt(f_y1, plat), pt(f_y0, plat)],
              "fino", fechado=True, preenche="#e4efdd", cor="#5a8a4a")
    cv.linha_p(pt(f_y0, esc0), pt(f_y1, esc1), "corte2", cor="#c0392b")
    cv.poli_p([pt(f_y0, plat), pt(f_y1, plat),
               pt(f_y1, p2["cota_piso_acabado"]), pt(f_y0, p2["cota_piso_acabado"])],
              "corte", fechado=True, preenche="#cfcac1", cor="#333")

    cv.texto_p(pt((f_y0 + f_y1) / 2, p2["cota_piso_acabado"] + 420),
               f"PISO ACABADO +{p2['cota_piso_acabado'] / 1000:.3f}".replace(".", ","),
               TXT["micro"], "middle", peso="bold")
    cv.texto_p(pt((f_y0 + f_y1) / 2, (plat + esc0) / 2 - 120),
               f"reposicao controlada {p2['reposicao_baixo_mm']:.0f} a "
               f"{p2['reposicao_alto_mm']:.0f} mm", TXT["micro"], "middle", cor="#3d6b30")
    cv.texto_p(pt(f_y1 + 900, esc1), "fundo da escavacao: 600 mm abaixo do natural",
               TXT["micro"], "start", cor="#c0392b")

    # ---- limites: casa, piscina e divisas
    for y_, rot in ((f_y0, "frente da casa"), (f_y1, "fundo da casa"),
                    (pj.PISCINA["y"], "piscina"), (pj.LOTE_P, "divisa de fundo")):
        cv.linha_p(pt(y_, -1_200), pt(y_, 1_400), "cota", cor="#0b6", dash="2 2")
        cv.texto_p((pt(y_, 1_400)[0], pt(y_, 1_400)[1] - 2.5), rot,
                   TXT["micro"], "middle", cor="#0b6")

    # ---- rampa de acesso
    cv.linha_p(pt(0, 0), pt(f_y0, p2["cota_piso_acabado"]), "corte", cor="#c8651a")
    cv.texto_p(pt(f_y0 / 2, p2["cota_piso_acabado"] / 2 + 320),
               f"rampa {a2['rampa_pct']:.1f} %", TXT["micro"], "middle",
               cor="#c8651a", peso="bold")

    # ---- escala vertical
    for c in (0, 250, 500, 750):
        cv.linha_p((ox - 13, pt(0, c)[1]), (ox - 3, pt(0, c)[1]), "cota", cor="#aaa")
        cv.texto_p((ox - 15, pt(0, c)[1]), f"+{c / 1000:.2f}".replace(".", ","),
                   TXT["micro"], "end", cor="#666")
    cv.texto_p((ox - 15, pt(0, -950)[1]), "cotas em m", TXT["micro"], "end", cor="#999")

    # ---- cadeia horizontal de profundidade
    for y_ in range(0, int(pj.LOTE_P) + 1, 10_000):
        cv.linha_p(pt(y_, -1_200), (pt(y_, -1_200)[0], pt(0, -1_200)[1] + 4),
                   "cota", cor="#bbb")
        cv.texto_p((pt(y_, -1_200)[0], pt(0, -1_200)[1] + 7.5),
                   f"{y_ / 1000:.0f}", TXT["micro"], "middle", cor="#777")
    cv.texto_p((pt(20_000, 0)[0], pt(0, -1_200)[1] + 11.5),
               "profundidade do lote, em metros a partir da testada",
               TXT["micro"], "middle", cor="#999")

    an.titulo_desenho(cv, (ox - 8, 196), "1",
                      "Perfil longitudinal do terreno e plataforma",
                      f"H 1:{ESC_H:.0f} · V 1:{ESC_H / EXAG:.0f}")

    # ---- tabelas
    y = _tabela(cv, (35, 210), "COTAS DO PROJETO — NAS DUAS PONTAS DA FAIXA DECLARADA",
                ["", "A 1 %", "A 2 %", "ORIGEM"],
                [["Natural na frente da casa", f"+{p1['cota_natural_frente']:.0f}",
                  f"+{p2['cota_natural_frente']:.0f}", "cota_natural(y) do caso"],
                 ["Natural no fundo da casa", f"+{p1['cota_natural_fundo']:.0f}",
                  f"+{p2['cota_natural_fundo']:.0f}", "cota_natural(y) do caso"],
                 ["Desnivel sob a casa", f"{p1['desnivel_mm']:.0f}",
                  f"{p2['desnivel_mm']:.0f}", f"em {p2['prof_mm'] / 1000:.1f} m de profundidade"],
                 ["Plataforma (topo da reposicao)", f"+{p1['cota_plataforma']:.0f}",
                  f"+{p2['cota_plataforma']:.0f}", "cota media: compensa corte e aterro"],
                 ["Piso acabado do terreo", f"+{p1['cota_piso_acabado']:.0f}",
                  f"+{p2['cota_piso_acabado']:.0f}",
                  f"plataforma + lastro {pj.RADIER['lastro']} + radier {pj.RADIER['espessura']}"],
                 ["Folga sobre a testada", f"{p1['cota_piso_acabado']:.0f}",
                  f"{p2['cota_piso_acabado']:.0f}", "protecao de enxurrada e saida por gravidade"]],
                larguras=[60, 20, 20, 92]) + 9

    y = _tabela(cv, (35, y), "REPOSICAO CONTROLADA — A ESPESSURA DEIXA DE SER UNICA",
                ["", "A 1 %", "A 2 %", "NOTA"],
                [["No fundo (lado alto)", f"{p1['reposicao_alto_mm']:.0f}",
                  f"{p2['reposicao_alto_mm']:.0f}", f"minimo admitido {tr.REPOSICAO_MIN_MM} mm"],
                 ["Na frente (lado baixo)", f"{p1['reposicao_baixo_mm']:.0f}",
                  f"{p2['reposicao_baixo_mm']:.0f}", "a plataforma e uma so"],
                 ["Media", f"{trat['remover_mm']}", f"{trat['remover_mm']}",
                  "e por isso o VOLUME nao muda"],
                 ["Camadas de 250 mm", f"{p1['camadas_alto']} a {p1['camadas_baixo']}",
                  f"{p2['camadas_alto']} a {p2['camadas_baixo']}",
                  "compactacao a 95 % do Proctor normal"],
                 ["Corte de regularizacao", "0,0 m3", "0,0 m3",
                  "cabe dentro da troca que o SPT obrigou"],
                 ["Aterro de regularizacao", "0,0 m3", "0,0 m3", "idem"]],
                larguras=[60, 20, 20, 92]) + 9

    _tabela(cv, (35, y), "ACESSO E ESCOAMENTO",
            ["", "A 1 %", "A 2 %", "CRITERIO"],
            [["Rampa de veiculos", f"{a1['rampa_pct']:.1f} %", f"{a2['rampa_pct']:.1f} %",
              f"confortavel ate {tr.RAMPA_CONFORTAVEL * 100:.0f} %, "
              f"limite {tr.RAMPA_MAX * 100:.0f} %"],
             ["Subida a vencer", f"{a1['subida_mm']:.0f} mm", f"{a2['subida_mm']:.0f} mm",
              f"no recuo de frente de {a2['corrida_mm'] / 1000:.1f} m"],
             ["Queda ate a rede publica",
              f"{pj.cota_natural(pj.LOTE_P, pj.DECLIVIDADE_MIN):.0f} mm",
              f"{g['queda_terreno_mm']:.0f} mm",
              "no sentido da sarjeta: sem elevatoria de esgoto"]],
            larguras=[60, 20, 20, 92])

    # ---- caixa de texto: por que custa zero
    cv.poli_p([(492, 40), (812, 40), (812, 122), (492, 122)], "fino",
              fechado=True, preenche="#fbfaf7", cor="#ddd")
    cv.texto_p((498, 48), "POR QUE A REGULARIZACAO CUSTA ZERO m3", TXT["peq"],
               "start", peso="bold")
    for i_, linha in enumerate([
            "O SPT reprovou o primeiro metro por uniformidade (N de 3 a 4) e obrigou",
            f"a remover {trat['remover_mm']} mm de solo em toda a area tratada, repondo",
            "material controlado. Essa escavacao ja ia acontecer.",
            "",
            "A plataforma fica na cota MEDIA do terreno sob a casa. Acima dela a",
            "reposicao afina, abaixo dela engrossa. Como a variacao e simetrica, o",
            "volume medio nao muda: a declividade inteira cabe dentro da troca.",
            "",
            "O que muda e executivo, nao orcamentario. A camada deixa de ter",
            "espessura unica, o numero de camadas de compactacao varia de ponta a",
            "ponta, e o nivelamento do topo da reposicao passa a ser item de",
            "conferencia de obra, com ensaio por camada e por area."]):
        cv.texto_p((498, 55 + i_ * 5.4), linha, TXT["micro"], "start", cor=CINZA)

    # ---- caixa de texto: o sitio confirmado
    cv.poli_p([(492, 130), (812, 130), (812, 200), (492, 200)], "fino",
              fechado=True, preenche="#fbfaf7", cor="#ddd")
    cv.texto_p((498, 138), "SITIO CONFIRMADO PELO PROPRIETARIO", TXT["peq"],
               "start", peso="bold")
    for i_, (k, v) in enumerate([
            ("Frente", pj.SITIO["frente"] + " (rua na testada)"),
            ("Fundos", pj.SITIO["fundos"]),
            ("Laterais", pj.SITIO["laterais"]),
            ("Topografia", "plana, 1 % a 2 % para a rua"),
            ("Vegetacao", "sem arvore grande na implantacao"),
            ("Entorno", "sem edificacao alta a Oeste ou Norte"),
            ("Ventilacao", "cruzada Norte-Sul"),
            ("Solo", "boletim SP-01/02/03 prevalece sobre a descricao")]):
        cv.texto_p((498, 146 + i_ * 5.4), k, TXT["micro"], "start", peso="bold")
        cv.texto_p((532, 146 + i_ * 5.4), v, TXT["micro"], "start", cor=CINZA)
    cv.texto_p((498, 146 + 8 * 5.4 + 2),
               "Pendencia 16: convencao de lateral esquerda/direita nos recuos. "
               "Pendencia 17: levantamento planialtimetrico fecha as cotas.",
               TXT["micro"], "start", cor="#c00")

    # ---- o vento que o sitio reabriu, e a resposta
    import nucleo.vento as _ve
    z = pj.TOPO_PLATIBANDA / 1000.0
    q = {c: _ve.pressao(_ve.vk(pj.V0_VENTO, z, c, pj.CLASSE_VENTO))
         for c in ("IV", "III")}
    _tabela(cv, (520, 215),
            "VENTO — ROBUSTEZ A CATEGORIA DE RUGOSIDADE (NBR 6123)",
            ["", "CAT. IV (declarada)", "CAT. III (lote aberto)", "LEITURA"],
            [["S2 no topo da platibanda", f"{_ve.s2(z, 'IV', pj.CLASSE_VENTO):.3f}",
              f"{_ve.s2(z, 'III', pj.CLASSE_VENTO):.3f}",
              f"z = {z:.2f} m, classe {pj.CLASSE_VENTO}"],
             ["Velocidade caracteristica",
              f"{_ve.vk(pj.V0_VENTO, z, 'IV', pj.CLASSE_VENTO):.1f} m/s",
              f"{_ve.vk(pj.V0_VENTO, z, 'III', pj.CLASSE_VENTO):.1f} m/s",
              f"V0 = {pj.V0_VENTO:.0f} m/s (isopleta de Manaus)"],
             ["Pressao dinamica", "referencia",
              f"+{(q['III'] / q['IV'] - 1) * 100:.0f} %",
              "a pressao e quadratica na velocidade"],
             ["Uso das fitas de contraventamento", "51 % (X) e 52 % (Y)",
              "64 % (X) e 64 % (Y)", "as duas passam"],
             ["Arrancamento no chumbador", "5,0 kN", "6,4 kN",
              "contra 12,0 kN do M10 de expansao"],
             ["Massa, pecas e custo", "identicos", "identicos",
              "o vento governa fita e chumbador, e os dois tem folga"]],
            larguras=[62, 40, 40, 78])
    cv.texto_p((520, 262),
               "O sitio diz que nao ha edificacao alta a Oeste nem a Norte, leitura que "
               "puxa para a Categoria III.", TXT["micro"], "start", cor=CINZA)
    cv.texto_p((520, 267),
               "Em vez de escolher a letra no olho, o projeto foi verificado nas duas. "
               "A duvida deixou de ser risco.", TXT["micro"], "start", cor=CINZA)

    return cv



# =========================================================================
# PR-48 — MATRIZ DE ENTREGAVEIS (a prancha mestre, item 621) (R69)
# =========================================================================
def entregaveis() -> Canvas:
    import nucleo.entregaveis as en
    r = en.resumo()
    ps = r["por_status"]
    cv = base("MATRIZ DE ENTREGAVEIS — PRANCHA MESTRE", "s/ escala", "48", notas=[
        f"{r['linhas']} itens pedidos pelo proprietario, {r['distintos']} entregaveis distintos "
        f"(sinonimos contam uma vez, no item que os resolve).",
        "TEM: existe e a referencia foi conferida pela auditoria 142. PARCIAL: o dado existe, "
        "a prancha propria nao. FALTA: produz-se do modelo, ainda nao produzido.",
        "EXTERNO: depende de levantamento, certidao ou obra. NA: nao se aplica a esta casa, "
        "com a razao escrita.",
        f"Resolvido (TEM + NA): {r['cobertura'] * 100:.0f} % dos distintos. "
        f"Backlog: {ps['FALTA']} entregaveis.",
    ])
    cor = {"TEM": "#2e7d32", "PARCIAL": "#b26a00", "FALTA": "#c62828",
           "EXTERNO": "#5c6bc0", "NA": "#757575"}
    # ---- resumo por bloco
    linhas = [[f"{l} · {b['nome'][:34]}", str(b["n"]), str(b["TEM"]), str(b["PARCIAL"]),
               str(b["FALTA"]), str(b["EXTERNO"]), str(b["NA"])]
              for l, b in r["por_bloco"].items()]
    linhas.append(["TOTAL", str(r["distintos"]), str(ps["TEM"]), str(ps["PARCIAL"]),
                   str(ps["FALTA"]), str(ps["EXTERNO"]), str(ps["NA"])])
    y = _tabela(cv, (30, 40), "RESUMO POR BLOCO — ENTREGAVEIS DISTINTOS",
                ["BLOCO", "N", "TEM", "PARC.", "FALTA", "EXT.", "NA"], linhas,
                larguras=[96, 14, 14, 16, 16, 14, 12], h_lin=4.4)
    # ---- barra de cobertura
    x0, w = 30, 182
    yb = y + 4
    cv.texto_p((x0, yb), "COBERTURA DOS ENTREGAVEIS DISTINTOS", TXT["micro"], "start", peso="bold")
    xx = x0
    for st in ("TEM", "NA", "PARCIAL", "FALTA", "EXTERNO"):
        wf = w * ps[st] / max(1, r["distintos"])
        cv.poli_p([(xx, yb + 3), (xx + wf, yb + 3), (xx + wf, yb + 9), (xx, yb + 9)],
                  "fino", fechado=True, preenche=cor[st], cor=cor[st])
        if wf > 9:
            cv.texto_p((xx + wf / 2, yb + 6.2), f"{st} {ps[st]}", TXT["micro"], "middle", cor="#fff")
        xx += wf
    # ---- a lista inteira, em colunas
    itens = en.itens()
    col_x = [232, 432, 632]
    col_w = 196
    y0, y1 = 40, 505
    h = 2.75
    por_col = int((y1 - y0) / h)
    for k, it in enumerate(itens):
        c = k // por_col
        if c >= len(col_x):
            break
        yy = y0 + (k % por_col) * h
        x = col_x[c]
        with cv.escopo("entregavel", str(it["n"]), status=it["status"], ref=it["ref"]):
            cv.poli_p([(x, yy - 1.0), (x + 2.2, yy - 1.0), (x + 2.2, yy + 1.0), (x, yy + 1.0)],
                      "fino", fechado=True, preenche=cor[it["status"]], cor=cor[it["status"]])
            nome = it["nome"][:38]
            ref = it["ref"] if it["ref"] else ("=" + str(it["sinonimo_de"]) if it["sinonimo_de"] else "")
            cv.texto_p((x + 4, yy + 0.7), f"{it['n']:>3} {nome}", 1.9, "start",
                       cor="#333" if it["status"] != "NA" else "#888")
            cv.texto_p((x + col_w - 2, yy + 0.7), ref[:22], 1.7, "end", cor=cor[it["status"]])
    for i_, st in enumerate(("TEM", "PARCIAL", "FALTA", "EXTERNO", "NA")):
        xx = 232 + i_ * 40
        cv.poli_p([(xx, 511), (xx + 3, 511), (xx + 3, 514), (xx, 514)], "fino",
                  fechado=True, preenche=cor[st], cor=cor[st])
        cv.texto_p((xx + 5, 513), st, TXT["micro"], "start", cor=cor[st])
    an.titulo_desenho(cv, (232, 522), "1", "Os 621 itens, com status e referencia", "s/ escala")
    return cv


# =========================================================================
# PR-49 — VENTILACAO NATURAL E PRIVACIDADE (R69)
# =========================================================================
def ventilacao() -> Canvas:
    import nucleo.ventilacao as vn
    amb = vn.por_ambiente(pj)
    pr = vn.privacidade(pj)
    cv = base("VENTILACAO NATURAL, CRUZADA E PRIVACIDADE", "1:100", "49", notas=[
        f"Area que ABRE por ambiente contra a area de piso. NBR 15575-4 exige "
        f"{vn.MINIMO_15575 * 100:.0f} % na regiao Norte; NBR 15220-3 recomenda "
        f"{vn.GRANDE_15220 * 100:.0f} % na ZB8 (aberturas grandes).",
        "Fracao que abre por familia (H): cortina e porta-balcao 100 %, janela de correr 50 %, "
        "basculante 33 %, porta opaca 0 %.",
        f"Privacidade pelo art. 1.301 do Codigo Civil: janela que olha a divisa a menos de "
        f"{vn.DIVISA_FRONTAL / 1000:.2f} m e proibida. O brise que protege esta nomeado.",
        "Seta em cada face com abertura; duas ou mais faces = ventilacao cruzada.",
    ])
    cor_face = {"L": "#c8651a", "O": "#2a7ab8", "N": "#2e7d32", "S": "#8e44ad"}

    def pavimento(pav, vw, titulo, num):
        ambs = pj.TERREO if pav == "T" else pj.SUPERIOR
        for a in ambs:
            r = next(x for x in amb if x["cod"] == a.cod)
            fill = ("#e8f5e9" if r["cruzada"] else "#fff8e1" if r["n_faces"] == 1 else "#f5f5f5")
            cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)), vw.pt(P(a.x + a.w, a.y + a.h)),
                       vw.pt(P(a.x, a.y + a.h))], "vista", fechado=True, preenche=fill, cor="#888")
            c = vw.pt(P(a.cx, a.cy))
            cv.texto_p((c[0], c[1] - 2.2), a.nome[:18], TXT["micro"], "middle", peso="bold")
            cv.texto_p((c[0], c[1] + 0.6), f"{r['fracao'] * 100:.0f} % abre · "
                       f"{'cruzada' if r['cruzada'] else 'unilateral' if r['n_faces'] else 'sem abertura'}",
                       TXT["micro"], "middle", cor=CINZA)
            for f in r["faces"]:
                d = 700
                if f == "L":   p0, p1 = (a.cx, a.y - d), (a.cx, a.y + d)
                elif f == "O": p0, p1 = (a.cx, a.y + a.h + d), (a.cx, a.y + a.h - d)
                elif f == "N": p0, p1 = (a.x + a.w + d, a.cy), (a.x + a.w - d, a.cy)
                else:          p0, p1 = (a.x - d, a.cy), (a.x + d, a.cy)
                cv.linha_p(vw.pt(P(*p0)), vw.pt(P(*p1)), "corte", cor=cor_face[f])
                e = vw.pt(P(*p1))
                cv.circ_p(e, 0.7, "fino", preenche=cor_face[f], cor=cor_face[f])
        an.titulo_desenho(cv, (vw.ox, 258), num, titulo, "1:100")

    pavimento("T", View(100, 30, 245, pj.RECUO_ESQ, pj.RECUO_FRENTE), "TERREO — faces que abrem", "1")
    pavimento("S", View(100, 300, 245, pj.RECUO_ESQ, pj.RECUO_FRENTE), "SUPERIOR — faces que abrem", "2")

    linhas = [[r["cod"], r["nome"][:22], r["categoria"], f"{r['piso_m2']:.1f}", f"{r['abre_m2']:.2f}",
               f"{r['fracao'] * 100:.0f} %", ",".join(r["faces"]) or "—",
               ("cruzada" if r["cruzada"] else "unilateral" if r["n_faces"] else "—"),
               ("OK" if r["atende_15575"] else "FALHA" if r["atende_15575"] is False else "n/e")]
              for r in amb]
    y = _tabela(cv, (30, 272), "VENTILACAO POR AMBIENTE",
                ["COD", "AMBIENTE", "CAT.", "PISO m2", "ABRE m2", "FRACAO", "FACES", "TIPO", "15575"],
                linhas, larguras=[16, 46, 20, 18, 18, 16, 16, 22, 16], h_lin=4.6) + 8
    linhas = [[p["tipo"], p["amb"], p["face"], f"{p['distancia_divisa'] / 1000:.2f}",
               (f"{p['minimo_legal'] / 1000:.2f}" if p["vizinho"] else "—"),
               f"{p['peitoril']}", p["brise"] or "—", p["leitura"], "OK" if p["legal"] else "ILEGAL"]
              for p in pr]
    _tabela(cv, (30, y), "PRIVACIDADE — CADA JANELA CONTRA A DIVISA QUE OLHA (art. 1.301 CC)",
            ["VAO", "AMB", "FACE", "DIST. m", "MIN. m", "PEITORIL", "BRISE", "LEITURA", ""],
            linhas, larguras=[16, 20, 14, 18, 16, 20, 18, 46, 16], h_lin=4.4)
    return cv
