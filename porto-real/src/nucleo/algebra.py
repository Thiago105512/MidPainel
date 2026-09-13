"""ALGEBRA — solucao de sistemas simetricos esparsos, sem dependencia externa.

O caderno inteiro se reproduz com `python3 build.py` e nada mais. Manter isso
custa escrever a fatoracao, e o metodo classico da analise estrutural e o
armazenamento em PERFIL (skyline): a matriz de rigidez de uma estrutura e
simetrica, positiva definida e quase vazia fora de uma faixa estreita em torno
da diagonal, e guardar so essa faixa transforma um problema cubico em um
problema praticamente linear.

Fatoracao LDL^T sem pivoteamento — legitima aqui porque a matriz de rigidez de
uma estrutura ESTAVEL e positiva definida. Se o pivo zera, a estrutura tem
mecanismo, e isso e informacao, nao falha numerica: a funcao diz qual grau de
liberdade soltou.
"""
from __future__ import annotations


class Mecanismo(Exception):
    """A estrutura tem movimento livre: pivo nulo na fatoracao."""

    def __init__(self, gl, msg=""):
        self.gl = gl
        super().__init__(msg or f"pivo nulo no grau de liberdade {gl}: "
                                f"a estrutura tem mecanismo nesse ponto")


class Skyline:
    """Matriz simetrica em armazenamento de perfil."""

    def __init__(self, n: int):
        self.n = n
        self.topo = list(range(n))     # primeira linha nao nula de cada coluna
        self._k: dict = {}

    def add(self, i: int, j: int, v: float) -> None:
        if v == 0.0:
            return
        if i > j:
            i, j = j, i
        self._k[(i, j)] = self._k.get((i, j), 0.0) + v
        if i < self.topo[j]:
            self.topo[j] = i

    def montar(self) -> None:
        """Fecha o perfil e passa para vetores contiguos."""
        self.ptr = [0] * (self.n + 1)
        for j in range(self.n):
            self.ptr[j + 1] = self.ptr[j] + (j - self.topo[j] + 1)
        self.a = [0.0] * self.ptr[self.n]
        for (i, j), v in self._k.items():
            self.a[self.ptr[j] + (i - self.topo[j])] = v
        self._k = None

    def _get(self, i, j):
        if i > j:
            i, j = j, i
        if i < self.topo[j]:
            return 0.0
        return self.a[self.ptr[j] + (i - self.topo[j])]

    def _set(self, i, j, v):
        if i > j:
            i, j = j, i
        self.a[self.ptr[j] + (i - self.topo[j])] = v

    def fatorar(self) -> None:
        """LDL^T no proprio perfil."""
        n = self.n
        d = [0.0] * n
        for j in range(n):
            t0 = self.topo[j]
            for i in range(t0, j):
                s = self._get(i, j)
                ti = self.topo[i]
                for k in range(max(t0, ti), i):
                    s -= self._get(k, i) * d[k] * self._get(k, j)
                self._set(i, j, s / d[i] if d[i] else 0.0)
            s = self._get(j, j)
            for k in range(t0, j):
                s -= self._get(k, j) ** 2 * d[k]
            if abs(s) < 1e-12 * max(1.0, abs(self._get(j, j))):
                raise Mecanismo(j)
            d[j] = s
            self._set(j, j, 1.0)
        self.d = d

    def resolver(self, f: list) -> list:
        """Resolve LDL^T x = f. Requer fatorar() antes."""
        n = self.n
        y = list(f)
        for j in range(n):                       # L y = f
            for i in range(self.topo[j], j):
                y[j] -= self._get(i, j) * y[i]
        for j in range(n):                       # D z = y
            y[j] /= self.d[j]
        for j in range(n - 1, -1, -1):           # L^T x = z
            for i in range(self.topo[j], j):
                y[i] -= self._get(i, j) * y[j]
        return y


def produto(k: Skyline, x: list) -> list:
    """K.x, para conferir o residuo da solucao."""
    n = k.n
    out = [0.0] * n
    for j in range(n):
        for i in range(k.topo[j], j + 1):
            v = k._get(i, j)
            if v:
                out[i] += v * x[j]
                if i != j:
                    out[j] += v * x[i]
    return out
