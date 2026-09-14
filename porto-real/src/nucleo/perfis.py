"""PERFIS — propriedades de secao pela linha media (secoes 08 e 09).

Nao ha uma formula por forma aqui. Ha UM solver: a secao entra como poligonal
da linha media com espessura constante, e dele saem A, Ix, Iy, Ixy, eixos
principais, J, centro de torcao e Cw. C, Ue, U, Z, Sigma, Omega, Cartola e
Cantoneira sao apenas poligonais diferentes — e um perfil que ninguem previu
entra como lista de pontos, sem tocar no solver.

O metodo e o linear da NBR 6355 (anexo): a parede vira linha de espessura t, e a
inercia propria da parede em torno do proprio eixo (t^3/12 por unidade de
comprimento) e desprezada, como a norma faz. Os cantos entram arredondados,
discretizados em arcos.

O centro de torcao sai da condicao de Vlasov — o polo para o qual a area
setorial e ortogonal a x e a y — e nao de tabela. Isso e verificavel: para um U
simples o resultado tem de dar e = 3b^2/(h + 6b), que e solucao fechada
conhecida. A verificacao esta em auditoria3.checar_perfis.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

# ---------------------------------------------------------------- geometria
def _arco(centro, p_ini, p_fim, n=4):
    """Discretiza o canto arredondado entre dois pontos, em torno do centro."""
    cx, cy = centro
    a0 = math.atan2(p_ini[1] - cy, p_ini[0] - cx)
    a1 = math.atan2(p_fim[1] - cy, p_fim[0] - cx)
    d = a1 - a0
    while d > math.pi:
        d -= 2 * math.pi
    while d < -math.pi:
        d += 2 * math.pi
    r = math.hypot(p_ini[0] - cx, p_ini[1] - cy)
    return [(cx + r * math.cos(a0 + d * i / n), cy + r * math.sin(a0 + d * i / n))
            for i in range(1, n)]


def arredondar(pts: list[tuple], r: float, n: int = 4) -> list[tuple]:
    """Substitui cada vertice interno por um arco de raio r na linha media."""
    if r <= 0 or len(pts) < 3:
        return list(pts)
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        u = _unit(a, b)
        v = _unit(b, c)
        ang = math.acos(max(-1.0, min(1.0, u[0] * v[0] + u[1] * v[1])))
        if ang < 1e-6 or abs(ang - math.pi) < 1e-6:
            out.append(b)
            continue
        # recuo do vertice ate o ponto de tangencia
        rec = r / math.tan((math.pi - ang) / 2)
        rec = min(rec, _dist(a, b) * 0.49, _dist(b, c) * 0.49)
        p1 = (b[0] - u[0] * rec, b[1] - u[1] * rec)
        p2 = (b[0] + v[0] * rec, b[1] + v[1] * rec)
        # centro do arco: na bissetriz interna
        nx, ny = -u[1], u[0]
        s = 1.0 if (u[0] * v[1] - u[1] * v[0]) > 0 else -1.0
        centro = (p1[0] + s * nx * r, p1[1] + s * ny * r)
        out.append(p1)
        out += _arco(centro, p1, p2, n)
        out.append(p2)
    out.append(pts[-1])
    return out


def _unit(a, b):
    d = _dist(a, b)
    return ((b[0] - a[0]) / d, (b[1] - a[1]) / d) if d else (0.0, 0.0)


def _dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


# ---------------------------------------------------------------- solver
def propriedades(pts: list[tuple], t: float, fechado: bool = False) -> dict:
    """Todas as propriedades da secao, em mm e suas potencias."""
    segs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    if fechado:
        segs.append((pts[-1], pts[0]))
    L = sum(_dist(a, b) for a, b in segs)
    if L <= 0:
        raise ValueError("linha media de comprimento nulo")
    A = t * L

    # centroide
    sx = sum(_dist(a, b) * (a[0] + b[0]) / 2 for a, b in segs)
    sy = sum(_dist(a, b) * (a[1] + b[1]) / 2 for a, b in segs)
    xc, yc = sx / L, sy / L

    # coordenadas centroidais
    P = [(x - xc, y - yc) for x, y in pts]
    S = [(P[i], P[i + 1]) for i in range(len(P) - 1)]
    if fechado:
        S.append((P[-1], P[0]))

    def i2(f1, f2, ds):                      # integral de f^2 ao longo do trecho
        return ds * (f1 * f1 + f1 * f2 + f2 * f2) / 3

    def i11(f1, f2, g1, g2, ds):             # integral de f*g
        return ds * (2 * f1 * g1 + f1 * g2 + f2 * g1 + 2 * f2 * g2) / 6

    Ix = Iy = Ixy = 0.0
    for (x1, y1), (x2, y2) in S:
        ds = _dist((x1, y1), (x2, y2))
        Ix += t * i2(y1, y2, ds)
        Iy += t * i2(x1, x2, ds)
        Ixy += t * i11(x1, x2, y1, y2, ds)

    # eixos principais
    if abs(Ix - Iy) < 1e-12 and abs(Ixy) < 1e-12:
        theta = 0.0
    else:
        theta = 0.5 * math.atan2(2 * Ixy, Iy - Ix)
    med, dif = (Ix + Iy) / 2, (Ix - Iy) / 2
    raiz = math.hypot(dif, Ixy)
    I1, I2 = med + raiz, med - raiz

    # torcao uniforme
    if fechado:
        Am = abs(_area_poligono(P)) if len(P) > 2 else 0.0
        J = 4 * Am * Am / (L / t) if L else 0.0
    else:
        J = L * t ** 3 / 3

    # area setorial com polo no centroide
    om = _setorial(S, (0.0, 0.0))
    Iwx = Iwy = 0.0
    for k, ((x1, y1), (x2, y2)) in enumerate(S):
        ds = _dist((x1, y1), (x2, y2))
        w1, w2 = om[k]
        Iwx += t * i11(w1, w2, x1, x2, ds)
        Iwy += t * i11(w1, w2, y1, y2, ds)

    det = Ix * Iy - Ixy * Ixy
    if abs(det) < 1e-9 or fechado:
        dx = dy = 0.0
    else:
        dx = (-Iwx * Ixy + Iy * Iwy) / det
        dy = (Ixy * Iwy - Ix * Iwx) / det

    # area setorial com polo no centro de torcao, normalizada
    om2 = _setorial(S, (dx, dy))
    med_w = 0.0
    for k, (a, b) in enumerate(S):
        ds = _dist(a, b)
        w1, w2 = om2[k]
        med_w += t * ds * (w1 + w2) / 2
    med_w /= A
    Cw = 0.0
    for k, (a, b) in enumerate(S):
        ds = _dist(a, b)
        w1, w2 = om2[k][0] - med_w, om2[k][1] - med_w
        Cw += t * i2(w1, w2, ds)
    if fechado:
        Cw = 0.0

    xs = [p[0] for p in P]
    ys = [p[1] for p in P]
    ymax, ymin = max(ys), min(ys)
    xmax, xmin = max(xs), min(xs)
    return dict(
        L=L, A=A, xc=xc, yc=yc,
        Ix=Ix, Iy=Iy, Ixy=Ixy, I1=I1, I2=I2, theta=math.degrees(theta),
        rx=math.sqrt(Ix / A), ry=math.sqrt(Iy / A),
        Wx_sup=Ix / abs(ymax) if ymax else float("inf"),
        Wx_inf=Ix / abs(ymin) if ymin else float("inf"),
        Wy_dir=Iy / abs(xmax) if xmax else float("inf"),
        Wy_esq=Iy / abs(xmin) if xmin else float("inf"),
        Wx=Ix / max(abs(ymax), abs(ymin)), Wy=Iy / max(abs(xmax), abs(xmin)),
        J=J, Cw=Cw, xo=dx, yo=dy,
        ro=math.sqrt((Ix + Iy) / A + dx * dx + dy * dy),
        h=ymax - ymin, b=xmax - xmin,
        massa_m=A * 7.85e-3,          # kg/m: A[mm2] x 1000 mm x 7.85e-6 kg/mm3
    )


def _setorial(S, polo):
    """Area setorial acumulada, por trecho: [(w_inicio, w_fim), ...]."""
    out, w = [], 0.0
    for (x1, y1), (x2, y2) in S:
        ds = _dist((x1, y1), (x2, y2))
        ux, uy = (x2 - x1) / ds, (y2 - y1) / ds
        rho = (x1 - polo[0]) * uy - (y1 - polo[1]) * ux
        out.append((w, w + rho * ds))
        w += rho * ds
    return out


def _area_poligono(P):
    s = 0.0
    for i in range(len(P)):
        x1, y1 = P[i]
        x2, y2 = P[(i + 1) % len(P)]
        s += x1 * y2 - x2 * y1
    return s / 2


# ---------------------------------------------------------------- formas
def linha_media(forma: str, bw: float, bf: float, D: float, t: float,
                r: float = None, bf2: float = None) -> tuple[list, bool]:
    """Poligonal da linha media a partir das dimensoes EXTERNAS (NBR 6355).

    bw = alma, bf = aba, D = labio, t = espessura, r = raio interno de dobra.
    Devolve (pontos, fechado).
    """
    if r is None:
        r = _raio_padrao(t)
    rm = r + t / 2                    # raio da linha media
    a = bw - t                        # alma na linha media
    f = bf - t / 2                    # aba ate a borda externa da aba
    f2 = (bf2 - t / 2) if bf2 else f
    d = D - t / 2
    F = forma.upper()

    if F in ("U", "C"):               # canal sem labio
        pts = [(f, a / 2), (0, a / 2), (0, -a / 2), (f2, -a / 2)]
    elif F in ("UE", "CE", "C-LIP"):  # canal com labio (montante LSF)
        pts = [(f, a / 2 - d), (f, a / 2), (0, a / 2),
               (0, -a / 2), (f2, -a / 2), (f2, -a / 2 + d)]
    elif F == "Z":
        pts = [(-f, a / 2), (0, a / 2), (0, -a / 2), (f2, -a / 2)]
    elif F == "ZE":
        pts = [(-f, a / 2 - d), (-f, a / 2), (0, a / 2),
               (0, -a / 2), (f2, -a / 2), (f2, -a / 2 + d)]
    elif F in ("CARTOLA", "HAT", "OMEGA"):
        pts = [(-d, a / 2), (0, a / 2), (0, -a / 2),
               (f, -a / 2), (f, a / 2), (f + d, a / 2)]
        if F == "OMEGA":
            pts = [(-d, -a / 2), (0, -a / 2), (0, a / 2),
                   (f, a / 2), (f, -a / 2), (f + d, -a / 2)]
    elif F in ("L", "CANTONEIRA"):
        pts = [(0, a), (0, 0), (f, 0)]
    elif F == "SIGMA":
        m = a / 6
        pts = [(f, a / 2 - d), (f, a / 2), (0, a / 2), (0, m), (m, m),
               (m, -m), (0, -m), (0, -a / 2), (f, -a / 2), (f, -a / 2 + d)]
    elif F in ("RHS", "SHS", "BOX"):
        w = bf - t
        pts = [(-w / 2, a / 2), (w / 2, a / 2), (w / 2, -a / 2), (-w / 2, -a / 2)]
        return arredondar(pts + [pts[0]], rm)[:-1], True
    elif F == "CHS":
        R = (bw - t) / 2
        n = 48
        pts = [(R * math.cos(2 * math.pi * i / n), R * math.sin(2 * math.pi * i / n))
               for i in range(n)]
        return pts, True
    else:
        raise ValueError(f"forma '{forma}' nao conhecida")
    return arredondar(pts, rm), False


def _raio_padrao(t: float) -> float:
    """Raio interno minimo de dobra usual para aco formado a frio."""
    return 1.0 * t if t <= 1.0 else 1.5 * t


@dataclass(frozen=True)
class Perfil:
    cod: str
    forma: str
    bw: float
    bf: float
    D: float
    t: float
    familia: str = ""
    r: float = None

    def props(self) -> dict:
        pts, fech = linha_media(self.forma, self.bw, self.bf, self.D, self.t, self.r)
        return propriedades(pts, self.t, fech)

    def __str__(self):
        return self.cod


def _cod(forma, bw, bf, D, t):
    n = f"{forma} {bw:g}x{bf:g}"
    if D:
        n += f"x{D:g}"
    return n + f"x{t:.2f}".replace(".", ",")


# Serie comercial de LSF. As dimensoes seguem a NBR 6355 / NBR 15253; a
# disponibilidade real por fabricante e (H) ate o catalogo chegar (secao 129).
ESPESSURAS = (0.80, 0.95, 1.25, 1.55, 2.00, 2.25, 3.00)
_STUDS = ((90, 40), (140, 40), (200, 40), (250, 40), (75, 40))
_GUIAS = ((92, 38), (142, 38), (202, 38), (252, 38), (77, 38))


def labio_minimo(t: float) -> float:
    """Labio menor que 2 x (raio de dobra + espessura) nao se forma.

    A auditoria pegou isto no catalogo: com t = 3,00 mm o raio interno e 4,5 mm,
    e um labio de 12 mm seria consumido inteiro pelas duas dobras. Nao e questao
    de projeto — a perfiladeira nao produz.
    """
    return 2 * (_raio_padrao(t) + t)


def labio_serie(t: float) -> float:
    """Labio comercial compativel com a espessura."""
    m = labio_minimo(t)
    for d in (12, 15, 20, 25, 30):
        if d >= m:
            return d
    return math.ceil(m / 5) * 5


def catalogo() -> list[Perfil]:
    """Perfis disponiveis. Estrutura real; disponibilidade e (H)."""
    out = []
    for bw, bf in _STUDS:
        for t in ESPESSURAS:
            D = labio_serie(t)
            out.append(Perfil(_cod("Ue", bw, bf, D, t), "Ue", bw, bf, D, t, "montante"))
    for bw, bf in _GUIAS:
        for t in ESPESSURAS[:5]:
            out.append(Perfil(_cod("U", bw, bf, 0, t), "U", bw, bf, 0, t, "guia"))
    for bw, bf in ((140, 40), (200, 40), (250, 40)):
        for t in ESPESSURAS[2:]:
            D = labio_serie(t)
            out.append(Perfil(_cod("Ue", bw, bf, D, t), "Ue", bw, bf, D, t, "viga"))
    for bw, bf in ((50, 20), (75, 25)):
        for t in (0.80, 0.95, 1.25):
            D = max(6, labio_minimo(t))
            out.append(Perfil(_cod("Cartola", bw, bf, D, t), "Cartola", bw, bf, D, t,
                              "cartola"))
    vistos, unicos = set(), []
    for p in out:
        if (p.cod, p.familia) not in vistos:
            vistos.add((p.cod, p.familia))
            unicos.append(p)
    return unicos


# Funcao estrutural de cada peca em LSF (secao 09)
FAMILIAS_LSF = {
    "stud": "montante de parede, comprimido e fletido pelo vento",
    "track": "guia de piso e de topo, distribui e alinha os montantes",
    "joist": "viga de piso, vence o vao entre paredes portantes",
    "rafter": "caibro de cobertura, recebe telha, vento e manutencao",
    "header": "verga sobre abertura",
    "lintel": "verga externa, recebe tambem carga de fachada",
    "jamb": "montante de ombreira, ladeia a abertura",
    "king stud": "montante continuo de piso a topo ao lado da abertura",
    "jack stud": "montante curto que apoia a verga",
    "cripple stud": "montante curto acima ou abaixo da abertura",
    "blocking": "travamento entre montantes, corta flambagem distorcional",
    "bridging": "travamento de linha de vigas, distribui carga concentrada",
    "furring": "perfil de rebaixo para fixar placa",
    "resilient channel": "perfil resiliente, quebra a transmissao de ruido de impacto",
    "hat channel": "cartola, apoio de placa e de fachada ventilada",
    "strap": "fita de contraventamento, so trabalha a tracao",
    "truss member": "barra de trelica: banzo, montante ou diagonal",
}
