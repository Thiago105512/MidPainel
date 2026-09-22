"""R70 — LOTE 1 DO BACKLOG DA MATRIZ: cortes por comodo, elevacoes derivadas,
esquadrias detalhadas, mapa de cores e planta humanizada.

Regra deste modulo, que vale para os lotes seguintes: nenhuma peca desenhada a
mao. A PR-15 (R03) tem elevacoes com modulos digitados um a um; as daqui saem
de ARMARIOS, BANCADAS, LAYOUT, LOUCAS e EQUIPAMENTOS — se um armario mudar de
largura no caso, a elevacao muda junto, e a auditoria de alcance (138) passa
a ver cada codigo tambem nestas pranchas.

  50  CORTES POR AMBIENTE — garagem, cozinha, gourmet, master, banhos, e o
      corte construtivo de fachada do radier a fascia (itens 84-89, 93)
  51  ELEVACOES INTERNAS II — lavanderia, quartos, closet, office, gourmet e
      paineis de TV, derivadas do modelo (100, 102-106)
  52  ESQUADRIAS — cada familia em elevacao com quantidade, vidro e peitoril,
      e os detalhes de peitoril, soleira, trilho e portao (108, 112-115, 119-123)
  53  MAPA DE CORES, RODAPES, SOLEIRAS E PEITORIS (72-76)
  54  PLANTA HUMANIZADA — pisos com a cor do acabamento e o mobiliario (51)
"""
from __future__ import annotations

import projeto as pj
import anotacao as an
import mobiliario as mb
from core import P, Canvas, View, TXT, CINZA, PRETO
from pranchas import base, _tabela, _extremos
from pranchas2 import _desenhar_corte, LAJE, RADIER

# cor de piso por palavra-chave do acabamento (H: paleta de apresentacao)
COR_PISO = [("porcelanato", "#e9e6df"), ("wpc", "#c9a37a"), ("deck", "#c9a37a"),
            ("ceramic", "#dfe4e6"), ("cimentic", "#cfcac1"), ("concreto", "#cfcac1"),
            ("vinil", "#e6dccb"), ("madeira", "#d7b98e"), ("grama", "#cfe3c4"),
            ("seixo", "#e2ddd2"), ("epoxi", "#d9dde2")]
ALTURA_MOVEL = {"guarda-roupa": 2_200, "gaveteiro": 900, "rouparia": 2_200,
                "prateleiras": 1_800, "armario alto": 2_200, "bancada": 900,
                "cabeceira": 1_200, "tv": 80, "rack": 450, "cama": 450,
                "geladeira": 1_900, "lavadora": 850, "secadora": 850, "tanque": 900,
                "lava-loucas": 850, "forno": 600, "micro-ondas": 400}
COR_MOVEL = {"guarda-roupa": "#f1ede4", "gaveteiro": "#f1ede4", "rouparia": "#f1ede4",
             "prateleiras": "#f1ede4", "armario alto": "#f1ede4", "bancada": "#e8e8e8",
             "cabeceira": "#e5d9c8", "tv": "#2b2f33", "rack": "#e5d9c8", "cama": "#efe9dd",
             "geladeira": "#dfe9f2", "lavadora": "#dfe9f2", "secadora": "#dfe9f2",
             "tanque": "#dfe9f2", "lava-loucas": "#dfe9f2"}


def _cor_piso(desc: str) -> str:
    d = (desc or "").lower()
    for k, c in COR_PISO:
        if k in d:
            return c
    return "#f0f0f0"


# =========================================================================
# PR-50 — CORTES POR AMBIENTE + CORTE CONSTRUTIVO DE FACHADA
# =========================================================================
def _amb(cod):
    return next(a for a in pj.TERREO + pj.SUPERIOR if a.cod == cod)


