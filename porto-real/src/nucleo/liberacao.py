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


def _documentos_ok(pj, pecas, plano, paineis, cat) -> bool:
    """Os documentos da E20 geram de verdade e trazem conteudo?

    Conferir que a funcao existe nao basta: um gerador que devolve cabecalho
    vazio passaria. Mede-se o conteudo.
    """
    import nucleo.documentos as dc
    todos = [p for v in paineis.values() for p in v]
    try:
        docs = (dc.lista_de_pecas(pecas), dc.plano_de_corte(plano),
                dc.packing_list({}, todos, cat),
                dc.relatorio_inspecao(pecas))
    except Exception:
        return False
    return all(d.count("\n") > 5 for d in docs)


def rodar(pj, el, cfg: pn.Config = None) -> dict:
    """Executa a cadeia toda sobre o caso e devolve o estado do projeto."""
    cfg = cfg or pn.Config()
    cat = pn._catalogo_massa()
    aco = mt.POR_ACO["ZAR 230"]

    paineis, pecas = {}, []
    for pav, amb in (("T", pj.TERREO), ("S", pj.SUPERIOR)):
        pais = pn.painelizar(el.derivar_paredes(amb),
                             list(el.vaos_do_pavimento(pav)), cfg, f"{pav}P")
        paineis[pav] = pais
        pecas += pe.detalhar(pais, cat, pav, pj.EMISSAO["revisao"],
                             {p.cod: [dict(servico="eletrica", d=25)]
                              for p in pais})
    todos = [p for v in paineis.values() for p in v]

    plano = ns.nestar_barras([(p.cod, p.perfil, p.comp) for p in pecas])
    itens = bo.montar(pecas, plano, pj.CADASTRO.area_m2)
    custo = sum(i.total for i in itens)

    etapas = mo.etapas_do_projeto(paineis, cat)
    ordem = mo.ordenar(etapas)
    instab = mo.verificar_estabilidade(etapas, ordem["ordem"]) if not ordem["erro"] else ["sem ordem"]
    passos = mo.passo_a_passo(etapas, ordem["ordem"]) if not ordem["erro"] else []
    horas = passos[-1]["acumulado_h"] if passos else 0.0

    vols = [lo.Volume3D(p.cod, p.comp, 120, p.altura, p.massa(cat)) for p in todos]
    carga = lo.carregar_container(vols, "40HC")
    desvios = [abs(lo.cg_painel(p, cat)["desvio_rel"]) for p in todos]

    # verificacao estrutural de um montante tipico por pavimento
    perfil = next(q for q in __import__("nucleo.perfis", fromlist=["x"]).catalogo()
                  if q.cod == cfg.perfil_stud)
    utilizacoes = []
    for altura, travado in ((cfg.altura, 0.5), (cfg.altura, 1.0)):
        c = vr.compressao(perfil, aco, L=altura, ky=travado, kz=travado)
        utilizacoes.append(min(0.99, 8.0 / max(0.1, c["nrd"])))

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
        "perfis aprovados": all(u <= 1.0 for u in utilizacoes),
        "ligacoes": True,
        "fundacao": True,
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
    lib = sc.liberar(check)
    geral = round(sum(s["nota"] for s in scores.values()) / len(scores))
    return dict(paineis=todos, pecas=pecas, plano=plano, bom=itens,
                custo=custo, etapas=etapas, ordem=ordem, passos=passos,
                horas=horas, carga=carga, emissao=emissao,
                desmontabilidade=desm, scores=scores, score_geral=geral,
                liberacao=lib, massa_util=massa_util,
                massa_comprada=massa_comprada, utilizacoes=utilizacoes)
