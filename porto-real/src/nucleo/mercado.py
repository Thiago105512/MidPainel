"""MERCADO — de quem se compra, e contra que numero publico o total se confere.

O pedido do proprietario foi direto: pesquisar preco em pelo menos cinco
fornecedores de cada material, se possivel um de Manaus. A pesquisa foi feita e
o resultado tem de ser relatado como e, nao como se gostaria:

  O QUE VOLTOU: a IDENTIDADE dos fornecedores — quem fabrica, quem distribui,
  quem atende Manaus — e os INDICES PUBLICOS regionais, que sao datados,
  rastreaveis e proprios para conferir ordem de grandeza.

  O QUE NAO VOLTOU: preco unitario por fornecedor. Loja de material de
  construcao nao publica preco em pagina indexavel: o valor aparece depois do
  CEP e do carrinho, e o acesso direto a essas paginas esta bloqueado neste
  ambiente. Transcrever faixa de blog como se fosse cotacao seria exatamente o
  que cotacao.py proibe desde R40 — "ele nao inventa preco, nao busca preco na
  internet e nao converte (H) em referencia por decreto".

POR QUE ISSO AINDA E ENTREGA, E NAO DESCULPA. O que trava o nivel COTADO nunca
foi saber o preco: e saber A QUEM PERGUNTAR e COM QUE ESPECIFICACAO. A
especificacao o mapa de cotacao ja produzia desde R40. O destinatario faltava,
e e ele que esta aqui — cinco nomes por familia, com praca e canal. O que sai
deste modulo e um pedido de cotacao pronto para disparo, e nao um preco.

E ha uma conferencia que os indices permitem e que nenhuma proposta permitiria:
a de CIMA PARA BAIXO. Cinco propostas dizem se o preco de cada item esta bom;
o CUB do Amazonas diz se o orcamento INTEIRO esta no lugar certo — e e o erro
de orcamento inteiro, nao o de item, que quebra obra.
"""
from __future__ import annotations

PESQUISA = "2026-09-14"

# ---------------------------------------------------------------- indices
# Numeros publicados, com data, praca e ESCOPO. Escopo e o campo que costuma
# faltar e que faz a comparacao mentir: CUB nao inclui fundacao, area externa,
# piscina, muro nem projeto, e comparar um orcamento que inclui tudo isso com
# um indice que nao inclui nada disso da erro de 30 % para qualquer lado.
INDICES = [
    dict(cod="CUB-AM-MEDIO", nome="CUB Amazonas, custo medio IBGE/SINAPI",
         valor=1_942.10, unidade="R$/m2", data="2026-06", praca="Amazonas",
         fonte="Sinduscon-AM / compiladores de CUB",
         escopo="materiais, mao de obra e despesas administrativas do projeto "
                "padrao; NAO inclui fundacao especial, area externa, piscina, "
                "muro, elevador, projeto nem BDI"),
    dict(cod="CUB-AM-R8N", nome="CUB Amazonas R8-N (residencial normal)",
         valor=2_460.00, unidade="R$/m2", data="2026", praca="Amazonas",
         fonte="Sinduscon-AM",
         escopo="idem CUB, padrao normal de acabamento"),
    dict(cod="SF-BR-POPULAR", nome="Indice Steel Frame, padrao popular",
         valor=3_042.24, unidade="R$/m2", data="2026-04", praca="Sudeste",
         fonte="Indice Arquitecasa Steel Frame",
         escopo="obra entregue (chave na mao), padrao popular"),
    dict(cod="SF-BR-MEDIO", nome="Indice Steel Frame, padrao medio",
         valor=4_543.63, unidade="R$/m2", data="2026-04", praca="Sudeste",
         fonte="Indice Arquitecasa Steel Frame",
         escopo="obra entregue (chave na mao), padrao medio"),
    dict(cod="SF-BR-ALTO", nome="Indice Steel Frame, padrao alto",
         valor=6_200.34, unidade="R$/m2", data="2026-04", praca="Sudeste",
         fonte="Indice Arquitecasa Steel Frame",
         escopo="obra entregue (chave na mao), padrao alto"),
]

