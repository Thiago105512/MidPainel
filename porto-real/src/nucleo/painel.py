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
    comp_barra: int = 6_000           # mm, comprimento da barra comprada
    # Utilizacao ALVO no dimensionamento. Nao se confunde com o limite
    # normativo, que e 1,0 e continua sendo o criterio de aprovacao: 0,95 e
    # POLITICA DE PROJETO, e a razao e operacional, nao estrutural. Uma peca
    # aprovada por 0,3 % reprova na primeira revisao de carga — troca de
    # telha, um reservatorio a mais, um vao alargado —, e refazer o
    # dimensionamento custa mais que os 5 % de aco. Quem discordar da politica
    # muda este numero; quem discordar da NORMA nao pode mudar nada.
    u_alvo: float = 0.95


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
    # A orientacao vem da parede que originou o painel. Ate R28 ela nao era
    # guardada, e quem precisava dela a re-deduzia por fora — duas deducoes do
    # mesmo fato, que divergem na primeira mudanca. A descida de cargas precisa
    # dela para saber em que direcao a laje vence.
    horizontal: bool = True
    pav: str = ""
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
        p = Painel(cod=suf, parede=cod, horizontal=bool(par.horizontal),
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


def cabe_verga(ab: dict, altura: int, cfg: Config = None) -> bool:
    """Ha altura para verga sobre este vao?

    Criterio unico, consultado pelo gerador, pela auditoria e pelo checklist —
    se cada um tivesse o seu, divergiriam na primeira revisao.
    """
    cfg = cfg or Config()
    topo = ab["peitoril"] + ab["alt"]
    return topo + bw(cfg.perfil_verga) <= altura - bw(cfg.perfil_track)


def bw(perfil: str) -> int:
    """Largura da alma declarada na designacao: "Ue 90x40x12x0,95" -> 90."""
    return int(float(perfil.split()[1].split("x")[0].replace(",", ".")))


def emendas(comp: int, cfg: Config, fase: int = 0, apoios=()) -> list:
    """Divide um trecho horizontal em barras que existem para comprar.

    Uma guia de 7.800 mm nao e um item de catalogo: a barra vem com 6.000. Ate
    R27 o modelo emitia a peca inteira e o nesting apenas declarava que ela nao
    cabia — o que e honesto, mas nao e fabricavel. A peca que nao cabe na barra
    nao e uma peca: sao duas, com uma emenda entre elas, e a emenda tem lugar.

    O lugar e um montante: emenda no vao livre e rotula. Por isso o corte cai
    sobre um APOIO REAL — nao sobre um multiplo da modulacao, que e onde o
    montante estaria se nada o tivesse suprimido. A diferenca apareceu no
    painel do portao: 7.200 mm com a abertura ocupando quase tudo, so dois
    montantes de ponta, e toda emenda calculada pela modulacao caia no ar.

    Quando nenhum apoio cabe na barra, a emenda e emitida assim mesmo, na
    posicao limite, e devolvida marcada como SEM APOIO — o painel declara, a
    auditoria acusa, e a decisao (barra especial sob encomenda ou talao
    dimensionado ao momento) fica com quem assina o projeto.

    `fase` recua a emenda em N modulos para ESCALONAR os trechos. Guia inferior,
    guia superior e blocking emendados na mesma secao transformam a emenda numa
    articulacao do painel inteiro — e e exatamente a secao onde o painel iria
    dobrar no icamento.

    Devolve [(x_inicio, comprimento, apoiada), ...] cobrindo o trecho inteiro.
    """
    if comp <= cfg.comp_barra:
        return [(0, comp, True)]
    segs, x = [], 0
    while comp - x > cfg.comp_barra:
        limite = x + cfg.comp_barra
        # Apoio so serve se deixar trecho utilizavel dos dois lados: um apoio a
        # 90 mm do inicio "cabe na barra" e produziria um pedaco de 90 mm. Por
        # isso o candidato precisa distar ao menos um modulo do corte anterior.
        minimo = x + cfg.modulacao
        cabem = sorted((a for a in apoios if minimo <= a <= limite), reverse=True)
        apoiada = bool(cabem)
        if not cabem:
            # nenhum apoio utilizavel: a emenda vai para a modulacao teorica e
            # sai MARCADA. Os candidatos continuam varios para que a fase ainda
            # escalone — emenda sem apoio, todas na mesma secao, seria a pior
            # das combinacoes possiveis.
            cabem = [m for m in range(int(limite // cfg.modulacao) * cfg.modulacao,
                                      int(minimo) - 1, -cfg.modulacao)] or [limite]
        j = cabem[min(fase, len(cabem) - 1)]
        segs.append((x, j - x, apoiada))
        x = j
    segs.append((x, comp - x, True))
    return segs


def _preencher(p: Painel, aberturas: list, cfg: Config, jamba=None) -> None:
    """Gera as pecas do painel: guias, montantes, reforco de abertura, blocking.

    CONVENCAO DE COORDENADA, e ela e o contrato com o desenho e com a maquina:
    (x, z) e o canto de MENOR coordenada da peca no plano do painel, e nenhuma
    peca sai do envelope 0..comp x 0..altura. Montante e cripple atravessam a
    guia — isso e fisico, o montante encaixa DENTRO da guia — mas nada
    ultrapassa a face externa do painel.

    Ate R25 a convencao era implicita e, por isso, inconsistente: a guia
    superior nascia em z = altura (92 mm acima do painel), o montante de ponta
    em x = comp (90 mm alem da borda) e a verga vencia exatamente o vao livre,
    sem apoio sobre os jacks. Nada disso aparecia em prancha porque nada
    desenhava a peca a partir da propria coordenada. O visualizador desenhou, e
    138 pecas apareceram fora do painel.
    """
    # UMA identidade por peca. Ate R31 havia duas: o painel numerava por ordem
    # de geracao (TP01-1-ST001) e a fabrica renomeava por posicao
    # (TP01-1-ST1FB). A peca que se clica no 3D tinha codigo diferente da mesma
    # peca no plano de corte, e rastreabilidade com dois codigos nao e
    # rastreabilidade. O codigo da fabrica e o unico, e nasce aqui.
    import nucleo.peca as _pe
    bt, bs, bv = bw(cfg.perfil_track), bw(cfg.perfil_stud), bw(cfg.perfil_verga)

    def add(familia, perfil, comp, x, z, vertical=True, obs=""):
        p.pecas.append(Peca(_pe._codigo(familia, p.cod, int(x), int(z)),
                            familia, perfil, int(comp), int(x), int(z),
                            vertical, obs))

    # As horizontais so podem ser emendadas depois que se sabe ONDE ha apoio, e
    # isso so se sabe depois de gerar as verticais. Por isso ficam na fila.
    horizontais = []

    def add_h(familia, perfil, comp, x0, z, obs, fase=0):
        horizontais.append((familia, perfil, int(comp), int(x0), int(z), obs, fase))

    # guias inferior e superior, na largura inteira do painel
    add_h("track", cfg.perfil_track, p.comp, 0, 0, "guia inferior", fase=0)
    add_h("track", cfg.perfil_track, p.comp, 0, p.altura - bt, "guia superior",
          fase=1)

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
            add("stud", cfg.perfil_stud, p.altura, min(x, p.comp - bs), 0)
        x += cfg.modulacao
    if (p.comp % cfg.modulacao) != 0 and not any(a < p.comp < b for a, b in proibido):
        add("stud", cfg.perfil_stud, p.altura, p.comp - bs, 0, True,
            "montante de ponta")

    # reforco de cada abertura
    for ab in aberturas:
        v = ab["larg"] + 2 * cfg.folga_abertura
        e, d = ab["centro"] - v / 2, ab["centro"] + v / 2
        topo = ab["peitoril"] + ab["alt"]
        # o king e o jack ficam FORA do vao: a face interna deles e a borda do
        # vao bruto, senao o vao livre entregue e 180 mm menor que o esquadria.
        # Quantos sao vem do dimensionamento (jamba_necessaria), nao da praxe
        # de "um de cada lado" — a jamba recebe a reacao da verga, e essa cresce
        # com o vao enquanto a carga do montante corrente nao muda.
        nj = (jamba or {}).get("n", 1)
        pj_ = (jamba or {}).get("perfil") or cfg.perfil_stud
        for lado, x0j, passo in (("esq", max(0, e - bs), -bs),
                                 ("dir", min(d, p.comp - bs), +bs)):
            for i in range(nj):
                xx = x0j + i * passo
                if xx < 0 or xx + bs > p.comp:
                    p.obs = (p.obs + " | " if p.obs else "") + (
                        f"{ab['tipo']} {lado}: a jamba exige {nj} montantes e "
                        f"so cabem {i} dentro do painel — o vao esta perto "
                        f"demais da borda")
                    break
                extra = "" if nj == 1 else f" ({i+1} de {nj}, caixa parafusada)"
                add("king stud", pj_, p.altura, xx, 0, True,
                    f"{ab['tipo']} {lado}: continuo de piso a topo{extra}")
                add("jack stud", pj_, min(topo, p.altura), xx, 0, True,
                    (f"{ab['tipo']} {lado}: apoia a verga{extra}"
                     if cabe_verga(ab, p.altura, cfg) else
                     f"{ab['tipo']} {lado}: vao de altura total, "
                     f"sobe ate a guia{extra}"))
        # a verga APOIA sobre os jacks — por isso vence o vao bruto mais a
        # largura dos dois jacks, e nao o vao livre
        xh = max(0, e - bs)
        ch = min(v + 2 * bs, p.comp - xh)
        zh = min(topo, p.altura - bt - bv)
        if not cabe_verga(ab, p.altura, cfg):
            # Vao mais alto que o painel: nao existe verga possivel. Antes de
            # R25 o gerador emitia um jack de 2800 mm dentro de um painel de
            # 2600 e seguia adiante. Emitir geometria impossivel em silencio e
            # pior do que nao emitir: aqui o vao e assumido de altura total e a
            # falta da verga e declarada, porque a carga passa a ser da
            # estrutura do pavimento de cima.
            p.obs = (p.obs + " | " if p.obs else "") + (
                f"{ab['tipo']} tem {topo} mm de topo num painel de "
                f"{p.altura} mm: vao de altura total, sem verga — a carga "
                f"acima do vao e da estrutura do pavimento superior")
            continue
        add_h("header", cfg.perfil_verga, ch, xh, zh,
              f"verga do {ab['tipo']}, vao livre {ab['larg']} mm, "
              f"apoio de {bs} mm em cada jack")
        if ab["peitoril"] > 0:
            # a face SUPERIOR do peitoril e a linha do peitoril: a esquadria
            # senta sobre ele, nao ao lado dele
            add_h("sill", cfg.perfil_track, ch, xh,
                  max(0, ab["peitoril"] - bt), f"peitoril do {ab['tipo']}")
        # cripples na MESMA modulacao, para a placa continuar achando montante
        # o cripple superior comeca ACIMA da verga, nao dentro dela
        for zc, hc, fam in ((zh + bv, p.altura - zh - bv, "cripple superior"),
                            (0, max(0, ab["peitoril"] - bt), "cripple inferior")):
            if hc < 100:
                continue
            xc = math.ceil(e / cfg.modulacao) * cfg.modulacao
            while xc < d:
                # sem clamp: um cripple deslocado para caber sairia da
                # modulacao, e a placa ficaria sem apoio justamente na borda.
                # Quando nao cabe, quem apoia ali e o montante de ponta.
                if xc + bs <= p.comp:
                    add(fam, cfg.perfil_stud, hc, xc, zc, True,
                        "mantem a modulacao da placa")
                xc += cfg.modulacao

    # blocking: corta o comprimento de flambagem distorcional
    alturas = []
    z = cfg.blocking_a_cada
    while z < p.altura - 200:
        alturas.append(z)
        z += cfg.blocking_a_cada
    for i, z in enumerate(alturas):
        add_h("blocking", cfg.perfil_track, p.comp, 0, z,
              "corta a flambagem distorcional do montante", fase=2 + i)

    # ---- agora sim: emendar as horizontais sobre os apoios que existem
    apoios = sorted({q.x for q in p.pecas if q.vertical} |
                    {q.x + bs for q in p.pecas if q.vertical})
    sem_apoio = []
    for familia, perfil, comp, x0, z, obs, fase in horizontais:
        segs = emendas(comp, cfg, fase, [a - x0 for a in apoios if x0 < a < x0 + comp])
        for k, (dx, c, apoiada) in enumerate(segs, 1):
            nota = obs
            if len(segs) > 1:
                # o flag pertence a junta DIREITA do trecho; o ultimo trecho nao
                # tem junta direita, e a esquerda e a do trecho anterior. Sem
                # isso, metade de cada emenda sem apoio sairia sem o aviso —
                # e seria justamente a metade que alguem leria na obra.
                ultimo = k == len(segs)
                junta = x0 + dx if ultimo else x0 + dx + c
                apoiada = segs[k - 2][2] if ultimo else apoiada
                nota = (f"{obs} — trecho {k} de {len(segs)}, emenda em "
                        f"x = {junta}" + ("" if apoiada else ", SEM MONTANTE"))
                if not apoiada and not ultimo:
                    sem_apoio.append((familia, junta))
            add(familia, perfil, c, x0 + dx, z, False, nota)
    if sem_apoio:
        onde = ", ".join(f"{f} em x = {j}" for f, j in sem_apoio)
        p.obs = (p.obs + " | " if p.obs else "") + (
            f"emenda sem montante de apoio ({onde}): a abertura ocupa a faixa "
            f"onde a barra de {cfg.comp_barra} mm termina. Exige barra sob "
            f"encomenda ou talao dimensionado ao momento da emenda")


def painelizar(paredes, vaos, cfg: Config = None, prefixo: str = "P",
               pav: str = "") -> list[Painel]:
    cfg = cfg or Config()
    out = []
    for i, par in enumerate(paredes, 1):
        out += montar(par, vaos, cfg, f"{prefixo}{i:02d}")
    for p in out:
        p.pav = pav or (prefixo[0] if prefixo and prefixo[0] in "TS" else "")
    return out


def verga_necessaria(vao_mm: int, carga_kn_m: float, aco, cfg: Config = None,
                     candidatos=None, flecha_div: float = 350.0) -> dict:
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
    # O limite de flecha e PARAMETRO do problema, nao constante da funcao:
    # verga de parede aceita L/350, piso com porcelanato colado pede L/500 e
    # cobertura aceita L/250. Fixar 350 aqui obrigava quem precisasse de outro
    # a filtrar por fora — e filtrar por fora de uma lista truncada foi
    # exatamente como tres comodos foram declarados invencíveis quando o
    # catalogo tinha perfil para eles: os mais pesados nunca entravam na lista.
    flecha_lim = L / flecha_div
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
        return dict(escolhido=None, alternativas=testados[:6], testados=testados,
                    motivo=f"nenhum perfil do catalogo vence {L} mm com "
                           f"{carga_kn_m} kN/m — reduzir vao ou inserir apoio")
    e = aprovados[0]
    return dict(escolhido=e, alternativas=testados[:6], testados=testados,
                motivo=f"utilizacao {e['uso']*100:.0f} %, flecha "
                       f"{e['flecha']:.2f} de {flecha_lim:.2f} mm admissiveis, "
                       f"menor massa entre os {len(aprovados)} perfis validos")


def jamba_necessaria(nsd_kn: float, altura: int, aco, cfg: Config = None,
                     k: float = 0.5, perfis=None) -> dict:
    """Quantos montantes a jamba precisa ter, e por que nao menos.

    A jamba de uma abertura nao e um montante: e o apoio da verga. Ela recebe a
    reacao de tudo o que a verga colheu, e por isso a carga nela cresce com o
    VAO da abertura enquanto a do montante corrente nao muda. Numa parede com
    portao de 4,8 m o king stud recebe 29 kN onde o montante corrente recebe 3.

    Ate R28 toda abertura saia com um king e um jack, independentemente do vao.
    Isso aprovava a janela de 800 mm e reprovava o portao por 2x — e a
    verificacao nao dizia, porque so olhava um montante tipico.

    Duas familias de solucao, e as duas entram na comparacao:
      - COMPOSTA: n montantes iguais em caixa, Nrd = n x Nrd (limite inferior;
        a caixa parafusada tem rigidez a torcao maior que a soma, entao contar
        so a soma e a favor da seguranca);
      - CHAPA MAIOR: o mesmo perfil em espessura superior.

    Devolve a escolha e as rejeitadas com o motivo — secao 20.
    """
    cfg = cfg or Config()
    base = next((p for p in (perfis or pf.catalogo()) if p.cod == cfg.perfil_stud),
                None)
    if base is None:
        raise KeyError(f"perfil de montante '{cfg.perfil_stud}' fora do catalogo")
    massa = _catalogo_massa()

    alvo = max(0.1, min(1.0, cfg.u_alvo))

    def nrd(p):
        return vr.compressao(p, aco, L=altura, kx=1.0, ky=k, kz=k)["nrd"]

    n_base = nrd(base)
    testados, escolha = [], None

    # familia 1: composta com o proprio perfil
    for n in range(1, 7):
        cap = n * n_base
        ok = cap * alvo >= nsd_kn
        testados.append(dict(solucao=f"{n} x {base.cod}", n=n, perfil=base.cod,
                             nrd=cap, u=nsd_kn / cap if cap else float("inf"),
                             massa=n * massa[base.cod] * altura / 1000.0,
                             aceita=ok))
        if ok and escolha is None:
            escolha = testados[-1]

    # familia 2: mesma forma, chapa mais grossa, dois montantes no maximo
    mesma_forma = [p for p in (perfis or pf.catalogo())
                   if p.familia == base.familia and p.bw == base.bw
                   and p.cod != base.cod and p.t > base.t]
    for p in sorted(mesma_forma, key=lambda q: q.t)[:3]:
        for n in (1, 2):
            cap = n * nrd(p)
            testados.append(dict(solucao=f"{n} x {p.cod}", n=n, perfil=p.cod,
                                 nrd=cap, u=nsd_kn / cap if cap else float("inf"),
                                 massa=n * massa[p.cod] * altura / 1000.0,
                                 aceita=cap * alvo >= nsd_kn))

    # Criterio de escolha, declarado porque e uma decisao e nao um calculo: a
    # mais leve vence, MAS a composta do proprio montante vence empate de ate
    # 15 % de massa. Uma espessura nova para uma peca so e um SKU novo — outro
    # fardo no estoque, outra etiqueta, outra chance de o montador pegar o
    # errado. Quinze por cento de aco e mais barato que isso.
    MARGEM_SKU = 0.15
    aceitas = [t for t in testados if t["aceita"]]
    if aceitas:
        leve = min(aceitas, key=lambda t: t["massa"])
        mesma_sku = [t for t in aceitas if t["perfil"] == base.cod]
        escolha = leve
        if mesma_sku:
            cand = min(mesma_sku, key=lambda t: t["massa"])
            if cand["massa"] <= leve["massa"] * (1 + MARGEM_SKU):
                escolha = cand
    rejeitadas = [t for t in testados if not t["aceita"]]
    return dict(
        escolha=escolha, nsd=nsd_kn, nrd_unitario=n_base,
        n=escolha["n"] if escolha else 0,
        perfil=escolha["perfil"] if escolha else "",
        alternativas=testados, rejeitadas=rejeitadas,
        sku_nova=bool(escolha) and escolha["perfil"] != base.cod,
        u_alvo=alvo,
        motivo=(f"{escolha['solucao']} da {escolha['nrd']:.1f} kN para "
                f"{nsd_kn:.1f} kN de calculo (u = {escolha['u']:.2f}, "
                f"alvo {alvo:.2f}); "
                f"{len(rejeitadas)} alternativa(s) rejeitada(s), a mais proxima "
                f"por {min((t['u'] for t in rejeitadas), default=0):.2f} de "
                f"utilizacao" if escolha else
                f"NENHUMA solucao do catalogo atende {nsd_kn:.1f} kN com "
                f"L = {altura} mm, k = {k} e utilizacao alvo {alvo:.2f}: o vao "
                f"exige pilar, nao jamba"))


def travamento_k(p: Painel) -> float:
    """k de flambagem do montante, derivado do blocking que o painel TEM."""
    zs = sorted({q.z for q in p.pecas if q.familia == "blocking"})
    if not zs:
        return 1.0
    cortes = [0] + zs + [p.altura]
    return max(b - a for a, b in zip(cortes, cortes[1:])) / p.altura


def dimensionar_jambas(p: Painel, nsd_king: float, aco, cfg: Config = None,
                       perfis=None) -> dict | None:
    """Redimensiona as jambas do painel para a carga real e regenera as pecas.

    Segunda passada, e a segunda passada e necessaria por um motivo que nao e
    preguica: a carga na jamba depende da area de influencia do painel, que
    depende da posicao das paredes, que so existe depois da painelizacao. A
    primeira passada monta a geometria; a segunda a dimensiona. Como acrescentar
    montante nao muda area de influencia nenhuma, duas passadas bastam — o ponto
    fixo se fecha na segunda.
    """
    if not p.aberturas:
        return None
    cfg = cfg or Config()
    r = jamba_necessaria(nsd_king, p.altura, aco, cfg,
                         k=travamento_k(p), perfis=perfis)
    p.pecas = []
    p.obs = " | ".join(t for t in p.obs.split(" | ")
                       if t and "jamba exige" not in t)
    _preencher(p, p.aberturas, cfg, jamba=r)
    return r
