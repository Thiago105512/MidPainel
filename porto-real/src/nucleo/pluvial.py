"""PLUVIAL — o que cai no lote, para onde vai, e quanto disso fica.

R52 trocou uma decisao por outra a pedido do proprietario: sai o REUSO, entra a
RETENCAO. Nao e ajuste de tamanho do mesmo reservatorio — sao sistemas de
dimensionamento OPOSTO. O reuso quer o reservatorio cheio na vespera da seca; a
retencao quer o reservatorio VAZIO na vespera da chuva. Um enche para guardar,
o outro esvazia para poder receber. Confundir os dois e o erro classico do
"reservatorio que faz as duas coisas" e que nao faz nenhuma: no dia da chuva
ele esta cheio de agua de reuso e nao retem nada.

O QUE FALTAVA PARA CALCULAR QUALQUER UMA DAS DUAS. A area impermeabilizada do
LOTE nunca existiu no modelo. Existia a projecao coberta (que e telhado),
existiam os pisos externos (que sao parte do descoberto) e existia o jardim —
e 333,44 m2 do terreno, 42 % dele, nao tinham superficie declarada nenhuma.
Recuo, faixa tecnica e acesso de veiculos sao chao, chovem, e escoam. Retencao
calculada sem eles seria retencao calculada sobre metade do lote.

A LEI. Lei municipal 1.192/2007 (Pro-Aguas, Manaus) obriga reservatorio de
retardo em empreendimento com area impermeabilizada superior a 500 m2, manda
indicar localizacao e calculo do volume no projeto, e prefere que a agua
INFILTRE no solo, admitindo descarga por gravidade ou bomba na rede. O gatilho
e conferido aqui, e conferido contra a area que o modelo calcula — nao contra
uma frase.
"""
from __future__ import annotations

import math

# --------------------------------------------------- coeficientes de deflusao
# C do metodo racional por tipo de superficie. Sao valores de pratica corrente
# (Wilken / ASCE, reproduzidos em manuais de drenagem urbana brasileiros) e
# estao aqui como TABELA declarada, nao espalhados em formula.
C_SUPERFICIE = {
    "cobertura": 0.95,
    "piso rigido descoberto": 0.90,
    "lamina de piscina": 1.00,
    "piso drenante": 0.50,
    "brita solta": 0.35,
    "jardim e grama": 0.20,
    "terreno natural": 0.20,
}

# complemento do lote: o que existe no terreno e nao estava em ambiente nenhum.
# Cada faixa e geometria, nao estimativa — sai dos recuos ja declarados e do
# portao que o muro ja descontava.
# largura e posicao vem de pj.ACESSO_TESTADA: o mesmo dado que abre o muro na
# cena 3D e que o comprimento do muro desconta. Tres consumidores, uma fonte.

# chuva de projeto: uma so fonte para todo o projeto. A mesma intensidade que
# dimensiona calha e descida em COBERTURA dimensiona a retencao — se um dia ela
# mudar, muda nos dois lugares porque e o mesmo numero.
TC_MIN = 10.0          # min, tempo de concentracao adotado para o lote
C_PRE = 0.20           # lote antes da obra: terreno natural com vegetacao

RETENCAO = dict(
    tipo="reservatorio enterrado em concreto armado, sob o acesso de veiculos",
    onde="faixa do recuo frontal, ja escavada para o acesso e sem uso vertical",
    fundo="drenante, com lastro de brita e manta geotextil: a propria Lei "
          "1.192/2007 pede que a agua infiltre antes de mandar para a rede",
    descarga="orificio calibrado na vazao de pre-ocupacao, com grade e caixa "
             "de inspecao a montante",
    extravasor="tubo DN150 acima do nivel maximo, ligado a sarjeta",
    altura_util=1_200,     # mm de lamina util
    borda_livre=200,       # mm acima do nivel maximo
    cd_orificio=0.61,      # coeficiente de descarga de orificio de parede fina
)


