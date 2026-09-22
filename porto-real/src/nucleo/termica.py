"""TERMICA — a parede verificada passa a ser a parede construida.

O DEFEITO QUE ESTE MODULO FECHA. Ate R57 o desempenho termico saia de
`projeto.CAMADAS`, uma lista de camadas escrita a mao, e o fechamento real
saia de `nucleo/camadas.COMPOSICOES`. Duas fontes para a mesma parede — e
elas divergiam:

    PE-1 real                    CAMADAS termica
    placa cimenticia 10          placa cimenticia 10        igual
    XPS 20 (ISO strip)           camara de ar 40            DIFERENTE
    montante Ue 90               (ausente)                  DIFERENTE
    la de rocha 50               la mineral 50              igual
    gesso 12,5                   gesso 12,5                 igual

Ou seja: a verificacao termica ignorava os R$ 9.753,90 de XPS que a obra
compra, e no lugar dele punha uma camara de ar de 40 mm que a parede nao tem.
Verificava uma parede que ninguem vai construir. Era o terceiro caso do mesmo
padrao neste projeto (defeitos 39 e 62), e o mais caro dos tres, porque o
numero errado PASSAVA na norma — erro que passa nao levanta suspeita.

O QUE MUDA NO METODO. A ponte termica deixa de ser hipotese e vira geometria.
Ate aqui o efeito do montante era "40 % sem quebra, 8 % com quebra", dois
numeros escolhidos a dedo. Agora ele sai da fracao de area que o montante
ocupa NO PLANO da parede — largura da mesa sobre o espacamento — e de dois
caminhos de fluxo em paralelo (ISO 6946). A hipotese antiga fica no relatorio
como aferição: se o metodo novo devolver algo proximo dela, os dois estao
provavelmente certos; se devolver muito longe, um dos dois esta errado e vale
descobrir qual antes de confiar no novo.

O QUE CONTINUA APROXIMADO, E DECLARADO. O atraso termico usa a formula de
componente HOMOGENEO da NBR 15220-2 (phi = 0,7284 . raiz(Rt . CT)). Uma parede
de LSF e o oposto de homogenea, e a norma tem expressao propria para o caso
heterogeneo. Enquanto ela nao estiver implementada, o valor sai marcado como
aproximacao — nao como resultado. Numero aproximado que se declara aproximado
e informacao; o mesmo numero sem a marca e mentira com casa decimal.
"""
from __future__ import annotations

import math

# Resistencias superficiais, NBR 15220-2 tabela A.1 [m2.K/W]
RSE = 0.04                    # externa, qualquer fluxo
RSI_HORIZONTAL = 0.13         # parede, fluxo horizontal
RSI_DESCENDENTE = 0.17        # cobertura, fluxo descendente (verao)
RSI_ASCENDENTE = 0.10

# Camara de ar nao ventilada, e > 20 mm, fluxo horizontal (NBR 15220-2 A.2)
R_CAMARA = 0.16

# Fluxo de calor por tipo de plano
FLUXO = {"parede": RSI_HORIZONTAL, "cobertura": RSI_DESCENDENTE,
         "entrepiso": RSI_ASCENDENTE, "forro": RSI_DESCENDENTE}


def _mat(cod):
    import nucleo.materiais as mt
    return mt.POR_MATERIAL.get(cod)


def fracao_montante(pj, comp) -> float:
    """Quanto da area da parede e aco, visto de frente.

    Nao e a espessura do perfil: e a largura da MESA, que e o que o fluxo
    atravessa, sobre o espacamento entre montantes. Para Ue 90x40 a cada
    600 mm sao 40/600 = 6,67 % — e esses 6,67 % conduzem 1.200 vezes mais
    que a la ao lado deles. E por isso que a ponte termica existe.
    """
    if not any(c.material == "ACO" for c in comp.camadas):
        return 0.0
    bf = 40.0
    try:
        import nucleo.perfis as pf
        cat = pf.catalogo()
        alvo = [p for p in cat if p.forma == "Ue" and abs(p.bw - _alma(comp)) < 1]
        if alvo:
            bf = min(p.bf for p in alvo)
    except Exception:
        pass
    return bf / float(pj.MONTANTE_ESPACAMENTO)


def _alma(comp) -> float:
    for c in comp.camadas:
        if c.material == "ACO" and c.funcao == "estrutural":
            return c.espessura
    return 0.0


