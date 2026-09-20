"""AREA EXTERNA — 286 m2 de projeto que nao existiam no orcamento.

Quinze areas abertas declaradas, uma piscina de 17,82 m2 de lamina com sistema
completo, um deck de 7,8 x 5,4 m, um muro de 2,2 m de altura em todo o
perimetro, oito itens de paisagismo e tres zonas de piso externo com material
escolhido e razao escrita. Nada disso tinha quantidade, e nenhuma familia
"externo" existia no BOM.

Em residencia deste porte a area externa e 10 a 20 % do custo, e e onde o
orcamento costuma estourar — justamente porque entra por ultimo e sem
levantamento. O padrao e o mesmo do vigamento ate R31, da fundacao ate R37 e do
brise ate R48: existe no desenho, nao existe no modelo.

O QUE E DERIVADO E O QUE E DECIDIDO. Area, perimetro e volume saem da geometria
declarada. Material vem do que o projeto ja escolheu — PISO_EXTERNO nomeia as
tres zonas com a razao de cada uma. Onde faltava decisao, ela esta comentada no
ponto em que foi tomada, com a alternativa que foi descartada.
"""
from __future__ import annotations

# MURO — decisao R49. Bloco de concreto APARENTE de 14 cm, junta rebaixada,
# com hidrofugante incolor. Alternativas descartadas:
#   alvenaria revestida e pintada: repintura a cada 4 a 5 anos em 60 m de muro,
#     e a regra da fachada recusa superficie que exija pintura (mesmo a 2,2 m,
#     sao 132 m2 de andaime baixo e tinta, para sempre);
#   placa cimenticia sobre estrutura: mesmo acabamento da casa, porem o dobro do
#     preco por m2 num elemento que ninguem olha de perto;
#   bloco aparente: textura franca, zero manutencao, e conversa com o ripado de
#     aluminio e com o mineral claro sem competir com eles.
MURO = dict(
    altura=2_200, espessura=140,
    material="bloco de concreto estrutural 14 x 19 x 39 aparente, junta "
             "rebaixada, hidrofugante incolor",
    norma="NBR 6136 (bloco) e NBR 16868 (execucao)",
    blocos_m2=12.5,            # 19 x 39 com junta de 10: 12,5 blocos/m2
    graute_m3_m2=0.012,        # grauteamento de cinta e pilaretes
    pilarete_cada=3_000,       # mm, enrijecimento vertical
)

# (H) precos, como todos os deste projeto
PRECO = {
    "bloco_un": 4.80, "graute_m3": 620.00, "hidrofugante_m2": 18.00,
    "piso_porcelanato_m2": 148.00, "piso_wpc_m2": 320.00,
    "piso_drenante_m2": 96.00, "grama_m2": 38.00,
    "piscina_revest_m2": 210.00, "piscina_estrutura_m3": 1_450.00,
    "borda_m": 185.00, "arvore_un": 780.00, "vaso_un": 240.00,
    "seixo_m2": 62.00, "irrigacao_m": 42.00,
}

# a que zona de piso externo cada area aberta pertence. Nao e adivinhacao: as
# tres zonas foram nomeadas em PISO_EXTERNO com a razao de cada uma, e o que
# faltava era dizer QUAIS areas caem em cada uma.
ZONA_DE_AREA = {
    "T-DKP": "faixa seca da piscina",
    "T-DKL": "patio e deck descoberto",       # R59: descoberto, sol pleno
    "T-DKC": "lounge e circulacao do deck",
    "T-ALP": "lounge e circulacao do deck",
    "T-PAT": "patio e deck descoberto",       # R59: churrasqueira
    "T-PT2": "patio e deck descoberto",       # R59: descoberto
    "T-VAR": "passeio e acesso",
    "T-LOG": "passeio e acesso",
    "T-VRL": "passeio e acesso",
    "S-BAL": "varanda do pavimento superior",
}
# jardins nao levam piso: levam grama e canteiro
JARDINS = ("T-JLE", "T-JNO", "T-JS2", "T-JN2", "T-JN3", "T-JFU")


def muro(pj) -> dict:
    """Comprimento a partir do lote, descontando a testada com portao."""
    L, P = pj.LOTE_L, pj.LOTE_P
    pt = pj.PORTAO_TESTADA
    portao, acesso = pt["veiculo_larg"], pt["pedestre_larg"]
    # tres divisas fechadas mais a testada menos o portao e menos o acesso
    comp = (2 * P + L) + (L - portao - acesso)
    area = comp * MURO["altura"] / 1e6
    blocos = int(area * MURO["blocos_m2"])
    pilaretes = int(comp / MURO["pilarete_cada"]) + 1
    return dict(
        comprimento_m=round(comp / 1000.0, 1), altura=MURO["altura"],
        area=round(area, 1), blocos=blocos,
        graute_m3=round(area * MURO["graute_m3_m2"], 2),
        pilaretes=pilaretes, material=MURO["material"], norma=MURO["norma"],
        obs="testada descontada do portao de "
            f"{portao} mm e de {acesso} mm de acesso de pedestre")


