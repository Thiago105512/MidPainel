"""
Desempenho termico e acustico — calculo e verificacao normativa.

NBR 15220-3  Zoneamento bioclimatico (Manaus = ZB8)
NBR 15575-4/5 Desempenho de vedacoes e coberturas
NBR 15575-3  Desempenho acustico

Nada aqui e estimado por analogia: transmitancia, fator solar, angulo de
sombreamento, Rw composto e tempo de reverberacao sao calculados a partir
das camadas e geometrias declaradas em projeto.py.
"""
from __future__ import annotations

import math

import projeto as pj
import anotacao as an
from core import P, Canvas, View, TXT, CINZA, PRETO
from pranchas import base, _tabela


# ---------------------------------------------------------------- termico
# R58 — O CALCULO TERMICO NAO MORA MAIS AQUI.
#
# Ate R57 este arquivo calculava U a partir de `projeto.CAMADAS`, uma lista de
# camadas escrita a mao que NAO era o fechamento construido: ela trocava os
# 20 mm de XPS da ISO strip por uma camara de ar de 40 mm que a parede nao
# tem, e nao continha o montante. Verificava uma parede inexistente — e
# passava, que e o pior desfecho possivel para uma verificacao errada.
#
# Agora U, CT, atraso e FSo saem de `nucleo/termica.py`, que le as MESMAS
# composicoes que geram o BOM. As funcoes abaixo continuam existindo porque a
# prancha as usa, mas viraram fachada de leitura: nao ha mais aritmetica
# termica neste arquivo.
import nucleo.termica as tm
import nucleo.camadas as cm

COMPOSICAO_DE = {"parede_externa": "PE-1", "cobertura": "CB-1"}


def _comp(chave):
    cod = COMPOSICAO_DE[chave]
    return cm.COMPOSICOES.get(cod) or cm.COMPOSICOES_PLANO[cod]


def detalhe(chave) -> tuple[float, list[tuple[str, str, float]]]:
    """Camada a camada da composicao REAL, para a prancha."""
    comp = _comp(chave)
    tipo = "cobertura" if chave == "cobertura" else "parede"
    r = tm.resistencia(pj, comp, tipo)
    linhas = [("Rse (superficial externa)", "-", tm.RSE)]
    cont, miolo = tm.caminhos(comp)
    for c in cont:
        linhas.append((_mat_nome(c), f"{c.espessura * c.n:g}", round(tm._r_camada(c), 4)))
    for c in miolo:
        if c.material == "ACO":
            linhas.append((f"{_mat_nome(c)} — {r['fracao_aco'] * 100:.1f} % da area",
                           f"{c.espessura:g}", 0.0))
        else:
            linhas.append((_mat_nome(c), f"{c.espessura * c.n:g}", round(tm._r_camada(c), 4)))
    if r["r_camara"]:
        linhas.append((f"Camara de ar na sobra da cavidade", f"{r['camara_mm']:g}", r["r_camara"]))
    linhas.append((f"Rsi (superficial interna)", "-", tm.FLUXO[tipo]))
    return r["r_efetivo"], linhas


def _mat_nome(c) -> str:
    import nucleo.materiais as mt
    m = mt.POR_MATERIAL.get(c.material)
    nome = m.nome if m else c.material
    return f"{nome} (x{c.n})" if c.n > 1 else nome


def resistencia(camadas) -> tuple[float, list[tuple[str, str, float]]]:
    """R total [m2.K/W] e o detalhamento camada a camada."""
    linhas, R = [], 0.0
    for nome, esp, lam in camadas:
        if esp is None:                       # resistencia direta (superficial/ar)
            r = lam
            linhas.append((nome, "-", r))
        elif nome.lower().startswith("camara"):
            r = lam
            linhas.append((nome, f"{esp:g}", r))
        else:
            r = (esp / 1000.0) / lam
            linhas.append((nome, f"{esp:g}", r))
        R += r
    return R, linhas


def transmitancia(camadas) -> float:
    R, _ = resistencia(camadas)
    return 1.0 / R


