"""GEOTECNIA — o solo deixa de ser hipotese e passa a ser dado.

Ate R51 o radier era o sistema mais caro do projeto apoiado no dado mais fraco:
espessura, fck e taxa de armadura eram todos (H), e a pendencia 2 dizia
exatamente isso. O proprietario entregou tres sondagens a percussao (SP-01,
SP-02 e SP-03) com o NSPT metro a metro ate 8 m. Este modulo transforma esses
numeros em decisao de projeto.

O QUE ELE FAZ. Le o perfil, estima tensao admissivel por tres correlacoes
consagradas e adota a MENOR, monta a carga que a casa entrega a fundacao a
partir das cargas ja declaradas em CARGAS e da geometria que o modelo ja
conhece, verifica pressao de contato, profundidade investigada e recalque, e
decide o tratamento do solo superficial.

O QUE ELE NAO FAZ. Ele nao substitui o projeto de fundacao com ART — isso e a
pendencia 3. A diferenca entre R51 e R52 nao e ter o calculo assinado; e que
antes nao havia numero nenhum contra o qual conferir o desenho, e agora ha.

POR QUE TRES CORRELACOES E NAO UMA. Cada uma nasceu de um universo diferente de
ensaios: N/50 de sapatas quadradas a 1,5 m em areia pura; Teixeira-96 de solos
arenosos, com a largura da sapata explicita; Mello-75 sem distincao de solo,
valida so entre N 4 e 16. Nenhuma delas foi feita para ESTE solo. Adotar a
menor das tres nao e conservadorismo decorativo: e a unica forma honesta de
usar correlacao fora do universo que a gerou.
"""
from __future__ import annotations

import math

# --------------------------------------------------------------- o dado
# Tres furos, NSPT por metro, entregues pelo proprietario. A ultima faixa e
# declarada com o sinal de "ou mais" que veio no boletim: adota-se o valor
# cheio, que e o lado conservador para RECALQUE (rigidez menor) e nao e usado
# para capacidade, onde a camada nem chega a ser solicitada.
SONDAGENS = {
    "SP-01": [(0, 1, 3), (1, 2, 5), (2, 3, 8), (3, 4, 11), (4, 5, 16),
              (5, 6, 22), (6, 8, 30)],
    "SP-02": [(0, 1, 4), (1, 2, 6), (2, 3, 9), (3, 4, 13), (4, 5, 18),
              (5, 6, 24), (6, 8, 32)],
    "SP-03": [(0, 1, 3), (1, 2, 5), (2, 3, 7), (3, 4, 10), (4, 5, 15),
              (5, 6, 20), (6, 8, 28)],
}

# interpretacao do boletim, por faixa de profundidade
INTERPRETACAO = {
    (0, 1): "aterro / solo superficial pouco compacto",
    (1, 2): "argila arenosa mole a media",
    (2, 3): "resistencia media",
    (3, 4): "solo medianamente resistente",
    (4, 5): "solo firme",
    (5, 6): "firme a compacto",
    (6, 8): "camada muito resistente",
}

PROF_INVESTIGADA = 8.0        # m
NA = None                     # nivel d'agua: NAO informado no boletim — (H)

# Teixeira & Godoy (1996): E = alfa . K . N, com K em MPa por tipo de solo.
# A faixa 1-6 m foi lida como argila arenosa a solo arenoso medianamente
# resistente; adota-se o par mais deformavel de cada trecho, que e o que
# governa recalque.
K_SOLO = 0.35                 # MPa, argila arenosa
ALFA_SOLO = 7.0               # argila
PESO_ESPECIFICO_SOLO = 18.0   # kN/m3 (H): valor tipico, sem ensaio
POISSON = 0.35

# tratamento do solo superficial — a decisao de R52
TRATAMENTO = dict(
    remover_mm=600,
    substituir_por="areia grossa com brita graduada, em camadas de 250 mm",
    grau_compactacao=0.95,     # Proctor normal
    ensaio="densidade in situ a cada 200 m2 por camada",
    bordadura_mm=500,          # alem da projecao do radier, em cada lado
    razao=("N de 3 a 4 no primeiro metro nao reprova por CAPACIDADE — a "
           "pressao de contato desta casa e uma fracao da admissivel, e o "
           "fator sai calculado em dimensionar(). Reprova por "
           "UNIFORMIDADE. Aterro pouco compacto nao e fraco por igual — e "
           "fraco em manchas, e mancha de rigidez diferente sob radier vira "
           "fissura de flexao, nao recalque uniforme. Trocar 600 mm de solo "
           "sem controle por 600 mm com controle custa uma fracao do radier e "
           "e o unico item aqui que compra PREVISIBILIDADE."),
)


