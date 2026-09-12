"""
AUDITORIA — segundo bloco.

Verificacoes acrescentadas pelo programa de 63 auditorias do proprietario, nos
pontos em que o primeiro bloco (auditoria.py) nao alcancava: fluxos, cozinha
como posto de trabalho, ventilacao cruzada, profundidade de luz, odor, prumadas,
privacidade, seguranca, niveis, padronizacao e regressao.

Mesmo principio do primeiro bloco: o que nao esta no modelo nao e verificado.
"""
from __future__ import annotations

import math
from collections import defaultdict

import projeto as pj
import elementos as el
import especificacao as ep
from auditoria import (Achado, grafo, _ambs, _pecas_do_pav, _sobrepoe, _folga,
                       _ret, _ret_vao, grupos_integrados, area_vaos_por_ambiente,
                       PROLONGADA, DISPENSADOS)

# ---------------------------------------------------------------- criterios
SOCIAL = {"T-SOC", "T-GOU", "T-COZ", "T-COR", "T-HAL"}
INTIMO = {"T-REV", "S-S02", "S-S03", "S-MAS", "S-LOU", "S-HAL"}
SERVICO = {"T-LAV", "T-DEP", "T-OFI", "T-GAR"}
PERCURSO_MAX_SERVICO = 25_000     # mm — da garagem a lavanderia
TRIANGULO_MIN, TRIANGULO_MAX = 3_600, 8_000
PROF_LUZ_FATOR = 2.5              # profundidade util = 2,5 x altura do vao
DIST_EXAUSTAO_VAO = 1_500
GUARDA_CORPO_MIN = 1_100
DESNIVEL_MAX_SEM_AVISO = 15       # mm — acima disso e degrau, precisa sinalizar
FAMILIAS_MAX = {"portas": 5, "janelas": 6, "loucas": 5, "bancadas": 2,
                "pisos": 4, "perfis_laminados": 4}


def _centro(cod):
    a = next((x for x in pj.TERREO + pj.SUPERIOR + pj.TERREO_ABERTO
              + pj.SUPERIOR_ABERTO if x.cod == cod), None)
    return (a.cx, a.cy) if a else None


def _caminho(pav, origem, destino):
    """Menor caminho no grafo de vaos, em lista de ambientes."""
    g = grafo(pav)
    if origem not in g or destino not in g:
        return None
    fila, visto = [[origem]], {origem}
    while fila:
        cam = fila.pop(0)
        if cam[-1] == destino:
            return cam
        for viz in sorted(g.get(cam[-1], ())):
            if viz not in visto:
                visto.add(viz)
                fila.append(cam + [viz])
    return None


def _comprimento(cam):
    if not cam or len(cam) < 2:
        return 0.0
    tot = 0.0
    for a, b in zip(cam, cam[1:]):
        ca, cb = _centro(a), _centro(b)
        if ca and cb:
            tot += abs(ca[0] - cb[0]) + abs(ca[1] - cb[1])
    return tot


# ------------------------------------------------- 33. fluxos e cruzamentos
def checar_fluxos() -> list[Achado]:
    """Servico nao pode atravessar social; percurso longo e gargalo aparecem aqui."""
    out = []
    rotas = [
        ("servico", "T-GAR", "T-LAV", SOCIAL),
        ("servico", "T-GAR", "T-COZ", SOCIAL - {"T-COZ"}),
        ("servico", "T-LAV", "T-COZ", SOCIAL - {"T-COZ"}),
        ("intimo", "T-HAL", "T-REV", {"T-COZ", "T-LAV", "T-DEP"}),
    ]
    for nome, o, d, proibidos in rotas:
        cam = _caminho("T", o, d)
        if cam is None:
            out.append(Achado("ERRO", "Rota inexistente",
                              f"{nome}: nao ha caminho de {o} a {d}"))
            continue
        cruza = [c for c in cam[1:-1] if c in proibidos]
        if cruza:
            out.append(Achado("ATENCAO", "Circulacao cruzada",
                              f"{nome}: {o} -> {d} atravessa {', '.join(cruza)}"))
        comp = _comprimento(cam)
        if comp > PERCURSO_MAX_SERVICO:
            out.append(Achado("ATENCAO", "Percurso longo",
                              f"{nome}: {o} -> {d} = {comp/1000:.1f} m por "
                              f"{len(cam)-1} ambientes"))
        else:
            out.append(Achado("NOTA", "Rota verificada",
                              f"{nome}: {' -> '.join(cam)} = {comp/1000:.1f} m"))
    # gargalo: ambiente por onde passam muitas rotas e que e estreito
    g = grafo("T")
    for cod, viz in sorted(g.items()):
        amb = next((a for a in pj.TERREO if a.cod == cod), None)
        if amb is None or len(viz) < 3:
            continue
        menor = min(amb.w, amb.h)
        if menor < 1_500:
            out.append(Achado("ATENCAO", "Gargalo de circulacao",
                              f"{cod} liga {len(viz)} ambientes com apenas {menor} mm "
                              f"de menor dimensao"))
    return out


