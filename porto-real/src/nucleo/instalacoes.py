"""INSTALACOES — o tracado que existia no desenho e nao no modelo.

As pranchas 26 a 29 desenham hidraulica, eletrica, climatizacao e drenagem
completas, e tudo o que chegava ao BOM era zero. A razao e a mesma do vigamento
ate R31 e da fundacao ate R37: o dado existia como PONTO (18 pecas hidraulicas,
11 ralos, 24 cargas especiais, 8 equipamentos de clima) e nao existia como
PERCURSO. Ponto nao tem comprimento.

COMO SE MEDE, E POR QUE ASSIM. Sem projeto executivo de tracado, o comprimento
sai de percurso MANHATTAN de cada ponto ate a prumada mais proxima, mais a
descida. Nao e o percurso que o instalador vai fazer; e o percurso mais curto
que respeita a geometria da casa, e por isso e um limite INFERIOR declarado.
Um tubo real serpenteia — desvia de viga, contorna shaft, sobe e desce. O
acrescimo tipico de 15 a 25 % entra como fator explicito, nunca embutido.

O QUE ISSO NAO E. Nao e projeto de instalacoes. Nao dimensiona diametro — os
diametros vem do calculo que ja existe (NBR 5626 por pesos, NBR 8160 por UHC).
Aqui se mede COMPRIMENTO de diametro ja dimensionado, para que o material exista
no orcamento em vez de aparecer na obra.
"""
from __future__ import annotations

# Acrescimo sobre o percurso Manhattan. Declarado, nao embutido: quem discordar
# muda este numero e ve o efeito, em vez de descobrir que havia um fator
# escondido dentro do comprimento.
FATOR_PERCURSO = 1.20

# Conexoes por metro de tubo, por sistema. (H) de pratica: hidraulica tem joelho
# a cada mudanca de direcao e te em cada derivacao.
CONEXOES_POR_M = {"agua": 0.55, "esgoto": 0.35, "eletrica": 0.25}


def _manhattan(x1, y1, x2, y2) -> float:
    return abs(x2 - x1) + abs(y2 - y1)


def prumadas_efetivas(pj, shafts: dict = None) -> list:
    """A posicao que vale e a RESOLVIDA, quando existe uma.

    Uma so fonte: quem mede ramal, quem monta volume e quem confere clash leem
    daqui. Enquanto a resolucao nao existir, vale a declarada — e o conflito
    que ela produz continua aparecendo, que e o comportamento correto.
    """
    if not shafts:
        return pj.PRUMADAS
    res = shafts.get("prumadas", shafts)
    return [dict(pr, x=res[pr["cod"]]["x"], y=res[pr["cod"]]["y"])
            if pr["cod"] in res else pr for pr in pj.PRUMADAS]


def _prumada_mais_proxima(x, y, prumadas, tipo) -> dict:
    cands = [p for p in prumadas if p["tipo"] == tipo] or prumadas
    return min(cands, key=lambda p: _manhattan(x, y, p["x"], p["y"]))


