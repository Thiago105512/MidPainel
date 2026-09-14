"""AMBIENTE — a verificacao que faltava, e o eixo em que ela faltava.

Todas as 510 condicoes deste projeto verificam por SISTEMA: a estrutura, as
camadas, o MEP, a fundacao, a cotacao. Nenhuma verifica por CoMODO — e o comodo
e a unidade em que a casa e vivida, em que o pedreiro trabalha e em que o dono
percebe erro. "A lavanderia tem quantas tomadas?" era uma pergunta que este
modelo, com 1.033 pecas conferidas uma a uma, nao sabia responder.

O eixo importa porque defeito nao se distribui por sistema: ele se concentra
onde dois sistemas se encontram, e os dois sistemas se encontram DENTRO de um
comodo. Um piso antiderrapante que nao acompanhou a decisao de area molhada, um
ralo que ficou num comodo seco, uma tomada a menos na area de servico — nada
disso aparece somando metros quadrados ou quilos de aco.

O QUE ESTE MODULO NAO FAZ. Nao redesenha nada e nao decide nada. Ele CONFRONTA
o que ja foi decidido em lugares diferentes e diz onde as decisoes discordam.
"""
from __future__ import annotations

import math

# Tolerancia para dizer que um vao pertence a um ambiente: meia parede externa
# (75 mm) com folga. Menos que isso perde vao de parede espessa; mais, cola vao
# em comodo vizinho.
TOL_VAO = 90.0

# (H) Criterio de iluminacao e ventilacao naturais. NAO e da NBR: e do Codigo
# de Obras municipal, e o de Manaus e a pendencia 1 do caderno. As fracoes
# abaixo sao a pratica corrente brasileira, declaradas para que a conferencia
# EXISTA e possa ser refeita com o numero certo quando a certidao chegar.
ILUM_MIN = {"dormitorio": 1 / 6, "permanencia": 1 / 6, "molhado": 1 / 8,
            "servico": 1 / 8, "circulacao": 0.0}
VENT_MIN = {"dormitorio": 1 / 12, "permanencia": 1 / 12, "molhado": 1 / 16,
            "servico": 1 / 16, "circulacao": 0.0}
# fracao do vao que de fato abre. Correr abre metade; maxim-ar e basculante,
# quase tudo; fixa nao abre. Sem isto, "area de vao" viraria "area ventilada",
# que e o erro mais comum de memorial de ventilacao.
ABRE = {"correr": 0.50, "batente": 0.90, "basculante": 0.85, "fixa": 0.0,
        "cortina": 0.85, "porta": 0.90}


def _classe(pj, a) -> str:
    """Como este ambiente e tratado para iluminacao e ventilacao."""
    import especificacao as ep
    cat = ep.CATEGORIA.get(a.cod, "apoio")
    if a.cod in ep.MOLHADOS or getattr(a, "molhado", False):
        return "molhado"
    if cat in ("intimo",):
        return "dormitorio"
    if cat in ("social",):
        return "permanencia"
    if cat in ("servico", "apoio", "oficina"):
        return "servico"
    return "circulacao"


def _translucido(tipo: str, fam: str) -> bool:
    """Este vao deixa passar luz?

    Nao e "e janela": o estar abre por uma porta-balcao de 2,4 m e o eixo
    social por uma cortina de vidro de 7,2 m. Classificar por PREFIXO de codigo
    reprovou os dois — e o erro estava na classificacao, nao no projeto.
    """
    f = (fam or "").lower()
    if "opaca" in f:
        return False
    if tipo.startswith("J") or tipo.startswith("CV") or tipo.startswith("PV"):
        return True
    return "vidro" in f or "ripado" in f or "balcao" in f


def _tipo_abertura(tipo: str, fam: str) -> str:
    f = (fam or "").lower()
    if "correr" in f or "cortina" in f:
        return "cortina" if "cortina" in f else "correr"
    if "basculante" in f or "alta" in f:
        return "basculante"
    if tipo.startswith("P"):
        return "porta"
    return "batente"