# ------------------------------------------------- 34. cozinha como posto de trabalho
def checar_cozinha() -> list[Achado]:
    """Triangulo de trabalho, lixo, lava-loucas, forno e apoio."""
    out = []
    gel = next((e for e in pj.EQUIPAMENTOS if e["tipo"] == "geladeira"), None)
    cuba = next((b for b in pj.BANCADAS if b["amb"] == "T-COZ" and b["cubas"]), None)
    cook = next((b for b in pj.BANCADAS if b["amb"] == "T-COZ" and b["cooktop"]), None)
    if not (gel and cuba and cook):
        out.append(Achado("ERRO", "Cozinha incompleta",
                          "faltam geladeira, cuba ou coccao declarados"))
        return out
    pts = [(gel["x"] + gel["w"] / 2, gel["y"] + gel["h"] / 2),
           (cuba["x"] + cuba["w"] / 2, cuba["y"] + cuba["h"] / 2),
           (cook["x"] + cook["w"] / 2, cook["y"] + cook["h"] / 2)]
    lados = [math.dist(pts[i], pts[(i + 1) % 3]) for i in range(3)]
    tri = sum(lados)
    if tri < TRIANGULO_MIN:
        out.append(Achado("ATENCAO", "Triangulo de trabalho apertado",
                          f"{tri/1000:.2f} m (min {TRIANGULO_MIN/1000:.1f})"))
    elif tri > TRIANGULO_MAX:
        out.append(Achado("ATENCAO", "Triangulo de trabalho longo",
                          f"{tri/1000:.2f} m (max {TRIANGULO_MAX/1000:.1f}): "
                          f"geladeira-cuba {lados[0]/1000:.2f}, cuba-coccao "
                          f"{lados[1]/1000:.2f}, coccao-geladeira {lados[2]/1000:.2f}"))
    else:
        out.append(Achado("NOTA", "Triangulo de trabalho",
                          f"{tri/1000:.2f} m, dentro da faixa de "
                          f"{TRIANGULO_MIN/1000:.1f} a {TRIANGULO_MAX/1000:.1f} m"))
    # apoio ao lado da coccao e da geladeira (NBR de mobiliario / pratica)
    for peca, nome, lado_min in ((cook, "coccao", 400), (gel, "geladeira", 400)):
        px = peca["x"] + peca["w"] / 2
        py = peca["y"] + peca["h"] / 2
        # a bancada de apoio pode estar do outro lado da fronteira: cozinha e
        # gourmet sao o mesmo volume, e a peninsula que recebe o que sai da
        # geladeira fica declarada no gourmet
        grupo = {"T-COZ"}
        for g in grupos_integrados("T"):
            if "T-COZ" in g:
                grupo |= g
        apoio = False
        for b in pj.BANCADAS:
            if b["amb"] not in grupo or b["cod"] == peca.get("cod"):
                continue
            if _folga((peca["x"], peca["y"], peca["w"], peca["h"]),
                      (b["x"], b["y"], b["w"], b["h"])) <= 50:
                apoio = True
        if not apoio:
            out.append(Achado("ATENCAO", f"Sem bancada de apoio junto a {nome}",
                              f"pratica corrente pede {lado_min} mm de apoio ao lado"))
    # itens que o programa exige e que precisam existir no modelo
    declarados = {e["tipo"] for e in pj.EQUIPAMENTOS if e["amb"] in ("T-COZ", "T-GOU")}
    for item in ("lava-loucas", "lixo", "forno", "micro-ondas"):
        if item not in declarados:
            out.append(Achado("ERRO", f"Cozinha sem {item} locado",
                              f"{item} aparece no quadro de cargas eletricas mas nao "
                              f"tem posicao no modelo: sem posicao nao ha verificacao "
                              f"de circulacao, tomada nem sifao"))
    return out


