#!/usr/bin/env python3
"""ENGENHARIA — a cadeia inteira reduzida a um arquivo que a interface le.

O visualizador de arquitetura mostra as 35 pranchas. Este arquivo existe
porque a engenharia nao cabe em prancha: 801 pecas, 84 paineis, um plano de
corte, uma sequencia de montagem e seis notas nao sao desenho, sao consulta.

A regra que governa tudo continua valendo aqui: o que nao esta no modelo a
interface nao alcanca. Nada neste modulo inventa numero — cada campo sai de
nucleo.liberacao.rodar(), que por sua vez roda painelizacao, verificacao,
nesting, BOM, montagem, logistica e scores sobre o mesmo caso. Se um numero
aparecer errado na tela, ele esta errado no motor, e a auditoria acusa.

Uso:  python3 engenharia.py [destino.json]
"""
from __future__ import annotations

import json
import os

import projeto as pj
import elementos as el
import nucleo.painel as pn
import nucleo.liberacao as lb
import nucleo.bom as bo
import nucleo.documentos as dc
import nucleo.contratos as ct
import nucleo.cotacao as co
import nucleo.geotecnia as gt
import nucleo.pluvial as pl
import nucleo.acustica as ac
import nucleo.eletrica as elt
import nucleo.mercado as mk

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, "..", "out", "engenharia.json")

# Cores por familia estrutural: a familia e um dado do modelo, nao um estilo.
# R53 — uma tabela so, em nucleo/cores.py
from nucleo.cores import CORES_PECA as CORES_FAMILIA


def _stud(cfg):
    """O montante tipico, como objeto — o memorial verifica o perfil, nao o nome."""
    import nucleo.perfis as pf
    return next(q for q in pf.catalogo() if q.cod == cfg.perfil_stud)


def _aco():
    import nucleo.materiais as mt
    return mt.POR_ACO["ZAR 230"]


def _campos(o) -> dict:
    """Dataclass -> dict raso, sem depender de asdict (que desce recursivo)."""
    return {k: getattr(o, k) for k in o.__dataclass_fields__}


def _peca_json(p, massas: dict) -> dict:
    d = dict(cod=p.cod, familia=p.familia, perfil=p.perfil,
             comp=round(p.comp), x=round(p.x), z=round(p.z),
             vertical=bool(p.vertical))
    det = massas.get(p.cod)
    if det is not None:
        d["massa"] = round(det.massa, 2)
        d["marcacao"] = det.marcacao
        d["furos"] = [dict(x=round(f.x), d=round(f.d, 1), servico=f.servico)
                      for f in det.furos]
    if p.obs:
        d["obs"] = p.obs
    return d


def _orientacoes() -> dict:
    """Cada parede e horizontal ou vertical — sem isto nao ha planta.

    A orientacao existe em elementos.Parede, mas o painel so guarda a origem.
    Em vez de adivinhar pelo codigo (o que falharia no painel unico), a
    derivacao e refeita com a mesma funcao e o mesmo indice do painelizar.
    """
    out = {}
    for pav, amb, pre in (("T", pj.TERREO, "TP"), ("S", pj.SUPERIOR, "SP")):
        for i, par in enumerate(el.derivar_paredes(amb), 1):
            out[f"{pre}{i:02d}"] = bool(par.horizontal)
    return out


def _painel_json(p, massas: dict, cat: dict, ori: dict, juntas=None) -> dict:
    return dict(
        horizontal=ori.get(p.parede, True),
        cod=p.cod, parede=p.parede, x=p.x, y=p.y, comp=p.comp,
        altura=p.altura, esp=p.esp, externa=bool(p.externa),
        pav=p.cod[0] if p.cod[0] in "TS" else "T",
        massa=round(p.massa(cat), 1),
        n_pecas=len(p.pecas), obs=p.obs,
        parafusos=(juntas or {}).get(p.cod, {}).get("n_parafusos", 0),
        juntas=[dict(j, pecas=list(j["pecas"]))
                for j in (juntas or {}).get(p.cod, {}).get("juntas", [])],
        familias=p.por_familia(),
        aberturas=[dict(tipo=a["tipo"], centro=a["centro"], larg=a["larg"],
                        alt=a["alt"], peitoril=a["peitoril"],
                        desc=a.get("desc", ""))
                   for a in p.aberturas],
        pecas=[_peca_json(q, massas) for q in p.pecas])