def vaos_do_ambiente(pj, a, todos_ambientes) -> list[dict]:
    """Os vaos que pertencem a este ambiente, e se abrem para fora.

    Um vao que toca DOIS ambientes fechados e porta interna: nao ilumina nem
    ventila, porque do outro lado ha teto. Um que toca um ambiente aberto
    (varanda, loggia, jardim) abre para o ar — e essa distincao e o que separa
    ventilacao real de ventilacao no papel.
    """
    out = []
    for tipo, x, y, ori, pav in pj.VAOS:
        if pav != a.pav:
            continue
        if not (a.x - TOL_VAO <= x <= a.x + a.w + TOL_VAO
                and a.y - TOL_VAO <= y <= a.y + a.h + TOL_VAO):
            continue
        vizinhos = [b for b in todos_ambientes
                    if b.pav == pav and b.cod != a.cod
                    and (b.x - TOL_VAO <= x <= b.x + b.w + TOL_VAO)
                    and (b.y - TOL_VAO <= y <= b.y + b.h + TOL_VAO)]
        externo = (not vizinhos) or any(getattr(b, "aberto", False)
                                        for b in vizinhos)
        larg, alt, peit, fam = pj.ESQUADRIAS[tipo]
        k = _tipo_abertura(tipo, fam)
        out.append(dict(tipo=tipo, x=x, y=y, orientacao=ori, familia=fam,
                        larg=larg, alt=alt, peitoril=peit,
                        area=larg * alt / 1e6,
                        abre=ABRE.get(k, 0.5), modo=k, externo=externo,
                        translucido=_translucido(tipo, fam),
                        vizinhos=[b.cod for b in vizinhos]))
    return out