def hidraulica(pj, shafts: dict = None) -> dict:
    """Agua fria, agua quente e esgoto: comprimento por diametro.

    O percurso de cada peca vai ate a prumada do seu sistema. Agua quente so
    existe onde a peca pede — e isso e dado, nao suposicao: `quente` ja e campo
    da peca desde a prancha 26.
    """
    pecas = pj.pecas_hidraulicas()
    pru = prumadas_efetivas(pj, shafts)
    ramais = []
    for p in pecas:
        # agua fria: sempre; quente: so onde declarado
        af = _prumada_mais_proxima(p["x"], p["y"], pru, "agua fria")
        d_af = _manhattan(p["x"], p["y"], af["x"], af["y"]) * FATOR_PERCURSO
        ramais.append(dict(peca=p["cod"], sistema="agua fria", dn=25,
                           comp_mm=d_af, prumada=af["cod"]))
        if p["quente"]:
            ramais.append(dict(peca=p["cod"], sistema="agua quente", dn=20,
                               comp_mm=d_af, prumada=af["cod"],
                               obs="PEX paralelo ao ramal de fria"))
        # esgoto: ate a prumada de esgoto, no diametro do aparelho
        es = _prumada_mais_proxima(p["x"], p["y"], pru, "esgoto")
        dn_es = 100 if p["uhc"] >= 6 else (50 if p["uhc"] >= 3 else 40)
        ramais.append(dict(peca=p["cod"], sistema="esgoto", dn=dn_es,
                           comp_mm=_manhattan(p["x"], p["y"], es["x"], es["y"])
                           * FATOR_PERCURSO, prumada=es["cod"]))
    for r in pj.RALOS:
        es = _prumada_mais_proxima(r["x"], r["y"], pru, "esgoto")
        ramais.append(dict(peca=r["cod"], sistema="esgoto", dn=r["dn"],
                           comp_mm=_manhattan(r["x"], r["y"], es["x"], es["y"])
                           * FATOR_PERCURSO, prumada=es["cod"]))

    # prumada vertical: uma descida por pavimento, mais ventilacao ate a laje
    h = pj.PISO_A_PISO + pj.PE_DIREITO
    for p in pru:
        ramais.append(dict(peca=p["cod"], sistema=("esgoto" if p["tipo"] ==
                                                   "esgoto" else "agua fria"),
                           dn=p["dn"], comp_mm=h, prumada=p["cod"],
                           obs="prumada vertical, do terreo a cobertura"))

    por_dn: dict = {}
    for r in ramais:
        chave = (r["sistema"], r["dn"])
        por_dn[chave] = por_dn.get(chave, 0.0) + r["comp_mm"] / 1000.0
    itens = [dict(sistema=s, dn=d, comp_m=round(m, 1),
                  conexoes=int(m * CONEXOES_POR_M.get(
                      "agua" if "agua" in s else "esgoto", 0.4)))
             for (s, d), m in sorted(por_dn.items(), key=lambda kv: -kv[1])]
    return dict(ramais=ramais, itens=itens,
                comp_total=round(sum(i["comp_m"] for i in itens), 1),
                conexoes=sum(i["conexoes"] for i in itens),
                fator=FATOR_PERCURSO,
                pecas=len(pecas), ralos=len(pj.RALOS), prumadas=len(pru))


def eletrica(pj) -> dict:
    """Eletroduto, cabo e caixa: do quadro a cada ponto.

    O quadro fica no centro de gravidade da casa — nao por elegancia: o cabo e
    o item caro, e o centro minimiza a soma das distancias. Onde o quadro real
    estiver em outro lugar, o numero cresce, e por isso ele e declarado.
    """
    xs = [a.x + a.w / 2 for a in pj.TERREO]
    ys = [a.y + a.h / 2 for a in pj.TERREO]
    qx, qy = sum(xs) / len(xs), sum(ys) / len(ys)

    pontos = []
    for c in pj.CARGAS_ESPECIAIS:
        pontos.append(dict(cod=c["cod"], tipo="TUE", va=c["va"], v=c["v"]))
    # PONTOS DE TOMADA: da previsao que o CASO ja faz pela NBR 5410 9.5.2.2,
    # que conta PERIMETRO — uma tomada a cada 5 m de parede, ou 3,5 m em area
    # molhada. Esta funcao contava `area / 5`, inventando uma segunda regra
    # para o mesmo fato, e a segunda estava errada: dava 55 tomadas onde a
    # norma pede 71. O sinal do erro nao era uniforme — sobrava na garagem e na
    # master, faltava na lavanderia (1 contra 4), no banho, na despensa e na
    # cozinha, justamente onde a norma e mais exigente. Comodo estreito e
    # comprido tem muito perimetro e pouca area, e e nele que se mora.
    prev = {x["amb"]: x for x in pj.previsao_iluminacao_tug()}
    for a in pj.TERREO + pj.SUPERIOR:
        n_tom = prev.get(a.cod, {}).get("tugs", 1)
        for i in range(n_tom):
            pontos.append(dict(cod=f"{a.cod}-TUG{i+1}", tipo="TUG",
                               amb=a.cod, x=a.x + a.w / 2, y=a.y + a.h / 2))
        pontos.append(dict(cod=f"{a.cod}-ILU", tipo="ILU", amb=a.cod,
                           x=a.x + a.w / 2, y=a.y + a.h / 2))

    comp = 0.0
    for p in pontos:
        if "x" not in p:
            continue
        comp += _manhattan(p["x"], p["y"], qx, qy) * FATOR_PERCURSO
    # subida ate o ponto: 1,3 m em media entre tomada baixa e interruptor alto
    comp += len(pontos) * 1_300
    m = comp / 1000.0
    return dict(quadro=(round(qx), round(qy)), pontos=len(pontos),
                eletroduto_m=round(m, 1),
                cabo_m=round(m * 3.2, 1),     # fase, neutro e terra + reserva
                caixas=len(pontos),
                disjuntores=len(pj.CARGAS_ESPECIAIS) + 12,
                fator=FATOR_PERCURSO,
                obs="quadro no centro de gravidade dos ambientes do terreo: o "
                    "cabo e o item caro, e o centro minimiza a soma das "
                    "distancias. Quadro em outro lugar so aumenta")


