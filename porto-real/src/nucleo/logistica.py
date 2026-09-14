"""LOGISTICA — embalar, carregar, icar e transportar (secoes 96 a 102).

Um painel de LSF e leve e grande: o que limita o transporte quase nunca e o
peso, e sim o volume e a dimensao. Por isso o calculo aqui comeca pela
geometria e so depois olha a balanca.

O ponto que costuma faltar: o centro de gravidade. Um painel com todas as
aberturas de um lado nao sobe equilibrado, e o ponto de icamento colocado no
meio geometrico o faz girar no ar. Aqui o CG sai da soma dos momentos das pecas.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

CONTAINERS = {
    "20'": dict(comp=5_898, larg=2_352, alt=2_393, carga_kg=28_200, volume=33.2),
    "40'": dict(comp=12_032, larg=2_352, alt=2_393, carga_kg=26_680, volume=67.7),
    "40HC": dict(comp=12_032, larg=2_352, alt=2_698, carga_kg=26_512, volume=76.3),
}
# (H) limites rodoviarios: variam por pais, estado e via
LIMITES_RODOVIARIOS = dict(largura=2_600, altura=4_400, comprimento=18_600,
                           peso_kg=45_000,
                           obs="(H) conforme legislacao local — confirmar")


@dataclass
class Volume3D:
    cod: str
    comp: float
    larg: float
    alt: float
    massa: float
    cg_local: tuple = None      # (x, y, z) do CG dentro da peca

    @property
    def volume(self) -> float:
        return self.comp * self.larg * self.alt / 1e9   # m3

    def cg(self) -> tuple:
        return self.cg_local or (self.comp / 2, self.larg / 2, self.alt / 2)


def centro_de_gravidade(itens: list, posicoes: dict = None) -> dict:
    """CG do conjunto, pela soma dos momentos (secao 99)."""
    posicoes = posicoes or {}
    m = sum(i.massa for i in itens)
    if m <= 0:
        return dict(massa=0.0, cg=(0.0, 0.0, 0.0))
    sx = sy = sz = 0.0
    for i in itens:
        px, py, pz = posicoes.get(i.cod, (0.0, 0.0, 0.0))
        cx, cy, cz = i.cg()
        sx += i.massa * (px + cx)
        sy += i.massa * (py + cy)
        sz += i.massa * (pz + cz)
    return dict(massa=m, cg=(sx / m, sy / m, sz / m))


def cg_painel(painel, cat_massa: dict) -> dict:
    """CG do painel a partir das pecas — nao do meio geometrico.

    Um painel com as aberturas de um lado nao sobe equilibrado; o ponto de
    icamento no meio geometrico o faz girar no ar.
    """
    m = sx = sz = 0.0
    for p in painel.pecas:
        mm = cat_massa[p.perfil] * p.comp / 1000.0
        cx = p.x + (0.0 if p.vertical else p.comp / 2)
        cz = p.z + (p.comp / 2 if p.vertical else 0.0)
        m += mm
        sx += mm * cx
        sz += mm * cz
    if m <= 0:
        return dict(massa=0.0, x=0.0, z=0.0, desvio=0.0)
    x, z = sx / m, sz / m
    return dict(massa=m, x=x, z=z, desvio=x - painel.comp / 2,
                desvio_rel=(x - painel.comp / 2) / painel.comp)


def pontos_icamento(painel, cat_massa: dict, n: int = 2,
                    angulo_cabo: float = 60.0) -> dict:
    """Posicao dos pontos, carga em cada um e tracao no cabo (secao 100)."""
    cg = cg_painel(painel, cat_massa)
    if n < 2:
        raise ValueError("icamento com um ponto so gira: minimo 2")
    # pontos simetricos em torno do CG, a 1/4 e 3/4 do vao util
    meia = painel.comp * 0.25
    pts = [cg["x"] - meia, cg["x"] + meia] if n == 2 else \
          [cg["x"] + meia * (2 * k / (n - 1) - 1) for k in range(n)]
    pts = [max(100.0, min(painel.comp - 100.0, p)) for p in pts]
    # distribuicao por alavanca simples entre os dois extremos
    a, b = min(pts), max(pts)
    if b - a < 1e-6:
        cargas = [cg["massa"] / n] * n
    else:
        f_b = cg["massa"] * (cg["x"] - a) / (b - a)
        f_a = cg["massa"] - f_b
        cargas = [f_a, f_b] if n == 2 else [cg["massa"] / n] * n
    t = max(cargas) / math.sin(math.radians(angulo_cabo)) * 9.81 / 1000.0
    return dict(pontos=[round(p, 1) for p in pts],
                cargas_kg=[round(c, 1) for c in cargas],
                tracao_cabo_kn=round(t, 2), angulo=angulo_cabo,
                cg=cg,
                alerta="" if abs(cg["desvio_rel"]) < 0.08 else
                f"CG deslocado {cg['desvio']:.0f} mm do meio "
                f"({cg['desvio_rel']*100:.1f} %): o painel gira se icado pelo "
                f"centro geometrico")


def carregar_container(itens: list, tipo: str = "40HC") -> dict:
    """Empacotamento simples por camadas, com CG e checagem de peso (secao 97)."""
    c = CONTAINERS[tipo]
    pilhas, usados, rejeitados = [], [], []
    x = 0.0
    for it in sorted(itens, key=lambda i: -i.comp):
        if it.comp > c["comp"] or it.larg > c["larg"] or it.alt > c["alt"]:
            rejeitados.append((it.cod, "nao cabe nas dimensoes internas"))
            continue
        if x + it.larg > c["comp"]:
            pilhas.append(list(usados))
            usados, x = [], 0.0
        usados.append((it, x))
        x += it.larg + 20
    if usados:
        pilhas.append(usados)
    postos = [it for p in pilhas for it, _ in p]
    massa = sum(i.massa for i in postos)
    vol = sum(i.volume for i in postos)
    pos = {}
    for p_i, p in enumerate(pilhas):
        for it, off in p:
            pos[it.cod] = (off, p_i * 400.0, 0.0)
    cg = centro_de_gravidade(postos, pos)
    return dict(container=tipo, n=len(postos), rejeitados=rejeitados,
                massa=massa, volume=vol,
                uso_peso=massa / c["carga_kg"], uso_volume=vol / c["volume"],
                cg=cg["cg"], pilhas=len(pilhas),
                excede_peso=massa > c["carga_kg"],
                limitante="peso" if massa / c["carga_kg"] > vol / c["volume"]
                          else "volume")


def dentro_do_limite(comp: float, larg: float, alt: float, peso: float) -> dict:
    """Limites rodoviarios (H)."""
    L = LIMITES_RODOVIARIOS
    faltas = []
    for nome, v, lim in (("largura", larg, L["largura"]),
                         ("altura", alt, L["altura"]),
                         ("comprimento", comp, L["comprimento"]),
                         ("peso", peso, L["peso_kg"])):
        if v > lim:
            faltas.append(f"{nome} {v:.0f} acima do limite {lim:.0f}")
    return dict(ok=not faltas, faltas=faltas, obs=L["obs"])