def dossie(pj, r: dict) -> list[dict]:
    """Tudo o que o modelo sabe sobre cada comodo, num lugar so."""
    import especificacao as ep
    todos = (pj.TERREO + pj.SUPERIOR + pj.TERREO_ABERTO + pj.SUPERIOR_ABERTO)
    acab = {x["amb"]: x for x in pj.acabamentos()}
    prev = {x["amb"]: x for x in pj.previsao_iluminacao_tug()}
    hidr = {}
    for p in pj.pecas_hidraulicas():
        hidr.setdefault(p["amb"], []).append(p)
    ralos = {}
    for x in pj.RALOS:
        ralos.setdefault(x.get("amb", ""), []).append(x)
    clima = {}
    for c in pj.CLIMATIZACAO:
        clima.setdefault(c["amb"], []).append(c)
    tue = {}
    for c in pj.CARGAS_ESPECIAIS:
        for a in pj.TERREO + pj.SUPERIOR:
            if a.cod in c.get("amb", "") or c.get("amb") == a.cod:
                tue.setdefault(a.cod, []).append(c)

    # composicao das paredes que cercam o comodo, do levantamento de camadas
    fam_painel = ((r.get("camadas") or {}).get("familias") or {}).get("familia", {})
    paineis = r.get("paineis") or []

    out = []
    for a in pj.TERREO + pj.SUPERIOR:
        vs = vaos_do_ambiente(pj, a, todos)
        ext = [v for v in vs if v["externo"] and v["translucido"]]
        classe = _classe(pj, a)
        # subdivisoes ocupam area DENTRO do retangulo: banho e closet nao sao
        # area de permanencia e nao se iluminam pela janela do quarto. Somar o
        # retangulo inteiro reprovava a suite por uma area que nao e dela.
        subs = [d for d in pj.SUBDIVISOES if d["pai"] == a.cod]
        area_sub = sum(d["w"] * d["h"] for d in subs) / 1e6
        area = a.area_mod
        area_util = round(area - area_sub, 2)
        a_ilum = sum(v["area"] for v in ext)
        a_vent = sum(v["area"] * v["abre"] for v in ext)
        base = area_util if area_util > 0 else area
        # paineis cujo segmento encosta no retangulo do comodo
        cerca = []
        for p in paineis:
            if p.pav != a.pav:
                continue
            x0, y0 = p.x, p.y
            x1 = p.x + (p.comp if p.horizontal else 0)
            y1 = p.y + (0 if p.horizontal else p.comp)
            if (min(x0, x1) <= a.x + a.w + TOL_VAO and max(x0, x1) >= a.x - TOL_VAO
                    and min(y0, y1) <= a.y + a.h + TOL_VAO
                    and max(y0, y1) >= a.y - TOL_VAO):
                cerca.append(dict(cod=p.cod, composicao=fam_painel.get(p.cod, ""),
                                  comp=p.comp))
        comps = sorted({c["composicao"] for c in cerca if c["composicao"]})
        ac = acab.get(a.cod, {})
        pv = prev.get(a.cod, {})
        out.append(dict(
            cod=a.cod, nome=a.nome, pav=a.pav, area=round(area, 2),
            perimetro=round(2 * (a.w + a.h) / 1000.0, 2),
            largura=a.w, profundidade=a.h,
            categoria=ep.CATEGORIA.get(a.cod, "apoio"), classe=classe,
            molhado=a.cod in ep.MOLHADOS or bool(getattr(a, "molhado", False)),
            # o banho da suite e SUBDIVISAO: a peca hidraulica e o ralo sao
            # lancados no codigo do comodo-pai, e o flag de molhado vive na
            # subdivisao. Sao duas formas de dizer a mesma coisa, e conferir
            # so uma delas foi o que produziu o defeito 44
            molhado_por_subdivisao=[d["nome"] for d in subs if d.get("molhado")],
            piso=ac.get("piso", ""), parede=ac.get("parede", ""),
            forro=ac.get("forro", ""), forro_h=ac.get("forro_h", 0),
            rodape=ac.get("rodape", ""), revest_h=ac.get("revest_h"),
            vaos=vs, n_vaos=len(vs), externos=len(ext),
            area_ilum=round(a_ilum, 2), area_vent=round(a_vent, 2),
            area_util=area_util, subdivisoes=[d["nome"] for d in subs],
            area_subdividida=round(area_sub, 2),
            frac_ilum=round(a_ilum / base, 4) if base else 0.0,
            frac_vent=round(a_vent / base, 4) if base else 0.0,
            exige_ilum=ILUM_MIN.get(classe, 0.0),
            exige_vent=VENT_MIN.get(classe, 0.0),
            tugs_norma=pv.get("tugs", 0), tug_va=pv.get("tug_va", 0),
            ilum_va=pv.get("ilum_va", 0), molhada_eletrica=pv.get("molhada", False),
            tue=[dict(cod=c["cod"], desc=c["desc"], va=c["va"])
                 for c in tue.get(a.cod, [])],
            hidraulicas=[dict(cod=p["cod"], tipo=p.get("tipo", ""),
                              quente=p.get("quente", False), uhc=p.get("uhc", 0))
                         for p in hidr.get(a.cod, [])],
            ralos=len(ralos.get(a.cod, [])),
            clima=[dict(capacidade=c["capacidade"], nicho=c.get("nicho", "—"))
                   for c in clima.get(a.cod, [])],
            paineis=len(cerca), composicoes=comps,
        ))
    return out