def _faixas() -> list[tuple[float, float]]:
    return [(a, b) for a, b, _ in SONDAGENS["SP-01"]]


def perfil() -> list[dict]:
    """Perfil medio das tres sondagens, com a dispersao entre furos.

    A media diz a rigidez; a dispersao diz o risco de recalque DIFERENCIAL, que
    e o que trinca radier. Um perfil medio bom com furos discordantes e pior
    que um perfil medio pior com furos iguais.
    """
    out = []
    for i, (z0, z1) in enumerate(_faixas()):
        ns = [SONDAGENS[s][i][2] for s in sorted(SONDAGENS)]
        med = sum(ns) / len(ns)
        out.append(dict(z0=z0, z1=z1, n=ns, medio=round(med, 2),
                        minimo=min(ns), maximo=max(ns),
                        dispersao=round((max(ns) - min(ns)) / med, 3),
                        solo=INTERPRETACAO[(z0, z1)]))
    return out


# ------------------------------------------------------- tensao admissivel
def sigma_n50(n: float) -> float:
    """N/50 em MPa. Universo: sapata quadrada a 1,5 m em areia pura."""
    return n / 50.0


def sigma_teixeira(n: float, b_m: float) -> float:
    """Teixeira-96, MPa: 0,05 + (1 + 0,4 B) N/100, B em metros.

    A formula cresce com B, o que e valido para sapata e perigoso para radier:
    extrapolar B de 16 m daria tensao irreal. Limita-se B a 3,0 m, que e o topo
    do universo de ensaios que a gerou.
    """
    b = min(b_m, 3.0)
    return 0.05 + (1 + 0.4 * b) * n / 100.0


def sigma_mello(n: float) -> float:
    """Mello-75, MPa: 0,1 (raiz(N) - 1). So vale para N entre 4 e 16."""
    return 0.1 * (math.sqrt(n) - 1)


def tensao_admissivel(n: float, b_m: float) -> dict:
    """As tres correlacoes e a adotada, que e a menor delas."""
    cand = {
        "N/50": sigma_n50(n),
        "Teixeira-96": sigma_teixeira(n, b_m),
        "Mello-75": sigma_mello(n) if 4 <= n <= 16 else None,
    }
    validas = {k: v for k, v in cand.items() if v is not None}
    quem = min(validas, key=validas.get)
    return dict(candidatas={k: round(v * 1000, 1) for k, v in cand.items()
                            if v is not None},
                fora_do_universo=[k for k, v in cand.items() if v is None],
                adotada_kpa=round(validas[quem] * 1000, 1), governa=quem)


# ------------------------------------------------------- carga e pressao
def carga_na_fundacao(pj, r) -> dict:
    """O que a casa entrega ao solo, das cargas declaradas e da geometria.

    Ninguem tinha somado isto. O modelo sabia a carga de cada viga e de cada
    painel, e nao sabia o total que chega ao radier — que e justamente o numero
    que o solo responde. Peso proprio do radier e do lastro entram: eles pesam
    sobre o solo tanto quanto a casa.
    """
    import nucleo.fundacao as fu
    C = pj.CARGAS
    fun = fu.levantar(pj)
    par_m2 = sum(p.comp * p.altura for p in r["paineis"]) / 1e6
    perm = {
        "cobertura": C["cobertura_perm"] * pj.area_contribuicao_m2(),
        "piso do superior": C["piso_lsf_perm"] * pj.area_fechada("S"),
        "paredes": C["parede_lsf_m"] * par_m2,
        "radier": 25.0 * fun["volume_m3"],
        "lastro e substituicao": 19.0 * fun["lastro_m3"],
    }
    acid = {
        "piso do superior": C["piso_lsf_acid"] * pj.area_fechada("S"),
        "piso do terreo": 1.5 * pj.area_fechada("T"),
        "cobertura": C["cobertura_acid"] * pj.projecao_coberta_m2(),
    }
    p, a = sum(perm.values()), sum(acid.values())
    area = fun["area"]
    # lado equivalente do radier: raiz da area, para as correlacoes e para o
    # espraiamento. Declarado como equivalente, nao como dimensao real.
    b_eq = math.sqrt(area)
    return dict(permanente=round(p, 1), acidental=round(a, 1),
                servico=round(p + a, 1),
                por_parcela={**{f"G {k}": round(v, 1) for k, v in perm.items()},
                             **{f"Q {k}": round(v, 1) for k, v in acid.items()}},
                area=area, b_equivalente=round(b_eq, 2),
                pressao_kpa=round((p + a) / area, 2),
                parede_m2=round(par_m2, 1),
                obs="pressao de SERVICO (G + Q sem majoracao): e contra a "
                    "tensao admissivel, que ja traz o fator de seguranca, que "
                    "ela se compara")