def _painel_do_passo(cod: str) -> str:
    """PA-T-TP01-1 -> TP01-1. Vazio quando o passo nao e de painel.

    A relacao e do gerador da sequencia (montagem.etapas_do_projeto monta o
    codigo assim); decifra-la por expressao regular na interface faria dois
    lugares saberem o mesmo formato, e um deles ficaria para tras.
    """
    partes = cod.split("-", 2)
    return partes[2] if len(partes) == 3 and partes[0] == "PA" else ""


def _resumo(r: dict) -> list[dict]:
    """As doze figuras do painel — todas derivadas, nenhuma digitada."""
    area = pj.CADASTRO.area_m2
    b = r["plano"]
    return [
        dict(rotulo="Painéis", valor=len(r["paineis"]), unidade="montados"),
        dict(rotulo="Peças", valor=len(r["pecas"]), unidade="detalhadas"),
        dict(rotulo="Aço útil", valor=round(r["massa_util"]), unidade="kg"),
        dict(rotulo="Aço comprado", valor=round(r["massa_comprada"]),
             unidade="kg"),
        dict(rotulo="Aproveitamento", valor=round(b["aproveitamento"] * 100, 1),
             unidade="% do bruto"),
        dict(rotulo="Barras de 6 m", valor=b["n_barras"], unidade="cortadas"),
        dict(rotulo="Consumo", valor=round(r["massa_comprada"] / area, 1),
             unidade="kg/m² de área"),
        dict(rotulo="Custo", valor=round(r["custo"]), unidade="R$ (H)"),
        dict(rotulo="Custo por área", valor=round(r["custo"] / area),
             unidade="R$/m² (H)"),
        dict(rotulo="Montagem", valor=round(r["horas"]), unidade="h de equipe"),
        dict(rotulo="CO₂e", valor=round(r["emissao"]["total"]), unidade="kg"),
        dict(rotulo="Score geral", valor=r["score_geral"], unidade="de 100"),
    ]


