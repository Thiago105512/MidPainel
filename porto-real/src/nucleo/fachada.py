"""FACHADA — o que foi combinado, o que foi desenhado e o que tem estrutura.

Tres perguntas diferentes, e o projeto so respondia a segunda.

A fachada deste caso tem REGRAS declaradas desde R06, vindas do YAML do
proprietario: no maximo tres familias de material, vidro concentrado na face
posterior, nenhum ornamento sem funcao, e — a mais exigente — NENHUMA SUPERFICIE
QUE EXIJA PINTURA EM ALTURA. Regra declarada que ninguem confere e preferencia,
nao regra.

E os brises: cinco elementos, 16,8 m lineares de ripado, presentes no desenho e
no 3D, ausentes do modelo estrutural, do orcamento e da carga. Mesmo padrao do
vigamento ate R31 — o desenho convence, e a obra descobre.
"""
from __future__ import annotations

# (H) ripa de aluminio tubular 50 x 20 x 1,2 mm, que e a secao corrente de
# ripado de fachada. Massa linear de catalogo entra pelo contrato do
# fornecedor; aqui basta a ordem de grandeza para a carga existir.
RIPA = dict(b=50, h=20, t=1.2, massa_m=0.62,
            desc="tubular de aluminio 50 x 20 x 1,2 mm")
# travessa superior e inferior que recebem as ripas e transferem para o montante
TRAVESSA = dict(perfil="U 50x25x1,2 aluminio", massa_m=0.55)
# fixacao: a travessa vai no MONTANTE, nunca na placa. Placa cimenticia nao e
# elemento estrutural, e parafusar brise nela e arrancar a fachada no primeiro
# vento de 30 m/s.
PASSO_FIXACAO = 600


def faces(pj) -> list[dict]:
    """As quatro faces do volume, com area, vao e material.

    A face e derivada do envelope construido, e nao digitada: se um comodo
    crescer, a fachada cresce junto. Foi assim que R46 apareceu aqui sem que
    ninguem mexesse nesta funcao.
    """
    ambs = pj.TERREO + pj.SUPERIOR
    xs = [a.x for a in ambs] + [a.x + a.w for a in ambs]
    ys = [a.y for a in ambs] + [a.y + a.h for a in ambs]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    h_t = pj.PE_DIREITO
    h_s = pj.PE_DIREITO
    # extensao de cada face por pavimento: a do superior e menor, porque o
    # volume de cima nao cobre a planta toda
    def extensao(lista, face):
        seg = 0
        for a in lista:
            if face == "S":
                seg += a.w if abs(a.x - min(q.x for q in lista)) >= 0 and a.x == min(
                    q.x for q in lista) else 0
        return seg

    out = []
    # R64 — defeito 96: as larguras estavam TROCADAS. A face LESTE e a parede
    # em y = y0 (a testada esta em y = 0), que corre ao longo de X: sua
    # largura e x1 - x0 = 12,6 m, nao y1 - y0 = 19,2. O mesmo _face_do_vao
    # abaixo ja classificava certo (H em y0 -> L); so a extensao da parede
    # olhava o eixo errado. O total das quatro faces nao mudava — por isso
    # passou — mas a fracao de vidro por face, que decide brise e vidro,
    # estava atribuida a face errada.
    sx_t, sy_t = x1 - x0, y1 - y0
    sx_s = max((a.x + a.w) for a in pj.SUPERIOR) - min(a.x for a in pj.SUPERIOR)
    sy_s = max((a.y + a.h) for a in pj.SUPERIOR) - min(a.y for a in pj.SUPERIOR)
    for face, larg_t, larg_s in (("L", sx_t, sx_s), ("O", sx_t, sx_s),
                                 ("S", sy_t, sy_s), ("N", sy_t, sy_s)):
        area = (larg_t * h_t + larg_s * h_s) / 1e6
        vaos = [v for v in pj.VAOS if _face_do_vao(pj, v) == face]
        a_vao = sum(pj.ESQUADRIAS[t][0] * pj.ESQUADRIAS[t][1]
                    for t, *_ in vaos) / 1e6
        vidro = sum(pj.ESQUADRIAS[t][0] * pj.ESQUADRIAS[t][1]
                    for t, *_ in vaos
                    if not _opaco(pj.ESQUADRIAS[t][3])) / 1e6
        out.append(dict(
            face=face, nome={"L": "leste (testada)", "O": "oeste (fundo)",
                             "S": "sul", "N": "norte"}[face],
            largura_terreo=larg_t, largura_superior=larg_s,
            area_bruta=round(area, 1), area_vao=round(a_vao, 2),
            area_vidro=round(vidro, 2), n_vaos=len(vaos),
            area_liquida=round(area - a_vao, 1),
            frac_vidro=round(vidro / area, 4) if area else 0.0))
    return out


def _opaco(familia: str) -> bool:
    f = (familia or "").lower()
    # R64 — "portao de correr, aluminio ripado" passava por vidro porque tem
    # "correr" na descricao: 12,96 m2 de aluminio contados como vidro na face
    # leste. Ripado e portao sao opacos por definicao.
    if "ripado" in f or "portao" in f or "opaca" in f:
        return True
    return "porta" in f and "balcao" not in f and "vidro" not in f and "correr" not in f


