"""QR Code (ISO/IEC 18004) em Python puro, modo byte, versões 1 a 40, saída em SVG.

Usado para o Pix copia e cola. Implementa: escolha da menor versão em que os dados cabem, Reed–Solomon em GF(256)
(polinômio 0x11D), intercalação dos blocos, padrões de função (localizadores, alinhamento, sincronismo, módulo escuro),
informação de formato (BCH 15,5) e de versão (BCH 18,6), as 8 máscaras e a escolha da máscara pelas 4 regras de
penalidade da norma.
"""

NIVEIS = {"L": 1, "M": 0, "Q": 3, "H": 2}  # bits do nível de correção na informação de formato

# Códigos de correção por bloco e número de blocos, por nível (L, M, Q, H) e versão (índice 0 não usado).
_ECC_POR_BLOCO = {
    "L": (-1, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28, 28, 28, 30, 30, 26, 28,
          30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    "M": (-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28, 28,
          28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28),
    "Q": (-1, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30, 28, 30, 30, 30, 30, 28,
          30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
    "H": (-1, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28, 30, 24, 30, 30, 30, 30,
          30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30),
}
_BLOCOS = {
    "L": (-1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8, 8, 9, 9, 10, 12, 12, 12, 13, 14, 15, 16, 17,
          18, 19, 19, 20, 21, 22, 24, 25),
    "M": (-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21, 23, 25, 26, 28, 29,
          31, 33, 35, 37, 38, 40, 43, 45, 47, 49),
    "Q": (-1, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8, 8, 10, 12, 16, 12, 17, 16, 18, 21, 20, 23, 23, 25, 27, 29, 34, 34, 35, 38,
          40, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68),
    "H": (-1, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25, 25, 34, 30, 32, 35, 37, 40, 42, 45,
          48, 51, 54, 57, 60, 63, 66, 70, 74, 77, 81),
}

# ---------------------------------------------------------------- GF(256) e Reed–Solomon

_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]
del _x, _i


def _mult(a, b):
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def polinomio_gerador(grau):
    """Coeficientes de (x − α⁰)(x − α¹)…(x − α^(grau−1)), do termo de maior grau ao independente (líder = 1)."""
    poli = [1]
    for i in range(grau):
        novo = poli + [0]
        for j, coef in enumerate(poli):
            novo[j + 1] ^= _mult(coef, _EXP[i])
        poli = novo
    return poli


def reed_solomon(dados, grau):
    """Resto da divisão de dados·x^grau pelo polinômio gerador: os `grau` bytes de correção."""
    gerador = polinomio_gerador(grau)[1:]
    resto = [0] * grau
    for byte in dados:
        fator = byte ^ resto[0]
        resto = resto[1:] + [0]
        if fator:
            for i, coef in enumerate(gerador):
                resto[i] ^= _mult(coef, fator)
    return resto


# ---------------------------------------------------------------- capacidade e estrutura

def lado(versao):
    return versao * 4 + 17


def posicoes_alinhamento(versao):
    if versao == 1:
        return []
    n = versao // 7 + 2
    passo = 26 if versao == 32 else (versao * 4 + n * 2 + 1) // (n * 2 - 2) * 2
    return [6] + sorted(lado(versao) - 7 - i * passo for i in range(n - 1))


def _modulos_de_dados(versao):
    """Número de módulos disponíveis para dados + correção (inclui os bits de resto)."""
    total = (16 * versao + 128) * versao + 64
    if versao >= 2:
        n = versao // 7 + 2
        total -= (25 * n - 10) * n - 55
        if versao >= 7:
            total -= 36
    return total


def capacidade_bytes(versao, nivel):
    """Codewords de dados (bytes) da versão/nível."""
    return _modulos_de_dados(versao) // 8 - _ECC_POR_BLOCO[nivel][versao] * _BLOCOS[nivel][versao]


def _bits_contagem(versao):
    return 8 if versao <= 9 else 16


def escolher_versao(tamanho, nivel="M"):
    for versao in range(1, 41):
        bits = 4 + _bits_contagem(versao) + 8 * tamanho
        if bits <= capacidade_bytes(versao, nivel) * 8:
            return versao
    raise ValueError("Dados grandes demais para um QR Code.")


def _codewords(dados, versao, nivel):
    """Monta o fluxo de bits (modo byte), completa e intercala blocos de dados e de correção."""
    capacidade = capacidade_bytes(versao, nivel)
    bits = []

    def poe(valor, n):
        bits.extend((valor >> i) & 1 for i in range(n - 1, -1, -1))

    poe(0b0100, 4)
    poe(len(dados), _bits_contagem(versao))
    for byte in dados:
        poe(byte, 8)
    if len(bits) > capacidade * 8:
        raise ValueError("Dados não cabem nesta versão.")
    bits.extend([0] * min(4, capacidade * 8 - len(bits)))  # terminador
    bits.extend([0] * (-len(bits) % 8))
    palavras = [int("".join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
    enchimento = (0xEC, 0x11)
    i = 0
    while len(palavras) < capacidade:
        palavras.append(enchimento[i % 2])
        i += 1

    n_blocos = _BLOCOS[nivel][versao]
    ecc = _ECC_POR_BLOCO[nivel][versao]
    total = _modulos_de_dados(versao) // 8
    n_curtos = n_blocos - total % n_blocos
    tam_curto = total // n_blocos  # dados + correção de um bloco curto
    blocos, correcoes, k = [], [], 0
    for b in range(n_blocos):
        n_dados = tam_curto - ecc + (0 if b < n_curtos else 1)
        bloco = palavras[k:k + n_dados]
        k += n_dados
        blocos.append(bloco)
        correcoes.append(reed_solomon(bloco, ecc))
    saida = []
    for i in range(max(len(b) for b in blocos)):
        saida.extend(b[i] for b in blocos if i < len(b))
    for i in range(ecc):
        saida.extend(c[i] for c in correcoes)
    return saida


# ---------------------------------------------------------------- matriz

def _bits_formato(nivel, mascara):
    dados = NIVEIS[nivel] << 3 | mascara
    resto = dados
    for _ in range(10):
        resto = (resto << 1) ^ ((resto >> 9) * 0x537)
    return (dados << 10 | resto) ^ 0x5412


def _bits_versao(versao):
    resto = versao
    for _ in range(12):
        resto = (resto << 1) ^ ((resto >> 11) * 0x1F25)
    return versao << 12 | resto


class _Matriz:
    def __init__(self, versao):
        self.versao = versao
        self.n = lado(versao)
        self.m = [[0] * self.n for _ in range(self.n)]  # m[linha][coluna]; 1 = escuro
        self.funcao = [[False] * self.n for _ in range(self.n)]
        self._padroes_de_funcao()

    def poe(self, x, y, escuro):
        self.m[y][x] = 1 if escuro else 0
        self.funcao[y][x] = True

    def _padroes_de_funcao(self):
        n = self.n
        for i in range(n):  # sincronismo
            self.poe(6, i, i % 2 == 0)
            self.poe(i, 6, i % 2 == 0)
        for cx, cy in ((3, 3), (n - 4, 3), (3, n - 4)):  # localizadores com separador
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < n and 0 <= y < n:
                        self.poe(x, y, max(abs(dx), abs(dy)) not in (2, 4))
        pos = posicoes_alinhamento(self.versao)
        ultimo = len(pos) - 1
        for i, cy in enumerate(pos):
            for j, cx in enumerate(pos):
                if (i, j) in ((0, 0), (0, ultimo), (ultimo, 0)):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self.poe(cx + dx, cy + dy, max(abs(dx), abs(dy)) != 1)
        # reserva as áreas de formato e de versão, claras até a máscara ser escolhida
        self.formato(0, "M", reservar=True)
        self.info_versao(reservar=True)

    def info_versao(self, reservar=False):
        if self.versao < 7:
            return
        n = self.n
        bits = 0 if reservar else _bits_versao(self.versao)
        for i in range(18):
            bit = (bits >> i) & 1
            a, b = n - 11 + i % 3, i // 3
            self.poe(a, b, bit)
            self.poe(b, a, bit)

    def formato(self, mascara, nivel, reservar=False):
        n = self.n
        bits = 0 if reservar else _bits_formato(nivel, mascara)
        bit = [(bits >> i) & 1 for i in range(15)]
        for i in range(6):
            self.poe(8, i, bit[i])
        self.poe(8, 7, bit[6])
        self.poe(8, 8, bit[7])
        self.poe(7, 8, bit[8])
        for i in range(9, 15):
            self.poe(14 - i, 8, bit[i])
        for i in range(8):
            self.poe(n - 1 - i, 8, bit[i])
        for i in range(8, 15):
            self.poe(8, n - 15 + i, bit[i])
        self.poe(8, n - 8, 0 if reservar else 1)  # módulo escuro

    def dados(self, palavras):
        n = self.n
        i, total = 0, len(palavras) * 8
        direita = n - 1
        while direita >= 1:
            if direita == 6:
                direita = 5
            for vert in range(n):
                for k in range(2):
                    x = direita - k
                    subindo = ((direita + 1) & 2) == 0
                    y = n - 1 - vert if subindo else vert
                    if not self.funcao[y][x]:
                        if i < total:
                            self.m[y][x] = (palavras[i >> 3] >> (7 - (i & 7))) & 1
                            i += 1
                        # o resto (bits de resto) fica 0
            direita -= 2

    def aplicar_mascara(self, mascara):
        f = _MASCARAS[mascara]
        for y in range(self.n):
            linha, func = self.m[y], self.funcao[y]
            for x in range(self.n):
                if not func[x] and f(y, x):
                    linha[x] ^= 1


_MASCARAS = (
    lambda i, j: (i + j) % 2 == 0,
    lambda i, j: i % 2 == 0,
    lambda i, j: j % 3 == 0,
    lambda i, j: (i + j) % 3 == 0,
    lambda i, j: (i // 2 + j // 3) % 2 == 0,
    lambda i, j: (i * j) % 2 + (i * j) % 3 == 0,
    lambda i, j: ((i * j) % 2 + (i * j) % 3) % 2 == 0,
    lambda i, j: ((i + j) % 2 + (i * j) % 3) % 2 == 0,
)

_PADRAO_N3 = (1, 0, 1, 1, 1, 0, 1)


def _n3(linha):
    """N3: cada padrão escuro-claro-escuro×3-claro-escuro (1:1:3:1:1) com 4 módulos claros antes ou depois conta 40.

    A zona de silêncio fora do símbolo é clara. Um padrão já contado não divide módulos com o seguinte.
    """
    n = len(linha)
    pontos, k = 0, 0
    while k <= n - 7:
        if linha[k:k + 7] != _PADRAO_N3:
            k += 1
            continue
        if not any(linha[max(k - 4, 0):k]) or not any(linha[k + 7:k + 11]):
            pontos += 40
            k += 7
        else:
            k += 4
    return pontos


def penalidade(m):
    """Pontuação da norma (N1 a N4) de uma matriz já mascarada; quanto menor, melhor.

    Avaliada como no segno (e no ISO/IEC 18004:2015, 7.8.3): antes de gravar as informações de formato e de versão,
    cujas áreas contam como claras.
    """
    n = len(m)
    pontos = 0
    colunas = [tuple(m[y][x] for y in range(n)) for x in range(n)]
    for linha in list(map(tuple, m)) + colunas:
        # N1: sequências de 5 ou mais módulos da mesma cor
        seq = 1
        for k in range(1, n):
            if linha[k] == linha[k - 1]:
                seq += 1
            else:
                if seq >= 5:
                    pontos += seq - 2
                seq = 1
        if seq >= 5:
            pontos += seq - 2
        pontos += _n3(linha)
    # N2: blocos 2×2 da mesma cor
    for y in range(n - 1):
        a, b = m[y], m[y + 1]
        for x in range(n - 1):
            if a[x] == a[x + 1] == b[x] == b[x + 1]:
                pontos += 3
    # N4: proporção de módulos escuros, a cada 5% de distância de 50%
    escuros = sum(map(sum, m))
    total = n * n
    pontos += 10 * (abs(escuros * 20 - total * 10) // total)
    return pontos


def gerar(dados, nivel="M", versao=None, mascara=None):
    """Matriz do QR Code (lista de linhas com 0/1, sem a margem). `dados`: bytes ou texto (UTF-8)."""
    if isinstance(dados, str):
        dados = dados.encode("utf-8")
    nivel = nivel.upper()
    if nivel not in NIVEIS:
        raise ValueError("Nível de correção inválido.")
    versao = versao or escolher_versao(len(dados), nivel)
    if not 1 <= versao <= 40:
        raise ValueError("Versão inválida.")
    palavras = _codewords(bytes(dados), versao, nivel)
    base = _Matriz(versao)
    base.dados(palavras)
    candidatas = range(8) if mascara is None else (mascara,)
    melhor = None
    for k in candidatas:
        tentativa = _Matriz.__new__(_Matriz)
        tentativa.versao, tentativa.n = base.versao, base.n
        tentativa.m = [linha[:] for linha in base.m]
        tentativa.funcao = base.funcao
        tentativa.aplicar_mascara(k)
        pontos = penalidade(tentativa.m) if mascara is None else 0
        if melhor is None or pontos < melhor[0]:
            melhor = (pontos, k, tentativa)
    _, k, escolhida = melhor
    escolhida.formato(k, nivel)
    escolhida.info_versao()
    return escolhida.m


def svg(matriz, margem=4, modulo=8):
    """SVG com fundo branco e `margem` módulos de zona de silêncio; um único <path> com as faixas escuras."""
    n = len(matriz)
    total = n + 2 * margem
    trechos = []
    for y, linha in enumerate(matriz):
        x = 0
        while x < n:
            if linha[x]:
                inicio = x
                while x < n and linha[x]:
                    x += 1
                trechos.append(f"M{inicio + margem},{y + margem}h{x - inicio}v1h-{x - inicio}z")
            else:
                x += 1
    px = total * modulo
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {total}" width="{px}" height="{px}" '
            f'shape-rendering="crispEdges" role="img" aria-label="QR Code">'
            f'<rect width="{total}" height="{total}" fill="#fff"/>'
            f'<path fill="#000" d="{"".join(trechos)}"/></svg>')