def _estrutura(r: dict) -> dict:
    """A verificacao de todos os montantes, como dado para a interface.

    O histograma vai calculado daqui, e nao montado no navegador: um numero que
    a tela deriva sozinha e um numero que pode divergir do memorial.
    """
    v = r["verificacao"]
    us = sorted(v["utilizacoes"])
    faixas = [(0.0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.0),
              (1.0, 99.0)]
    hist = [dict(de=a, ate=b, n=sum(1 for u in us if a <= u < b))
            for a, b in faixas]
    g = v["governa"] or {}
    return dict(
        n=v["n"], reprovadas=len(v["reprovadas"]), aprovado=v["aprovado"],
        mediana=round(us[len(us) // 2], 3) if us else 0.0,
        maxima=round(us[-1], 3) if us else 0.0,
        histograma=hist,
        governa=dict(peca=g.get("peca", ""), painel=g.get("painel", ""),
                     familia=g.get("familia", ""), perfil=g.get("perfil", ""),
                     nsd=round(g.get("nsd", 0), 2), nrd=round(g.get("nrd", 0), 2),
                     u=round(g.get("u", 0), 3), modo=g.get("modo", ""),
                     k=round(g.get("k", 0), 2),
                     combinacao=g.get("combinacao", "")),
        hipoteses=v["hipoteses"],
        jambas=[dict(painel=k, solucao=j["escolha"]["solucao"],
                     nsd=round(j["nsd"], 2), u=round(j["escolha"]["u"], 3),
                     sku_nova=j["sku_nova"], motivo=j["motivo"],
                     rejeitadas=len(j["rejeitadas"]))
                for k, j in sorted(r["jambas"].items())
                if j["escolha"] and (j["sku_nova"] or j["n"] > 1)],
        apertadas=[dict(painel=a, solucao=b, u=round(c, 3))
                   for a, b, c in r["jambas_apertadas"]],
        u_alvo=r.get("u_alvo", 0.95))


def _plausibilidade(r: dict) -> dict:
    """A grandeza e possivel? Terceira classe de verificacao."""
    import nucleo.plausibilidade as pb
    a = pb.avaliar(pb.medir(r, pj.CADASTRO.area_m2))
    return dict(
        n=a["n"], fora=len(a["fora"]), todas_dentro=a["todas_dentro"],
        itens=[dict(cod=x["cod"], valor=round(x["valor"], 3),
                    unidade=x["unidade"], dentro=x["dentro"],
                    minimo=x["faixa"][0], maximo=x["faixa"][1],
                    fonte=x["fonte"], leitura=x["leitura"])
               for x in a["avaliacoes"]])


def _completude(r: dict) -> dict:
    """O sistema esta presente? Quarta classe."""
    import nucleo.completude as cm
    c = cm.conferir(r, pj.CADASTRO.tipologia)
    return dict(situacao=c["situacao"], completo=c["completo"],
                n=c["n"], presentes=c["presentes"], itens=c["itens"])


def _materiais(r: dict) -> dict:
    """Especificacao de material, estrutura por estrutura."""
    import nucleo.materiais as mt
    c = r["camadas"]
    comps = []
    for cod, area in sorted(c["por_composicao"].items()):
        import nucleo.camadas as cdm
        comp = cdm.COMPOSICOES[cod]
        comps.append(dict(
            cod=cod, nome=comp.nome, area=round(area, 1),
            esp_nominal=comp.esp_nominal,
            esp_construida=round(comp.esp_construida, 1), rw=comp.rw,
            onde=comp.onde,
            camadas=[dict(material=x.material,
                          nome=mt.POR_MATERIAL[x.material].nome,
                          espessura=x.espessura, n=x.n, funcao=x.funcao,
                          face=x.face, norma=x.norma,
                          formato=list(x.formato) if x.formato else [],
                          obs=x.obs)
                     for x in comp.camadas]))
    pg = c["paginacao"]
    esq = c["esquadrias"]
    return dict(
        composicoes=comps,
        paginacao=[dict(k, aproveitamento=round(k["aproveitamento"], 3))
                   for k in pg["itens"]],
        placas=pg["placas"], junta_m=pg["junta_m"], borda_m=pg["borda_m"],
        esquadrias=[dict(tipo=e.tipo, n=e.n, larg=e.larg, alt=e.alt,
                         tipologia=e.tipologia, folhas=e.folhas,
                         area=round(e.area, 2),
                         area_vidro=round(e.area_vidro, 2),
                         vidro=e.vidro, motivo=e.justificativa)
                    for e in esq["itens"]],
        esq_caixilho_m=esq["caixilho_m"], esq_vidro_m2=esq["area_vidro"],
        ferragem=esq["ferragem"], desempenho=esq["desempenho"],
        cobertura=c["cobertura"], fundacao=c["fundacao"],
        impermeabilizacao={k: v for k, v in c["impermeabilizacao"].items()
                           if k != "itens"},
        por_painel={p.cod: c["familias"]["familia"].get(p.cod, "")
                    for p in r["paineis"]})


def _instalacoes(r: dict) -> dict:
    """MEP e clash: o percurso medido, e onde ele encosta na estrutura.

    O que a tela precisa dizer, e que uma tabela de comprimentos nao diz: cada
    numero aqui e limite INFERIOR, por percurso Manhattan vezes fator
    declarado. Exportar o fator junto do comprimento e a diferenca entre um
    dado e um numero.
    """
    ins = r["camadas"]["instalacoes"]
    cl = r["camadas"]["clash"]
    # a posicao DECLARADA acompanha a resolvida. Mostrar so a resolvida
    # esconderia o deslocamento, que e a decisao inteira.
    _decl = {d["cod"]: (d["x"], d["y"]) for d in pj.PRUMADAS}
    h, e, cli = ins["hidraulica"], ins["eletrica"], ins["climatizacao"]
    return dict(
        hidraulica=dict(itens=h["itens"], comp_total=h["comp_total"],
                        conexoes=h["conexoes"], fator=h["fator"],
                        pecas=h["pecas"], ralos=h["ralos"],
                        prumadas=h["prumadas"]),
        eletrica=dict(pontos=e["pontos"], eletroduto_m=e["eletroduto_m"],
                      cabo_m=e["cabo_m"], caixas=e["caixas"],
                      disjuntores=e["disjuntores"], quadro=list(e["quadro"]),
                      fator=e["fator"], obs=e["obs"]),
        climatizacao=dict(n=cli["n"], linha_m=cli["linha_m"],
                          dreno_m=cli["dreno_m"],
                          isolamento_m=cli["isolamento_m"],
                          linhas=cli["linhas"], obs=cli["obs"]),
        # a decisao do shaft vai inteira: lado, afastamento, ambiente e motivo.
        # Exportar so a coordenada resolvida esconderia que ela e DERIVADA, e
        # uma coordenada sem o porque e indistinguivel de uma arbitrada.
        shafts=dict(
            regra=r["camadas"]["shafts"]["regra"],
            placa_m2=r["camadas"]["shafts"]["placa_m2"],
            piso_tomado_m2=r["camadas"]["shafts"]["piso_tomado_m2"],
            n=r["camadas"]["shafts"]["n"],
            n_resolvidos=r["camadas"]["shafts"]["n_resolvidos"],
            prumadas=[dict(cod=k, x=round(v["x"]), y=round(v["y"]),
                           dn=v["dn"], tipo=v["tipo"], secao=list(v["secao"]),
                           declarada=_decl.get(k, (None, None)),
                           deslocado=v["deslocado"], lado=v["lado"],
                           ambiente=v["ambiente"], onde=v["onde"],
                           molhado=bool(v.get("molhado")),
                           resolvido=v["resolvido"], motivo=v["motivo"])
                      for k, v in r["camadas"]["shafts"]["prumadas"].items()]),
        clash=dict(
            volumes=cl["volumes"], total=cl["total"],
            resolviveis=cl["resolviveis"], criterio=cl["criterio"], ok=cl["ok"],
            # o conflito vai inteiro: peca, prumada e motivo por extenso. Um
            # contador de conflitos nao permite resolver nenhum deles.
            criticos=[dict(a=c["a"], b=c["b"], peca=c["peca"], dn=c["dn"],
                           motivo=c["motivo"]) for c in cl["criticos"]],
            shafts=[dict(a=c["a"], b=c["b"], peca=c["peca"], dn=c["dn"],
                         motivo=c["motivo"]) for c in cl["shafts"]]))


def _juntas(r: dict) -> dict:
    """O programa de parafusos, agregado como a obra precisa ler.

    Por tipo de junta, por origem do numero e por painel. A origem e o campo
    que nao pode sumir na soma: 5.266 parafusos dos quais 1.538 vem de forca
    calculada e 3.656 de minimo construtivo e uma informacao diferente de
    "5.266 parafusos".
    """
    js = r["juntas"]
    por_tipo, por_origem, por_parafuso = {}, {}, {}
    for j in js.values():
        for x in j["juntas"]:
            por_tipo[x["tipo"]] = por_tipo.get(x["tipo"], 0) + x["n"]
            por_origem[x["origem"]] = por_origem.get(x["origem"], 0) + x["n"]
            por_parafuso[x["parafuso"]] = por_parafuso.get(x["parafuso"], 0) + x["n"]
    # uma junta representativa de cada tipo, com o motivo por extenso
    exemplo = {}
    for j in js.values():
        for x in j["juntas"]:
            if x["tipo"] not in exemplo:
                exemplo[x["tipo"]] = dict(x, pecas=list(x["pecas"]))
    return dict(
        total=r["n_parafusos"],
        # do CADASTRO, nao literal: o literal sobreviveu a R46 e teria passado
        # a dividir por uma area que a casa nao tem mais
        por_m2=round(r["n_parafusos"] / pj.CADASTRO.area_m2, 1),
        n_juntas=sum(j["n_juntas"] for j in js.values()),
        por_tipo=[dict(tipo=k, n=v) for k, v in
                  sorted(por_tipo.items(), key=lambda kv: -kv[1])],
        por_origem=[dict(origem=k, n=v) for k, v in
                    sorted(por_origem.items(), key=lambda kv: -kv[1])],
        por_parafuso=[dict(parafuso=k, n=v) for k, v in
                      sorted(por_parafuso.items(), key=lambda kv: -kv[1])],
        exemplos=list(exemplo.values()),
        por_painel={k: dict(n=j["n_parafusos"], juntas=j["n_juntas"],
                            tipos=j["por_tipo"])
                    for k, j in js.items()})


def _nesting(plano: dict) -> dict:
    barras = [dict(cod=b.cod, perfil=b.perfil, bruto=round(b.comp_bruto),
                   origem=b.origem,
                   usado=round(sum(c for _, c in b.pecas)),
                   pecas=[dict(cod=c, comp=round(v)) for c, v in b.pecas])
              for b in plano["barras"]]
    return dict(aproveitamento=plano["aproveitamento"],
                n_barras=plano["n_barras"], n_novas=plano["n_novas"],
                bruto=plano["bruto"], usado=plano["usado"],
                perda=plano["perda"], barras=barras)


def montar() -> dict:
    """Roda a cadeia e transcreve o resultado — sem recalcular nada."""
    cfg = pn.Config(altura=pj.PE_DIREITO)   # R61: uma fonte para a altura
    r = lb.rodar(pj, el, cfg)
    cat = pn._catalogo_massa()
    massas = {p.cod: p for p in r["pecas"]}
    ori = _orientacoes()

    _de_painel = {q.cod for p in r["paineis"] for q in p.pecas}
    familias: dict[str, int] = {}
    perfis: dict[str, float] = {}
    for p in r["pecas"]:
        familias[p.familia] = familias.get(p.familia, 0) + 1
        perfis[p.perfil] = perfis.get(p.perfil, 0.0) + p.massa

    return dict(
        revisao=pj.EMISSAO["revisao"],
        projeto=dict(nome=pj.CADASTRO.nome, id=pj.CADASTRO.project_id,
                     local=pj.CADASTRO.localizacao,
                     area_m2=pj.CADASTRO.area_m2,
                     sistema=pj.CADASTRO.sistema,
                     status=pj.CADASTRO.status),
        config=_campos(cfg),
        resumo=_resumo(r),
        cores=CORES_FAMILIA,
        familias=familias,
        # pecas que nao pertencem a painel de parede: vigamento de entrepiso,
        # cobertura e contraventamento. Sem elas a tabela mostrava 805 de 1.011
        # e o total das familias nao fechava com o que a tela sabia percorrer.
        extras=[dict(cod=p.cod, familia=p.familia, perfil=p.perfil,
                     comp=round(p.comp), massa=round(p.massa, 2),
                     plano=p.painel, pav=p.pav, marcacao=p.marcacao)
                for p in r["pecas"] if p.cod not in _de_painel],
        perfis=[dict(perfil=k, massa=round(v, 1)) for k, v in
                sorted(perfis.items(), key=lambda kv: -kv[1])],
        paineis=[_painel_json(p, massas, cat, ori, r["juntas"])
                 for p in r["paineis"]],
        nesting=_nesting(r["plano"]),
        bom=[dict(sku=i.sku, descricao=i.descricao, unidade=i.unidade,
                  quantidade=round(i.quantidade, 2),
                  preco=i.preco_unit, total=round(i.total, 2),
                  # o que se COMPRA e o que se produz nao somam. A linha de
                  # producao vai junto, marcada, porque a fabrica precisa dela
                  # — e porque escondê-la seria trocar uma dupla contagem por
                  # uma omissao.
                  compra=i.compra, total_compra=round(i.total_compra, 2),
                  familia=i.familia, fonte=i.fonte) for i in r["bom"]],
        abc=bo.curva_abc(r["bom"]),
        custo=round(r["custo"], 2),
        montagem=dict(horas=round(r["horas"], 1), n_passos=len(r["passos"]),
                      passos=[dict(p, duracao_h=round(p["duracao_h"], 2),
                                   acumulado_h=round(p["acumulado_h"], 2),
                                   massa=round(p["massa"], 1),
                                   painel=_painel_do_passo(p["cod"]))
                              for p in r["passos"]]),
        logistica=dict(container=r["carga"]["container"],
                       volumes=r["carga"]["n"],
                       rejeitados=len(r["carga"]["rejeitados"]),
                       uso_peso=r["carga"]["uso_peso"],
                       uso_volume=r["carga"]["uso_volume"],
                       limitante=r["carga"]["limitante"],
                       massa=round(r["carga"]["massa"], 1),
                       pilhas=r["carga"]["pilhas"]),
        emissao=r["emissao"],
        desmontabilidade=r["desmontabilidade"],
        estrutura=_estrutura(r),
        plausibilidade=_plausibilidade(r),
        completude=_completude(r),
        juntas=_juntas(r),
        materiais=_materiais(r),
        instalacoes=_instalacoes(r),
        combinacoes=dict(
            n=r["combinacoes"]["conferencia"]["n"],
            tipos=r["combinacoes"]["conferencia"]["tipos"],
            criterio=r["combinacoes"]["conferencia"]["criterio"],
            n_favoravel=r["combinacoes"]["conferencia"]["n_favoravel"],
            erros=r["combinacoes"]["conferencia"]["erros"],
            faltas=r["combinacoes"]["conferencia"]["faltas"],
            cobertura=r["combinacoes"]["cobertura"]["por_natureza"],
            leitura=r["combinacoes"]["cobertura"]["leitura"],
            orfas=r["combinacoes"]["cobertura"]["orfas"],
            ok=r["combinacoes"]["ok"]),
        pendencias=r["pendencias"],
        catalogo=r["catalogo"],
        viabilidade=r["viabilidade"],
        fachada=dict(r["fachada"],
                     platibanda=r["camadas"]["platibanda"],
                     externo=r["camadas"]["externo"]),
        # o dossie vai INTEIRO: e a unica vista em que alguem procura "o que
        # tem na lavanderia", e responder isso pela metade e pior que nao
        # responder — manda conferir na prancha o que ja esta no modelo
        ambientes=dict(
            n=r["ambientes"]["n"], area_total=r["ambientes"]["area_total"],
            criterio=r["ambientes"]["criterio"],
            achados=r["ambientes"]["achados"],
            # o grafo vai junto: e o unico dado desta vista que nao e uma
            # propriedade de comodo, e sim a relacao entre eles
            conectividade=r["ambientes"]["conectividade"],
            por_ambiente=r["ambientes"]["por_ambiente"],
            dossies=[{k: v for k, v in d.items() if k != "vaos"}
                     | dict(vaos=[dict(tipo=v["tipo"], larg=v["larg"],
                                       alt=v["alt"], peitoril=v["peitoril"],
                                       area=round(v["area"], 2),
                                       externo=v["externo"],
                                       translucido=v["translucido"],
                                       familia=v["familia"])
                                  for v in d["vaos"]])
                     for d in r["ambientes"]["dossies"]]),
        cotacao=dict(
            cobertura=r["cotacao"]["cobertura"],
            sensibilidade=sorted(r["cotacao"]["sensibilidade"],
                                 key=lambda x: -x["exposicao"]),
            mapa=dict(n=r["cotacao"]["mapa"]["n"],
                      n_alternativas=r["cotacao"]["mapa"]["n_alternativas"],
                      cotaveis=r["cotacao"]["mapa"]["cotaveis"],
                      n_lacunas=r["cotacao"]["mapa"]["n_lacunas"],
                      instrucao=r["cotacao"]["mapa"]["instrucao"],
                      min_propostas=r["cotacao"]["mapa"]["min_propostas"],
                      lacunas=r["cotacao"]["mapa"]["lacunas"],
                      linhas=[dict(sku=l["sku"], quantidade=l["quantidade"],
                                   unidade=l["unidade"],
                                   descricao=l["descricao"],
                                   especificacao=l["especificacao"],
                                   normas=l["normas"], lacunas=l["lacunas"])
                              for l in r["cotacao"]["mapa"]["linhas"]],
                      alternativas=[dict(sku=l["sku"], unidade=l["unidade"],
                                         quantidade=l["quantidade"],
                                         descricao=l["descricao"])
                                    for l in r["cotacao"]["mapa"]["alternativas"]]),
            niveis=list(co.NIVEIS)),
        scores=r["scores"], score_geral=r["score_geral"],
        liberacao=r["liberacao"],
        documentos=dict(
            lista_de_pecas=dc.lista_de_pecas(r["pecas"]),
            plano_de_corte=dc.plano_de_corte(r["plano"]),
            packing_list=dc.packing_list({}, r["paineis"], cat),
            manual=dc.manual_de_montagem(r["passos"]),
            inspecao=dc.relatorio_inspecao(r["pecas"]),
            memorial=dc.memorial_descritivo(pj, r),
            mapa_de_cotacao=dc.mapa_de_cotacao(r["cotacao"]["mapa"], pj),
        ),
        contratos=[dict(cod=c.cod, titulo=c.titulo, secoes=list(c.secoes),
                        bloqueio=c.bloqueio, fonte=c.fonte, aceite=c.aceite,
                        esforco=c.esforco,
                        esquema=[dict(nome=k.nome, tipo=k.tipo,
                                      unidade=k.unidade,
                                      obrigatorio=k.obrigatorio,
                                      descricao=k.descricao,
                                      dominio=list(k.dominio))
                                 for k in c.esquema])
                   for c in ct.CONTRATOS],
        memoriais={m: dc.memorial_compressao(_stud(cfg), _aco(), cfg.altura, m)
                   for m in dc.MODOS},
        # R52 — quatro sistemas novos. A regra de R51 e de R52 e a mesma em
        # suportes diferentes: o que esta no modelo tem de chegar ao papel E a
        # tela. Deixar de exportar aqui repetiria, na tela, exatamente o que o
        # catalogo tecnico fez na prancha.
        geotecnia=dict(
            sondagens=gt.SONDAGENS, perfil=gt.perfil(),
            interpretacao={f"{a}-{b}": v
                           for (a, b), v in gt.INTERPRETACAO.items()},
            investigada=gt.PROF_INVESTIGADA,
            tratamento=gt.TRATAMENTO,
            carga=gt.carga_na_fundacao(pj, r),
            dimensionamento=gt.dimensionar(pj, r),
            armadura=gt.armadura(pj),
            terraplenagem=gt.terraplenagem(pj),
            conferencia=[dict(titulo=t, detalhe=d, ok=o)
                         for t, d, o in gt.conferir(pj, r)]),
        pluvial=dict(
            balanco=pl.balanco(pj), gatilho=pl.gatilho_legal(pj),
            vazoes=pl.vazoes(pj), retencao=pl.retencao(pj),
            coeficientes=pl.C_SUPERFICIE,
            decisao=pj.PLUVIAL,
            conferencia=[dict(titulo=t, detalhe=d, ok=o)
                         for t, d, o in pl.conferir(pj)]),
        acustica=dict(
            pares=ac.pares(pj), entre_zonas=ac.entre_zonas(pj),
            fontes=ac.FONTES, limites=ac.LIMITE, portas=ac.RW_PORTA,
            zonas=ac.ZONA_ACUSTICA,
            conferencia=[dict(titulo=t, detalhe=d, ok=o)
                         for t, d, o in ac.conferir(pj)]),
        eletrica=dict(
            tensao=pj.TENSAO, equilibrio=elt.equilibrar(pj),
            entrada=elt.entrada(pj), demanda=pj.demanda_eletrica(),
            conferencia=[dict(titulo=t, detalhe=d, ok=o)
                         for t, d, o in elt.conferir(pj)]),
        mercado=dict(
            indices=mk.INDICES, fornecedores=mk.FORNECEDORES,
            cobertura=mk.cobertura_de_fornecedores(r),
            aderencia=mk.aderencia(pj, r),
            fora_do_orcamento=mk.FORA_DO_ORCAMENTO,
            sem_praca_local=mk.SEM_PRACA_LOCAL,
            pesquisa=mk.PESQUISA,
            conferencia=[dict(titulo=t, detalhe=d, ok=o)
                         for t, d, o in mk.conferir(pj, r)]),
    )


def main(destino: str | None = None) -> str:
    alvo = os.path.abspath(destino or OUT)
    os.makedirs(os.path.dirname(alvo), exist_ok=True)
    texto = json.dumps(montar(), ensure_ascii=False, separators=(",", ":"))
    open(alvo, "w", encoding="utf-8").write(texto)
    print(f"  {alvo}  {len(texto) // 1024} KB  (engenharia)")
    return alvo


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else None)
