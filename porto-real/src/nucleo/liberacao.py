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
import nucleo.combinacoes as cb


def _documentos_ok(pj, pecas, plano, paineis, cat, carga=None) -> bool:
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
            dc.packing_list(carga, todos, cat),
            dc.relatorio_inspecao(pecas))
    return all(d.count("\n") > 5 for d in docs)


def rodar(pj, el, cfg: pn.Config = None) -> dict:
    """Executa a cadeia toda sobre o caso e devolve o estado do projeto."""
    # R61 — a altura do painel e o pe-direito do PROJETO. Um Config() default
    # aqui painelizava a 2.600 enquanto o modelo ja estava a 2.900: 64 pecas
    # de guia com codigo diferente entre a fabrica e a cena.
    cfg = cfg or pn.Config(altura=pj.PE_DIREITO, modulacao=pj.MONTANTE_ESPACAMENTO)
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
    ds.PILARES_XY = {(q["x"], q["y"]) for q in getattr(pj, "PILARES", [])}
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
    # R80 — eletrica em todo painel (furo de 25 a 1.450); hidraulica (32 a 400)
    # so nos paineis das paredes por onde nucleo/percurso leva a agua
    import nucleo.percurso as _pr
    for pav, pais in paineis.items():
        pecas += pe.detalhar(pais, cat, pav, pj.EMISSAO["revisao"],
                             _pr.servicos_por_painel(pj, pais))

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
    # R59 — quem nao recebe forro vem do quadro de forros do projeto, nao de
    # lista escrita aqui: "sem forro" no quadro e a unica fonte.
    sem_forro = tuple(f[0] for f in pj.FORROS_SRC() if "estrutura aparente" in f[1].lower())
    camadas["planos"] = cd.quantificar_planos(casa, sem_forro)
    import nucleo.esquadrias as _es
    camadas["esquadrias"] = _es.levantar(pj, _es.vidros_da_prancha(_ep))
    camadas["cobertura"] = cd.acessorios_cobertura(casa, pj)
    camadas["impermeabilizacao"] = cd.impermeabilizacao(pj)
    import nucleo.fundacao as _fd
    camadas["fundacao"] = _fd.levantar(pj)
    import nucleo.spda as _sp
    import nucleo.fotovoltaica as _fv
    camadas["spda"] = _sp.levantar(pj, camadas["cobertura"], camadas["fundacao"])
    camadas["fotovoltaica"] = _fv.levantar(pj, camadas["planos"])
    import nucleo.externo as _ex
    camadas["externo"] = _ex.levantar(pj)
    import nucleo.fachada as _fa
    camadas["brises"] = _fa.brises(pj)
    camadas["fascia"] = _fa.fascia(pj)
    # R68 — a declividade do lote vira plataforma, cota de piso e rampa
    import nucleo.terreno as _tr
    camadas["terreno"] = dict(
        plataforma=_tr.plataforma(pj), acessos=_tr.acessos(pj),
        gravidade=_tr.gravidade(pj),
        plataforma_min=_tr.plataforma(pj, pj.DECLIVIDADE_MIN))
    camadas["platibanda"] = _fa.platibanda(pj)
    camadas["faces"] = _fa.faces(pj)
    import nucleo.instalacoes as _ins
    _base = dict(T=pj.NIVEL_TERREO, S=pj.NIVEL_SUPERIOR)
    # A decisao do shaft vem ANTES de medir ramal e de conferir clash, porque
    # as duas leem a posicao. Uma fonte so: quem mede, quem monta volume e quem
    # confere leem de prumadas_efetivas().
    shafts = _ins.resolver_shafts(pj, todos, _base)
    camadas["shafts"] = shafts
    # R80 — o percurso parede a parede (nucleo/percurso) e o que a BOM compra:
    # eletroduto pela arvore de cada circuito, cabo pelo circuito dimensionado,
    # PEX pelo trecho real, e os fixadores contados montante a montante
    import nucleo.percurso as _prc
    import nucleo.circuitos as _cir
    camadas["instalacoes"] = dict(hidraulica=_ins.hidraulica(pj, shafts),
                                  eletrica=_ins.eletrica(pj),
                                  climatizacao=_ins.climatizacao(pj),
                                  shafts=shafts,
                                  percurso=dict(resumo=_prc.resumo(pj), fixadores=_prc.fixadores(pj),
                                                cabo_m=_cir.resumo(pj)["cabo_m"]))
    camadas["clash"] = _ins.conferir_clash(pj, todos, _base, shafts)
    # a decisao tem MATERIAL: enclausurar a caixa consome placa RU. Se a
    # decisao existisse so como coordenada, o orcamento nao saberia dela.
    if shafts["placa_m2"] > 0:
        # MERGE, nao append: a placa do shaft e a mesma placa RU de 12,5 mm que
        # ja esta na lista. Duas linhas do mesmo material com a mesma espessura
        # viram dois itens de BOM com o MESMO SKU — e o contrato do ERP diz que
        # a chave de SKU e o que liga preco a quantidade. SKU repetido nao
        # recebe cotacao: recebe duas cotacoes que ninguem sabe somar.
        alvo = next((x for x in camadas["itens"]
                     if x["material"] == "GESSORU" and x["espessura"] == 12.5),
                    None)
        if alvo:
            alvo["area"] = round(alvo["area"] + shafts["placa_m2"], 1)
        else:
            camadas["itens"].append(dict(material="GESSORU", espessura=12.5,
                                         area=shafts["placa_m2"]))
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
    import nucleo.acabamento as ab
    acab = ab.levantar(pj, camadas)
    # R86 — pilar e viga laminada entram no custo. A massa e derivada aqui,
    # onde o caso esta disponivel, e vai ao motor como dado: nucleo nao importa
    # projeto (a auditoria cobra essa separacao, e cobrou na primeira execucao).
    _h = pj.PILAR_ALTURA / 1_000
    _lam = dict(pilares=[], vigas=[])
    for sku, lista, secao, rot in (
            ("EST-PILAR", [q for q in pj.PILARES if not q.get("embutido")], pj.PILAR_SECAO, "aparente"),
            ("EST-PILAR-EMB", [q for q in pj.PILARES if q.get("embutido")], pj.PILAR_SECAO_EMBUTIDO, "embutido na parede")):
        if lista:
            _lam["pilares"].append(dict(
                sku=sku, secao=secao, rot=rot,
                kg=len(lista) * _h * pj.PILAR_MASSA_KG_M[secao],
                fonte=f"derivado: {len(lista)} pilares x {_h:g} m x {pj.PILAR_MASSA_KG_M[secao]:g} kg/m"))
    _por_w: dict = {}
    for v in pj.dimensionar_vigas():
        comp = v["vao"] * v.get("tramos", 1) / 1_000
        d = _por_w.setdefault(v["perfil"], [0, 0.0, []])
        d[0] += 1; d[1] += comp * pj.PERFIS_LAMINADOS[v["perfil"]]["massa"]; d[2].append(v["cod"])
    for perfil, (n_v, kg, cods) in sorted(_por_w.items(), key=lambda kv: -kv[1][1]):
        _lam["vigas"].append(dict(perfil=perfil, kg=kg,
                                  fonte=f"derivado do vao e da flecha: {n_v} viga(s) — {', '.join(sorted(cods))}"))
    itens = bo.montar(pecas, plano, pj.CADASTRO.area_m2,
                      n_parafusos=n_parafusos, camadas=camadas,
                      acabamento=acab, laminados=_lam)
    # o custo e o que se COMPRA. A regra mora no BOM: quando morava aqui, na
    # forma de sum(i.total), esta linha somava o aco duas vezes — em kg e em pc.
    custo = bo.total(itens)

    etapas = mo.etapas_do_projeto(paineis, cat)
    ordem = mo.ordenar(etapas)
    instab = mo.verificar_estabilidade(etapas, ordem["ordem"]) if not ordem["erro"] else ["sem ordem"]
    passos = mo.passo_a_passo(etapas, ordem["ordem"]) if not ordem["erro"] else []
    horas = passos[-1]["acumulado_h"] if passos else 0.0

    vols = [lo.Volume3D(p.cod, p.comp, 120, p.altura, p.massa(cat)) for p in todos]
    carga = lo.plano_de_transporte(vols)     # R69: container se couber, senao carreta
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

    # ---- o ultimo literal do checklist. "combinacoes": True nao era mentira:
    # as combinacoes existem, sao geradas e sao usadas. Mas um item que nao
    # pode reprovar nao verifica nada. Sao duas perguntas distintas, e a
    # segunda e a que morde: (1) os fatores sao os das tabelas da NBR 8681,
    # recalculados sem passar por gerar()? (2) toda acao DECLARADA no caso e
    # consumida por alguma verificacao? Uma acao pode estar perfeitamente
    # declarada, com gama e psi certos, e nao entrar em calculo nenhum —
    # existir no papel e nao existir no calculo e a forma mais silenciosa de
    # erro que este projeto ja encontrou.
    comb_conf = cb.conferir(verif["combs"], verif["acoes_cod"],
                            verif["subclasses"])
    declaradas = {
        "permanente": [k for k in pj.CARGAS if k.endswith(("_perm", "_m"))],
        "acidental": [k for k in pj.CARGAS if k.endswith("_acid")],
        "vento": ["V0_VENTO"] if getattr(pj, "V0_VENTO", None) else [],
    }
    # cada verificacao declara o que consumiu a partir da chamada que fez
    consumidas = {"descida de cargas": verif["acoes"],
                  "contraventamento": contra["acoes"]}
    comb_cob = cb.cobertura_de_acoes(declaradas, consumidas)
    combinacoes = dict(conferencia=comb_conf, cobertura=comb_cob,
                       ok=comb_conf["ok"] and comb_cob["ok"])

    # o que o caderno declara aberto tranca o que ele mesmo diz trancar
    pendencias_bloqueantes = (pj.pendencias_abertas("fabricacao")
                              if hasattr(pj, "pendencias_abertas") else [])

    # checklist, item a item, cada um consultando um resultado de verdade
    check = {
        "modelo conectado": all(p.pecas for p in todos),
        "cargas": bool(pj.CARGAS),
        "combinacoes": combinacoes["ok"],
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
        # o ultimo literal cai: o item era True desde sempre porque nao havia
        # com o que conflitar — a estrutura so ganhou vigamento em R31 e o MEP
        # so ganhou tracado agora. Verificar interferencia contra o vazio acha
        # zero conflitos, e o zero e verdadeiro e inutil.
        "clashes": camadas["clash"]["ok"],
        "painelizacao": all(p.comp <= cfg.comp_max or p.obs for p in todos),
        "fabricacao": all(any(fb.compativel(p, m.cod)["ok"] for m in fb.MAQUINAS)
                          for p in pecas),
        "nesting": abs(plano["bruto"] - plano["usado"] - plano["perda"]) < 1e-6,
        "BOM": abs(next(i for i in itens if i.sku == "ACO-PERF").quantidade
                   - massa_comprada) < 1.0,
        # O item que faltava, e a sua ausencia era a mais grave de todas: o
        # checklist media a coerencia do MODELO e anunciava "LIBERADO PARA
        # FABRICACAO" com oito pendencias abertas no proprio caderno, duas
        # delas — ART do calculo estrutural e nesting codificado — trancando
        # exatamente a fabricacao. Consistencia interna nao e autorizacao.
        "pendencias": not pendencias_bloqueantes,
        "revisao": pj.CADASTRO.revisao == pj.EMISSAO["revisao"],
        "documentacao": _documentos_ok(pj, pecas, plano, paineis, cat, carga),
    }
    # As duas verificacoes de R32 rodam SOBRE o resultado, e por isso vem por
    # ultimo: completude pergunta "isto esta aqui?" e plausibilidade pergunta
    # "isto e possivel?". As 447 condicoes anteriores so sabiam perguntar
    # "isto esta certo?", e foi por isso que uma casa sem vigamento passou 31
    # revisoes com a auditoria verde.
    # O dicionario que a completude consulta e o MESMO que a funcao devolve —
    # nao uma copia parcial. A primeira versao montava um `parcial` com seis
    # chaves escolhidas a mao, e quando a fundacao entrou no modelo a chave
    # `camadas` nao estava la: a completude leu volume zero e reprovou o
    # projeto por falta de fundacao, que existia. Duas construcoes do mesmo
    # dado divergem na primeira chave nova — pela quarta vez nesta sessao.
    parcial = dict(pecas=pecas, plano=plano, paineis=todos,
                   n_parafusos=n_parafusos, passos=passos,
                   ancoragem=ancoragem["paineis"], camadas=camadas)
    completo = cm.conferir(parcial, pj.CADASTRO.tipologia)
    check["completude"] = completo["completo"]
    lib = sc.liberar(check)
    geral = round(sum(s["nota"] for s in scores.values()) / len(scores))
    # ---- cotacao: o mapa que se manda ao fornecedor, e quanto do custo ja
    # foi perguntado a alguem. Precisa do resultado quase pronto, por isso vem
    # aqui: a especificacao de cada linha sai do modelo inteiro — norma do
    # material, designacao do perfil, DN da instalacao, fck da fundacao.
    # ---- dossie por comodo: o eixo em que a verificacao nao existia. Vem
    # depois das camadas porque le a composicao de cada parede que cerca o
    # comodo, e depois dos paineis porque e deles que a parede vem.
    import nucleo.ambiente as amb
    ambientes = amb.conferir(pj, dict(paineis=todos, camadas=camadas))

    # ---- catalogo tecnico: o desenho de cada peca, gerado da propria peca.
    # Vem depois de tudo porque le peca, junta, camada e instalacao — e porque
    # o desenho e VISTA do modelo, nunca uma fonte paralela.
    import nucleo.fachada as _fa2
    fachada = _fa2.conferir(pj, dict(pecas=pecas))

    import nucleo.catalogo as cg
    catalogo = cg.montar(pj, dict(pecas=pecas, juntas=juntas, camadas=camadas))

    import nucleo.cotacao as co
    _parcial = dict(bom=itens, plano=plano, juntas=juntas, camadas=camadas)
    cot = dict(mapa=co.mapa(_parcial),
               cobertura=co.cobertura(itens),
               sensibilidade=[co.sensibilidade(itens, f, 0.20)
                              for f in sorted({i.familia for i in itens})])

    # ---- viabilidade: o que falta, quem fecha e QUANTO DO PROJETO depende
    # disso. Vem por ultimo porque mede exposicao sobre o custo e sobre o
    # levantamento inteiro — precisa deles prontos.
    import nucleo.viabilidade as vi
    _rv = dict(custo=custo, bom=itens, camadas=camadas, plano=plano,
               verificacao=verif, cotacao=cot)
    viabilidade = vi.avaliar(pj, _rv)

    return dict(cotacao=cot, ambientes=ambientes, catalogo=catalogo,
                viabilidade=viabilidade,
                fachada=fachada,
                paineis=todos, pecas=pecas, plano=plano, bom=itens,
                custo=custo, etapas=etapas, ordem=ordem, passos=passos,
                horas=horas, carga=carga, emissao=emissao,
                desmontabilidade=desm, scores=scores, score_geral=geral,
                liberacao=lib, massa_util=massa_util,
                massa_comprada=massa_comprada, utilizacoes=utilizacoes,
                verificacao=verif, jambas=jambas, jambas_apertadas=apertadas,
                u_alvo=cfg.u_alvo, juntas=juntas, n_parafusos=n_parafusos,
                casa=casa, contraventamento=contra, escada=escada,
                combinacoes=combinacoes,
                pendencias=dict(
                    abertas=[dict(d) for d in
                             (pj.pendencias_abertas()
                              if hasattr(pj, "pendencias_abertas") else [])],
                    bloqueantes=[dict(d) for d in pendencias_bloqueantes],
                    portao="fabricacao"),
                camadas=camadas, ancoragem=ancoragem["paineis"],
                ancoragem_completa=ancoragem)