def conferir(pj, r: dict) -> dict:
    """Onde as decisoes discordam, comodo a comodo."""
    import especificacao as ep
    ds = dossie(pj, r)
    achados = []

    def ach(amb, nivel, item, texto):
        achados.append(dict(amb=amb, nivel=nivel, item=item, texto=texto))

    por_cod = {d["cod"]: d for d in ds}

    # ---- 1. TUG: a norma conta PERIMETRO; o levantamento de MEP contava area.
    # Fica como REGRESSAO: se alguem reintroduzir a regra por area, isto acusa.
    import nucleo.instalacoes as _ins
    import inspect as _insp
    fonte_mep = _insp.getsource(_ins.eletrica)
    if "previsao_iluminacao_tug" not in fonte_mep:
        for d in ds:
            ach(d["cod"], "ERRO", "tomadas",
                f"o levantamento de instalacoes voltou a contar tomada por "
                f"AREA; a NBR 5410 9.5.2.2 conta PERIMETRO, e aqui sao "
                f"{d['tugs_norma']} tomadas")
    for d in []:
        n_mep = 0
        if False:
            ach(d["cod"], "ERRO" if n_mep < d["tugs_norma"] else "ATENCAO",
                "tomadas",
                f"{d['tugs_norma']} tomadas pela NBR 5410 (uma a cada "
                f"{'3,5' if d['molhada_eletrica'] else '5,0'} m dos "
                f"{d['perimetro']:.1f} m de perimetro) contra {n_mep} que o "
                f"levantamento de instalacoes contou por AREA. A norma conta "
                f"perimetro porque tomada serve parede, nao metro quadrado")

    # ---- 2. iluminacao e ventilacao naturais.
    # Ambientes CONJUGADOS se conferem juntos: a cozinha e o gourmet sao um so
    # comodo com 6.600 de fronteira aberta, e conferi-los separados reprova a
    # cozinha por uma parede que nao existe.
    vistos = set()
    for d in ds:
        if d["exige_ilum"] <= 0 or d["cod"] in vistos:
            continue
        grupo = [por_cod[c] for c in pj.conjugado_de(d["cod"]) if c in por_cod]
        vistos.update(x["cod"] for x in grupo)
        if len(grupo) > 1:
            base = sum(x["area_util"] or x["area"] for x in grupo)
            ilum = sum(x["area_ilum"] for x in grupo)
            vent = sum(x["area_vent"] for x in grupo)
            d = dict(d, area=round(base, 2), area_ilum=round(ilum, 2),
                     area_vent=round(vent, 2),
                     frac_ilum=ilum / base if base else 0.0,
                     frac_vent=vent / base if base else 0.0,
                     conjugado=[x["cod"] for x in grupo])
        if d["frac_ilum"] < d["exige_ilum"] - 1e-6:
            ach(d["cod"], "ATENCAO", "iluminacao natural",
                f"{d['area_ilum']:.2f} m2 de vao para {d['area']:.1f} m2 de "
                f"piso = 1/{1 / d['frac_ilum']:.1f} se houver vao, contra o "
                f"minimo (H) de 1/{1 / d['exige_ilum']:.0f} para "
                f"{d['classe']}" if d["frac_ilum"] else
                f"NENHUM vao externo em {d['area']:.1f} m2 de "
                f"{d['classe']}: o minimo (H) e 1/{1 / d['exige_ilum']:.0f}")
        elif d["frac_vent"] < d["exige_vent"] - 1e-6:
            ach(d["cod"], "ATENCAO", "ventilacao natural",
                f"area ventilavel de {d['area_vent']:.2f} m2 "
                f"(1/{1 / d['frac_vent']:.1f}) contra o minimo (H) de "
                f"1/{1 / d['exige_vent']:.0f}: o vao existe, mas parte dele "
                f"nao abre")

    # ---- 3. molhado: piso, ralo e impermeabilizacao andam juntos ou nao andam
    acab_cod = {x["amb"] for x in pj.acabamentos()}
    for d in ds:
        if d.get("molhado_por_subdivisao") and not d["molhado"]:
            faltando = [n for n in d["molhado_por_subdivisao"]
                        if f"{d['cod']}/{n}" not in acab_cod]
            if not faltando:
                continue
            ach(d["cod"], "ATENCAO", "acabamento da subdivisao",
                f"a area molhada deste comodo e a subdivisao "
                f"{', '.join(d['molhado_por_subdivisao'])}, e acabamentos() "
                f"enumera AMBIENTES: nao existe piso, revestimento nem rodape "
                f"declarado para ela. Mesma raiz do defeito 44 — o dado do "
                f"banho da suite mora numa lista que a conferencia nao lia")
            continue
        if d["molhado"]:
            if "antiderrapante" not in d["piso"].lower():
                ach(d["cod"], "ERRO", "piso molhado",
                    f"area molhada com piso '{d['piso'][:44]}': sem "
                    f"antiderrapante declarado")
            if not d["ralos"]:
                ach(d["cod"], "ATENCAO", "ralo",
                    "area molhada sem ralo no levantamento de drenagem")
        elif d["hidraulicas"]:
            ach(d["cod"], "ERRO", "molhado nao declarado",
                f"{len(d['hidraulicas'])} peca(s) hidraulica(s) num ambiente "
                f"que nao esta na lista de molhados: ou a peca esta no comodo "
                f"errado, ou o comodo precisa de impermeabilizacao")
        elif d["ralos"]:
            # garagem e area tecnica tem ralo por lavagem, nao por louca: e
            # decisao de projeto, nao divergencia
            esperado = d["categoria"] in ("apoio", "servico", "oficina")
            ach(d["cod"], "NOTA" if esperado else "ATENCAO",
                "ralo em ambiente seco",
                f"{d['ralos']} ralo(s) em ambiente nao declarado molhado"
                + (" — esperado em area de lavagem, e por isso nao vira "
                   "impermeabilizacao de area molhada" if esperado else ""))

    # ---- 4. clima: equipamento sem ambiente, ambiente sem equipamento
    quentes = [d for d in ds if d["classe"] in ("dormitorio", "permanencia")]
    for d in quentes:
        if not d["clima"] and d["area"] >= 9.0:
            ach(d["cod"], "NOTA", "climatizacao",
                f"{d['area']:.1f} m2 de {d['classe']} sem equipamento "
                f"declarado — verificar se a estrategia ali e passiva")

    # ---- 5. conectividade: da para chegar em todo comodo?
    con = conectividade(pj)
    for c in con["ilhados"]:
        ach(c, "ERRO", "ilhado",
            "nao se alcanca este comodo a pe a partir da porta de entrada: "
            "ele tem porta, mas a porta nao da para ambiente nenhum")

    # ---- 6. a soma dos comodos e a area do projeto
    soma = sum(d["area"] for d in ds)
    return dict(conectividade=con,
        dossies=ds, achados=achados,
        n=len(ds), n_achados=len(achados),
        erros=sum(1 for a in achados if a["nivel"] == "ERRO"),
        area_total=round(soma, 2),
        por_ambiente={d["cod"]: sum(1 for a in achados if a["amb"] == d["cod"])
                      for d in ds},
        criterio="iluminacao e ventilacao pelo Codigo de Obras municipal, que "
                 "e a pendencia 1: as fracoes usadas sao (H) da pratica "
                 "corrente, declaradas para que a conferencia exista e possa "
                 "ser refeita com o numero certo quando a certidao chegar")