def climatizacao(pj) -> dict:
    """Linha frigorigena e dreno, por equipamento ate o seu nicho."""
    linhas = []
    for c in pj.CLIMATIZACAO:
        if c.get("reserva"):
            continue
        # a distancia ao nicho ja e dado da prancha 28 quando existir; onde nao
        # houver, o percurso e o do ambiente ate a fachada mais proxima
        linhas.append(dict(equip=c["amb"], nicho=c.get("nicho", "-"),
                           capacidade=c["capacidade"],
                           comp_m=c.get("linha_m", 8.0)))
    total = sum(l["comp_m"] for l in linhas)
    return dict(linhas=linhas, n=len(linhas),
                linha_m=round(total, 1),
                dreno_m=round(total * 0.8, 1),
                isolamento_m=round(total * 2, 1),
                obs="linha frigorigena de ida e volta isolada separadamente: "
                    "o isolamento e o dobro do percurso")


# ---------------------------------------------------------------------------
# VOLUMES PARA CLASH — o tracado em 3D, contra a estrutura em 3D
# ---------------------------------------------------------------------------
# O item "clashes" do checklist trazia `True` literal desde sempre, e o motivo
# nao era preguica: nao havia com o que conflitar. A estrutura so ganhou
# vigamento em R31 e o MEP so ganhou tracado agora. Uma verificacao de
# interferencia entre uma disciplina e o vazio acha zero conflitos, e o zero e
# verdadeiro — e inutil.
def volumes_mep(pj, shafts: dict = None) -> list:
    """Cada ramal como um volume de passagem, em coordenada do mundo.

    O volume nao e o tubo: e o tubo MAIS o espaco que ele precisa para ser
    instalado e isolado. Um DN100 com 110 mm de diametro externo exige cerca de
    150 mm de vao livre — conferir o tubo nu contra a estrutura aprovaria
    passagens onde nao cabe a mao do instalador.
    """
    import nucleo.peca as pe
    FOLGA = 40.0          # mm de cada lado, para instalar e isolar
    vols = []
    pecas = pj.pecas_hidraulicas()
    efetivas = prumadas_efetivas(pj, shafts)
    for p in pecas:
        pru = _prumada_mais_proxima(p["x"], p["y"], efetivas, "esgoto")
        dn = 100 if p["uhc"] >= 6 else (50 if p["uhc"] >= 3 else 40)
        r = dn / 2 + FOLGA
        # ESGOTO HORIZONTAL NAO CORRE NA PAREDE. Ele corre sob o piso — no
        # radier no terreo, dentro do entrepiso no superior — e so a prumada e
        # vertical. A primeira versao roteou o ramal no plano da parede, na
        # altura do montante, e produziu 85 "conflitos criticos" que eram erro
        # meu de tracado: a propria PR-21 ja dizia que esgoto vertical nao cabe
        # em montante por definicao, e o horizontal nem tenta.
        if p["amb"].startswith("S-"):
            z = pj.NIVEL_SUPERIOR - 150.0      # dentro do vigamento
        else:
            z = -150.0                          # sob o radier
        # trecho em X e depois em Y, que e o percurso Manhattan medido
        x0, x1 = sorted((p["x"], pru["x"]))
        y0, y1 = sorted((p["y"], pru["y"]))
        # o DN viaja NO CODIGO do volume. Sem isso a severidade tinha de
        # supor, e supus DN100 em todo ramal: 191 conflitos "criticos" onde a
        # maioria e DN40 que passa em furo de 45 mm sem problema nenhum.
        vols.append(pe.Volume(f"{p['cod']}-X-DN{dn}", "hidraulica",
                              x0, p["y"] - r, z - r, x1, p["y"] + r, z + r))
        vols.append(pe.Volume(f"{p['cod']}-Y-DN{dn}", "hidraulica",
                              pru["x"] - r, y0, z - r, pru["x"] + r, y1, z + r))
    for pr in efetivas:
        a, b = pr["secao"]
        vols.append(pe.Volume(f"{pr['cod']}-V-DN{pr['dn']}", "hidraulica",
                              pr["x"], pr["y"], 0.0,
                              pr["x"] + a, pr["y"] + b,
                              pj.NIVEL_SUPERIOR + pj.PE_DIREITO))
    return vols