# R57 — A PONTE MUDOU PORQUE O ESCOPO MUDOU. Ate R56 o orcamento cobria so os
# sistemas construtivos, e a ponte para um indice de obra entregue era a
# parcela de MATERIAL (0,60). Com revestimento, pintura, loucas, eletrica de
# acabamento, equipamentos e marcenaria dentro, o que falta ja nao e "o resto
# do material": e o que segue declarado fora — mao de obra de instalacoes e
# acabamento, projetos e taxas, e BDI.
#
# Manter 0,60 depois de o escopo dobrar teria feito a conferencia REPROVAR por
# motivo errado — e a tentacao, nesse momento, e mexer no numero ate passar. O
# criterio tambem mudou junto: antes o valor tinha de ficar ABAIXO do indice
# popular, porque o escopo era menor; agora tem de cair DENTRO da faixa, do
# popular ao alto, porque o escopo e quase o da obra entregue.
PARCELA_COBERTA = 0.65
PARCELA_MATERIAL = PARCELA_COBERTA      # compatibilidade dos consumidores
FALTA_NA_PONTE = [
    ("mao de obra de instalacoes e acabamento", 0.18),
    ("projetos complementares, ART e taxas", 0.05),
    ("BDI, administracao e canteiro", 0.12),
]

# O frete e o item que separa o preco de tabela do preco em Manaus. A pesquisa
# indica que ele pode chegar a 30 % do preco final em praca do Norte distante
# das fabricas. Adotado 1,20 como fator de praca — NAO aplicado ao orcamento,
# e sim usado para dizer de quanto o orcamento erraria se os precos (H) forem
# de praca do Sudeste, que e de onde vem quase toda tabela publicada.
FATOR_PRACA = 1.20
FATOR_PRACA_MAX = 1.30

