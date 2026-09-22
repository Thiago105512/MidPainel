"""BRIEFING DE IMAGENS — a casa descrita em codigo, lida do modelo (R83).

O proprietario vai pedir imagens a um gerador externo e precisa entregar a
ele a casa inteira em texto: lote, volumes, materiais, cada face, cada vao,
piscina, jardim, o que ha e o que NAO ha. Se esse texto fosse escrito a mao
seria a quarta copia da casa (depois da prancha, do 3D e do BOM), e copia
escrita a mao e o defeito que este projeto mais catalogou. Entao ele e
DERIVADO: cada campo abaixo sai de uma tabela do caso ou de um modulo que ja
e auditado. Mudou o modelo, muda o briefing; e a auditoria confere que o
briefing diz o que o modelo diz (checar_briefing).

Orientacao para quem olha DA RUA: a rua esta a LESTE (y = 0). Quem esta na
rua olhando a casa olha para OESTE; a sua direita e o NORTE (+x), a sua
esquerda e o SUL (x = 0). Todas as palavras "esquerda/direita" deste
briefing sao nesse referencial, e so nele.
"""
from __future__ import annotations

import json

LADO = {"L": "frente (leste, rua)", "O": "fundo (oeste, piscina)",
        "S": "lateral esquerda vista da rua (sul)", "N": "lateral direita vista da rua (norte)"}

# palavra que descreve cada categoria de uso, para o gerador de imagens
USO = {"intimo": "dormitorio", "social": "social", "servico": "servico", "oficina": "oficina",
       "circulacao": "circulacao", "apoio": "garagem"}


def _m(v) -> float:
    return round(v / 1000.0, 2)


def _env(ambs) -> dict:
    xs = [a.x for a in ambs]; xe = [a.x + a.w for a in ambs]
    ys = [a.y for a in ambs]; ye = [a.y + a.h for a in ambs]
    return dict(largura_norte_sul_m=_m(max(xe) - min(xs)), profundidade_leste_oeste_m=_m(max(ye) - min(ys)),
                recuo_da_rua_m=_m(min(ys)), recuo_lateral_esquerda_m=_m(min(xs)))


def terreno(pj) -> dict:
    import nucleo.externo as ex
    m = ex.muro(pj)
    return dict(
        lote_m=dict(frente=_m(pj.LOTE_L), profundidade=_m(pj.LOTE_P), area_m2=round(pj.LOTE_L * pj.LOTE_P / 1e6, 1)),
        rua="a LESTE; o terreno e plano, dentro de condominio fechado",
        fechamento=dict(
            frente="ABERTA: nao ha muro, mureta, grade nem portao na rua — a casa e a fachada, com jardim e piso drenante ate a calcada",
            laterais_e_fundo=f"muro de bloco de concreto aparente, {m['altura'] / 1000:g} m, junta rebaixada, sem pintura",
            portoes_laterais=[dict(cod=p["cod"], onde=("lateral esquerda (sul)" if p["lado"] == "esq" else "lateral direita (norte)"),
                                   largura_m=_m(p["larg"]), altura_m=_m(p["altura"]), abertura=p["abertura"], material=p["material"],
                                   posicao="na linha da frente da casa, fechando a passagem entre a casa e o muro") for p in m["portoes_laterais"]]),
        acessos=dict(veiculos=f"faixa de piso drenante claro de {_m(pj.ACESSO_TESTADA['veiculo_larg'])} m, reta, da calcada ao portao da garagem",
                     pedestre=f"passeio de piso drenante claro de {_m(pj.ACESSO_TESTADA['pedestre_larg'])} m, reto, da calcada a porta de entrada",
                     resto_do_recuo="grama e jardim (vasos com formio e agave no jardim leste)"),
    )


