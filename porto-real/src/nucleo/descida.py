"""DESCIDA DE CARGAS — quanto, de verdade, chega em cada montante.

Este arquivo existe porque a verificacao estrutural do projeto repousava sobre
uma constante. Ate R28, a liberacao verificava DOIS montantes tipicos contra uma
carga de 8 kN escrita a mao, e relatava a utilizacao com `min(0.99, ...)` — um
teto que transformava reprovacao em aprovacao. Com trava de 0,99 o item
"perfis aprovados" do checklist nao podia falhar, e um item que nao pode falhar
nao verifica nada: apenas assina.

O que falta a um numero de carga para ser um numero de engenharia:

  1. area de influencia — quanto de laje cada montante sustenta;
  2. o que ha ACIMA — parede do pavimento superior, laje, cobertura;
  3. combinacao normativa — NBR 8681, com permanente favoravel e desfavoravel;
  4. o comprimento destravado real — o blocking existe e muda o Nrd em 2,7x.

Nada aqui e adivinhado em silencio. Toda hipotese de caminho de carga entra em
`hipoteses` no resultado, porque caminho de carga e decisao de projeto, e uma
decisao que ninguem ve nao pode ser contestada por ninguem.

LIMITE DECLARADO, e ele e grande: o modelo NAO SABE a direcao do vigamento.
Sem saber, cada parede recebe meia distancia ate a parede paralela de cada lado
— nas duas direcoes. O resultado e que a soma das faixas de influencia cobre
MAIS que a area do pavimento: no Porto Real, 1,54x no terreo.

Isso e conservador, e conservador nao e desculpa. Um fator de 1,54 que ninguem
escolheu e que ninguem mediu seria exatamente o tipo de numero que este projeto
recusa em toda parte. Entao ele e medido: `cobertura_de_area()` devolve a razao,
a auditoria confere que ela e SEMPRE maior ou igual a 1 (nunca contra a
seguranca) e a declara no relatorio. No dia em que o vigamento entrar no modelo,
a direcao passa a ser conhecida, a razao cai para perto de 1 e a economia
aparece — sobretudo nas jambas, que sao as unicas pecas onde a carga governa.

Nada disto substitui calculo estrutural com ART.
"""
from __future__ import annotations

import nucleo.combinacoes as cb
import nucleo.painel as pn
import nucleo.verificacao as vr

# Vao maximo admitido para a faixa de influencia quando nao ha parede paralela
# de referencia. Nao e um chute de conveniencia: e o limite de vao do vigamento
# LSF corrente, e exceder isto significa que falta uma viga no modelo.
VAO_MAX_LAJE = 4_500.0     # mm


def contexto(paineis, acima_de: dict = None) -> dict:
    """Geometria de influencia de cada painel, como DADO devolvido.

    Ate R32 estes dois valores eram escritos DENTRO do objeto Painel, que
    pertence a outro modulo: `p._influencia` e `p._parede_acima`. Funcionava —
    e escondia uma dependencia temporal. Chamar esforco_por_montante() sem ter
    chamado a funcao que preenche quebrava com AttributeError, e nada na
    assinatura dizia isso. E a mesma classe do `min(0.99, ...)`: funciona ate
    alguem chamar na ordem errada.

    Agora e um dicionario lateral {cod: {...}}, passado como argumento. O
    Painel volta a ser so geometria, e a dependencia aparece onde tem de
    aparecer — na assinatura de quem precisa dela.

    CONVENCAO: `acima_de[pav]` sao os paineis que ficam ACIMA dos paineis
    daquele pavimento. Para o terreo de um sobrado, `acima_de["T"]` sao os
    paineis do superior. Havia duas convencoes para este mesmo parametro no
    arquivo — uma delas indexada pelo pavimento de origem e a outra pelo de
    destino —, e a unificacao so apareceu quando os campos enxertados sairam.
    """
    acima_de = acima_de or {}
    return {p.cod: dict(
        influencia=largura_influencia(p, paineis),
        parede_acima=_tem_parede_acima(p, acima_de.get(p.pav, [])))
        for p in paineis}