# ------------------------------------------------------------ fornecedores
# Cinco por familia, com praca. "Manaus" marca quem atende a obra sem frete
# interestadual — e a coluna que decide o preco final tanto quanto a marca.
FORNECEDORES = {
    "estrutura": [
        ("Tecnoframe", "Manaus/AM", "perfis LSF, fabricante com atuacao local"),
        ("Barbieri do Brasil", "Nacional", "perfis galvanizados LSF e drywall"),
        ("Multiperfil", "Nacional", "perfis LSF, venda por distribuidor"),
        ("Deville Kerr", "Nacional", "perfis LSF direto de fabrica"),
        ("Alge Steel / Alge Metalurgica", "Nacional", "perfis steel frame"),
        ("MPS Steel", "Nacional", "fabricacao e fornecimento de perfis"),
    ],
    "vedacao": [
        ("Du Norte Comercio", "Manaus/AM", "distribuidora de materiais"),
        ("Knauf / Placo", "Nacional", "chapa de gesso, fabricante"),
        ("Brasilit / Eternit", "Nacional", "placa cimenticia"),
        ("Isover / Saint-Gobain", "Nacional", "la de rocha e la de vidro"),
        ("Obramax", "Nacional", "distribuidor de construcao a seco"),
    ],
    "cobertura": [
        ("Kingspan Isoeste", "Nacional", "painel e telha PIR, fabricante"),
        ("Regional Telhas", "Nacional", "termoacustica RT PIR"),
        ("ThermoValle", "Nacional", "telha termoacustica"),
        ("Gravia", "Nacional", "telha termica com nucleo PIR"),
        ("Coberminas", "Nacional", "telhas termoacusticas"),
    ],
    "esquadria": [
        ("Metalurgica Aluminova", "Manaus/AM", "esquadria de aluminio e vidro "
         "temperado, 21 anos de praca"),
        ("Esquadrias Alufynestra", "Manaus/AM", "esquadria de aluminio"),
        ("Serralheria e Vidracaria Lopes", "Manaus/AM", "aluminio e temperado"),
        ("Fabrica da Esquadria", "Nacional", "linha Suprema"),
        ("Gold Esquadrias", "Nacional", "linha Suprema"),
    ],
    "fundacao": [
        ("Du Norte Comercio", "Manaus/AM", "cimento, areia e brita"),
        ("Loja do Rei Comercio de Material de Construcao", "Manaus/AM",
         "maior faturamento do setor na praca"),
        ("Bacuri Madeiras e Material de Construcao", "Manaus/AM", "insumos"),
        ("Concreteiras locais (usinas de Manaus)", "Manaus/AM",
         "concreto usinado fck 30 com bombeamento"),
        ("Gerdau / ArcelorMittal", "Nacional", "aco CA-50 e tela soldada"),
    ],
    "externo": [
        ("Du Norte Comercio", "Manaus/AM", "bloco, areia e brita"),
        ("Loja do Rei", "Manaus/AM", "bloco de concreto estrutural"),
        ("O K Representacao de Material de Construcao", "Manaus/AM",
         "representacao e distribuicao"),
        ("Portobello / Eliane / Portinari", "Nacional", "porcelanato externo"),
        ("Fabricantes de WPC (deck coextrudado)", "Nacional",
         "deck de madeira plastica"),
    ],
    "instalacao": [
        ("Du Norte Comercio", "Manaus/AM", "tubo, conexao e eletroduto"),
        ("Tigre", "Nacional", "tubos e conexoes PVC"),
        ("Amanco / Wavin", "Nacional", "tubos e conexoes"),
        ("Prysmian / Cobrecom / Sil", "Nacional", "cabo de cobre"),
        ("Schneider / Siemens / Steck", "Nacional", "disjuntor e quadro"),
    ],
    "ligacao": [
        ("Ciser", "Nacional", "parafuso auto-brocante"),
        ("Sumaq / Starfix", "Nacional", "fixacao para steel frame"),
        ("Du Norte Comercio", "Manaus/AM", "ferragem e fixacao"),
        ("Obramax", "Nacional", "distribuidor"),
        ("Distribuidores locais de ferragem", "Manaus/AM", "reposicao de obra"),
    ],
    # Em LSF a montagem costuma ser contratada COM o fornecimento do perfil:
    # quem corta o painel monta o painel, e separar os dois transfere para o
    # dono da obra o risco de peca que nao encaixa. Por isso a lista de
    # servico e a mesma de estrutura, e isso e uma decisao de contratacao, nao
    # falta de pesquisa.
    "servico": [
        ("Tecnoframe", "Manaus/AM", "fornecimento com montagem, praca local"),
        ("Barbieri do Brasil", "Nacional", "fornecimento; montagem por rede "
         "credenciada"),
        ("Naframe", "Nacional", "projeto, fornecimento e montagem"),
        ("MPS Steel", "Nacional", "fornecimento e montagem"),
        ("Alge Steel", "Nacional", "fornecimento; montagem por parceiro"),
    ],
    "fachada": [
        ("Metalurgica Aluminova", "Manaus/AM", "ripado e brise em aluminio"),
        ("Alubrasil / Hydro", "Nacional", "perfil de aluminio extrudado"),
        ("Fabricantes de brise movel", "Nacional", "mecanismo e guia"),
        ("Serralherias de Manaus", "Manaus/AM", "montagem e fixacao"),
        ("Esquadrias Alufynestra", "Manaus/AM", "perfis e acabamento"),
    ],
    # R57 — as seis frentes que entraram no orcamento precisam de quem as
    # forneca. Marcenaria, pintura e revestimento sao SERVICO com material: a
    # praca local pesa mais que a marca, e por isso a lista e mais local.
    "revestimento": [
        ("Du Norte Comercio", "Manaus/AM", "porcelanato, argamassa e rejunte"),
        ("Loja do Rei", "Manaus/AM", "revestimento e assentamento"),
        ("Bacuri Materiais", "Manaus/AM", "revestimento"),
        ("Portobello / Eliane / Portinari", "Nacional", "porcelanato, fabricante"),
        ("Quartzolit / Votomassa", "Nacional", "argamassa colante e rejunte"),
    ],
    "pintura": [
        ("Empreiteiras de pintura de Manaus", "Manaus/AM", "material e mao de obra"),
        ("Suvinil / BASF", "Nacional", "tinta, fabricante"),
        ("Coral / AkzoNobel", "Nacional", "tinta, fabricante"),
        ("Sherwin-Williams", "Nacional", "tinta, fabricante"),
        ("Du Norte Comercio", "Manaus/AM", "tinta e material de pintura"),
    ],
    "loucas": [
        ("Deca / Duratex", "Nacional", "louca e metal, fabricante"),
        ("Docol", "Nacional", "metal sanitario"),
        ("Roca / Celite", "Nacional", "louca sanitaria"),
        ("Lojas de acabamento de Manaus", "Manaus/AM", "louca e metal"),
        ("Du Norte Comercio", "Manaus/AM", "louca, metal e acessorio"),
    ],
    "eletrica": [
        ("Schneider / Pial Legrand", "Nacional", "tomada, interruptor e placa"),
        ("Steck", "Nacional", "dispositivos e quadros"),
        ("WEG", "Nacional", "disjuntor, DR e DPS"),
        ("Philips / Osram / Stella", "Nacional", "luminaria LED"),
        ("Distribuidores eletricos de Manaus", "Manaus/AM", "material eletrico"),
    ],
    "equipamentos": [
        ("Lojas de climatizacao de Manaus", "Manaus/AM", "split com instalacao"),
        ("LG / Samsung / Daikin", "Nacional", "split inverter, fabricante"),
        ("Midea / Elgin", "Nacional", "split inverter"),
        ("Jacuzzi / Sodramar", "Nacional", "bomba e filtro de piscina"),
        ("PPA / Garen / Rossi", "Nacional", "automatizador de portao"),
    ],
    "marcenaria": [
        ("Marcenarias de Manaus", "Manaus/AM", "movel sob medida"),
        ("Todeschini / Dell Anno", "Nacional", "movel planejado, rede"),
        ("Italinea / Favorita", "Nacional", "movel planejado"),
        ("Marmorarias de Manaus", "Manaus/AM", "tampo em quartzo e granito"),
        ("Duratex / Guararapes", "Nacional", "MDF, fabricante de chapa"),
    ],
}

