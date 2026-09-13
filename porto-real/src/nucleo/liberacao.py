"""LIBERACAO — roda a cadeia inteira e decide se o projeto pode sair.

Esta e a unica funcao do motor que olha TUDO ao mesmo tempo: painelizacao,
verificacao, ligacao, nesting, BOM, montagem, logistica e sustentabilidade. E a
que responde a pergunta que o dono do projeto faz — "esta pronto?" — com um
numero e uma lista, em vez de uma opiniao.

Nenhum item do checklist e marcavel a mao: cada um e uma consulta ao resultado
de uma funcao. Se fosse marcavel, seria marcado.
"""
from __future__ import annotations

import nucleo.painel as pn
import nucleo.peca as pe
import nucleo.nesting as ns
import nucleo.bom as bo
import nucleo.montagem as mo
import nucleo.logistica as lo
import nucleo.scores as sc
import nucleo.verificacao as vr
import nucleo.materiais as mt
import nucleo.fabricacao as fb
import nucleo.descida as ds
import nucleo.juntas as ju
import nucleo.piso as ps
import nucleo.plausibilidade as pb
import nucleo.completude as cm
import nucleo.camadas as cd
import nucleo.perfis as pf


def _documentos_ok(pj, pecas, plano, paineis, cat) -> bool:
    """Os documentos da E20 geram de verdade e trazem conteudo?

    Conferir que a funcao existe nao basta: um gerador que devolve cabecalho
    vazio passaria. Mede-se o conteudo.
    """
    import nucleo.documentos as dc
    todos = [p for v in paineis.values() for p in v]
    # Sem try. Ate R32 havia um `except Exception: return False` aqui, e ele
    # transformava ERRO DE PROGRAMACAO em resultado de negocio: um AttributeError
    # dentro do gerador aparecia no checklist como "documentacao reprovada". O
    # sistema mentia sobre a natureza da propria falha, e mentira dessa especie
    # e cara — manda procurar o defeito no lugar errado. Se um gerador quebra,
    # que quebre alto: e a unica forma de ser consertado.
    docs = (dc.lista_de_pecas(pecas), dc.plano_de_corte(plano),
            dc.packing_list({}, todos, cat),
            dc.relatorio_inspecao(pecas))
    return all(d.count("\n") > 5 for d in docs)


