"""PAINEL — a parede vira produto de fabrica (secoes 05, 23, 24, 25, 26).

Ate R18 uma parede era uma linha com espessura: o suficiente para desenhar a
planta, insuficiente para fabricar qualquer coisa. Aqui ela vira um PAINEL, com
todas as pecas que a compoem, cada uma com codigo, perfil, comprimento e
posicao — o que a perfiladeira corta e o que o montador parafusa.

As regras nao sao arbitrarias, e cada uma existe por um motivo construtivo:

  modulacao      o montante segue a malha porque a PLACA segue a malha; furar
                 placa fora de montante e o defeito mais comum de LSF;
  king stud      o montante continuo ao lado da abertura leva a carga da verga
                 ate a guia inferior sem interrupcao;
  jack stud      o montante curto SOB a verga e quem realmente apoia — o king
                 sozinho nao apoia nada, so amarra;
  cripple        acima da verga e abaixo do peitoril, na MESMA modulacao, para
                 que a placa continue encontrando montante;
  blocking       corta o comprimento de flambagem distorcional do montante. Na
                 E6 isso apareceu como +216 % de resistencia.

O painel se parte quando ultrapassa o que cabe no caminhao ou o que o guindaste
levanta — e a emenda nao cai em abertura, porque emenda em abertura e a junta
que trinca.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import nucleo.perfis as pf
import nucleo.verificacao as vr


@dataclass
class Config:
    modulacao: int = 600              # mm entre eixos de montante
    altura: int = 2_600               # mm, piso a forro
    perfil_stud: str = "Ue 90x40x12x0,95"
    perfil_track: str = "U 92x38x0,95"
    perfil_verga: str = "Ue 90x40x12x1,25"
    comp_max: int = 3_600             # mm, limite de transporte e manuseio
    peso_max: float = 120.0           # kg, limite de icamento manual (4 pessoas)
    blocking_a_cada: int = 1_300      # mm de altura
    folga_abertura: int = 10          # mm de folga de vao em cada lado


@dataclass
class Peca:
    cod: str
    familia: str          # stud, track, king stud, jack stud, cripple, header...
    perfil: str
    comp: int             # mm
    x: int                # posicao no painel, mm do canto esquerdo
    z: int                # altura da base da peca, mm
    vertical: bool = True
    obs: str = ""

    def massa(self, cat: dict) -> float:
        return cat[self.perfil] * self.comp / 1000.0


@dataclass
class Painel:
    cod: str
    parede: str
    x: int                # posicao no pavimento
    y: int
    comp: int
    altura: int
    esp: int
    externa: bool
    pecas: list = field(default_factory=list)
    aberturas: list = field(default_factory=list)
    obs: str = ""

    def por_familia(self) -> dict:
        d = {}
        for p in self.pecas:
            d[p.familia] = d.get(p.familia, 0) + 1
        return d

    def massa(self, cat: dict) -> float:
        return sum(p.massa(cat) for p in self.pecas)

    def comprimento_total(self) -> int:
        return sum(p.comp for p in self.pecas)


def _catalogo_massa() -> dict:
    return {p.cod: p.props()["massa_m"] for p in pf.catalogo()}


def _vaos_da_parede(par, vaos) -> list:
    """Aberturas que pertencem a esta parede, em coordenada local do painel."""
    out = []
    for v in vaos:
        if par.horizontal:
            if v["ori"] != "H" or abs(v["y"] - par.y1) > 1:
                continue
            a, b = min(par.x1, par.x2), max(par.x1, par.x2)
            if not (a <= v["x"] <= b):
                continue
            local = v["x"] - a
        else:
            if v["ori"] != "V" or abs(v["x"] - par.x1) > 1:
                continue
            a, b = min(par.y1, par.y2), max(par.y1, par.y2)
            if not (a <= v["y"] <= b):
                continue
            local = v["y"] - a
        out.append(dict(tipo=v["tipo"], centro=int(local), larg=v["larg"],
                        alt=v["alt"], peitoril=v["peitoril"], desc=v.get("desc", "")))
    return sorted(out, key=lambda d: d["centro"])


def _quebrar(comp: int, aberturas: list, cfg: Config) -> tuple[list, str]:
    """Onde partir a parede, e por que as vezes nao da para partir.

    A primeira versao movia o corte para fora da abertura e nao reconferia o
    limite de transporte: numa parede de 6.000 mm com um portao de 5.400, o
    corte fugia para 600 mm e sobrava um painel de 5.400 — acima do caminhao e
    do guindaste, sem ninguem avisar.

    Agora o corte e escolhido entre as posicoes ADMISSIVEIS (multiplo da
    modulacao, fora de qualquer abertura com folga), tomando sempre a mais
    distante que ainda respeite o comprimento maximo. Quando nao existe posicao
    admissivel, a parede nao pode ser partida ali — e isso e devolvido como
    motivo, nao escondido num painel grande demais.
    """
    if comp <= cfg.comp_max:
        return [(0, comp)], ""
    proibido = []
    for ab in aberturas:
        m = 100                                   # folga para o king stud
        proibido.append((ab["centro"] - ab["larg"] / 2 - m,
                         ab["centro"] + ab["larg"] / 2 + m))
    admissiveis = [x for x in range(cfg.modulacao, comp, cfg.modulacao)
                   if not any(a < x < b for a, b in proibido)]
    trechos, ini, motivo = [], 0, ""
    while comp - ini > cfg.comp_max:
        cands = [x for x in admissiveis if ini < x <= ini + cfg.comp_max]
        if not cands:
            motivo = (f"nao ha corte admissivel entre {ini} e "
                      f"{ini + cfg.comp_max} mm: a abertura ocupa toda a faixa. "
                      f"O painel sai com {comp - ini} mm e exige montagem no "
                      f"local ou icamento especial")
            break
        x = max(cands)
        trechos.append((ini, x))
        ini = x
    trechos.append((ini, comp))
    return trechos, motivo


def montar(par, vaos, cfg: Config, cod: str, pav: str = "T") -> list[Painel]:
    """Transforma uma parede em um ou mais paineis fabricaveis."""
    aberturas = _vaos_da_parede(par, vaos)
    trechos, motivo = _quebrar(par.comp, aberturas, cfg)
    saida = []
    for i, (ini, fim) in enumerate(trechos, 1):
        comp = fim - ini
        suf = f"{cod}" if len(trechos) == 1 else f"{cod}-{i}"
        p = Painel(cod=suf, parede=cod,
                   x=par.x1 + (ini if par.horizontal else 0),
                   y=par.y1 + (0 if par.horizontal else ini),
                   comp=comp, altura=cfg.altura, esp=par.esp,
                   externa=par.externa,
                   obs=motivo if comp > cfg.comp_max else "")
        locais = [dict(ab, centro=ab["centro"] - ini) for ab in aberturas
                  if ini <= ab["centro"] <= fim]
        p.aberturas = locais
        _preencher(p, locais, cfg)
        saida.append(p)
    return saida


def _preencher(p: Painel, aberturas: list, cfg: Config) -> None:
    """Gera as pecas do painel: guias, montantes, reforco de abertura, blocking."""
    n = 0

    def add(familia, perfil, comp, x, z, vertical=True, obs=""):
        nonlocal n
        n += 1
        p.pecas.append(Peca(f"{p.cod}-{familia[:2].upper()}{n:03d}",
                            familia, perfil, int(comp), int(x), int(z),
                            vertical, obs))

    # guias inferior e superior, na largura inteira do painel
    add("track", cfg.perfil_track, p.comp, 0, 0, False, "guia inferior")
    add("track", cfg.perfil_track, p.comp, 0, p.altura, False, "guia superior")

    # zonas proibidas para montante modular: dentro do vao mais os king studs
    proibido = []
    for ab in aberturas:
        v = ab["larg"] + 2 * cfg.folga_abertura
        proibido.append((ab["centro"] - v / 2, ab["centro"] + v / 2))

    # montantes modulares
    x = 0
    while x <= p.comp:
        dentro = any(a < x < b for a, b in proibido)
        if not dentro:
            add("stud", cfg.perfil_stud, p.altura, x, 0)
        x += cfg.modulacao
    if (p.comp % cfg.modulacao) != 0 and not any(a < p.comp < b for a, b in proibido):
        add("stud", cfg.perfil_stud, p.altura, p.comp, 0, True, "montante de ponta")

    # reforco de cada abertura
    for ab in aberturas:
        v = ab["larg"] + 2 * cfg.folga_abertura
        e, d = ab["centro"] - v / 2, ab["centro"] + v / 2
        topo = ab["peitoril"] + ab["alt"]
        for lado, xx in (("esq", e), ("dir", d)):
            add("king stud", cfg.perfil_stud, p.altura, xx, 0, True,
                f"{ab['tipo']} {lado}: continuo de piso a topo")
            add("jack stud", cfg.perfil_stud, topo, xx, 0, True,
                f"{ab['tipo']} {lado}: apoia a verga")
        add("header", cfg.perfil_verga, v, e, topo, False,
            f"verga do {ab['tipo']}, vao livre {ab['larg']} mm")
        if ab["peitoril"] > 0:
            add("sill", cfg.perfil_track, v, e, ab["peitoril"], False,
                f"peitoril do {ab['tipo']}")
        # cripples na MESMA modulacao, para a placa continuar achando montante
        for zc, hc, fam in ((topo, p.altura - topo, "cripple superior"),
                            (0, ab["peitoril"], "cripple inferior")):
            if hc < 100:
                continue
            xc = math.ceil(e / cfg.modulacao) * cfg.modulacao
            while xc < d:
                add(fam, cfg.perfil_stud, hc, xc, zc, True,
                    "mantem a modulacao da placa")
                xc += cfg.modulacao

    # blocking: corta o comprimento de flambagem distorcional
    alturas = []
    z = cfg.blocking_a_cada
    while z < p.altura - 200:
        alturas.append(z)
        z += cfg.blocking_a_cada
    for z in alturas:
        add("blocking", cfg.perfil_track, p.comp, 0, z, False,
            "corta a flambagem distorcional do montante")


def painelizar(paredes, vaos, cfg: Config = None, prefixo: str = "P") -> list[Painel]:
    cfg = cfg or Config()
    out = []
    for i, par in enumerate(paredes, 1):
        out += montar(par, vaos, cfg, f"{prefixo}{i:02d}")
    return out


def verga_necessaria(vao_mm: int, carga_kn_m: float, aco, cfg: Config = None,
                     candidatos=None) -> dict:
    """Escolhe a verga pelo vao e pela carga, com as alternativas rejeitadas.

    Secao 20: a escolha vem com o motivo. Nao basta dizer qual perfil entrou —
    e preciso dizer quais falharam e por que.
    """
    cfg = cfg or Config()
    cands = candidatos or [p for p in pf.catalogo()
                           if p.familia in ("montante", "viga") and p.bw >= 90]
    massa = _catalogo_massa()
    L = vao_mm
    msd = carga_kn_m * (L / 1000.0) ** 2 / 8        # kNm, biapoiada
    flecha_lim = L / 350.0
    testados = []
    for p in sorted(cands, key=lambda q: massa[q.cod]):
        f = vr.flexao(p, aco, L=L, travado=True)
        d = p.props()
        # flecha 5wL4/384EI. A identidade que evita o erro: 1 kN/m e
        # EXATAMENTE 1 N/mm (1000 N dividido por 1000 mm), e E esta em N/mm2.
        # Dividir por 1000 aqui — que foi o primeiro instinto — subestimava a
        # flecha em tres ordens de grandeza e aprovava qualquer verga.
        w = carga_kn_m                              # N/mm
        flecha = 5 * w * L ** 4 / (384 * 205_000.0 * d["Ix"])
        ok_m = msd <= f["mrd"]
        ok_f = flecha <= flecha_lim
        testados.append(dict(perfil=p.cod, mrd=f["mrd"], msd=msd, flecha=flecha,
                             flecha_lim=flecha_lim, uso=msd / f["mrd"],
                             ok=ok_m and ok_f, massa=massa[p.cod],
                             motivo="" if ok_m and ok_f else
                             ("momento insuficiente" if not ok_m else "flecha excedida")))
    aprovados = [t for t in testados if t["ok"]]
    if not aprovados:
        return dict(escolhido=None, alternativas=testados[:6],
                    motivo=f"nenhum perfil do catalogo vence {L} mm com "
                           f"{carga_kn_m} kN/m — reduzir vao ou inserir apoio")
    e = aprovados[0]
    return dict(escolhido=e, alternativas=testados[:6],
                motivo=f"utilizacao {e['uso']*100:.0f} %, flecha "
                       f"{e['flecha']:.2f} de {flecha_lim:.2f} mm admissiveis, "
                       f"menor massa entre os {len(aprovados)} perfis validos")