def superficies(pj) -> list[dict]:
    """Particao do lote inteiro em superficies com coeficiente de deflusao.

    A regra e uma so e vale para tudo: a soma tem de dar o lote. Nao ha classe
    "outros" nem sobra — sobra e superficie nao declarada, e superficie nao
    declarada nao escoa no calculo e escoa na chuva.
    """
    cob = {a.cod for a in pj.cobertos()}
    jard = ("JARDIM",)
    desc = [a for a in pj.TERREO + pj.TERREO_ABERTO if a.cod not in cob]
    rigido = sum(a.area_mod for a in desc
                 if not any(j in a.nome.upper() for j in jard))
    jardim = sum(a.area_mod for a in desc
                 if any(j in a.nome.upper() for j in jard))
    lamina = pj.PISCINA["lamina_m2"]
    # a piscina esta DENTRO do retangulo do deck: o deck rigido e o que sobra
    rigido -= lamina

    # complemento geometrico do lote
    xs = [a.x for a in pj.TERREO + pj.TERREO_ABERTO]
    xe = [a.x + a.w for a in pj.TERREO + pj.TERREO_ABERTO]
    ys = [a.y for a in pj.TERREO + pj.TERREO_ABERTO]
    ye = [a.y + a.h for a in pj.TERREO + pj.TERREO_ABERTO]
    x0, x1, y0, y1 = min(xs), max(xe), min(ys), max(ye)
    L, P = pj.LOTE_L, pj.LOTE_P
    esq = x0 * P / 1e6
    dir_ = (L - x1) * P / 1e6
    frente = (x1 - x0) * y0 / 1e6
    fundo = (x1 - x0) * (P - y1) / 1e6
    pt = pj.ACESSO_TESTADA
    acesso = pt["veiculo_larg"] * y0 / 1e6
    passeio = pt["pedestre_larg"] * y0 / 1e6

    return [
        dict(classe="cobertura", nome="telhado e projecao coberta",
             area=pj.projecao_coberta_m2(), origem="modelo"),
        dict(classe="piso rigido descoberto",
             nome="deck, patio e faixa seca da piscina",
             area=round(rigido, 2), origem="modelo, menos a lamina da piscina"),
        dict(classe="lamina de piscina", nome="espelho d'agua",
             area=lamina, origem="modelo"),
        dict(classe="jardim e grama", nome="jardins do modelo",
             area=round(jardim, 2), origem="modelo"),
        dict(classe="piso drenante", nome="acesso de veiculos",
             area=round(acesso, 2), origem="portao x recuo frontal"),
        dict(classe="piso drenante", nome="passeio de pedestres",
             area=round(passeio, 2), origem="portao x recuo frontal"),
        dict(classe="jardim e grama", nome="recuo frontal ajardinado",
             area=round(frente - acesso - passeio, 2), origem="recuo frontal"),
        dict(classe="brita solta", nome="faixa tecnica lateral direita",
             area=round(dir_, 2), origem="recuo lateral direito x profundidade"),
        dict(classe="jardim e grama", nome="recuo lateral esquerdo",
             area=round(esq, 2), origem="recuo lateral esquerdo x profundidade"),
        dict(classe="jardim e grama", nome="recuo de fundo",
             area=round(fundo, 2), origem="recuo de fundo"),
    ]


def balanco(pj) -> dict:
    """Area total, impermeavel, e o C ponderado do lote."""
    sup = superficies(pj)
    total = sum(s["area"] for s in sup)
    for s in sup:
        s["c"] = C_SUPERFICIE[s["classe"]]
    # impermeavel no sentido da lei: superficie que nao deixa a agua passar.
    # O drenante NAO conta como impermeavel — e e por isso que ele foi
    # escolhido no acesso desde R08, antes de haver qualquer lei no modelo.
    imper = sum(s["area"] for s in sup if s["c"] >= 0.80)
    c_pond = sum(s["area"] * s["c"] for s in sup) / total
    return dict(superficies=sup, total=round(total, 2),
                lote=pj.LOTE_AREA_M2,
                fecha=abs(total - pj.LOTE_AREA_M2) < 0.05,
                impermeavel=round(imper, 2),
                taxa_impermeabilizacao=round(imper / pj.LOTE_AREA_M2, 4),
                c_ponderado=round(c_pond, 4),
                c_pre=C_PRE)


def gatilho_legal(pj) -> dict:
    """Lei 1.192/2007 de Manaus: obriga acima de 500 m2 impermeabilizados."""
    b = balanco(pj)
    return dict(lei="Lei municipal 1.192/2007 (Pro-Aguas), Manaus",
                limite_m2=500.0,
                impermeavel=b["impermeavel"],
                obriga=b["impermeavel"] > 500.0,
                folga=round(500.0 - b["impermeavel"], 2),
                exigencias=[
                    "reservatorio que retarde o escoamento das aguas pluviais",
                    "localizacao e calculo do volume indicados no projeto",
                    "agua deve infiltrar no solo, salvo indicacao do orgao de "
                    "drenagem; admite-se descarga por gravidade ou bomba",
                    "implantacao e condicao para a licenca ambiental de "
                    "operacao",
                ],
                decisao=("adotada por decisao do proprietario mesmo abaixo do "
                         "gatilho legal, e dimensionada pelo mesmo criterio "
                         "que a lei usaria"))


