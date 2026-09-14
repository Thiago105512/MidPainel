"""PLAUSIBILIDADE — a verificacao que faltava, e o que ela custa nao ter.

Ate R31 a auditoria sabia verificar duas coisas, e so duas: IDENTIDADES (bruto
= usado + perda, soma das reacoes = soma das cargas) e FORMAS FECHADAS (viga
biapoiada, caso normativo tabelado). Sao verificacoes fortes e sao cegas para
um tipo inteiro de erro — aquele em que a conta esta certa e o resultado e
absurdo.

O caso que provou isso: o consumo de aco marcava 9,4 kg/m2 num sobrado em Light
Steel Frame, onde a faixa corrente e 20 a 30. O numero esteve a vista em toda
revisao desde a E12, e nenhuma das 447 condicoes o olhava — porque nao havia
com o que comparar. Faltava mais da metade do aco.

O QUE ESTE ARQUIVO NAO E. Nao e norma. Faixa de plausibilidade nao aprova nem
reprova projeto: ela obriga a JUSTIFICAR. Um sobrado com 12 kg/m2 pode existir
— com vaos curtos, dois pavimentos pequenos e nenhum balanco —, e nesse caso a
saida da faixa e explicada e fica registrada. O que nao pode e passar batido.

DE ONDE VEM CADA FAIXA. Toda entrada declara a fonte. Onde a fonte e pratica
corrente e nao norma, isso esta escrito: sao (H) no mesmo sentido que o resto
do projeto usa — hipotese declarada, contestavel, e que vira pendencia quando
alguem tiver o dado melhor.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Faixa:
    cod: str
    grandeza: str
    unidade: str
    minimo: float
    maximo: float
    fonte: str
    consequencia: str        # o que a saida da faixa costuma significar
    normativa: bool = False  # True so quando o limite vem de norma

    def avaliar(self, v: float) -> dict:
        dentro = self.minimo <= v <= self.maximo
        lado = "" if dentro else ("abaixo" if v < self.minimo else "acima")
        # distancia relativa a borda violada, para ordenar por gravidade
        if dentro:
            desvio = 0.0
        elif v < self.minimo:
            desvio = (self.minimo - v) / self.minimo if self.minimo else 1.0
        else:
            desvio = (v - self.maximo) / self.maximo if self.maximo else 1.0
        return dict(cod=self.cod, valor=v, dentro=dentro, lado=lado,
                    desvio=desvio, faixa=(self.minimo, self.maximo),
                    unidade=self.unidade, fonte=self.fonte,
                    leitura=(f"{self.grandeza}: {v:.4g} {self.unidade}"
                             + ("" if dentro else
                                f" — {lado} da faixa {self.minimo:g} a "
                                f"{self.maximo:g}. {self.consequencia}")))


# ---------------------------------------------------------------------------
# AS FAIXAS
# ---------------------------------------------------------------------------
# Cada uma responde a pergunta: "um projeto deste tipo, fora desta faixa, e
# possivel — mas exige explicacao?". Se a resposta for nao, a faixa esta larga
# demais e nao serve; se for "impossivel", entao e limite normativo e nao e
# faixa de plausibilidade, e o lugar dele e na verificacao, nao aqui.
FAIXAS = (
    Faixa("aco_m2", "consumo de aco estrutural", "kg/m2", 18.0, 32.0,
          "(H) pratica corrente para residencia em LSF de dois pavimentos; "
          "casa terrea leve fica abaixo, edificio com grandes vaos acima",
          "abaixo costuma significar estrutura FALTANDO no modelo — foi "
          "assim que se descobriu que nao havia vigamento; acima costuma "
          "significar vao grande sem viga intermediaria"),

    Faixa("parafusos_m2", "parafusos estruturais", "un/m2", 12.0, 28.0,
          "(H) pratica corrente, so estrutura (sem fechamento)",
          "abaixo indica junta nao enumerada; acima, junta contada duas vezes"),

    Faixa("aproveitamento", "aproveitamento do plano de corte", "%", 78.0, 96.0,
          "(H) first-fit decreasing em barra de 6 m com pecas de 0,3 a 6 m",
          "abaixo indica peca comprida demais para a barra; acima de 96 e "
          "improvavel sem emenda livre, e sugere perda nao contabilizada"),

    Faixa("horas_m2", "montagem da estrutura", "h/m2", 0.25, 0.90,
          "(H) equipe de 4, estrutura apenas, sem fechamento nem instalacoes",
          "abaixo indica etapa faltando na sequencia; acima, painel pesado "
          "demais ou acesso ruim"),

    Faixa("co2e_m2", "CO2e incorporado", "kg/m2", 25.0, 75.0,
          "(H) dominado pelo aco: ~2 kg CO2e por kg de aco galvanizado, mais "
          "OSB e gesso",
          "acompanha a massa de aco; divergir dela indica fator trocado"),

    Faixa("pecas_m2", "densidade de pecas", "un/m2", 2.0, 6.0,
          "(H) modulacao de 400 a 600 mm com vigamento e contraventamento",
          "abaixo indica sistema estrutural ausente do modelo"),

    Faixa("massa_painel", "massa do painel mais pesado", "kg", 30.0, 130.0,
          "limite superior de icamento manual por 4 pessoas (NR-17 e pratica)",
          "acima exige equipamento de icamento, e isso muda a logistica"),

    # RECALIBRADA EM R36, e o motivo importa mais que o numero. Uma faixa
    # alargada porque o valor estourou deixa de verificar — e assim que a
    # verificacao vira carimbo. Esta foi alargada porque o ESCOPO DO BOM mudou:
    # ate R35 ele cobria estrutura e fechamento; agora cobre tambem esquadria
    # (R$ 313/m2), cobertura (R$ 73/m2) e impermeabilizacao. Esquadria sozinha
    # e 12 a 18 % de uma obra residencial, e estava em zero.
    #
    # A regra que fica: recalibrar faixa exige dizer O QUE MUDOU no que se
    # mede. Se a resposta for "nada, so o valor", a faixa esta certa e o
    # projeto e que precisa de explicacao.
    # R49 — a faixa e o texto mudam porque O QUE SE MEDE mudou, que e a unica
    # justificativa que esta regra aceita. A descricao dizia "NAO inclui
    # fundacao, instalacoes, acabamento" e isso deixou de ser verdade em R37 e
    # R38, quando fundacao e MEP entraram; agora entra a area externa — muro,
    # piso, piscina e paisagismo, R$ 88 mil, 17 % do total. O divisor continua
    # sendo a area FECHADA, e por isso o valor por m2 sobe sem que a casa fique
    # mais cara por metro: ele passou a carregar 286 m2 de area aberta.
    Faixa("custo_m2", "custo de TUDO o que ja esta levantado, por m2 de area "
                      "fechada", "R$/m2", 900.0, 2600.0,
          "(H) os precos da tabela sao (H): esta faixa so detecta incoerencia "
          "INTERNA, nunca preco de mercado errado. Inclui estrutura, "
          "fechamento, esquadria, cobertura, fundacao, instalacoes, brise e "
          "area externa; NAO inclui mao de obra de campo alem da declarada, "
          "mobiliario nem equipamento de piscina",
          "fora da faixa com precos (H) indica quantitativo errado, nao preco"),

    Faixa("placa_m2", "placa por area de projeto", "m2/m2", 2.0, 4.5,
          "(H) fechamento de parede em duas faces mais forro; sobrado tem "
          "mais parede por m2 de piso que casa terrea",
          "abaixo indica camada faltando no modelo — foi assim que se "
          "descobriu que piso, forro e cobertura nao tinham composicao"),

    Faixa("junta_m2", "fita e acabamento de junta", "m/m2 de placa", 1.6, 2.4,
          "(H) pratica corrente de drywall, contando junta entre placas mais "
          "arremate de borda",
          "acima indica junta contada dos dois lados: entre duas placas ha "
          "UMA junta, e entre dois paineis tambem"),

    Faixa("aprov_placa", "aproveitamento da placa", "%", 70.0, 95.0,
          "(H) placa de 2.400 num pe-direito de 2.600 obriga emenda e retalho",
          "acima de 95 sugere retalho contado como reaproveitado sem que o "
          "corte caiba de fato"),

    Faixa("concreto_m2", "concreto de radier", "m3/m2 de projeto", 0.07, 0.20,
          "(H) radier de 120 a 220 mm sobre a projecao; solo mole ou carga "
          "concentrada elevam a espessura e com ela o consumo",
          "abaixo indica area de radier menor que a projecao — falta laje "
          "sob alguma parte da casa; acima, espessura de pre-dimensionamento "
          "grande demais para o porte"),

    Faixa("armadura_radier", "taxa de armadura do radier", "kg/m3", 30.0, 90.0,
          "(H) radier residencial leve fica em 40 a 60; abaixo de 30 nao "
          "arma nem a retracao, acima de 90 e peca de carga concentrada",
          "fora da faixa indica taxa arbitrada sem calculo — e ela e (H) ate "
          "a sondagem"),

    Faixa("uso_estrutural", "utilizacao mediana dos montantes", "-", 0.05, 0.70,
          "(H) em LSF o montante corrente e governado pela modulacao da placa, "
          "nao pela carga; mediana alta indica subdimensionamento",
          "mediana acima de 0,7 significa que o sistema esta no limite e "
          "qualquer revisao de carga reprova"),
)

POR_COD = {f.cod: f for f in FAIXAS}


def medir(r: dict, area_m2: float) -> dict:
    """Extrai do resultado da liberacao as grandezas que tem faixa.

    Nada e recalculado aqui: cada valor sai de onde ja foi calculado. Uma
    verificacao que refaz a conta verifica a copia, nao o original.
    """
    plano = r["plano"]
    us = sorted(r["verificacao"]["utilizacoes"]) if r.get("verificacao") else []
    # o catalogo de massa e requisito, nao conveniencia: sem ele a massa do
    # painel sai zero e a faixa aprova o que nao mediu
    import nucleo.painel as pn
    cat = pn._catalogo_massa()
    massa_max = max((p.massa(cat) for p in r["paineis"]), default=0.0)
    return {
        "aco_m2": r["massa_comprada"] / area_m2,
        "parafusos_m2": r["n_parafusos"] / area_m2,
        "aproveitamento": plano["aproveitamento"] * 100.0,
        "horas_m2": r["horas"] / area_m2,
        "co2e_m2": r["emissao"]["total"] / area_m2,
        "pecas_m2": len(r["pecas"]) / area_m2,
        "massa_painel": massa_max,
        "custo_m2": r["custo"] / area_m2,
        "uso_estrutural": us[len(us) // 2] if us else 0.0,
        **_medir_fechamento(r, area_m2),
    }


def _medir_fechamento(r: dict, area_m2: float) -> dict:
    """As tres grandezas do fechamento, quando a paginacao existir."""
    c = r.get("camadas") or {}
    pg = c.get("paginacao")
    if not pg:
        return {}
    placa = sum(i["area_util"] for i in pg["itens"]
                if i["material"] in ("GESSO", "GESSORU", "PLCIM"))
    # PLACA, nao camada: la de rocha e XPS nao sao placa de fechamento. Medir
    # "area_total" contra uma faixa de placa deu 7,88 m2/m2 contra 2 a 4,5 — e a
    # faixa acusou, que e exatamente para o que ela serve. O erro nao era do
    # projeto, era da medicao: grandeza e faixa tem de falar da mesma coisa.
    placas = sum(i["area"] for i in c["itens"]
                 if i["material"] in ("GESSO", "GESSORU", "PLCIM", "OSB"))
    return {
        "placa_m2": placas / area_m2,
        "junta_m2": (pg["junta_m"] + pg["borda_m"]) / placa if placa else 0.0,
        "aprov_placa": (pg["area_util"] / pg["area_bruta"] * 100
                        if pg["area_bruta"] else 0.0),
        **_medir_fundacao(c),
    }


def _medir_fundacao(c: dict) -> dict:
    f = c.get("fundacao")
    if not f:
        return {}
    return {
        "concreto_m2": f["consumo_m3_m2"],
        "armadura_radier": (f["aco_kg"] / f["volume_m3"]
                            if f["volume_m3"] else 0.0),
    }


def avaliar(valores: dict) -> dict:
    """Confronta cada grandeza com a sua faixa.

    Fora da faixa NAO reprova: obriga a justificar. A diferenca importa —
    reprovar o que e apenas incomum treina quem le a ignorar o aviso, e um
    aviso ignorado e pior que aviso nenhum, porque da a impressao de vigilancia.
    """
    out, fora = [], []
    for f in FAIXAS:
        if f.cod not in valores:
            continue
        a = f.avaliar(valores[f.cod])
        out.append(a)
        if not a["dentro"]:
            fora.append(a)
    fora.sort(key=lambda a: -a["desvio"])
    return dict(avaliacoes=out, fora=fora, n=len(out),
                todas_dentro=not fora,
                pior=fora[0] if fora else None)