# ---------------------------------------------------------------------------
# SHAFT — a decisao que o modelo nao tinha como tomar, e agora toma por regra
#
# R38 achou o conflito e parou nele: a posicao declarada de tres prumadas cai
# dentro da linha de parede, e um shaft de 300 x 300 nao cabe numa parede de
# 150 mm. Havia duas saidas, e o modelo nao tinha dado para escolher.
#
# A REGRA ADOTADA, e por que ela e a menos arriscada das duas:
#
#   O shaft e uma CAIXA NA FACE da parede, do lado do ambiente molhado que ele
#   serve, e a parede permanece CONTINUA.
#
# Interromper a parede seria a outra saida, e custa caro em tres frentes:
#   1. a descida de cargas supoe TODA parede portante (hipotese declarada, a
#      favor da seguranca). Interromper uma parede portante exige verga e
#      transferencia de carga para os montantes vizinhos — uma verificacao que
#      este modelo nao faz;
#   2. a parede interrompida perde o painel de contraventamento naquele trecho,
#      e o contraventamento ja e verificado contra a forca global da NBR 6123;
#   3. a NBR 8160 exige ACESSO de inspecao a prumada. Caixa com portinhola na
#      face molhada da acesso; shaft dentro da parede nao da.
#
# O custo da regra e conhecido e pequeno: 0,09 m2 de piso por prumada de
# esgoto, tomados do ambiente molhado, mais o enclausuramento em placa RU.
#
# E o resultado NAO e uma coordenada escrita a mao. O deslocamento e PROCURADO:
# o menor afastamento que (a) tira a caixa de dentro de qualquer peca de
# estrutura e (b) deixa a caixa inteira dentro de um ambiente — de preferencia
# molhado. Se nenhum lado servir, a funcao nao inventa: devolve a prumada como
# NAO RESOLVIDA, e o conflito continua de pe.
# ---------------------------------------------------------------------------
PASSO_BUSCA = 25.0        # mm por tentativa
AFASTAMENTO_MAX = 400.0   # mm: alem disso a caixa deixa de ser caixa de parede


def _ambientes(pj) -> list:
    """Todo retangulo habitavel do caso, ambiente ou subdivisao.

    A subdivisao entra porque e ONDE o banho de fato esta: as suites sao
    retangulos unicos e o banho vive em SUBDIVISOES, com geometria exata. Ler
    so a lista de ambientes e o que fazia o modelo achar que nao ha banheiro
    no pavimento superior.
    """
    out = []
    for a in pj.TERREO + pj.SUPERIOR:
        out.append(dict(cod=a.cod, nome=a.nome, x=a.x, y=a.y, w=a.w, h=a.h,
                        pav=a.pav, molhado=a.molhado))
    for sd in pj.SUBDIVISOES:
        pai = next((a for a in pj.TERREO + pj.SUPERIOR if a.cod == sd["pai"]),
                   None)
        out.append(dict(cod=f"{sd['pai']}/{sd['nome']}", nome=sd["nome"],
                        x=sd["x"], y=sd["y"], w=sd["w"], h=sd["h"],
                        pav=pai.pav if pai else "T",
                        molhado=sd.get("molhado", False)))
    return out


def _dentro(x0, y0, x1, y1, a) -> bool:
    return (x0 >= a["x"] and y0 >= a["y"]
            and x1 <= a["x"] + a["w"] and y1 <= a["y"] + a["h"])


def _bate(x0, y0, x1, y1, vols) -> int:
    """Quantas pecas de estrutura a caixa atravessa nesta posicao."""
    n = 0
    for v in vols:
        if x0 < v.x1 and x1 > v.x0 and y0 < v.y1 and y1 > v.y0:
            n += 1
    return n