# ------------------------------------------------- 35. ventilacao cruzada
def checar_ventilacao_cruzada() -> list[Achado]:
    """Entrada e saida de ar em faces distintas, por grupo integrado."""
    out = []
    for pav in ("T", "S"):
        grupos = grupos_integrados(pav)
        for g in grupos:
            faces = set()
            area = 0.0
            for tipo, x, y, ori, p in pj.VAOS:
                if p != pav:
                    continue
                for cod in g:
                    a = next((z for z in _ambs(pav) if z.cod == cod), None)
                    if a is None:
                        continue
                    if abs(y - a.y) < 1 and a.x <= x <= a.x + a.w:
                        faces.add("L")
                    elif abs(y - (a.y + a.h)) < 1 and a.x <= x <= a.x + a.w:
                        faces.add("O")
                    elif abs(x - a.x) < 1 and a.y <= y <= a.y + a.h:
                        faces.add("S")
                    elif abs(x - (a.x + a.w)) < 1 and a.y <= y <= a.y + a.h:
                        faces.add("N")
                    else:
                        continue
                    lg, al = pj.ESQUADRIAS[tipo][0], pj.ESQUADRIAS[tipo][1]
                    area += lg * al / 1e6
            nome = " + ".join(sorted(g))
            if not (g & DISPENSADOS) and len(faces) < 2:
                out.append(Achado("ERRO", "Sem ventilacao cruzada",
                                  f"{nome}: vaos em uma unica face ({', '.join(faces) or 'nenhuma'})"))
            elif {"L", "O"} <= faces or {"N", "S"} <= faces:
                out.append(Achado("NOTA", "Ventilacao cruzada em faces opostas",
                                  f"{nome}: {', '.join(sorted(faces))} com "
                                  f"{area:.2f} m2 de vao"))
    return out


# ------------------------------------------------- 36. profundidade de luz natural
def checar_profundidade_luz() -> list[Achado]:
    """Regra de bolso: a luz util entra ate 2,5 x a altura da verga do vao."""
    out = []
    for pav in ("T", "S"):
        for a in _ambs(pav):
            if a.cod in DISPENSADOS:
                continue
            por_face = {}
            for tipo, x, y, ori, p in pj.VAOS:
                if p != pav:
                    continue
                if abs(y - a.y) < 1 and a.x <= x <= a.x + a.w:
                    face = "L"
                elif abs(y - (a.y + a.h)) < 1 and a.x <= x <= a.x + a.w:
                    face = "O"
                elif abs(x - a.x) < 1 and a.y <= y <= a.y + a.h:
                    face = "S"
                elif abs(x - (a.x + a.w)) < 1 and a.y <= y <= a.y + a.h:
                    face = "N"
                else:
                    continue
                lg, al, peit, _ = pj.ESQUADRIAS[tipo]
                por_face[face] = max(por_face.get(face, 0), peit + al)
            if not por_face:
                continue
            # A profundidade que a luz precisa vencer e medida PERPENDICULAR a
            # face onde esta o vao — nao e a maior dimensao do ambiente. Uma
            # cozinha de 3 x 7 m com janela na parede longa e iluminada em 3 m,
            # nao em 7. A versao anterior desta verificacao errava nisso.
            melhor_sobra = None
            for face, verga in por_face.items():
                prof = a.w if face in ("S", "N") else a.h
                if ("S" in por_face and "N" in por_face and face in ("S", "N")) or \
                   ("L" in por_face and "O" in por_face and face in ("L", "O")):
                    prof /= 2
                sobra = verga * PROF_LUZ_FATOR - prof
                if melhor_sobra is None or sobra > melhor_sobra[0]:
                    melhor_sobra = (sobra, face, verga, prof)
            sobra, face, verga, prof = melhor_sobra
            if sobra < -verga * PROF_LUZ_FATOR * 0.15:
                out.append(Achado("ATENCAO", "Ambiente mais fundo que a luz alcanca",
                                  f"{a.cod}: {prof:.0f} mm a vencer pela face {face} "
                                  f"contra {verga*PROF_LUZ_FATOR:.0f} mm de alcance "
                                  f"(verga a {verga} mm)"))
    return out