def cortes_por_ambiente() -> Canvas:
    cv = base("CORTES POR AMBIENTE E CORTE DE FACHADA", "1:50 · 1:25", "50", notas=[
        "Cada corte passa pelo centro do ambiente que o nomeia; o plano e o eixo estao "
        "na planta-chave ao lado do titulo.",
        f"Pe-direito {pj.PE_DIREITO} mm; piso a piso {pj.PISO_A_PISO} mm; radier {RADIER} mm.",
        "Corte construtivo de fachada: do radier a fascia, com as camadas da PE-1 "
        "(PR-13) e a fascia de aluminio grafite (R67).",
        "Cortes gerados pelo mesmo desenhador dos cortes AA e BB (PR-06).",
    ])
    x0, y0, x1, y1 = _extremos(pj.TERREO)
    planos = [("T-GAR", "V", "GARAGEM", "1"), ("T-COZ", "H", "COZINHA", "2"),
              ("T-GOU", "H", "GOURMET", "3"), ("S-MAS", "V", "SUITE MASTER", "4"),
              ("S-S02", "H", "BANHOS DAS SUITES 02 E 03", "5")]
    pos = [(28, 150), (285, 150), (545, 150), (28, 330), (285, 330)]
    for (cod, eixo, nome, num), (ox, oy) in zip(planos, pos):
        a = _amb(cod)
        coord = int(a.cy) if eixo == "H" else int(a.cx)
        ini, fim = (x0, x1) if eixo == "H" else (y0, y1)
        with cv.escopo("corte", cod, eixo=eixo, coord=str(coord)):
            with cv.recorte(ox - 4, oy - 150, ox + 240, oy + 12):
                _desenhar_corte(cv, View(50, ox, oy, ini, 0), eixo, coord, num, ini, fim)
        an.titulo_desenho(cv, (ox, oy + 30), num, f"CORTE {num}-{num} — {nome}", "1:50")
        # planta-chave
        kx, ky = ox + 190, oy + 24
        k = 40.0 / max(pj.LOTE_L, pj.LOTE_P)
        for q in pj.TERREO:
            cv.poli_p([(kx + q.y * k, ky - q.x * k), (kx + (q.y + q.h) * k, ky - q.x * k),
                       (kx + (q.y + q.h) * k, ky - (q.x + q.w) * k), (kx + q.y * k, ky - (q.x + q.w) * k)],
                      "cota", fechado=True, preenche="#f4f4f4" if q.cod != cod else "#dfe9f2", cor="#bbb")
        if eixo == "H":
            cv.linha_p((kx + coord * k, ky - x0 * k), (kx + coord * k, ky - x1 * k), "fino", cor="#c00", dash="2 1")
        else:
            cv.linha_p((kx + y0 * k, ky - coord * k), (kx + y1 * k, ky - coord * k), "fino", cor="#c00", dash="2 1")

    # ---- corte construtivo de fachada, 1:20, do radier a fascia
    # entre o corte 3 (ate y=180) e o carimbo (y=523), a esquerda das notas (x=655)
    ox, oy = 592, 478
    vw = View(25, ox, oy, 0, 0)
    fa = pj.FASCIA
    z_top = pj.TOPO_PLATIBANDA
    pat_cc = cv.hachura_dupla("cc50", espac=1.1, w=0.06, cor="#666")
    def ret(x, z, w, h, estilo="corte", preenche="#fff", cor=None):
        cv.poli_p([vw.pt(P(x, z)), vw.pt(P(x + w, z)), vw.pt(P(x + w, z + h)), vw.pt(P(x, z + h))],
                  estilo, fechado=True, preenche=preenche, cor=cor)
    # radier e reposicao
    ret(-600, -RADIER, 1_200, RADIER, preenche=f"url(#{pat_cc})")
    ret(-600, -RADIER - pj.RADIER["lastro"], 1_200, pj.RADIER["lastro"], "fino", "#e8e2d4")
    # parede PE-1: placa externa, montante, placa interna (espessuras da familia)
    ret(0, 0, 150, pj.PE_DIREITO, preenche="#f7f5f0")
    ret(-12, 0, 12, pj.PE_DIREITO, preenche="#ebe7e0", cor="#888")       # mineral
    ret(150, 0, 12, pj.PE_DIREITO, preenche="#f0eee8", cor="#888")       # gesso
    cv.texto_p(vw.pt(P(75, pj.PE_DIREITO / 2)), "PE-1", TXT["micro"], "middle", rot=90)
    # laje de entrepiso e parede do superior
    ret(-150, pj.PE_DIREITO, 1_200, LAJE, preenche=f"url(#{pat_cc})")
    ret(0, pj.PISO_A_PISO, 150, pj.PE_DIREITO, preenche="#f7f5f0")
    ret(-12, pj.PISO_A_PISO, 12, pj.PE_DIREITO, preenche="#ebe7e0", cor="#888")
    # laje de cobertura, platibanda e fascia
    zc = pj.PISO_A_PISO + pj.PE_DIREITO
    ret(-150, zc, 1_200, LAJE, preenche=f"url(#{pat_cc})")
    ret(0, zc + LAJE, 150, z_top - zc - LAJE, "corte2", "#f7f5f0")
    ret(-fa["espessura"] - 12, z_top - fa["altura"], fa["espessura"], fa["altura"] + fa["espessura"],
        preenche="#4a4f55", cor="#4a4f55")
    ret(-fa["espessura"] - 12, z_top, 150 + fa["espessura"] + 24, fa["espessura"], preenche="#4a4f55", cor="#4a4f55")
    for z, rot in ((0, "piso terreo +0,00"), (pj.PE_DIREITO, f"forro +{pj.PE_DIREITO / 1000:.2f}"),
                   (pj.PISO_A_PISO, f"piso superior +{pj.PISO_A_PISO / 1000:.2f}"),
                   (zc, f"laje de cobertura +{zc / 1000:.2f}"), (z_top, f"topo da fascia +{z_top / 1000:.2f}")):
        p = vw.pt(P(600, z))
        cv.linha_p(vw.pt(P(-700, z)), p, "cota", cor="#999", dash="2 2")
        cv.texto_p((p[0] + 2, p[1]), rot.replace(".", ","), TXT["micro"], "start", cor="#666")
    cv.texto_p(vw.pt(P(-700, -RADIER - 500)), "reposicao controlada (PR-47)", TXT["micro"], "start", cor="#8a6d3b")
    cv.texto_p(vw.pt(P(-40, z_top - fa["altura"] / 2)), f"fascia {fa['altura']} mm", TXT["micro"], "end", cor="#4a4f55")
    an.titulo_desenho(cv, (ox - 50, oy + 22), "6", "CORTE DE FACHADA — PE-1, RADIER A FASCIA", "1:25")
    return cv