def _paralelos(p, paineis) -> list:
    """Paineis paralelos a p cuja projecao se sobrepoe a dele."""
    out = []
    a0, a1 = ((p.x, p.x + p.comp) if p.horizontal else (p.y, p.y + p.comp))
    for q in paineis:
        if q is p or q.horizontal != p.horizontal or q.pav != p.pav:
            continue
        b0, b1 = ((q.x, q.x + q.comp) if q.horizontal else (q.y, q.y + q.comp))
        if min(a1, b1) - max(a0, b0) > 300:      # sobreposicao util
            out.append(q)
    return out


def largura_influencia(p, paineis) -> dict:
    """Faixa de laje que este painel sustenta, em mm, e de onde ela saiu.

    A laje vence de parede a parede: cada uma leva METADE do vao de cada lado.
    Parede externa so recebe de um lado — e por isso uma parede interna
    costuma ser mais carregada que a da fachada, o que contraria a intuicao.
    """
    eixo = (lambda q: q.y) if p.horizontal else (lambda q: q.x)
    meu = eixo(p)
    vizinhos = _paralelos(p, paineis)
    acima = [eixo(q) - meu for q in vizinhos if eixo(q) > meu]
    abaixo = [meu - eixo(q) for q in vizinhos if eixo(q) < meu]
    d1 = min(acima) if acima else None
    d2 = min(abaixo) if abaixo else None
    lados, origem = [], []
    for d, nome in ((d1, "frente"), (d2, "fundo")):
        if d is None:
            if not p.externa:
                # parede interna sem vizinha daquele lado: a laje ainda vence
                # ate alguma coisa, e o limite declarado e o do vigamento
                lados.append(VAO_MAX_LAJE / 2)
                origem.append(f"{nome}: sem parede paralela, "
                              f"vao maximo de vigamento ({VAO_MAX_LAJE:.0f} mm)")
            else:
                origem.append(f"{nome}: face externa, nao recebe laje")
        else:
            lados.append(min(d, VAO_MAX_LAJE) / 2)
            origem.append(f"{nome}: metade de {min(d, VAO_MAX_LAJE):.0f} mm")
    return dict(largura=sum(lados), origem=origem,
                vaos=[d for d in (d1, d2) if d is not None])


def cobertura_de_area(paineis, area_pavimento_m2: float, ctx: dict) -> dict:
    """Quanto da area do pavimento as faixas de influencia cobrem, ao todo.

    Verificacao por caminho independente: a soma de (faixa x comprimento) de
    todas as paredes tem de cobrir a area do pavimento. Abaixo de 1 ha area de
    laje que nao desce por parede nenhuma — carga perdida, e isso e contra a
    seguranca. Acima de 1 ha area contada mais de uma vez — conservador, e o
    quanto precisa estar escrito.
    """
    coberta = sum(ctx[p.cod]["influencia"]["largura"] * p.comp
                  for p in paineis) / 1e6
    razao = coberta / area_pavimento_m2 if area_pavimento_m2 else 0.0
    return dict(coberta_m2=coberta, pavimento_m2=area_pavimento_m2,
                razao=razao,
                seguro=razao >= 1.0,
                leitura=(f"as faixas cobrem {coberta:.1f} m2 para um pavimento "
                         f"de {area_pavimento_m2:.1f} m2 ({razao:.2f}x): "
                         + ("area contada mais de uma vez, porque a direcao do "
                            "vigamento e desconhecida — conservador"
                            if razao >= 1.0 else
                            "HA AREA QUE NAO DESCE POR PAREDE NENHUMA")))


def _tem_parede_acima(p, superiores) -> bool:
    """Existe painel do pavimento de cima apoiado sobre este?"""
    a0, a1 = ((p.x, p.x + p.comp) if p.horizontal else (p.y, p.y + p.comp))
    eixo = (lambda q: q.y) if p.horizontal else (lambda q: q.x)
    meu = eixo(p)
    for q in superiores:
        if q.horizontal != p.horizontal or abs(eixo(q) - meu) > 150:
            continue
        b0, b1 = ((q.x, q.x + q.comp) if q.horizontal else (q.y, q.y + q.comp))
        if min(a1, b1) - max(a0, b0) > 300:
            return True
    return False