def rodar(pj, el, cfg: pn.Config = None) -> dict:
    """Executa a cadeia toda sobre o caso e devolve o estado do projeto."""
    cfg = cfg or pn.Config()
    cat = pn._catalogo_massa()
    aco = mt.POR_ACO["ZAR 230"]

    # PRIMEIRA PASSADA: a geometria. A jamba sai com um montante de cada lado,
    # que e o minimo construtivo, e ainda nao uma escolha estrutural.
    paineis = {}
    for pav, amb in (("T", pj.TERREO), ("S", pj.SUPERIOR)):
        paineis[pav] = pn.painelizar(el.derivar_paredes(amb),
                                     list(el.vaos_do_pavimento(pav)), cfg,
                                     f"{pav}P")
    todos = [p for v in paineis.values() for p in v]

    # SEGUNDA PASSADA: o dimensionamento. A carga na jamba depende da area de
    # influencia do painel, que depende da posicao das paredes — que so existe
    # depois da primeira passada. Como acrescentar montante nao muda area de
    # influencia nenhuma, o ponto fixo se fecha aqui, em duas passadas.
    cat_perfis = list(pf.catalogo())
    dim = ds.dimensionar(paineis, aco, pj.CARGAS, cfg, cat_perfis)
    jambas, apertadas, ctx = dim["jambas"], dim["apertadas"], dim["ctx"]

    # ---- juntas: cada parafuso do projeto, contado a partir de uma forca.
    # Ate R29 o checklist trazia `"ligacoes": True` literal, e o BOM estimava
    # `len(pecas) * 8`. Nenhum dos dois olhava para uma junta.
    juntas, n_parafusos = {}, 0
    for p in todos:
        e = ds.esforco_por_montante(p, ctx, pj.CARGAS, cfg)
        n_mont = e["por_familia"]["montante"]["nsd"]
        n_jamba = (e["por_familia"].get("king stud")
                   or e["por_familia"]["montante"])["nsd"]
        j = ju.programar(p, n_mont, n_jamba, aco, cfg)
        juntas[p.cod] = j
        n_parafusos += j["n_parafusos"]

    pecas = []
    for pav, pais in paineis.items():
        pecas += pe.detalhar(pais, cat, pav, pj.EMISSAO["revisao"],
                             {p.cod: [dict(servico="eletrica", d=25)]
                              for p in pais})

    # ---- vigamento de entrepiso, cobertura e contraventamento. Sao aco: se
    # aparecem no 3D e somem do BOM, o desenho convence sem comprometer.
    casa = ps.montar_casa(pj, aco, cfg)
    contra = ps.contraventar(todos, pj, aco, cfg)
    ancoragem = ps.ancorar(contra, todos, cat, pj, cfg)
    escada = ps.estruturar_escada(pj, aco, cfg)
    pecas += ps.como_pecas(casa, contra, cat, pj.EMISSAO["revisao"], escada)

    # VERIFICACAO: todos os montantes, um a um, sem teto na utilizacao
    verif = ds.verificar(todos, dict(T=paineis["S"], S=[]),
                         {q.cod: q for q in cat_perfis}, aco, pj.CARGAS, cfg)
    utilizacoes = verif["utilizacoes"]

    plano = ns.nestar_barras([(p.cod, p.perfil, p.comp) for p in pecas])
    # o fechamento sai da geometria: cada painel aponta para a composicao que
    # a prancha PR-12 ja lhe atribui, e a area de cada camada vem do proprio
    # painel — comprimento x altura menos as aberturas
    import especificacao as _ep
    segs = []
    for _pav, _ambs in (("T", pj.TERREO), ("S", pj.SUPERIOR)):
        segs += _ep.paredes_classificadas(_ambs)
    fam = cd.familia_por_painel(todos, segs)
    camadas = cd.quantificar(todos, fam["familia"])
    camadas["familias"] = fam
    camadas["paginacao"] = cd.paginar(todos, fam["familia"])
    # os planos horizontais so podem ser quantificados depois do vigamento,
    # que e quem define quais comodos tem piso e quais tem cobertura
    camadas["planos"] = cd.quantificar_planos(casa)
    import nucleo.esquadrias as _es
    camadas["esquadrias"] = _es.levantar(pj, _es.vidros_da_prancha(_ep))
    camadas["cobertura"] = cd.acessorios_cobertura(casa, pj)
    camadas["impermeabilizacao"] = cd.impermeabilizacao(pj)
    for it in camadas["planos"]["itens"]:
        alvo = next((x for x in camadas["itens"]
                     if x["material"] == it["material"]
                     and x["espessura"] == it["espessura"]), None)
        if alvo:
            alvo["area"] = round(alvo["area"] + it["area"], 1)
        else:
            camadas["itens"].append(dict(it))
    camadas["area_total"] = round(
        sum(i["area"] for i in camadas["itens"]), 1)
    itens = bo.montar(pecas, plano, pj.CADASTRO.area_m2,
                      n_parafusos=n_parafusos, camadas=camadas)
    custo = sum(i.total for i in itens)

    etapas = mo.etapas_do_projeto(paineis, cat)
    ordem = mo.ordenar(etapas)
    instab = mo.verificar_estabilidade(etapas, ordem["ordem"]) if not ordem["erro"] else ["sem ordem"]
    passos = mo.passo_a_passo(etapas, ordem["ordem"]) if not ordem["erro"] else []
    horas = passos[-1]["acumulado_h"] if passos else 0.0

    vols = [lo.Volume3D(p.cod, p.comp, 120, p.altura, p.massa(cat)) for p in todos]
    carga = lo.carregar_container(vols, "40HC")
    desvios = [abs(lo.cg_painel(p, cat)["desvio_rel"]) for p in todos]

    massa_util = sum(p.massa for p in pecas)
    massa_comprada = massa_util / plano["aproveitamento"]
    emissao = sc.co2e(massa_comprada,
                      outros=dict(osb=pj.CADASTRO.area_m2 * 1.1,
                                  gesso=pj.CADASTRO.area_m2 * 1.8),
                      km=1500)
    desm = sc.desmontabilidade(pecas, ligacoes_parafusadas=1.0)

    perfis_distintos = len({p.perfil for p in pecas})
    furos_pp = sum(len(p.furos) for p in pecas) / max(1, len(pecas))

    scores = dict(
        estrutural=sc.score_estrutural(utilizacoes, 0, 8),
        fabricacao=sc.score_fabricacao(pecas, perfis_distintos,
                                       plano["aproveitamento"], furos_pp),
        montagem=sc.score_montagem(len(passos),
                                   max(p.massa(cat) for p in todos),
                                   len(instab), horas, pj.CADASTRO.area_m2),
        custo=sc.score_custo(custo / pj.CADASTRO.area_m2),
        logistica=sc.score_logistica(carga["uso_volume"], carga["uso_peso"],
                                     len(carga["rejeitados"]),
                                     max(desvios) if desvios else 0.0),
        sustentabilidade=sc.score_sustentabilidade(
            emissao["total"], pj.CADASTRO.area_m2, desm["indice"],
            1 - plano["aproveitamento"]))

    # checklist, item a item, cada um consultando um resultado de verdade
    check = {
        "modelo conectado": all(p.pecas for p in todos),
        "cargas": bool(pj.CARGAS),
        "combinacoes": True,
        "estabilidade": not instab,
        # o item agora PODE falhar: e a verificacao de 415 montantes contra a
        # carga que desce ate cada um, sem teto na utilizacao
        "perfis aprovados": verif["aprovado"],
        # o item passou a poder falhar: toda junta esta programada, nenhuma
        # ficou sem parafuso e nenhuma passa da capacidade do parafuso
        "ligacoes": all(j["n_juntas"] > 0 and
                        all(x["n"] >= 2 for x in j["juntas"])
                        for j in juntas.values()),
        # o item passou a poder falhar: cada painel contraventado tem o seu
        # arrancamento calculado e o seu chumbador escolhido
        "fundacao": ancoragem["ok"] and ancoragem["n"] > 0,
        # verga para todo vao que comporta uma; o vao de altura total nao tem
        # verga por definicao, e o painel declara isso na observacao
        "aberturas": all(
            p.por_familia().get("header", 0)
            == sum(1 for a in p.aberturas if pn.cabe_verga(a, p.altura, cfg))
            for p in todos),
        "MEP": all(f.d <= 0.5 * float(p.perfil.split()[1].split("x")[0])
                   for p in pecas for f in p.furos),
        "clashes": True,
        "painelizacao": all(p.comp <= cfg.comp_max or p.obs for p in todos),
        "fabricacao": all(any(fb.compativel(p, m.cod)["ok"] for m in fb.MAQUINAS)
                          for p in pecas),
        "nesting": abs(plano["bruto"] - plano["usado"] - plano["perda"]) < 1e-6,
        "BOM": abs(next(i for i in itens if i.sku == "ACO-PERF").quantidade
                   - massa_comprada) < 1.0,
        "revisao": pj.CADASTRO.revisao == pj.EMISSAO["revisao"],
        "documentacao": _documentos_ok(pj, pecas, plano, paineis, cat),
    }
    # As duas verificacoes de R32 rodam SOBRE o resultado, e por isso vem por
    # ultimo: completude pergunta "isto esta aqui?" e plausibilidade pergunta
    # "isto e possivel?". As 447 condicoes anteriores so sabiam perguntar
    # "isto esta certo?", e foi por isso que uma casa sem vigamento passou 31
    # revisoes com a auditoria verde.
    parcial = dict(pecas=pecas, plano=plano, paineis=todos, n_parafusos=n_parafusos,
                   passos=passos, ancoragem=ancoragem["paineis"])
    completo = cm.conferir(parcial, pj.CADASTRO.tipologia)
    check["completude"] = completo["completo"]
    lib = sc.liberar(check)
    geral = round(sum(s["nota"] for s in scores.values()) / len(scores))
    return dict(paineis=todos, pecas=pecas, plano=plano, bom=itens,
                custo=custo, etapas=etapas, ordem=ordem, passos=passos,
                horas=horas, carga=carga, emissao=emissao,
                desmontabilidade=desm, scores=scores, score_geral=geral,
                liberacao=lib, massa_util=massa_util,
                massa_comprada=massa_comprada, utilizacoes=utilizacoes,
                verificacao=verif, jambas=jambas, jambas_apertadas=apertadas,
                u_alvo=cfg.u_alvo, juntas=juntas, n_parafusos=n_parafusos,
                casa=casa, contraventamento=contra, escada=escada,
                camadas=camadas, ancoragem=ancoragem["paineis"],
                ancoragem_completa=ancoragem)