# =========================================================================
# PR-51 — ELEVACOES INTERNAS II, DERIVADAS DO MODELO
# =========================================================================
def _elevacao_derivada(cv, vw, a, face: str, titulo: str, num: str):
    """Vista frontal da parede `face` do ambiente `a`, com o que o caso poe nela.

    Um item do caso "esta" na parede quando encosta nela a menos de 150 mm.
    O eixo horizontal do desenho corre ao longo da parede; a largura e a do
    ambiente. Moveis (ARMARIOS), bancadas, loucas, equipamentos e LAYOUT
    entram com a altura da familia (ALTURA_MOVEL); janela e porta da parede
    entram da lista de VAOS.
    """
    h = pj.PE_DIREITO
    larg = a.w if face in ("L", "O") else a.h
    z0 = 0 if a.pav == "T" else pj.NIVEL_SUPERIOR

    def ao_longo(it):          # posicao e largura do item ao longo da parede
        if face in ("L", "O"):
            return it["x"] - a.x, it["w"]
        return it["y"] - a.y, it["h"]

    def encosta(it):
        tol = 150
        if face == "L": return abs(it["y"] - a.y) <= tol
        if face == "O": return abs(it["y"] + it["h"] - (a.y + a.h)) <= tol
        if face == "S": return abs(it["x"] - a.x) <= tol
        return abs(it["x"] + it["w"] - (a.x + a.w)) <= tol

    pecas = []
    for lista in (pj.ARMARIOS, pj.BANCADAS, pj.EQUIPAMENTOS, pj.LOUCAS, pj.LAYOUT):
        for it in lista:
            if it.get("amb", "").split("/")[0] != a.cod or not all(k in it for k in ("x", "y", "w", "h")):
                continue
            if not encosta(it):
                continue
            u, w = ao_longo(it)
            tipo = it.get("tipo", "")
            alt = ALTURA_MOVEL.get(tipo, 900)
            zb = 0
            if tipo == "tv": zb = 1_100
            if tipo == "rack": zb = 0
            pecas.append((u, zb, w, alt, f"{it['cod']} {tipo}"[:22], COR_MOVEL.get(tipo, "#eeeeee"), it["cod"]))
    # vaos na parede
    for tipo, x, y, ori, pav in pj.VAOS:
        if pav != a.pav:
            continue
        lg, al, pe, _ = pj.ESQUADRIAS[tipo]
        na_face = ((face == "L" and ori == "H" and abs(y - a.y) <= 150 and a.x <= x <= a.x + a.w) or
                   (face == "O" and ori == "H" and abs(y - (a.y + a.h)) <= 150 and a.x <= x <= a.x + a.w) or
                   (face == "S" and ori == "V" and abs(x - a.x) <= 150 and a.y <= y <= a.y + a.h) or
                   (face == "N" and ori == "V" and abs(x - (a.x + a.w)) <= 150 and a.y <= y <= a.y + a.h))
        if na_face:
            u = (x - a.x if face in ("L", "O") else y - a.y) - lg / 2
            pecas.append((u, pe, lg, al, tipo, "#dfeef7" if tipo.startswith(("J", "PV", "CV")) else "#e5d3bd", tipo))

    cv.poli_p([vw.pt(P(0, 0)), vw.pt(P(larg, 0)), vw.pt(P(larg, h)), vw.pt(P(0, h))],
              "corte", fechado=True, preenche="#fff")
    for u, zb, w, alt, rot, cor, cod in sorted(pecas, key=lambda p: -p[3]):
        with cv.escopo("elevacao", cod, amb=a.cod, face=face):
            cv.poli_p([vw.pt(P(u, zb)), vw.pt(P(u + w, zb)), vw.pt(P(u + w, zb + alt)), vw.pt(P(u, zb + alt))],
                      "vista", fechado=True, preenche=cor)
            if w > 400 and alt > 250:
                cv.texto_p(vw.pt(P(u + w / 2, zb + alt / 2)), rot, TXT["micro"], "middle", cor="#333")
    an.cadeia(cv, vw, [0, larg], 0, "H", 10)
    an.cadeia(cv, vw, [0, 900, 2_200, h], 0, "V", -10)
    cv.texto_p(vw.pt(P(larg / 2, h + 500)), f"{num}. {titulo}", TXT["peq"], "middle", peso="bold")
    cv.texto_p(vw.pt(P(larg / 2, -700)), f"{len(pecas)} itens do caso nesta parede", TXT["micro"], "middle", cor=CINZA)
    return len(pecas)