def acrescimo(q_kpa: float, b: float, l: float, z: float) -> float:
    """Espraiamento 2:1: a tensao que sobra na profundidade z."""
    return q_kpa * (b * l) / ((b + z) * (l + z))


def profundidade_suficiente(pj, r) -> dict:
    """A sondagem foi fundo o bastante?

    Pergunta que quase ninguem faz e que a NBR 6122 exige responder: a
    investigacao tem de alcancar a profundidade onde o acrescimo de tensao
    deixa de importar — o criterio classico e 10 % da tensao vertical efetiva
    do terreno. Se a sondagem para antes disso, o recalque calculado ignora
    camada que ainda esta trabalhando.
    """
    cg = carga_na_fundacao(pj, r)
    b = cg["b_equivalente"]
    q = cg["pressao_kpa"]
    z = 0.5
    limite = None
    while z <= 40:
        dsig = acrescimo(q, b, b, z)
        sigv = PESO_ESPECIFICO_SOLO * z
        if dsig <= 0.10 * sigv:
            limite = z
            break
        z += 0.5
    return dict(z_critico=limite, investigada=PROF_INVESTIGADA,
                suficiente=(limite is not None and limite <= PROF_INVESTIGADA),
                acrescimo_no_fundo=round(
                    acrescimo(q, b, b, PROF_INVESTIGADA), 2),
                sigma_v_no_fundo=round(
                    PESO_ESPECIFICO_SOLO * PROF_INVESTIGADA, 2),
                criterio="acrescimo <= 10 % da tensao vertical efetiva")


def recalque(pj, r) -> dict:
    """Recalque por somatorio de camadas, com E do SPT (Teixeira & Godoy).

    O primeiro metro entra com o modulo do material de SUBSTITUICAO, nao com o
    do aterro: depois do tratamento ele deixa de ser o solo do boletim. Essa e
    a diferenca que o tratamento compra, e ela aparece aqui em milimetros.
    """
    cg = carga_na_fundacao(pj, r)
    b = cg["b_equivalente"]
    q = cg["pressao_kpa"]
    camadas = []
    total = 0.0
    for f in perfil():
        h = f["z1"] - f["z0"]
        zm = (f["z0"] + f["z1"]) / 2
        dsig = acrescimo(q, b, b, zm)
        if f["z0"] == 0:
            # camada tratada: material granular compactado a 95 % PN
            e_mpa = 40.0
            fonte = "substituicao compactada (E adotado 40 MPa)"
        else:
            e_mpa = ALFA_SOLO * K_SOLO * f["medio"]
            fonte = f"E = {ALFA_SOLO:g} x {K_SOLO} x N({f['medio']:.2f})"
        ds = dsig * h / (e_mpa * 1000) * 1000  # mm
        total += ds
        camadas.append(dict(z0=f["z0"], z1=f["z1"], dsigma=round(dsig, 2),
                            e_mpa=round(e_mpa, 1), recalque_mm=round(ds, 2),
                            fonte=fonte))
    # recalque diferencial estimado pela dispersao do NSPT entre furos
    disp = max(f["dispersao"] for f in perfil()[1:])
    dif = total * disp
    # a distancia entre furos governa o comprimento em que a diferenca ocorre
    return dict(camadas=camadas, total_mm=round(total, 2),
                limite_total_mm=25.0,
                diferencial_mm=round(dif, 2),
                dispersao_max=disp,
                distorcao=round(dif / 1000 / 10.0, 6),
                limite_distorcao=1 / 300,
                norma="NBR 6122: recalque total e distorcao angular",
                obs="distorcao estimada sobre 10 m, que e a ordem da distancia "
                    "entre furos; o diferencial vem da DISPERSAO do NSPT, nao "
                    "de um coeficiente de livro")