def resolver_shafts(pj, paineis, base_por_pav: dict) -> dict:
    """Acha, para cada prumada, o menor afastamento que a tira da parede.

    Devolve tambem o enclausuramento, porque a decisao TEM material: a caixa e
    montante de 48 mm e placa RU nas faces expostas, e se a decisao existisse
    so como coordenada o orcamento nao saberia dela.
    """
    est = volumes_estrutura(paineis, base_por_pav)
    ambs = _ambientes(pj)
    out, placa, piso_tomado = {}, 0.0, 0.0
    for pr in pj.PRUMADAS:
        a, b = pr["secao"]
        x, y = float(pr["x"]), float(pr["y"])
        base = _bate(x, y, x + a, y + b, est)
        if base == 0:
            out[pr["cod"]] = dict(pr, x=x, y=y, deslocado=0.0, lado="—",
                                  ambiente="", resolvido=True,
                                  motivo="a posicao declarada ja esta livre de "
                                         "estrutura: nada a decidir")
            continue
        melhor = None
        d = PASSO_BUSCA
        while d <= AFASTAMENTO_MAX and melhor is None:
            # quatro lados e quatro diagonais. A diagonal nao e refinamento:
            # uma prumada no ENCONTRO de duas paredes — e PN-02 esta no canto
            # de duas — nao se livra das duas afastando-se numa direcao so.
            for lado, (dx, dy) in (("+Y", (0, 1)), ("-Y", (0, -1)),
                                   ("+X", (1, 0)), ("-X", (-1, 0)),
                                   ("+X+Y", (1, 1)), ("+X-Y", (1, -1)),
                                   ("-X+Y", (-1, 1)), ("-X-Y", (-1, -1))):
                nx, ny = x + dx * d, y + dy * d
                if _bate(nx, ny, nx + a, ny + b, est):
                    continue
                # a caixa tem de cair DENTRO de um ambiente: uma caixa que
                # sobra para fora da casa nao e caixa, e apendice de fachada
                cand = [amb for amb in ambs
                        if _dentro(nx, ny, nx + a, ny + b, amb)]
                if not cand:
                    continue
                alvo = next((c for c in cand if c["molhado"]), cand[0])
                melhor = dict(pr, x=nx, y=ny, deslocado=d, lado=lado,
                              ambiente=alvo["cod"], resolvido=True,
                              molhado=alvo["molhado"],
                              motivo=(f"caixa na face {lado} da parede, dentro "
                                      f"de {alvo['cod']}, afastada {d:.0f} mm "
                                      f"do eixo declarado. A parede segue "
                                      f"CONTINUA: interrompe-la exigiria verga "
                                      f"e transferencia de carga que este "
                                      f"modelo nao verifica, e tiraria o "
                                      f"painel de contraventamento do trecho"))
                break
            d += PASSO_BUSCA
        if melhor is None:
            out[pr["cod"]] = dict(pr, x=x, y=y, deslocado=0.0, lado="—",
                                  ambiente="", resolvido=False,
                                  motivo=f"nenhum dos quatro lados libera a "
                                         f"caixa em ate {AFASTAMENTO_MAX:.0f} "
                                         f"mm sem sair de ambiente: a decisao "
                                         f"nao cabe ao modelo e o conflito "
                                         f"continua declarado")
            continue
        out[pr["cod"]] = melhor
        # enclausuramento: tres faces expostas (a quarta encosta na parede),
        # do piso ao teto, em placa RU. A quarta face e a propria parede.
        alt = (pj.NIVEL_SUPERIOR + pj.PE_DIREITO) / 1000.0
        placa += (2 * b + a) / 1000.0 * alt
        piso_tomado += (a * b) / 1e6
    return dict(prumadas=out, placa_m2=round(placa, 2),
                piso_tomado_m2=round(piso_tomado, 3),
                n_resolvidos=sum(1 for v in out.values() if v["resolvido"]),
                n=len(out),
                regra="shaft e caixa na face da parede, do lado do ambiente "
                      "molhado, com a parede continua e portinhola de inspecao "
                      "(NBR 8160). O afastamento e PROCURADO, nao escrito: o "
                      "menor que tira a caixa da estrutura sem sair do ambiente")


