"""CAMADAS — o fechamento deixa de ser coeficiente e passa a ser geometria.

Ate R33 a estrutura era especificada peca a peca — 11 perfis com designacao
completa, aco, revestimento e massa derivada — e o FECHAMENTO inteiro saia de
um numero escolhido a dedo:

    area_placa_m2 = area_m2 * 2.4

E cada camada era esse numero vezes outro coeficiente: OSB 0,45, cimenticia
0,55, gesso 1,00, la 0,90, membrana 0,50. Seis numeros arbitrados onde ha
geometria para derivar — o modelo ja sabe o comprimento, a altura e as
aberturas de cada um dos 62 paineis.

O coeficiente acertava por acaso: 710,2 m2 contra 718,6 m2 de area real de
duas faces, 1 % de erro. Nao e acerto, e cancelamento — e o mesmo padrao do
`len(pecas) * 8` dos parafusos e do `8,0 kN` da carga.

ESPECIFICACAO POR DESEMPENHO, NAO POR MARCA. Cada camada declara material,
espessura, funcao e norma. Nao declara fabricante nem ficha tecnica de produto
comercial: densidade de manta especifica, Rw de sistema ensaiado e TRRF de
composicao vem de RELATORIO DE ENSAIO, entram marcados (H) e viram pendencia.
Uma ficha tecnica inventada seria plausivel e indistinguivel de uma real, e e
exatamente esse o erro que o projeto recusa desde os contratos da E23.
"""
from __future__ import annotations

from dataclasses import dataclass

FUNCOES = ("estrutural", "isolante", "barreira", "vedacao", "acabamento")
FACES = ("externa", "interna", "miolo")


@dataclass(frozen=True)
class Camada:
    material: str          # codigo em materiais.MATERIAIS
    espessura: float       # mm, por chapa
    funcao: str
    face: str
    n: int = 1             # chapas por face (dupla chapa = 2)
    obs: str = ""

    @property
    def total(self) -> float:
        """Espessura que esta camada ocupa na parede."""
        return self.espessura * self.n

    @property
    def norma(self) -> str:
        """Do MATERIAL, nao da camada.

        Esta propriedade nasceu como campo proprio e durou uma revisao. Duas
        fontes para o mesmo fato divergem na primeira correcao — foi assim que
        o projeto teve dois codigos para a mesma peca (defeito 39). Nao ha
        razao para repetir o erro dois dias depois de documenta-lo.
        """
        import nucleo.materiais as mt
        m = mt.POR_MATERIAL.get(self.material)
        return m.norma if m else ""

    @property
    def formato(self) -> tuple:
        """Dimensao comercial da chapa ou rolo, do material."""
        import nucleo.materiais as mt
        m = mt.POR_MATERIAL.get(self.material)
        return m.chapa if m else ()


@dataclass(frozen=True)
class Composicao:
    cod: str
    nome: str
    esp_nominal: int       # espessura MODULAR declarada, em mm
    camadas: tuple
    rw: float = 0.0        # (H) de ensaio do sistema
    onde: str = ""

    @property
    def esp_construida(self) -> float:
        return sum(c.total for c in self.camadas)

    @property
    def folga(self) -> float:
        """Nominal menos construida. Positiva e tolerancia; negativa e erro."""
        return self.esp_nominal - self.esp_construida

    def por_face(self, face: str) -> tuple:
        return tuple(c for c in self.camadas if c.face == face)


# ---------------------------------------------------------------------------
# AS COMPOSICOES
# ---------------------------------------------------------------------------
# Cada uma e a transcricao, camada a camada, do que a prancha PR-12 ja
# descrevia em prosa no campo `comp` de especificacao.FAMILIAS. Transcricao, e
# nao redacao nova: se divergirem, a auditoria acusa, e quem manda e a prancha.
#
# A espessura NOMINAL e modular — a parede ocupa um modulo de 100 ou 150 mm. A
# CONSTRUIDA e a soma das camadas. A diferenca e tolerancia de montagem e
# acabamento, e precisa ser positiva: uma parede que se constroi mais grossa
# que o modulo nao cabe no modulo.

