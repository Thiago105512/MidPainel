"""COTACAO — do preco (H) ao preco que alguem assina.

Todo preco deste projeto e (H) desde a primeira revisao, e sempre esteve
marcado como tal. A pergunta "da para incluir cotacao dos materiais?" tem uma
resposta que nao e sim nem nao: depende de qual das TRES coisas se chama de
cotacao, e cada uma exige algo diferente.

  NIVEL 0  (H)          numero arbitrado para a estrutura do calculo existir.
                        E o que ha hoje. Serve para auditar quantidade, nunca
                        para fechar contrato.
  NIVEL 1  REFERENCIA   tabela publica com data e origem — SINAPI do Amazonas
                        no mes X, tabela de preco de catalogo do fabricante.
                        Rastreavel, nao vinculante. Erra por regiao e por lote.
  NIVEL 2  COTADO       proposta de um fornecedor NOMEADO, com data, validade,
                        prazo de entrega e condicao de pagamento. Vinculante
                        enquanto vale.
  NIVEL 3  CONTRATADO   pedido colocado. O preco deixa de ser estimativa.

O QUE ESTE MODULO FAZ, e o que ele explicitamente nao faz. Ele monta o MAPA DE
COTACAO — a pergunta que se manda ao fornecedor —, recebe a resposta, valida,
compara e substitui. Ele nao inventa preco, nao busca preco na internet e nao
converte (H) em referencia por decreto. O numero entra pela porta do contrato
ERP da E23, que ja existe desde R27 com o esquema pronto e a frase que resume
tudo: "preco sem data nao e preco".

POR QUE O MAPA E A PARTE DIFICIL. Uma cotacao nao se pede com quantidade: se
pede com ESPECIFICACAO. "Chapa de gesso, 675 m2" nao e cotavel — falta
espessura, borda, formato e norma. Montar o mapa obriga o modelo a responder,
item por item, o que exatamente se esta comprando; e a linha que nao souber
responder aparece como LACUNA, que e informacao melhor que um preco bonito.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Ordem de confianca. Um nivel mais alto sempre prevalece sobre um mais baixo;
# entre iguais decide a data, e nunca o valor — escolher pelo menor preco entre
# fontes de niveis diferentes e como comparar orcamento com boato.
NIVEIS = ("H", "REFERENCIA", "COTADO", "CONTRATADO")
ORDEM = {n: i for i, n in enumerate(NIVEIS)}

# Uma proposta so e comparavel com outras se houver outras. Tres e o minimo de
# praxe em compra privada e o exigido em compra publica (Lei 14.133, art. 23).
MIN_PROPOSTAS = 3


@dataclass(frozen=True)
class Cotacao:
    """Uma proposta, de um fornecedor, para um SKU, numa data.

    `cotado_em` e `validade_dias` nao sao burocracia: aco laminado e perfil
    formado a frio oscilam com bobina e cambio, e uma proposta de 90 dias atras
    nao e um preco — e uma lembranca.
    """
    sku: str
    fornecedor: str
    preco: float
    unidade: str
    cotado_em: str                 # ISO: AAAA-MM-DD
    moeda: str = "BRL"
    validade_dias: int = 30
    lead_time_dias: int = 0
    frete_incluso: bool = False
    condicao: str = ""             # pagamento
    documento: str = ""            # numero da proposta, para rastrear
    nivel: str = "COTADO"
    obs: str = ""


def _dias(a: str, b: str) -> int:
    """Diferenca em dias entre duas datas ISO, sem dependencia externa."""
    from datetime import date
    try:
        ya, ma, da = (int(x) for x in a.split("-"))
        yb, mb, db = (int(x) for x in b.split("-"))
    except (ValueError, AttributeError):
        return -10_000
    return (date(yb, mb, db) - date(ya, ma, da)).days


# ---------------------------------------------------------------------------
# ESPECIFICACAO — o que o fornecedor precisa saber para responder um numero
# ---------------------------------------------------------------------------
DEMAOS_PINTURA = 2
def especificar(item, r: dict) -> dict:
    """Traduz uma linha de BOM no que se pede numa cotacao.

    Nada aqui e digitado: norma e formato vem do material, designacao vem do
    perfil, DN vem do levantamento de instalacoes, fck e taxa vem da fundacao.
    Onde o modelo nao tiver o que dizer, a linha sai SEM especificacao — e essa
    e a resposta util, porque comprar sem especificar e como o preco vira
    surpresa na entrega.
    """
    import nucleo.materiais as mt
    sku = item.sku
    esp, normas, faltas = [], [], []

    if sku == "ACO-PERF":
        aco = mt.POR_ACO.get("ZAR 230")
        pl = r.get("plano") or {}
        esp.append("perfil formado a frio em barra de 6.000 mm")
        if aco:
            esp.append(f"aco {aco.cod}, fy {aco.fy} MPa, fu {aco.fu} MPa")
            esp.append(f"revestimento {getattr(aco, 'revestimento', 'Z275')}")
        esp.append(f"massa BRUTA, ja com a perda de corte "
                   f"({(1 - pl.get('aproveitamento', 0)) * 100:.1f} %)")
        normas += ["NBR 15253", "NBR 14762", "NBR 7008"]

    elif sku.startswith("PF-"):
        esp.append(f"peca cortada e furada conforme {sku[3:]}")
        esp.append("rota ALTERNATIVA a barra: cotar peca pronta so faz sentido "
                   "contra o custo de corte proprio")
        normas += ["NBR 15253"]

    elif sku.startswith(("PAR-EST", "PAR-PLA")):
        js = r.get("juntas") or {}
        tipos = sorted({x["parafuso"] for j in js.values()
                        for x in j["juntas"]})
        if tipos:
            esp.append("tipos em uso: " + ", ".join(tipos))
        else:
            faltas.append("tipo de parafuso por junta")
        normas += ["NBR 14762 item 8.4"]

    elif "-" in sku and sku.split("-")[0] in mt.POR_MATERIAL:
        cod = sku.split("-")[0]
        m = mt.POR_MATERIAL[cod]
        esp.append(m.nome)
        if m.chapa:
            esp.append(f"chapa {m.chapa[0]} x {m.chapa[1]} mm")
        else:
            faltas.append("formato comercial")
        parte = sku.split("-", 1)[1].replace(",", ".")
        esp.append(f"espessura {parte} mm")
        if m.norma:
            normas.append(m.norma)
        else:
            faltas.append("norma do material")

    elif sku in ("FITA", "MASSA", "CANT", "PLACA"):
        rotulo = {"FITA": "fita de papel microperfurada para junta",
                  "MASSA": "massa para junta, aplicacao em 3 demaos",
                  "CANT": "cantoneira de canto e arremate",
                  "PLACA": "placa inteira, por formato — rota alternativa a "
                           "compra por m2"}[sku]
        esp.append(rotulo)
        pg = (r.get("camadas") or {}).get("paginacao") or {}
        if sku == "PLACA" and pg.get("itens"):
            esp.append("formatos: " + ", ".join(
                sorted({str(x.get("formato")) for x in pg["itens"]})))
        # o rendimento e o que transforma metro de junta em rolo e em balde, e
        # o modelo nao o tem: comprar fita em metro linear e comprar rolo sao
        # perguntas diferentes para o fornecedor
        if sku in ("FITA", "MASSA"):
            faltas.append("rendimento da embalagem (metros por rolo, metros "
                          "por balde): o modelo mede COMPRIMENTO de junta, "
                          "nao embalagem")
        normas += ["NBR 15758"]

    elif sku.startswith("FER-"):
        esp.append("ferragem de esquadria conforme quadro de vaos")
        esp.append("acabamento e sentido de abertura por vao")
        faltas.append("linha e fabricante da ferragem: a norma de desempenho "
                      "e do SISTEMA esquadria + ferragem, e cotar ferragem "
                      "solta nao garante o ensaio")
        normas += ["NBR 10821"]

    elif sku.startswith("MEP-"):
        esp.append("tubo, conexao ou condutor conforme descricao")
        dn = "".join(c for c in sku if c.isdigit())
        if dn:
            esp.append(f"DN{dn}")
        normas += ["NBR 5626", "NBR 8160", "NBR 5410"]

    elif sku.startswith("FUN-"):
        f = (r.get("camadas") or {}).get("fundacao") or {}
        if f:
            esp.append(f"fck {f.get('fck', '?')} MPa, aco {f.get('aco', '?')}, "
                       f"tela {f.get('tela', '?')}")
            esp.append("(H) ate a sondagem: a especificacao muda com o laudo")
        normas += ["NBR 6118", "NBR 6122", "NBR 12655"]

    elif sku.startswith("ESQ-"):
        e = (r.get("camadas") or {}).get("esquadrias") or {}
        esp.append("caixilho de aluminio com desempenho ENSAIADO do sistema")
        faltas.append("classificacao de estanqueidade a agua, ao ar e a carga "
                      "de vento — exige relatorio de ensaio, nunca valor")
        normas += ["NBR 10821"]
        if e.get("area_vidro"):
            esp.append(f"vidro conforme quadro, {e['area_vidro']} m2")

    elif sku.startswith("COB-") or sku == "IMP-MANTA":
        esp.append("chapa dobrada / manta conforme descricao")
        normas += ["NBR 10844", "NBR 9575"]

    elif sku.startswith("MO-"):
        esp.append("hora de equipe, com encargos e EPI")
        faltas.append("convencao coletiva vigente e composicao de encargos")

    elif sku.startswith(("LOU-", "MET-")):
        esp.append("louca / metal sanitario de linha comercial, cor branca "
                   "para louca e acabamento cromado para metal")
        esp.append("quantidade contada das pecas LOCADAS em planta, nao "
                   "estimada por comodo")
        faltas.append("linha e fabricante: louca e metal sao decisao de "
                      "acabamento do proprietario, e a mesma peca varia 3x de "
                      "preco entre linhas")
        normas += ["NBR 15097", "NBR 15705"]

    elif sku.startswith("ELE-"):
        esp.append("dispositivo de embutir em caixa 4x2 / 4x4, linha unica "
                   "em toda a casa")
        tens = ((r.get("eletrica") or {}).get("tensao") or {}).get(
            "esquema", "esquema declarado no projeto")
        esp.append(f"tensao 127 V para TUG e 220 V para TUE, conforme {tens}")
        normas += ["NBR 5410", "NBR 14136"]

    elif sku.startswith("EQP-"):
        esp.append("equipamento novo, com garantia de fabrica e instalacao "
                   "por credenciado")
        if "SPLIT" in sku:
            esp.append("inverter, ciclo frio, R-32 ou R-410A, classe A")
            normas += ["NBR 16401", "Portaria INMETRO de eficiencia"]
        faltas.append("marca e modelo: a capacidade esta dimensionada, a "
                      "escolha do equipamento e do proprietario")

    elif sku.startswith("MAR-"):
        esp.append("marcenaria sob medida conforme planta de layout")
        esp.append("MDF 18 mm com acabamento em laminado ou pintura PU; "
                   "ferragem com amortecedor")
        faltas.append("desenho executivo de marcenaria: a planta da a "
                      "extensao e a profundidade, nao o interior do movel")

    elif sku.startswith("FAC-"):
        if sku == "FAC-MINERAL":
            esp.append("placa cimenticia 1.200 x 2.400 com revestimento mineral "
                       "aplicado em fabrica, cor clara, junta seca de 6 mm com "
                       "perfil EPDM — face externa do volume superior e da platibanda")
            faltas.append("fabricante e linha do revestimento mineral: acabamento "
                          "de fachada e decisao do proprietario")
        else:
            esp.append("sistema de fachada sobre placa cimenticia: basecoat com "
                       "tela de fibra de vidro alcali-resistente, junta com "
                       "selante PU, acabamento acrilico elastomerico LISO com "
                       "biocida — faixa ate 2.600 mm e face interna da platibanda")
        normas += ["NBR 15498", "NBR 13245"]

    elif sku.startswith("FOR-"):
        esp.append("perfilaria de forro em aco galvanizado, malha 600 x 1.200, "
                   "pendural regulavel; tabica perimetral de sombra")
        normas += ["NBR 15758-2"]

    elif sku.startswith("LUM-"):
        esp.append("luminaria LED de linha, IRC >= 80 (>= 90 no closet), "
                   "eficacia >= 80 lm/W, driver com garantia >= 3 anos")
        esp.append("temperatura de cor por ambiente conforme o quadro "
                   "luminotecnico: 2.700 K intimo, 3.000 K social, 4.000 K tarefa")
        esp.append("quantidade pelo METODO DOS LUMENS por ambiente e malha de "
                   "uniformidade (SHR 1,2); tarefa contada das pecas")
        faltas.append("marca e modelo: o fluxo e a potencia de cada tipo estao "
                      "declarados; o produto e escolha de acabamento")
        normas += ["NBR ISO/CIE 8995-1", "Portaria INMETRO 20/2017 (LED)"]

    elif sku.startswith("PIN-"):
        esp.append("tinta e mao de obra conforme especificacao de acabamento")
        esp.append(f"{DEMAOS_PINTURA} demaos sobre selador; rendimento "
                   f"declarado na quantidade")
        normas += ["NBR 11702", "NBR 13245"]

    elif sku.startswith("REV-"):
        esp.append("revestimento ceramico conforme quadro de acabamentos por "
                   "ambiente")
        esp.append("area ja com 10 % de perda de corte e quebra")
        faltas.append("linha, formato e PEI: o modelo define o TIPO por "
                      "ambiente, a linha e escolha de acabamento")
        normas += ["NBR 13818", "NBR 15463"]

    else:
        faltas.append("o modelo nao sabe descrever este item para um "
                      "fornecedor")

    return dict(sku=sku, descricao=item.descricao, unidade=item.unidade,
                quantidade=round(item.quantidade, 2),
                compra=item.compra,
                especificacao="; ".join(esp),
                normas=sorted(set(normas)), lacunas=faltas,
                cotavel=bool(esp) and not any(
                    "nao sabe descrever" in x for x in faltas))


def mapa(r: dict) -> dict:
    """O documento que se manda ao fornecedor.

    So o que se COMPRA entra como pedido de preco. A linha de producao entra
    como rota alternativa, marcada, porque cotar peca cortada faz sentido — e
    somar as duas nao.
    """
    itens = r["bom"]
    linhas = [especificar(i, r) for i in itens]
    compra = [l for l in linhas if l["compra"]]
    alternativa = [l for l in linhas if not l["compra"]]
    lacunas = [l for l in compra if l["lacunas"]]
    return dict(
        linhas=compra, alternativas=alternativa,
        n=len(compra), n_alternativas=len(alternativa),
        lacunas=[dict(sku=l["sku"], faltam=l["lacunas"]) for l in lacunas],
        n_lacunas=len(lacunas),
        cotaveis=sum(1 for l in compra if l["cotavel"] and not l["lacunas"]),
        instrucao="preco unitario por unidade indicada, em BRL, com data, "
                  "validade, prazo de entrega e se o frete esta incluso. "
                  "Proposta sem data nao entra na comparacao",
        min_propostas=MIN_PROPOSTAS)


# ---------------------------------------------------------------------------
# RECEBER — a porta. Tudo o que entra e validado antes de virar preco
# ---------------------------------------------------------------------------
def receber(cotacoes: list, itens: list, hoje: str) -> dict:
    """Valida proposta a proposta contra o BOM e contra o calendario."""
    por_sku = {}
    for i in itens:
        por_sku.setdefault(i.sku, i)
    aceitas, recusadas = [], []
    for c in cotacoes:
        motivos = []
        alvo = por_sku.get(c.sku)
        if alvo is None:
            motivos.append("SKU nao existe no BOM: a chave esta errada, ou o "
                           "fornecedor cotou outra coisa")
        elif c.unidade != alvo.unidade:
            motivos.append(f"unidade {c.unidade} contra {alvo.unidade} do BOM: "
                           f"preco por unidade diferente nao e comparavel")
        if c.preco <= 0:
            motivos.append("preco nao positivo")
        if c.nivel not in NIVEIS:
            motivos.append(f"nivel '{c.nivel}' desconhecido")
        idade = _dias(c.cotado_em, hoje)
        if idade < -9_000:
            motivos.append("data ausente ou malformada: preco sem data nao e "
                           "preco")
        elif idade < 0:
            motivos.append("cotada no futuro")
        elif c.nivel in ("COTADO", "CONTRATADO") and idade > c.validade_dias:
            motivos.append(f"vencida ha {idade - c.validade_dias} dia(s): "
                           f"validade de {c.validade_dias}")
        if c.moeda != "BRL":
            motivos.append(f"moeda {c.moeda} sem taxa de conversao declarada")
        (recusadas if motivos else aceitas).append(
            dict(cotacao=c, motivos=motivos, idade_dias=idade))
    return dict(aceitas=aceitas, recusadas=recusadas,
                n=len(cotacoes), n_aceitas=len(aceitas),
                ok=bool(aceitas) and not recusadas)


def comparar(aceitas: list, min_propostas: int = MIN_PROPOSTAS) -> dict:
    """Agrupa por SKU e diz o que a comparacao permite concluir.

    Uma proposta unica nao e cotacao: e um preco. A diferenca importa porque o
    spread entre propostas e a unica medida de mercado que uma compra privada
    consegue produzir sem tabela publica.
    """
    por_sku = {}
    for a in aceitas:
        por_sku.setdefault(a["cotacao"].sku, []).append(a["cotacao"])
    out = []
    for sku, cs in sorted(por_sku.items()):
        cs = sorted(cs, key=lambda c: c.preco)
        menor, maior = cs[0], cs[-1]
        spread = (maior.preco / menor.preco - 1) if menor.preco else 0.0
        out.append(dict(
            sku=sku, n=len(cs), menor=menor.preco, maior=maior.preco,
            spread=round(spread, 4),
            escolhido=menor.fornecedor, preco=menor.preco,
            lead_time_dias=menor.lead_time_dias,
            competitiva=len(cs) >= min_propostas,
            criterio="menor preco valido na data; empate decide por prazo de "
                     "entrega. O criterio e declarado porque 'melhor proposta' "
                     "sem regra e escolha, nao comparacao",
            propostas=[dict(fornecedor=c.fornecedor, preco=c.preco,
                            cotado_em=c.cotado_em,
                            lead_time_dias=c.lead_time_dias,
                            frete_incluso=c.frete_incluso) for c in cs]))
    return dict(itens=out, n=len(out),
                competitivos=sum(1 for x in out if x["competitiva"]),
                min_propostas=min_propostas)


def aplicar(itens: list, comparacao: dict) -> dict:
    """Troca o preco (H) pelo cotado, item a item, sem tocar na quantidade.

    O aceite escrito no contrato ERP desde R27: substituir a tabela (H) pelos
    precos reais nao pode mudar a ESTRUTURA do BOM, so os valores. Se a lista
    de itens mudar, a chave de SKU esta errada — e por isso esta funcao devolve
    a lista com o mesmo tamanho e a mesma ordem, sempre.
    """
    escolha = {x["sku"]: x for x in comparacao["itens"]}
    novos, trocados = [], []
    for i in itens:
        x = escolha.get(i.sku)
        if not x:
            novos.append(i)
            continue
        antes = i.preco_unit
        novo = type(i)(**{**i.__dict__, "preco_unit": x["preco"],
                          "fonte": f"COTADO {x['escolhido']}"})
        novos.append(novo)
        trocados.append(dict(sku=i.sku, de=antes, para=x["preco"],
                             variacao=round(x["preco"] / antes - 1, 4)
                             if antes else None,
                             fornecedor=x["escolhido"]))
    assert len(novos) == len(itens), "aplicar nao pode mudar a lista de itens"
    return dict(itens=novos, trocados=trocados, n=len(trocados))


def cobertura(itens: list, comparacao: dict = None) -> dict:
    """Quanto do custo esta COTADO — o numero que decide se isto se assina.

    E a pergunta que um orcamento com precos (H) nao respondia: nao "quanto
    custa", mas "quanto do que custa foi perguntado a alguem". Um total 100 %
    (H) e uma ordem de grandeza; a 60 % cotado e uma proposta; a 100 % e um
    orcamento.
    """
    escolha = {x["sku"] for x in (comparacao or {}).get("itens", [])}
    por_nivel = {n: 0.0 for n in NIVEIS}
    for i in itens:
        if not i.compra:
            continue
        nivel = "COTADO" if i.sku in escolha else "H"
        por_nivel[nivel] += i.total
    total = sum(por_nivel.values()) or 1.0
    return dict(por_nivel={k: round(v, 2) for k, v in por_nivel.items()},
                fracao={k: round(v / total, 4) for k, v in por_nivel.items()},
                total=round(total, 2),
                cotado_pct=round(por_nivel["COTADO"] / total * 100, 1),
                leitura=(f"{por_nivel['COTADO'] / total * 100:.1f} % do custo "
                         f"esta cotado; o restante e (H) — ordem de grandeza "
                         f"para a estrutura do calculo existir, nunca base de "
                         f"contrato"))


def sensibilidade(itens: list, familia: str, variacao: float) -> dict:
    """Quanto o total anda se o preco de uma familia andar.

    Com 100 % dos precos (H), esta e a informacao mais honesta que o custo
    consegue dar: nao o valor, mas a DERIVADA — quanto do orcamento depende de
    um preco que ninguem confirmou.
    """
    base = sum(i.total_compra for i in itens)
    depois = sum(i.total_compra * (1 + variacao if i.familia == familia else 1.0)
                 for i in itens)
    exposto = sum(i.total_compra for i in itens if i.familia == familia)
    return dict(familia=familia, variacao=variacao, base=round(base, 2),
                depois=round(depois, 2),
                delta=round(depois - base, 2),
                exposicao=round(exposto / base, 4) if base else 0.0,
                elasticidade=round((depois / base - 1) / variacao, 4)
                if base and variacao else 0.0)