def _face_do_vao(pj, v) -> str:
    """De que face este vao pertence, pela posicao no envelope."""
    tipo, x, y, ori, pav = v
    ambs = pj.TERREO + pj.SUPERIOR
    xs = [a.x for a in ambs] + [a.x + a.w for a in ambs]
    ys = [a.y for a in ambs] + [a.y + a.h for a in ambs]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    T = 200
    if ori == "V" and abs(x - x0) <= T:
        return "S"
    if ori == "V" and abs(x - x1) <= T:
        return "N"
    if ori == "H" and abs(y - y0) <= T:
        return "L"
    if ori == "H" and abs(y - y1) <= T:
        return "O"
    return "interno"


def brises(pj) -> dict:
    """Cada brise com ripa, travessa, fixacao e MASSA.

    Ate R48 os cinco brises existiam como retangulo no desenho e no 3D, e nao
    existiam como peca, como material nem como carga. O 3D desenhava altura
    1.500 e profundidade 120; o dado declarava profundidade 150. Duas fontes, e
    as duas em modulos de desenho.
    """
    itens = []
    for b in pj.BRISES:
        comp = b["w"]
        alt = b.get("altura", 1_500)
        passo = b["passo"]
        n_ripas = int(comp / passo) + 1
        m_ripa = n_ripas * alt / 1000.0
        m_trav = 2 * comp / 1000.0
        massa = m_ripa * RIPA["massa_m"] + m_trav * TRAVESSA["massa_m"]
        n_fix = 2 * (int(comp / PASSO_FIXACAO) + 1)
        movel = "movel" in b["tipo"].lower() or "MOVEL" in b["tipo"]
        itens.append(dict(
            cod=b["cod"], face=b["face"], tipo=b["tipo"], desc=b["desc"],
            comp=comp, altura=alt, prof=b["h"], passo=passo,
            n_ripas=n_ripas, ripa_m=round(m_ripa, 1),
            travessa_m=round(m_trav, 1), massa=round(massa, 1),
            fixacoes=n_fix, movel=movel,
            area=round(comp * alt / 1e6, 2),
            mecanismo=("guia superior e inferior, roldana e trava — item de "
                       "fornecedor, (H) ate a especificacao" if movel else "")))
    return dict(itens=itens, n=len(itens),
                comp_total=round(sum(i["comp"] for i in itens) / 1000.0, 1),
                ripa_m=round(sum(i["ripa_m"] for i in itens), 1),
                travessa_m=round(sum(i["travessa_m"] for i in itens), 1),
                massa=round(sum(i["massa"] for i in itens), 1),
                fixacoes=sum(i["fixacoes"] for i in itens),
                moveis=sum(1 for i in itens if i["movel"]),
                ripa=RIPA, travessa=TRAVESSA,
                nota="a travessa vai no MONTANTE, nunca na placa: placa "
                     "cimenticia nao e elemento estrutural, e parafusar brise "
                     "nela e arrancar a fachada no primeiro vento de 30 m/s")