COMPOSICOES = {
    "PE-1": Composicao(
        cod="PE-1", nome="Parede externa unica", esp_nominal=150, rw=45,
        onde="todas as faces externas, sem excecao",
        camadas=(
            Camada("PLCIM", 10.0, "vedacao", "externa",
                   obs="placa cimenticia, face exposta a chuva"),
            Camada("XPS", 20.0, "barreira", "externa",
                   obs="ISO strip continuo: quebra termica E barreira de vapor "
                       "do lado quente-umido — a funcao principal e evitar "
                       "condensacao no montante, nao economizar energia"),
            Camada("ACO", 90.0, "estrutural", "miolo",
                   obs="montante Ue 90; a espessura da camada e a alma"),
            Camada("LAROCHA", 50.0, "isolante", "miolo",
                   obs="dentro da cavidade do montante, nao soma espessura"),
            Camada("GESSO", 12.5, "vedacao", "interna"),
        )),
    "PH-1": Composicao(
        cod="PH-1", nome="Parede hidraulica interna", esp_nominal=150, rw=44,
        onde="apenas onde passa prumada de esgoto DN100 ou ha louca suspensa",
        camadas=(
            Camada("GESSORU", 12.5, "vedacao", "externa",
                   obs="RU: resistente a umidade, face molhada"),
            Camada("ACO", 90.0, "estrutural", "miolo"),
            Camada("LAROCHA", 50.0, "isolante", "miolo"),
            Camada("GESSO", 12.5, "vedacao", "interna"),
        )),
    "PA-1": Composicao(
        cod="PA-1", nome="Parede acustica", esp_nominal=100, rw=49,
        onde="intimo x fonte de ruido, social x servico, entorno do core",
        camadas=(
            Camada("GESSO", 12.5, "vedacao", "externa", n=2,
                   obs="dupla chapa: +5 dB por chapa, o ganho acustico mais "
                       "barato que existe"),
            Camada("ACO", 48.0, "estrutural", "miolo"),
            Camada("LAVIDRO", 48.0, "isolante", "miolo"),
            Camada("GESSO", 12.5, "vedacao", "interna", n=2),
        )),
    "PA-2": Composicao(
        cod="PA-2", nome="Parede acustica de alto desempenho",
        esp_nominal=150, rw=56,
        onde="EXCLUSIVAMENTE a parede entre a oficina e o estar/jantar",
        camadas=(
            Camada("GESSO", 12.5, "vedacao", "externa", n=2),
            Camada("ACO", 16.0, "barreira", "externa",
                   obs="perfil resiliente: desacopla a chapa do montante e "
                       "acrescenta 7 a 9 dB dentro da mesma espessura"),
            Camada("ACO", 70.0, "estrutural", "miolo"),
            Camada("LAROCHA", 50.0, "isolante", "miolo"),
            Camada("GESSO", 12.5, "vedacao", "interna", n=2),
        )),
    "PI-1": Composicao(
        cod="PI-1", nome="Divisoria interna simples", esp_nominal=100, rw=41,
        onde="dentro de zonas homogeneas",
        camadas=(
            Camada("GESSO", 12.5, "vedacao", "externa"),
            Camada("ACO", 70.0, "estrutural", "miolo"),
            Camada("LAVIDRO", 50.0, "isolante", "miolo"),
            Camada("GESSO", 12.5, "vedacao", "interna"),
        )),
}


def conferir_espessuras() -> list[dict]:
    """A soma das camadas cabe no modulo declarado?

    A camada isolante NAO soma: ela vive dentro da cavidade do montante. Somar
    a la de rocha a espessura da parede seria contar o mesmo espaco duas vezes
    — e daria uma parede de 182,5 mm onde ha 150.
    """
    out = []
    for c in COMPOSICOES.values():
        util = sum(x.total for x in c.camadas if x.funcao != "isolante")
        out.append(dict(cod=c.cod, nominal=c.esp_nominal, construida=util,
                        folga=c.esp_nominal - util,
                        cabe=util <= c.esp_nominal,
                        camadas=len(c.camadas)))
    return out