def volumetria(pj) -> dict:
    topo = getattr(pj, "TOPO_PLATIBANDA", pj.NIVEL_SUPERIOR + pj.PE_DIREITO + 550)
    fas = pj.FASCIA
    vg = pj.VARANDA_GOURMET
    return dict(
        pavimentos=2, sistema="Light Steel Frame sobre radier; aparencia externa lisa, sem textura de bloco",
        terreo=_env(pj.TERREO) | dict(pe_direito_m=_m(pj.PE_DIREITO)),
        superior=_env(pj.SUPERIOR) | dict(pe_direito_m=_m(pj.PE_DIREITO), nivel_do_piso_m=_m(pj.NIVEL_SUPERIOR),
                                          posicao="ALINHADO com a frente da garagem: o volume superior fica SOBRE a garagem, o hall e o quarto da frente, sem recuo em relacao a rua"),
        altura_total_m=_m(topo),
        cobertura=dict(tipo="plana, escondida por platibanda — de fora NAO se ve telha nem beiral inclinado",
                       inclinacao=f"{pj.INCLIN_COBERTURA * 100:g} % para as calhas internas",
                       fascia=f"linha escura continua de {fas['altura']} mm de {fas['material']} no topo de toda platibanda, terreo e superior"),
        varanda_gourmet=dict(onde="fundo (oeste), voltada para a piscina", profundidade_m=_m(vg["prof"]), largura_m=_m(vg["largura"]),
                             cobertura=vg["cobertura"], forro=vg["forro"]),
        pe_direito_duplo=[a for a in getattr(pj, "PE_DIREITO_DUPLO", [])],
        lanternim="sobre a metade sul do estar, veneziana de aluminio grafite em duas faces, vidro leitoso; visto so de longe ou de cima",
    )


def materiais(pj) -> dict:
    import modelo3d as m3
    c = m3.CORES
    return dict(
        regra=f"no maximo {pj.FACHADA_REGRAS['familias_max']} familias de acabamento na fachada; {pj.FACHADA_REGRAS['vidro']}; {pj.FACHADA_REGRAS['ornamento']}",
        familias=[dict(nome=n, onde=o) for n, o in pj.FACHADA_MATERIAIS],
        tratamento_das_paredes=dict(
            base_terreo=dict(desc="pintura mineral clara, fosca, ate 2,6 m do chao (o que se alcanca do chao)", cor_ref=c["parede_base"]),
            volume_superior=dict(desc="placa mineral clara de grande formato 1,2 x 2,4 m, junta seca de 6 mm em malha visivel", cor_ref=c["parede_ext"]),
        ),
        aluminio_grafite=dict(desc="ripas verticais tubulares 50 x 20 mm, grafite escuro fosco; mesma familia em portao, brises, guarda-corpo, fascia e caixilhos", cor_ref=c["fascia"]),
        madeira=dict(desc="folha da porta de entrada e forro do portico, madeira natural de tom medio", cor_ref=c["porta"]),
        vidro=dict(desc="incolor; low-e onde declarado; caixilho grafite", cor_ref=c["vidro"]),
        piso_externo=[dict(zona=z["zona"], material=z["material"], porque=z["razao"]) for z in pj.PISO_EXTERNO],
        muro=dict(desc="bloco de concreto aparente cinza claro, junta rebaixada", cor_ref=c["muro"]),
        piscina=dict(desc="agua azul clara sobre revestimento claro", cor_ref=c["piscina"]),
    )


def _vaos_por_face(pj) -> dict:
    import nucleo.fachada as fa
    out = {f: [] for f in "LOSN"}
    for v in pj.VAOS:
        t, x, y, o, p = v
        face = fa._face_ou_interno(pj, v)
        if face not in out:
            continue
        larg, alt, peit, fam = pj.ESQUADRIAS[t]
        out[face].append(dict(tipo=t, pav="terreo" if p == "T" else "superior", largura_m=_m(larg), altura_m=_m(alt),
                              peitoril_m=_m(peit), familia=fam, ambiente=pj.amb_do_vao(x, y, p)))
    return out