def acoes_sobre(p, ctx: dict, cargas: dict, cfg: pn.Config) -> dict:
    """Acoes por metro de parede, separadas por natureza (kN/m).

    Separadas, e nao somadas: a NBR 8681 pondera cada natureza com um gama
    diferente, e o permanente FAVORAVEL (gama 1,0) e o que revela o
    arrancamento. Somar antes de combinar perderia isso.
    """
    c = ctx[p.cod]
    larg_m = c["influencia"]["largura"] / 1000.0
    acima = c["parede_acima"]
    g = q = 0.0
    memoria = []

    # cobertura: chega em toda parede que nao tem parede acima dela
    if not acima:
        g += cargas["cobertura_perm"] * larg_m
        q += cargas["cobertura_acid"] * larg_m
        memoria.append(f"cobertura {cargas['cobertura_perm']:.2f}+"
                       f"{cargas['cobertura_acid']:.2f} kN/m2 x {larg_m:.2f} m")
    else:
        # parede do pavimento superior, a laje que ela sustenta e a cobertura
        # que chega nela — tudo desce por esta parede
        g += cargas["parede_lsf_m"] * (cfg.altura / 1000.0)
        g += cargas["piso_lsf_perm"] * larg_m
        q += cargas["piso_lsf_acid"] * larg_m
        g += cargas["cobertura_perm"] * larg_m
        q += cargas["cobertura_acid"] * larg_m
        memoria.append(f"parede superior {cargas['parede_lsf_m']:.2f} kN/m2 x "
                       f"{cfg.altura/1000:.2f} m")
        memoria.append(f"piso superior {cargas['piso_lsf_perm']:.2f}+"
                       f"{cargas['piso_lsf_acid']:.2f} kN/m2 x {larg_m:.2f} m")
        memoria.append(f"cobertura sobre a parede de cima, {larg_m:.2f} m")

    # peso proprio da propria parede
    g += cargas["parede_lsf_m"] * (cfg.altura / 1000.0)
    memoria.append(f"peso proprio {cargas['parede_lsf_m']:.2f} kN/m2 x "
                   f"{cfg.altura/1000:.2f} m")
    return dict(g=g, q=q, memoria=memoria)


def esforco_por_montante(p, ctx: dict, cargas: dict, cfg: pn.Config,
                         combs: list = None) -> dict:
    """N de calculo no montante mais carregado, pela combinacao que governa.

    A largura de influencia do MONTANTE e a modulacao — exceto junto a uma
    abertura, onde o king stud recebe tambem metade do vao, porque a verga
    entrega ali tudo o que ela colheu. E o king stud, nao o montante corrente,
    o que costuma governar um painel com abertura.
    """
    combs = combs or cb.gerar([("g", "permanente"), ("q", "acidental")],
                              {"q": "acidental"})
    a = acoes_sobre(p, ctx, cargas, cfg)
    mod_m = cfg.modulacao / 1000.0

    # o king stud mais solicitado: metade do maior vao de abertura, de cada lado
    maior_vao = max((ab["larg"] for ab in p.aberturas), default=0) / 1000.0
    larg_king = mod_m / 2 + maior_vao / 2

    saida = {}
    for nome, larg in (("montante", mod_m), ("king stud", larg_king)):
        if larg <= 0:
            continue
        pior, qual = 0.0, None
        for c in combs:
            if c.tipo != "ELU":
                continue
            n = (c.fator("g") * a["g"] + c.fator("q") * a["q"]) * larg
            if n > pior:
                pior, qual = n, c
        saida[nome] = dict(nsd=pior, combinacao=qual.cod if qual else "",
                           descricao=str(qual) if qual else "",
                           largura_m=larg)
    return dict(por_familia=saida, g=a["g"], q=a["q"], memoria=a["memoria"])


def travamento(p, cfg: pn.Config) -> dict:
    """Comprimento destravado real do montante, e por que ele e esse.

    O blocking nao e decoracao: ele divide o comprimento de flambagem em torno
    do eixo fraco e da torcao. Passar k = 0,5 a mao seria supor o blocking; aqui
    o k SAI do blocking que o painel de fato tem.
    """
    zs = sorted({q.z for q in p.pecas if q.familia == "blocking"})
    if not zs:
        return dict(k=1.0, l_destravado=p.altura, motivo="sem blocking")
    cortes = [0] + zs + [p.altura]
    maior = max(b - a for a, b in zip(cortes, cortes[1:]))
    return dict(k=maior / p.altura, l_destravado=maior,
                motivo=f"{len(zs)} blocking em z = {zs}")