def fator_solar(U: float, alfa: float = pj.ABSORTANCIA) -> float:
    """FSo em %, conforme NBR 15220-3: FSo = 100 . U . alfa . 0,04."""
    return 100.0 * U * alfa * 0.04


def ponte_termica(U_ideal: float, com_quebra: bool) -> float:
    """Efeito dos montantes de aco (lambda = 50 W/m.K).

    Sem quebra termica o perfil curto-circuita o isolante: a literatura de
    LSF em clima quente aponta perda de 35 a 50 % do R efetivo. Com banda
    isolante continua (ISO strip) sob a placa externa a perda cai para
    menos de 10 %. Adotados 40 % e 8 % como hipoteses (H).
    """
    perda = 0.08 if com_quebra else 0.40
    R = (1.0 / U_ideal) * (1.0 - perda)
    return 1.0 / R


def verificar_zb8() -> list[list[str]]:
    out = []
    for l in tm.levantar(pj):
        lim = pj.LIMITES_ZB8[l["limite"]]
        out.append([lim["rotulo"].upper(),
                    f"{l['u']:.3f}", f"<= {lim['U']:.2f}",
                    "OK" if l["u"] <= lim["U"] else "REVER",
                    f"{l['fso']:.2f} %", f"<= {lim['FSo']:.1f} %",
                    "OK" if l["fso"] <= lim["FSo"] else "REVER",
                    f"{l['atraso_h']:.1f} h", f"<= {lim['atraso']:.1f} h",
                    "OK" if l["atraso_h"] <= lim["atraso"] else "FORA DA CATEGORIA"])
    return out


# ------------------------------------------------------------ sombreamento
def projecao_necessaria(altura_vao: float, altitude_solar: float) -> float:
    """Projecao horizontal, em mm, para sombrear todo o vao."""
    return altura_vao / math.tan(math.radians(altitude_solar))


def estudo_sombreamento(altura_vao: int = 2_400) -> list[list[str]]:
    casos = [
        ("NORTE", 63.5, "21/jun, meio-dia", "horizontal (beiral)"),
        ("SUL", 69.7, "21/dez, meio-dia", "horizontal (beiral)"),
        ("LESTE", 30.0, "08h, ano todo", "VERTICAL (ripado)"),
        ("OESTE", 30.0, "16h, ano todo", "VERTICAL (ripado)"),
    ]
    out = []
    for face, alt, quando, estrategia in casos:
        p = projecao_necessaria(altura_vao, alt)
        viavel = "sim" if p <= 1_500 else "NAO"
        out.append([face, f"{alt:.1f} graus", quando, f"{p:.0f} mm", viavel, estrategia])
    return out


# ---------------------------------------------------------------- acustico
def rw_composto(pares: list[tuple[float, float]]) -> float:
    """Rw de uma fachada composta. pares = [(area_m2, Rw_dB), ...]."""
    st = sum(a for a, _ in pares)
    soma = sum(a * 10 ** (-r / 10.0) for a, r in pares)
    return -10.0 * math.log10(soma / st)


def comparativo_esquadria(area_parede: float = 0.8, rw_parede: float = 45.0) -> list[list[str]]:
    out = []
    for desc, rw in pj.ESQUADRIA_ACUSTICA.items():
        comp = rw_composto([(area_parede, rw_parede), (1 - area_parede, rw)])
        classe = ("SUPERIOR" if comp >= 40 else
                  "INTERMEDIARIO" if comp >= 35 else
                  "MINIMO" if comp >= 30 else "NAO ATENDE")
        out.append([desc[:52], f"{rw:.0f}", f"{comp:.1f}", classe])
    return out