def caminhos(comp) -> tuple[list, list]:
    """Separa as camadas em CONTINUAS e as do MIOLO.

    Continua e a camada que atravessa a parede inteira sem encontrar aco:
    placa, XPS, gesso. Miolo e a espessura da alma do montante, onde o fluxo
    escolhe entre dois caminhos — pela cavidade isolada ou pelo aco.
    """
    cont, miolo = [], []
    for c in comp.camadas:
        (miolo if c.face == "miolo" else cont).append(c)
    return cont, miolo


def _r_camada(c) -> float:
    m = _mat(c.material)
    if m is None or m.lambda_t <= 0:
        return 0.0
    return (c.espessura * c.n / 1000.0) / m.lambda_t


def resistencia(pj, comp, tipo: str = "parede") -> dict:
    """R e U da composicao, pelos dois caminhos em paralelo (ISO 6946).

    O limite SUPERIOR de U (caminhos paralelos isolados) e o que se usa em
    parede de LSF: o aco e tao condutor que o espalhamento lateral do fluxo
    dentro da placa nao chega a compensar, e o limite inferior (camadas em
    serie com condutividade media) subestimaria a ponte grosseiramente.
    """
    rse, rsi = RSE, FLUXO.get(tipo, RSI_HORIZONTAL)
    cont, miolo = caminhos(comp)
    r_cont = sum(_r_camada(c) for c in cont)

    alma = _alma(comp)
    r_isol = 0.0
    esp_isol = 0.0
    for c in miolo:
        if c.material == "ACO":
            continue
        r_isol += _r_camada(c)
        esp_isol += c.espessura * c.n
    # o que sobra da cavidade depois do isolante e camara de ar nao ventilada
    sobra = max(alma - esp_isol, 0.0)
    r_ar = R_CAMARA if sobra >= 20 else 0.0

    r_base = rse + rsi + r_cont
    r_cav = r_base + r_isol + r_ar
    r_aco = r_base + ((alma / 1000.0) / _mat("ACO").lambda_t if alma else 0.0)

    f = fracao_montante(pj, comp)
    u_cav = 1.0 / r_cav
    u_aco = 1.0 / r_aco if alma else u_cav
    u = f * u_aco + (1 - f) * u_cav
    return dict(cod=comp.cod, tipo=tipo, r_continua=round(r_cont, 4),
                r_cavidade=round(r_cav, 4), r_montante=round(r_aco, 4),
                fracao_aco=round(f, 5), u_cavidade=round(u_cav, 4),
                u_montante=round(u_aco, 4), u=round(u, 4),
                r_efetivo=round(1.0 / u, 4),
                penalidade_ponte=round(u / u_cav - 1.0, 4),
                camara_mm=round(sobra, 1), r_camara=r_ar)


def massa_aco_m2(pj, comp) -> float:
    """kg de aco por m2 de parede — da secao do perfil, nao da alma.

    A camada "ACO 90 mm" do modelo descreve o ESPACO que o montante ocupa,
    nao materia macica: o perfil tem 0,95 mm de chapa dobrada. Tratar os 90 mm
    como aco cheio da a uma parede de LSF 325 kJ/m2.K de capacidade termica —
    inercia de parede de concreto, o oposto exato do que ela e. O erro nao e
    academico: ele multiplica por treze o atraso termico e faria o projeto
    "provar" que a casa tem massa que nao tem.

    A massa sai do perimetro desenvolvido da secao vezes a espessura da chapa,
    dividido pelo espacamento. E o mesmo caminho que o BOM ja usa para pesar
    a estrutura — uma fonte, nao duas.
    """
    alma = _alma(comp)
    if not alma:
        return 0.0
    import nucleo.materiais as mt
    bf, D, t = 40.0, 12.0, 0.95
    try:
        import nucleo.perfis as pf
        cand = [p for p in pf.catalogo() if p.forma == "Ue" and abs(p.bw - alma) < 1]
        if cand:
            q = min(cand, key=lambda p: p.t)
            bf, D, t = q.bf, q.D, q.t
    except Exception:
        pass
    perim = alma + 2 * bf + 2 * D          # mm, linha media da secao
    area_m2 = perim * t / 1e6              # m2 de secao transversal
    kg_m = area_m2 * mt.POR_MATERIAL["ACO"].densidade
    return kg_m / (pj.MONTANTE_ESPACAMENTO / 1000.0)