# Diametro externo do tubo de esgoto, NBR 5688. O DN nao e o diametro externo:
# DN100 tem 110 mm de face a face, e essa diferenca de 10 mm e exatamente a
# que decide se ele cabe na cavidade do montante.
DE_ESGOTO = {"DN40": 40.0, "DN50": 50.0, "DN75": 75.0, "DN100": 110.0}


def cabe_prumada(comp: Composicao, dn: str = "DN100",
                 folga: float = 20.0) -> dict:
    """A prumada cabe DENTRO da cavidade desta parede?

    A justificativa escrita da PH-1 e que os 150 mm existem "para acomodar o
    tubo DN100". Transcrever a parede camada a camada permite conferir a
    afirmacao, e a conferencia depende de um detalhe que a prosa esconde: a
    cavidade nao e a espessura da parede, e a alma do montante. Uma parede de
    150 mm com montante de 90 tem 90 mm de cavidade, e o DN100 tem 110 de
    diametro EXTERNO.
    """
    cav = max((c.total for c in comp.camadas if c.funcao == "estrutural"),
              default=0.0)
    d = DE_ESGOTO.get(dn, 0.0)
    precisa = d + folga
    return dict(composicao=comp.cod, dn=dn, diametro_externo=d,
                cavidade=cav, precisa=precisa, cabe=cav >= precisa,
                leitura=(f"{comp.cod}: cavidade de {cav:.0f} mm (alma do "
                         f"montante) para um {dn} de {d:.0f} mm de diametro "
                         f"externo + {folga:.0f} de folga"
                         + ("" if cav >= precisa else
                            f" — FALTAM {precisa - cav:.0f} mm: a prumada nao "
                            f"passa dentro do montante e tem de ir em shaft, "
                            f"como a PR-21 ja determina")))


# ---------------------------------------------------------------------------
# QUANTIDADE — da geometria do painel, nao de coeficiente
# ---------------------------------------------------------------------------
def area_do_painel(p) -> dict:
    """Area bruta, de abertura e liquida de UM painel, por face.

    A abertura desconta das duas faces: uma janela e um buraco, nao um
    revestimento diferente. Foi este desconto que o coeficiente nao fazia —
    ele multiplicava a area de PROJETO, que nao sabe onde ha janela.
    """
    bruta = p.comp * p.altura / 1e6
    vao = sum(a["larg"] * a["alt"] for a in p.aberturas) / 1e6
    return dict(painel=p.cod, bruta=bruta, aberturas=vao,
                liquida=max(0.0, bruta - vao))


def quantificar(paineis, familia_por_painel: dict) -> dict:
    """Area de cada CAMADA de cada material, somada sobre a casa inteira.

    A camada de miolo (montante, la) conta UMA vez por painel; a camada de face
    conta uma vez por face, e as duas faces de uma divisoria interna existem. E
    por isso que o coeficiente unico nao podia funcionar: parede externa e
    parede interna tem numero de faces diferente do ponto de vista de QUEM as
    recebe, mas a mesma parede tem duas faces sempre — o que muda e o material
    de cada uma.
    """
    por_material: dict[str, float] = {}
    por_composicao: dict[str, float] = {}
    detalhe = []
    sem_familia = []
    for p in paineis:
        fam = familia_por_painel.get(p.cod)
        if fam is None or fam not in COMPOSICOES:
            sem_familia.append(p.cod)
            continue
        comp = COMPOSICOES[fam]
        a = area_do_painel(p)
        por_composicao[fam] = por_composicao.get(fam, 0.0) + a["liquida"]
        for c in comp.camadas:
            # miolo e por painel; face e por face — e um painel tem duas
            vezes = 1 if c.face == "miolo" else 1
            area = a["liquida"] * c.n * vezes
            chave = (c.material, c.espessura)
            por_material[chave] = por_material.get(chave, 0.0) + area
            detalhe.append(dict(painel=p.cod, composicao=fam,
                                material=c.material, espessura=c.espessura,
                                funcao=c.funcao, face=c.face, n=c.n,
                                area=round(area, 2)))
    itens = [dict(material=m, espessura=e, area=round(a, 1))
             for (m, e), a in sorted(por_material.items(),
                                     key=lambda kv: -kv[1])]
    return dict(itens=itens, por_composicao=por_composicao, detalhe=detalhe,
                sem_familia=sem_familia,
                area_total=round(sum(i["area"] for i in itens), 1))