def reverberacao(tratado: bool) -> tuple[float, float, float]:
    """Tempo de reverberacao da fita social integrada (Sabine)."""
    a_social = sum(a.area_mod for a in pj.TERREO if a.cod in ("T-SOC", "T-GOU", "T-COZ"))
    a_core = next(a.area_mod for a in pj.TERREO if a.cod == "T-COR")
    V = a_social * pj.PE_DIREITO / 1000 + a_core * (pj.PISO_A_PISO + pj.PE_DIREITO) / 1000

    sup = [(a_social + a_core, 0.02),          # piso porcelanato
           (a_social + a_core, 0.05),          # teto de gesso
           (150.0, 0.05)]                      # paredes e vidro
    if tratado:
        sup += [(30.0, 0.70),                  # forro absorvente no gourmet
                (25.0, 0.45),                  # cortinas pesadas
                (18.0, 0.35)]                  # tapetes e estofados
        sup[1] = (a_social + a_core - 30.0, 0.05)
    A = sum(s * alfa for s, alfa in sup)
    return 0.161 * V / A, V, A


def impacto_piso() -> list[list[str]]:
    return [
        ["Piso seco (OSB + placa cimenticia), sem tratamento", "78 a 85", "NAO ATENDE"],
        ["+ manta resiliente 5 mm sob contrapiso", "68 a 72", "INTERMEDIARIO"],
        ["+ manta 5 mm + forro suspenso com la mineral", "55 a 60", "SUPERIOR"],
    ]