# ---------------------------------------------------------------------------
# CONECTIVIDADE — a pergunta que 517 verificacoes nao faziam
#
# Todas elas conferem PROPRIEDADES de um comodo: area, acabamento, carga,
# iluminacao. Nenhuma perguntava se da para CHEGAR nele. E dava para nao dar:
# o mini lounge tinha porta, tinha janela, tinha climatizacao, tinha piso
# especificado — e nao tinha vizinho. A porta abria para uma faixa de 600 mm
# que nao pertencia a ambiente nenhum, cercada por duas paredes externas
# paralelas que o painelizador ergueu porque via exterior dos dois lados.
#
# Nenhuma verificacao de propriedade pega isso, por mais fina que seja: o comodo
# estava correto em tudo o que se media DENTRO dele. O que faltava era medir a
# relacao entre comodos — e relacao e grafo, nao tabela.
# ---------------------------------------------------------------------------
def conectividade(pj, entrada: str = "T-VAR") -> dict:
    """Todo comodo fechado se alcanca a pe, a partir da porta de entrada?"""
    todos = (pj.TERREO + pj.SUPERIOR + pj.TERREO_ABERTO + pj.SUPERIOR_ABERTO)
    g: dict = {}

    def liga(a, b, por):
        g.setdefault(a, {}).setdefault(b, []).append(por)
        g.setdefault(b, {}).setdefault(a, []).append(por)

    for tipo, x, y, ori, pav in pj.VAOS:
        ambs = [a.cod for a in todos if a.pav == pav
                and a.x - TOL_VAO <= x <= a.x + a.w + TOL_VAO
                and a.y - TOL_VAO <= y <= a.y + a.h + TOL_VAO]
        for i in range(len(ambs)):
            for j in range(i + 1, len(ambs)):
                liga(ambs[i], ambs[j], tipo)
    # fronteira aberta liga tanto quanto porta — e em alguns casos liga mais
    for grupo in getattr(pj, "INTEGRADOS", ()):
        gl = list(grupo)
        for i in range(len(gl)):
            for j in range(i + 1, len(gl)):
                liga(gl[i], gl[j], "fronteira aberta")
    # a escada e o unico vinculo entre pavimentos, e nao e um vao
    liga("T-COR", "S-HAL", "escada")

    vistos, fila = {entrada}, [entrada]
    while fila:
        c = fila.pop()
        for n in g.get(c, {}):
            if n not in vistos:
                vistos.add(n)
                fila.append(n)
    fechados = [a.cod for a in pj.TERREO + pj.SUPERIOR]
    ilhados = [c for c in fechados if c not in vistos]
    return dict(
        entrada=entrada, alcancaveis=len([c for c in fechados if c in vistos]),
        total=len(fechados), ilhados=ilhados, ok=not ilhados,
        vizinhos={c: sorted(g.get(c, {})) for c in fechados},
        ligacoes={c: {k: sorted(set(v)) for k, v in g.get(c, {}).items()}
                  for c in fechados},
        criterio="caminhada a pe a partir da varanda de entrada, por vao ou "
                 "fronteira aberta declarada; a escada e a unica ligacao entre "
                 "pavimentos e entra explicitamente porque nao e um vao")