def familia_por_painel(paineis, segmentos) -> dict:
    """Casa cada painel com o trecho de parede classificado que o originou.

    Pelo TRECHO que mais se sobrepoe, nao pelo eixo mais proximo. A primeira
    versao usava proximidade de eixo e classificou 62 de 62 paineis sem que
    uma unica divisoria simples (PI-1) aparecesse — sinal de que estava
    casando painel com a parede errada, e nao de que a casa nao tem divisoria.

    `segmentos` vem de especificacao.paredes_classificadas(): cada um traz
    ori ("H" ou "V"), fixo (a coordenada constante), ini, fim e familia.
    """
    saida, orfaos = {}, []
    for p in paineis:
        eixo = p.y if p.horizontal else p.x
        a0 = p.x if p.horizontal else p.y
        a1 = a0 + p.comp
        melhor, area = None, 0.0
        for s in segmentos:
            if (s["ori"] == "H") != bool(p.horizontal):
                continue
            if abs(s["fixo"] - eixo) > 200:      # mesma linha de parede
                continue
            sobrep = min(a1, s["fim"]) - max(a0, s["ini"])
            if sobrep > area:
                melhor, area = s, sobrep
        if melhor is None or area <= 0:
            orfaos.append(p.cod)
        else:
            saida[p.cod] = melhor["familia"]
    return dict(familia=saida, orfaos=orfaos,
                cobertura=len(saida) / max(1, len(paineis)))


# ---------------------------------------------------------------------------
# PAGINACAO — ninguem compra metro quadrado, compra placa
# ---------------------------------------------------------------------------
def _ladrilhar(larg_face: float, alt_face: float,
               larg_ch: float, alt_ch: float) -> dict:
    """Cobre uma face com placas inteiras, e devolve os retalhos que sobram.

    A primeira versao tratou a face inteira como uma PECA a ser cortada de uma
    placa — e uma parede de 3.600 x 2.600 nao cabe numa chapa de 1.200 x 2.400,
    entao 92 pecas sairam como "nao cabem" e a paginacao devolveu 2 placas para
    a casa toda. O erro nao era de calculo: era de modelo. Uma face nao e
    cortada de uma placa, ela e COBERTA por varias.

    A cobertura e em colunas de largura da chapa. A ultima coluna e a ultima
    fiada sobram parciais, e essas sobras sao retalhos — nao lixo: elas voltam
    para o corte, como as sobras de barra voltam para o nesting.
    """
    import math
    ncol = int(math.ceil(larg_face / larg_ch))
    nfila = int(math.ceil(alt_face / alt_ch))
    inteiras = 0
    retalhos = []
    for c in range(ncol):
        w = min(larg_ch, larg_face - c * larg_ch)
        for f in range(nfila):
            h = min(alt_ch, alt_face - f * alt_ch)
            if w >= larg_ch - 1 and h >= alt_ch - 1:
                inteiras += 1
            else:
                retalhos.append((w, h))
    # Junta e o encontro de DUAS placas, e por isso conta uma vez, nao duas.
    # Somar o perimetro de cada placa dava 16.607 m de fita para esta casa —
    # dezesseis quilometros, o que e visivelmente absurdo e foi assim que o
    # erro apareceu. A junta interna e o numero de encontros vezes o vao:
    # (colunas - 1) verticais e (fiadas - 1) horizontais.
    # Sao dois insumos, e somar os dois num numero so dava 2,44 m de "fita" por
    # m2 contra 1,6 a 2,2 da pratica. Entre duas placas vai FITA e massa; no
    # encontro com piso, teto e canto vai CANTONEIRA ou perfil de acabamento,
    # que e outro produto e outro preco.
    junta_int = (ncol - 1) * alt_face + (nfila - 1) * larg_face
    # As bordas horizontais (piso e teto) sao exclusivas desta face. As
    # VERTICAIS encostam no painel vizinho, e a junta entre dois paineis e uma
    # so — contar as duas dava 2,44 m de acabamento por m2 contra 1,6 a 2,2 da
    # pratica, e o excesso era exatamente este. Mesmo principio da junta entre
    # placas, um nivel acima.
    borda = 2 * larg_face + alt_face
    return dict(inteiras=inteiras, retalhos=retalhos,
                junta_m=junta_int / 1000.0, borda_m=borda / 1000.0,
                area=larg_face * alt_face / 1e6)