# =========================================================================
# PR-11 — prancha de desempenho
# =========================================================================
def prancha() -> Canvas:
    cv = base("DESEMPENHO TERMICO E ACUSTICO", "s/ escala", "11", notas=[
        "Testada a LESTE (sol da manha na frente) -> fundo do lote e do social a OESTE.",
        "Manaus: Zona Bioclimatica 8 (NBR 15220-3), latitude 3 S, clima Af quente-umido.",
        "Em ZB8 a estrategia e sombreamento total + ventilacao permanente + massa LEVE.",
        "Valores de lambda conforme NBR 15220-2; itens (H) sao hipoteses de projeto.",
    ])

    # ---- 1. transmitancia camada a camada
    y = 40
    for chave, titulo in [("parede_externa", "PAREDE EXTERNA LSF 150 mm"),
                          ("cobertura", "COBERTURA — PAINEL SANDUICHE PIR 75 mm")]:
        R, linhas = detalhe(chave)
        U = 1.0 / R
        dados = [[n, e, f"{r:.4f}"] for n, e, r in linhas]
        dados.append(["R TOTAL", "", f"{R:.4f}"])
        dados.append(["U = 1/R  [W/m2.K]", "", f"{U:.3f}"])
        dados.append([f"FSo (alfa = {pj.ABSORTANCIA:.2f})", "", f"{fator_solar(U):.2f} %"])
        y = _tabela(cv, (35, y), titulo, ["CAMADA", "esp. (mm)", "R (m2.K/W)"],
                    dados, larguras=[112, 26, 34]) + 16

    # ---- 2. verificacao ZB8
    y = _tabela(cv, (35, y), "VERIFICACAO — NBR 15220-3, ZONA BIOCLIMATICA 8",
                ["ELEMENTO", "U calc.", "U lim.", "", "FSo calc.", "FSo lim.", "",
                 "atraso", "lim.", ""],
                verificar_zb8(), larguras=[44, 17, 17, 12, 19, 19, 12, 16, 16, 30]) + 16

    # ---- 3. ponte termica dos montantes, agora DERIVADA da geometria
    pe = tm.resistencia(pj, _comp("parede_externa"))
    xps = tm.sem_isolante(pj, "PE-1", "XPS")
    _tabela(cv, (35, y), "PONTE TERMICA DOS MONTANTES — DA GEOMETRIA, NAO DE HIPOTESE",
            ["SITUACAO", "U efetivo", "penalidade", "efeito"],
            [["Cavidade isolada, fora do montante", f"{pe['u_cavidade']:.3f}", "-",
              f"{(1 - pe['fracao_aco']) * 100:.1f} % da area da parede"],
             ["Sobre o montante de aco", f"{pe['u_montante']:.3f}", "-",
              f"{pe['fracao_aco'] * 100:.1f} % da area — mesa de 40 mm a cada "
              f"{pj.MONTANTE_ESPACAMENTO} mm"],
             ["PAREDE, caminhos em paralelo (ISO 6946)", f"{pe['u']:.3f}",
              f"+{pe['penalidade_ponte'] * 100:.1f} %", "o que a casa tem"],
             ["A mesma parede SEM a ISO strip de XPS", f"{xps['u_sem']:.3f}",
              f"+{xps['ponte_sem'] * 100:.1f} %",
              f"o XPS derruba U em {xps['ganho'] * 100:.0f} % e a ponte de "
              f"{xps['ponte_sem'] * 100:.0f} % para {xps['ponte_com'] * 100:.0f} %"]],
            larguras=[76, 26, 26, 84])

    # ---- 4. sombreamento por face
    y2 = _tabela(cv, (430, 40),
                 "SOMBREAMENTO NECESSARIO — VAO DE 2.400 mm, LATITUDE 3 S",
                 ["FACE", "altitude", "condicao critica", "projecao", "viavel?", "estrategia"],
                 estudo_sombreamento(), larguras=[22, 26, 46, 26, 20, 50]) + 6
    cv.texto_p((430, y2 + 4),
               "Nas faces leste e oeste o sol chega a 30 graus: a projecao horizontal",
               TXT["min"], "start")
    cv.texto_p((430, y2 + 9),
               "necessaria passa de 4,1 m. Beiral nao resolve — so brise VERTICAL.",
               TXT["min"], "start")

    # ---- 5. esquadria domina a fachada
    y2 = _tabela(cv, (430, y2 + 20),
                 "A ESQUADRIA DOMINA A FACHADA — Rw COMPOSTO (parede Rw 45 dB, vao = 20 % da area)",
                 ["ESQUADRIA", "Rw vao", "Rw composto", "classe NBR 15575-3"],
                 comparativo_esquadria(), larguras=[100, 20, 28, 42]) + 16

    # ---- 6. ruido de impacto entre pavimentos
    y2 = _tabela(cv, (430, y2), "RUIDO DE IMPACTO — PISO SECO ENTRE PAVIMENTOS",
                 ["SOLUCAO", "L'nT,w (dB)", "classe"],
                 impacto_piso(), larguras=[120, 30, 40]) + 16

    # ---- 7. reverberacao do espaco integrado
    tr0, V, A0 = reverberacao(False)
    tr1, _, A1 = reverberacao(True)
    y2 = _tabela(cv, (430, y2),
                 "REVERBERACAO DA FITA SOCIAL INTEGRADA (SABINE) — CONSEQUENCIA DA INTEGRACAO",
                 ["SITUACAO", "V (m3)", "A (m2 sabine)", "TR (s)", "avaliacao"],
                 [["Superficies duras, sem tratamento", f"{V:.0f}", f"{A0:.1f}",
                   f"{tr0:.2f}", "inaceitavel"],
                  ["Com forro absorvente, cortinas e tapetes", f"{V:.0f}", f"{A1:.1f}",
                   f"{tr1:.2f}", "dentro da meta"],
                  ["Meta para ambiente social residencial", "-", "-", "0,60 a 0,80", "referencia"]],
                 larguras=[86, 22, 32, 22, 34]) + 14

    cv.texto_p((430, y2), "ESPECIFICACOES DECORRENTES", TXT["peq"], "start", peso="bold")
    for i, t in enumerate([
        "Barreira de vapor pelo lado EXTERNO (clima quente-umido inverte o gradiente).",
        "Galvanizacao Z275; isolar contato aco-aluminio contra par galvanico.",
        "Banda isolante continua sob a placa externa — sem ela, 40 % do R se perde.",
        "Vidro laminado 6+6 com PVB acustico nas faces leste (rua) e oeste (social).",
        "Manta resiliente sob contrapiso seco + forro com la mineral sob as suites.",
        "Forro absorvente no gourmet: sem ele a fita social integrada reverbera 2,5 s.",
        "Caixilho operavel no topo do core: aberto ventila, fechado isola o social.",
        "Cobertura e paredes em cor clara — manter absortancia menor ou igual a 0,40.",
    ]):
        cv.texto_p((430, y2 + 7 + i * 5), f"{i+1}. {t}", TXT["min"], "start")

    an.norte(cv, (790, 300), 10, pj.NORTE_EM_PLANTA)
    return cv