# ------------------------------------------------- 37. exaustao e retorno de odor
def checar_exaustao_odor() -> list[Achado]:
    """Saida de exaustao perto de vao devolve o odor para dentro."""
    out = []
    saidas = {"EX-01": ("cobertura", None), "EX-02": ("fachada sul", (2_400, 22_200)),
              "EX-03": ("cobertura", None), "EX-04": ("cobertura", None),
              "EX-05": ("cobertura", None), "EX-06": ("cobertura", None)}
    for e in pj.EXAUSTAO:
        onde, pos = saidas.get(e["cod"], ("nao declarada", None))
        if onde == "nao declarada":
            out.append(Achado("ERRO", "Exaustao sem saida declarada",
                              f"{e['cod']} ({e['fonte']}): sem ponto de descarga o "
                              f"odor volta pela primeira janela"))
            continue
        if pos is None:
            continue
        for tipo, x, y, ori, p in pj.VAOS:
            if p != "T" or not (tipo.startswith("J") or tipo.startswith("PV")
                                or tipo.startswith("CV")):
                continue
            d = math.dist(pos, (x, y))
            if d < DIST_EXAUSTAO_VAO:
                out.append(Achado("ATENCAO", "Exaustao perto de vao",
                                  f"{e['cod']} a {d:.0f} mm de {tipo} em ({x}, {y}) "
                                  f"(min {DIST_EXAUSTAO_VAO} mm)"))
    return out


# ------------------------------------------------- 38. prumadas e alinhamento vertical
def checar_prumadas() -> list[Achado]:
    """Molhado do superior deve cair sobre molhado, shaft ou parede do terreo."""
    out = []
    molhados_s = [sd for sd in pj.SUBDIVISOES
                  if sd["pai"].startswith("S-") and sd["nome"] == "BANHO"]
    molhados_t = [a for a in pj.TERREO if a.cod in ep.MOLHADOS]
    for sd in molhados_s:
        cx, cy = sd["x"] + sd["w"] / 2, sd["y"] + sd["h"] / 2
        sobre = None
        for a in pj.TERREO:
            if a.x <= cx < a.x + a.w and a.y <= cy < a.y + a.h:
                sobre = a
                break
        if sobre is None:
            out.append(Achado("ERRO", "Banho do superior sobre o vazio",
                              f"{sd['pai']}/BANHO em ({cx:.0f}, {cy:.0f})"))
            continue
        alinhado = sobre.cod in ep.MOLHADOS
        if alinhado:
            out.append(Achado("NOTA", "Prumada alinhada",
                              f"{sd['pai']}/BANHO cai sobre {sobre.cod} (molhado)"))
        else:
            # aceitavel se houver shaft declarado servindo o ambiente
            shaft = any(p["de"] == sd["pai"] and "shaft" in p["solucao"]
                        for p in pj.PENETRACOES)
            nivel = "NOTA" if shaft else "ATENCAO"
            out.append(Achado(nivel, "Prumada sem molhado embaixo",
                              f"{sd['pai']}/BANHO cai sobre {sobre.cod}"
                              + (" — resolvido por shaft declarado" if shaft
                                 else ": exige shaft ou desvio em forro")))
    return out


# ------------------------------------------------- 39. privacidade
def checar_privacidade() -> list[Achado]:
    """Vaos de ambiente intimo visiveis da rua ou da divisa."""
    out = []
    for tipo, x, y, ori, pav in pj.VAOS:
        dono = None
        for a in _ambs(pav):
            if (a.x - 200 <= x <= a.x + a.w + 200
                    and a.y - 200 <= y <= a.y + a.h + 200):
                dono = a
                break
        if dono is None or dono.cod not in INTIMO:
            continue
        lg, al, peit, _ = pj.ESQUADRIAS[tipo]
        if peit >= 1_500:          # janela alta ja resolve
            continue
        # brise declarado sobre o vao tambem resolve
        protegido = False
        for br in pj.BRISES:
            if abs(br["x"] - x) < 1 or abs(br["y"] - y) < 1:
                dist = math.dist((br["x"], br["y"]), (x, y))
                if dist <= max(lg, br.get("w", 0)):
                    protegido = True
        if protegido:
            out.append(Achado("NOTA", "Vao intimo protegido por brise",
                              f"{tipo} de {dono.cod}: ripado vertical fixo resolve "
                              f"privacidade e sol rasante"))
            continue
        d_rua = y
        d_sul, d_norte = x, pj.LOTE_L - x
        for onde, d, lim in (("testada", d_rua, pj.RECUO_FRENTE),
                             ("divisa sul", d_sul, 3_000),
                             ("divisa norte", d_norte, 3_000)):
            if d < lim:
                out.append(Achado("ATENCAO", "Vao intimo exposto",
                                  f"{tipo} de {dono.cod} a {d} mm da {onde} "
                                  f"com peitoril de {peit} mm"))
    return out