def paginar(paineis, familia: dict) -> dict:
    """Quantas placas inteiras, e quanto sobra.

    O BOM dizia "546,5 m2 de gesso". Nao existe pedido de 546,5 m2: existe
    pedido de N placas de 1.200 x 2.400. A diferenca nao e formal — ela e a
    PERDA, e num pe-direito de 2.600 mm com placa de 2.400 ela e grande por um
    motivo geometrico simples: toda parede pede uma emenda horizontal e uma
    fiada de 200 mm.

    Os retalhos nao viram lixo: sao reagrupados pelo mesmo nestar_chapas() que
    corta o OSB, como as sobras de barra voltam para o nesting de 6 m.
    """
    import nucleo.materiais as mt
    import nucleo.nesting as ns

    por_material: dict = {}
    for p in paineis:
        fam = familia.get(p.cod)
        comp = COMPOSICOES.get(fam)
        if comp is None:
            continue
        for c in comp.camadas:
            m = mt.POR_MATERIAL.get(c.material)
            if not m or not m.chapa or c.funcao == "estrutural":
                continue
            larg_ch, alt_ch = m.chapa
            # area liquida: a abertura nao recebe placa
            a = area_do_painel(p)
            fator = a["liquida"] / a["bruta"] if a["bruta"] else 1.0
            d = _ladrilhar(p.comp, p.altura, larg_ch, alt_ch)
            reg = por_material.setdefault((c.material, c.espessura),
                                          dict(inteiras=0, retalhos=[],
                                               area=0.0, faces=0, perim=0.0,
                                               borda=0.0))
            reg["inteiras"] += int(round(d["inteiras"] * fator)) * c.n
            for i in range(c.n):
                reg["retalhos"] += [(f"{p.cod}-{c.material}{i}-{k}", w, h)
                                    for k, (w, h) in enumerate(d["retalhos"])]
            reg["area"] += a["liquida"] * c.n
            reg["faces"] += c.n
            # Junta so existe onde ha tratamento de junta. La de rocha e XPS
            # sao encaixados, nao fitados — inclui-los levava a 2,54 m de fita
            # por m2 de placa, contra 1,6 a 2,2 da pratica. A funcao da camada
            # ja diz isso: vedacao recebe fita, isolante e barreira nao.
            if c.funcao == "vedacao":
                reg["perim"] += d["junta_m"] * c.n * fator
                reg["borda"] += d["borda_m"] * c.n * fator

    saida = []
    for (material, esp), reg in sorted(por_material.items(),
                                       key=lambda kv: -kv[1]["area"]):
        m = mt.POR_MATERIAL[material]
        larg_ch, alt_ch = m.chapa
        r = ns.nestar_chapas(reg["retalhos"], larg=larg_ch, alt=alt_ch)
        placas = reg["inteiras"] + r["n"]
        bruta = placas * larg_ch * alt_ch / 1e6
        saida.append(dict(
            material=material, nome=m.nome, espessura=esp, norma=m.norma,
            formato=f"{larg_ch:.0f} x {alt_ch:.0f}",
            placas=placas, inteiras=reg["inteiras"], de_retalho=r["n"],
            area_util=round(reg["area"], 1), area_bruta=round(bruta, 1),
            aproveitamento=reg["area"] / bruta if bruta else 0.0,
            nao_cabem=len(r.get("nao_cabem", [])),
            junta_m=round(reg["perim"], 1),
            borda_m=round(reg["borda"], 1)))
    return dict(itens=saida,
                placas=sum(i["placas"] for i in saida),
                area_bruta=round(sum(i["area_bruta"] for i in saida), 1),
                area_util=round(sum(i["area_util"] for i in saida), 1),
                junta_m=round(sum(i["junta_m"] for i in saida), 1),
                borda_m=round(sum(i["borda_m"] for i in saida), 1))