def pisos(pj) -> dict:
    """Cada area aberta na sua zona, com o material que o projeto escolheu.

    R52 — A PISCINA NAO PAGA PISO. O deck da piscina e um retangulo de 42,12
    m2 e a piscina esta DENTRO dele: 17,82 m2 de lamina d'agua. Ate R51 o
    orcamento comprava porcelanato para os 42,12, ou seja, 17,82 m2 de piso
    sobre a agua — R$ 2.637 de material que nao existe. O erro sobreviveu
    porque area de ambiente e area de piso pareciam a mesma coisa, e sao a
    mesma coisa em todo lugar MENOS onde ha um vazio dentro do ambiente.
    Vazio dentro de area e o caso que toda conferencia por soma deixa passar.
    """
    mat = {z["zona"]: z for z in pj.PISO_EXTERNO}
    vazios = {"T-DKP": pj.PISCINA["lamina_m2"]}
    por_zona: dict = {}
    jardim = 0.0
    fora = []
    for a in pj.TERREO_ABERTO + pj.SUPERIOR_ABERTO:
        if a.cod in JARDINS:
            jardim += a.area_mod
            continue
        z = ZONA_DE_AREA.get(a.cod)
        if z is None:
            fora.append(a.cod)
            continue
        d = por_zona.setdefault(z, dict(area=0.0, areas=[], descontado=0.0))
        d["area"] += a.area_mod - vazios.get(a.cod, 0.0)
        d["descontado"] += vazios.get(a.cod, 0.0)
        d["areas"].append(a.cod)
    itens = []
    for z, d in sorted(por_zona.items()):
        m = mat.get(z, {})
        itens.append(dict(zona=z, material=m.get("material", ""),
                          razao=m.get("razao", ""), area=round(d["area"], 2),
                          descontado=round(d["descontado"], 2),
                          areas=sorted(d["areas"])))
    return dict(itens=itens, jardim=round(jardim, 2), sem_zona=fora,
                total=round(sum(i["area"] for i in itens), 2))


def piscina(pj) -> dict:
    """Revestimento, borda e estrutura a partir da geometria declarada."""
    p = pj.PISCINA
    w, h = p["w"] / 1000.0, p["h"] / 1000.0
    prof = p["prof_principal"] / 1000.0
    prainha = p["prof_prainha"] / 1000.0
    # area molhada = fundo + quatro paredes, com o fundo medio entre prainha e
    # profundidade principal
    fundo = w * h
    paredes = 2 * (w + h) * ((prof + prainha) / 2)
    revest = fundo + paredes
    borda = 2 * (w + h)
    # casca de concreto armado de 150 mm, que e o usual para piscina de alvenaria
    esp = 0.15
    conc = (fundo + paredes) * esp
    return dict(
        lamina=p["lamina_m2"], volume=p["volume_m3"],
        largura=p["w"], comprimento=p["h"],
        prof_principal=p["prof_principal"], prof_prainha=p["prof_prainha"],
        revestimento_m2=round(revest, 2), borda_m=round(borda, 2),
        concreto_m3=round(conc, 2), espessura_casca=int(esp * 1000),
        sistema=pj.PISCINA_SISTEMA,
        obs="area molhada = fundo mais quatro paredes com profundidade MEDIA "
            "entre prainha e parte funda; casca de 150 mm em concreto armado")


def paisagismo(pj) -> dict:
    arvores = [x for x in pj.PAISAGISMO
               if x.get("qtd") and "m" in str(x.get("porte", ""))
               and "0," not in str(x.get("porte", ""))]
    vasos = [x for x in pj.PAISAGISMO
             if x.get("qtd") and x not in arvores and x["qtd"] > 0]
    return dict(
        arvores=sum(x["qtd"] for x in arvores),
        vasos=sum(x["qtd"] for x in vasos),
        itens=[dict(cod=x["cod"], especie=x["especie"], qtd=x.get("qtd", 0),
                    porte=x.get("porte", "")) for x in pj.PAISAGISMO])


def levantar(pj) -> dict:
    m, pi, pc, pa = muro(pj), pisos(pj), piscina(pj), paisagismo(pj)
    return dict(muro=m, pisos=pi, piscina=pc, paisagismo=pa,
                area_externa=round(pi["total"] + pi["jardim"], 2),
                metodo="area, perimetro e volume saem da geometria declarada; "
                       "material vem do que o projeto ja escolheu em "
                       "PISO_EXTERNO, com a razao de cada zona. O muro e a "
                       "unica decisao nova, e esta justificada no codigo")
