"""PECA — o item que a fabrica corta e a obra instala (secoes 47 a 51, 66, 46).

Um painel e uma ideia; a peca e o objeto. Aqui cada elemento ganha identidade
estavel, comprimento, massa, furos, recortes e marcacao — e, com isso, deixa de
existir apenas no desenho.

A identidade precisa ser ESTAVEL entre revisoes. Se o codigo de uma peca muda
porque outra foi inserida antes dela, toda a rastreabilidade se perde: a bobina
apontaria para a peca errada, a inspecao para o painel errado. Por isso o codigo
deriva da POSICAO no painel, nao da ordem de geracao.

O furo em LSF nao e detalhe de obra. O montante e uma chapa de 0,95 mm
trabalhando a compressao: furo fora de lugar reduz a carga critica, e o
eletricista resolve cortando a aba — que e exatamente onde esta a rigidez.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

PREFIXO = {
    "stud": "ST", "track": "TR", "joist": "JO", "rafter": "RF",
    "king stud": "KS", "jack stud": "JS", "cripple superior": "CS",
    "cripple inferior": "CI", "header": "HD", "sill": "SL",
    "blocking": "BL", "bridging": "BR", "strap": "SP", "hold-down": "HO",
    "anchor": "AN", "screw": "SC", "truss member": "TM",
}
# Zona util de furacao: fracao da altura da alma onde o furo e admitido,
# medida do eixo. Fora dela o furo corta a regiao que trabalha a compressao.
ZONA_FURO = 0.25
DIAM_MAX_ALMA = 0.50        # do diametro em relacao a altura da alma
BORDA_FURO_MIN = 25.0       # mm da extremidade da peca


@dataclass
class Furo:
    x: float            # mm ao longo da peca
    d: float            # mm de diametro
    forma: str = "circular"
    servico: str = ""   # eletrica, hidraulica, dados
    obs: str = ""


@dataclass
class PecaDetalhada:
    cod: str
    familia: str
    perfil: str
    comp: float
    massa: float
    painel: str
    pav: str
    x: float
    z: float
    vertical: bool
    furos: list = field(default_factory=list)
    recortes: list = field(default_factory=list)
    marcacao: str = ""
    revisao: str = ""

    def passaporte(self) -> dict:
        """Secao 66: o que acompanha a peca da bobina ao fim de vida."""
        return dict(
            id=self.cod, familia=self.familia, perfil=self.perfil,
            comprimento=round(self.comp, 1), massa=round(self.massa, 3),
            painel=self.painel, pavimento=self.pav,
            posicao=dict(x=self.x, z=self.z, vertical=self.vertical),
            furos=len(self.furos), marcacao=self.marcacao,
            revisao=self.revisao,
            # os campos abaixo so se preenchem quando o dado existir de fato
            bobina=None, heat=None, lote=None, producao=None,
            inspecao=None, instalacao=None, fim_de_vida=None)

    def carga_marcacao(self) -> str:
        """Texto que a marcadora grava na peca (secao 51)."""
        return f"{self.cod}|{self.painel}|{self.perfil}|{self.comp:.0f}|{self.revisao}"


def _codigo(familia: str, painel: str, x: float, z: float) -> str:
    """Codigo estavel: deriva da posicao, nao da ordem de geracao.

    Ate R25 a funcao dizia isto e fazia o contrario: o numero legivel era `seq`,
    o contador global de geracao. Enquanto duas revisoes produzissem a MESMA
    quantidade de pecas, o defeito nao aparecia — bastou um cripple a menos num
    painel para renumerar tudo o que vinha depois, e mover uma janela 600 mm
    passou a "afetar" 73 % da casa. Codigo de peca e identidade: se ele muda
    porque um vizinho mudou, a rastreabilidade entre revisoes nao existe.

    Agora o codigo e formado so por coisas que a peca E: o painel a que
    pertence, a familia estrutural e o hash da posicao dentro do painel. Nada
    ali depende de quantas pecas existem antes. Duas pecas da mesma familia na
    mesma posicao do mesmo painel nao podem existir, entao a chave e unica — e
    a auditoria confere a unicidade, em vez de supor.
    """
    p = PREFIXO.get(familia, familia[:2].upper())
    chave = f"{painel}|{familia}|{int(x)}|{int(z)}"
    # R82 — tres caracteres (4.096 valores) colidiram em 1.201 pecas
    # (SP16-1-ST75A duas vezes); quatro (65.536) deixam a colisao improvavel,
    # e a auditoria de unicidade continua conferindo em vez de supor
    h = hashlib.sha1(chave.encode()).hexdigest()[:4].upper()
    return f"{painel}-{p}{h}"


def furos_de_servico(comp: float, alma: float, servicos: list) -> list[Furo]:
    """Gera os furos de passagem no eixo da alma, dentro da zona util."""
    out = []
    if not servicos:
        return out
    passo = comp / (len(servicos) + 1)
    for i, s in enumerate(servicos, 1):
        d = min(s.get("d", 25.0), DIAM_MAX_ALMA * alma)
        # R80 — o servico pode dizer a ALTURA do furo (eletrica a 1.450, agua a
        # 400): e a cota em que o percurso corre na parede. Sem altura, divide
        # o montante em partes iguais, como antes.
        alvo = s["z"] if s.get("z") is not None else passo * i
        x = max(BORDA_FURO_MIN + d / 2,
                min(comp - BORDA_FURO_MIN - d / 2, alvo))
        out.append(Furo(x=x, d=d, servico=s.get("servico", ""),
                        obs="no eixo da alma, dentro da zona util"))
    return out


def verificar_furos(p: PecaDetalhada, alma: float) -> list[str]:
    """Furo grande demais, na borda, ou proximo demais de outro."""
    ruins = []
    for f in p.furos:
        if f.d > DIAM_MAX_ALMA * alma:
            ruins.append(f"{p.cod}: furo de {f.d:.0f} mm acima de "
                         f"{DIAM_MAX_ALMA*alma:.0f} (metade da alma)")
        if f.x < BORDA_FURO_MIN or p.comp - f.x < BORDA_FURO_MIN:
            ruins.append(f"{p.cod}: furo a {min(f.x, p.comp-f.x):.0f} mm da "
                         f"extremidade, minimo {BORDA_FURO_MIN:.0f}")
    for a, b in zip(sorted(p.furos, key=lambda f: f.x),
                    sorted(p.furos, key=lambda f: f.x)[1:]):
        livre = (b.x - b.d / 2) - (a.x + a.d / 2)
        if livre < max(a.d, b.d):
            ruins.append(f"{p.cod}: {livre:.0f} mm entre furos, minimo "
                         f"{max(a.d, b.d):.0f} (um diametro)")
    return ruins


def detalhar(paineis: list, cat_massa: dict, pav: str, revisao: str,
             servicos_por_painel: dict = None) -> list[PecaDetalhada]:
    """Transforma as pecas do painel em pecas de fabrica, com ID e furo."""
    servicos_por_painel = servicos_por_painel or {}
    out = []
    for pa in paineis:
        for pc in pa.pecas:
            d = PecaDetalhada(
                cod=_codigo(pc.familia, pa.cod, pc.x, pc.z),
                familia=pc.familia, perfil=pc.perfil, comp=pc.comp,
                massa=cat_massa[pc.perfil] * pc.comp / 1000.0,
                painel=pa.cod, pav=pav, x=pc.x, z=pc.z,
                vertical=pc.vertical, revisao=revisao)
            if pc.familia in ("stud", "king stud"):
                serv = servicos_por_painel.get(pa.cod, [])
                alma = float(pc.perfil.split()[1].split("x")[0])
                d.furos = furos_de_servico(pc.comp, alma, serv)
            d.marcacao = d.carga_marcacao()
            out.append(d)
    return out


# --------------------------------------------------------------- clash (46)
@dataclass
class Volume:
    cod: str
    disciplina: str      # estrutura, eletrica, hidraulica, hvac, arquitetura
    x0: float
    y0: float
    z0: float
    x1: float
    y1: float
    z1: float

    def intersecta(self, o: "Volume", folga: float = 0.0) -> float:
        """Volume de interpenetracao em mm3. Zero = sem conflito."""
        dx = min(self.x1, o.x1) - max(self.x0, o.x0) + folga
        dy = min(self.y1, o.y1) - max(self.y0, o.y0) + folga
        dz = min(self.z1, o.z1) - max(self.z0, o.z0) + folga
        if dx <= 0 or dy <= 0 or dz <= 0:
            return 0.0
        return dx * dy * dz


def detectar_clash(volumes: list, pares_ignorados=()) -> list[dict]:
    """Interferencia entre disciplinas. Ignora conflito dentro da mesma peca."""
    ign = {frozenset(p) for p in pares_ignorados}
    out = []
    for i, a in enumerate(volumes):
        for b in volumes[i + 1:]:
            if a.disciplina == b.disciplina:
                continue
            if frozenset((a.disciplina, b.disciplina)) in ign:
                continue
            v = a.intersecta(b)
            if v > 0:
                out.append(dict(a=a.cod, b=b.cod, volume=v,
                                disciplinas=(a.disciplina, b.disciplina),
                                severidade="critico" if v > 1e6 else "revisar"))
    return sorted(out, key=lambda d: -d["volume"])