# ---------------------------------------------------------------------------
# PISO, FORRO E COBERTURA — os planos horizontais, que nao tinham camada
# ---------------------------------------------------------------------------
# Ate R34 so a PAREDE tinha composicao. Contrapiso, forro e o painel de
# cobertura ficavam fora do BOM — o mesmo buraco que o vigamento teve ate R31,
# e pela mesma razao: ninguem tinha escrito que deviam existir.
COMPOSICOES_PLANO = {
    "EP-1": Composicao(
        cod="EP-1", nome="Entrepiso seco sobre vigamento", esp_nominal=250,
        onde="piso do pavimento superior, sobre o vigamento",
        camadas=(
            Camada("OSB", 18.0, "estrutural", "externa",
                   obs="substrato estrutural, tambem diafragma horizontal"),
            Camada("LAROCHA", 50.0, "isolante", "miolo",
                   obs="entre as vigas: ruido de impacto e aereo"),
            Camada("GESSO", 12.5, "vedacao", "interna",
                   obs="forro do pavimento de baixo, parafusado na viga"),
        )),
    "FO-1": Composicao(
        cod="FO-1", nome="Forro suspenso", esp_nominal=100,
        onde="ambientes sob cobertura e sob area molhada",
        camadas=(
            Camada("GESSO", 12.5, "vedacao", "interna"),
            Camada("LAVIDRO", 50.0, "isolante", "miolo",
                   obs="sobre o forro: absorve e isola o atico"),
        )),
    "CB-1": Composicao(
        cod="CB-1", nome="Cobertura em painel sanduiche", esp_nominal=75,
        onde="toda a cobertura, 5 % de caimento",
        camadas=(
            Camada("PIR", 75.0, "isolante", "externa",
                   obs="painel sanduiche autoportante entre tercas; face "
                       "metalica nos dois lados ja e a estanqueidade"),
        )),
}


def quantificar_planos(casa: dict) -> dict:
    """Area de camada dos planos horizontais, da geometria do vigamento.

    A area vem dos PLANOS que o vigamento ja define — cada comodo vigado tem
    vao, corrido e tipo. Nao ha coeficiente: o piso do superior e a soma dos
    comodos do superior, e a cobertura e a soma do que esta sob ela.
    """
    por_material: dict = {}
    detalhe = []
    for pl in casa["planos"]:
        if not pl["ok"]:
            continue
        area = pl["vao"] * pl["corrido"] / 1e6
        comp = COMPOSICOES_PLANO["EP-1" if pl["tipo"] == "piso" else "CB-1"]
        for c in comp.camadas:
            chave = (c.material, c.espessura)
            por_material[chave] = por_material.get(chave, 0.0) + area * c.n
            detalhe.append(dict(plano=pl["regiao"], tipo=pl["tipo"],
                                composicao=comp.cod, material=c.material,
                                espessura=c.espessura, area=round(area, 2)))
    itens = [dict(material=m, espessura=e, area=round(a, 1))
             for (m, e), a in sorted(por_material.items(), key=lambda kv: -kv[1])]
    return dict(itens=itens, detalhe=detalhe,
                area_total=round(sum(i["area"] for i in itens), 1))
