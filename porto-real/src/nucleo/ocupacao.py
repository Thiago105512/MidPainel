"""OCUPACAO — espaco morto deixa de ser impressao e vira medida.

"Sem espacos mortos" e um pedido que todo projeto recebe e quase nenhum
verifica, porque espaco morto nao tem cota: ele e o que sobra depois que todo
o resto foi cotado. Este modulo o transforma em tres perguntas que o modelo
consegue responder sozinho.

1. VAZIO GEOMETRICO — ha area dentro do envelope que nao pertence a ambiente
   nenhum? Rasteriza o pavimento, inunda a partir de fora e chama de vazio
   interno o que a inundacao nao alcanca. Hoje devolve zero, e devolver zero
   e o ponto: a conferencia fica instalada e acusa no dia em que alguem mover
   uma parede e abrir um bolsao sem nome.

2. CIRCULACAO EXCEDENTE — corredor mais largo que o necessario e espaco morto
   em pe. A NBR 9050 pede 0,90 m de passagem e 1,20 m de conforto; acima de
   1,50 m um corredor so se justifica se guardar alguma coisa. A medida aqui
   nao e "o corredor e largo", e "quantos m2 de largura excedente existem e o
   que ha dentro deles".

3. AMBIENTE SEM O QUE SEU NOME PROMETE — o caso que este modulo encontrou na
   estreia: "HALL E ROUPARIA", 11,52 m2, zero armarios no modelo. A rouparia
   existia no nome do comodo e em lugar nenhum mais. E o mesmo defeito que o
   projeto ja catalogou tres vezes — existe no desenho, nao existe no modelo —
   so que desta vez o desenho era uma palavra.

O QUE ESTE MODULO NAO FAZ. Nao julga se um quarto de 25 m2 e grande demais:
area de dormitorio e programa do proprietario, nao norma. Ele mede o que
sobra sem dono, nao o que tem dono e e generoso.
"""
from __future__ import annotations

from collections import deque

GRID = 100                   # mm, resolucao do raster
PASSAGEM_MIN = 900           # NBR 9050 — passagem
PASSAGEM_CONFORTO = 1_200    # NBR 9050 — duas pessoas cruzando
# Largura acima da qual o corredor precisa justificar-se. Nao e um numero de
# gosto: e folha de porta + passagem. Onde ha duas ou mais portas dando para a
# circulacao, uma folha de 900 mm abre dentro dela e ainda precisa sobrar a
# passagem de 900 mm da NBR 9050 — 1.800 mm. Onde ha uma porta so, a folha
# nunca disputa com quem passa, e 1.500 mm bastam.
LARGURA_SEM_USO = 1_500
LARGURA_SEM_USO_MULTIPORTA = 1_800
PROF_ARMARIO = 600
# Comodos de circulacao que NAO sao corredor: o core tem escada dentro.
CIRCULACAO_ESTRUTURADA = ("T-COR",)


def _por_pav(pj) -> dict:
    return {"T": list(pj.TERREO), "S": list(pj.SUPERIOR)}