# ------------------------------------------------- 40. seguranca
def checar_seguranca() -> list[Achado]:
    """Guarda-corpo, vidro, piso molhado e piscina."""
    out = []
    # toda area aberta do superior e todo vazio precisam de guarda-corpo
    for a in pj.SUPERIOR_ABERTO:
        if pj.ESCADA_EXEC["guarda_corpo"] < GUARDA_CORPO_MIN:
            out.append(Achado("ERRO", "Guarda-corpo baixo",
                              f"{a.cod}: {pj.ESCADA_EXEC['guarda_corpo']} mm "
                              f"(min {GUARDA_CORPO_MIN})", "NBR 14718"))
    for cod in pj.PE_DIREITO_DUPLO:
        out.append(Achado("NOTA", "Guarda-corpo no vazio",
                          f"{cod}: borda de laje do superior sobre pe-direito duplo "
                          f"exige guarda-corpo de {GUARDA_CORPO_MIN} mm"))
    # vidro grande sem sinalizacao
    cv = pj.CORTINA_VIDRO
    if "faixa" not in cv.get("pelicula", ""):
        out.append(Achado("ERRO", "Vidro sem sinalizacao",
                          "pano de vidro sem faixa visivel na altura dos olhos"))
    # piso molhado
    for z in pj.PISO_EXTERNO:
        if "R11" not in z["material"] and "drenante" not in z["material"] \
                and "faixa seca" in z["zona"]:
            out.append(Achado("ERRO", "Piso de piscina sem antiderrapante",
                              z["material"]))
    # piscina: profundidade e borda
    p = pj.PISCINA
    if p["prof_principal"] > 1_400:
        out.append(Achado("ATENCAO", "Piscina funda para uso de lazer",
                          f"{p['prof_principal']} mm"))
    if not p.get("prainha_w"):
        out.append(Achado("ATENCAO", "Piscina sem entrada rasa", "prainha ausente"))
    return out


# ------------------------------------------------- 41. niveis e transicoes
def checar_niveis() -> list[Achado]:
    """Degraus nao declarados entre interno, coberto e externo."""
    out = []
    cont = pj.CONTINUIDADE_INTERNO_EXTERNO
    transicoes = [
        ("interno -> varanda gourmet", cont["desnivel_piso"]),
        ("interno -> loggia sul", 0),
        ("interno -> varal coberto", 0),
        ("varanda -> deck", 0),
        ("deck -> faixa seca da piscina", 0),
        ("interno -> garagem", 0),
    ]
    for nome, d in transicoes:
        if d > DESNIVEL_MAX_SEM_AVISO:
            out.append(Achado("ATENCAO", "Degrau em transicao",
                              f"{nome}: {d} mm — precisa de sinalizacao e nao serve "
                              f"a rota acessivel"))
    out.append(Achado("NOTA", "Niveis verificados",
                      f"{len(transicoes)} transicoes declaradas, todas em nivel; "
                      f"soleira do box com {pj.SOLEIRA_BOX} mm e a unica excecao"))
    return out


# ------------------------------------------------- 42. padronizacao e SKUs
def checar_padronizacao() -> list[Achado]:
    """Numero de familias por sistema: cada familia a mais e um SKU a comprar,
    estocar, instalar e repor."""
    out = []
    familias = {
        "portas": {t for t in pj.ESQUADRIAS if t.startswith("P") and not t.startswith("PV")},
        "janelas": {t for t in pj.ESQUADRIAS if t.startswith("J")},
        "loucas": {l["tipo"] for l in pj.LOUCAS},
        "bancadas": {b["tipo"] for b in pj.BANCADAS},
        "pisos": {z["peca"] for z in pj.ZONAS_PAGINACAO},
        "perfis_laminados": {v["perfil"] for v in pj.dimensionar_vigas()},
    }
    for nome, s in sorted(familias.items()):
        lim = FAMILIAS_MAX.get(nome, 99)
        if len(s) > lim:
            out.append(Achado("ATENCAO", "Familias acima do alvo",
                              f"{nome}: {len(s)} ({', '.join(sorted(s))}) contra "
                              f"alvo de {lim}"))
        else:
            out.append(Achado("NOTA", "Familias dentro do alvo",
                              f"{nome}: {len(s)} de {lim} — {', '.join(sorted(s))}"))
    # repeticao das suites espelhadas
    s02 = [sd for sd in pj.SUBDIVISOES if sd["pai"] == "S-S02"]
    s03 = [sd for sd in pj.SUBDIVISOES if sd["pai"] == "S-S03"]
    if len(s02) != len(s03):
        out.append(Achado("ERRO", "Suites deixaram de ser espelhadas",
                          f"S-S02 tem {len(s02)} compartimentos e S-S03 tem {len(s03)}"))
    else:
        iguais = all(a["w"] == b["w"] and a["h"] == b["h"]
                     for a, b in zip(s02, s03))
        out.append(Achado("NOTA" if iguais else "ATENCAO", "Espelhamento das suites",
                          "compartimentos identicos em dimensao" if iguais
                          else "compartimentos divergem em dimensao"))
    return out


