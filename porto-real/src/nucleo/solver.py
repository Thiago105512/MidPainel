"""SOLVER — analise de porticos espaciais por rigidez direta (secoes 15, 16, 18).

Ate R16 o projeto verificava FLECHA por formula fechada de viga isolada, o que
so vale enquanto cada viga e de fato isolada. Uma parede de LSF nao e: o
montante recebe carga axial do piso acima e flexao do vento ao mesmo tempo, e a
guia redistribui o que chega. Sem resolver a estrutura inteira, a interacao
N + M — que e o que de fato governa o montante — nao existe.

Doze graus de liberdade por barra: tres translacoes e tres rotacoes em cada
extremidade. Segunda ordem por matriz geometrica, iterada ate convergir, que e
o que revela o efeito P-Delta: a carga vertical, atuando sobre a estrutura ja
deslocada pelo vento, amplifica o proprio deslocamento.

Convencao local: x ao longo da barra, do no inicial para o final; z para cima
sempre que a barra nao for vertical; y completando o triedro direto.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from nucleo.algebra import Skyline, Mecanismo, produto

GL = 6            # graus de liberdade por no
LIVRE = (False,) * 6
ENGASTE = (True,) * 6
ROTULA = (True, True, True, False, False, False)


@dataclass
class No:
    cod: str
    x: float
    y: float
    z: float
    apoio: tuple = LIVRE       # (ux, uy, uz, rx, ry, rz) True = restringido

    def p(self):
        return (self.x, self.y, self.z)


@dataclass
class Secao:
    """O que o solver precisa saber de um perfil. Vem de nucleo.perfis."""
    cod: str
    A: float
    Iy: float          # inercia para flexao no plano local x-z
    Iz: float          # inercia para flexao no plano local x-y
    J: float
    E: float = 205_000.0
    G: float = 78_850.0

    @classmethod
    def de_perfil(cls, perfil, aco=None):
        d = perfil.props()
        E = aco.E if aco and hasattr(aco, "E") else 205_000.0
        return cls(perfil.cod, d["A"], d["Iy"], d["Ix"], d["J"], E)


@dataclass
class Barra:
    cod: str
    ni: str
    nj: str
    secao: Secao
    roll: float = 0.0          # giro em torno do eixo da barra, graus
    q_local: tuple = (0.0, 0.0)   # carga distribuida local (qy, qz), kN/m
    N: float = 0.0             # esforco axial da iteracao anterior (P-Delta)


def _eixos(pi, pj, roll_graus=0.0):
    dx, dy, dz = (pj[0] - pi[0], pj[1] - pi[1], pj[2] - pi[2])
    L = math.sqrt(dx * dx + dy * dy + dz * dz)
    if L < 1e-9:
        raise ValueError("barra de comprimento nulo")
    ex = (dx / L, dy / L, dz / L)
    ref = (0.0, 0.0, 1.0)
    if abs(ex[0] * ref[0] + ex[1] * ref[1] + ex[2] * ref[2]) > 0.9999:
        ref = (1.0, 0.0, 0.0)
    ey = _norm(_cruz(ref, ex))
    ez = _cruz(ex, ey)
    if roll_graus:
        c, s = math.cos(math.radians(roll_graus)), math.sin(math.radians(roll_graus))
        ey, ez = (tuple(c * a + s * b for a, b in zip(ey, ez)),
                  tuple(-s * a + c * b for a, b in zip(ey, ez)))
    return L, (ex, ey, ez)


def _cruz(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _norm(v):
    m = math.sqrt(sum(c * c for c in v))
    return tuple(c / m for c in v)


def k_local(s: Secao, L: float) -> list:
    """Rigidez elastica local, 12 x 12."""
    k = [[0.0] * 12 for _ in range(12)]
    EA, GJ = s.E * s.A / L, s.G * s.J / L
    k[0][0] = k[6][6] = EA
    k[0][6] = k[6][0] = -EA
    k[3][3] = k[9][9] = GJ
    k[3][9] = k[9][3] = -GJ
    for I, (a, b, c, d) in ((s.Iz, (1, 5, 7, 11)), (s.Iy, (2, 4, 8, 10))):
        e = s.E * I
        sg = 1.0 if I is s.Iz else -1.0        # o plano x-z inverte o acoplamento
        k[a][a] = k[c][c] = 12 * e / L ** 3
        k[a][c] = k[c][a] = -12 * e / L ** 3
        k[b][b] = k[d][d] = 4 * e / L
        k[b][d] = k[d][b] = 2 * e / L
        k[a][b] = k[b][a] = sg * 6 * e / L ** 2
        k[a][d] = k[d][a] = sg * 6 * e / L ** 2
        k[c][b] = k[b][c] = -sg * 6 * e / L ** 2
        k[c][d] = k[d][c] = -sg * 6 * e / L ** 2
    return k


def kg_local(N: float, L: float) -> list:
    """Rigidez geometrica local (N positivo = tracao)."""
    g = [[0.0] * 12 for _ in range(12)]
    if N == 0.0:
        return g
    for (a, b, c, d) in ((1, 5, 7, 11), (2, 4, 8, 10)):
        sg = 1.0 if a == 1 else -1.0
        g[a][a] = g[c][c] = 6 * N / (5 * L)
        g[a][c] = g[c][a] = -6 * N / (5 * L)
        g[b][b] = g[d][d] = 2 * N * L / 15
        g[b][d] = g[d][b] = -N * L / 30
        g[a][b] = g[b][a] = sg * N / 10
        g[a][d] = g[d][a] = sg * N / 10
        g[c][b] = g[b][c] = -sg * N / 10
        g[c][d] = g[d][c] = -sg * N / 10
    g[3][3] = g[9][9] = 0.0
    return g


def _T(eixos):
    """Matriz de rotacao 12 x 12 em blocos."""
    R = eixos
    T = [[0.0] * 12 for _ in range(12)]
    for blk in range(4):
        for i in range(3):
            for j in range(3):
                T[blk * 3 + i][blk * 3 + j] = R[i][j]
    return T


def _tkt(k, T):
    """T^T . k . T"""
    kt = [[sum(k[i][m] * T[m][j] for m in range(12)) for j in range(12)]
          for i in range(12)]
    return [[sum(T[m][i] * kt[m][j] for m in range(12)) for j in range(12)]
            for i in range(12)]


def _feq(b: Barra, L: float) -> list:
    """Forcas de engastamento perfeito da carga distribuida, local."""
    # Os sinais NAO foram deduzidos no papel: foram determinados contra a
    # solucao fechada do balanco com carga distribuida, delta = wL4/8EI, que os
    # fixa sem ambiguidade. As quatro combinacoes possiveis foram testadas e so
    # esta reproduz o valor exato.
    qy, qz = b.q_local
    f = [0.0] * 12
    f[1] = f[7] = -qy * L / 2
    f[5], f[11] = qy * L * L / 12, -qy * L * L / 12
    f[2] = f[8] = -qz * L / 2
    f[4], f[10] = -qz * L * L / 12, qz * L * L / 12
    return f


@dataclass
class Modelo:
    nos: dict = field(default_factory=dict)
    barras: dict = field(default_factory=dict)
    cargas_no: dict = field(default_factory=dict)   # cod -> [Fx,Fy,Fz,Mx,My,Mz]

    def no(self, cod, x, y, z, apoio=LIVRE):
        self.nos[cod] = No(cod, x, y, z, apoio)
        return self.nos[cod]

    def barra(self, cod, ni, nj, secao, roll=0.0, q_local=(0.0, 0.0)):
        self.barras[cod] = Barra(cod, ni, nj, secao, roll, q_local)
        return self.barras[cod]

    def carga(self, no, fx=0, fy=0, fz=0, mx=0, my=0, mz=0):
        v = self.cargas_no.setdefault(no, [0.0] * 6)
        for i, c in enumerate((fx, fy, fz, mx, my, mz)):
            v[i] += c

    # ------------------------------------------------------------- solucao
    def resolver(self, segunda_ordem: bool = False, iteracoes: int = 12,
                 tol: float = 1e-5) -> dict:
        ordem = list(self.nos)
        idx = {c: i for i, c in enumerate(ordem)}
        n = len(ordem) * GL
        rest = [False] * n
        for c, no in self.nos.items():
            for k, r in enumerate(no.apoio):
                if r:
                    rest[idx[c] * GL + k] = True
        livres = [i for i in range(n) if not rest[i]]
        pos = {g: i for i, g in enumerate(livres)}

        anterior = None
        for it in range(iteracoes if segunda_ordem else 1):
            K = Skyline(len(livres))
            F = [0.0] * len(livres)
            for c, v in self.cargas_no.items():
                for k in range(GL):
                    g = idx[c] * GL + k
                    if g in pos:
                        F[pos[g]] += v[k]
            cache = {}
            for b in self.barras.values():
                L, eixos = _eixos(self.nos[b.ni].p(), self.nos[b.nj].p(), b.roll)
                T = _T(eixos)
                kl = k_local(b.secao, L)
                if segunda_ordem and b.N:
                    kgl = kg_local(b.N, L)
                    kl = [[kl[i][j] + kgl[i][j] for j in range(12)] for i in range(12)]
                kg = _tkt(kl, T)
                fl = _feq(b, L)
                fg = [sum(T[m][i] * fl[m] for m in range(12)) for i in range(12)]
                cache[b.cod] = (L, T, kl, fl)
                gl = [idx[b.ni] * GL + k for k in range(GL)] + \
                     [idx[b.nj] * GL + k for k in range(GL)]
                for a in range(12):
                    ga = gl[a]
                    if ga not in pos:
                        continue
                    F[pos[ga]] -= fg[a]
                    for bb in range(12):
                        gb = gl[bb]
                        if gb in pos and pos[gb] >= pos[ga]:
                            K.add(pos[ga], pos[gb], kg[a][bb])
            K.montar()
            K.fatorar()
            u_livre = K.resolver(F)
            u = [0.0] * n
            for g, i in pos.items():
                u[g] = u_livre[i]

            # esforcos de extremidade e axial para a proxima iteracao
            esf = {}
            for b in self.barras.values():
                L, T, kl, fl = cache[b.cod]
                gl = [idx[b.ni] * GL + k for k in range(GL)] + \
                     [idx[b.nj] * GL + k for k in range(GL)]
                ug = [u[g] for g in gl]
                ul = [sum(T[i][m] * ug[m] for m in range(12)) for i in range(12)]
                fe = [sum(kl[i][m] * ul[m] for m in range(12)) + fl[i]
                      for i in range(12)]
                esf[b.cod] = fe
                b.N = -fe[0]                     # tracao positiva
            if not segunda_ordem:
                break
            if anterior is not None:
                d = max(abs(a - c) for a, c in zip(u, anterior)) or 0.0
                ref = max(abs(v) for v in u) or 1.0
                if d / ref < tol:
                    break
            anterior = list(u)

        # reacoes
        reac = {}
        for c, no in self.nos.items():
            if not any(no.apoio):
                continue
            r = [0.0] * 6
            for b in self.barras.values():
                if b.ni != c and b.nj != c:
                    continue
                L, T, kl, fl = cache[b.cod]
                fe = esf[b.cod]
                off = 0 if b.ni == c else 6
                fg = [sum(T[m][i] * fe[m] for m in range(12)) for i in range(12)]
                for k in range(6):
                    r[k] += fg[off + k]
            reac[c] = r
        return dict(u=u, idx=idx, esforcos=esf, reacoes=reac,
                    iteracoes=it + 1, gl_livres=len(livres))

    def deslocamento(self, res, no, comp=2):
        return res["u"][res["idx"][no] * GL + comp]
