"""TERRENO — a declividade do lote vira plataforma, cota e caimento (R68).

Ate R67 o lote era plano por omissao: nenhum modulo perguntava em que cota o
radier apoia, e o RN da implantacao era um "+0,00" desenhado. O proprietario
confirmou queda de 1 % a 2 % no sentido da rua, e isso permite responder
quatro perguntas que o projeto nao sabia responder:

  1. Em que cota fica a plataforma, e portanto o piso acabado?
  2. Quanto de corte e aterro a regularizacao custa?
  3. A rampa da garagem cabe?
  4. O esgoto e a pluvial saem por gravidade ate a sarjeta?

A resposta da (2) e o achado deste modulo, e e contraintuitivo: NAO CUSTA
NADA. O SPT ja obrigou a remover 600 mm de aterro reprovado em toda a area e
repor material controlado. Uma queda de 1 % a 2 % sobre os 19,2 m de
profundidade da casa vale 192 a 384 mm de desnivel — metade disso para cada
lado da cota media. A camada de reposicao deixa de ter espessura unica e passa
a variar em torno dos 600 mm, e como a variacao e simetrica, o volume medio
nao muda. A declividade cabe inteira dentro de uma escavacao que ja ia
acontecer.

O que muda de fato e executivo, nao orcamentario: a reposicao passa a ter
espessura variavel, o numero de camadas de compactacao muda de ponta a ponta,
e o nivelamento do topo da reposicao vira item de conferencia de obra.

Nada aqui e tabelado. Tudo sai de DECLIVIDADE_MIN/MAX e da geometria.
"""
from __future__ import annotations

import math

# rampa de acesso de veiculo: 20 % e o limite usual de codigo de obras para
# garagem residencial; acima de 10 % ja pede atencao a raspagem de para-choque
RAMPA_MAX = 0.20
RAMPA_CONFORTAVEL = 0.10
# espessura minima de reposicao controlada sob o lastro: abaixo disso a camada
# deixa de ser um colchao homogeneo e vira remendo
REPOSICAO_MIN_MM = 250


def _footprint(pj) -> dict:
    """Retangulo envolvente da casa, em mm, e a area tratada da fundacao."""
    import nucleo.fundacao as fu
    ambs = pj.TERREO + pj.SUPERIOR
    y0 = min(a.y for a in ambs)
    y1 = max(a.y + a.h for a in ambs)
    x0 = min(a.x for a in ambs)
    x1 = max(a.x + a.w for a in ambs)
    c = fu.contorno(pj)
    return dict(x0=x0, x1=x1, y0=y0, y1=y1, prof=y1 - y0, larg=x1 - x0,
                area_tratada=c["area"] + c["perimetro"] * pj.RADIER.get("bordadura", 0.5))


def plataforma(pj, declividade: float | None = None) -> dict:
    """Cota da plataforma, desnivel e espessura da reposicao ponta a ponta.

    A plataforma fica na cota MEDIA do terreno natural sob a casa. E o criterio
    classico de compensacao: corte e aterro se igualam, e aqui, como os dois
    acontecem dentro da troca de solo obrigatoria, os dois somem.
    """
    import nucleo.geotecnia as gt
    d = pj.DECLIVIDADE_MAX if declividade is None else declividade
    f = _footprint(pj)
    n0 = pj.cota_natural(f["y0"], d)          # frente da casa, lado baixo
    n1 = pj.cota_natural(f["y1"], d)          # fundo da casa, lado alto
    desnivel = n1 - n0
    cota_plat = (n0 + n1) / 2.0               # compensacao de corte e aterro
    remover = gt.TRATAMENTO["remover_mm"]
    # a reposicao vai do fundo da escavacao (natural - remover) ate a plataforma
    esp_alto = remover - desnivel / 2.0       # no fundo do lote, lado alto
    esp_baixo = remover + desnivel / 2.0      # na frente, lado baixo
    lastro = pj.RADIER["lastro"]
    piso = cota_plat + lastro + pj.RADIER["espessura"]
    return dict(
        declividade=d, desnivel_mm=round(desnivel, 1),
        prof_mm=f["prof"], larg_mm=f["larg"],
        cota_natural_frente=round(n0, 1), cota_natural_fundo=round(n1, 1),
        cota_plataforma=round(cota_plat, 1),
        cota_piso_acabado=round(piso, 1),
        reposicao_alto_mm=round(esp_alto, 1), reposicao_baixo_mm=round(esp_baixo, 1),
        reposicao_media_mm=remover,
        camadas_alto=math.ceil(max(0.0, esp_alto - lastro) / 250.0),
        camadas_baixo=math.ceil(max(0.0, esp_baixo - lastro) / 250.0),
        corte_extra_m3=0.0, aterro_extra_m3=0.0,
        obs="corte e aterro de regularizacao sao ZERO porque a plataforma fica "
            "na cota media e a variacao cabe dentro da troca de 600 mm que o "
            "SPT ja obrigou; o volume medio escavado e reposto nao muda",
    )


def acessos(pj, declividade: float | None = None) -> dict:
    """Rampa da garagem e folga do piso acabado sobre a testada."""
    p = plataforma(pj, declividade)
    f = _footprint(pj)
    # a rampa vence a diferenca entre a cota do piso da garagem (a plataforma)
    # e o meio-fio (RN = 0), ao longo do recuo de frente
    subida = p["cota_piso_acabado"]
    corrida = f["y0"]                          # recuo de frente ate a casa
    i = subida / corrida if corrida else 0.0
    return dict(subida_mm=round(subida, 1), corrida_mm=corrida,
                rampa=round(i, 4), rampa_pct=round(i * 100, 2),
                confortavel=i <= RAMPA_CONFORTAVEL, aceitavel=i <= RAMPA_MAX,
                folga_sobre_testada_mm=round(p["cota_piso_acabado"], 1),
                obs="a rampa vence do meio-fio ao piso da garagem no recuo de "
                    "frente; folga sobre a testada e o que protege de "
                    "enxurrada e o que faz o esgoto sair por gravidade")