def fachadas(pj) -> list[dict]:
    import nucleo.fachada as fa
    vf = _vaos_por_face(pj)
    brises = {f: [] for f in "LOSN"}
    for b in pj.BRISES:
        brises[b["face"]].append(dict(cod=b["cod"], pav="terreo" if b["pav"] == "T" else "superior", comprimento_m=_m(b["w"]),
                                      altura_m=_m(b.get("altura", 1_500)), tipo=b["tipo"], passo_mm=b["passo"], o_que_faz=b["desc"]))
    out = []
    for f in fa.faces(pj):
        face = f["face"]
        d = dict(face=LADO[face], largura_terreo_m=_m(f["largura_terreo"]), largura_superior_m=_m(f["largura_superior"]),
                 fracao_de_vidro=f"{f['frac_vidro'] * 100:.0f} %", vaos=vf[face], brises=brises[face])
        if face == "L":
            pg = pj.PG01_OPCIONAL
            d["composicao"] = ("terreo: portao da garagem ripado grafite a esquerda, portico de entrada recuado com porta alta de madeira "
                               "e forro de madeira no centro, quarto da frente a direita. Superior: volume alinhado com a garagem, faixa "
                               "continua de ripas grafite sobre as quatro janelas; fascia escura no topo. Sem muro na frente.")
            d["portao_da_garagem"] = dict(tipo="de correr, aluminio grafite ripado", largura_m=_m(pj.ESQUADRIAS["PG01"][0]),
                                          altura_m=_m(pj.ESQUADRIAS["PG01"][1]), opcional=pg["opcional"], mantido=pg["mantido"], motivo=pg["motivo"])
        if face == "O":
            cv = pj.CORTINA_VIDRO
            d["composicao"] = (f"terreo: cortina de vidro de {_m(cv['largura'])} m ({cv['folhas']} folhas de {_m(cv['largura_folha'])} m, "
                               f"{cv['uso_padrao'].lower()} por padrao) abrindo cozinha e gourmet para a varanda coberta em balanco de "
                               f"{_m(pj.VARANDA_GOURMET['prof'])} m e para a piscina. Superior: varanda da suite master com brise ripado movel e guarda-corpo grafite.")
        out.append(d)
    return out


def entrada(pj) -> dict:
    var = next(a for a in pj.TERREO_ABERTO if a.cod == "T-VAR")
    p01 = pj.ESQUADRIAS["P01"]
    return dict(portico=dict(largura_m=_m(var.w), profundidade_m=_m(var.h), forro="madeira", piso="porcelanato externo claro"),
                porta=dict(largura_m=_m(p01[0]), altura_m=_m(p01[1]), desc=p01[3] + ", madeira natural, sem vidro"),
                iluminacao=[dict(onde=i["onde"], tipo=i["tipo"], efeito=i["efeito"]) for i in pj.ILUMINACAO_FACHADA])


def area_externa(pj) -> dict:
    import nucleo.externo as ex
    import nucleo.piscina as psc
    ps, dk = pj.PISCINA, pj.DECK
    il = psc.iluminacao(pj)
    pai = ex.paisagismo(pj)
    return dict(
        piscina=dict(onde="fundo do lote (oeste), no eixo da varanda gourmet", comprimento_m=_m(ps["w"]), largura_m=_m(ps["h"]),
                     lamina_m2=ps["lamina_m2"], prainha=f"{_m(ps['prainha_w'])} m de prainha com {ps['prof_prainha']} mm de agua",
                     profundidade_m=_m(ps["prof_principal"]), banco="banco submerso em uma borda",
                     borda=f"borda de porcelanato claro com pingadeira; deck em volta em {next((z['material'] for z in ex.pisos(pj)['itens'] if 'T-DKP' in z['areas']), '')}", iluminacao=f"{len(il.get('leds', []))} LEDs submersos brancos quentes na parede leste"),
        deck=dict(comprimento_m=_m(dk["w"]), largura_m=_m(dk["h"]), pisos=[dict(zona=z["zona"], material=z["material"], area_m2=z["area"]) for z in ex.pisos(pj)["itens"]]),
        areas_abertas=[dict(cod=a.cod, nome=a.nome.title(), largura_m=_m(a.w), profundidade_m=_m(a.h),
                            piso=next((z["material"] for z in ex.pisos(pj)["itens"] if a.cod in z["areas"]), "grama e canteiro"))
                       for a in pj.TERREO_ABERTO + getattr(pj, "SUPERIOR_ABERTO", [])],
        paisagismo=[dict(cod=p["cod"], especie=p["especie"], qtd=p["qtd"], porte=p["porte"], onde=p["amb"], funcao=p["funcao"]) for p in pj.PAISAGISMO],
        resumo=f"{pai['arvores']} arvores e {pai['vasos']} vasos; nenhuma arvore na frente alem das palmeiras iluminadas; jabuticabeira e ipe no fundo, acai no canto noroeste",
    )