def _itens_na_face(a, face: str) -> int:
    """Quantos itens do caso encostam na parede `face` do ambiente."""
    n = 0
    tol = 150
    for lista in (pj.ARMARIOS, pj.BANCADAS, pj.EQUIPAMENTOS, pj.LOUCAS, pj.LAYOUT):
        for it in lista:
            if it.get("amb", "").split("/")[0] != a.cod or not all(k in it for k in ("x", "y", "w", "h")):
                continue
            if ((face == "L" and abs(it["y"] - a.y) <= tol) or
                    (face == "O" and abs(it["y"] + it["h"] - (a.y + a.h)) <= tol) or
                    (face == "S" and abs(it["x"] - a.x) <= tol) or
                    (face == "N" and abs(it["x"] + it["w"] - (a.x + a.w)) <= tol)):
                n += 1
    return n


def _melhor_face(a) -> str:
    """A parede com mais itens do caso: e a que vale desenhar."""
    return max(("L", "O", "S", "N"), key=lambda f: _itens_na_face(a, f))


def elevacoes_derivadas() -> Canvas:
    cv = base("ELEVACOES INTERNAS II — DERIVADAS DO MODELO", "1:40", "51", notas=[
        "Cada item desenhado vem de ARMARIOS, BANCADAS, LOUCAS, EQUIPAMENTOS ou LAYOUT do caso, "
        "pelo codigo; nenhum modulo foi digitado nesta prancha.",
        "Um item esta na parede quando encosta nela a menos de 150 mm. Alturas por familia (H).",
        "Janelas e portas da parede vem de VAOS, com peitoril e altura da esquadria.",
        "Complementa a PR-15 (cozinha, gourmet, lavabo, banho master, oficina, lavanderia).",
    ])
    NOME_FACE = {"L": "leste", "O": "oeste", "S": "sul", "N": "norte"}
    comodos = ["T-LAV", "S-S02", "S-S03", "S-MAS", "T-GOU", "T-SOC", "S-LOU", "T-REV", "T-COZ"]
    esc = 40
    col_w = 262
    for i, cod in enumerate(comodos):
        a = _amb(cod)
        face = _melhor_face(a)          # a parede com mais itens do caso, nao a que eu escolhi
        tit = f"{a.nome} — parede {NOME_FACE[face]} ({_itens_na_face(a, face)} itens)"
        ox = 42 + (i % 3) * col_w       # a cadeia vertical fica 10 mm a esquerda de ox
        oy = 150 + (i // 3) * 160
        _elevacao_derivada(cv, View(esc, ox, oy, 0, 0), a, face, tit, str(i + 1))
    return cv


# =========================================================================
# PR-52 — ESQUADRIAS: TIPOS, QUANTIDADES E DETALHES
# =========================================================================
def esquadrias() -> Canvas:
    import collections
    cv = base("ESQUADRIAS — TIPOS, QUANTIDADES E DETALHES", "1:40 · 1:5", "52", notas=[
        "Uma elevacao por familia em uso, com largura x altura, peitoril, quantidade e o vidro "
        "que a regra de fator solar atribui (projeto.vidro_do_vao).",
        "Familias declaradas SEM USO (J03, PV01) ficam fora: esquadria que nao esta em VAOS "
        "nao e comprada.",
        "Detalhes 1:5 — peitoril com pingadeira, soleira de porta externa, trilho e roldana da "
        "porta de correr, ripa e guia do portao — sao os quatro encontros que decidem a "
        "estanqueidade.",
        "Aluminio grafite em todas as familias (FACHADA_MATERIAIS); sem PVC, sem veneziana.",
    ])
    uso = collections.Counter(t for t, *_ in pj.VAOS)
    faces = collections.defaultdict(set)
    for t, x, y, o, p in pj.VAOS:
        if pj.vao_externo(x, y, o, p):
            faces[t].add(pj.face_do_vao(x, y, o, p))
    tipos = [t for t in pj.ESQUADRIAS if uso.get(t)]
    # 1:40: a familia mais alta (P01, 2.800 + titulo) ocupa 88 mm acima da linha
    # de base e 23 abaixo; duas linhas de 120 mm cabem sobre os detalhes de y=500
    esc = 40
    X0, LIMITE, PITCH = 40, 530, 120
    ox, oy = X0, 130
    for i, t in enumerate(tipos):
        lg, al, pe, desc = pj.ESQUADRIAS[t]
        if ox + lg / esc + 12 > LIMITE:
            ox, oy = X0, oy + PITCH
        vw = View(esc, ox, oy, 0, 0)
        vidro = pj.vidro_do_vao(t, sorted(faces[t])[0])[0] if faces[t] and t.startswith(("J", "PV", "CV")) else "—"
        with cv.escopo("esquadria", t, qtd=str(uso[t])):
            cv.linha_p(vw.pt(P(-300, 0)), vw.pt(P(lg + 300, 0)), "cota", cor="#999")
            cv.poli_p([vw.pt(P(0, pe)), vw.pt(P(lg, pe)), vw.pt(P(lg, pe + al)), vw.pt(P(0, pe + al))],
                      "corte", fechado=True, preenche="#dfeef7" if t.startswith(("J", "PV", "CV")) else "#e5d3bd")
            # folhas
            n_folhas = 8 if t == "CV01" else (2 if t in ("PV02", "J05", "J01", "PG01") else 1)
            if t == "PG01":
                for r in range(0, int(lg), 150):
                    cv.linha_p(vw.pt(P(r, pe)), vw.pt(P(r, pe + al)), "fino", cor="#4a4f55")
            else:
                for f in range(1, n_folhas):
                    cv.linha_p(vw.pt(P(lg * f / n_folhas, pe)), vw.pt(P(lg * f / n_folhas, pe + al)), "fino", cor="#666")
            if t.startswith("J") and t != "J04":
                cv.linha_p(vw.pt(P(0, pe)), vw.pt(P(lg / n_folhas, pe + al)), "cota", cor="#999", dash="2 2")
            an.cadeia(cv, vw, [0, lg], pe + al, "H", -8)
            if pe:
                an.cadeia(cv, vw, [0, pe, pe + al], lg, "V", 8)
            else:
                an.cadeia(cv, vw, [0, al], lg, "V", 8)
            cv.texto_p(vw.pt(P(lg / 2, pe + al + 700)), f"{t} — {uso[t]} un", TXT["peq"], "middle", peso="bold")
            cv.texto_p(vw.pt(P(lg / 2, -500)), desc[:48], TXT["micro"], "middle", cor=CINZA)
            cv.texto_p(vw.pt(P(lg / 2, -900)), f"vidro: {vidro[:44]}" if vidro != "—" else "folha opaca", TXT["micro"], "middle", cor="#2a7ab8")
        ox += lg / esc + 30
    # ---- detalhes 1:5
    def det(ox, oy, num, nome, blocos, notas):
        vw = View(5, ox, oy, 0, 0)
        for x, z, w, h, cor, rot in blocos:
            cv.poli_p([vw.pt(P(x, z)), vw.pt(P(x + w, z)), vw.pt(P(x + w, z + h)), vw.pt(P(x, z + h))],
                      "corte", fechado=True, preenche=cor)
            if rot:
                c = vw.pt(P(x + w / 2, z + h / 2)); cv.texto_p(c, rot, TXT["micro"], "middle")
        for i, n in enumerate(notas):
            cv.texto_p((ox, oy + 6 + i * 3.6), "- " + n, TXT["micro"], "start", cor=CINZA)
        an.titulo_desenho(cv, (ox, oy + 6 + len(notas) * 3.6 + 6), num, nome, "1:5")
    det(40, 500, "A", "PEITORIL COM PINGADEIRA", [
        (0, 0, 150, 60, "#f7f5f0", "parede PE-1"), (-40, 60, 230, 30, "#d8d3c8", "granito 30 mm"),
        (-40, 40, 20, 20, "#d8d3c8", ""), (150, 90, 60, 220, "#dfeef7", "caixilho")],
        ["granito 30 mm com pingadeira de 20 mm e caimento de 5 % para fora",
         "selante PU entre caixilho e peitoril; fita de estanqueidade na guia"])
    det(170, 500, "B", "SOLEIRA DE PORTA EXTERNA", [
        (0, -60, 300, 60, "#cfcac1", "radier"), (0, 0, 150, 30, "#d8d3c8", "soleira granito"),
        (150, 0, 150, 12, "#e9e6df", "piso interno"), (60, 30, 40, 200, "#e5d3bd", "folha")],
        ["soleira em granito 30 mm nivelada com o piso interno (NBR 9050: sem degrau)",
         "rebaixo de 12 mm no lado externo para a agua nao entrar"])
    det(300, 500, "C", "TRILHO E ROLDANA — PORTA DE CORRER", [
        (0, -30, 300, 30, "#cfcac1", "piso"), (100, 0, 100, 25, "#4a4f55", "trilho"),
        (125, 25, 50, 40, "#888", "roldana"), (130, 65, 40, 200, "#dfeef7", "folha")],
        ["trilho de aluminio embutido no piso, drenado para fora",
         "roldana de nylon com rolamento; duas por folha; fecho com trava"])
    det(430, 500, "D", "PORTAO RIPADO — RIPA E GUIA", [
        (0, 0, 40, 240, "#4a4f55", ""), (150, 0, 40, 240, "#4a4f55", ""), (300, 0, 40, 240, "#4a4f55", ""),
        (0, 240, 340, 30, "#4a4f55", "travessa"), (0, -30, 340, 30, "#6b6f75", "guia inferior")],
        ["ripa 40 x 100 mm de aluminio grafite a cada 150 mm, em travessa de 30 mm",
         "guia inferior embutida; motor deslizante 1/3 cv (BOM)"])
    return cv


# =========================================================================
# PR-53 — MAPA DE CORES, RODAPES, SOLEIRAS E PEITORIS
# =========================================================================
def mapa_de_cores() -> Canvas:
    import modelo3d as m3
    cv = base("MAPA DE CORES, RODAPES, SOLEIRAS E PEITORIS", "s/ escala", "53", notas=[
        "Cores de fachada de FACHADA_MATERIAIS e da cena 3D (modelo3d.CORES): a amostra aqui "
        "e a mesma que o visualizador e o render usam.",
        "Rodape por ambiente de acabamentos(); soleira por porta externa e peitoril por janela, "
        "derivados de VAOS e ESQUADRIAS.",
        "Textura: junta seca de 6 mm no mineral 1.200 x 2.400; ripa de 40 mm a cada 150 no "
        "aluminio; madeira em regua de 100 mm.",
    ])
    paleta = [("Mineral claro de grande formato", m3.CORES["parede_ext"], "volume superior e face externa da platibanda"),
              ("Base pintada do terreo", m3.CORES["parede_base"], "acrilico elastomerico, alfa 0,30"),
              ("Aluminio grafite", m3.CORES["fascia"], "portao, brises, guarda-corpo, fascia, caixilhos"),
              ("Madeira", m3.CORES["porta"], "folha da porta de entrada e forro do portico"),
              ("Deck WPC", m3.CORES["deck"], "deck da piscina e varandas"),
              ("Vidro low-e", m3.CORES["vidro"], "cortina e face oeste"),
              ("Muro", m3.CORES["muro"], "reboco pintado, mesma base do terreo"),
              ("Piso interno", "#e9e6df", "porcelanato 900 x 900 acetinado")]
    y = 44
    cv.texto_p((30, y), "PALETA — FAMILIAS DE MATERIAL E ONDE VAO", TXT["peq"], "start", peso="bold")
    for i, (nome, cor, onde) in enumerate(paleta):
        xx = 30 + (i % 4) * 195
        yy = y + 8 + (i // 4) * 62
        cv.poli_p([(xx, yy), (xx + 180, yy), (xx + 180, yy + 40), (xx, yy + 40)], "fino",
                  fechado=True, preenche=cor, cor="#666")
        cv.texto_p((xx, yy + 46), nome, TXT["peq"], "start", peso="bold")
        cv.texto_p((xx, yy + 51), f"{cor}  ·  {onde}", TXT["micro"], "start", cor=CINZA)
    # rodapes
    acab = pj.acabamentos()
    linhas = [[a["amb"], a["nome"][:22], (a.get("rodape") or "—")[:44], (a.get("piso") or "")[:30]]
              for a in acab if not a.get("subdivisao")]
    _tabela(cv, (30, 185), "RODAPES POR AMBIENTE", ["COD", "AMBIENTE", "RODAPE", "PISO"],
            linhas, larguras=[16, 50, 100, 80], h_lin=4.6)
    y = 185
    # soleiras: portas externas
    sol = []
    for t, x, yv, o, p in pj.VAOS:
        if t.startswith(("P", "PG", "PV", "CV")) and pj.vao_externo(x, yv, o, p):
            mat = ("sem soleira: guia embutida" if t == "PG01" else
                   "trilho de aluminio drenado" if t in ("PV02", "CV01") else "granito 30 mm nivelado")
            sol.append([t, pj.amb_do_vao(x, yv, p), pj.face_do_vao(x, yv, o, p), mat])
    y = _tabela(cv, (300, y), "SOLEIRAS — PORTAS EXTERNAS", ["VAO", "AMB", "FACE", "SOLEIRA"],
                sol, larguras=[16, 22, 14, 170], h_lin=4.6) + 10
    pei = []
    for t, x, yv, o, p in pj.VAOS:
        if t.startswith("J") and pj.vao_externo(x, yv, o, p):
            lg, al, pe, _ = pj.ESQUADRIAS[t]
            pei.append([t, pj.amb_do_vao(x, yv, p), pj.face_do_vao(x, yv, o, p), f"{pe}",
                        "granito 30 mm com pingadeira (det. A da PR-52)"])
    _tabela(cv, (300, y), "PEITORIS — JANELAS", ["VAO", "AMB", "FACE", "PEITORIL mm", "MATERIAL"],
            pei, larguras=[16, 22, 14, 26, 144], h_lin=4.6)
    return cv


# =========================================================================
# PR-54 — PLANTA HUMANIZADA
# =========================================================================
def humanizada() -> Canvas:
    # 1:100 e nao 1:75: o terreo humanizado inclui as areas abertas ate o fundo
    # do lote (39,6 m), e a 1:75 sao 528 mm de desenho numa folha de 574 uteis
    cv = base("PLANTA HUMANIZADA — TERREO E SUPERIOR", "1:100", "54", notas=[
        "Piso de cada ambiente na cor do acabamento declarado (acabamentos()); mobiliario de "
        "LAYOUT, ARMARIOS, BANCADAS e LOUCAS.",
        "Areas abertas com o piso externo declarado (deck, grama, seixo).",
        "Sem cota: a leitura e de uso, nao de execucao. Cotas na PR-02/03.",
    ])
    acab = {a["amb"]: a for a in pj.acabamentos()}

    def pavimento(pav, vw, titulo, num):
        ambs = (pj.TERREO + pj.TERREO_ABERTO) if pav == "T" else pj.SUPERIOR
        for a in ambs:
            piso = (acab.get(a.cod) or {}).get("piso") or getattr(a, "piso", "")
            cor = _cor_piso(piso)
            with cv.escopo("piso", a.cod, piso=piso[:30]):
                cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)), vw.pt(P(a.x + a.w, a.y + a.h)),
                           vw.pt(P(a.x, a.y + a.h))], "vista", fechado=True, preenche=cor, cor="#777")
            c = vw.pt(P(a.cx, a.cy))
            cv.texto_p((c[0], c[1] - 1.6), a.nome[:20], TXT["micro"], "middle", peso="bold")
            cv.texto_p((c[0], c[1] + 1.4), (piso or "")[:26], TXT["micro"], "middle", cor="#555")
        for d in pj.SUBDIVISOES:
            if (d["pai"].startswith("S-")) != (pav == "S"):
                continue
            cv.poli_p([vw.pt(P(d["x"], d["y"])), vw.pt(P(d["x"] + d["w"], d["y"])),
                       vw.pt(P(d["x"] + d["w"], d["y"] + d["h"])), vw.pt(P(d["x"], d["y"] + d["h"]))],
                      "fino", fechado=True, preenche="#dfe4e6" if d.get("molhado") else "none", cor="#888")
        mb.desenhar(cv, vw, pav, layout=True)
        if pav == "T":
            mb.piscina(cv, vw)
        an.titulo_desenho(cv, (vw.ox, 500), num, titulo, "1:100")

    pavimento("T", View(100, 40, 470, pj.RECUO_ESQ, 0), "TERREO — HUMANIZADA", "1")
    pavimento("S", View(100, 300, 470, pj.RECUO_ESQ, pj.RECUO_FRENTE), "SUPERIOR — HUMANIZADA", "2")
    # legenda de pisos
    usados = {}
    for a in pj.acabamentos():
        k = _cor_piso(a.get("piso") or "")
        usados.setdefault(k, (a.get("piso") or "")[:40])
    for i, (cor, nome) in enumerate(usados.items()):
        yy = 44 + i * 6
        cv.poli_p([(560, yy), (568, yy), (568, yy + 4), (560, yy + 4)], "fino", fechado=True, preenche=cor, cor="#666")
        cv.texto_p((571, yy + 3), nome, TXT["micro"], "start", cor="#444")
    return cv