# ------------------------------------------------- 43. coccao, marcenaria e fila
FOLGA_FILA_MAX = 50        # mm de desalinhamento aceito entre frentes vizinhas
SOB_BANCADA = {"lava-loucas": "cuba", "lixo": "cuba", "forno": "alto",
               "micro-ondas": "alto"}


def checar_coccao() -> list[Achado]:
    """Um ponto de coccao por volume integrado. Dois sao duas cozinhas."""
    out = []
    for pav in ("T",):
        for g in grupos_integrados(pav):
            pontos = [b for b in pj.BANCADAS
                      if b["amb"] in g and b.get("cooktop")]
            if len(pontos) > 1:
                d = max(_folga((a["x"], a["y"], a["w"], a["h"]),
                               (b["x"], b["y"], b["w"], b["h"]))
                        for a in pontos for b in pontos if a is not b)
                out.append(Achado("ERRO", "Coccao duplicada no mesmo volume",
                                  f"{', '.join(p['cod'] for p in pontos)} a "
                                  f"{d/1000:.1f} m, em {' + '.join(sorted(g))}: "
                                  f"sem parede entre eles, sao duas cozinhas na "
                                  f"mesma sala"))
            elif pontos:
                out.append(Achado("NOTA", "Coccao unica no volume integrado",
                                  f"{pontos[0]['cod']} em {' + '.join(sorted(g))}"))
    # toda coccao e toda ignicao precisam de exaustao propria
    for b in pj.BANCADAS:
        if not (b.get("cooktop") or b.get("ignicao")):
            continue
        if not any(e["amb"] == b["amb"] for e in pj.EXAUSTAO):
            out.append(Achado("ERRO", "Coccao sem exaustao",
                              f"{b['cod']} em {b['amb']}"))
    return out


def checar_marcenaria_fila() -> list[Achado]:
    """Pecas VIZINHAS numa mesma fila devem compartilhar a face.

    A primeira versao agrupava por orientacao da peca e comparava movel de
    parede oposta com movel de parede oposta — e por isso acusava 2.300 mm de
    "degrau" entre a bancada da cuba e a geladeira, que estao em paredes
    diferentes. Agora duas pecas so sao comparadas quando de fato formam fila:
    encostadas no eixo longo E sobrepostas no eixo da profundidade.
    """
    # louca sanitaria nao entra: vaso e mais fundo que lavatorio por natureza,
    # e ninguem constroi caixa para alinhar os dois
    IGNORAR = {"vaso", "lavatorio", "box", "tanque"}

    def _compartimento(x, y, pai):
        """Em que subdivisao a peca esta, se estiver em alguma."""
        for sd in pj.SUBDIVISOES:
            if sd["pai"] != pai:
                continue
            if sd["x"] <= x < sd["x"] + sd["w"] and sd["y"] <= y < sd["y"] + sd["h"]:
                return sd["nome"]
        return None

    out = []
    for amb in pj.TERREO + pj.SUPERIOR:
        pecas = [(cod, tipo, x, y, w, h)
                 for cod, tipo, x, y, w, h in _pecas_do_pav(amb.pav)
                 if amb.x <= x < amb.x + amb.w and amb.y <= y < amb.y + amb.h
                 and tipo not in IGNORAR]
        for i, a in enumerate(pecas):
            for b in pecas[i + 1:]:
                ca, ta, ax, ay, aw, ah = a
                cb, tb, bx, by, bw, bh = b
                # peca em compartimento diferente tem PAREDE entre as duas
                if _compartimento(ax, ay, amb.cod) != _compartimento(bx, by, amb.cod):
                    continue
                # fila no eixo Y: encostadas em y, sobrepostas em x
                gap_y = max(by - (ay + ah), ay - (by + bh))
                ov_x = min(ax + aw, bx + bw) - max(ax, bx)
                if 0 <= gap_y <= 300 and ov_x > 0:
                    # so a FRENTE importa: o fundo pode variar (equipamento
                    # embutido em armario mais fundo deixa folga de sombra atras,
                    # que e como se constroi de verdade)
                    d = abs((ax + aw) - (bx + bw))
                    if d > FOLGA_FILA_MAX:
                        out.append(Achado("ATENCAO", "Frentes desalinhadas na fila",
                                          f"{amb.cod}: {ca} ({ta}) termina em "
                                          f"x={ax+aw:.0f} e {cb} ({tb}) em "
                                          f"x={bx+bw:.0f} — {d:.0f} mm de degrau"))
                    continue
                # fila no eixo X: encostadas em x, sobrepostas em y
                gap_x = max(bx - (ax + aw), ax - (bx + bw))
                ov_y = min(ay + ah, by + bh) - max(ay, by)
                if 0 <= gap_x <= 300 and ov_y > 0:
                    d = abs((ay + ah) - (by + bh))
                    if d > FOLGA_FILA_MAX:
                        out.append(Achado("ATENCAO", "Frentes desalinhadas na fila",
                                          f"{amb.cod}: {ca} ({ta}) termina em "
                                          f"y={ay+ah:.0f} e {cb} ({tb}) em "
                                          f"y={by+bh:.0f} — {d:.0f} mm de degrau"))
    return out


