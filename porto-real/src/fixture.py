"""FIXTURE — o modelo construido UMA vez, para auditoria e produto olharem o mesmo.

ONDE ESTE ARQUIVO MORA, E POR QUE NAO EM nucleo/. A primeira versao ficou em
nucleo/fixture.py e a auditoria da E0 reprovou na mesma execucao: "o motor
importa 'projeto': a separacao se desfez". Estava certa. O motor nao conhece
caso nenhum — e a fixture e, por definicao, o modelo DE UM CASO. O lugar dela e
ao lado do caso, e a auditoria que separa os dois e mais confiavel que a minha
memoria de onde as coisas vao.

Ate R32 cada bateria de auditoria montava o seu proprio modelo: catorze chamadas
a painelizar() num unico programa, cada uma refazendo painelizacao,
dimensionamento e detalhamento. Funcionava, e custava caro de um jeito que nao
aparece no relogio.

O custo real nao e o tempo. E que duas construcoes separadas do mesmo modelo
podem DIVERGIR — e isso ja aconteceu neste projeto. Quando a segunda passada de
dimensionamento de jamba morava dentro da liberacao, a auditoria montava o
painel sem ela e verificava outra coisa que nao o produto. A correcao daquela
vez foi mover a funcao de lugar; a correcao desta vez e tirar a possibilidade.

O que este modulo garante nao e velocidade: e que auditoria, exportacao,
desenho e liberacao consultem o MESMO objeto. Divergencia por esquecimento
deixa de ser possivel, em vez de deixar de acontecer por disciplina — e
disciplina e o que falha na decima quarta vez.

Uso:
    from nucleo.fixture import modelo
    m = modelo()           # constroi na primeira chamada, devolve o mesmo depois
    m["paineis"], m["ctx"], m["pecas"], m["liberacao"]

`modelo(fresco=True)` forca uma reconstrucao — necessario quando um teste muda o
caso de proposito, e so nesse caso.
"""
from __future__ import annotations

_CACHE: dict = {}


def modelo(pj=None, el=None, cfg=None, fresco: bool = False) -> dict:
    """O modelo do caso, construido uma vez por processo.

    A chave do cache inclui a revisao do caso: se alguem trocar de projeto ou
    bumpar a revisao no meio da execucao, o cache nao entrega o modelo velho.
    """
    import projeto as _pj
    import elementos as _el
    import nucleo.painel as pn
    import nucleo.perfis as pf
    import nucleo.materiais as mt
    import nucleo.descida as ds

    pj = pj or _pj
    el = el or _el
    cfg = cfg or pn.Config()
    chave = (pj.CADASTRO.project_id, pj.EMISSAO["revisao"], id(cfg.__class__),
             cfg.modulacao, cfg.altura, cfg.perfil_stud, cfg.u_alvo)
    if not fresco and _CACHE.get("chave") == chave:
        return _CACHE["valor"]

    aco = mt.POR_ACO["ZAR 230"]
    cat = pn._catalogo_massa()
    perfis = list(pf.catalogo())
    paineis = {pav: pn.painelizar(el.derivar_paredes(amb),
                                  list(el.vaos_do_pavimento(pav)), cfg,
                                  f"{pav}P")
               for pav, amb in (("T", pj.TERREO), ("S", pj.SUPERIOR))}
    dim = ds.dimensionar(paineis, aco, pj.CARGAS, cfg, perfis)
    todos = paineis["T"] + paineis["S"]

    valor = dict(pj=pj, el=el, cfg=cfg, aco=aco, cat=cat, perfis=perfis,
                 por_cod={q.cod: q for q in perfis},
                 paineis=paineis, todos=todos, ctx=dim["ctx"],
                 jambas=dim["jambas"], apertadas=dim["apertadas"],
                 acima_de=dict(T=paineis["S"], S=[]))
    _CACHE["chave"], _CACHE["valor"] = chave, valor
    return valor


def liberacao(fresco: bool = False) -> dict:
    """O resultado da cadeia inteira, tambem uma vez por processo.

    `liberacao.rodar()` custa alguns segundos e era chamada cinco vezes num
    unico programa de auditoria. Nao e o tempo que incomoda: e que cinco
    execucoes sao cinco oportunidades de divergir.
    """
    import projeto as pj
    import elementos as el
    import nucleo.liberacao as lb
    chave = (pj.CADASTRO.project_id, pj.EMISSAO["revisao"])
    if not fresco and _CACHE.get("lib_chave") == chave:
        return _CACHE["lib_valor"]
    r = lb.rodar(pj, el)
    _CACHE["lib_chave"], _CACHE["lib_valor"] = chave, r
    return r


def limpar() -> None:
    """Descarta o cache. So faz sentido em teste que altera o caso."""
    _CACHE.clear()
