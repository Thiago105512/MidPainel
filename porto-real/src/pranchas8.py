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
