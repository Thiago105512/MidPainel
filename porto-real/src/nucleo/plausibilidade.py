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

    Faixa("custo_m2", "custo da estrutura", "R$/m2", 350.0, 1200.0,
          "(H) os precos da tabela sao (H): esta faixa so detecta incoerencia "
          "INTERNA, nunca preco de mercado errado",
          "fora da faixa com precos (H) indica quantitativo errado, nao preco"),

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
    cat = None
    try:
        import nucleo.painel as pn
        cat = pn._catalogo_massa()
    except Exception:
        pass
    massa_max = max((p.massa(cat) for p in r["paineis"]), default=0.0) if cat else 0.0
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
