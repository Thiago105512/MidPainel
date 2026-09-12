"""
Especificacao diferenciada por exigencia.

Principio: nao se especifica "superior em tudo". Cada vedacao, piso, forro e
vao recebe a composicao exigida pelo que acontece nos seus DOIS lados — e,
onde a exigencia nao existe, aplica-se a solucao simples. Gastar onde nao ha
demanda nao melhora o desempenho percebido; apenas encarece.

Coordenacao modular preservada: mantem-se as DUAS familias dimensionais do
briefing (150 mm externa/hidraulica e 100 mm interna). O que varia e a
COMPOSICAO dentro da mesma espessura — montante, la e numero de chapas.
Nenhum detalhe de vao, nenhum eixo e nenhuma cota muda.
"""
from __future__ import annotations

import math

import projeto as pj
import desempenho as dp
import anotacao as an
from core import P, Canvas, View, TXT, CINZA, PRETO
from pranchas import base, _tabela, _extremos

G = pj.GRID

# ------------------------------------------------------- categorias de uso
CATEGORIA = {
    "T-REV": "intimo", "S-S02": "intimo", "S-S03": "intimo", "S-MAS": "intimo",
    "T-SOC": "social", "T-GOU": "social", "T-COZ": "social",
    "T-LAV": "servico", "T-DEP": "servico", "T-DES": "servico",
    "T-OFI": "oficina",
    "T-HAL": "circulacao", "T-COR": "circulacao", "S-HAL": "circulacao",
    "T-GAR": "apoio", "T-BWC": "molhado",
}
MOLHADOS = {"T-BWC", "T-COZ", "T-LAV", "T-GOU"}
# a oficina e fonte E receptor: quer silencio para dentro e para fora
SILENCIO = {"T-OFI"}

# fontes de ruido relevantes: o que exige parede acustica do outro lado
FONTES = {"social", "apoio", "circulacao", "servico"}

# =========================================================================
# FAMILIAS — duas espessuras, quatro composicoes
# =========================================================================
FAMILIAS = {
    "PE-1": dict(
        esp=150, nome="Parede externa unica",
        comp="cimenticia 10 + XPS 20 (ISO strip) + montante 90 c/ la 50 + gesso 12,5 + acabamento",
        U=None, Rw=45, indice=1.12,
        onde="todas as faces externas, sem excecao",
        porque="O ISO strip continuo e, ao mesmo tempo, quebra termica e barreira "
               "de vapor do lado quente-umido. Sua funcao principal NAO e economia "
               "de energia (payback longo), e evitar condensacao no montante."),
    "PH-1": dict(
        esp=150, nome="Parede hidraulica interna",
        comp="gesso RU 12,5 + montante 90 c/ la 50 + gesso 12,5 + reforco para loucas",
        U=None, Rw=44, indice=1.20,
        onde="apenas onde passa prumada de esgoto DN100 ou ha louca suspensa",
        porque="A espessura de 150 mm existe para acomodar o tubo DN100. Usar 150 "
               "onde nao ha prumada e desperdicio de area util."),
    "PA-1": dict(
        esp=100, nome="Parede acustica",
        comp="dupla chapa 12,5 + montante 48 c/ la 48 + dupla chapa 12,5",
        U=None, Rw=49, indice=1.35,
        onde="intimo x fonte de ruido, social x servico, entorno do core e toda a oficina",
        porque="Dupla chapa e o unico ganho acustico barato: +5 dB por chapa "
               "adicional. Decupla-se a massa sem mudar a espessura modular."),
    "PI-1": dict(
        esp=100, nome="Divisoria interna simples",
        comp="gesso 12,5 + montante 70 c/ la 50 + gesso 12,5",
        U=None, Rw=41, indice=1.00,
        onde="dentro de zonas homogeneas (servico com servico, social com social)",
        porque="Rw 41 dB ja supera o minimo da NBR 15575-3 entre ambientes da "
               "mesma unidade. Reforcar aqui nao produz diferenca perceptivel."),
}