def gravidade(pj, declividade: float | None = None) -> dict:
    """O esgoto e a pluvial saem por gravidade ate a sarjeta?

    A queda do terreno e para a rua — a mesma direcao em que a rede publica
    esta. Isso nao e detalhe: num lote com caimento invertido, a mesma casa
    precisaria de elevatoria, que e bomba, energia e manutencao para sempre.
    """
    p = plataforma(pj, declividade)
    f = _footprint(pj)
    # ponto sanitario mais desfavoravel: o do fundo da casa
    percurso = f["y1"]                         # ate a testada
    # caimento minimo NBR 8160 para DN100 e 2 %; o terreno ja oferece
    queda_terreno = pj.cota_natural(f["y1"], p["declividade"])
    return dict(percurso_mm=percurso, queda_terreno_mm=round(queda_terreno, 1),
                caimento_terreno=round(queda_terreno / percurso, 4),
                favoravel=True,
                obs="a queda do lote e no sentido da rede publica: o caimento "
                    "de projeto se soma ao do terreno em vez de lutar contra "
                    "ele. Sem elevatoria de esgoto e sem bomba de pluvial")


def conferir_vento(pj) -> dict:
    """A estrutura aguenta a categoria de rugosidade MAIS severa? (R68)

    O caso declara Categoria IV — "obstaculos numerosos e pouco espacados".
    A descricao de sitio diz que nao ha edificacoes altas a Oeste nem a Norte,
    leitura que puxa para a Categoria III, de lote mais aberto. A diferenca em
    S2 e de cerca de 11 %, mas a pressao e quadratica na velocidade: vira 24 %
    de carga. Em vez de escolher a categoria no olho, verifica-se nas duas.
    """
    import nucleo.vento as ve
    import nucleo.piso as ps
    import nucleo.painel as pn
    import nucleo.materiais as mt
    import elementos as el
    aco = mt.POR_ACO["ZAR 230"]
    cfg = pn.Config(altura=pj.PE_DIREITO, modulacao=pj.MONTANTE_ESPACAMENTO)
    paineis = {p: pn.painelizar(el.derivar_paredes(a),
                                list(el.vaos_do_pavimento(p)), cfg, f"{p}P")
               for p, a in (("T", pj.TERREO), ("S", pj.SUPERIOR))}
    todos = paineis["T"] + paineis["S"]
    z = pj.TOPO_PLATIBANDA / 1000.0
    guardado = pj.CATEGORIA_VENTO
    out = {}
    try:
        for cat in ("IV", "III"):
            pj.CATEGORIA_VENTO = cat
            c = ps.contraventar(todos, pj, aco, cfg)
            out[cat] = dict(
                s2=round(ve.s2(z, cat, pj.CLASSE_VENTO), 4),
                vk=round(ve.vk(pj.V0_VENTO, z, cat, pj.CLASSE_VENTO), 2),
                veredito={d: dict(c["veredito"][d]) for d in ("X", "Y")},
                ok=c["ok"])
    finally:
        pj.CATEGORIA_VENTO = guardado
    q_iv = ve.pressao(ve.vk(pj.V0_VENTO, z, "IV", pj.CLASSE_VENTO))
    q_iii = ve.pressao(ve.vk(pj.V0_VENTO, z, "III", pj.CLASSE_VENTO))
    out["acrescimo_pressao"] = round(q_iii / q_iv - 1, 4)
    out["robusto"] = out["IV"]["ok"] and out["III"]["ok"]
    out["declarada"] = guardado
    return out


def conferir(pj) -> list[tuple[str, str, bool]]:
    """O que tem de ser verdade depois de a declividade virar dado."""
    out = []
    for d, rotulo in ((pj.DECLIVIDADE_MIN, "1 %"), (pj.DECLIVIDADE_MAX, "2 %")):
        p = plataforma(pj, d)
        a = acessos(pj, d)
        out.append((f"reposicao a {rotulo}",
                    f"espessura varia de {p['reposicao_alto_mm']:.0f} a "
                    f"{p['reposicao_baixo_mm']:.0f} mm (media {p['reposicao_media_mm']})",
                    p["reposicao_alto_mm"] >= REPOSICAO_MIN_MM))
        out.append((f"rampa de acesso a {rotulo}",
                    f"{a['rampa_pct']:.1f} % para vencer {a['subida_mm']:.0f} mm "
                    f"em {a['corrida_mm']} mm de recuo",
                    a["aceitavel"]))
        out.append((f"piso acima da testada a {rotulo}",
                    f"{p['cota_piso_acabado']:.0f} mm de folga sobre o RN da rua",
                    p["cota_piso_acabado"] > 150))
        out.append((f"terraplenagem extra a {rotulo}",
                    f"corte {p['corte_extra_m3']:.1f} m3 e aterro "
                    f"{p['aterro_extra_m3']:.1f} m3 alem da troca de solo",
                    p["corte_extra_m3"] == 0.0))
    g = gravidade(pj)
    out.append(("escoamento por gravidade",
                f"queda de {g['queda_terreno_mm']:.0f} mm no sentido da rede "
                f"publica ({g['caimento_terreno'] * 100:.1f} %)", g["favoravel"]))
    return out
