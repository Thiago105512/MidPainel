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

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(AQUI, "..", "out", "engenharia.json")

# Cores por familia estrutural: a familia e um dado do modelo, nao um estilo.
CORES_FAMILIA = {
    "track": "#8a94a6", "stud": "#3f6fb5", "king stud": "#1f4e96",
    "jack stud": "#4d8fd6", "cripple superior": "#9fc0e8",
    "cripple inferior": "#7ba7dc", "header": "#c4491f",
    "sill": "#d98324", "blocking": "#6fae7c", "diagonal": "#7a5fb0",
}


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


def _painel_json(p, massas: dict, cat: dict, ori: dict) -> dict:
    return dict(
        horizontal=ori.get(p.parede, True),
        cod=p.cod, parede=p.parede, x=p.x, y=p.y, comp=p.comp,
        altura=p.altura, esp=p.esp, externa=bool(p.externa),
        pav=p.cod[0] if p.cod[0] in "TS" else "T",
        massa=round(p.massa(cat), 1),
        n_pecas=len(p.pecas), obs=p.obs,
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
    cfg = pn.Config()
    r = lb.rodar(pj, el, cfg)
    cat = pn._catalogo_massa()
    massas = {p.cod: p for p in r["pecas"]}
    ori = _orientacoes()

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
        perfis=[dict(perfil=k, massa=round(v, 1)) for k, v in
                sorted(perfis.items(), key=lambda kv: -kv[1])],
        paineis=[_painel_json(p, massas, cat, ori) for p in r["paineis"]],
        nesting=_nesting(r["plano"]),
        bom=[dict(sku=i.sku, descricao=i.descricao, unidade=i.unidade,
                  quantidade=round(i.quantidade, 2),
                  preco=i.preco_unit, total=round(i.total, 2),
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
        scores=r["scores"], score_geral=r["score_geral"],
        liberacao=r["liberacao"],
        documentos=dict(
            lista_de_pecas=dc.lista_de_pecas(r["pecas"]),
            plano_de_corte=dc.plano_de_corte(r["plano"]),
            packing_list=dc.packing_list({}, r["paineis"], cat),
            manual=dc.manual_de_montagem(r["passos"]),
            inspecao=dc.relatorio_inspecao(r["pecas"]),
            memorial=dc.memorial_descritivo(pj, r),
        ),
        memoriais={m: dc.memorial_compressao(_stud(cfg), _aco(), cfg.altura, m)
                   for m in dc.MODOS},
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
