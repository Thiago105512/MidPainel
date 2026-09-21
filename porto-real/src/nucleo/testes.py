"""MAPA DE TESTES E INSPECOES — por sistema, com fase, criterio e registro (R80).

O plano de qualidade estava em FALTA e os ensaios ja existiam espalhados
pelo caso (densidade do radier, SPDA, estanqueidade da piscina). Aqui cada
sistema do modelo declara o seu teste: quando (fase da obra, nucleo/canteiro),
o que se mede, com que criterio (H: norma citada) e o que fica registrado.
Os pontos criticos saem dos modulos que os criaram: furos hidraulicos nos
montantes (percurso), esgoto sob o radier antes da concretagem, cargas
suspensas (detalhes_lsf), contraventamento, impermeabilizacao.
"""
from __future__ import annotations


def testes(pj) -> list[dict]:
    import nucleo.percurso as pr
    import nucleo.circuitos as ci
    import nucleo.piscina as ps
    r = pr.resumo(pj)
    e = ci.entrada(pj)
    ag = __import__("nucleo.agua", fromlist=["reservatorio"]).reservatorio(pj)
    p_est = round(9.81 * (ag["nivel_min"]) / 1000 + 200)   # kPa: estatica maxima + margem (H)
    return [
        dict(sistema="Radier e troca de solo", fase="1", teste="densidade in situ da troca de solo (frasco de areia) e prova de carga leve",
             criterio="GC >= 95 % do Proctor normal por camada (H, NBR 7182); nivelamento +- 10 mm", registro="laudo por camada; topografia da plataforma",
             quando="antes de cada camada seguinte e antes da armacao"),
        dict(sistema="Esgoto sob o radier", fase="1", teste=f"teste de estanqueidade com agua: {r['esgoto_m']} m de ramal e coletor",
             criterio="coluna de 3 m de agua por 15 min sem queda (H, NBR 8160 11.2); caimento conferido tubo a tubo", registro="planta com os trechos testados assinada",
             quando="ANTES da concretagem do radier: depois nao se ve mais"),
        dict(sistema="Aterramento e SPDA", fase="1-3", teste="resistencia de aterramento da malha do radier e continuidade das descidas",
             criterio="<= 10 ohm (H, NBR 5419-3); continuidade < 0,2 ohm", registro="laudo com o terrometro e croqui das hastes", quando="antes do fechamento das paredes"),
        dict(sistema="LSF: montagem", fase="2", teste="prumo, nivel e esquadro de cada painel; torque dos parafusos de ancoragem; fita X tensionada",
             criterio="tolerancias da PR-67 (NBR 16970); hold-down em toda extremidade com fita", registro="checklist por painel (documentos.py, inspecao dimensional)",
             quando="painel a painel, antes de fechar a face seguinte"),
        dict(sistema="Furos de servico", fase="2", teste=f"furos dos montantes: eletrica a {pr.Z_ELETRICA} mm em todos, hidraulica a {pr.Z_AGUA} mm nos {r['paredes_com_agua']} paredes com agua",
             criterio="diametro <= meia alma, borda >= 25 mm, bucha em todo furo (peca.verificar_furos)", registro="marcacao de fabrica conferida no cavalete",
             quando="na chegada do lote, antes de montar"),
        dict(sistema="Agua fria (PEX em parede)", fase="3", teste=f"estanqueidade dos {r['pex_m']} m de PEX com a parede ABERTA",
             criterio=f"1,5 x pressao estatica maxima, minimo {p_est} kPa, 1 h sem queda (H, NBR 5626)", registro="manometro fotografado em cada ramal; parede so fecha depois",
             quando="antes das placas de fechamento interno"),
        dict(sistema="Esgoto e ventilacao (superior)", fase="3", teste="teste de fumaca ou agua nos ramais do entrepiso e nas prumadas",
             criterio="sem vazamento e sem retorno de odor; ventilacao ate a cobertura (H, NBR 8160)", registro="planta assinada", quando="antes do forro"),
        dict(sistema="Eletrica", fase="3-4", teste=f"continuidade do PE, resistencia de isolamento dos {ci.resumo(pj)['circuitos']} circuitos, DR, polaridade e queda",
             criterio=f"isolamento >= 1 Mohm a 500 V; DR dispara a 30 mA; queda <= {ci.QUEDA_MAX} % no ponto mais longe (H, NBR 5410 7.3)",
             registro=f"planilha por circuito com o megometro; laudo do padrao de {e['disjuntor_a']} A", quando="com a parede aberta (isolamento) e no fim (funcional)"),
        dict(sistema="Dados e CFTV", fase="4", teste="certificacao dos cabos UTP e teste de cada camera e AP",
             criterio="Cat.6 permanent link aprovado; cobertura Wi-Fi conferida por ambiente (PR-65)", registro="relatorio do certificador", quando="antes do forro"),
        dict(sistema="Climatizacao", fase="3-4", teste=f"pressurizacao com nitrogenio e vacuo das {len(pj.linhas_frigorigenas())} linhas frigorigenas; dreno com agua",
             criterio="N2 a 30 bar por 24 h sem queda; vacuo <= 500 microns mantido 30 min (H)", registro="manometro e vacuometro fotografados por linha",
             quando="antes de fechar a parede e antes da carga de gas"),
        dict(sistema="Gas GLP", fase="4", teste="estanqueidade da rede de cobre",
             criterio="ar ou N2 a 1,5 x pressao de trabalho, 15 min sem queda (H, NBR 15526); central a 1,5 m de vao", registro="laudo do instalador",
             quando="antes de ligar os aparelhos"),
        dict(sistema="Impermeabilizacao", fase="3-4", teste="lamina d'agua nas areas molhadas e na cobertura",
             criterio="72 h sem umidade na face oposta (H, NBR 9575)", registro="foto datada do inicio e do fim", quando="antes do revestimento"),
        dict(sistema="Piscina", fase="5", teste="teste de estanqueidade da casca e da hidraulica",
             criterio=f"72 h com nivel marcado (PR-70); hidraulica a 1,5 x pressao da bomba ({ps.bomba(pj)['h_man_m']:.0f} m.c.a.)", registro="nivel marcado e fotografado",
             quando="antes do revestimento"),
        dict(sistema="Fotovoltaica", fase="5", teste="Voc e Isc de cada string, isolamento CC, polaridade e comissionamento do inversor",
             criterio="Voc dentro de +-5 % do datasheet corrigido pela temperatura; isolamento >= 1 Mohm (H, NBR 16274)", registro="relatorio de comissionamento", quando="antes da ligacao a rede"),
        dict(sistema="Estanqueidade ao ar e a agua (envoltoria)", fase="4", teste="teste de jato d'agua nas esquadrias e inspecao das juntas de fachada",
             criterio="sem infiltracao com jato de 15 min por vao (H); juntas de movimentacao seladas (PR-69)", registro="checklist por vao", quando="antes da pintura final"),
    ]


