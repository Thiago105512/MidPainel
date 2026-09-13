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
    norma: str = ""
    obs: str = ""

    @property
    def total(self) -> float:
        """Espessura que esta camada ocupa na parede."""
        return self.espessura * self.n


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
_N_GESSO = "NBR 14715"
_N_CIM = "NBR 15498"
_N_LA = "NBR 11722"
_N_XPS = "NBR 11752"
_N_PERF = "NBR 15217"

COMPOSICOES = {
    "PE-1": Composicao(
        cod="PE-1", nome="Parede externa unica", esp_nominal=150, rw=45,
        onde="todas as faces externas, sem excecao",
        camadas=(
            Camada("PLCIM", 10.0, "vedacao", "externa", norma=_N_CIM,
                   obs="placa cimenticia, face exposta a chuva"),
            Camada("XPS", 20.0, "barreira", "externa", norma=_N_XPS,
                   obs="ISO strip continuo: quebra termica E barreira de vapor "
                       "do lado quente-umido — a funcao principal e evitar "
                       "condensacao no montante, nao economizar energia"),
            Camada("ACO", 90.0, "estrutural", "miolo", norma="NBR 15253",
                   obs="montante Ue 90; a espessura da camada e a alma"),
            Camada("LAROCHA", 50.0, "isolante", "miolo", norma=_N_LA,
                   obs="dentro da cavidade do montante, nao soma espessura"),
            Camada("GESSO", 12.5, "vedacao", "interna", norma=_N_GESSO),
        )),
    "PH-1": Composicao(
        cod="PH-1", nome="Parede hidraulica interna", esp_nominal=150, rw=44,
        onde="apenas onde passa prumada de esgoto DN100 ou ha louca suspensa",
        camadas=(
            Camada("GESSORU", 12.5, "vedacao", "externa", norma=_N_GESSO,
                   obs="RU: resistente a umidade, face molhada"),
            Camada("ACO", 90.0, "estrutural", "miolo", norma="NBR 15253"),
            Camada("LAROCHA", 50.0, "isolante", "miolo", norma=_N_LA),
            Camada("GESSO", 12.5, "vedacao", "interna", norma=_N_GESSO),
        )),
    "PA-1": Composicao(
        cod="PA-1", nome="Parede acustica", esp_nominal=100, rw=49,
        onde="intimo x fonte de ruido, social x servico, entorno do core",
        camadas=(
            Camada("GESSO", 12.5, "vedacao", "externa", n=2, norma=_N_GESSO,
                   obs="dupla chapa: +5 dB por chapa, o ganho acustico mais "
                       "barato que existe"),
            Camada("ACO", 48.0, "estrutural", "miolo", norma="NBR 15253"),
            Camada("LAVIDRO", 48.0, "isolante", "miolo", norma=_N_LA),
            Camada("GESSO", 12.5, "vedacao", "interna", n=2, norma=_N_GESSO),
        )),
    "PA-2": Composicao(
        cod="PA-2", nome="Parede acustica de alto desempenho",
        esp_nominal=150, rw=56,
        onde="EXCLUSIVAMENTE a parede entre a oficina e o estar/jantar",
        camadas=(
            Camada("GESSO", 12.5, "vedacao", "externa", n=2, norma=_N_GESSO),
            Camada("ACO", 16.0, "barreira", "externa", norma=_N_PERF,
                   obs="perfil resiliente: desacopla a chapa do montante e "
                       "acrescenta 7 a 9 dB dentro da mesma espessura"),
            Camada("ACO", 70.0, "estrutural", "miolo", norma="NBR 15253"),
            Camada("LAROCHA", 50.0, "isolante", "miolo", norma=_N_LA),
            Camada("GESSO", 12.5, "vedacao", "interna", n=2, norma=_N_GESSO),
        )),
    "PI-1": Composicao(
        cod="PI-1", nome="Divisoria interna simples", esp_nominal=100, rw=41,
        onde="dentro de zonas homogeneas",
        camadas=(
            Camada("GESSO", 12.5, "vedacao", "externa", norma=_N_GESSO),
            Camada("ACO", 70.0, "estrutural", "miolo", norma="NBR 15253"),
            Camada("LAVIDRO", 50.0, "isolante", "miolo", norma=_N_LA),
            Camada("GESSO", 12.5, "vedacao", "interna", norma=_N_GESSO),
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