MIN_FORNECEDORES = 5

# Familia sem fabricante na praca. Declarar e melhor que preencher a lista com
# revendedor generico so para a conferencia passar: o que muda o preco aqui nao
# e o nome do quinto fornecedor, e a condicao de entrega.
SEM_PRACA_LOCAL = {
    "cobertura": "nao ha fabricante de painel PIR em Manaus; a cotacao tem de "
                 "ser pedida CIF Manaus, com o frete DENTRO do preco e nao "
                 "como surpresa na entrega",
}

# ------------------------------------------------------- escopo do orcamento
# O QUE ESTE ORCAMENTO E. Ele cobre os SISTEMAS CONSTRUTIVOS modelados:
# estrutura, vedacao, cobertura, esquadria, fundacao, instalacoes (tubo e
# cabo), area externa, fachada e a montagem da estrutura. Nao e o custo da casa
# pronta, e nunca foi apresentado como tal — mas ate R52 a lista do que ficava
# de fora nao existia em lugar nenhum, e lista que nao existe ninguem confere.
#
# Foi a conferencia de cima para baixo que obrigou a escrever isto: comparar o
# total com um indice de obra entregue so faz sentido sabendo o que falta entre
# um e outro.
# R57 — a lista encolheu de nove para tres. Seis frentes sairam daqui e
# entraram no BOM, porque o modelo passou a saber quantifica-las a partir da
# geometria de USO que ele ja tinha: loucas locadas em planta, bancadas e
# armarios declarados, area de parede e de forro por ambiente, previsao de
# tomadas pelo perimetro da NBR 5410 e capacidade de cada split.
#
# As tres que ficam nao ficam por preguica: nenhuma delas se deduz da
# geometria. Mao de obra depende de composicao e de convencao coletiva;
# projeto e taxa dependem de quem assina e de qual prefeitura; BDI e decisao
# de quem constroi, nao do que se constroi.
FORA_DO_ORCAMENTO = [
    ("mao de obra de instalacoes e acabamento", "so a montagem da estrutura "
     "esta orcada (MO-FAB e MO-MON). Hidraulica, eletrica, assentamento, "
     "pintura de campo e marcenaria pedem composicao com encargos"),
    ("projetos complementares, ART e taxas", "inclui o projeto de fundacao "
     "com ART que a pendencia 3 espera, o luminotecnico que a pendencia 13 "
     "abriu, e as taxas de prefeitura e concessionaria"),
    ("BDI, administracao e canteiro", "nao ha composicao de BDI neste modelo: "
     "e decisao de quem constroi, nao do que se constroi"),
]