def capacidade_termica(pj, comp) -> float:
    """CT = soma de (espessura . densidade . calor especifico), em kJ/m2.K.

    O aco entra pela MASSA REAL do perfil por m2 de parede (ver massa_aco_m2),
    nunca pela espessura nominal da camada.
    """
    ct = 0.0
    for c in comp.camadas:
        m = _mat(c.material)
        if m is None:
            continue
        if c.material == "ACO" and c.funcao == "estrutural":
            ct += massa_aco_m2(pj, comp) * m.calor_especifico
            continue
        ct += (c.espessura * c.n / 1000.0) * m.densidade * m.calor_especifico
    return round(ct, 2)


def atraso_termico(r_total: float, ct: float) -> float:
    """NBR 15220-2, expressao de componente HOMOGENEO — aproximacao declarada.

    Ver o cabecalho do modulo: a parede de LSF e heterogenea e a norma tem
    expressao propria para ela. Este valor serve para classificar (leve, leve
    refletora, pesada), nao para dimensionar.
    """
    return round(0.7284 * math.sqrt(max(r_total, 0.0) * max(ct, 0.0)), 2)


def fator_solar(u: float, alfa: float) -> float:
    """FSo em %, NBR 15220-3: FSo = 100 . U . alfa . 0,04."""
    return round(100.0 * u * alfa * 0.04, 3)


def levantar(pj) -> list[dict]:
    """Uma linha por composicao que fecha o envelope."""
    import nucleo.camadas as cm
    out = []
    alvo = [("PE-1", "parede", "parede_externa"),
            ("CB-1", "cobertura", "cobertura")]
    for cod, tipo, limite in alvo:
        comp = cm.COMPOSICOES.get(cod) or cm.COMPOSICOES_PLANO.get(cod)
        if comp is None:
            continue
        r = resistencia(pj, comp, tipo)
        ct = capacidade_termica(pj, comp)
        r["ct"] = ct
        r["atraso_h"] = atraso_termico(r["r_efetivo"] - RSE - FLUXO.get(tipo, RSI_HORIZONTAL), ct)
        r["fso"] = fator_solar(r["u"], pj.ABSORTANCIA)
        r["limite"] = limite
        r["nome"] = comp.nome
        out.append(r)
    return out


def conferir(pj) -> list[dict]:
    """Verificacao ZB8 contra a NBR 15220-3, sobre a parede que se constroi."""
    falhas = []
    for l in levantar(pj):
        lim = pj.LIMITES_ZB8.get(l["limite"])
        if lim is None:
            falhas.append(dict(item=l["cod"], erro="sem limite normativo declarado"))
            continue
        if l["u"] > lim["U"]:
            falhas.append(dict(item=l["cod"], erro=f"U {l['u']:.3f} > {lim['U']:.2f}"))
        if l["fso"] > lim["FSo"]:
            falhas.append(dict(item=l["cod"], erro=f"FSo {l['fso']:.2f} % > {lim['FSo']:.1f} %"))
        # O atraso termico e a metade da linha da tabela que ninguem confere, e
        # aqui ele REPROVA — por excesso de desempenho, nao por falta. A linha
        # "parede leve refletora" da ZB8 pressupoe uma parede de U alto; uma
        # parede de U = 0,53 nao cabe nessa categoria, cabe numa melhor que a
        # tabela nao tem. Reprovar e mesmo assim o comportamento certo: quem
        # decide se a categoria mudou e o projetista, nao a verificacao.
        if lim.get("atraso") and l["atraso_h"] > lim["atraso"]:
            falhas.append(dict(item=l["cod"], classe="atraso",
                               erro=f"atraso {l['atraso_h']:.2f} h > {lim['atraso']:.1f} h "
                                    f"da categoria '{lim['rotulo']}' (U = {l['u']:.3f}, "
                                    f"muito abaixo do U <= {lim['U']:.2f} que a categoria supoe)"))
    return falhas


def sem_isolante(pj, cod: str, material: str) -> dict:
    """Quanto vale, em U, uma camada — removendo-a e recalculando.

    E o unico jeito honesto de responder "esse isolante compensa?": nao pela
    ficha do fabricante, pela parede inteira sem ele.
    """
    import nucleo.camadas as cm
    from dataclasses import replace
    comp = cm.COMPOSICOES[cod]
    novo = replace(comp, camadas=tuple(c for c in comp.camadas
                                       if c.material != material))
    com = resistencia(pj, comp)
    sem = resistencia(pj, novo)
    return dict(material=material, u_com=com["u"], u_sem=sem["u"],
                ganho=round(1 - com["u"] / sem["u"], 4),
                ponte_com=com["penalidade_ponte"], ponte_sem=sem["penalidade_ponte"])