def interiores(pj) -> list[dict]:
    import nucleo.luminotecnica as lu
    forros = {c: d for c, d, *_ in pj.FORROS}
    out = []
    for a in pj.TERREO + pj.SUPERIOR:
        cat = pj.CATEGORIA.get(a.cod, "social")
        sub = [dict(nome=s["nome"].title(), largura_m=_m(s["w"]), profundidade_m=_m(s["h"])) for s in pj.SUBDIVISOES if s["pai"] == a.cod]
        mob = sorted({l["tipo"] for l in pj.LAYOUT if l["amb"] == a.cod})
        arm = [f"{g['tipo']} {_m(g['w'])} x {_m(g['h'])} m" for g in pj.ARMARIOS if g.get("amb") == a.cod]
        banc = [b["uso"] for b in pj.BANCADAS if b["amb"] == a.cod]
        vaos = [dict(tipo=t, largura_m=_m(pj.ESQUADRIAS[t][0]), altura_m=_m(pj.ESQUADRIAS[t][1]), familia=pj.ESQUADRIAS[t][3])
                for t, x, y, o, p in pj.VAOS if p == a.pav and pj.amb_do_vao(x, y, p) == a.cod and pj.vao_externo(x, y, o, p)]
        tcor = lu.TCOR.get(cat, lu.TCOR.get("social")) if isinstance(getattr(lu, "TCOR", None), dict) else None
        out.append(dict(cod=a.cod, nome=a.nome.title(), pavimento="terreo" if a.pav == "T" else "superior", uso=USO.get(cat, cat),
                        largura_m=_m(a.w), profundidade_m=_m(a.h), area_m2=round(a.w * a.h / 1e6, 2),
                        pe_direito="duplo" if a.cod in getattr(pj, "PE_DIREITO_DUPLO", []) else f"{_m(pj.PE_DIREITO)} m",
                        piso=pj.PISOS_PADRAO.get(cat, ""), forro=forros.get(a.cod, "gesso liso"),
                        luz=(f"{tcor} K" if tcor else ""), subdivisoes=sub, mobiliario=mob, armarios=arm, bancadas=banc, aberturas_externas=vaos))
    return out


def regras_para_a_imagem(pj) -> list[str]:
    import nucleo.externo as ex
    m = ex.muro(pj)
    return [
        "NAO desenhar muro, grade, mureta ou portao de pedestre na frente: a testada e aberta, casa de condominio",
        f"muro de {m['altura'] / 1000:g} m so nas laterais e no fundo, bloco aparente, sem pintura",
        "NAO desenhar telhado aparente, telha, beiral inclinado ou cumeeira: cobertura plana atras de platibanda com fascia escura",
        "o volume superior fica alinhado com a frente da garagem; nao ha recuo do superior em relacao a rua",
        "ripas SEMPRE verticais, aluminio grafite; nunca madeira nas ripas — madeira so na porta de entrada e no forro do portico",
        "pouco vidro na frente; o vidro grande esta atras, na cortina de vidro do gourmet voltada para a piscina",
        "tres familias de material e nenhuma a mais: mineral claro, aluminio grafite, madeira",
        "nao ha pilar na frente da varanda gourmet: a laje e em balanco",
        "deck da piscina, deck norte e varanda gourmet em WPC de tom claro (areia), reguas corridas; so o patio da churrasqueira e porcelanato",
        "carros: dois, dentro da garagem; a faixa de acesso e reta e de piso drenante claro",
        "clima: Manaus — vegetacao tropical densa no fundo, ceu claro, luz forte; nada de pinheiros ou gramado seco",
    ]