def conferir(pj, r: dict) -> dict:
    """As regras de fachada foram declaradas. Elas estao sendo cumpridas?"""
    reg = pj.FACHADA_REGRAS
    fs = faces(pj)
    br = brises(pj)
    achados = []

    def ach(nivel, item, texto):
        achados.append(dict(nivel=nivel, item=item, texto=texto))

    # 1. familias de material
    n_fam = len(pj.FACHADA_MATERIAIS)
    ach("NOTA" if n_fam <= reg["familias_max"] else "ERRO", "familias",
        f"{n_fam} familias de material na fachada, contra o maximo de "
        f"{reg['familias_max']} declarado: "
        + "; ".join(m[0] for m in pj.FACHADA_MATERIAIS))

    # 2. vidro concentrado na face posterior
    posterior = max(fs, key=lambda f: f["area_vidro"])
    ach("NOTA" if posterior["face"] == "O" else "ATENCAO", "vidro",
        f"a face com mais vidro e a {posterior['nome']} "
        f"({posterior['area_vidro']} m2, {posterior['frac_vidro'] * 100:.1f} % "
        f"da face). A regra declarada e '{reg['vidro']}'")

    # 3. pintura em altura — a regra mais exigente, e a que o projeto quebrava
    pint = (getattr(pj, "PINTURA", {}) or {}).get("externa", "")
    fachada_pintada = "pintura" in pint.lower() or "acrilico" in pint.lower()
    onde = (getattr(pj, "PINTURA", {}) or {}).get("externa_onde", "")
    ach("NOTA" if (not fachada_pintada or onde) else "ERRO", "pintura em altura",
        f"a regra diz '{reg['manutencao']}'. O acabamento externo declarado e "
        f"'{pint}'"
        + (f", aplicado em: {onde}" if onde else
           " — e isso e pintura, sobre um volume de "
           f"{(pj.NIVEL_SUPERIOR + pj.PE_DIREITO) / 1000:.2f} m. Repintar a "
           f"cada cinco anos exige andaime, que e exatamente o que a regra "
           f"recusa"))

    # 4. estrutura para o brise.
    # O brise NAO tem peca de aco propria, e nao deve ter: ele se fixa nos
    # montantes que ja existem. O que precisa existir e (a) o material, para
    # que alguem compre, (b) a massa, para que a parede a receba, e (c) a
    # fixacao caindo em montante. A verificacao que falta e outra, e esta
    # declarada: arrancamento do parafuso sob vento em ripado, que depende do
    # coeficiente de forma de uma tela permeavel — dado de ensaio, (H).
    tem_material = br["ripa_m"] > 0 and br["massa"] > 0
    ach("NOTA" if tem_material or br["n"] == 0 else "ERRO", "brise",
        f"{br['n']} brises somando {br['comp_total']} m de fachada, "
        f"{br['ripa_m']} m de ripa e {br['massa']} kg pendurados na parede"
        + (". O ripado se fixa nos montantes que ja existem — nao leva peca de "
           "aco propria, e nao deveria levar. O que falta e a verificacao de "
           "arrancamento sob vento, que depende do coeficiente de forma de uma "
           "tela permeavel: ensaio, e portanto (H)" if tem_material else
           " — e nada disso existe no orcamento nem na carga"))

    # 5. a face que recebe brise tem montante para receber a travessa
    ach("NOTA", "fixacao", br["nota"] + f". Sao {br['fixacoes']} pontos de "
        f"fixacao a cada {PASSO_FIXACAO} mm")

    return dict(faces=fs, brises=br, achados=achados,
                n_achados=len(achados),
                erros=sum(1 for a in achados if a["nivel"] == "ERRO"),
                regras=reg,
                materiais=[dict(familia=m[0], onde=m[1])
                           for m in pj.FACHADA_MATERIAIS])


# ---------------------------------------------------------------------------
# PLATIBANDA — 550 mm de parede correndo todo o perimetro, sem estrutura
#
# TOPO_PLATIBANDA = 6.150 e o topo da parede do superior = 5.600. A diferenca —
# 550 mm — e uma parede que existe em todo o contorno da cobertura, aparece nas
# quatro fachadas, esconde a calha e recebe o rufo. Ela nao tinha montante, nao
# tinha guia, nao tinha fechamento e nao tinha massa.
#
# E o terceiro elemento com o mesmo padrao nesta revisao, depois do brise e da
# area externa: existe no desenho, existe no 3D, nao existe no modelo.
# ---------------------------------------------------------------------------
PLATIBANDA = dict(
    montante="Ue 90x40x12x0,95", guia="U 92x38x0,95",
    espac=600,
    fechamento_externo="placa cimenticia 10 mm, mesmo mineral da fachada",
    fechamento_interno="placa cimenticia 10 mm — face voltada para a calha, "
                       "exposta a chuva dos dois lados",
    massa_montante_m=1.407, massa_guia_m=1.229, massa_placa_m2=16.0,
)


def platibanda(pj) -> dict:
    """Estrutura e fechamento dos 550 mm que coroam o volume."""
    alt = pj.TOPO_PLATIBANDA - (pj.NIVEL_SUPERIOR + pj.PE_DIREITO)
    if alt <= 0:
        return dict(altura=0, comprimento_m=0.0, n=0, ok=True)
    ambs = pj.TERREO + pj.SUPERIOR
    xs = [a.x for a in ambs] + [a.x + a.w for a in ambs]
    ys = [a.y for a in ambs] + [a.y + a.h for a in ambs]
    # perimetro do envelope construido: a platibanda corre no contorno da
    # projecao, e nao na soma dos planos de cobertura (que conta borda
    # partilhada duas vezes, e esta declarado como conservador no seu proprio
    # levantamento)
    comp = 2 * ((max(xs) - min(xs)) + (max(ys) - min(ys))) / 1000.0
    n_mont = int(comp * 1000 / PLATIBANDA["espac"]) + 1
    m_mont = n_mont * alt / 1000.0
    m_guia = 2 * comp
    area_placa = 2 * comp * alt / 1000.0
    massa = (m_mont * PLATIBANDA["massa_montante_m"]
             + m_guia * PLATIBANDA["massa_guia_m"])
    return dict(
        altura=alt, comprimento_m=round(comp, 1), n_montantes=n_mont,
        montante_m=round(m_mont, 1), guia_m=round(m_guia, 1),
        placa_m2=round(area_placa, 1), massa_aco=round(massa, 1),
        massa_placa=round(area_placa * PLATIBANDA["massa_placa_m2"], 1),
        espac=PLATIBANDA["espac"], perfis=PLATIBANDA,
        obs="a face interna da platibanda tambem leva placa: ela olha para a "
            "calha e recebe chuva dos dois lados. Deixa-la aberta expoe o "
            "montante ao tempo, e montante galvanizado exposto e o primeiro "
            "ponto de corrosao de uma cobertura em LSF")