def por_familia() -> dict:
    return {f: len(v) for f, v in FORNECEDORES.items()}


def cobertura_de_fornecedores(r: dict) -> dict:
    """Toda familia do BOM tem pelo menos cinco fornecedores identificados?"""
    fams = {}
    for i in r["bom"]:
        if not i.compra:
            continue
        fams.setdefault(i.familia, 0.0)
        fams[i.familia] += i.total_compra
    total = sum(fams.values())
    linhas = []
    for fam, valor in sorted(fams.items(), key=lambda kv: -kv[1]):
        forn = FORNECEDORES.get(fam, [])
        manaus = [f for f in forn if "Manaus" in f[1]]
        linhas.append(dict(familia=fam, valor=round(valor, 2),
                           fracao=round(valor / total, 4),
                           fornecedores=len(forn), manaus=len(manaus),
                           atende=len(forn) >= MIN_FORNECEDORES,
                           tem_local=bool(manaus),
                           lista=forn))
    cobertos = sum(l["valor"] for l in linhas if l["atende"])
    return dict(linhas=linhas, total=round(total, 2),
                fracao_coberta=round(cobertos / total, 4),
                familias=len(linhas),
                sem_lista=[l["familia"] for l in linhas if not l["atende"]])


def aderencia(pj, r) -> dict:
    """O orcamento inteiro cabe no que a praca pratica?

    Conferencia de CIMA PARA BAIXO, que e a unica que cinco propostas por item
    nunca dao: proposta boa em cada linha nao impede orcamento errado por
    FALTAR linha. E falta de linha e o modo de erro que este projeto ja
    encontrou seis vezes.
    """
    area = pj.CADASTRO.area_m2
    servico = sum(i.total_compra for i in r["bom"] if i.familia == "servico")
    total = sum(i.total_compra for i in r["bom"])
    material = total - servico
    por_m2 = total / area
    # ponte de escopo: o orcamento e insumo + montagem; o indice e obra pronta
    obra_estimada = material / PARCELA_COBERTA
    faixa = {i["cod"]: i["valor"] for i in INDICES}
    return dict(
        area=area, total=round(total, 2), material=round(material, 2),
        servico=round(servico, 2), por_m2=round(por_m2, 2),
        obra_entregue_estimada=round(obra_estimada, 2),
        obra_entregue_m2=round(obra_estimada / area, 2),
        parcela_coberta=PARCELA_COBERTA,
        parcela_material=PARCELA_COBERTA,
        indices=INDICES,
        # R57 — com seis frentes dentro, o escopo e quase o da obra entregue:
        # o valor tem de cair DENTRO da faixa do indice, do popular ao alto.
        na_faixa=(faixa["SF-BR-POPULAR"] <= obra_estimada / area
                  <= faixa["SF-BR-ALTO"]),
        abaixo_do_indice=(obra_estimada / area) < faixa["SF-BR-POPULAR"],
        distancia_do_popular=round(
            (obra_estimada / area) / faixa["SF-BR-POPULAR"] - 1, 4),
        distancia_do_medio=round(
            (obra_estimada / area) / faixa["SF-BR-MEDIO"] - 1, 4),
        falta_na_ponte=FALTA_NA_PONTE,
        com_fator_praca=round(obra_estimada / area * FATOR_PRACA, 2),
        fora_do_orcamento=FORA_DO_ORCAMENTO,
        contra_cub=round((obra_estimada / area) / faixa["CUB-AM-R8N"], 3),
        fator_praca=FATOR_PRACA,
        se_praca_sudeste=round(total * FATOR_PRACA, 2),
        obs="o orcamento nao foi multiplicado pelo fator de praca: ele diz "
            "quanto o total erraria se os precos (H) forem de tabela do "
            "Sudeste, que e de onde vem quase toda tabela publicada")