# --------------------------------------------------------------- o radier
def dimensionar(pj, r) -> dict:
    """Verifica o radier declarado contra o solo medido."""
    cg = carga_na_fundacao(pj, r)
    p0 = perfil()[0]              # camada de apoio depois do tratamento
    p1 = perfil()[1]              # a camada natural logo abaixo
    adm_nat = tensao_admissivel(p1["medio"], cg["b_equivalente"])
    fs = adm_nat["adotada_kpa"] / cg["pressao_kpa"]
    rec = recalque(pj, r)
    prof = profundidade_suficiente(pj, r)
    return dict(
        pressao_kpa=cg["pressao_kpa"],
        admissivel=adm_nat,
        fator=round(fs, 2),
        fator_minimo=3.0,
        capacidade_ok=fs >= 3.0,
        recalque=rec,
        recalque_ok=rec["total_mm"] <= rec["limite_total_mm"],
        distorcao_ok=rec["distorcao"] <= rec["limite_distorcao"],
        investigacao=prof,
        camada_superficial=p0,
        tratamento=TRATAMENTO,
        governa=("recalque" if rec["total_mm"] / rec["limite_total_mm"]
                 > 1 / fs else "uniformidade do apoio"),
    )


# ------------------------------------------------------------- armadura
# A taxa de 45 kg/m3 era (H) de livro. Com o solo medido, a armadura pode ser
# DERIVADA do que de fato se compra: duas telas soldadas e o reforco de borda.
# Taxa e resultado, nao dado.
TELA = dict(cod="Q196", kg_m2=3.11, traspasse=0.10, camadas=2,
            norma="NBR 7481")
BORDA = dict(largura=300, altura=400, barras=4, bitola=10.0,
             kg_m_barra=0.617, estribo_bitola=6.3, estribo_kg_m=0.245,
             estribo_passo=200,
             razao=("a borda e o ponto fragil de todo radier: e onde o solo "
                    "perde confinamento, onde a chuva bate e onde o chumbador "
                    "do LSF ancora. Engrossar so o perimetro custa pouco "
                    "concreto e resolve os tres de uma vez"))


def armadura(pj) -> dict:
    """Aco do radier derivado da armadura real, nao de taxa por metro cubico."""
    import nucleo.fundacao as fu
    c = fu.contorno(pj)
    area, perim = c["area"], c["perimetro"]
    tela_m2 = area * (1 + TELA["traspasse"]) * TELA["camadas"]
    tela_kg = tela_m2 * TELA["kg_m2"]
    long_kg = perim * BORDA["barras"] * BORDA["kg_m_barra"]
    n_est = math.ceil(perim / (BORDA["estribo_passo"] / 1000.0))
    # perimetro do estribo: retangulo da borda menos 2 x cobrimento em cada lado
    cob = pj.RADIER["cobrimento"] / 1000.0
    per_est = 2 * ((BORDA["largura"] / 1000.0 - 2 * cob)
                   + (BORDA["altura"] / 1000.0 - 2 * cob)) + 0.10
    est_kg = n_est * per_est * BORDA["estribo_kg_m"]
    total = tela_kg + long_kg + est_kg
    vol = volume_concreto(pj)
    return dict(tela_m2=round(tela_m2, 1), tela_kg=round(tela_kg, 1),
                longitudinal_kg=round(long_kg, 1),
                estribos=n_est, estribo_kg=round(est_kg, 1),
                total_kg=round(total, 1),
                taxa_kg_m3=round(total / vol["total"], 1),
                obs="taxa e RESULTADO da armadura escolhida; antes era o dado "
                    "de entrada, e a armadura nao existia em lugar nenhum")