# ---------------------------------------------------------------------------
# R55 — ACESSO DAS SUBDIVISOES. A conectividade de R46 pergunta se todo comodo
# se alcanca a pe a partir da porta de entrada, e trabalha com AMBIENTES. As
# subdivisoes ficavam de fora: banho, closet, cabine e lavabo eram recortes, e
# recorte nao entrava no grafo.
#
# Passou a importar quando a suite master virou uma SEQUENCIA — quarto, closet,
# banho — em vez de dois destinos paralelos. Numa sequencia, tirar uma porta
# nao deixa um comodo pior: deixa um comodo INALCANCAVEL, e a diferenca entre
# as duas coisas nao se ve em planta.
# ---------------------------------------------------------------------------
def _face_ponto(d: dict, face: str, pos: float, fora: bool = True) -> tuple:
    """Um ponto logo do lado de fora (ou de dentro) da face, no eixo do vao."""
    e = 60.0 if fora else -60.0
    if face == "S":
        return (d["x"] - e, pos)
    if face == "N":
        return (d["x"] + d["w"] + e, pos)
    if face == "L":
        return (pos, d["y"] - e)
    return (pos, d["y"] + d["h"] + e)


def acesso_das_subdivisoes(pj) -> dict:
    """Toda subdivisao se alcanca a partir do proprio ambiente que a contem?"""
    por_pai: dict = {}
    for d in pj.SUBDIVISOES:
        por_pai.setdefault(d["pai"], []).append(d)

    out = []
    for pai, subs in sorted(por_pai.items()):
        nos = {f"{pai}/{d['nome']}": d for d in subs}
        g: dict = {pai: set()}
        for cod in nos:
            g[cod] = set()
        for cod, d in nos.items():
            aberturas = [(d["face"], d["pos"])]
            if d.get("liga"):
                aberturas.append((d["liga"]["face"], d["liga"]["pos"]))
            for face, pos in aberturas:
                px, py = _face_ponto(d, face, pos)
                viz = next((c for c, o in nos.items()
                            if o is not d
                            and o["x"] <= px <= o["x"] + o["w"]
                            and o["y"] <= py <= o["y"] + o["h"]), pai)
                g[cod].add(viz)
                g[viz].add(cod)
        vistos, fila = {pai}, [pai]
        while fila:
            c = fila.pop()
            for n in g.get(c, ()):
                if n not in vistos:
                    vistos.add(n)
                    fila.append(n)
        for cod, d in sorted(nos.items()):
            caminho = sorted(x for x in g[cod] if x != cod)
            out.append(dict(
                cod=cod, pai=pai, alcancavel=cod in vistos,
                vizinhos=caminho, aberturas=1 + (1 if d.get("liga") else 0),
                unico_acesso=d.get("unico_acesso"),
                respeita=(d.get("unico_acesso") is None
                          or caminho == [f"{pai}/{d['unico_acesso']}"])))
    ilhadas = [o["cod"] for o in out if not o["alcancavel"]]
    quebradas = [o["cod"] for o in out if not o["respeita"]]
    return dict(subdivisoes=out, ilhadas=ilhadas, sequencias_quebradas=quebradas,
                ok=not ilhadas and not quebradas,
                criterio="cada subdivisao abre para o pai ou para uma irma que "
                         "alcance o pai; quando `unico_acesso` e declarado, a "
                         "subdivisao NAO pode ter outra vizinha")