def pontos_criticos(pj) -> list[dict]:
    import nucleo.percurso as pr
    import nucleo.detalhes_lsf as dl
    r = pr.resumo(pj)
    cs = dl.cargas_suspensas(pj)
    ct = dl.contraventamento(pj)
    return [
        dict(onde="radier", o_que=f"{r['esgoto_m']} m de esgoto embutido", risco="fica invisivel depois da concretagem", conferir="teste de agua e caimento antes de concretar; foto com trena"),
        dict(onde=f"{r['paredes_com_agua']} paredes com agua", o_que="PEX a 400 mm por furos de 32 nos montantes", risco="furo errado enfraquece o montante; parafuso de placa fura o tubo",
             conferir="furo na cota de fabrica, bucha, e a placa parafusada fora das faixas 350-450 e 1.400-1.500 mm"),
        dict(onde="todas as paredes", o_que=f"eletroduto a 1.450 mm por {r['montantes_eletrica']} montantes", risco="parafuso de placa no eletroduto",
             conferir="parafusos das placas fora da faixa 1.400-1.500; mapa de ocultos (PR-74) na obra"),
        dict(onde=f"{len(cs)} cargas suspensas", o_que="reforco de OSB na faixa de altura (PR-68)", risco="movel pendurado em placa", conferir="reforco fotografado antes de fechar"),
        dict(onde=f"{len(ct['paineis'])} paineis com fita X", o_que="hold-down e chumbador (PR-67)", risco="fita solta ou hold-down sem chumbador", conferir="torque e tensao antes do fechamento"),
        dict(onde="areas molhadas e cobertura", o_que="impermeabilizacao", risco="infiltracao no LSF", conferir="lamina d'agua de 72 h"),
        dict(onde="shaft do core", o_que="prumadas de esgoto, agua e ventilacao", risco="inspecao impossivel depois", conferir="alcapao por pavimento (SHAFT)"),
    ]


def resumo(pj) -> dict:
    t = testes(pj)
    return dict(testes=len(t), sistemas=len({x["sistema"] for x in t}), pontos_criticos=len(pontos_criticos(pj)),
                fases=sorted({x["fase"] for x in t}))


def conferir(pj) -> list[tuple[str, str, bool]]:
    t = testes(pj)
    out = []
    sistemas = {"esgoto": any("Esgoto" in x["sistema"] for x in t), "agua": any("Agua" in x["sistema"] for x in t),
                "eletrica": any("Eletrica" in x["sistema"] for x in t), "climatizacao": any("Climatizacao" in x["sistema"] for x in t),
                "gas": any("Gas" in x["sistema"] for x in t), "piscina": any("Piscina" in x["sistema"] for x in t),
                "spda": any("SPDA" in x["sistema"] for x in t), "fotovoltaica": any("Fotovoltaica" in x["sistema"] for x in t)}
    faltam = [k for k, v in sistemas.items() if not v]
    out.append(("todo sistema do modelo tem teste", ", ".join(faltam) if faltam else f"{len(t)} testes em {len(sistemas)} sistemas", not faltam))
    sem = [x["sistema"] for x in t if not x["criterio"] or not x["registro"]]
    out.append(("todo teste tem criterio e registro", ", ".join(sem) if sem else "todos", not sem))
    cedo = [x["sistema"] for x in t if "radier" in x["sistema"].lower() and x["fase"] != "1"]
    out.append(("o que fica escondido testa antes de esconder", ", ".join(cedo) if cedo else "esgoto do radier na fase 1, PEX com a parede aberta", not cedo))
    return out