def vazoes(pj) -> dict:
    """Metodo racional: o que o lote mandava para a rua antes e depois."""
    b = balanco(pj)
    i = pj.COBERTURA["intensidade_mm_h"]
    a = pj.LOTE_AREA_M2
    q_pos = b["c_ponderado"] * i * a / 3_600
    q_pre = C_PRE * i * a / 3_600
    return dict(intensidade=i, area=a,
                q_pos_ls=round(q_pos, 2), q_pre_ls=round(q_pre, 2),
                excedente_ls=round(q_pos - q_pre, 2),
                razao=round(q_pos / q_pre, 2),
                fonte_intensidade="COBERTURA['intensidade_mm_h'], a mesma que "
                                  "dimensiona calha e descida",
                metodo="Q = C i A / 3600, com C ponderado pelas superficies")


def retencao(pj) -> dict:
    """Volume, orificio e geometria do reservatorio de retardo.

    O volume e o EXCEDENTE — a diferenca entre o que o lote passou a mandar
    para a rua e o que ele mandava antes — acumulado durante o tempo de
    concentracao. Reter o escoamento inteiro seria dimensionar para um problema
    que a cidade nunca teve: o terreno natural tambem escoava.
    """
    v = vazoes(pj)
    t = TC_MIN * 60
    vol = v["excedente_ls"] * t / 1_000.0
    R = RETENCAO
    h = R["altura_util"] / 1_000.0
    area = vol / h
    lado = math.sqrt(area)
    # orificio de descarga calibrado na vazao de pre-ocupacao com lamina cheia
    g = 9.81
    q_pre = v["q_pre_ls"] / 1_000.0
    a_or = q_pre / (R["cd_orificio"] * math.sqrt(2 * g * h))
    d_or = math.sqrt(4 * a_or / math.pi) * 1_000
    # tempo de esvaziamento com carga variavel (orificio de fundo)
    t_esv = (2 * area * math.sqrt(h)) / (R["cd_orificio"] * a_or
                                         * math.sqrt(2 * g))
    return dict(volume_m3=round(vol, 2),
                tempo_concentracao_min=TC_MIN,
                altura_util=R["altura_util"], borda_livre=R["borda_livre"],
                area_planta=round(area, 2),
                lado_equivalente=round(lado, 2),
                orificio_mm=round(d_or, 1),
                orificio_area_cm2=round(a_or * 1e4, 2),
                vazao_de_saida_ls=v["q_pre_ls"],
                esvaziamento_min=round(t_esv / 60, 1),
                tipo=R["tipo"], onde=R["onde"], fundo=R["fundo"],
                descarga=R["descarga"], extravasor=R["extravasor"],
                obs="o orificio limita a saida a vazao de PRE-ocupacao: e ele, "
                    "e nao o volume, que faz o reservatorio cumprir a funcao")


def conferir(pj) -> list[tuple[str, str, bool]]:
    b = balanco(pj)
    g = gatilho_legal(pj)
    v = vazoes(pj)
    r = retencao(pj)
    return [
        ("a soma das superficies e o lote",
         f"{b['total']:.2f} m2 declarados contra {b['lote']:.2f} m2 de lote",
         b["fecha"]),
        ("nenhuma superficie sem classe",
         f"{len(b['superficies'])} superficies, todas com C de tabela",
         all(s["c"] in C_SUPERFICIE.values() for s in b["superficies"])),
        ("gatilho da Lei 1.192/2007",
         f"{g['impermeavel']:.2f} m2 impermeabilizados contra "
         f"{g['limite_m2']:.0f} m2 — "
         + ("obriga" if g["obriga"] else f"nao obriga, folga de {g['folga']:.2f} m2"),
         True),
        ("a retencao foi adotada de qualquer forma",
         "decisao do proprietario, dimensionada pelo criterio da lei",
         r["volume_m3"] > 0),
        ("a piscina nao paga piso",
         f"a lamina de {pj.PISCINA['lamina_m2']:.2f} m2 esta dentro do "
         f"retangulo do deck e foi descontada do piso rigido",
         any(s["classe"] == "lamina de piscina" for s in b["superficies"])),
        ("a chuva de projeto tem fonte unica",
         f"{v['intensidade']:.0f} mm/h, a mesma de calha e descida",
         v["intensidade"] == pj.COBERTURA["intensidade_mm_h"]),
        ("o reservatorio esvazia antes da proxima chuva",
         f"{r['esvaziamento_min']:.1f} min por orificio de "
         f"{r['orificio_mm']:.1f} mm",
         r["esvaziamento_min"] <= 720),
        ("a saida e limitada a vazao de pre-ocupacao",
         f"{r['vazao_de_saida_ls']:.2f} L/s de saida contra "
         f"{v['q_pos_ls']:.2f} L/s que chegariam sem reservatorio",
         r["vazao_de_saida_ls"] < v["q_pos_ls"]),
    ]