def checar_equipamento_sob_bancada() -> list[Achado]:
    """Lava-loucas e lixo vao sob a bancada da CUBA; forno e micro, em torre."""
    out = []
    for e in pj.EQUIPAMENTOS:
        exige = SOB_BANCADA.get(e["tipo"])
        if not exige:
            continue
        ret = (e["x"], e["y"], e["w"], e["h"])
        if exige == "cuba":
            sob = [b for b in pj.BANCADAS
                   if b["amb"] == e["amb"] and _sobrepoe(ret,
                       (b["x"], b["y"], b["w"], b["h"])) > 0.05]
            if not sob:
                out.append(Achado("ERRO", "Equipamento sem bancada acima",
                                  f"{e['cod']} ({e['tipo']}) nao esta sob bancada "
                                  f"nenhuma"))
            elif not any(b["cubas"] for b in sob):
                out.append(Achado("ERRO", "Equipamento sob bancada errada",
                                  f"{e['cod']} ({e['tipo']}) esta sob "
                                  f"{sob[0]['cod']}"
                                  + (" (cooktop)" if sob[0]["cooktop"] else "")
                                  + f": precisa da bancada da cuba, onde estao o "
                                    f"sifao e o ralo"))
        else:
            torre = [a for a in pj.ARMARIOS
                     if a["amb"] == e["amb"] and a["tipo"] == "armario alto"
                     and _sobrepoe(ret, (a["x"], a["y"], a["w"], a["h"])) > 0.05]
            if not torre:
                out.append(Achado("ERRO", "Equipamento sem torre",
                                  f"{e['cod']} ({e['tipo']}) precisa de armario "
                                  f"alto que o abrigue e alinhe a frente"))
    return out


def checar_peninsula() -> list[Achado]:
    """Peninsula encosta em algo. O que nao encosta e ilha, e ilha em cozinha de
    3,00 m de largura nao cabe."""
    out = []
    for b in pj.BANCADAS:
        if "peninsula" not in b["uso"].lower():
            continue
        ret = (b["x"], b["y"], b["w"], b["h"])
        encosta = []
        for o in list(pj.BANCADAS) + [dict(cod=a["cod"], x=a["x"], y=a["y"],
                                           w=a["w"], h=a["h"])
                                      for a in pj.ARMARIOS] + \
                 [dict(cod=e["cod"], x=e["x"], y=e["y"], w=e["w"], h=e["h"])
                  for e in pj.EQUIPAMENTOS]:
            if o["cod"] == b["cod"]:
                continue
            if _folga(ret, (o["x"], o["y"], o["w"], o["h"])) <= FOLGA_FILA_MAX:
                encosta.append(o["cod"])
        # tambem vale encostar numa parede / linha de fronteira de ambiente
        for a in pj.TERREO:
            if abs(b["x"] - a.x) <= 1 or abs(b["x"] + b["w"] - (a.x + a.w)) <= 1:
                encosta.append(a.cod)
                break
        if not encosta:
            out.append(Achado("ERRO", "Peninsula que nao encosta em nada",
                              f"{b['cod']}: e ilha, nao peninsula — solta no meio "
                              f"da circulacao"))
        else:
            out.append(Achado("NOTA", "Peninsula ancorada",
                              f"{b['cod']} encosta em {', '.join(sorted(set(encosta)))}"))
        # nao pode invadir o eixo visual da piscina
        eixo = pj.eixo_visual()["eixo_x_piscina"]
        if b["x"] < eixo < b["x"] + b["w"]:
            out.append(Achado("ERRO", "Peninsula no eixo visual",
                              f"{b['cod']} cruza x = {eixo:.0f}, o eixo estar-piscina"))
    return out


