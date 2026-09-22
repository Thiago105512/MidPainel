"""
Motor de desenho tecnico — nucleo.

Coordenadas do MODELO em milimetros (unidade mestre da base R32).
Coordenadas do PAPEL em milimetros, origem no canto superior esquerdo,
Y crescente para baixo (convencao SVG).

Convencoes normativas adotadas:
  NBR 10068 — formatos de folha e margens
  NBR 10582 — posicao do carimbo (legenda)
  NBR 8403  — larguras de linha
  NBR 8402  — caligrafia tecnica (alturas de texto)
  NBR 6492  — representacao de projetos de arquitetura
"""
from __future__ import annotations

import math
from contextlib import contextmanager
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

# --------------------------------------------------------------------------
# formatos de folha (NBR 10068) — largura x altura em mm, margem esquerda 25
# --------------------------------------------------------------------------
FORMATOS = {
    "A0": (1189, 841, 10),
    "A1": (841, 594, 10),
    "A2": (594, 420, 7),
    "A3": (420, 297, 7),
    "A4": (297, 210, 7),
}
MARGEM_ESQ = 25.0

# --------------------------------------------------------------------------
# larguras de linha (NBR 8403) em mm de papel
# --------------------------------------------------------------------------
LW = {
    "corte": 0.60,     # elementos seccionados pelo plano de corte
    "corte2": 0.40,    # secao secundaria
    "vista": 0.30,     # arestas vistas
    "fino": 0.18,      # mobiliario, pisos, simbolos
    "cota": 0.13,      # linhas de cota e auxiliares
    "eixo": 0.13,      # eixos e linhas de centro
    "oculto": 0.20,    # projecoes / elementos ocultos
    "hachura": 0.10,
    "moldura": 0.70,
}

# alturas de texto (NBR 8402) em mm de papel
TXT = {"micro": 1.4, "min": 1.8, "peq": 2.5, "med": 3.5, "gr": 5.0, "tit": 7.0}

CINZA = "#8a8a8a"
PRETO = "#000000"


# --------------------------------------------------------------------------
# geometria
# --------------------------------------------------------------------------
# R65 — a formatacao mora no nucleo (nucleo/formato.py); aqui so se reexporta,
# para que prancha e visualizador continuem a importar de core.
from nucleo.formato import num_br, brl  # noqa: E402,F401


@dataclass(frozen=True)
class P:
    x: float
    y: float

    def __add__(self, o: "P") -> "P":
        return P(self.x + o.x, self.y + o.y)

    def __sub__(self, o: "P") -> "P":
        return P(self.x - o.x, self.y - o.y)

    def __mul__(self, k: float) -> "P":
        return P(self.x * k, self.y * k)

    @property
    def norma(self) -> float:
        return math.hypot(self.x, self.y)

    def unit(self) -> "P":
        n = self.norma
        return P(self.x / n, self.y / n) if n else P(0.0, 0.0)

    def perp(self) -> "P":
        """Normal a 90 graus no sentido anti-horario."""
        return P(-self.y, self.x)

    def rot(self, ang_rad: float) -> "P":
        c, s = math.cos(ang_rad), math.sin(ang_rad)
        return P(self.x * c - self.y * s, self.x * s + self.y * c)


def retangulo(x: float, y: float, w: float, h: float) -> list[P]:
    return [P(x, y), P(x + w, y), P(x + w, y + h), P(x, y + h)]


def area_poligono(pts: list[P]) -> float:
    """Area em unidades do modelo ao quadrado (mm2). Formula do shoelace."""
    s = 0.0
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        s += a.x * b.y - b.x * a.y
    return abs(s) / 2.0


def centroide(pts: list[P]) -> P:
    return P(sum(p.x for p in pts) / len(pts), sum(p.y for p in pts) / len(pts))


def m2(area_mm2: float) -> float:
    return area_mm2 / 1_000_000.0