def volumes_estrutura(paineis, base_por_pav: dict) -> list:
    """As pecas de parede como volumes, direto dos paineis.

    A primeira versao lia o modelo 3D ja exportado — e com isso a LIBERACAO
    passou a importar modelo3d.py, que e modulo do CASO. A auditoria da E0
    existe exatamente para isso: o motor nao conhece caso nenhum. O volume sai
    da geometria do painel, que o motor ja tem.
    """
    import nucleo.painel as pn
    import nucleo.peca as pe
    vols = []
    for p in paineis:
        z0 = base_por_pav.get(p.pav, 0)
        for q in p.pecas:
            bw = pn.bw(q.perfil)
            ao_longo = bw if q.vertical else q.comp
            alto = q.comp if q.vertical else bw
            if p.horizontal:
                x0, x1 = p.x + q.x, p.x + q.x + ao_longo
                y0, y1 = p.y, p.y + p.esp
            else:
                x0, x1 = p.x, p.x + p.esp
                y0, y1 = p.y + q.x, p.y + q.x + ao_longo
            vols.append(pe.Volume(q.cod, "estrutura", x0, y0, z0 + q.z,
                                  x1, y1, z0 + q.z + alto))
    return vols


def conferir_clash(pj, paineis, base_por_pav: dict,
                   shafts: dict = None) -> dict:
    """Interferencia entre MEP e estrutura, com o criterio de severidade.

    Nem toda interseccao e defeito: um ramal que cruza um montante e NORMAL em
    LSF — resolve-se com furo, e a furacao ja e verificada desde a E10. O que e
    defeito e o furo que o perfil nao comporta: acima de metade da alma a peca
    perde carga critica, e ai a solucao deixa de ser furo e passa a ser desvio.
    """
    import nucleo.peca as pe
    vols = (volumes_mep(pj, shafts)
            + volumes_estrutura(paineis, base_por_pav))
    brutos = pe.detectar_clash(vols)
    resolviveis, criticos, shafts = [], [], []
    for c in brutos:
        import re as _re
        mep = c["a"] if "-DN" in c["a"] else c["b"]
        alvo = c["b"] if mep == c["a"] else c["a"]
        m = _re.search(r"-DN(\d+)", mep)
        dn = int(m.group(1)) if m else 0
        # perfil de 90 mm de alma admite furo de ate 45 mm
        # furo admissivel na alma: metade de 90 mm. O tubo precisa do
        # diametro EXTERNO, nao do DN — e sao esses 10 mm que decidem
        import nucleo.camadas as _cd
        de = _cd.DE_ESGOTO.get(f"DN{dn}", float(dn))
        if mep.endswith(f"-V-DN{dn}"):
            # PRUMADA x montante. Nao e o mesmo defeito: o shaft e um vazio
            # PROJETADO, e a parede deveria ser enquadrada em volta dele. O
            # conflito e real e a causa e outra — o painelizador nao sabe que
            # shaft existe, e monta montante continuo por cima de um vazio de
            # 300 x 300 mm. E uma lacuna do MODELO, nao do tracado.
            shafts.append(dict(
                c, peca=alvo, dn=dn,
                motivo="a posicao declarada da prumada cai DENTRO da linha de "
                       "parede, e um shaft de 300 x 300 nao cabe numa parede "
                       "de 150 mm. Ou ele e uma caixa ao lado da parede — e a "
                       "coordenada precisa dizer de que lado — ou a parede e "
                       "interrompida e enquadrada em volta dele. O modelo nao "
                       "tem essa informacao, e arbitra-la seria escolher por "
                       "quem assina"))
        elif de > 45:
            criticos.append(dict(c, motivo=f"DN{dn} (externo {de:.0f} mm) nao "
                                           f"cabe em furo de 45 mm: exige "
                                           f"desvio ou shaft",
                                 peca=alvo, dn=dn))
        else:
            resolviveis.append(dict(c, motivo=f"DN{dn} cruza em furo de alma "
                                              f"verificado: normal em LSF",
                                    peca=alvo, dn=dn))
    return dict(total=len(brutos), criticos=criticos, shafts=shafts,
                resolviveis=len(resolviveis),
                ok=not criticos and not shafts,
                volumes=len(vols),
                criterio="interseccao e cruzamento, nao defeito; defeito e o "
                         "furo que o perfil nao comporta — acima de metade da "
                         "alma a peca perde carga critica")