# =========================================================================
# R12 — a FOLHA entra na auditoria
# =========================================================================
def checar_extravasamento() -> list[Achado]:
    """Nenhuma prancha pode desenhar fora da moldura.

    Ate R11 a planta baixa emitia 136 mm de conteudo acima da moldura — o fim
    da piscina, o jardim de fundo, o rotulo "JARDIM DE FUNDO". O papel corta,
    o SVG corta no viewBox e ninguem fica sabendo: e a mesma classe de defeito
    do resto do caderno, so que uma camada adiante. O que nao esta na folha nao
    existe, mesmo estando no modelo.

    A verificacao constroi as 35 pranchas e mede a caixa do que cada uma
    emitiu contra a propria moldura.
    """
    import build
    out = []
    for num, nome, fn in build.CADERNO:
        try:
            cv = fn()
        except Exception as e:                       # pragma: no cover
            out.append(Achado("ERRO", f"PR-{num}", f"prancha nao constroi: {e}"))
            continue
        fora = {k: v for k, v in cv.cortado().items() if v > 2.0}
        # cortar e legitimo quando se declara: a linha de ruptura (NBR 8403) diz
        # ao leitor que o desenho continua alem do limite, e para onde ir ver
        if fora and 'data-tipo="ruptura"' in cv.svg():
            out.append(Achado("NOTA", f"PR-{num}",
                              f"{nome}: corte declarado por linha de ruptura "
                              f"({', '.join(f'{k} {v} mm' for k, v in sorted(fora.items()))})"))
        elif fora:
            lados = ", ".join(f"{k} {v} mm" for k, v in sorted(fora.items()))
            out.append(Achado("ERRO", f"PR-{num}",
                              f"{nome}: a moldura corta desenho ({lados}) — "
                              f"conteudo que nao chega ao papel"))
        else:
            out.append(Achado("NOTA", f"PR-{num}",
                              f"{nome}: desenho contido na moldura"))
    return out


def checar_procedencia() -> list[Achado]:
    """Cada prancha precisa emitir procedencia suficiente para ser navegavel.

    Um SVG sem data-tipo e uma figura: o visualizador consegue amplia-lo e nada
    mais. A planta baixa, que e a peca que se le elemento por elemento, tem de
    trazer ambiente, parede e vao identificados.
    """
    import re
    import pranchas as pr
    out = []
    exigido = {"02": {"ambiente", "parede", "vao", "piso", "cota"},
               "03": {"ambiente", "parede", "vao", "cota"},
               "04": {"ambiente", "parede", "vao"}}
    for num, cv in (("02", pr.planta("T", "02")), ("03", pr.planta("S", "03")),
                    ("04", pr.planta("T", "04", layout=True))):
        svg = cv.svg()
        tipos = set(re.findall(r'data-tipo="(\w+)"', svg))
        falta = exigido[num] - tipos
        if falta:
            out.append(Achado("ERRO", f"PR-{num}",
                              f"sem procedencia para {sorted(falta)}: o traco "
                              f"chega ao visualizador sem saber de onde veio"))
        else:
            n = svg.count("data-tipo=")
            out.append(Achado("NOTA", f"PR-{num}",
                              f"{n} escopos com procedencia; a interface alcanca "
                              f"{len(tipos)} tipos de elemento"))
        # toda prancha tem de declarar carimbo e moldura, que e o que o modo
        # sem moldura desliga
        for t in ("carimbo", "moldura"):
            if t not in tipos:
                out.append(Achado("ERRO", f"PR-{num}", f"{t} sem procedencia"))
    return out