def dimensionar(paineis_por_pav: dict, aco, cargas: dict, cfg: pn.Config = None,
                perfis=None) -> dict:
    """As duas passadas, num lugar so — e este e o lugar.

    Enquanto a segunda passada morava na liberacao, quem chamava painelizar()
    direto (a auditoria, um teste, um script) recebia o painel SEM a jamba
    dimensionada e verificava outra coisa que nao o produto. Auditoria e
    produto divergirem e o defeito que este projeto passa o tempo todo
    encontrando; nao faz sentido cria-lo aqui.
    """
    import nucleo.perfis as _pf
    cfg = cfg or pn.Config()
    perfis = perfis or list(_pf.catalogo())
    todos = [p for v in paineis_por_pav.values() for p in v]
    ctx = contexto(todos, dict(T=paineis_por_pav.get("S", []), S=[]))
    jambas, apertadas = {}, []
    for p in todos:
        e = esforco_por_montante(p, ctx, cargas, cfg)
        alvo = e["por_familia"].get("king stud") or e["por_familia"]["montante"]
        r = pn.dimensionar_jambas(p, alvo["nsd"], aco, cfg, perfis)
        if r:
            jambas[p.cod] = r
            if r["escolha"] and r["escolha"]["u"] > cfg.u_alvo:
                apertadas.append((p.cod, r["escolha"]["solucao"],
                                  r["escolha"]["u"]))
    return dict(jambas=jambas, apertadas=apertadas, paineis=todos, ctx=ctx)


def verificar(paineis, superiores_por_pav: dict, perfis: dict, aco,
              cargas: dict, cfg: pn.Config = None) -> dict:
    """Verifica TODOS os montantes do projeto, um a um.

    `perfis` mapeia cod -> objeto de perfil. Devolve a lista completa de
    utilizacoes, a peca que governa e as que reprovam. Sem teto: uma utilizacao
    de 1,47 sai 1,47. Foi um `min(0.99, ...)` que manteve o projeto liberado
    enquanto um montante estava 47 % sobrecarregado.
    """
    cfg = cfg or pn.Config()
    combs = cb.gerar([("g", "permanente"), ("q", "acidental")],
                     {"q": "acidental"})
    itens, hipoteses = [], [
        "laje armada em uma direcao, apoiada nas paredes paralelas mais proximas",
        f"vao de vigamento limitado a {VAO_MAX_LAJE:.0f} mm onde nao ha parede "
        f"paralela — acima disso falta viga no modelo",
        "parede externa recebe laje de um lado so",
        "toda parede e portante: o modelo ainda nao distingue portante de "
        "divisoria, e supor o contrario seria contra a seguranca",
        "k de flambagem derivado do blocking existente, nao arbitrado",
        "direcao do vigamento desconhecida: cada parede recebe dos dois lados, "
        "e a area total desce mais de uma vez — o fator esta medido em "
        "cobertura_de_area(), nao suposto",
    ]
    ctx = contexto(paineis, superiores_por_pav)
    for p in paineis:
        esf = esforco_por_montante(p, ctx, cargas, cfg, combs)
        tr = travamento(p, cfg)
        for q in p.pecas:
            if q.familia not in ("stud", "king stud", "jack stud"):
                continue
            perfil = perfis.get(q.perfil)
            if perfil is None:
                continue
            chave = "king stud" if q.familia != "stud" else "montante"
            dado = esf["por_familia"].get(chave) or esf["por_familia"]["montante"]
            # o jack stud e mais curto: destravado so no trecho que existe
            k = tr["k"] if q.comp >= p.altura - 1 else min(1.0, tr["k"])
            c = vr.compressao(perfil, aco, L=q.comp, kx=1.0, ky=k, kz=k)
            u = dado["nsd"] / c["nrd"] if c["nrd"] > 0 else float("inf")
            itens.append(dict(
                peca=q.cod, painel=p.cod, familia=q.familia, perfil=q.perfil,
                comp=q.comp, nsd=dado["nsd"], nrd=c["nrd"], u=u,
                modo=c["modo"], k=k, l_destravado=k * q.comp,
                combinacao=dado["combinacao"], largura_m=dado["largura_m"]))

    itens.sort(key=lambda d: -d["u"])
    reprovadas = [d for d in itens if d["u"] > 1.0]
    return dict(itens=itens, n=len(itens), reprovadas=reprovadas, ctx=ctx,
                utilizacoes=[d["u"] for d in itens],
                governa=itens[0] if itens else None,
                hipoteses=hipoteses,
                aprovado=not reprovadas)