# --------------------------------------------------------------------------
# transformacao modelo -> papel
# --------------------------------------------------------------------------
@dataclass
class View:
    """Mapeia coordenadas do modelo (mm reais) para o papel (mm).

    escala = denominador (50 -> 1:50). ox/oy = posicao no papel, em mm,
    do ponto (mx0, my0) do modelo. O eixo Y do modelo aponta para cima
    (convencao arquitetonica) e e invertido na projecao para o papel.
    """
    escala: float
    ox: float
    oy: float
    mx0: float = 0.0
    my0: float = 0.0

    def k(self) -> float:
        return 1.0 / self.escala

    def pt(self, p: P) -> tuple[float, float]:
        return (self.ox + (p.x - self.mx0) * self.k(),
                self.oy - (p.y - self.my0) * self.k())

    def d(self, valor_modelo: float) -> float:
        """Converte um comprimento do modelo para mm de papel."""
        return valor_modelo * self.k()

    def inv_d(self, valor_papel: float) -> float:
        """Converte mm de papel para comprimento do modelo."""
        return valor_papel * self.escala


# --------------------------------------------------------------------------
# canvas SVG
# --------------------------------------------------------------------------
class Canvas:
    def __init__(self, formato: str = "A1", fundo: str = "#ffffff"):
        self.larg, self.alt, self.marg = FORMATOS[formato]
        self.formato = formato
        self.fundo = fundo
        self._el: list[str] = []
        self._defs: list[str] = []
        self._def_ids: set[str] = set()
        self._abertos = 0
        self._cx0 = self._cy0 = 1e9      # caixa do que ja foi desenhado
        self._cx1 = self._cy1 = -1e9
        self._n_rec = 0
        self._folha = None          # recorte da folha, aberto por pranchas.base
        self._corte_folha = None

    # ---- caixa do desenho -------------------------------------------------
    def _marcar(self, *pts) -> None:
        for x, y in pts:
            if x < self._cx0: self._cx0 = x
            if y < self._cy0: self._cy0 = y
            if x > self._cx1: self._cx1 = x
            if y > self._cy1: self._cy1 = y

    def zerar_caixa(self) -> None:
        """Recomeca a medicao da caixa do desenho (apos moldura e carimbo)."""
        self._cx0 = self._cy0 = 1e9
        self._cx1 = self._cy1 = -1e9

    def caixa_desenho(self) -> tuple[float, float, float, float]:
        """(x0, y0, x1, y1) do que foi emitido, em mm de papel."""
        return (self._cx0, self._cy0, self._cx1, self._cy1)

    def extravasamento(self, folga: float = 0.0) -> dict:
        """Quanto o desenho passou de cada lado da moldura.

        Traco fora da moldura nao e traco discreto: e traco que NAO EXISTE.
        O papel corta, o SVG corta no viewBox, e ninguem fica sabendo."""
        # folga ALARGA a area aceita: a estimativa de caixa do texto e grosseira
        m, e = self.marg - folga, MARGEM_ESQ - folga
        x0, y0, x1, y1 = self.caixa_desenho()
        if x1 < x0:
            return {}
        fora = {}
        if x0 < e: fora["esquerda"] = round(e - x0, 1)
        if y0 < m: fora["cima"] = round(m - y0, 1)
        if x1 > self.larg - m: fora["direita"] = round(x1 - (self.larg - m), 1)
        if y1 > self.alt - m: fora["baixo"] = round(y1 - (self.alt - m), 1)
        return fora

    # ---- recorte -----------------------------------------------------------
    @contextmanager
    def recorte(self, x0: float, y0: float, x1: float, y1: float):
        """Limita ao retangulo o que for desenhado no bloco.

        Nao e enfeite: e o que impede que uma vista grande demais para a folha
        vaze para fora da moldura sem que ninguem perceba."""
        self._n_rec += 1
        nome = f"rec{self._n_rec}"
        self._defs.append(
            f'<clipPath id="{nome}"><rect x="{x0:.2f}" y="{y0:.2f}" '
            f'width="{x1 - x0:.2f}" height="{y1 - y0:.2f}"/></clipPath>')
        self._el.append(f'<g clip-path="url(#{nome})" data-tipo="recorte">')
        self._abertos += 1
        fora = (self._cx0, self._cy0, self._cx1, self._cy1)
        self._cx0 = self._cy0 = 1e9
        self._cx1 = self._cy1 = -1e9
        rec = {"cortou": {}, "caixa": None}
        try:
            yield rec
        finally:
            self._el.append("</g>")
            self._abertos -= 1
            ix0, iy0, ix1, iy1 = self._cx0, self._cy0, self._cx1, self._cy1
            if ix1 >= ix0:
                rec["caixa"] = (ix0, iy0, ix1, iy1)
                if ix0 < x0: rec["cortou"]["esquerda"] = round(x0 - ix0, 1)
                if iy0 < y0: rec["cortou"]["cima"] = round(y0 - iy0, 1)
                if ix1 > x1: rec["cortou"]["direita"] = round(ix1 - x1, 1)
                if iy1 > y1: rec["cortou"]["baixo"] = round(iy1 - y1, 1)
            # o que foi recortado nao conta como extravasamento: foi contido
            gx0, gy0, gx1, gy1 = fora
            self._cx0 = min(gx0, max(ix0, x0)) if ix1 >= ix0 else gx0
            self._cy0 = min(gy0, max(iy0, y0)) if ix1 >= ix0 else gy0
            self._cx1 = max(gx1, min(ix1, x1)) if ix1 >= ix0 else gx1
            self._cy1 = max(gy1, min(iy1, y1)) if ix1 >= ix0 else gy1

    # ---- primitivas em coordenadas de PAPEL -------------------------------
    def _stroke(self, estilo: str, cor: str | None = None, dash: str | None = None) -> str:
        w = LW.get(estilo, 0.25)
        s = f'stroke="{cor or PRETO}" stroke-width="{w}" fill="none"'
        if dash:
            s += f' stroke-dasharray="{dash}"'
        elif estilo == "eixo":
            s += ' stroke-dasharray="6,2,1,2"'
        elif estilo == "oculto":
            s += ' stroke-dasharray="3,2"'
        return s

    def linha_p(self, a: tuple[float, float], b: tuple[float, float],
                estilo: str = "vista", cor: str | None = None, dash: str | None = None) -> None:
        self._marcar(a, b)
        self._el.append(
            f'<line x1="{a[0]:.3f}" y1="{a[1]:.3f}" x2="{b[0]:.3f}" y2="{b[1]:.3f}" '
            f'{self._stroke(estilo, cor, dash)} stroke-linecap="round"/>')

    def imagem_p(self, pos: tuple[float, float], w: float, h: float, caminho: str) -> bool:
        """PNG embutido (base64) — perspectivas renderizadas do modelo (R66).

        A imagem entra na caixa de desenho como qualquer traco: a ocupacao da
        folha e a moldura a veem. Se o arquivo nao existe, devolve False e nao
        desenha nada — a prancha decide como avisar.
        """
        import base64, os
        if not os.path.exists(caminho):
            return False
        with open(caminho, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        self._marcar(pos, (pos[0] + w, pos[1] + h))
        self._el.append(
            f'<image x="{pos[0]:.3f}" y="{pos[1]:.3f}" width="{w:.3f}" height="{h:.3f}" '
            f'preserveAspectRatio="xMidYMid slice" xlink:href="data:image/png;base64,{b64}"/>')
        return True

    def poli_p(self, pts: list[tuple[float, float]], estilo: str = "vista",
               fechado: bool = False, preenche: str = "none",
               cor: str | None = None, dash: str | None = None) -> None:
        self._marcar(*pts)
        d = " ".join(f"{x:.3f},{y:.3f}" for x, y in pts)
        tag = "polygon" if fechado else "polyline"
        st = self._stroke(estilo, cor, dash).replace('fill="none"', f'fill="{preenche}"')
        self._el.append(f'<{tag} points="{d}" {st} stroke-linejoin="miter"/>')

    def circ_p(self, c: tuple[float, float], r: float, estilo: str = "vista",
               preenche: str = "none", cor: str | None = None) -> None:
        self._marcar((c[0] - r, c[1] - r), (c[0] + r, c[1] + r))
        st = self._stroke(estilo, cor).replace('fill="none"', f'fill="{preenche}"')
        self._el.append(f'<circle cx="{c[0]:.3f}" cy="{c[1]:.3f}" r="{r:.3f}" {st}/>')

    def arco_p(self, c: tuple[float, float], r: float, a0: float, a1: float,
               estilo: str = "fino", cor: str | None = None) -> None:
        """Angulos em graus, sentido trigonometrico, no espaco do papel (Y p/ baixo)."""
        x0 = c[0] + r * math.cos(math.radians(a0))
        y0 = c[1] - r * math.sin(math.radians(a0))
        x1 = c[0] + r * math.cos(math.radians(a1))
        y1 = c[1] - r * math.sin(math.radians(a1))
        self._marcar((x0, y0), (x1, y1))
        grande = 1 if abs(a1 - a0) > 180 else 0
        varr = 0 if a1 > a0 else 1
        self._el.append(
            f'<path d="M {x0:.3f} {y0:.3f} A {r:.3f} {r:.3f} 0 {grande} {varr} {x1:.3f} {y1:.3f}" '
            f'{self._stroke(estilo, cor)}/>')

    def texto_p(self, pos: tuple[float, float], s: str, h: float = TXT["peq"],
                anc: str = "middle", rot: float = 0.0, cor: str = PRETO,
                peso: str = "normal", base: str = "middle",
                fam: str = "Helvetica, Arial, sans-serif") -> None:
        # o texto ocupa area: sem isso um rotulo fora da moldura passaria batido
        meia = len(s) * h * 0.30
        if rot:
            self._marcar((pos[0] - h, pos[1] - meia), (pos[0] + h, pos[1] + meia))
        else:
            dx = {"start": (0, 2 * meia), "end": (2 * meia, 0)}.get(anc, (meia, meia))
            self._marcar((pos[0] - dx[0], pos[1] - h * 0.7),
                         (pos[0] + dx[1], pos[1] + h * 0.7))
        tr = f' transform="rotate({-rot:.2f} {pos[0]:.3f} {pos[1]:.3f})"' if rot else ""
        self._el.append(
            f'<text x="{pos[0]:.3f}" y="{pos[1]:.3f}" font-family="{fam}" '
            f'font-size="{h:.2f}" font-weight="{peso}" fill="{cor}" '
            f'text-anchor="{anc}" dominant-baseline="{base}"{tr}>{escape(s)}</text>')

    # ---- proveniencia -----------------------------------------------------
    #
    # O modelo sabe que aquele retangulo e a COZINHA, codigo T-COZ, 21,60 m2.
    # Ate aqui o SVG recebia `<line>` e `<polygon>` soltos: a informacao morria
    # entre o modelo e o papel, e por isso a prancha na tela nao passava de uma
    # fotografia de si mesma. O escopo carrega a procedencia para dentro do
    # desenho — sem alterar um unico traco do que se imprime, porque `data-*`
    # nao tem efeito visual nenhum.
    @staticmethod
    def _at(v) -> str:
        return (str(v).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))

    @contextmanager
    def escopo(self, tipo: str, cod: str | None = None, **dados):
        """Agrupa o que for emitido no bloco num <g> com data-tipo/data-cod."""
        at = f' data-tipo="{self._at(tipo)}"'
        if cod:
            at += f' data-cod="{self._at(cod)}"'
        for k, v in dados.items():
            if v is None or v == "":
                continue
            at += f' data-{k}="{self._at(v)}"'
        self._el.append(f"<g{at}>")
        self._abertos += 1
        try:
            yield self
        finally:
            self._el.append("</g>")
            self._abertos -= 1

    def grupo(self, nome: str) -> None:
        self._el.append(f'<g id="{nome}">')
        self._abertos += 1

    def fim_grupo(self) -> None:
        self._el.append("</g>")
        self._abertos -= 1

    # ---- padroes de hachura ----------------------------------------------
    def hachura(self, nome: str, espac: float = 1.2, ang: float = 45.0,
                w: float = 0.08, cor: str = "#000") -> str:
        if nome in self._def_ids:
            return nome
        self._def_ids.add(nome)
        self._defs.append(
            f'<pattern id="{nome}" patternUnits="userSpaceOnUse" '
            f'width="{espac}" height="{espac}" patternTransform="rotate({ang})">'
            f'<line x1="0" y1="0" x2="0" y2="{espac}" stroke="{cor}" stroke-width="{w}"/>'
            f"</pattern>")
        return nome

    def hachura_dupla(self, nome: str, espac: float = 1.0, w: float = 0.08,
                      cor: str = "#000") -> str:
        if nome in self._def_ids:
            return nome
        self._def_ids.add(nome)
        self._defs.append(
            f'<pattern id="{nome}" patternUnits="userSpaceOnUse" '
            f'width="{espac}" height="{espac}">'
            f'<line x1="0" y1="0" x2="{espac}" y2="{espac}" stroke="{cor}" stroke-width="{w}"/>'
            f'<line x1="{espac}" y1="0" x2="0" y2="{espac}" stroke="{cor}" stroke-width="{w}"/>'
            f"</pattern>")
        return nome

    def pontilhado(self, nome: str, espac: float = 1.0, r: float = 0.12,
                   cor: str = "#000") -> str:
        if nome in self._def_ids:
            return nome
        self._def_ids.add(nome)
        self._defs.append(
            f'<pattern id="{nome}" patternUnits="userSpaceOnUse" '
            f'width="{espac}" height="{espac}">'
            f'<circle cx="{espac/2}" cy="{espac/2}" r="{r}" fill="{cor}"/>'
            f"</pattern>")
        return nome

    # ---- moldura e carimbo ------------------------------------------------
    def moldura(self) -> None:
        m, e = self.marg, MARGEM_ESQ
        with self.escopo("moldura"):
            self._el.append(
                f'<rect x="{e}" y="{m}" width="{self.larg - e - m:.2f}" '
                f'height="{self.alt - 2*m:.2f}" fill="none" stroke="#000" '
                f'stroke-width="{LW["moldura"]}"/>')

    # ---- recorte da folha --------------------------------------------------
    def abrir_folha(self) -> None:
        """Recorta TODO o desenho a moldura, uma vez, para a folha inteira.

        Garantia estrutural: depois disto nenhuma prancha consegue emitir
        conteudo fora da moldura sem que o corte seja medido e relatado.
        """
        self._folha = self.recorte(MARGEM_ESQ, self.marg,
                                   self.larg - self.marg, self.alt - self.marg)
        self._corte_folha = self._folha.__enter__()

    def fechar_folha(self) -> None:
        if self._folha is not None:
            self._folha.__exit__(None, None, None)
            self._folha = None

    def cortado(self) -> dict:
        """Quanto de desenho a moldura comeu, por lado, em mm de papel."""
        self.fechar_folha()
        return dict(self._corte_folha["cortou"]) if self._corte_folha else {}

    def svg(self) -> str:
        self.fechar_folha()
        if self._abertos:
            raise RuntimeError(
                f"{self._abertos} escopo(s) sem fechar: tudo o que veio depois "
                f"herdaria uma procedencia que nao e a sua")
        defs = f"<defs>{''.join(self._defs)}</defs>" if self._defs else ""
        return (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" '
            f'width="{self.larg}mm" height="{self.alt}mm" '
            f'viewBox="0 0 {self.larg} {self.alt}">\n'
            f'<rect width="{self.larg}" height="{self.alt}" fill="{self.fundo}"/>\n'
            f"{defs}\n" + "\n".join(self._el) + "\n</svg>\n")

    def salvar(self, caminho: str) -> str:
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(self.svg())
        return caminho