# =========================================================================
# classificacao das paredes a partir da malha
# =========================================================================
def paredes_classificadas(ambs) -> list[dict]:
    """Cada trecho de parede com os codigos dos ambientes que ele separa."""
    cel: dict[tuple[int, int], str] = {}
    for a in ambs:
        for i in range(a.x // G, (a.x + a.w) // G):
            for j in range(a.y // G, (a.y + a.h) // G):
                cel[(i, j)] = a.cod
    if not cel:
        return []
    imin, imax = min(i for i, _ in cel) - 1, max(i for i, _ in cel) + 1
    jmin, jmax = min(j for _, j in cel) - 1, max(j for _, j in cel) + 1

    bruto = []
    for i in range(imin, imax + 1):
        for j in range(jmin, jmax + 1):
            a, b = cel.get((i, j)), cel.get((i + 1, j))
            if a != b and frozenset((a, b)) not in pj.INTEGRADOS:
                bruto.append(("V", (i + 1) * G, j, a, b))
            a, b = cel.get((i, j)), cel.get((i, j + 1))
            if a != b and frozenset((a, b)) not in pj.INTEGRADOS:
                bruto.append(("H", (j + 1) * G, i, a, b))

    grupos: dict[tuple, list[int]] = {}
    for ori, fixo, idx, a, b in bruto:
        grupos.setdefault((ori, fixo, a, b), []).append(idx)

    saida = []
    for (ori, fixo, a, b), idxs in grupos.items():
        idxs.sort()
        ini = ant = idxs[0]
        for k in idxs[1:] + [None]:
            if k == ant + 1:
                ant = k
                continue
            saida.append(_segmento(ori, fixo, ini, ant, a, b))
            if k is not None:
                ini = ant = k
    return saida


def _segmento(ori, fixo, ini, fim, a, b) -> dict:
    externa = a is None or b is None
    fam = classificar(a, b, externa)
    seg = dict(ori=ori, fixo=fixo, ini=ini * G, fim=(fim + 1) * G,
               a=a, b=b, externa=externa, familia=fam,
               esp=FAMILIAS[fam]["esp"])
    seg["comp"] = seg["fim"] - seg["ini"]
    seg["face"] = _face(ori, a, b)
    return seg


def _face(ori, a, b) -> str:
    """Orientacao da face externa. Testada a leste: +X = norte, +Y = oeste."""
    if a is not None and b is not None:
        return "-"
    if ori == "V":                      # parede de x constante, normal em X
        return "N" if a is not None else "S"
    return "O" if a is not None else "L"


def classificar(a: str | None, b: str | None, externa: bool) -> str:
    if externa:
        return "PE-1"
    ca, cb = CATEGORIA.get(a, "outro"), CATEGORIA.get(b, "outro")
    # a oficina tem precedencia: nenhuma prumada encosta nela — agua descendo
    # em tubo e ruido de impacto continuo dentro do ambiente que pede silencio
    if a in SILENCIO or b in SILENCIO:
        return "PA-1"
    if a in MOLHADOS or b in MOLHADOS:
        if a in ("T-BWC", "T-COZ", "T-LAV") or b in ("T-BWC", "T-COZ", "T-LAV"):
            return "PH-1"
    if "intimo" in (ca, cb) and (ca in FONTES or cb in FONTES or ca == cb == "intimo"):
        return "PA-1"
    if {"social", "servico"} <= {ca, cb}:
        return "PA-1"
    if "T-COR" in (a, b) or "S-HAL" in (a, b):
        return "PA-1"
    return "PI-1"


def quantitativo() -> dict[str, float]:
    """Area de parede por familia, em m2, descontando o pe-direito."""
    q: dict[str, float] = {}
    for pav, ambs in (("T", pj.TERREO), ("S", pj.SUPERIOR)):
        for s in paredes_classificadas(ambs):
            q[s["familia"]] = q.get(s["familia"], 0.0) + \
                s["comp"] / 1000 * pj.PE_DIREITO / 1000
    return q


# =========================================================================
# pisos e forros — tratamento por par de ambientes sobrepostos
# =========================================================================
def sobreposicao() -> list[dict]:
    """Onde cada ambiente superior se apoia, e qual o tratamento exigido."""
    out = []
    for s in pj.SUPERIOR:
        for t in pj.TERREO:
            ox = max(0, min(s.x + s.w, t.x + t.w) - max(s.x, t.x))
            oy = max(0, min(s.y + s.h, t.y + t.h) - max(s.y, t.y))
            if ox > 0 and oy > 0:
                area = ox * oy / 1e6
                cat_inf = CATEGORIA.get(t.cod, "outro")
                if CATEGORIA.get(s.cod) == "intimo" and cat_inf in ("social", "servico"):
                    trat, just = ("manta 5 mm + forro suspenso com la",
                                  f"dormitorio sobre {cat_inf}: ruido aereo e de impacto")
                elif CATEGORIA.get(s.cod) == "intimo":
                    trat, just = ("manta resiliente 5 mm",
                                  "dormitorio sobre circulacao: impacto apenas")
                else:
                    trat, just = ("contrapiso seco simples",
                                  "sem dormitorio acima: tratamento nao se justifica")
                out.append(dict(sup=s.cod, inf=t.cod, area=area,
                                tratamento=trat, justificativa=just))
    # balanco sobre area externa
    for s in pj.SUPERIOR:
        coberto = sum(o["area"] for o in out if o["sup"] == s.cod)
        resto = s.area_mod - coberto
        if resto > 0.5:
            out.append(dict(sup=s.cod, inf="EXTERNO", area=resto,
                            tratamento="isolamento termico inferior + barreira de vapor",
                            justificativa="piso em balanco exposto: ganho termico, nao acustico"))
    return out


FORROS = [
    ("T-GOU", "forro absorvente (la mineral aparente ou perfurado, alfa 0,70)", 30.24,
     "unico ponto que derruba a reverberacao de 3,20 s para 0,86 s"),
    ("T-SOC", "gesso liso + cortinas e tapetes", 25.20,
     "absorcao vem do mobiliario; forro tecnico aqui teria ganho marginal"),
    ("T-COZ", "gesso liso lavavel", 18.00,
     "superficie de facil limpeza tem prioridade sobre absorcao"),
    ("S-S02", "gesso liso + la mineral sobre o forro", 25.92,
     "la sobre o forro atenua ruido de chuva no painel PIR"),
    ("S-S03", "gesso liso + la mineral sobre o forro", 25.92, "idem"),
    ("S-MAS", "gesso liso + la mineral sobre o forro", 28.80, "idem"),
    ("T-GAR", "sem forro (estrutura aparente)", 36.00,
     "ambiente sem exigencia acustica nem termica"),
    ("T-OFI", "sem forro (estrutura aparente)", 9.00, "idem"),
    ("T-DML", "sem forro (estrutura aparente)", 3.60, "idem"),
]


# =========================================================================
# vidros — especificacao por vao, conforme face e uso
# =========================================================================
def especificar_vaos() -> list[list[str]]:
    fam_amb = {}
    for a in pj.TERREO + pj.SUPERIOR:
        fam_amb[a.cod] = CATEGORIA.get(a.cod, "outro")

    out = []
    for tipo, x, y, ori, pav in pj.VAOS:
        if not tipo.startswith(("J", "PV")):
            continue
        lg, al, pe, _ = pj.ESQUADRIAS[tipo]
        face = _face_do_vao(x, y, ori, pav)
        crit_solar = face in ("L", "O")
        # ruido externo relevante: face leste (via do condominio)
        crit_acustico = face == "L" or (face == "O" and tipo.startswith("PV"))
        if tipo == "J02":
            vidro, just = "temperado 6 mm translucido", "banheiro: sem exigencia"
        elif crit_solar and crit_acustico:
            vidro, just = ("laminado 6+6 PVB acustico + controle solar",
                           "face critica em sol E em ruido")
        elif crit_acustico:
            vidro, just = "laminado 6+6 PVB acustico", "ruido externo relevante"
        elif crit_solar:
            vidro, just = "laminado 6+6 com controle solar", "sol rasante, sem ruido"
        else:
            vidro, just = "temperado 8 mm comum", "face protegida: sem exigencia"
        out.append([tipo, f"{lg}x{al}", face, fam_amb.get(_amb_do_vao(x, y, pav), "-"),
                    vidro, just])
    # consolida repetidos
    vistos, final = set(), []
    for r in out:
        k = (r[0], r[2], r[4])
        if k in vistos:
            continue
        vistos.add(k)
        n = sum(1 for o in out if (o[0], o[2], o[4]) == k)
        final.append(r[:4] + [str(n)] + r[4:])
    return final


def _amb_do_vao(x, y, pav):
    ambs = pj.TERREO if pav == "T" else pj.SUPERIOR
    for d in (300, -300):
        for a in ambs:
            if a.x <= x + d <= a.x + a.w and a.y <= y + d <= a.y + a.h:
                return a.cod
    return "-"


def _face_do_vao(x, y, ori, pav):
    ambs = pj.TERREO if pav == "T" else pj.SUPERIOR
    def dentro(px, py):
        return any(a.x <= px < a.x + a.w and a.y <= py < a.y + a.h for a in ambs)
    if ori == "H":
        return "L" if dentro(x, y + 300) else "O"
    return "N" if dentro(x - 300, y) else "S"


# =========================================================================
# onde NAO gastar
# =========================================================================
NAO_APLICAR = [
    ["Parede acustica (PA-1)", "entre lavanderia e deposito",
     "ambos de servico, com o mesmo tipo de ruido — o reforco vai para a oficina"],
    ["Parede acustica (PA-1)", "dentro da fita social integrada",
     "o cliente pediu integracao: parede ali contradiz o partido"],
    ["Parede hidraulica 150 mm", "onde nao passa prumada DN100",
     "50 mm a mais de espessura sem funcao consomem area util"],
    ["Manta resiliente", "sob piso do terreo (sobre radier)",
     "nao ha pavimento abaixo: nao existe ruido de impacto a transmitir"],
    ["Forro absorvente", "em dormitorios",
     "volume pequeno e mobiliario textil ja garantem TR baixo"],
    ["Vidro laminado acustico", "banheiros e area de servico",
     "vaos de 600x600 e faces protegidas: custo sem retorno perceptivel"],
    ["Controle solar", "faces norte e sul",
     "beiral de 1.200 mm ja sombreia; vidro de controle so escurece"],
    ["Brise vertical", "faces norte e sul",
     "sol alto (63 a 87 graus): brise vertical nao intercepta nada"],
    ["La mineral de 90 mm (preenchimento total)", "qualquer parede",
     "acima de 50 mm o ganho acustico e residual; a chapa adicional rende mais"],
    ["Isolamento adicional na cobertura", "alem do PIR de 75 mm",
     "U ja em 0,276 contra limite de 2,30: o proximo real e o sombreamento"],
]


def hierarquia_investimento() -> list[list[str]]:
    """Ordem de retorno decrescente, com o ganho medido pelos calculos."""
    return [
        ["1", "Vedacao de frestas com selante acustico",
         "muito baixo", "ate +10 dB", "uma fresta de 1 % anula 10 dB de parede"],
        ["2", "Brise vertical nas faces leste e oeste",
         "baixo", "bloqueia ~75 % do ganho solar", "projecao horizontal exigida seria 4,16 m"],
        ["3", "Manta resiliente sob contrapiso seco",
         "baixo", "L'nT,w de 80 para 70 dB", "reprova sem ela na NBR 15575-3"],
        ["4", "Forro absorvente no gourmet (30 m2)",
         "baixo", "TR de 3,20 para ~1,1 s", "o resto vem do mobiliario"],
        ["5", "Vidro laminado acustico nos vaos criticos",
         "medio", "Rw composto de 31,8 para 42,4 dB", "so 6 vaos de 29"],
        ["6", "Dupla chapa nas paredes PA-1",
         "medio", "Rw de 41 para 49 dB", "so onde ha intimo x fonte de ruido"],
        ["7", "ISO strip continuo (XPS 20 mm)",
         "baixo", "U efetivo de 1,025 para 0,668", "justificado por patologia, nao por energia"],
        ["8", "Forro suspenso com la sob as suites",
         "medio", "L'nT,w de 70 para 57 dB", "so onde ha dormitorio sobre area ruidosa"],
    ]


def payback_iso_strip(area_parede_m2: float) -> dict:
    """Retorno energetico do ISO strip, para mostrar que NAO e ele o argumento."""
    U_s, U_c = dp.ponte_termica(dp.transmitancia(pj.CAMADAS["parede_externa"]), False), \
               dp.ponte_termica(dp.transmitancia(pj.CAMADAS["parede_externa"]), True)
    dU = U_s - U_c
    dT, horas, cop, tarifa = 6.0, 3_000.0, 3.2, 0.95
    kwh = dU * area_parede_m2 * dT * horas / 1000.0 / cop
    return dict(dU=dU, kwh=kwh, economia=kwh * tarifa,
                custo=area_parede_m2 * 35.0,
                payback=(area_parede_m2 * 35.0) / max(kwh * tarifa, 1e-6))


# =========================================================================
# PR-12 — mapa de familias de vedacao
# =========================================================================
CORES_FAM = {"PE-1": "#2d6a4f", "PH-1": "#1d4e89", "PA-1": "#c1121f", "PI-1": "#adb5bd"}


def _mapa(cv: Canvas, vw: View, ambs, titulo: str) -> None:
    for a in ambs:
        cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                   vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                  "cota", fechado=True, preenche="#fbfbfb", cor="#e8e8e8")
        c = vw.pt(P(a.cx, a.cy))
        cv.texto_p((c[0], c[1] - 2), a.nome, TXT["micro"], "middle", cor=CINZA)
        cv.texto_p((c[0], c[1] + 2), CATEGORIA.get(a.cod, "-"), TXT["micro"],
                   "middle", cor="#bbb")
    for s in paredes_classificadas(ambs):
        cor = CORES_FAM[s["familia"]]
        e = s["esp"]
        if s["ori"] == "V":
            x, y, w, h = s["fixo"] - e / 2, s["ini"], e, s["comp"]
        else:
            x, y, w, h = s["ini"], s["fixo"] - e / 2, s["comp"], e
        cv.poli_p([vw.pt(P(x, y)), vw.pt(P(x + w, y)), vw.pt(P(x + w, y + h)),
                   vw.pt(P(x, y + h))], "corte2", fechado=True, preenche=cor, cor=cor)
    cv.texto_p((vw.ox, vw.oy + 14), titulo, TXT["peq"], "start", peso="bold")


def prancha_mapa() -> Canvas:
    cv = base("MAPA DE FAMILIAS DE VEDACAO", "1:100", "12", notas=[
        "Duas familias dimensionais (150 e 100 mm), quatro composicoes.",
        "Nenhum eixo, vao ou cota muda: varia so o conteudo dentro da espessura.",
        "A cor indica a exigencia do local, nao a espessura.",
    ])
    _mapa(cv, View(100, 60, 330, 2_400, 7_200), pj.TERREO, "TERREO")
    _mapa(cv, View(100, 230, 330, 2_400, 7_200), pj.SUPERIOR, "SUPERIOR")

    q = quantitativo()
    linhas = []
    for cod, f in FAMILIAS.items():
        linhas.append([cod, f["nome"], f"{f['esp']}", f"{f['Rw']}",
                       f"{q.get(cod, 0):.2f}", f"{f['indice']:.2f}", f["onde"][:54]])
    linhas.append(["", "TOTAL", "", "", f"{sum(q.values()):.2f}", "", ""])
    y = _tabela(cv, (400, 40), "FAMILIAS DE VEDACAO — COMPOSICAO POR EXIGENCIA",
                ["COD", "FAMILIA", "esp.", "Rw", "AREA m2", "indice", "ONDE SE APLICA"],
                linhas, larguras=[16, 52, 14, 12, 24, 18, 124]) + 14

    for cod, f in FAMILIAS.items():
        cv.poli_p([(400, y), (410, y), (410, y + 4), (400, y + 4)], "fino",
                  fechado=True, preenche=CORES_FAM[cod])
        cv.texto_p((414, y + 2), f"{cod} — {f['comp']}", TXT["micro"], "start", peso="bold")
        cv.texto_p((414, y + 7), f["porque"], TXT["micro"], "start", cor=CINZA)
        y += 14

    pb = payback_iso_strip(q.get("PE-1", 0))
    y += 6
    cv.texto_p((400, y), "POR QUE O ISO STRIP, SE O PAYBACK E LONGO",
               TXT["peq"], "start", peso="bold")
    for i, t in enumerate([
        f"Ganho energetico: dU = {pb['dU']:.3f} W/m2K sobre {q.get('PE-1',0):.0f} m2 "
        f"-> {pb['kwh']:.0f} kWh/ano, payback de {pb['payback']:.0f} anos (H).",
        "Isolado, o argumento energetico NAO sustenta o investimento.",
        "O argumento e outro: em clima quente-umido com ar-condicionado o vapor migra",
        "de FORA para DENTRO. O montante de aco fica mais frio que o ponto de orvalho",
        "externo (28,2 C a 32 C / 80 % UR) e a agua condensa DENTRO do painel — sobre o",
        "aco, encharcando a la, sem sinal visivel ate a patologia estar instalada.",
        "O XPS de celula fechada e quebra termica E barreira de vapor, na posicao certa",
        "(lado quente-umido). Um material, duas funcoes. Precisa ser CONTINUO: aplicar",
        "por partes cria justamente o ponto frio onde a condensacao se concentra.",
    ]):
        cv.texto_p((400, y + 7 + i * 4.6), t, TXT["min"], "start")

    an.norte(cv, (790, 90), 9, pj.NORTE_EM_PLANTA)
    return cv


# =========================================================================
# PR-13 — especificacao por exigencia
# =========================================================================
def prancha_especificacao() -> Canvas:
    cv = base("ESPECIFICACAO POR EXIGENCIA", "s/ escala", "13", notas=[
        "Especificar 'superior em tudo' encarece sem melhorar o desempenho percebido.",
        "Cada item responde ao que acontece nos seus dois lados.",
        "Indices de custo sao relativos a solucao simples (1,00); cotar em Manaus.",
    ])

    linhas = [[o["sup"], o["inf"], f"{o['area']:.2f}", o["tratamento"][:46],
               o["justificativa"][:52]] for o in sobreposicao()]
    y = _tabela(cv, (35, 40), "PISOS — TRATAMENTO CONFORME O QUE ESTA ABAIXO",
                ["SUPERIOR", "INFERIOR", "AREA m2", "TRATAMENTO", "POR QUE"],
                linhas, larguras=[24, 24, 22, 100, 110]) + 16

    y = _tabela(cv, (35, y), "FORROS — ABSORCAO SO ONDE HA REVERBERACAO",
                ["AMBIENTE", "SOLUCAO", "AREA m2", "POR QUE"],
                [[c, s[:50], f"{a:.2f}", j[:58]] for c, s, a, j in FORROS],
                larguras=[24, 108, 22, 126]) + 16

    _tabela(cv, (35, y), "VIDROS — ESPECIFICACAO POR VAO",
            ["REF", "VAO", "FACE", "USO", "QTD", "VIDRO", "POR QUE"],
            especificar_vaos(), larguras=[16, 26, 16, 24, 14, 92, 92])

    y2 = _tabela(cv, (35, 300), "HIERARQUIA DE INVESTIMENTO — RETORNO DECRESCENTE",
                 ["#", "MEDIDA", "CUSTO", "GANHO MEDIDO", "OBSERVACAO"],
                 hierarquia_investimento(),
                 larguras=[8, 104, 24, 62, 112]) + 16

    _tabela(cv, (35, y2), "ONDE NAO APLICAR — RACIONALIZACAO",
            ["ITEM", "NAO APLICAR EM", "POR QUE"],
            NAO_APLICAR, larguras=[76, 76, 158])
    return cv