def volume_concreto(pj) -> dict:
    """Laje de espessura constante mais o engrossamento do perimetro."""
    import nucleo.fundacao as fu
    c = fu.contorno(pj)
    laje = c["area"] * pj.RADIER["espessura"] / 1000.0
    extra = c["perimetro"] * (BORDA["largura"] / 1000.0) * \
        ((BORDA["altura"] - pj.RADIER["espessura"]) / 1000.0)
    return dict(laje=round(laje, 2), borda=round(extra, 2),
                total=round(laje + extra, 2))


def terraplenagem(pj) -> dict:
    """Escavacao, bota-fora e material de substituicao do tratamento."""
    import nucleo.fundacao as fu
    c = fu.contorno(pj)
    b = TRATAMENTO["bordadura_mm"] / 1000.0
    # a area tratada avanca uma bordadura em todo o perimetro
    area = c["area"] + c["perimetro"] * b
    h = TRATAMENTO["remover_mm"] / 1000.0
    corte = area * h
    # o material solto empola: 1,25 e o fator usual para solo argiloso
    # R68 — a reposicao nao tem mais espessura unica: com a declividade
    # confirmada (1 % a 2 % para a rua) a plataforma fica na cota media e a
    # camada varia em torno dos 600 mm. O VOLUME nao muda, porque a variacao e
    # simetrica; o que muda e o numero de camadas de compactacao ponta a ponta,
    # e portanto o numero de ensaios. Ver nucleo/terreno.plataforma().
    import nucleo.terreno as _tr
    plat = _tr.plataforma(pj)
    return dict(area_tratada=round(area, 1), profundidade=h,
                reposicao_alto_mm=plat["reposicao_alto_mm"],
                reposicao_baixo_mm=plat["reposicao_baixo_mm"],
                cota_plataforma_mm=plat["cota_plataforma"],
                corte_m3=round(corte, 1),
                bota_fora_m3=round(corte * 1.25, 1),
                substituicao_m3=round(area * (h - pj.RADIER["lastro"] / 1000.0), 1),
                lastro_m3=round(area * pj.RADIER["lastro"] / 1000.0, 1),
                camadas=math.ceil((h - pj.RADIER["lastro"] / 1000.0) / 0.25),
                ensaios=math.ceil(area / 200.0) *
                math.ceil((h - pj.RADIER["lastro"] / 1000.0) / 0.25),
                obs="o material escavado empola 25 % no caminhao; a "
                    "substituicao e medida COMPACTADA, que e como se paga")


def conferir(pj, r) -> list[tuple[str, str, bool]]:
    """O que tem de ser verdade depois de o solo virar dado."""
    d = dimensionar(pj, r)
    rec = d["recalque"]
    inv = d["investigacao"]
    arm = armadura(pj)
    out = [
        ("pressao de contato",
         f"{d['pressao_kpa']:.2f} kPa contra {d['admissivel']['adotada_kpa']:.1f} "
         f"kPa admissiveis ({d['admissivel']['governa']}) — fator {d['fator']:.2f}",
         d["capacidade_ok"]),
        ("correlacao adotada e a menor",
         f"{d['admissivel']['candidatas']}",
         d["admissivel"]["adotada_kpa"] ==
         min(d["admissivel"]["candidatas"].values())),
        ("recalque total",
         f"{rec['total_mm']:.2f} mm contra {rec['limite_total_mm']:.0f} mm",
         d["recalque_ok"]),
        ("distorcao angular",
         f"{rec['distorcao']:.6f} contra {rec['limite_distorcao']:.5f} (1/300)",
         d["distorcao_ok"]),
        ("profundidade investigada",
         f"o acrescimo cai a 10 % da tensao do terreno em {inv['z_critico']} m "
         f"e a sondagem foi a {inv['investigada']:.0f} m",
         inv["suficiente"]),
        ("tres furos, nao um",
         f"{len(SONDAGENS)} sondagens: a dispersao entre elas e o que estima "
         f"recalque diferencial",
         len(SONDAGENS) >= 3),
        ("nivel d'agua",
         "NAO informado no boletim: segue (H) e pode mudar impermeabilizacao "
         "de base e empuxo no fosso do elevador de servico",
         NA is None),
        ("taxa de armadura e resultado",
         f"{arm['taxa_kg_m3']:.1f} kg/m3 derivados de {arm['tela_m2']:.0f} m2 "
         f"de tela e {arm['longitudinal_kg']:.0f} kg de borda",
         arm["total_kg"] > 0),
    ]
    return out