# ------------------------------------------------------- 1. vazio geometrico
def vazios(pj) -> list[dict]:
    """Bolsoes de area dentro do envelope que nao pertencem a ambiente nenhum."""
    out = []
    for pav, L in _por_pav(pj).items():
        if not L:
            continue
        x0 = min(a.x for a in L); x1 = max(a.x + a.w for a in L)
        y0 = min(a.y for a in L); y1 = max(a.y + a.h for a in L)
        nx, ny = (x1 - x0) // GRID, (y1 - y0) // GRID
        occ = [[False] * ny for _ in range(nx)]
        for a in L:
            for i in range((a.x - x0) // GRID, (a.x + a.w - x0) // GRID):
                for j in range((a.y - y0) // GRID, (a.y + a.h - y0) // GRID):
                    if 0 <= i < nx and 0 <= j < ny:
                        occ[i][j] = True
        fora = [[False] * ny for _ in range(nx)]
        q = deque()
        for i in range(nx):
            for j in (0, ny - 1):
                if not occ[i][j] and not fora[i][j]:
                    fora[i][j] = True; q.append((i, j))
        for j in range(ny):
            for i in (0, nx - 1):
                if not occ[i][j] and not fora[i][j]:
                    fora[i][j] = True; q.append((i, j))
        while q:
            i, j = q.popleft()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = i + di, j + dj
                if 0 <= a < nx and 0 <= b < ny and not occ[a][b] and not fora[a][b]:
                    fora[a][b] = True; q.append((a, b))
        visto = [[False] * ny for _ in range(nx)]
        for i in range(nx):
            for j in range(ny):
                if occ[i][j] or fora[i][j] or visto[i][j]:
                    continue
                q = deque([(i, j)]); visto[i][j] = True; cel = []
                while q:
                    p, r = q.popleft(); cel.append((p, r))
                    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        a, b = p + di, r + dj
                        if (0 <= a < nx and 0 <= b < ny and not occ[a][b]
                                and not fora[a][b] and not visto[a][b]):
                            visto[a][b] = True; q.append((a, b))
                xs = [c[0] for c in cel]; ys = [c[1] for c in cel]
                w = (max(xs) - min(xs) + 1) * GRID
                h = (max(ys) - min(ys) + 1) * GRID
                out.append(dict(pav=pav, area=round(len(cel) * GRID * GRID / 1e6, 2),
                                x=x0 + min(xs) * GRID, y=y0 + min(ys) * GRID,
                                w=w, h=h, menor=min(w, h)))
    return out


# ------------------------------------------------- 2. circulacao e excedente
def circulacao(pj) -> dict:
    """Quanto da area construida e so passagem, e quanto disso e excedente."""
    import especificacao as _ep  # so para a categoria; nao ha dado aqui
    cat = _ep.CATEGORIA
    total = sum(a.w * a.h for a in pj.TERREO + pj.SUPERIOR) / 1e6
    itens = []
    for a in pj.TERREO + pj.SUPERIOR:
        if cat.get(a.cod) != "circulacao":
            continue
        larg, comp = min(a.w, a.h), max(a.w, a.h)
        estruturada = a.cod in CIRCULACAO_ESTRUTURADA
        # A largura que o armario ocupa NAO e excedente: ela virou guarda. O
        # que sobra depois dele e que continua sendo passagem — e e essa a
        # largura que a conta precisa usar, senao a conferencia reprova para
        # sempre o corredor que ela propria mandou aproveitar.
        # Profundidade do armario e sempre a MENOR dimensao dele: armario e
        # mais comprido que fundo. Deduzir a dimensao errada foi o primeiro
        # erro desta conferencia, e ela reprovou o hall por "0 mm de passagem".
        guardado = max((min(g["w"], g["h"]) for g in _armarios_de(pj, a.cod)),
                       default=0)
        livre = larg - guardado
        portas = _portas_de(pj, a)
        limite = (LARGURA_SEM_USO_MULTIPORTA if portas >= 2 else LARGURA_SEM_USO)
        excedente = 0.0 if estruturada else max(livre - limite, 0) * comp / 1e6
        # A mesma largura e piso e teto. Onde duas portas ou mais abrem para a
        # circulacao, uma folha de 900 mm ocupa metade dela e a NBR 9050 ainda
        # quer 900 mm de passagem ao lado: 1.800 mm e o MINIMO e tambem o ponto
        # a partir do qual sobra. Abaixo disso a circulacao estrangula; acima,
        # desperdica. Foi esta conta que reprovou o armario que esta mesma
        # conferencia havia sugerido para o hall do terreo.
        if livre < (limite if portas >= 2 else PASSAGEM_MIN) and not estruturada:
            excedente = -1.0
        itens.append(dict(cod=a.cod, nome=a.nome, area=round(a.w * a.h / 1e6, 2),
                          largura=larg, guardado=guardado, livre=livre,
                          comprimento=comp, estruturada=estruturada,
                          portas=portas, limite=limite,
                          excedente=round(excedente, 2),
                          cabe_armario=(not estruturada
                                        and livre - PROF_ARMARIO >= PASSAGEM_CONFORTO)))
    area = sum(i["area"] for i in itens)
    return dict(itens=itens, area=round(area, 2), total=round(total, 2),
                taxa=round(area / total, 4),
                excedente=round(sum(i["excedente"] for i in itens), 2))


# --------------------------------------- 3. o que o nome promete e nao existe
# Palavra no nome do ambiente -> o que o modelo precisa conter para a palavra
# ser verdadeira. A chave e a promessa; o valor, a prova.
PROMESSAS = {
    "ROUPARIA": ("armario", "ARMARIOS"),
    "CLOSET": ("armario", "ARMARIOS"),
    "DESPENSA": ("armario", "ARMARIOS"),
    "ROUPEIRO": ("armario", "ARMARIOS"),
}
# Todo dormitorio guarda roupa em algum lugar: armario proprio ou closet.
DORMITORIO = ("intimo",)


def _armarios_de(pj, cod) -> list:
    """Armarios DENTRO do ambiente — os que ocupam largura dele."""
    return [a for a in pj.ARMARIOS if a.get("amb") == cod]


def _guarda_de(pj, cod) -> list:
    """Armarios que SERVEM o ambiente, dentro dele ou em outro declarado.

    Guarda fora do comodo so conta quando o projeto DECLARA que serve — nunca
    por proximidade nem por semelhanca de nome. Deduzir do nome seria repetir,
    do lado da conferencia, o mesmo erro que ela existe para achar.
    """
    return [a for a in pj.ARMARIOS
            if a.get("amb") == cod or a.get("serve") == cod]


def _portas_de(pj, a) -> int:
    """Quantas portas dao para este ambiente — define a largura que ele precisa."""
    n = 0
    for tipo, x, y, ori, pav in pj.VAOS:
        if pav != a.pav or not tipo.startswith("P"):
            continue
        if (a.x - 90 <= x <= a.x + a.w + 90 and a.y - 90 <= y <= a.y + a.h + 90):
            n += 1
    return n


def _subdiv_de(pj, cod) -> list:
    return [d for d in pj.SUBDIVISOES if d["pai"] == cod]


def promessas(pj) -> list[dict]:
    """Ambiente cujo NOME promete guarda e cujo modelo nao entrega."""
    falhas = []
    for a in pj.TERREO + pj.SUPERIOR:
        nome = a.nome.upper()
        for palavra, (_o, _f) in PROMESSAS.items():
            if palavra not in nome:
                continue
            tem = _armarios_de(pj, a.cod) or [d for d in _subdiv_de(pj, a.cod)
                                              if palavra in d["nome"].upper()]
            if not tem:
                falhas.append(dict(cod=a.cod, nome=a.nome, promessa=palavra,
                                   erro=f"o nome do ambiente diz {palavra}, e nao ha "
                                        f"armario nem subdivisao correspondente no modelo"))
    return falhas


def guarda(pj) -> list[dict]:
    """Dormitorio sem lugar declarado para guardar roupa."""
    import especificacao as _ep
    cat = _ep.CATEGORIA
    falhas = []
    for a in pj.TERREO + pj.SUPERIOR:
        if cat.get(a.cod) not in DORMITORIO:
            continue
        if "ALCOVA" in a.nome.upper():
            continue
        closets = [d for d in _subdiv_de(pj, a.cod) if "CLOSET" in d["nome"].upper()]
        if closets or _guarda_de(pj, a.cod):
            continue
        falhas.append(dict(cod=a.cod, nome=a.nome, area=round(a.w * a.h / 1e6, 2),
                           erro="dormitorio sem closet e sem armario no modelo"))
    return falhas


def conferir(pj) -> list[dict]:
    out = []
    for v in vazios(pj):
        if v["menor"] > 150:      # ate 150 mm e espessura de parede
            out.append(dict(classe="vazio", item=f"{v['pav']} ({v['x']},{v['y']})",
                            erro=f"bolsao de {v['area']:.2f} m2 sem ambiente, "
                                 f"{v['w']} x {v['h']} mm"))
    c = circulacao(pj)
    if c["taxa"] > 0.15:
        out.append(dict(classe="circulacao",
                        erro=f"circulacao e {c['taxa'] * 100:.1f} % da area construida "
                             f"(referencia: ate 15 %)"))
    for i in c["itens"]:
        if i["excedente"] < 0:
            out.append(dict(classe="circulacao", item=i["cod"],
                            erro=f"{i['nome']}: restam {i['livre']} mm de passagem, "
                                 f"abaixo dos {i['limite'] if i['portas'] >= 2 else PASSAGEM_MIN} mm "
                                 f"que {i['portas']} porta(s) exigem "
                                 f"(folha de 900 mm mais a passagem da NBR 9050)"))
            continue
        if i["excedente"] > 1.0:
            out.append(dict(classe="circulacao", item=i["cod"],
                            erro=f"{i['excedente']:.2f} m2 de largura excedente em "
                                 f"{i['nome']}: {i['largura']} mm de largura contra "
                                 f"{i['limite']} mm que dispensam justificativa "
                                 f"({i['portas']} portas)"
                                 + (" — cabe armario" if i["cabe_armario"] else "")))
    for f in promessas(pj):
        out.append(dict(classe="promessa", item=f["cod"], erro=f["erro"]))
    for f in guarda(pj):
        out.append(dict(classe="guarda", item=f["cod"], erro=f["erro"]))
    return out