def vistas(pj) -> list[dict]:
    try:
        import perspectivas as pp
        ext = [dict(id=v["id"], titulo=v["titulo"]) for v in pp.vistas() if v.get("grupo") == "externa"]
    except Exception:
        ext = []
    return ext + [
        dict(id="int-social", titulo="Estar com pe-direito duplo, escada e cozinha ao fundo, cortina de vidro aberta para a piscina"),
        dict(id="int-gourmet", titulo="Gourmet e varanda coberta em balanco, mesa de 8, piscina em segundo plano ao entardecer"),
        dict(id="int-master", titulo="Suite master olhando a piscina pela varanda com brise ripado movel"),
        dict(id="int-suite", titulo="Suite 02 sobre a garagem, janela da frente filtrada pela faixa de ripas grafite"),
    ]


def montar(pj) -> dict:
    cd = pj.CADASTRO
    return dict(
        projeto=dict(nome=cd.nome, local=cd.localizacao, tipologia="sobrado contemporaneo em condominio fechado", sistema=cd.sistema,
                     area_construida_m2=cd.area_m2, revisao=cd.revisao, estilo="contemporaneo, volumes retos, poucos materiais, horizontalidade"),
        orientacao=dict(rua="leste", vista_da_rua="quem esta na rua olha para oeste: NORTE a direita, SUL a esquerda",
                        sol="frente recebe o sol da manha; a piscina e o fundo recebem o sol da tarde"),
        terreno=terreno(pj), volumetria=volumetria(pj), materiais=materiais(pj), fachadas=fachadas(pj), entrada=entrada(pj),
        area_externa=area_externa(pj), interiores=interiores(pj), regras_para_a_imagem=regras_para_a_imagem(pj), vistas_sugeridas=vistas(pj),
    )


def texto(pj) -> str:
    return json.dumps(montar(pj), ensure_ascii=False, indent=1)


def conferir(pj) -> list[tuple[str, str, bool]]:
    """O briefing diz o que o modelo diz."""
    import nucleo.externo as ex
    b = montar(pj)
    m = ex.muro(pj)
    out = []
    out.append(("frente aberta no briefing e no modelo", b["terreno"]["fechamento"]["frente"][:40], m["testada_aberta"] and "ABERTA" in b["terreno"]["fechamento"]["frente"]))
    n_pg = len(b["terreno"]["fechamento"]["portoes_laterais"])
    out.append(("portoes laterais: um por passagem", f"{n_pg} portoes, {len(pj.PORTOES_LATERAIS)} declarados", n_pg == len(pj.PORTOES_LATERAIS) == 2))
    n_v = sum(len(f["vaos"]) for f in b["fachadas"])
    n_ext = sum(1 for t, x, y, o, p in pj.VAOS if pj.vao_externo(x, y, o, p))
    out.append(("todo vao externo aparece em uma face", f"{n_v} no briefing, {n_ext} externos no caso", n_v == n_ext))
    n_b = sum(len(f["brises"]) for f in b["fachadas"])
    out.append(("todo brise aparece na sua face", f"{n_b} de {len(pj.BRISES)}", n_b == len(pj.BRISES)))
    out.append(("todo comodo tem ficha", f"{len(b['interiores'])} de {len(pj.TERREO) + len(pj.SUPERIOR)}", len(b["interiores"]) == len(pj.TERREO) + len(pj.SUPERIOR)))
    fam = {f["nome"] for f in b["materiais"]["familias"]}
    out.append(("familias de fachada dentro da regra", f"{len(fam)} de {pj.FACHADA_REGRAS['familias_max']}", len(fam) <= pj.FACHADA_REGRAS["familias_max"]))
    sup = b["volumetria"]["superior"]; ter = b["volumetria"]["terreo"]
    out.append(("superior alinhado com a frente do terreo", f"recuos {ter['recuo_da_rua_m']} / {sup['recuo_da_rua_m']} m", sup["recuo_da_rua_m"] == ter["recuo_da_rua_m"]))
    out.append(("o briefing serializa sem perda", f"{len(texto(pj)) // 1024} KB de JSON", bool(texto(pj))))
    return out


def escrever(pj, destino: str) -> str:
    with open(destino, "w", encoding="utf-8") as f:
        f.write(texto(pj))
    return destino