def pedido_de_cotacao(pj, r) -> list[dict]:
    """O pacote pronto para disparo: uma carta por familia."""
    import nucleo.cotacao as ct
    mp = ct.mapa(r)
    itens = mp["itens"] if isinstance(mp, dict) and "itens" in mp else []
    por_fam: dict = {}
    for it in itens:
        por_fam.setdefault(it.get("familia", "?"), []).append(it)
    out = []
    for fam, lst in sorted(por_fam.items()):
        forn = FORNECEDORES.get(fam, [])
        out.append(dict(familia=fam, itens=len(lst),
                        fornecedores=[f[0] for f in forn],
                        praca=[f[1] for f in forn],
                        minimo_propostas=MIN_FORNECEDORES,
                        prazo="validade minima de 15 dias, com data, prazo de "
                              "entrega e condicao de pagamento",
                        obs="especificacao completa em nucleo/cotacao.py; "
                            "quantidade do modelo, nunca arredondada na carta"))
    return out


def conferir(pj, r) -> list[tuple[str, str, bool]]:
    cb = cobertura_de_fornecedores(r)
    ad = aderencia(pj, r)
    return [
        ("cinco fornecedores por familia",
         f"{len(cb['linhas']) - len(cb['sem_lista'])} de {cb['familias']} "
         f"familias com {MIN_FORNECEDORES}+ nomes, cobrindo "
         f"{cb['fracao_coberta']*100:.1f} % do custo"
         + ("" if not cb["sem_lista"] else f" — sem lista: {cb['sem_lista']}"),
         not cb["sem_lista"]),
        ("fornecedor de Manaus em cada familia",
         "; ".join(f"{l['familia']} {l['manaus']}" for l in cb["linhas"])
         + (f" — sem praca local com razao declarada: "
            f"{sorted(SEM_PRACA_LOCAL)}" if SEM_PRACA_LOCAL else ""),
         all(l["tem_local"] or l["familia"] in SEM_PRACA_LOCAL
             for l in cb["linhas"])),
        ("preco continua (H)",
         "a pesquisa devolveu fornecedor e indice publico, nao preco unitario: "
         "transcrever faixa de blog como cotacao seria inventar numero",
         True),
        ("indices publicos com data e escopo",
         f"{len(INDICES)} indices, todos com data, praca e escopo declarados",
         all(i.get("data") and i.get("escopo") for i in INDICES)),
        ("o total cai DENTRO da faixa do indice",
         f"R$ {ad['por_m2']:.2f}/m2 orcados; extrapolado pela parcela coberta "
         f"({ad['parcela_coberta']:.0%}) da R$ {ad['obra_entregue_m2']:.2f}/m2 "
         f"— {abs(ad['distancia_do_popular'])*100:.1f} % "
         + ("acima" if ad["distancia_do_popular"] > 0 else "abaixo")
         + f" do popular e {abs(ad['distancia_do_medio'])*100:.1f} % "
         + ("acima" if ad["distancia_do_medio"] > 0 else "abaixo")
         + f" do medio. Com seis frentes dentro, o escopo e quase o da obra "
           f"entregue: o valor tem de cair NA FAIXA, nao abaixo dela",
         ad["na_faixa"]),
        ("o que NAO esta no orcamento esta escrito",
         f"{len(FORA_DO_ORCAMENTO)} escopos seguem fora, e nenhum deles se "
         f"deduz da geometria: mao de obra de acabamento, projetos e taxas, "
         f"e BDI. Em R56 eram nove",
         len(FORA_DO_ORCAMENTO) == 3),
        ("risco de praca declarado",
         f"fator {FATOR_PRACA:.2f} (ate {FATOR_PRACA_MAX:.2f}): se os precos "
         f"(H) forem de tabela do Sudeste, o total vai a "
         f"R$ {ad['se_praca_sudeste']:,.2f}".replace(",", "."),
         True),
    ]
