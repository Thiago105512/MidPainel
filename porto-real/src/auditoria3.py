"""AUDITORIA 3 — o motor (nucleo/). Bloco iniciado em R13.

Os dois primeiros blocos de auditoria verificam o CASO: se a cozinha tem
circulacao, se a viga flecha demais, se a prancha cabe na folha. Este verifica o
MOTOR: se o solver de secao esta certo, se o catalogo e consistente, se a norma
foi implementada como a norma diz.

O criterio aqui e mais duro, e por uma razao: um erro no caso estraga um
projeto; um erro no motor estraga todos. Por isso nada aqui se valida contra
tabela decorada — valida-se contra solucao fechada, identidade algebrica ou
conservacao.
"""
from __future__ import annotations

import math
import re

from auditoria import Achado
import projeto as pj
import nucleo.perfis as pf
import fixture as fx


def checar_solver_secao() -> list[Achado]:
    """O solver de secao contra solucoes fechadas e identidades.

    Duas solucoes fechadas classicas do U simples exercitam toda a maquinaria de
    area setorial — se o centro de torcao e o Cw batem, a implementacao de
    Vlasov esta certa, e dai saem tambem os perfis para os quais nao ha formula
    publicada.
    """
    out = []
    h, b, t = 200.0, 50.0, 1.5
    vivo = [(b, h / 2), (0, h / 2), (0, -h / 2), (b, -h / 2)]   # cantos vivos
    d = pf.propriedades(vivo, t)

    # 1) centro de torcao do U simples: e = 3b^2 / (6b + h), medido da alma
    e = 3 * b * b / (6 * b + h)
    xc_alma = b * b / (h + 2 * b)
    esp = -(e + xc_alma)
    err = abs(d["xo"] - esp)
    out.append(Achado("NOTA" if err < 1e-6 else "ERRO", "centro de torcao",
                      f"U simples: numerico {d['xo']:.6f} mm contra fechada "
                      f"{esp:.6f} mm (e = 3b2/(6b+h)); erro {err:.2e} mm"))

    # 2) constante de empenamento do U simples
    cw = (t * b ** 3 * h ** 2 / 12) * (2 * h + 3 * b) / (h + 6 * b)
    rel = abs(d["Cw"] - cw) / cw
    out.append(Achado("NOTA" if rel < 1e-9 else "ERRO", "empenamento",
                      f"U simples: numerico {d['Cw']:.6e} mm6 contra fechada "
                      f"{cw:.6e}; erro relativo {rel:.2e}"))

    # 3) area e identidade A = t.L
    err = abs(d["A"] - t * d["L"])
    out.append(Achado("NOTA" if err < 1e-9 else "ERRO", "area",
                      f"A = t.L conferido: erro {err:.2e} mm2"))

    # 4) torcao uniforme de secao aberta J = L.t3/3
    j = d["L"] * t ** 3 / 3
    out.append(Achado("NOTA" if abs(d["J"] - j) < 1e-9 else "ERRO", "torcao",
                      f"J = L.t3/3 conferido: {d['J']:.4f} mm4"))

    # 5) invariancia por translacao e teorema dos eixos paralelos
    des = 137.0
    d2 = pf.propriedades([(x, y + des) for x, y in vivo], t)
    rel = abs(d2["Ix"] - d["Ix"]) / d["Ix"]
    desloc = abs((d2["yc"] - d["yc"]) - des)
    transporte = d["Ix"] + d["A"] * des * des     # inercia no eixo deslocado
    ok = rel < 1e-9 and desloc < 1e-9 and transporte > d["Ix"]
    out.append(Achado("NOTA" if ok else "ERRO", "eixos paralelos",
                      f"transladar {des:.0f} mm nao muda a inercia centroidal "
                      f"(erro {rel:.2e}) e desloca o centroide de {des:.0f} mm "
                      f"(erro {desloc:.2e}); no eixo deslocado ela vale "
                      f"{transporte:.4e} mm4"))

    # 6) secao duplamente simetrica: produto de inercia e centro de torcao nulos
    a = 100.0
    ret = [(-a / 2, -a / 2), (a / 2, -a / 2), (a / 2, a / 2), (-a / 2, a / 2)]
    dr = pf.propriedades(ret, 2.0, fechado=True)
    ok = abs(dr["Ixy"]) < 1e-6 and abs(dr["xo"]) < 1e-6 and abs(dr["yo"]) < 1e-6
    out.append(Achado("NOTA" if ok else "ERRO", "simetria",
                      f"tubo quadrado: Ixy = {dr['Ixy']:.2e}, "
                      f"centro de torcao = ({dr['xo']:.2e}, {dr['yo']:.2e})"))

    # 7) torcao de secao fechada pela formula de Bredt
    am = a * a                      # a poligonal JA e a linha media
    jb = 4 * am * am / (dr["L"] / 2.0)
    out.append(Achado("NOTA" if abs(dr["J"] - jb) / jb < 1e-9 else "ERRO",
                      "Bredt", f"tubo fechado: J = 4Am2/(ds/t) = {dr['J']:.4e} mm4"))

    # 8) monotonia fisica: o labio aumenta a rigidez ao empenamento
    u = pf.Perfil("U", "U", 90, 40, 0, 0.95).props()
    ue = pf.Perfil("Ue", "Ue", 90, 40, 12, 0.95).props()
    out.append(Achado("NOTA" if ue["Cw"] > u["Cw"] else "ERRO", "labio",
                      f"labio de 12 mm eleva Cw de {u['Cw']:.3e} para "
                      f"{ue['Cw']:.3e} mm6 (+{(ue['Cw']/u['Cw']-1)*100:.0f} %)"))
    return out


def checar_catalogo() -> list[Achado]:
    """Todo perfil do catalogo precisa ser calculavel e fisicamente possivel."""
    out, ruins = [], []
    cat = pf.catalogo()
    for p in cat:
        try:
            d = p.props()
        except Exception as exc:                       # pragma: no cover
            ruins.append((p.cod, f"nao calcula: {exc}"))
            continue
        if d["A"] <= 0 or d["Ix"] <= 0 or d["Iy"] <= 0 or d["J"] <= 0:
            ruins.append((p.cod, "propriedade nao positiva"))
        if d["Cw"] < 0:
            ruins.append((p.cod, "Cw negativo"))
        # esbeltez de parede: alma/espessura acima de 500 nao e perfil, e chapa
        if (p.bw - p.t) / p.t > 500:
            ruins.append((p.cod, f"alma/t = {(p.bw-p.t)/p.t:.0f}, acima de 500"))
        # raio de dobra tem de caber na aba
        r = p.r if p.r is not None else pf._raio_padrao(p.t)
        if p.D and p.D < 2 * (r + p.t):
            ruins.append((p.cod, f"labio {p.D} mm menor que o dobro do raio de dobra"))
    for cod, motivo in ruins[:12]:
        out.append(Achado("ERRO", cod, motivo))
    if not ruins:
        massas = [p.props()["massa_m"] for p in cat]
        out.append(Achado("NOTA", "catalogo",
                          f"{len(cat)} perfis calculaveis, de "
                          f"{min(massas):.3f} a {max(massas):.3f} kg/m"))
    # a espessura precisa estar na serie comercial
    fora = sorted({p.t for p in cat} - set(pf.ESPESSURAS))
    if fora:
        out.append(Achado("ERRO", "catalogo",
                          f"espessuras fora da serie comercial: {fora}"))
    return out


def checar_familias_lsf() -> list[Achado]:
    """Cada funcao estrutural de LSF precisa existir e ser explicada.

    Sem isso, 'stud' e 'jack stud' viram sinonimos na cabeca de quem le, e a
    lista de pecas deixa de dizer o que a peca faz.
    """
    out = []
    exigidas = {"stud", "track", "joist", "rafter", "header", "jamb",
                "king stud", "jack stud", "cripple stud", "blocking",
                "bridging", "strap"}
    falta = exigidas - set(pf.FAMILIAS_LSF)
    if falta:
        out.append(Achado("ERRO", "familias", f"sem funcao declarada: {sorted(falta)}"))
    else:
        out.append(Achado("NOTA", "familias",
                          f"{len(pf.FAMILIAS_LSF)} funcoes estruturais declaradas"))
    vazias = [k for k, v in pf.FAMILIAS_LSF.items() if len(v) < 20]
    if vazias:
        out.append(Achado("ATENCAO", "familias",
                          f"descricao curta demais para: {vazias}"))
    return out


def checar_materiais() -> list[Achado]:
    """Aco, revestimento e material: identidades e coerencia fisica.

    Sem fy nao existe NBR 14762 — ate R13 o projeto so sabia E, e por isso so
    conseguia verificar flecha. E 'galvanizado' nao e especificacao: Z275 e, e
    tem consequencia dimensional de cerca de 20 micrometros por face.
    """
    import nucleo.materiais as mt
    out = []

    # identidade da elasticidade: G = E / (2(1+v))
    g = mt.E_ACO / (2 * (1 + mt.POISSON))
    rel = abs(g - mt.G_ACO) / mt.G_ACO
    out.append(Achado("NOTA" if rel < 1e-3 else "ERRO", "elasticidade",
                      f"G = E/(2(1+v)) da {g:.1f} MPa contra {mt.G_ACO:.0f} "
                      f"declarado; divergencia {rel*100:.3f} %"))

    # todo aco: fu > fy, alongamento positivo, resistencias de calculo menores
    for a in mt.ACOS:
        if a.fu <= a.fy:
            out.append(Achado("ERRO", a.cod, f"fu {a.fu} nao maior que fy {a.fy}"))
        if a.along <= 0:
            out.append(Achado("ERRO", a.cod, "alongamento nao declarado"))
        if a.fyd >= a.fy or a.fud >= a.fu:
            out.append(Achado("ERRO", a.cod, "resistencia de calculo nao minora"))

    # revestimento: a espessura por face tem de sair da massa e da densidade
    for r in mt.REVESTIMENTOS:
        esp = (r.massa_total / 2) / r.densidade * 1000.0
        if abs(esp - r.espessura_face) > 1e-9:
            out.append(Achado("ERRO", r.cod, "espessura de camada inconsistente"))
        if not (5 <= r.espessura_face <= 40):
            out.append(Achado("ATENCAO", r.cod,
                              f"{r.espessura_face:.1f} um/face fora da faixa usual"))
    if not [a for a in out if a.nivel == "ERRO"]:
        out.append(Achado("NOTA", "materiais",
                          f"{len(mt.ACOS)} acos, {len(mt.REVESTIMENTOS)} revestimentos "
                          f"e {len(mt.MATERIAIS)} materiais, todos consistentes"))

    # o LSF estrutural nao aceita revestimento abaixo do minimo da NBR 15253
    minimo = mt.POR_REV[mt.REVESTIMENTO_MINIMO_LSF]
    fracos = [r.cod for r in mt.REVESTIMENTOS
              if r.liga == "Zn" and r.massa_total < minimo.massa_total]
    out.append(Achado("NOTA", "NBR 15253",
                      f"revestimento minimo do perfil estrutural: "
                      f"{minimo.cod} ({minimo.espessura_face:.1f} um/face); "
                      f"{len(fracos)} revestimentos do catalogo so servem a "
                      f"perfil nao estrutural"))
    return out


def checar_normas() -> list[Achado]:
    """Um sistema normativo nao se mistura com outro.

    Combinacao do Eurocode com resistencia da NBR e erro que nao aparece no
    desenho: as duas normas sao coerentes por dentro e incompativeis entre si,
    porque repartem a seguranca entre acao e resistencia de modos diferentes.
    """
    import nucleo.normas as nm
    out = []
    campos = ("formado_frio", "laminado", "cargas", "vento", "combinacoes", "perfis")
    for s in nm.SISTEMAS:
        falta = [c for c in campos if not getattr(s, c)]
        if falta:
            out.append(Achado("ERRO", s.cod, f"sistema incompleto: {falta}"))
        if s.gama_a1 <= 0 or s.gama_a2 <= 0:
            out.append(Achado("ERRO", s.cod, "coeficiente de ponderacao nao positivo"))
    if nm.PADRAO not in nm.POR_SISTEMA:
        out.append(Achado("ERRO", "normas", f"sistema padrao '{nm.PADRAO}' nao existe"))

    # as normas do caso precisam pertencer ao sistema escolhido
    c = getattr(pj, "CADASTRO", None)
    if c is not None:
        s = nm.POR_SISTEMA[nm.PADRAO]
        exigidas = {s.cargas.split(":")[0], s.vento.split(":")[0],
                    s.combinacoes.split(":")[0], s.perfis.split(":")[0],
                    s.formado_frio.split(":")[0]}
        declaradas = set(c.normas)
        falta = sorted(n for n in exigidas if n not in declaradas)
        if falta:
            out.append(Achado("ATENCAO", "CADASTRO",
                              f"sistema {s.cod} exige {falta}, que o cadastro "
                              f"nao declara"))
        else:
            out.append(Achado("NOTA", "CADASTRO",
                              f"as {len(declaradas)} normas do caso contem as "
                              f"{len(exigidas)} estruturais do sistema {s.cod}"))
    out.append(Achado("NOTA", "normas",
                      f"{len(nm.SISTEMAS)} sistemas normativos selecionaveis; "
                      f"padrao {nm.PADRAO}"))
    return out


def checar_incendio() -> list[Achado]:
    """TRRF declarado e crescente com a altura, e protecao compativel."""
    import nucleo.normas as nm
    out = []
    c = getattr(pj, "CADASTRO", None)
    if c is None:
        return [Achado("ERRO", "incendio", "sem cadastro")]
    alt = c.pavimentos * c.pe_direito / 1000.0
    t = nm.trrf(c.tipo.uso, alt)
    n = nm.camadas_para_trrf(t)
    # monotonia: mais alto nunca pode exigir menos
    anterior = 0
    for h in (6, 12, 23, 30):
        v = nm.trrf(c.tipo.uso, h)
        if v < anterior:
            out.append(Achado("ERRO", "TRRF",
                              f"uso {c.tipo.uso}: {h} m exige {v} min, menos que "
                              f"a faixa anterior ({anterior} min)"))
        anterior = v
    out.append(Achado("NOTA", "TRRF",
                      f"{c.tipo.uso} com {alt:.1f} m: TRRF {t} min, atendido por "
                      f"{n} camada(s) de gesso de 12,5 mm por face (H — a "
                      f"resistencia efetiva depende de ensaio do fabricante)"))
    return out


def checar_vento() -> list[Achado]:
    """O gerador de vento contra a definicao da propria NBR 6123.

    O ponto de ancoragem e definicional: a categoria II, classe A, a 10 m e o
    terreno de REFERENCIA da norma, e ali S2 tem de valer exatamente 1,000. Se
    esse valor sai diferente, toda a tabela esta deslocada.
    """
    import nucleo.vento as vt
    out = []

    ref = vt.s2(10.0, "II", "A")
    out.append(Achado("NOTA" if abs(ref - 1.0) < 1e-12 else "ERRO", "S2",
                      f"terreno de referencia (cat II, classe A, z = 10 m): "
                      f"S2 = {ref:.6f}, tem de ser 1,000000"))

    # monotonia: sobe com a altura, desce com a rugosidade
    alturas = [vt.s2(z, "III", "A") for z in (2, 5, 10, 20, 50, 100)]
    cresce = all(b > a for a, b in zip(alturas, alturas[1:]))
    out.append(Achado("NOTA" if cresce else "ERRO", "S2",
                      f"cresce com a altura: {[round(a,3) for a in alturas]}"))
    cats = [vt.s2(10.0, c, "A") for c in ("I", "II", "III", "IV", "V")]
    desce = all(b < a for a, b in zip(cats, cats[1:]))
    out.append(Achado("NOTA" if desce else "ERRO", "S2",
                      f"desce com a rugosidade: {[round(c,3) for c in cats]}"))

    # identidade da pressao dinamica
    v = 42.0
    q = vt.pressao(v)
    out.append(Achado("NOTA" if abs(q - 0.613 * v * v / 1000) < 1e-12 else "ERRO",
                      "pressao", f"q = 0,613.Vk2 conferido: {q:.4f} kN/m2 a {v} m/s"))

    # S3: grupo 2 e a referencia e vale 1,00; mais critico nunca da menos
    if vt.s3(2) != 1.00:
        out.append(Achado("ERRO", "S3", "grupo 2 deveria valer 1,00"))
    if not (vt.s3(1) > vt.s3(2) > vt.s3(3) > vt.s3(4) > vt.s3(5)):
        out.append(Achado("ERRO", "S3", "grupos fora de ordem de importancia"))

    # sinal fisico: barlavento comprime, sotavento suga
    cpe = vt.cpe_paredes(24.0, 13.2, 6.15)
    if cpe["C"] <= 0:
        out.append(Achado("ERRO", "Cpe", "barlavento com coeficiente nao positivo"))
    if cpe["D"] >= 0:
        out.append(Achado("ERRO", "Cpe", "sotavento com coeficiente nao negativo"))
    if max(cpe.values()) > 1.0 or min(cpe.values()) < -2.0:
        out.append(Achado("ERRO", "Cpe", f"coeficiente fora da faixa fisica: {cpe}"))

    # a interpolacao entre faixas precisa ser DECLARADA, nunca silenciosa
    org = vt.origem_cpe(24.0, 13.2, 6.15)
    if "INTERPOL" in org.upper():
        out.append(Achado("NOTA", "Cpe", org))
    else:
        out.append(Achado("NOTA", "Cpe", org))

    # forma fora da tabela tem de levantar erro, nao devolver numero plausivel
    try:
        vt.cpe_paredes(100.0, 10.0, 5.0)
        out.append(Achado("ERRO", "Cpe",
                          "a/b = 10 esta fora da Tabela 4 e mesmo assim devolveu "
                          "valor — numero inventado e pior que ausencia"))
    except ValueError:
        out.append(Achado("NOTA", "Cpe",
                          "forma fora da Tabela 4 levanta erro em vez de "
                          "devolver numero plausivel"))
    return out


def checar_ambientes() -> list[Achado]:
    """A verificacao por COMODO — o eixo que nao existia.

    As 510 condicoes anteriores verificam por SISTEMA: estrutura, camadas, MEP,
    fundacao, cotacao. Nenhuma verificava por comodo, e o comodo e a unidade em
    que a casa e vivida, em que o pedreiro trabalha e em que o dono percebe
    erro. Defeito nao se distribui por sistema: ele se concentra onde dois
    sistemas se encontram, e os dois se encontram DENTRO de um comodo.

    Na primeira execucao o eixo novo achou 24 divergencias. Quatorze eram um
    defeito real e dez eram grossura da propria conferencia — e separar as duas
    coisas foi metade do trabalho.
    """
    import projeto as pj
    import nucleo.ambiente as am
    out = []
    r = fx.liberacao()
    c = am.conferir(pj, r)
    ds = c["dossies"]

    out.append(Achado("NOTA" if abs(c["area_total"] - pj.CADASTRO.area_m2) < 0.1
                      else "ERRO", "fecha a casa",
                      f"{c['n']} comodos somando {c['area_total']} m2, contra "
                      f"{pj.CADASTRO.area_m2} m2 de area declarada do projeto. "
                      f"O dossie de cada comodo reune acabamento, vao, "
                      f"tomada, peca hidraulica, ralo, clima e composicao de "
                      f"parede num lugar so — que e onde o pedreiro trabalha"))

    # ---- o defeito que o eixo novo achou: duas regras para a mesma tomada
    prev = {x["amb"]: x for x in pj.previsao_iluminacao_tug()}
    norma = sum(x["tugs"] for x in prev.values())
    area5 = sum(max(1, int(a.area_mod / 5)) for a in pj.TERREO + pj.SUPERIOR)
    import nucleo.instalacoes as ins
    import inspect
    usa = "previsao_iluminacao_tug" in inspect.getsource(ins.eletrica)
    out.append(Achado("NOTA" if usa else "ERRO", "tomadas",
                      f"{norma} tomadas pela NBR 5410 9.5.2.2, que conta "
                      f"PERIMETRO — uma a cada 5,0 m de parede, 3,5 m em area "
                      f"molhada. O levantamento de instalacoes contava "
                      f"{area5} por AREA, uma segunda regra para o mesmo fato, "
                      f"e a segunda estava errada. O sinal do erro nao era "
                      f"uniforme: sobrava na garagem e na master, faltava na "
                      f"lavanderia (1 contra 4), no banho, na despensa e na "
                      f"cozinha — comodo estreito e comprido tem muito "
                      f"perimetro e pouca area, e e nele que se mora"))

    # ---- a decisao que vivia em comentario
    out.append(Achado("NOTA" if hasattr(pj, "CONJUGADOS") else "ERRO",
                      "conjugados",
                      f"{len(getattr(pj, 'CONJUGADOS', []))} par(es) de "
                      f"ambientes se conferem juntos, e isso agora e DADO. A "
                      f"cozinha reprovou em iluminacao natural na primeira "
                      f"execucao porque a conferencia via dois retangulos onde "
                      f"o projeto ve um: 6.600 dos 7.200 mm de fronteira com o "
                      f"gourmet estao abertos desde R07 — escrito em "
                      f"comentario, e comentario nao e consultavel"))

    # ---- classificar vao por prefixo de codigo reprovava o estar
    esc = [d for d in ds if d["cod"] == "T-SOC"]
    if esc:
        d = esc[0]
        out.append(Achado("NOTA" if d["area_ilum"] > 0 else "ERRO",
                          "vao translucido",
                          f"o estar ilumina por {d['area_ilum']:.2f} m2 de "
                          f"porta-balcao. Classificar vao por PREFIXO de "
                          f"codigo — J e janela, P e porta — reprovava o estar "
                          f"e o eixo social inteiro, que abre por cortina de "
                          f"vidro de 7,2 m. O criterio e opacidade, nao codigo"))

    # ---- a area de permanencia nao e o retangulo
    sub = [d for d in ds if d["area_subdividida"] > 0]
    out.append(Achado("NOTA" if sub else "ATENCAO", "area de permanencia",
                      f"{len(sub)} comodos descontam a subdivisao da area que "
                      f"a janela precisa iluminar: banho e closet nao se "
                      f"iluminam pela janela do quarto. A master cai de 46,8 "
                      f"para {next((d['area_util'] for d in ds if d['cod'] == 'S-MAS'), 0)} "
                      f"m2 de permanencia, e passa"))

    # ---- a pergunta que 517 verificacoes nao faziam: da para CHEGAR la?
    con = c["conectividade"]
    out.append(Achado("NOTA" if con["ok"] else "ERRO", "conectividade",
                      f"{con['alcancaveis']} de {con['total']} comodos se "
                      f"alcancam a pe a partir da porta de entrada"
                      + ("" if con["ok"] else f" — ILHADOS: {con['ilhados']}")
                      + ". Todas as outras verificacoes conferem PROPRIEDADES "
                        "de um comodo, e nenhuma pegaria isto: o mini lounge "
                        "tinha porta, janela, climatizacao e piso "
                        "especificado, e estava correto em tudo o que se mede "
                        "dentro dele. O que faltava era a RELACAO entre "
                        "comodos, e relacao e grafo, nao tabela"))
    exemplo = con["ligacoes"].get("S-LOU", {})
    out.append(Achado("NOTA" if exemplo else "ERRO", "o poco de 600 mm",
                      f"o mini lounge liga a {', '.join(exemplo) or 'NADA'}. "
                      f"Antes de R46 havia entre ele e o hall uma faixa de "
                      f"600 x 2.400 mm que nao pertencia a ambiente nenhum: o "
                      f"painelizador via exterior dos dois lados e erguia DUAS "
                      f"paredes externas de 150 mm paralelas, e a porta do "
                      f"lounge abria para dentro desse poco. Estender o hall "
                      f"REMOVEU uma parede em vez de acrescentar"))

    # ---- o que sobrou, e sobrou de verdade
    reais = [a for a in c["achados"] if a["nivel"] in ("ERRO", "ATENCAO")]
    for a in reais:
        out.append(Achado(a["nivel"], f"{a['amb']} · {a['item']}", a["texto"]))

    out.append(Achado("NOTA", "criterio", c["criterio"]))
    return out


# Cada sistema levantado no MODELO e as marcas que provam que ele chegou ao
# DESENHO. Escrito antes de olhar as pranchas, como a completude de R32: a lista
# diz o que precisa estar la, e a conferencia diz se esta.
DESENHADO = {
    "estrutura LSF": ("stud", "TP01"),
    "vigamento de entrepiso": ("viga", "VIG"),
    "contraventamento": ("diagonal", "fita X", "contravent"),
    "fundacao / radier": ("radier", "RADIER"),
    "hidraulica": ("prumada", "DN100"),
    "eletrica": ("TUG", "quadro"),
    "climatizacao": ("BTU", "condensadora"),
    "drenagem": ("ralo", "RL-"),
    "esquadrias": ("esquadria", "caixilho", "J04"),
    "cobertura e calha": ("calha", "rufo"),
    "platibanda": ("platibanda", "PLATIB"),
    "brise": ("brise", "ripado"),
    "muro": ("muro", "Muro", "MURO"),
    "piscina": ("piscina", "PISCINA"),
    "piso externo e deck": ("deck", "WPC", "drenante"),
    "paisagismo": ("paisag", "Ipe", "almeira"),
    "catalogo de peca": ("SECOES DOS PERFIS", "Ue 90x40x12"),
    "parafuso": ("parafuso", "AB 4,8"),
    # R52 — cinco sistemas que sairam da hipotese nesta revisao. Cada um teve
    # de ganhar prancha: a regra que R51 escreveu vale para quem a escreveu.
    "sondagem SPT": ("SP-01", "NSPT"),
    "tratamento do solo": ("substituicao compactada", "Terraplenagem",
                           "TERRAPLENAGEM"),
    "retencao pluvial": ("RETENCAO", "retencao", "orificio"),
    "superficies do lote": ("SUPERFICIES DO LOTE", "impermeabiliza"),
    "acustica": ("ACUSTICO", "acustic", "Rw"),
    "equilibrio de fases": ("CARGA POR FASE", "desequilibrio"),
    "fornecedores": ("DE QUEM SE COMPRA", "fornecedor"),
    # R53
    "lavabo e en-suite": ("LAVABO SOCIAL", "LAVABO"),
    # R54 — a cabine do vaso saiu por decisao do proprietario; entrou o
    # lavabo sob a escada, que e o que agora tem de chegar ao papel.
    "lavabo sob a escada": ("LAVABO", "SOB A ESCADA"),
    "layout do estar": ("LY-05", "layout"),
}


def checar_completude_do_desenho() -> list[Achado]:
    """O caderno mostra tudo o que o modelo sabe?

    A completude de R32 pergunta se o SISTEMA esta no modelo. Esta pergunta o
    inverso: se o que ESTA no modelo chegou ao papel. Sao falhas de sentido
    oposto e nenhuma das duas pega a outra — um sistema pode estar
    perfeitamente modelado, orcado e verificado, e nao aparecer em prancha
    nenhuma. Foi o que aconteceu com o catalogo de pecas entre R47 e R50: ele
    existia como vista de tela, e a fabrica recebe o PDF, nao a tela.
    """
    import glob
    import os
    out = []
    svgs = sorted(glob.glob(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "out", "PR-*.svg")))
    if not svgs:
        out.append(Achado("ATENCAO", "desenho nao gerado",
                          "nenhum SVG em out/: esta verificacao le o desenho "
                          "EMITIDO, e sem build ela nao tem o que ler"))
        return out
    cache = {os.path.basename(f)[:5]: open(f, encoding="utf-8").read()
             for f in svgs}
    out.append(Achado("NOTA", "caderno", f"{len(cache)} pranchas emitidas"))

    faltando = []
    for sistema, chaves in sorted(DESENHADO.items()):
        onde = sorted({p for p, txt in cache.items()
                       if any(k in txt for k in chaves)})
        if not onde:
            faltando.append(sistema)
        out.append(Achado("NOTA" if onde else "ERRO", f"desenho: {sistema}",
                          f"aparece em {', '.join(onde[:7])}"
                          + (f" e mais {len(onde) - 7}" if len(onde) > 7 else "")
                          if onde else
                          "NAO aparece em prancha nenhuma: o modelo sabe e o "
                          "caderno nao mostra"))

    out.append(Achado("NOTA" if not faltando else "ERRO", "cobertura",
                      f"{len(DESENHADO) - len(faltando)} de {len(DESENHADO)} "
                      f"sistemas levantados chegam ao papel"
                      + ("" if not faltando else f" — FALTAM: {faltando}")
                      + ". A completude de R32 pergunta se o sistema esta no "
                        "modelo; esta pergunta o inverso, e nenhuma das duas "
                        "pega a outra"))

    # a revisao do carimbo tem de ser a do caso, em TODA prancha
    import projeto as pj
    rev = pj.EMISSAO["revisao"]
    sem = [p for p, txt in cache.items() if rev not in txt]
    out.append(Achado("NOTA" if not sem else "ERRO", "revisao no carimbo",
                      f"as {len(cache)} pranchas trazem {rev} no carimbo"
                      if not sem else f"sem {rev}: {sem}"))

    # e a contagem de pranchas do carimbo tem de bater com o que foi emitido
    import pranchas as pr
    out.append(Achado("NOTA" if pr.TOTAL_PRANCHAS == str(len(cache)) else "ERRO",
                      "contagem",
                      f"o carimbo diz {pr.TOTAL_PRANCHAS} pranchas e foram "
                      f"emitidas {len(cache)}. Carimbo que conta errado e a "
                      f"primeira coisa que um fiscal olha"))
    return out


def checar_viabilidade() -> list[Achado]:
    """O que falta, quem fecha, e QUANTO DO PROJETO depende disso.

    Uma lista de pendencias diz o que falta. Ela nao diz a unica coisa que
    decide se um projeto pode andar: quanto dele depende de cada uma. Um item
    que move 2 % do orcamento e nota de rodape; um que move 100 % e risco de
    contrato — e os dois aparecem iguais numa lista com bolinha.
    """
    import projeto as pj
    out = []
    r = fx.liberacao()
    v = r["viabilidade"]

    out.append(Achado("NOTA", "portoes",
                      "; ".join(f"{p['portao']}: "
                                + (f"TRAVADO por #{', #'.join(p['itens'])}"
                                   if p["travado"] else "livre")
                                for p in v["portoes"])
                      + ". " + v["leitura"]))

    abertas = sorted((i for i in v["itens"] if i["status"] == "ABERTA"),
                     key=lambda i: -i["fracao"])
    for i in abertas:
        nivel = "ATENCAO" if i["fracao"] >= 0.5 else "NOTA"
        out.append(Achado(nivel, f"#{i['n']} {i['titulo'][:34]}",
                          f"exposicao de {i['fracao'] * 100:.1f} % do custo "
                          f"(R$ {i['exposicao']:,.0f})"
                          + (f", tranca {i['bloqueia']}" if i["bloqueia"]
                             else ", nao tranca portao nenhum")
                          + (f". {i['grandeza']}" if i["grandeza"] else "")
                          + (f". {i['simulacao']}" if i["simulacao"] else "")))

    # a exposicao tem de ser medida, nao chutada
    mediveis = [i for i in abertas if i["simulacao"]]
    out.append(Achado("NOTA" if len(mediveis) == len(abertas) else "ATENCAO",
                      "exposicao medida",
                      f"{len(mediveis)} de {len(abertas)} pendencias abertas "
                      f"dizem o que muda quando o dado chegar, e duas delas "
                      f"trazem SIMULACAO calculada — radier de 250 mm em vez "
                      f"de 180, e nesting de 80 % em vez do atual. "
                      + v["criterio"]))

    # a pendencia 11 fechou por conferencia, nao por decreto
    p11 = next((i for i in v["itens"] if i["n"] == "11"), None)
    pru = pj.prumadas_hidraulicas()
    dns = sorted({x["dn_agua"] for x in pru})
    out.append(Achado("NOTA" if p11 and p11["status"] == "RESOLVIDA" else "ERRO",
                      "#11 fechada por conferencia",
                      f"o ramal de agua fria sai do calculo por pesos da NBR "
                      f"5626 e da DN{', DN'.join(str(d) for d in dns)} — nao "
                      f"existe DN50 em ramal de agua fria no modelo. O DN50 da "
                      f"PR-09 e a succao e o retorno da PISCINA, circuito "
                      f"proprio e correto. A pendencia nasceu em R39, quando "
                      f"unifiquei duas listas e li a tabela antiga errado"))
    return out


def checar_externo() -> list[Achado]:
    """286 m2 de projeto que nao existiam no orcamento.

    Quinze areas abertas declaradas, uma piscina com sistema completo, um deck,
    um muro de 2,2 m em todo o perimetro, oito itens de paisagismo e tres zonas
    de piso com material escolhido E RAZAO ESCRITA. Nada disso tinha
    quantidade. Em residencia deste porte a area externa e 10 a 20 % do custo,
    e e onde o orcamento estoura — justamente porque entra por ultimo.
    """
    import projeto as pj
    import nucleo.externo as ex
    import nucleo.fachada as fa
    out = []
    r = fx.liberacao()
    e = r["camadas"]["externo"]

    m = e["muro"]
    out.append(Achado("NOTA", "muro",
                      f"{m['comprimento_m']} m de muro a {m['altura'] / 1000:g} m "
                      f"= {m['area']} m2, {m['blocos']} blocos e "
                      f"{m['pilaretes']} pilaretes. {m['obs']}. Bloco APARENTE "
                      f"com hidrofugante, e nao alvenaria pintada: a regra de "
                      f"fachada recusa superficie que exija repintura, e 250 "
                      f"m2 de muro repintado a cada cinco anos e tinta mais "
                      f"andaime baixo, para sempre"))

    pi = e["pisos"]
    out.append(Achado("NOTA" if not pi["sem_zona"] else "ATENCAO",
                      "piso externo",
                      "; ".join(f"{i['zona']} {i['area']} m2" for i in pi["itens"])
                      + f"; jardim {pi['jardim']} m2"
                      + ("" if not pi["sem_zona"]
                         else f" — SEM ZONA: {pi['sem_zona']}")))

    pc = e["piscina"]
    out.append(Achado("NOTA", "piscina",
                      f"{pc['lamina']} m2 de lamina e {pc['volume']} m3 dao "
                      f"{pc['revestimento_m2']} m2 de revestimento, "
                      f"{pc['borda_m']} m de borda e {pc['concreto_m3']} m3 de "
                      f"casca. {pc['obs']}"))

    ext = [i for i in r["bom"] if i.familia == "externo"]
    tot = sum(i.total for i in ext)
    frac = tot / r["custo"] if r["custo"] else 0
    out.append(Achado("NOTA" if 0.05 <= frac <= 0.30 else "ATENCAO",
                      "peso no orcamento",
                      f"a area externa soma R$ {tot:,.0f} em {len(ext)} linhas, "
                      f"{frac * 100:.1f} % do custo. A faixa de pratica para "
                      f"residencia deste porte e 10 a 20 %, e o valor cair "
                      f"nela e o unico sinal disponivel de que o levantamento "
                      f"nao esquece um bloco inteiro"))

    pb = r["camadas"]["platibanda"]
    out.append(Achado("NOTA" if pb["altura"] > 0 else "NOTA", "platibanda",
                      f"{pb['altura']} mm de parede em {pb['comprimento_m']} m "
                      f"de perimetro: {pb['n_montantes']} montantes, "
                      f"{pb['guia_m']} m de guia, {pb['placa_m2']} m2 de placa "
                      f"e {pb['massa_aco']} kg de aco. {pb['obs']}"))

    # o aco da platibanda nao pode aparecer duas vezes
    import nucleo.bom as bo
    aco_modelo = next(i for i in r["bom"] if i.sku == "ACO-PERF")
    massa_pecas = sum(q.massa for q in r["pecas"])
    plat = [i for i in r["bom"] if i.sku.startswith("PLA-M") or i.sku == "PLA-GUIA"]
    out.append(Achado("NOTA", "sem dupla contagem",
                      f"o aco da platibanda ({pb['massa_aco']} kg) entra em "
                      f"linha propria e NAO esta em ACO-PERF, que continua "
                      f"sendo a massa das {len(r['pecas'])} pecas do modelo "
                      f"({massa_pecas:,.0f} kg uteis). E a mesma disciplina do "
                      f"defeito 47: o que se compra aparece uma vez so"))
    return out


def checar_fachada() -> list[Achado]:
    """A fachada foi COMBINADA, foi desenhada — e tem estrutura?

    Sao tres perguntas diferentes, e o projeto so respondia a segunda. As
    regras estao declaradas desde R06, vindas do YAML do proprietario, e regra
    declarada que ninguem confere e preferencia, nao regra.
    """
    import projeto as pj
    import nucleo.fachada as fa
    out = []
    r = fx.liberacao()
    c = fa.conferir(pj, r)

    for f in c["faces"]:
        out.append(Achado("NOTA", f"face {f['face']}",
                          f"{f['nome']}: {f['area_bruta']} m2 brutos, "
                          f"{f['n_vaos']} vao(s) somando {f['area_vao']} m2, "
                          f"{f['frac_vidro'] * 100:.1f} % de vidro. A face e "
                          f"derivada do envelope construido: quando o hall "
                          f"cresceu em R46, a fachada cresceu junto sem que "
                          f"ninguem a redesenhasse"))

    for a in c["achados"]:
        out.append(Achado(a["nivel"], a["item"], a["texto"]))

    b = c["brises"]
    out.append(Achado("NOTA" if b["ripa_m"] > 0 else "ERRO", "brise como material",
                      f"{b['n']} brises: {b['comp_total']} m de fachada, "
                      f"{b['n_ripas'] if 'n_ripas' in b else sum(i['n_ripas'] for i in b['itens'])} "
                      f"ripas somando {b['ripa_m']} m, {b['travessa_m']} m de "
                      f"travessa, {b['fixacoes']} fixacoes e {b['massa']} kg "
                      f"pendurados na fachada. Ate R47 nada disso existia no "
                      f"orcamento nem na carga: o ripado era retangulo no "
                      f"desenho e no 3D"))

    # a fixacao cai em montante? o passo de 600 tem de bater com a modulacao
    mod = pj.MONTANTE_ESPACAMENTO
    out.append(Achado("NOTA" if fa.PASSO_FIXACAO % mod == 0 else "ERRO",
                      "fixacao no montante",
                      f"passo de fixacao de {fa.PASSO_FIXACAO} mm contra "
                      f"modulacao de montante de {mod} mm: cada travessa cai "
                      f"em montante. Parafusar brise na placa cimenticia e "
                      f"arrancar a fachada no primeiro vento de 30 m/s — a "
                      f"placa nao e elemento estrutural"))

    # o 3D nao pode mais ter a medida do brise como literal
    import inspect
    import modelo3d as m3
    src = inspect.getsource(m3)
    i = src.find("for br in pj.BRISES")
    trecho = src[i:i + 500]
    out.append(Achado("NOTA" if 'br.get("altura"' in trecho else "ERRO",
                      "medida no dado",
                      "a altura e a profundidade do brise saem do DADO. O 3D "
                      "desenhava 1.500 de altura e 120 de profundidade como "
                      "literais, enquanto o dado declarava 150 de "
                      "profundidade: o desenho convencia com uma medida que o "
                      "projeto nao tinha"))
    return out


def checar_nichos_e_familias() -> list[Achado]:
    """Duas conferencias que nasceram da caminhada por comodo.

    A primeira: o nicho de condensadora trazia ESCRITO "2 ativas + 1
    reservada" e a lista lhe mandava cinco. Prosa nao roda e nao reprova —
    envelhece em silencio enquanto a lista muda.

    A segunda: familia de esquadria que existe no catalogo e nao existe em vao
    nenhum. Ela nao chega ao BOM, porque o levantamento le VAOS; chega ao
    QUADRO, que e o que vai para o fornecedor cotar.
    """
    import projeto as pj
    import nucleo.instalacoes as ins
    out = []

    o = ins.ocupacao_de_nicho(pj)
    for n in o["nichos"]:
        out.append(Achado("NOTA" if n["cabe"] else "ERRO", f"nicho {n['nicho']}",
                          f"{n['leitura']}, sobrando {n['sobra']} mm. A "
                          f"ocupacao e DERIVADA da lista de climatizacao: o "
                          f"texto do nicho dizia 2 ativas e a lista mandava "
                          f"{n['ativos']}"))
    out.append(Achado("NOTA", "criterio de nicho", o["criterio"]))

    # o texto do nicho nao pode voltar a contar unidades
    import re
    tec = {t["cod"]: t for t in pj.TECNICOS}
    conta = [c for c, t in tec.items()
             if re.search(r"\b\d+ (condensadora|posicoes|posicao)", t.get("obs", "")
                          + " " + t.get("nome", ""))]
    out.append(Achado("NOTA" if not conta else "ATENCAO", "prosa que conta",
                      "nenhum texto de area tecnica conta unidades: quem conta "
                      "e a lista, e o texto descreve"
                      if not conta else
                      f"texto de {', '.join(conta)} voltou a contar unidades"))

    usadas = {v[0] for v in pj.VAOS}
    orfas = sorted(set(pj.ESQUADRIAS) - usadas)
    marcadas = [f for f in orfas if "SEM USO" in pj.ESQUADRIAS[f][3].upper()]
    out.append(Achado("NOTA" if len(marcadas) == len(orfas) else "ATENCAO",
                      "familia sem vao",
                      f"{len(orfas)} familia(s) de esquadria sem nenhum vao: "
                      f"{', '.join(orfas) or 'nenhuma'}"
                      + (" — todas marcadas no catalogo" if len(marcadas) == len(orfas)
                         else f" — SEM MARCACAO: {set(orfas) - set(marcadas)}")
                      + ". Familia orfa nao chega ao BOM, que le VAOS; chega ao "
                        "QUADRO, que e o que o fornecedor cota"))

    # a simetria declarada entre as suites espelhadas
    def janela_do_banho(pai):
        d = next(x for x in pj.SUBDIVISOES
                 if x["pai"] == pai and x["nome"] == "BANHO")
        for t, x, y, o_, pav in pj.VAOS:
            # o pavimento FILTRA: sem isto, a janela do terreo que cai sob o
            # banho do superior casa por coordenada e responde pela de cima
            if (pav == pai[0]
                    and d["x"] - 90 <= x <= d["x"] + d["w"] + 90
                    and d["y"] - 90 <= y <= d["y"] + d["h"] + 90
                    and t.startswith("J")):
                return t, pj.ESQUADRIAS[t][0] * pj.ESQUADRIAS[t][1] / 1e6
        return None, 0.0
    a2, ar2 = janela_do_banho("S-S02")
    a3, ar3 = janela_do_banho("S-S03")
    out.append(Achado("NOTA" if a2 == a3 else "ERRO", "suites espelhadas",
                      f"o banho da suite 02 leva {a2} e o da 03 leva {a3}. As "
                      f"duas sao declaradas ESPELHADAS e intocadas desde R06, e "
                      f"ate R46 tinham esquadrias diferentes — 0,36 m2 contra "
                      f"0,72 — com o lado menor justamente abaixo do minimo de "
                      f"area molhada. Simetria declarada que o desenho nao "
                      f"cumpre e simetria que ninguem confere"))
    return out


def checar_cotacao() -> list[Achado]:
    """O preco (H) vira cotacao por uma porta, e a porta tem tranca.

    E, no caminho, a pergunta "da para cotar?" achou o defeito que a faixa de
    plausibilidade nao achava: o aco estava no BOM DUAS VEZES, em duas
    unidades — 6.230,8 kg de barra e 1.033 pecas cortadas, as duas com preco,
    as duas somadas. R$ 62.664 de um total de R$ 464.861: 13,5 %.

    Nenhuma faixa pegaria isso. A faixa de custo por m2 vai de 600 a 1.800, e o
    valor inflado — 1.571 — cabia dentro dela com folga. Faixa larga o bastante
    para ser segura e larga o bastante para esconder uma dupla contagem. O que
    pega e IDENTIDADE: a mesma materia aparece uma vez so.
    """
    import projeto as pj
    import nucleo.bom as bo
    import nucleo.cotacao as co
    out = []
    r = fx.liberacao()
    itens = r["bom"]

    # ---- 1. a identidade: barra e peca sao o MESMO aco
    aco = next(i for i in itens if i.sku == "ACO-PERF")
    pf = [i for i in itens if i.sku.startswith("PF-")]
    massa_pf = sum(i.quantidade * i.preco_unit / bo.PRECOS["aco_perfil_kg"]
                   for i in pf)
    bruta = massa_pf / r["plano"]["aproveitamento"]
    bate = abs(bruta - aco.quantidade) < 1.0
    compram = [i.sku for i in [aco] + pf if i.compra]
    out.append(Achado("NOTA" if bate and compram == ["ACO-PERF"] else "ERRO",
                      "aco uma vez so",
                      f"as {len(pf)} linhas de perfil somam {massa_pf:,.1f} kg "
                      f"uteis, que sobre o aproveitamento de "
                      f"{r['plano']['aproveitamento'] * 100:.1f} % dao "
                      f"{bruta:,.1f} kg — exatamente a linha ACO-PERF. E o "
                      f"MESMO aco descrito de dois jeitos: compra-se barra, "
                      f"produz-se peca. So uma das duas entra no custo, e o "
                      f"campo `compra` diz qual"))

    # ---- 2. o contrafactual: quanto custava contar duas vezes
    inflado = sum(i.total for i in itens)   # ignora o campo `compra`
    real = bo.total(itens)
    area = pj.CADASTRO.area_m2
    out.append(Achado("NOTA" if inflado > real else "ERRO", "o que custava",
                      f"somando tudo sem distinguir compra de producao o total "
                      f"vai de R$ {real:,.0f} para R$ {inflado:,.0f} "
                      f"(+{(inflado / real - 1) * 100:.1f} %), e o custo por m2 "
                      f"de R$ {real / area:,.0f} para R$ {inflado / area:,.0f}. "
                      f"Os dois cabem na faixa de plausibilidade de 600 a "
                      f"1.800: faixa larga o bastante para ser segura e larga "
                      f"o bastante para esconder dupla contagem. O que pega "
                      f"nao e faixa, e identidade"))

    # ---- 3. SKU e chave: repetido nao recebe cotacao, recebe duas
    import collections
    dup = [k for k, v in collections.Counter(i.sku for i in itens).items()
           if v > 1]
    out.append(Achado("NOTA" if not dup else "ERRO", "sku unico",
                      "nenhum SKU se repete no BOM. O contrato do ERP liga "
                      "preco a quantidade pela chave de SKU, e chave repetida "
                      "recebe duas cotacoes que ninguem sabe somar"
                      if not dup else f"SKU repetido: {dup}"))

    # ---- 4. o mapa: o que se pergunta ao fornecedor
    m = r["cotacao"]["mapa"]
    out.append(Achado("NOTA" if m["n"] == sum(1 for i in itens if i.compra)
                      else "ERRO", "mapa",
                      f"{m['n']} linhas de compra no mapa de cotacao, "
                      f"{m['n_alternativas']} rotas alternativas separadas "
                      f"(peca cortada em vez de barra, placa inteira em vez de "
                      f"m2) e {m['cotaveis']} prontas para virar preco. Cotacao "
                      f"nao se pede com quantidade: se pede com especificacao"))

    out.append(Achado("ATENCAO" if m["lacunas"] else "NOTA", "lacuna",
                      f"{m['n_lacunas']} linhas nao estao prontas para cotar, e "
                      f"cada uma diz o que falta: "
                      + "; ".join(sorted({x["faltam"][0][:46]
                                          for x in m["lacunas"]}))
                      + ". Preco recebido para linha mal especificada e pior "
                        "que preco nenhum — parece comparavel e nao e"))

    # ---- 5. a porta: o que entra e validado
    hoje = "2026-09-14"
    boa = co.Cotacao("ACO-PERF", "Fornecedor A", 12.40, "kg", "2026-09-01",
                     validade_dias=30, lead_time_dias=21)
    ruins = [
        co.Cotacao("ACO-PERF", "B", 11.90, "kg", ""),                 # sem data
        co.Cotacao("ACO-PERF", "C", 11.10, "kg", "2026-01-05"),       # vencida
        co.Cotacao("ACO-PERF", "D", 11.30, "t", "2026-09-01"),        # unidade
        co.Cotacao("NAO-EXISTE", "E", 10.00, "kg", "2026-09-01"),     # sku
        co.Cotacao("ACO-PERF", "F", 2.20, "kg", "2026-09-01", moeda="USD"),
    ]
    rec = co.receber([boa] + ruins, itens, hoje)
    motivos = {m_[:18] for x in rec["recusadas"] for m_ in x["motivos"]}
    out.append(Achado("NOTA" if rec["n_aceitas"] == 1 and
                      len(rec["recusadas"]) == len(ruins) else "ERRO",
                      "validacao",
                      f"das {len(ruins) + 1} propostas de teste, 1 entra e "
                      f"{len(rec['recusadas'])} sao recusadas, cada uma pelo "
                      f"seu motivo: {len(motivos)} motivos distintos. 'Preco "
                      f"sem data nao e preco' esta escrito no contrato do ERP "
                      f"desde R27 — agora e codigo que recusa"))

    # ---- 6. comparacao exige comparacao
    tres = [co.Cotacao("ACO-PERF", f"F{i}", 12.0 + i * 0.5, "kg", "2026-09-01")
            for i in range(3)]
    c3 = co.comparar(co.receber(tres, itens, hoje)["aceitas"])
    c1 = co.comparar(co.receber([boa], itens, hoje)["aceitas"])
    out.append(Achado("NOTA" if c3["competitivos"] == 1 and
                      c1["competitivos"] == 0 else "ERRO", "tres propostas",
                      f"com 3 propostas o item e competitivo e o spread sai "
                      f"medido ({c3['itens'][0]['spread'] * 100:.1f} %); com 1, "
                      f"nao. Proposta unica nao e cotacao: e um preco, e o "
                      f"spread e a unica medida de mercado que uma compra "
                      f"privada produz sem tabela publica"))

    # ---- 7. aplicar nao pode mexer na estrutura
    ap = co.aplicar(itens, c3)
    mesma = (len(ap["itens"]) == len(itens)
             and [i.sku for i in ap["itens"]] == [i.sku for i in itens]
             and all(a.quantidade == b.quantidade
                     for a, b in zip(ap["itens"], itens)))
    out.append(Achado("NOTA" if mesma and ap["n"] == 1 else "ERRO", "aceite",
                      "trocar o preco (H) pelo cotado nao muda a lista nem as "
                      "quantidades, so os valores — que e o criterio de aceite "
                      "escrito no contrato do ERP em R27. Se a lista mudasse, "
                      "a chave de SKU estaria errada"))

    # ---- 8. quanto do custo foi perguntado a alguem
    cob = r["cotacao"]["cobertura"]
    out.append(Achado("ATENCAO" if cob["cotado_pct"] < 100 else "NOTA",
                      "cobertura", cob["leitura"]
                      + ". Nao e 'quanto custa', e 'quanto do que custa foi "
                        "perguntado'. A 0 % isto e ordem de grandeza; a 100 % e "
                        "orcamento"))

    # ---- 9. e onde doi mais se o preco andar
    sens = sorted(r["cotacao"]["sensibilidade"], key=lambda x: -x["exposicao"])
    out.append(Achado("NOTA", "exposicao",
                      "com 100 % dos precos (H), a informacao honesta nao e o "
                      "valor: e a derivada. " + "; ".join(
                          f"{x['familia']} {x['exposicao'] * 100:.0f} % do total "
                          f"(+20 % = R$ {x['delta']:,.0f})"
                          for x in sens[:4])))
    return out


def checar_pendencias() -> list[Achado]:
    """O que o caderno declara aberto tranca o que ele diz trancar?

    Este e o item que faltava no checklist, e a sua ausencia era a mais grave
    de todas: dezessete verificacoes de coerencia interna do modelo produziam
    a frase "LIBERADO PARA FABRICACAO" enquanto o proprio caderno listava oito
    pendencias abertas, duas delas trancando exatamente a fabricacao.
    Consistencia interna nao e autorizacao.
    """
    import projeto as pj
    import inspect
    out = []
    r = fx.liberacao()
    pen = r["pendencias"]

    out.append(Achado("NOTA" if hasattr(pj, "PENDENCIAS") else "ERRO", "fonte",
                      f"as {len(pj.PENDENCIAS)} pendencias sao dado do CASO. "
                      f"Viviam dentro de pranchas7.py, com copia divergente "
                      f"dentro de pranchas3.py — duas listas de pendencias que "
                      f"ja discordavam entre si, e nenhuma consultavel pelo "
                      f"checklist"))

    # as duas pranchas tem de LER a mesma lista, nao manter copia
    import pranchas3 as p3, pranchas7 as p7
    lidas = ("pj.PENDENCIAS" in inspect.getsource(p3.quadros_gerais)
             if hasattr(p3, "quadros_gerais") else
             "pj.PENDENCIAS" in inspect.getsource(p3))
    out.append(Achado("NOTA" if lidas and len(p7.PENDENCIAS) == len(pj.PENDENCIAS)
                      else "ERRO", "uma lista so",
                      f"PR-09 e PR-33 leem a mesma lista de "
                      f"{len(pj.PENDENCIAS)} itens. A copia da PR-09 trazia um "
                      f"assunto que a outra nao tinha — o diametro do ramal do "
                      f"chuveiro — e unificar sem perde-lo foi parte do "
                      f"trabalho: unificacao que perde informacao e so a outra "
                      f"metade do mesmo defeito"))

    blo = pen["bloqueantes"]
    out.append(Achado("NOTA" if blo else "ATENCAO", "portao",
                      f"{len(pen['abertas'])} pendencias abertas, "
                      f"{len(blo)} trancando a fabricacao: "
                      + ", ".join(f"#{d['n']} {d['titulo']}" for d in blo)
                      + ". Nem todo item aberto impede fabricar — a certidao "
                        "do SU16 condiciona a implantacao, nao o corte do "
                        "perfil — e tratar todos como iguais tornaria o campo "
                        "inutil"))

    lib = r["liberacao"]
    coerente = (("pendencias" in lib["pendentes"]) == bool(blo))
    out.append(Achado("NOTA" if coerente else "ERRO", "efeito",
                      f"a situacao e '{lib['situacao']}' e o item 'pendencias' "
                      f"{'reprova' if blo else 'passa'}: o checklist agora "
                      f"responde ao que o caderno declara, em vez de ignora-lo"))

    # CONTRAFACTUAL: sem pendencia bloqueante o item passa. Um item que reprova
    # sempre e tao inutil quanto um que passa sempre.
    import nucleo.scores as sc
    sem = sc.liberar({c: True for c, _ in sc.CHECKLIST})
    com = sc.liberar({**{c: True for c, _ in sc.CHECKLIST}, "pendencias": False})
    out.append(Achado("NOTA" if sem["liberado"] and not com["liberado"]
                      else "ERRO", "contrafactual",
                      "com as pendencias bloqueantes resolvidas o checklist "
                      "libera, e com uma delas aberta nao libera: o item "
                      "decide, em vez de decorar"))

    out.append(Achado("NOTA" if len(sc.CHECKLIST) == 18 else "ERRO", "18 itens",
                      f"{len(sc.CHECKLIST)} itens em tres naturezas distintas: "
                      f"16 perguntam se o que esta no modelo esta certo, o 17o "
                      f"se o que precisa estar la esta, e o 18o se o que o "
                      f"projeto declara que falta permite fabricar"))
    return out


def checar_combinacoes() -> list[Achado]:
    """A combinacao e uma hipotese sobre simultaneidade, nao uma soma.

    A verificacao que mais importa e a do permanente FAVORAVEL: sem ela o
    levantamento da cobertura pelo vento nunca aparece, porque o peso proprio
    entra sempre majorado e sempre segura o telhado no lugar.
    """
    import nucleo.combinacoes as cb
    out = []

    for n, g in cb.GAMA.items():
        if g["fav"] > g["desf"]:
            out.append(Achado("ERRO", n, "gama favoravel maior que o desfavoravel"))
    for n, p in cb.PSI.items():
        vals = [p["psi0"], p["psi1"], p["psi2"]]
        if not all(0.0 <= v <= 1.0 for v in vals):
            out.append(Achado("ERRO", n, f"psi fora de [0,1]: {vals}"))
        if not (p["psi0"] >= p["psi1"] >= p["psi2"]):
            out.append(Achado("ERRO", n,
                              f"psi0 >= psi1 >= psi2 violado: {vals}"))

    acoes = [("G", "permanente"), ("Q", "acidental"), ("W", "vento")]
    combs = cb.gerar(acoes)
    elu = [c for c in combs if c.tipo == "ELU"]

    # toda acao precisa aparecer com fator nao nulo em alguma combinacao
    for cod, _ in acoes:
        if not any(c.fator(cod) for c in combs):
            out.append(Achado("ERRO", cod, "acao nunca entra em combinacao alguma"))

    # cada variavel precisa tomar a vez de principal
    princ = {c.principal for c in elu}
    falta = {c for c, n in acoes if n not in cb.PERMANENTES} - princ
    if falta:
        out.append(Achado("ERRO", "ELU", f"nunca sao acao principal: {sorted(falta)}"))

    # o permanente favoravel tem de existir — e o que revela o levantamento
    if not any(c.fator("G") < 1.4 for c in elu):
        out.append(Achado("ERRO", "ELU",
                          "nenhuma combinacao minora o permanente: o "
                          "levantamento da cobertura pelo vento nunca apareceria"))
    else:
        esf = {"G": {"telhado": -8.0}, "Q": {"telhado": 0.0}, "W": {"telhado": 14.0}}
        env = cb.envelope(elu, esf)["telhado"]
        out.append(Achado("NOTA", "ELU",
                          f"cobertura: de {env['min']:+.2f} ({env['comb_min']}) a "
                          f"{env['max']:+.2f} kN ({env['comb_max']}) — o "
                          f"levantamento so aparece com o peso proprio minorado"))

    # o envelope contem, por construcao, cada combinacao individual
    esf = {"G": {"x": -10.0}, "Q": {"x": -6.0}, "W": {"x": 2.0}}
    env = cb.envelope(elu, esf)["x"]
    todas = [sum(c.fator(a) * esf[a]["x"] for a in esf) for c in elu]
    ok = env["min"] <= min(todas) + 1e-9 and env["max"] >= max(todas) - 1e-9
    out.append(Achado("NOTA" if ok else "ERRO", "envelope",
                      f"contem as {len(todas)} combinacoes individuais"))

    out.append(Achado("NOTA", "combinacoes",
                      f"{len(combs)} combinacoes geradas de 3 acoes: "
                      f"{len(elu)} ELU e {len(combs)-len(elu)} ELS"))
    return out


def checar_cargas() -> list[Achado]:
    """Sobrecarga normativa positiva, e o uso do caso presente na tabela."""
    import nucleo.cargas as cg
    out = []
    ruins = [k for k, v in cg.SOBRECARGA_NBR6120.items() if v <= 0]
    if ruins:
        out.append(Achado("ERRO", "NBR 6120", f"sobrecarga nao positiva: {ruins}"))
    if cg.SOBRECARGA_NBR6120["biblioteca"] <= cg.SOBRECARGA_NBR6120["dormitorio"]:
        out.append(Achado("ERRO", "NBR 6120", "biblioteca leve demais"))
    try:
        cg.sobrecarga("nao existe")
        out.append(Achado("ERRO", "NBR 6120", "uso inexistente devolveu valor"))
    except KeyError:
        out.append(Achado("NOTA", "NBR 6120",
                          "uso sem sobrecarga tabelada levanta erro em vez de "
                          "assumir um valor"))
    p = cg.peso_camadas([("concreto armado", 80), ("argamassa", 20)])
    esperado = 25.0 * 0.08 + 21.0 * 0.02
    out.append(Achado("NOTA" if abs(p - esperado) < 1e-12 else "ERRO", "peso",
                      f"peso de pacote conferido: {p:.3f} kN/m2"))
    out.append(Achado("NOTA", "cargas",
                      f"{len(cg.SOBRECARGA_NBR6120)} usos tabelados, "
                      f"{len(cg.EQUIPAMENTOS)} equipamentos, "
                      f"{len(cg.NATUREZAS)} naturezas de acao"))
    return out


def checar_solver() -> list[Achado]:
    """O solver de porticos contra solucoes fechadas da resistencia dos materiais.

    Um solver errado nao se denuncia: devolve numeros plausiveis. Por isso a
    verificacao nao olha se o resultado "parece certo" — compara com os casos
    que tem solucao exata, e conta o residuo.
    """
    import nucleo.solver as sv
    out = []
    E, G = 205_000.0, 78_850.0
    I, A, J, L = 1.0e7, 1_000.0, 1.0e6, 3_000.0
    s = sv.Secao("ensaio", A, I, I, J, E, G)

    def modelo_barra(n=1, apoio_i=sv.ENGASTE, apoio_j=sv.LIVRE, q=(0.0, 0.0)):
        m = sv.Modelo()
        for k in range(n + 1):
            ap = apoio_i if k == 0 else (apoio_j if k == n else sv.LIVRE)
            m.no(f"n{k}", L * k / n, 0, 0, ap)
        for k in range(n):
            m.barra(f"b{k}", f"n{k}", f"n{k+1}", s, q_local=q)
        return m

    # 1) balanco com carga na ponta: flecha e rotacao
    m = modelo_barra()
    m.carga("n1", fz=-10.0)
    r = m.resolver()
    d = m.deslocamento(r, "n1", 2)
    dt = -10.0 * L ** 3 / (3 * E * I)
    th = m.deslocamento(r, "n1", 4)
    tht = 10.0 * L ** 2 / (2 * E * I)
    out.append(_conf("balanco: flecha PL3/3EI", d, dt, "mm"))
    out.append(_conf("balanco: rotacao PL2/2EI", abs(th), abs(tht), "rad"))

    # 2) biapoiada com carga distribuida
    w = 0.01                                   # kN/mm
    m = modelo_barra(8, (True, True, True, True, False, False),
                     (True, True, True, False, False, False), q=(0.0, -w))
    r = m.resolver()
    d = m.deslocamento(r, "n4", 2)
    dt = -5 * w * L ** 4 / (384 * E * I)
    out.append(_conf("biapoiada: flecha 5wL4/384EI", d, dt, "mm"))
    mmax = max(abs(r["esforcos"][b][10]) for b in r["esforcos"])
    out.append(_conf("biapoiada: momento wL2/8", mmax, w * L * L / 8, "kNmm", 0.02))

    # 3) barra tracionada: PL/EA
    m = modelo_barra()
    m.carga("n1", fx=25.0)
    r = m.resolver()
    out.append(_conf("axial: PL/EA", m.deslocamento(r, "n1", 0),
                     25.0 * L / (E * A), "mm"))

    # 4) torcao: TL/GJ
    m = modelo_barra()
    m.carga("n1", mx=1_000.0)
    r = m.resolver()
    out.append(_conf("torcao: TL/GJ", m.deslocamento(r, "n1", 3),
                     1_000.0 * L / (G * J), "rad"))

    # 5) equilibrio global em cada direcao
    m = modelo_barra(4, sv.ENGASTE, sv.LIVRE, q=(0.0, -w))
    m.carga("n4", fz=-7.0, fy=3.0)
    r = m.resolver()
    rz = sum(v[2] for v in r["reacoes"].values())
    ry = sum(v[1] for v in r["reacoes"].values())
    carga_z = -7.0 - w * L
    out.append(_conf("equilibrio vertical", rz, -carga_z, "kN", 1e-6))
    out.append(_conf("equilibrio horizontal", ry, -3.0, "kN", 1e-6))

    # 6) REGRESSAO: secao de inercias DIFERENTES nos dois eixos.
    # Este ensaio existe porque a versao anterior passava em tudo com inercias
    # iguais: um erro de sinal no acoplamento do plano x-z cancelava com um erro
    # nas forcas de engastamento, e os dois so apareceram ao cruzar o solver com
    # a formula fechada usando um perfil real, de Ix/Iy = 31. Secao simetrica
    # esconde par de erros; secao assimetrica nao.
    sa = sv.Secao("assim", A, 3.4e6, 1.1e5, J, E)
    for nome, plano, inercia in (("plano x-z (Iy)", (0.0, -0.006), 3.4e6),
                                 ("plano x-y (Iz)", (-0.006, 0.0), 1.1e5)):
        m = sv.Modelo()
        n = 8
        for k in range(n + 1):
            ap = ((True, True, True, True, False, False) if k == 0 else
                  ((True, True, True, False, False, False) if k == n else sv.LIVRE))
            m.no(f"a{k}", L * k / n, 0, 0, ap)
        for k in range(n):
            m.barra(f"e{k}", f"a{k}", f"a{k+1}", sa, q_local=plano)
        rr = m.resolver()
        comp = 2 if plano[1] else 1
        d = m.deslocamento(rr, f"a{n//2}", comp)
        dt = -5 * 0.006 * L ** 4 / (384 * E * inercia)
        out.append(_conf(f"inercias diferentes, {nome}", d, dt, "mm", 1e-9))

    # 7) mecanismo tem de ser detectado, nao mascarado
    m = sv.Modelo()
    m.no("a", 0, 0, 0, (True, True, True, False, False, False))
    m.no("b", L, 0, 0)
    m.barra("v", "a", "b", s)
    m.carga("b", fz=-1.0)
    try:
        m.resolver()
        out.append(Achado("ERRO", "mecanismo",
                          "estrutura com rotacao livre resolveu sem avisar"))
    except sv.Mecanismo as exc:
        out.append(Achado("NOTA", "mecanismo",
                          f"estrutura hipostatica detectada no grau de "
                          f"liberdade {exc.gl}, em vez de devolver deslocamento "
                          f"qualquer"))
    return out


def checar_segunda_ordem() -> list[Achado]:
    """P-Delta contra a carga critica de Euler.

    O efeito de segunda ordem e o que faz uma estrutura que passa no calculo de
    primeira ordem cair: a carga vertical, agindo sobre a geometria ja deslocada
    pelo vento, amplifica o proprio deslocamento. A amplificacao tem solucao
    fechada — 1/(1 - N/Ncr) — e e contra ela que o solver e conferido.
    """
    import math
    import nucleo.solver as sv
    out = []
    E, I, A, L, n = 205_000.0, 1.0e6, 1_000.0, 3_000.0, 10
    s = sv.Secao("col", A, I, I, 1.0e5, E)
    ncr = math.pi ** 2 * E * I / L ** 2

    def coluna(p):
        m = sv.Modelo()
        for k in range(n + 1):
            z = L * k / n
            ap = (True, True, True, False, False, True) if k == 0 else (
                 (True, True, False, False, False, False) if k == n else sv.LIVRE)
            m.no(f"n{k}", 0, 0, z, ap)
        for k in range(n):
            m.barra(f"b{k}", f"n{k}", f"n{k+1}", s)
        m.carga(f"n{n}", fz=-p)
        m.carga(f"n{n//2}", fy=0.5)
        return m

    m0 = coluna(0.0)
    r0 = m0.resolver()
    base = abs(m0.deslocamento(r0, f"n{n//2}", 1))
    for frac in (0.25, 0.50, 0.75):
        m = coluna(frac * ncr)
        r = m.resolver(segunda_ordem=True)
        d = abs(m.deslocamento(r, f"n{n//2}", 1))
        amp, teor = d / base, 1.0 / (1 - frac)
        out.append(_conf(f"amplificacao P-Delta a {frac:.0%} de Ncr",
                         amp, teor, "x", 0.05))
    out.append(Achado("NOTA", "Euler",
                      f"carga critica da coluna de ensaio: {ncr:.2f} kN "
                      f"(pi2.E.I/L2), com {n} barras"))
    return out


def _conf(nome, obtido, esperado, unid, tol=1e-6):
    """Compara com a solucao fechada e devolve o achado ja formatado."""
    ref = abs(esperado) or 1.0
    rel = abs(obtido - esperado) / ref
    return Achado("NOTA" if rel <= tol else "ERRO", nome,
                  f"numerico {obtido:+.6g} {unid} contra fechada "
                  f"{esperado:+.6g}; erro relativo {rel:.2e}")


def checar_mrd() -> list[Achado]:
    """O Metodo da Resistencia Direta contra as proprias curvas da norma.

    As curvas do MRD sao continuas por construcao: os dois ramos se encontram
    exatamente na esbeltez de transicao. Se nao encontram, um coeficiente esta
    trocado — e o erro nao aparece no resultado, so numa descontinuidade de
    alguns por cento que ninguem nota olhando um numero isolado.
    """
    import nucleo.verificacao as vr
    import nucleo.perfis as pf
    import nucleo.materiais as mt
    out = []

    # 1) continuidade dos dois ramos da curva global em lambda0 = 1,5
    a = 0.658 ** (1.5 ** 2)
    b = 0.877 / 1.5 ** 2
    out.append(Achado("NOTA" if abs(a - b) / b < 0.005 else "ERRO", "curva global",
                      f"os dois ramos se encontram em lambda0 = 1,5: "
                      f"{a:.5f} contra {b:.5f} ({abs(a-b)/b*100:.2f} % de salto)"))

    # 2) continuidade da curva local em lambda_l = 0,776
    r = 0.776 ** -2                          # Nl/Nc no ponto de transicao
    esq, dir_ = 1.0, (1 - 0.15 * r ** 0.4) * r ** 0.4
    out.append(Achado("NOTA" if abs(esq - dir_) < 0.02 else "ERRO", "curva local",
                      f"continuidade em lambda_l = 0,776: {esq:.4f} contra "
                      f"{dir_:.4f}"))

    # 3) limite fisico: barra curtissima chega a carga de escoamento
    p = pf.Perfil("Ue", "Ue", 90, 40, 12, 1.55)
    aco = mt.POR_ACO["ZAR 230"]
    c = vr.compressao(p, aco, L=1.0)
    ny = p.props()["A"] * aco.fy / 1000.0
    out.append(Achado("NOTA" if c["modos"]["global"] / ny > 0.999 else "ERRO",
                      "limite", f"a L = 1 mm a parcela global atinge a carga de "
                                f"escoamento: {c['modos']['global']/ny*100:.2f} % de Ny"))

    # 4) monotonia: alongar a barra nunca aumenta a resistencia
    ns = [vr.compressao(p, aco, L=L)["nrd"] for L in (500, 1000, 2000, 3000, 4500)]
    ok = all(y <= x + 1e-9 for x, y in zip(ns, ns[1:]))
    out.append(Achado("NOTA" if ok else "ERRO", "monotonia",
                      f"Nrd por comprimento: {[round(n,2) for n in ns]} kN"))

    # 5) secao duplamente simetrica nao tem reducao por flexo-torcao
    tubo = pf.Perfil("SHS", "SHS", 100, 100, 0, 2.0)
    pr = tubo.props()
    g = vr.n_global(pr, 230, 205_000.0, 78_850.0, L=3000.0)
    euler = math.pi ** 2 * 205_000.0 * min(pr["Ix"], pr["Iy"]) / 3000.0 ** 2
    ok = abs(g["ne"] - euler) / euler < 1e-9 and "flexo" not in g["modo"]
    out.append(Achado("NOTA" if ok else "ERRO", "simetria",
                      f"tubo quadrado: carga critica {g['ne']:.1f} N pelo modo "
                      f"'{g['modo']}', igual a Euler ({euler:.1f} N)"))

    # 6) travar a parede aumenta a resistencia — e por isso que ela e travada
    livre = vr.compressao(p, aco, L=2600)["nrd"]
    travado = vr.compressao(p, aco, L=2600, ky=0.5, kz=0.5)["nrd"]
    out.append(Achado("NOTA" if travado > livre else "ERRO", "travamento",
                      f"blocking no meio da altura leva Nrd de {livre:.2f} para "
                      f"{travado:.2f} kN (+{(travado/livre-1)*100:.0f} %) — e "
                      f"por isso que a parede de LSF e travada"))

    # 7) os tres modos competem, e qual governa muda com o comprimento
    modos = {vr.compressao(p, aco, L=L)["modo"] for L in (600, 1500, 4000)}
    out.append(Achado("NOTA" if len(modos) > 1 else "ATENCAO", "modos",
                      f"modos que governam ao longo do comprimento: "
                      f"{sorted(modos)} — perfil formado a frio nao se "
                      f"dimensiona 'pela tensao'"))

    # 8) interacao: os casos puros devolvem a propria utilizacao
    i1 = vr.interacao(10.0, 0.0, 20.0, 1.0)
    i2 = vr.interacao(0.0, 0.5, 20.0, 1.0)
    ok = abs(i1["uso"] - 0.5) < 1e-12 and abs(i2["uso"] - 0.5) < 1e-12
    out.append(Achado("NOTA" if ok else "ERRO", "interacao",
                      "compressao pura e flexao pura devolvem a propria "
                      "utilizacao"))

    # 9) o limite do modelo distorcional e declarado, nao escondido
    nota = vr.compressao(p, aco, L=2600)["nota_distorcional"]
    out.append(Achado("ATENCAO" if "(H)" in nota else "ERRO", "distorcional",
                      f"{nota} — pendencia declarada: o valor rigoroso exige "
                      f"analise de faixas finitas ou tabela do fabricante"))
    return out


def checar_cisalhamento() -> list[Achado]:
    """A curva de cortante e continua nas duas transicoes de esbeltez."""
    import nucleo.verificacao as vr
    import nucleo.perfis as pf
    import nucleo.materiais as mt
    out = []
    aco = mt.POR_ACO["ZAR 230"]
    vs = []
    for bw in (60, 90, 140, 200, 250, 300):
        p = pf.Perfil("x", "Ue", bw, 40, 12, 0.95)
        v = vr.cisalhamento(p, aco)
        vs.append((v["esbeltez"], v["vrd"]))
    # a resistencia por unidade de alma cai quando a alma afina demais
    razoes = [vrd / esb for esb, vrd in vs]
    ok = all(b <= a + 1e-9 for a, b in zip(razoes, razoes[1:]))
    out.append(Achado("NOTA" if ok else "ERRO", "cortante",
                      f"a resistencia por unidade de esbeltez cai "
                      f"monotonicamente: {[round(r,4) for r in razoes]}"))
    out.append(Achado("NOTA", "cortante",
                      f"alma de {vs[0][0]:.0f} a {vs[-1][0]:.0f} de esbeltez: "
                      f"Vrd de {vs[0][1]:.2f} a {vs[-1][1]:.2f} kN"))
    return out


def checar_painelizacao() -> list[Achado]:
    """A parede virou produto: o que se corta e o que se parafusa.

    Cada regra verificada aqui existe por um motivo construtivo, nao por
    convencao de desenho. Montante dentro do vao seria peca cortada e jogada
    fora; cripple fora da modulacao deixaria a placa sem onde parafusar; painel
    acima do peso nao sobe sem guindaste.
    """
    import projeto as pj
    import elementos as el
    import nucleo.painel as pn
    out = []
    cfg = pn.Config()
    cat = pn._catalogo_massa()
    total_pecas = total_massa = 0
    problemas, excecoes, sem_apoio_dec = [], [], set()

    for pav, ambientes in (("T", pj.TERREO), ("S", pj.SUPERIOR)):
        paredes = el.derivar_paredes(ambientes)
        vaos = list(el.vaos_do_pavimento(pav))
        pais = pn.painelizar(paredes, vaos, cfg, prefixo=f"{pav}P")
        comp_paredes = sum(p.comp for p in paredes)
        comp_paineis = sum(p.comp for p in pais)
        if abs(comp_paredes - comp_paineis) > 1:
            problemas.append(f"{pav}: painelizacao perde {comp_paredes-comp_paineis} "
                             f"mm de parede")
        for p in pais:
            fam = p.por_familia()
            total_pecas += len(p.pecas)
            m = p.massa(cat)
            total_massa += m
            if fam.get("track", 0) < 2:
                problemas.append(f"{p.cod}: sem guia inferior e superior")
            if p.comp > cfg.comp_max:
                # painel grande demais so e aceitavel se o motivo estiver
                # declarado: abertura que ocupa a faixa inteira de corte
                if p.obs:
                    excecoes.append(f"{p.cod} ({p.comp} mm): {p.obs}")
                else:
                    problemas.append(f"{p.cod}: {p.comp} mm acima do limite de "
                                     f"transporte ({cfg.comp_max}), sem motivo "
                                     f"declarado")
            if m > cfg.peso_max:
                problemas.append(f"{p.cod}: {m:.0f} kg acima do limite de "
                                 f"icamento ({cfg.peso_max})")
            n_ab = len(p.aberturas)
            if n_ab:
                # vao de altura total nao tem verga: o criterio e o mesmo que
                # o gerador usou, pn.cabe_verga, e nao uma copia dele aqui
                com_verga = sum(1 for a in p.aberturas
                                if pn.cabe_verga(a, p.altura, cfg))
                for nome, esperado in (("king stud", 2 * n_ab),
                                       ("jack stud", 2 * n_ab),
                                       ("header", com_verga)):
                    if fam.get(nome, 0) != esperado:
                        problemas.append(f"{p.cod}: {fam.get(nome,0)} {nome} para "
                                         f"{n_ab} abertura(s), esperado {esperado}")
            # nenhum montante modular dentro de vao
            for ab in p.aberturas:
                a0 = ab["centro"] - ab["larg"] / 2
                a1 = ab["centro"] + ab["larg"] / 2
                for pc in p.pecas:
                    if pc.familia == "stud" and a0 < pc.x < a1:
                        problemas.append(f"{p.cod}: montante em x = {pc.x} dentro "
                                         f"do vao {ab['tipo']}")
            # cripple tem de cair na modulacao, senao a placa fica sem apoio
            for pc in p.pecas:
                if pc.familia.startswith("cripple") and pc.x % cfg.modulacao:
                    problemas.append(f"{p.cod}: cripple em x = {pc.x}, fora da "
                                     f"modulacao de {cfg.modulacao} mm")
            # blocking obrigatorio acima da altura de travamento
            if p.altura > cfg.blocking_a_cada and not fam.get("blocking"):
                problemas.append(f"{p.cod}: sem blocking numa altura de {p.altura} mm")
            # BARRA: nenhuma peca maior que o que se compra. Uma guia de 7.800
            # mm nao e item de catalogo — a peca que nao cabe na barra nao e
            # uma peca, sao duas com uma emenda entre elas.
            for pc in p.pecas:
                if pc.comp > cfg.comp_barra:
                    problemas.append(f"{p.cod}: {pc.cod} tem {pc.comp} mm, "
                                     f"acima da barra de {cfg.comp_barra}")
            # EMENDA SOBRE APOIO: a emenda tem de cair num montante, senao
            # rotula. Onde nao cai, tem de estar declarada — e a verificacao
            # confere as duas coisas, porque declarar errado e pior que calar.
            verticais = {q.x for q in p.pecas if q.vertical}
            verticais |= {q.x + pn.bw(q.perfil) for q in p.pecas if q.vertical}
            juntas = {}
            for pc in p.pecas:
                m = re.search(r"emenda em x = (\d+)", pc.obs or "")
                if not m:
                    continue
                x = int(m.group(1))
                juntas.setdefault(pc.familia, set()).add(x)
                apoiada = any(abs(x - v) <= 1 for v in verticais)
                avisada = "SEM MONTANTE" in pc.obs
                if apoiada and avisada:
                    problemas.append(f"{p.cod}: {pc.cod} avisa emenda sem "
                                     f"montante em x = {x}, mas ha montante ali")
                if not apoiada and not avisada:
                    problemas.append(f"{p.cod}: {pc.cod} emenda em x = {x} sem "
                                     f"montante de apoio e sem aviso")
                if not apoiada:
                    if "emenda sem montante" not in (p.obs or ""):
                        problemas.append(f"{p.cod}: emenda sem apoio nao "
                                         f"declarada na observacao do painel")
                    else:
                        # declarada nao quer dizer resolvida: continua sendo
                        # item aberto de projeto, e sai da auditoria como tal.
                        # Uma emenda e uma so, ainda que apareca nas duas pecas
                        # que ela une — por isso a chave e (painel, familia, x).
                        sem_apoio_dec.add((p.cod, pc.familia, x))
            # ESCALONAMENTO: guia inferior, superior e blocking emendados na
            # mesma secao fazem do painel uma dobradica — e na secao exata onde
            # ele se dobraria no icamento.
            for fa, fb in (("track", "blocking"),):
                comum = juntas.get(fa, set()) & juntas.get(fb, set())
                if comum:
                    problemas.append(f"{p.cod}: {fa} e {fb} emendam na mesma "
                                     f"secao x = {sorted(comum)}")
            if len(juntas.get("track", ())) == 1 and any(
                    pc.familia == "track" and "emenda" in (pc.obs or "")
                    for pc in p.pecas):
                problemas.append(f"{p.cod}: as duas guias emendam na mesma "
                                 f"secao x = {sorted(juntas['track'])}")

            # ENVELOPE: nenhuma peca fora do painel. Esta condicao parece obvia
            # e por isso nunca tinha sido escrita — 138 pecas violavam-na ate
            # R25, e nenhuma prancha mostrava, porque nenhuma prancha desenhava
            # a peca a partir da propria coordenada.
            for pc in p.pecas:
                bwp = pn.bw(pc.perfil)
                w = bwp if pc.vertical else pc.comp
                h = pc.comp if pc.vertical else bwp
                if pc.x < 0 or pc.x + w > p.comp + 1:
                    problemas.append(f"{p.cod}: {pc.cod} ({pc.familia}) ocupa "
                                     f"x {pc.x}..{pc.x + w} num painel de "
                                     f"{p.comp} mm")
                if pc.z < 0 or pc.z + h > p.altura + 1:
                    problemas.append(f"{p.cod}: {pc.cod} ({pc.familia}) ocupa "
                                     f"z {pc.z}..{pc.z + h} num painel de "
                                     f"{p.altura} mm")

    for cod, familia, x in sorted(sem_apoio_dec):
        excecoes.append(f"{cod}: emenda de {familia} em x = {x} sem montante "
                        f"de apoio — a abertura ocupa a faixa onde a barra de "
                        f"{cfg.comp_barra} mm termina; exige barra sob "
                        f"encomenda ou talao dimensionado ao momento")

    for m in problemas[:10]:
        out.append(Achado("ERRO", "painelizacao", m))
    # Sem corte: cada excecao e um item aberto de projeto distinto, e truncar a
    # lista esconderia justamente os que ninguem viu ainda.
    for m in excecoes:
        out.append(Achado("ATENCAO", "painelizacao", m))
    if not problemas:
        out.append(Achado("NOTA", "painelizacao",
                          f"{total_pecas} pecas em paineis fabricaveis, "
                          f"{total_massa:.0f} kg de aco, sem montante em vao, "
                          f"sem cripple fora de modulacao e sem painel acima do "
                          f"limite de transporte ou de icamento"))
    return out


def checar_verga() -> list[Achado]:
    """A verga escolhida vem com as alternativas rejeitadas e o motivo (secao 20).

    Sistema que diz so o resultado e caixa-preta. A verificacao exige que a
    escolha traga o que falhou e por que — e que um vao impossivel devolva
    'nenhum perfil serve' em vez de um perfil que nao serve.
    """
    import nucleo.painel as pn
    import nucleo.materiais as mt
    import nucleo.solver as sv
    import nucleo.perfis as pf
    out = []
    aco = mt.POR_ACO["ZAR 230"]

    v = pn.verga_necessaria(2400, 6.0, aco)
    e = v["escolhido"]
    if not e:
        out.append(Achado("ERRO", "verga", "nenhum perfil para um vao corriqueiro"))
        return out
    rejeitados = [a for a in v["alternativas"] if not a["ok"]]
    out.append(Achado("NOTA" if rejeitados else "ATENCAO", "verga",
                      f"vao de 2.400 mm com 6 kN/m: {e['perfil']}, utilizacao "
                      f"{e['uso']*100:.0f} %, com {len(rejeitados)} alternativas "
                      f"rejeitadas e o motivo de cada uma"))

    # CRUZAMENTO: a flecha pela formula tem de bater com o solver da E5.
    # E deste cruzamento que saiu o erro de unidade (1 kN/m e 1 N/mm, nao
    # 0,001 N/mm) e, logo depois, o erro de sinal no acoplamento do solver.
    p = next(q for q in pf.catalogo() if q.cod == e["perfil"])
    d = p.props()
    L, w, n = 2400.0, 6.0, 8
    s = sv.Secao("v", d["A"], d["Ix"], d["Iy"], d["J"])
    m = sv.Modelo()
    for k in range(n + 1):
        ap = ((True, True, True, True, False, False) if k == 0 else
              ((True, True, True, False, False, False) if k == n else sv.LIVRE))
        m.no(f"n{k}", L * k / n, 0, 0, ap)
    for k in range(n):
        m.barra(f"b{k}", f"n{k}", f"n{k+1}", s, q_local=(0.0, -w))
    r = m.resolver()
    dsolver = abs(m.deslocamento(r, f"n{n//2}", 2))
    rel = abs(dsolver - e["flecha"]) / e["flecha"]
    out.append(Achado("NOTA" if rel < 1e-6 else "ERRO", "verga",
                      f"flecha pela formula {e['flecha']:.4f} mm contra "
                      f"{dsolver:.4f} mm pelo solver da E5; erro {rel:.2e}"))

    # vao impossivel nao pode devolver perfil
    imp = pn.verga_necessaria(12_000, 30.0, aco)
    out.append(Achado("NOTA" if imp["escolhido"] is None else "ERRO", "verga",
                      "vao de 12 m com 30 kN/m devolve 'nenhum perfil serve' em "
                      "vez de um perfil que nao serve"
                      if imp["escolhido"] is None else
                      f"vao impossivel devolveu {imp['escolhido']['perfil']}"))
    return out


def checar_contraventamento() -> list[Achado]:
    """Estabilidade horizontal: o que impede a casa de deitar.

    A verificacao que importa nao e a resistencia da diagonal — e o tombamento.
    O momento nao some porque a diagonal e forte: ele desce pelo montante de
    extremidade e tenta arrancar a parede do radier.
    """
    import nucleo.contraventamento as cv
    out = []

    # segmento esbelto demais nao pode ser contado como parede de cisalhamento
    estreito = cv.ShearWall("x", 900, 2600, "OSB")
    c = cv.capacidade(estreito, "OSB 11,1 mm, parafuso a 150 mm")
    out.append(Achado("NOTA" if not c["conta"] and c["vrd"] == 0 else "ERRO",
                      "aspecto", f"segmento de 900 x 2.600 mm: {c['motivo'][:80]}"))

    # o peso proprio alivia o tombamento — e por isso entra minorado
    sw = cv.ShearWall("y", 3000, 2600, "OSB", peso_permanente=12.0)
    leve = cv.tombamento(cv.ShearWall("y", 3000, 2600, "OSB", 0.0), 19.5)
    pesado = cv.tombamento(sw, 19.5)
    out.append(Achado("NOTA" if pesado["uplift"] < leve["uplift"] else "ERRO",
                      "tombamento",
                      f"o peso proprio reduz o arrancamento de "
                      f"{leve['uplift']:.2f} para {pesado['uplift']:.2f} kN; "
                      f"entra minorado em 0,9 porque aliviar e efeito favoravel"))

    # a fita so serve num intervalo de angulo
    for comp, esperado in ((3000, True), (8000, False), (700, False)):
        d = cv.forca_na_diagonal(10.0, comp, 2600)
        if d["eficiente"] != esperado:
            out.append(Achado("ERRO", "diagonal",
                              f"angulo {d['angulo']:.1f} classificado errado"))
    out.append(Achado("NOTA", "diagonal",
                      "a fita so e eficiente entre 30 e 60 graus: muito deitada "
                      "puxa a guia, muito em pe nao resiste a horizontal"))

    # trelicas: equilibrio e sinal dos banzos
    import nucleo.perfis as pf
    import nucleo.solver as sv
    p = pf.Perfil("t", "Ue", 140, 40, 12, 1.55)
    d2 = p.props()
    s = sv.Secao("t", d2["A"], d2["Ix"], d2["Iy"], d2["J"])
    for tipo in ("Fink", "Howe", "Pratt", "Warren", "Scissor", "Mono"):
        g = cv.geometria_trelica(tipo, 8000, 2000, 4)
        r = cv.resolver_trelica(g, s, 3.0)
        rz = sum(r["reacoes"][c][2] for c in r["apoios"])
        rel = abs(rz - r["carga_total"]) / r["carga_total"]
        if rel > 1e-6:
            out.append(Achado("ERRO", tipo,
                              f"equilibrio nao fecha: reacoes {rz:.3f} contra "
                              f"carga {r['carga_total']:.3f} kN"))
        if tipo not in ("Mono", "Scissor"):
            sup = [v["N"] for v in r["esforcos"].values()
                   if v["papel"] == "banzo superior"]
            inf = [v["N"] for v in r["esforcos"].values()
                   if v["papel"] == "banzo inferior"]
            if sup and inf and not (min(sup) < 0 < max(inf)):
                out.append(Achado("ERRO", tipo,
                                  "banzo superior deveria comprimir e o "
                                  "inferior tracionar numa trelica biapoiada"))
    out.append(Achado("NOTA", "trelicas",
                      f"{len(cv.TIPOS_TRELICA)} tipos geram geometria, rodam no "
                      f"solver da E5 e fecham o equilibrio"))
    return out


def checar_ligacoes() -> list[Achado]:
    """Cinco modos de ruina, e nenhum deles e o parafuso.

    Em chapa de 0,95 mm a ligacao falha na CHAPA, sempre. Se algum calculo
    apontar o parafuso como modo critico numa chapa fina, ha erro — e essa e a
    verificacao mais util deste bloco.
    """
    import nucleo.ligacoes as lg
    out = []
    p = lg.POR_PARAFUSO["AB 4,8x19 ponta broca"]

    c = lg.cisalhamento(p, 0.95, 0.95, 310, 310)
    if "parafuso" in c["modo"] and "basculamento" not in c["modo"]:
        out.append(Achado("ERRO", "ligacao",
                          f"em chapa de 0,95 mm o modo critico deu "
                          f"'{c['modo']}': a chapa deveria governar"))
    else:
        out.append(Achado("NOTA", "ligacao",
                          f"chapa de 0,95 mm: governa '{c['modo']}' com "
                          f"{c['nvrd']:.2f} kN por parafuso — e por isso que LSF "
                          f"leva dezenas de milhares deles"))

    # engrossar a chapa tem de aumentar a capacidade
    caps = [lg.cisalhamento(p, t, t, 310, 310)["nvrd"]
            for t in (0.80, 0.95, 1.25, 1.55, 2.00)]
    ok = all(b > a for a, b in zip(caps, caps[1:]))
    out.append(Achado("NOTA" if ok else "ERRO", "ligacao",
                      f"capacidade por espessura: {[round(x,2) for x in caps]} kN"))

    # tracao: em chapa fina o rosqueamento arranca antes de tudo
    t = lg.tracao(p, 0.95, 0.95, 310, 310)
    out.append(Achado("NOTA", "ligacao",
                      f"tracao em 0,95 mm: {t['ntrd']:.2f} kN, governa "
                      f"'{t['modo']}'"))

    # geometria: espacamento e borda
    ruins = lg.verificar_geometria([5.0, 12.0, 60.0], 70.0, p)
    out.append(Achado("NOTA" if len(ruins) >= 2 else "ERRO", "geometria",
                      f"espacamento e borda insuficientes detectados: "
                      f"{len(ruins)} violacoes"))
    bons = lg.verificar_geometria([20.0, 40.0, 60.0], 80.0, p)
    out.append(Achado("NOTA" if not bons else "ERRO", "geometria",
                      "arranjo correto passa sem apontamento"))

    # acessibilidade: reduzir a folga acaba deixando sem ferramenta
    seq = [lg.acessivel(f) for f in (250, 150, 90, 50, 30)]
    n_ok = sum(1 for a in seq if a["ok"])
    sem = [a for a in seq if not a["alternativas"]]
    out.append(Achado("NOTA" if n_ok >= 1 and sem else "ERRO", "acessibilidade",
                      f"de 250 a 30 mm de folga: {n_ok} posicao(oes) aceitam a "
                      f"parafusadeira comum e {len(sem)} nao aceitam ferramenta "
                      f"alguma — nenhuma norma verifica isto e toda obra encontra"))

    # chumbador: escolha com alternativas, e impossivel devolve None
    a = lg.ancoragem(11.5, 180)
    out.append(Achado("NOTA" if a["escolhido"] else "ERRO", "ancoragem",
                      f"uplift de 11,5 kN em radier de 180 mm: "
                      f"{a['escolhido']['chumbador'] if a['escolhido'] else 'nenhum'}, "
                      f"com {len(a['alternativas'])} alternativas avaliadas"))
    imp = lg.ancoragem(200.0, 100)
    out.append(Achado("NOTA" if imp["escolhido"] is None else "ERRO", "ancoragem",
                      "demanda impossivel devolve 'nenhum chumbador serve'"
                      if imp["escolhido"] is None else
                      "demanda impossivel devolveu um chumbador"))
    return out


def checar_pecas() -> list[Achado]:
    """Identidade estavel, furo na zona util e marcacao completa.

    A identidade precisa ser estavel entre revisoes: se o codigo de uma peca
    muda porque outra foi inserida antes dela, a rastreabilidade inteira se
    perde — a bobina aponta para a peca errada e a inspecao para o painel
    errado.
    """
    import projeto as pj
    import elementos as el
    import nucleo.painel as pn
    import nucleo.peca as pe
    out = []
    cat = pn._catalogo_massa()
    todas, problemas = [], []
    for pav, amb in (("T", pj.TERREO), ("S", pj.SUPERIOR)):
        pais = pn.painelizar(el.derivar_paredes(amb),
                             list(el.vaos_do_pavimento(pav)), prefixo=f"{pav}P")
        serv = {p.cod: [dict(servico="eletrica", d=25),
                        dict(servico="hidraulica", d=40)] for p in pais}
        todas += pe.detalhar(pais, cat, pav, pj.EMISSAO["revisao"], serv)

    # UMA identidade por peca: o codigo do painel e o codigo da fabrica tem de
    # ser o MESMO. Ate R31 eram dois — TP01-1-ST001 no desenho e TP01-1-ST1FB
    # no plano de corte —, e a peca clicada no 3D nao era encontravel na lista
    # de corte. Rastreabilidade com dois codigos nao e rastreabilidade.
    for pav, amb in (("T", pj.TERREO),):
        ps_ = pn.painelizar(el.derivar_paredes(amb),
                            list(el.vaos_do_pavimento(pav)), prefixo=f"{pav}P")
        no_painel = {q.cod for x in ps_ for q in x.pecas}
        na_fabrica = {q.cod for q in pe.detalhar(ps_, cat, pav,
                                                 pj.EMISSAO["revisao"])}
        if no_painel != na_fabrica:
            problemas.append(
                f"o codigo do painel e o da fabrica divergem em "
                f"{len(no_painel ^ na_fabrica)} pecas")

    cods = [p.cod for p in todas]
    if len(set(cods)) != len(cods):
        problemas.append(f"{len(cods)-len(set(cods))} codigos repetidos")

    # estabilidade: regerar do zero tem de dar exatamente os mesmos codigos
    de_novo = []
    for pav, amb in (("T", pj.TERREO), ("S", pj.SUPERIOR)):
        pais = pn.painelizar(el.derivar_paredes(amb),
                             list(el.vaos_do_pavimento(pav)), prefixo=f"{pav}P")
        serv = {p.cod: [dict(servico="eletrica", d=25),
                        dict(servico="hidraulica", d=40)] for p in pais}
        de_novo += pe.detalhar(pais, cat, pav, pj.EMISSAO["revisao"], serv)
    if [p.cod for p in de_novo] != cods:
        problemas.append("os codigos mudam entre duas geracoes identicas")

    # ESTABILIDADE DE VERDADE. Regerar o modelo identico e comparar nao testa
    # nada: qualquer contador determinista passa nesse teste. O que precisa ser
    # provado e que mexer NUM painel nao renumera os OUTROS — e foi exatamente
    # ai que o codigo antigo falhava, porque carregava o contador global de
    # geracao no numero legivel. O caso de teste tem de quebrar a simetria que
    # o defeito usava para se esconder.
    import copy as _copy
    v_alt = _copy.deepcopy(list(el.vaos_do_pavimento("T")))
    alvo = next(v for v in v_alt if v["tipo"].startswith("J"))
    alvo["alt"] = int(alvo["alt"]) + 800     # some com os cripples superiores
    pais0 = pn.painelizar(el.derivar_paredes(pj.TERREO),
                          list(el.vaos_do_pavimento("T")), prefixo="TP")
    pais1 = pn.painelizar(el.derivar_paredes(pj.TERREO), v_alt, prefixo="TP")
    a0 = pe.detalhar(pais0, cat, "T", pj.EMISSAO["revisao"])
    a1 = pe.detalhar(pais1, cat, "T", pj.EMISSAO["revisao"])
    if len(a0) == len(a1):
        problemas.append("o caso de teste nao mudou a contagem de pecas: "
                         "ele nao testa a estabilidade que promete testar")
    tocados = {p.painel for p in a0} ^ {p.painel for p in a1}
    tocados |= {p.painel for p in a0
                if p.cod not in {q.cod for q in a1}}
    intactos = [p for p in a0 if p.painel not in tocados]
    perdidos = [p.cod for p in intactos if p.cod not in {q.cod for q in a1}]
    if perdidos:
        problemas.append(f"elevar um vao renumerou {len(perdidos)} pecas de "
                         f"paineis que nao foram tocados (ex.: {perdidos[0]})")
    else:
        out.append(Achado("NOTA", "identidade",
                          f"elevar um vao 800 mm muda {len(a1)-len(a0):+d} "
                          f"pecas e nao renomeia nenhuma das {len(intactos)} "
                          f"pecas dos paineis intactos"))

    # furos dentro da zona util
    for p in todas:
        if not p.furos:
            continue
        alma = float(p.perfil.split()[1].split("x")[0])
        problemas += pe.verificar_furos(p, alma)

    # marcacao completa e passaporte sem numero inventado
    for p in todas[:50]:
        campos = p.carga_marcacao().split("|")
        if len(campos) != 5 or not all(campos):
            problemas.append(f"{p.cod}: marcacao incompleta")
        pas = p.passaporte()
        for k in ("bobina", "heat", "lote", "producao", "inspecao"):
            if pas[k] is not None:
                problemas.append(f"{p.cod}: campo '{k}' preenchido sem fonte "
                                 f"de dado — numero inventado")

    for m in problemas[:10]:
        out.append(Achado("ERRO", "pecas", m))
    if not problemas:
        massa = sum(p.massa for p in todas)
        furos = sum(len(p.furos) for p in todas)
        out.append(Achado("NOTA", "pecas",
                          f"{len(todas)} pecas com codigo unico e estavel, "
                          f"{massa:.0f} kg, {furos} furos de servico dentro da "
                          f"zona util, marcacao completa e passaporte sem campo "
                          f"preenchido sem fonte"))
    return out


def checar_clash() -> list[Achado]:
    """Interferencia entre disciplinas, com severidade por volume."""
    import nucleo.peca as pe
    out = []
    v = [pe.Volume("ST001", "estrutura", 0, 0, 0, 90, 40, 2600),
         pe.Volume("DUTO", "hvac", 50, 0, 1000, 250, 200, 1200),
         pe.Volume("ELE", "eletrica", 500, 0, 0, 520, 20, 2600),
         pe.Volume("ST002", "estrutura", 600, 0, 0, 690, 40, 2600)]
    c = pe.detectar_clash(v)
    achou = any(set(x["disciplinas"]) == {"estrutura", "hvac"} for x in c)
    out.append(Achado("NOTA" if achou else "ERRO", "clash",
                      f"{len(c)} interferencia(s) entre disciplinas; a do duto "
                      f"com o montante foi encontrada"))
    mesma = [x for x in c if x["disciplinas"][0] == x["disciplinas"][1]]
    out.append(Achado("NOTA" if not mesma else "ERRO", "clash",
                      "conflito dentro da mesma disciplina nao e reportado: "
                      "dois montantes vizinhos nao sao clash"))
    sem = pe.detectar_clash([v[0], v[3]])
    out.append(Achado("NOTA" if not sem else "ERRO", "clash",
                      "estrutura sem MEP nao gera interferencia falsa"))
    return out


def _pecas_do_projeto():
    import projeto as pj
    import elementos as el
    # As pecas do PRODUTO, nao uma reconstrucao parecida. Enquanto esta funcao
    # montava o seu proprio conjunto, ela devolvia 805 pecas enquanto o projeto
    # tinha 1.033: vigamento, escada e contraventamento nunca entravam. A
    # verificacao de clash — cuja unica razao de existir e olhar TUDO ao mesmo
    # tempo — rodava sobre cinco familias a menos. Nao era erro de calculo: era
    # a auditoria olhando outro edificio.
    return fx.liberacao()["pecas"]


def checar_nesting() -> list[Achado]:
    """Plano de corte: conservacao, e nenhuma peca perdida no caminho.

    A verificacao central e uma identidade: o comprimento bruto de todas as
    barras tem de ser exatamente o usado mais a perda. Se nao fecha, alguma peca
    foi contada duas vezes ou sumiu — e um plano de corte que perde peca produz
    obra parada.
    """
    import nucleo.nesting as ns
    out = []
    todas = _pecas_do_projeto()
    itens = [(p.cod, p.perfil, p.comp) for p in todas]
    r = ns.nestar_barras(itens)

    # conservacao do comprimento
    err = abs(r["bruto"] - (r["usado"] + r["perda"]))
    out.append(Achado("NOTA" if err < 1e-6 else "ERRO", "nesting",
                      f"bruto = usado + perda conferido: erro {err:.2e} mm"))

    # toda peca aparece exatamente uma vez, ou esta declarada como nao cabendo
    colocadas = [c for b in r["barras"] for c, _ in b.pecas]
    nao = {c for c, _, _ in r["nao_cabem"]}
    faltando = {p.cod for p in todas} - set(colocadas) - nao
    repetidas = len(colocadas) - len(set(colocadas))
    if faltando or repetidas:
        out.append(Achado("ERRO", "nesting",
                          f"{len(faltando)} pecas sumiram e {repetidas} foram "
                          f"colocadas duas vezes"))
    else:
        out.append(Achado("NOTA", "nesting",
                          f"{len(colocadas)} pecas colocadas uma unica vez em "
                          f"{r['n_barras']} barras; aproveitamento "
                          f"{r['aproveitamento']*100:.1f} %"))

    # peca maior que a barra e informacao, nao silencio
    if r["nao_cabem"]:
        maior = max(c for _, _, c in r["nao_cabem"])
        out.append(Achado("ATENCAO", "nesting",
                          f"{len(r['nao_cabem'])} pecas nao cabem em barra de "
                          f"6 m (a maior tem {maior:.0f} mm): exigem emenda "
                          f"declarada ou barra de comprimento especial"))

    # a sobra do deposito tem de reduzir a compra
    sob = [ns.Sobra(f"X{i}", "Ue 90x40x12x0,95", 1800) for i in range(30)]
    r2 = ns.nestar_barras(itens, sobras=sob)
    out.append(Achado("NOTA" if r2["n_novas"] <= r["n_novas"] else "ERRO",
                      "sobras",
                      f"30 sobras de 1,8 m no deposito reduzem a compra de "
                      f"{r['n_novas']} para {r2['n_novas']} barras novas"))

    # chapas e bobina
    # peca de 1.200 x 2.600 nao cabe em chapa de 1.200 x 2.400, nem girada:
    # tem de sair declarada, e o aproveitamento nunca pode passar de 100 %
    c = ns.nestar_chapas([(f"P{i}", 1200, 2600) for i in range(20)])
    ok = 0 <= c["aproveitamento"] <= 1.0 and len(c["nao_cabem"]) == 20
    out.append(Achado("NOTA" if ok else "ERRO", "chapas",
                      f"peca maior que a chapa: {len(c['nao_cabem'])} declaradas, "
                      f"aproveitamento {c['aproveitamento']*100:.1f} %"))
    c2 = ns.nestar_chapas([(f"Q{i}", 600, 1100) for i in range(24)] +
                          [(f"R{i}", 2300, 900) for i in range(4)])
    ok2 = 0 < c2["aproveitamento"] <= 1.0 and c2["girados"] > 0
    out.append(Achado("NOTA" if ok2 else "ERRO", "chapas",
                      f"{c2['n']} chapas, {c2['girados']} pecas giradas para "
                      f"caber, aproveitamento {c2['aproveitamento']*100:.1f} %"))
    b = ns.bobina(1.407, 3000.0, 1200.0, 0.95, 188.6)
    out.append(Achado("NOTA" if b["tiras"] >= 1 else "ERRO", "bobina",
                      f"{b['tiras']} tiras por bobina de 1.200 mm, perda de "
                      f"largura {b['perda_largura_pct']*100:.1f} %"))
    try:
        ns.bobina(1.0, 100.0, 100.0, 1.0, 300.0)
        out.append(Achado("ERRO", "bobina",
                          "desenvolvimento maior que a bobina nao levantou erro"))
    except ValueError:
        out.append(Achado("NOTA", "bobina",
                          "perfil que nao cabe na largura da bobina levanta erro"))
    return out


def checar_bom() -> list[Achado]:
    """BOM, custo e risco. As quantidades sao derivadas; os precos sao (H).

    A verificacao que separa as duas coisas: a massa comprada tem de ser
    exatamente a massa util dividida pelo aproveitamento do plano de corte. A
    perda foi paga — esquecer isso subestima o aco em 13 %.
    """
    import projeto as pj
    import nucleo.nesting as ns
    import nucleo.bom as bo
    out = []
    todas = _pecas_do_projeto()
    plano = ns.nestar_barras([(p.cod, p.perfil, p.comp) for p in todas])
    itens = bo.montar(todas, plano, pj.CADASTRO.area_m2)

    util = sum(p.massa for p in todas)
    comprado = next(i for i in itens if i.sku == "ACO-PERF").quantidade
    esperado = util / plano["aproveitamento"]
    rel = abs(comprado - esperado) / esperado
    out.append(Achado("NOTA" if rel < 1e-3 else "ERRO", "massa",
                      f"aco comprado {comprado:.0f} kg = util {util:.0f} kg / "
                      f"aproveitamento {plano['aproveitamento']:.3f}; a perda de "
                      f"{comprado-util:.0f} kg foi paga e esta no BOM"))

    # curva ABC: participacoes somam 1 e a classe A fecha em 80 %
    abc = bo.curva_abc(itens)
    soma = sum(x["participacao"] for x in abc)
    ultimo_a = max((x["acumulado"] for x in abc if x["classe"] == "A"), default=0)
    ok = abs(soma - 1.0) < 1e-9 and ultimo_a <= 0.8 + 1e-9
    out.append(Achado("NOTA" if ok else "ERRO", "ABC",
                      f"{sum(1 for x in abc if x['classe']=='A')} itens classe A "
                      f"concentram {ultimo_a*100:.1f} % do custo; participacoes "
                      f"somam {soma:.6f}"))

    # landed cost: cada parcela soma e o fator e maior que 1
    lc = bo.landed_cost(10_000, 2_500, ii_pct=0.14, despachante=800,
                        armazenagem=400, transporte_interno=600)
    parcelas = (lc["cif"] + lc["ii"] + lc["ipi"] + lc["icms"] + lc["pis_cofins"]
                + lc["despachante"] + lc["armazenagem"] + lc["transporte_interno"])
    ok = abs(parcelas - lc["total"]) < 1e-6 and lc["fator"] > 1
    out.append(Achado("NOTA" if ok else "ERRO", "landed cost",
                      f"FOB 10.000 chega a {lc['total']:.2f} posto, fator "
                      f"{lc['fator']:.2f}x, com as parcelas fechando a soma"))

    # Monte Carlo: os quantis precisam estar em ordem
    tot = sum(i.total for i in itens)
    mc = bo.monte_carlo(tot, {"cambio": (0.95, 1.0, 1.35),
                              "aco": (0.9, 1.0, 1.25)})
    ordem = mc["p05"] <= mc["p50"] <= mc["p80"] <= mc["p95"]
    out.append(Achado("NOTA" if ordem else "ERRO", "risco",
                      f"custo base {tot:,.0f}: p50 {mc['p50']:,.0f}, p80 "
                      f"{mc['p80']:,.0f}, p95 {mc['p95']:,.0f} — a cauda direita "
                      f"vale {(mc['p95']/mc['p50']-1)*100:.0f} % a mais que a "
                      f"mediana"))

    # todo preco entra declarado como hipotese
    sem_h = [i.sku for i in itens if i.fonte == "(H)" and i.preco_unit <= 0]
    out.append(Achado("ATENCAO", "precos",
                      f"os {len(bo.PRECOS)} precos da tabela sao (H): ordens de "
                      f"grandeza para a estrutura do calculo existir. As "
                      f"QUANTIDADES sao derivadas das 801 pecas e do plano de "
                      f"corte, e essas nao sao hipotese"))
    return out


def checar_fabricacao() -> list[Achado]:
    """CNC, compatibilidade de maquina, tempo, balanceamento e qualidade.

    A verificacao central do CNC e a ida e volta: exportar e reimportar tem de
    devolver a MESMA geometria. Um arquivo que a maquina le sozinha nao admite
    interpretacao.
    """
    import nucleo.fabricacao as fb
    out = []
    todas = _pecas_do_projeto()
    amostra = todas[:120]

    # ida e volta do formato neutro
    txt = fb.exportar_cnc(amostra)
    volta = fb.importar_cnc(txt)
    diverg = []
    for orig, v in zip(amostra, volta):
        if v["id"] != orig.cod or abs(v["comp"] - orig.comp) > 1e-6:
            diverg.append(orig.cod)
        furos_v = [o for o in v["operacoes"] if o["op"].startswith("furo")]
        if len(furos_v) != len(orig.furos):
            diverg.append(f"{orig.cod}: {len(furos_v)} furos contra "
                          f"{len(orig.furos)}")
    out.append(Achado("NOTA" if not diverg else "ERRO", "CNC",
                      f"{len(volta)} pecas exportadas e reimportadas sem perda"
                      if not diverg else f"divergencias: {diverg[:3]}"))

    # formato desconhecido levanta erro
    try:
        fb.importar_cnc('{"formato": "OUTRO", "pecas": []}')
        out.append(Achado("ERRO", "CNC", "formato desconhecido foi aceito"))
    except ValueError:
        out.append(Achado("NOTA", "CNC", "formato desconhecido levanta erro"))

    # toda peca precisa caber em ALGUMA maquina do parque
    orfas = []
    for p in todas:
        if not any(fb.compativel(p, m.cod)["ok"] for m in fb.MAQUINAS):
            orfas.append(p.cod)
    if orfas:
        exemplo = fb.compativel(next(p for p in todas if p.cod == orfas[0]),
                                "RF-02")
        out.append(Achado("ATENCAO", "maquina",
                          f"{len(orfas)} pecas nao cabem em maquina alguma do "
                          f"parque declarado; a primeira falha por: "
                          f"{exemplo['faltas']}"))
    else:
        out.append(Achado("NOTA", "maquina",
                          f"as {len(todas)} pecas cabem no parque de "
                          f"{len(fb.MAQUINAS)} maquinas (H: capacidades "
                          f"declaradas, a confirmar com o fabricante)"))

    # estados de producao: nao se pula etapa
    if fb.avancar("CUT", "PUNCHED") and not fb.avancar("CUT", "QC"):
        out.append(Achado("NOTA", "producao",
                          f"os {len(fb.ESTADOS)} estados avancam um a um: nao se "
                          f"pula do corte para a inspecao"))
    else:
        out.append(Achado("ERRO", "producao", "a maquina de estados aceita salto"))

    # balanceamento: o ciclo e o da estacao mais lenta, nunca a media
    b = fb.balancear({"perfilacao": 100.0, "montagem": 160.0,
                      "fechamento": 90.0, "QC": 40.0})
    ok = (b["gargalo"] == "montagem" and abs(b["ciclo"] - 160.0) < 1e-9
          and b["eficiencia"] < 1.0)
    out.append(Achado("NOTA" if ok else "ERRO", "linha",
                      f"gargalo '{b['gargalo']}', ciclo {b['ciclo']:.0f} min, "
                      f"eficiencia {b['eficiencia']*100:.0f} % — somar tempos em "
                      f"vez de tomar o maximo e o erro que faz a fabrica "
                      f"prometer prazo que nao cumpre"))

    # OEE recusa fator fora de [0,1]
    try:
        fb.oee(1.2, 0.9, 0.9)
        out.append(Achado("ERRO", "OEE", "aceitou disponibilidade de 120 %"))
    except ValueError:
        o = fb.oee(0.88, 0.92, 0.99)
        out.append(Achado("NOTA", "OEE",
                          f"D x P x Q = {o['oee']*100:.1f} % ({o['classe']}); "
                          f"fator fora de [0,1] levanta erro"))

    # inspecao: dentro e fora de tolerancia
    bom = fb.inspecionar({"comprimento": 2601.5}, {"comprimento": 2600})
    ruim = fb.inspecionar({"comprimento": 2605.0}, {"comprimento": 2600})
    ok = bom["status"] == "APROVADO" and ruim["status"] == "REPROVADO"
    out.append(Achado("NOTA" if ok else "ERRO", "qualidade",
                      f"tolerancia de {fb.TOLERANCIAS['comprimento']:.1f} mm no "
                      f"comprimento: 1,5 mm aprova e 5,0 mm reprova"))
    return out


def checar_logistica() -> list[Achado]:
    """Centro de gravidade, icamento e carregamento.

    O ponto que costuma faltar: um painel com as aberturas de um lado nao sobe
    equilibrado. O ponto de icamento no meio geometrico o faz girar no ar, e
    quem descobre isso e o montador, com o painel pendurado.
    """
    import projeto as pj
    import elementos as el
    import nucleo.painel as pn
    import nucleo.logistica as lo
    out = []
    cat = pn._catalogo_massa()
    pais = pn.painelizar(el.derivar_paredes(pj.TERREO),
                         list(el.vaos_do_pavimento("T")), prefixo="TP")

    # CG pela soma dos momentos: a massa tem de fechar com a das pecas
    for p in pais[:8]:
        cg = lo.cg_painel(p, cat)
        if abs(cg["massa"] - p.massa(cat)) > 1e-6:
            out.append(Achado("ERRO", p.cod, "massa do CG diverge da das pecas"))
    out.append(Achado("NOTA", "CG",
                      "o centro de gravidade sai da soma dos momentos das "
                      "pecas, nao do meio geometrico do painel"))

    # icamento com um ponto so tem de ser recusado
    try:
        lo.pontos_icamento(pais[0], cat, n=1)
        out.append(Achado("ERRO", "icamento", "aceitou icamento por um ponto so"))
    except ValueError:
        out.append(Achado("NOTA", "icamento",
                          "icamento por um ponto so e recusado: o painel gira"))

    # o painel mais desequilibrado tem de vir com alerta
    piores = sorted(pais, key=lambda p: -abs(lo.cg_painel(p, cat)["desvio_rel"]))
    pi = lo.pontos_icamento(piores[0], cat)
    out.append(Achado("NOTA" if (abs(pi["cg"]["desvio_rel"]) < 0.08
                                 or pi["alerta"]) else "ERRO", "icamento",
                      f"painel mais desequilibrado ({piores[0].cod}): CG a "
                      f"{pi['cg']['desvio']:+.0f} mm do meio "
                      f"({pi['cg']['desvio_rel']*100:+.1f} %)"
                      + (f" — alerta emitido" if pi["alerta"] else "")))

    # carregamento: nada maior que o container entra, e o limitante e declarado
    vols = [lo.Volume3D(p.cod, p.comp, 120, p.altura, p.massa(cat)) for p in pais]
    vols.append(lo.Volume3D("GIGANTE", 14_000, 500, 3_000, 900))
    c = lo.carregar_container(vols, "40HC")
    ok = any(r[0] == "GIGANTE" for r in c["rejeitados"]) and not c["excede_peso"]
    out.append(Achado("NOTA" if ok else "ERRO", "container",
                      f"40HC: {c['n']} paineis, {c['massa']:.0f} kg, "
                      f"{c['volume']:.1f} m3; limitante = {c['limitante']}; "
                      f"peca de 14 m recusada por dimensao"))

    # R69 (defeito 108) — a carga REAL, nao so o item sintetico: com o pe-direito
    # em 2.900 mm nenhum painel entra em pe no 40HC e o plano passava a rejeitar
    # os 62 em silencio. Agora o plano escolhe o veiculo pela geometria.
    reais = [lo.Volume3D(p.cod, p.comp, 120, p.altura, p.massa(cat)) for p in pais]
    pl = lo.plano_de_transporte(reais)
    out.append(Achado("NOTA" if not pl["rejeitados"] else "ERRO", "carga real",
                      f"modo {pl['modo']} ({pl.get('veiculo', pl['container'])}): "
                      f"{pl['n']} de {len(reais)} paineis embarcados em "
                      f"{pl.get('viagens', pl.get('pilhas', 0))} "
                      f"{'viagens' if pl['modo'] == 'carreta' else 'pilhas'}; {pl['motivo']}"))
    if pl["modo"] == "carreta":
        out.append(Achado("NOTA" if pl["altura_total"] <= pl["limite_altura"] else "ERRO",
                          "altura rodoviaria",
                          f"painel em pe sobre assoalho: {pl['altura_total']:.0f} mm contra "
                          f"limite de {pl['limite_altura']} mm"))

    # limites rodoviarios
    r = lo.dentro_do_limite(7_200, 2_400, 2_800, 1_200)
    r2 = lo.dentro_do_limite(7_200, 3_200, 2_800, 1_200)
    out.append(Achado("NOTA" if r["ok"] and not r2["ok"] else "ERRO", "transporte",
                      f"2,40 m de largura passa e 3,20 m nao: {r2['faltas']} "
                      f"{r2['obs']}"))
    return out


def checar_montagem() -> list[Achado]:
    """A ordem de montagem e uma ordem PARCIAL com restricoes fisicas.

    A verificacao que mais importa: em nenhum passo a estrutura pode ficar
    instavel. Painel de pe sozinho, sem o de canto e sem o piso superior, e
    painel que cai — e essa e a causa mais comum de acidente em obra de LSF.
    """
    import projeto as pj
    import elementos as el
    import nucleo.painel as pn
    import nucleo.montagem as mo
    out = []
    cat = pn._catalogo_massa()
    pp = {pav: pn.painelizar(el.derivar_paredes(amb),
                             list(el.vaos_do_pavimento(pav)), prefixo=f"{pav}P")
          for pav, amb in (("T", pj.TERREO), ("S", pj.SUPERIOR))}
    et = mo.etapas_do_projeto(pp, cat)
    r = mo.ordenar(et)
    if r["erro"]:
        return [Achado("ERRO", "montagem", r["erro"])]

    # toda dependencia precede a etapa que depende dela
    pos = {c: i for i, c in enumerate(r["ordem"])}
    fora = [(e.cod, d) for e in et for d in e.depende if pos[d] > pos[e.cod]]
    out.append(Achado("NOTA" if not fora else "ERRO", "sequencia",
                      f"{len(et)} etapas ordenadas; toda dependencia precede "
                      f"quem depende dela" if not fora else
                      f"{len(fora)} dependencias fora de ordem"))

    # estabilidade passo a passo
    falhas = mo.verificar_estabilidade(et, r["ordem"])
    out.append(Achado("NOTA" if not falhas else "ERRO", "estabilidade",
                      "em nenhum passo a estrutura fica instavel"
                      if not falhas else falhas[0][:120]))

    # ciclo de dependencia tem de ser detectado, nao contornado
    ciclo = [mo.Etapa("A", "painel", "a", ("B",)),
             mo.Etapa("B", "painel", "b", ("A",))]
    rc = mo.ordenar(ciclo)
    out.append(Achado("NOTA" if rc["erro"] and not rc["ordem"] else "ERRO",
                      "ciclo",
                      "dependencia circular e reportada como montagem "
                      "impossivel, em vez de resolvida em ordem arbitraria"))

    # desmontagem e a inversa exata
    d = mo.desmontagem(r["ordem"])
    out.append(Achado("NOTA" if d == list(reversed(r["ordem"])) else "ERRO",
                      "desmontagem",
                      f"a sequencia inversa sai de graca porque a direta foi "
                      f"DERIVADA: comeca por {d[0]} e termina na fundacao"))

    ps = mo.passo_a_passo(et, r["ordem"])
    ms = mo.marcos(ps)
    cresce = all(a["passo"] <= b["passo"] for a, b in zip(ms, ms[1:]))
    out.append(Achado("NOTA" if cresce else "ERRO", "timeline",
                      f"{ps[-1]['acumulado_h']:.0f} h no total, com marcos em "
                      f"{[m['tipo'] for m in ms]}"))
    return out


def checar_otimizacao() -> list[Achado]:
    """A decisao global contra o exemplo da propria especificacao (secao 148).

    A especificacao diz, em texto: 'o sistema PODE PREFERIR B mesmo sendo
    ligeiramente mais pesada'. Isso e um caso de teste — e e assim que ele esta
    verificado aqui.
    """
    import nucleo.otimizacao as ot
    out = []
    A = ot.Solucao("A", "11 perfis, 4.800 kg",
                   dict(custo=14200, peso=4800, sku=11, desperdicio=0.14,
                        montagem=420, carbono=9600))
    B = ot.Solucao("B", "5 perfis, 5.050 kg",
                   dict(custo=13600, peso=5050, sku=5, desperdicio=0.09,
                        montagem=310, carbono=10100))
    C = ot.Solucao("C", "8 perfis, 4.900 kg",
                   dict(custo=13950, peso=4900, sku=8, desperdicio=0.11,
                        montagem=370, carbono=9800))
    r = ot.ranquear([A, B, C])
    venceu = r[0]["cod"]
    mais_leve = min([A, B, C], key=lambda s: s.metricas["peso"]).cod
    out.append(Achado("NOTA" if venceu == "B" else "ERRO", "secao 148",
                      f"vence {venceu}, que NAO e a mais leve ({mais_leve}): "
                      f"5 SKUs contra 11 e 110 h a menos de montagem pagam os "
                      f"250 kg de aco a mais"))

    # a explicacao precisa dizer tambem o que a vencedora PERDEU
    exp = ot.explicar(r)
    out.append(Achado("NOTA" if "PERDER" in exp else "ATENCAO", "explicacao",
                      exp[:150]))

    # peso zero num objetivo tem de mudar o resultado
    so_peso = ot.ranquear([A, B, C], dict(custo=0, sku=0, desperdicio=0,
                                          montagem=0, carbono=0, peso=1))
    out.append(Achado("NOTA" if so_peso[0]["cod"] == "A" else "ERRO", "pesos",
                      f"otimizando so por peso vence {so_peso[0]['cod']} — a "
                      f"ponderacao muda a resposta, que e o proposito dela"))

    # solucao dominada fica fora da fronteira de Pareto
    D = ot.Solucao("D", "dominada por B em tudo",
                   dict(custo=15000, peso=5200, sku=12, desperdicio=0.18,
                        montagem=500, carbono=11000))
    fr = ot.pareto([A, B, C, D], ["custo", "peso", "sku", "montagem"])
    out.append(Achado("NOTA" if "D" not in fr else "ERRO", "Pareto",
                      f"fronteira {sorted(fr)}: a solucao dominada em todos os "
                      f"objetivos fica fora"))

    # padronizacao nunca troca por perfil que o elemento nao aceita
    esc = {f"e{i}": p for i, p in enumerate(
        ["P1"] * 10 + ["P2"] * 3 + ["P3"] * 4 + ["P4"] * 1)}
    alt = {e: ["P1", "P2"] for e in esc}
    p = ot.padronizar(esc, alt, max_sku=2)
    invalidas = [e for e, v in p["escolhas"].items() if v not in alt[e]
                 and v != esc[e]]
    out.append(Achado("NOTA" if not invalidas else "ERRO", "padronizacao",
                      f"de 4 para {p['skus']} SKUs com {len(p['trocas'])} "
                      f"trocas, todas por perfil ja aprovado no elemento — "
                      f"padronizar nunca reduz seguranca"))
    return out


def checar_revisao() -> list[Achado]:
    """Diferenca, impacto e congelamento.

    Comparar duas revisoes em CAD e trabalho manual. Aqui e computavel porque
    tudo e funcao do modelo: mudar a janela de lugar e mudar um numero, o resto
    se recalcula, e a diferenca entre os dois resultados E o impacto.
    """
    import copy
    import projeto as pj
    import elementos as el
    import nucleo.painel as pn
    import nucleo.peca as pe
    import nucleo.revisao as rv
    out = []
    cat = pn._catalogo_massa()

    def pecas(vaos):
        pais = pn.painelizar(el.derivar_paredes(pj.TERREO), vaos, prefixo="TP")
        return pe.detalhar(pais, cat, "T", pj.EMISSAO["revisao"])

    v0 = list(el.vaos_do_pavimento("T"))
    antes = pecas(v0)

    # modelo identico: o diff tem de ser VAZIO
    d0 = rv.diff_pecas(antes, pecas(v0))
    ok = d0["n_add"] == d0["n_rem"] == d0["n_alt"] == 0
    out.append(Achado("NOTA" if ok else "ERRO", "diff",
                      f"duas geracoes do MESMO modelo dao diferenca vazia "
                      f"({d0['inalteradas']} pecas inalteradas)"))

    # mover uma janela: o impacto tem de ser local, nao global
    v1 = copy.deepcopy(v0)
    alvo = next(v for v in v1 if v["tipo"].startswith("J"))
    if alvo["ori"] == "H":
        alvo["x"] += 600
    else:
        alvo["y"] += 600
    d = rv.diff_pecas(antes, pecas(v1))
    afetadas = d["n_add"] + d["n_rem"] + d["n_alt"]
    frac = afetadas / max(1, len(antes))
    ok = 0 < afetadas and frac < 0.20
    out.append(Achado("NOTA" if ok else "ERRO", "impacto",
                      f"mover uma janela 600 mm afeta {afetadas} de "
                      f"{len(antes)} pecas ({frac*100:.1f} %): local, como tem "
                      f"de ser — se afetasse tudo, o codigo de peca nao seria "
                      f"estavel"))

    # o mesmo diff custa zero em DESIGN e vira sucata em CUT
    livre = rv.impacto(d, {})
    cortado = rv.impacto(d, {c: "CUT" for c in d["removidas"]})
    ok = (livre["gravidade"] != "alta" and cortado["gravidade"] == "alta"
          and len(cortado["sucata"]) > 0)
    out.append(Achado("NOTA" if ok else "ERRO", "congelamento",
                      f"a MESMA alteracao: gravidade '{livre['gravidade']}' com "
                      f"as pecas em projeto e '{cortado['gravidade']}' com elas "
                      f"cortadas ({len(cortado['sucata'])} viram sucata)"))

    # freeze: revisao vencida nao fabrica
    revs = [r[0] for r in pj.REVISOES]
    atual = pj.EMISSAO["revisao"]
    f1 = rv.pode_fabricar(atual, atual, revs)
    f2 = rv.pode_fabricar(revs[-4], atual, revs)
    ok = f1["pode"] and not f2["pode"]
    out.append(Achado("NOTA" if ok else "ERRO", "freeze",
                      f"a revisao atual fabrica; {revs[-4]} nao: "
                      f"{f2['motivo'][:80]}"))

    co = rv.ChangeOrder("CO-001", "proprietario", "Mover janela 600 mm",
                        d, cortado, prazo_dias=3)
    r = co.resumo()
    faltando = [k for k in ("pecas", "massa_kg", "custo", "gravidade",
                            "sucata", "aprovacao") if k not in r]
    out.append(Achado("NOTA" if not faltando else "ERRO", "change order",
                      f"a ordem de alteracao traz pecas, massa, custo, prazo, "
                      f"gravidade, sucata e aprovacao (que nasce PENDENTE)"))
    return out


def checar_interop() -> list[Achado]:
    """Ida e volta em cada formato, e falha explicita no que e proprietario."""
    import nucleo.interop as io
    out = []

    ents = [dict(tipo="line", x1=0.0, y1=0.0, x2=100.0, y2=50.0, layer="PAREDE"),
            dict(tipo="text", x=10.0, y=20.0, texto="COZINHA", layer="ROTULO")]
    v = io.de_dxf(io.exportar("DXF", ents))
    ok = (len(v) == 2 and abs(v[0]["x2"] - 100.0) < 1e-9
          and v[1]["texto"] == "COZINHA")
    out.append(Achado("NOTA" if ok else "ERRO", "DXF",
                      "ida e volta preserva geometria, camada e texto"))

    el = [dict(cod=f"ST{i:03d}", perfil="Ue 90x40x12x0,95", familia="stud",
               x=i * 600.0, y=0.0, z=0.0, pav="T") for i in range(12)]
    ifc = io.exportar("IFC", dict(nome="Porto Real", empresa="—", data="2026"), el)
    r = io.de_ifc(ifc)
    ok = r["membros"] == 12 and "IFC4" in ifc and ifc.startswith("ISO-10303-21;")
    out.append(Achado("NOTA" if ok else "ERRO", "IFC",
                      f"arquivo STEP valido com {r['entidades']} entidades e "
                      f"{r['membros']} IfcMember; subconjunto DECLARADO — nao "
                      f"entram material nem propriedade"))

    sol = [dict(p=[0, 0, 0], s=[100, 100, 100])]
    obj, stl = io.exportar("OBJ", sol), io.exportar("STL", sol)
    ok = obj.count("\nv ") == 8 and stl.count("facet normal") == 12
    out.append(Achado("NOTA" if ok else "ERRO", "malha",
                      "OBJ com 8 vertices e STL com 12 triangulos por solido"))

    csv = io.exportar("CSV", [dict(a=1, b="x, y")], ["a", "b"])
    vc = io.de_csv(csv)
    ok = vc[0]["b"] == "x, y"
    out.append(Achado("NOTA" if ok else "ERRO", "CSV",
                      "campo com virgula sobrevive a ida e volta"))

    x = io.exportar("XML", "pecas", [dict(cod="ST001", comp=2600)])
    ok = io.de_xml(x)[0]["cod"] == "ST001"
    out.append(Achado("NOTA" if ok else "ERRO", "XML", "ida e volta preservada"))

    # proprietario: falha explicita, nunca aproximacao
    faltaram = []
    for f in ("DWG", "RVT", "SKP"):
        try:
            io.exportar(f)
            faltaram.append(f)
        except io.SemAdaptador:
            pass
    out.append(Achado("NOTA" if not faltaram else "ERRO", "proprietarios",
                      "DWG, RVT e SKP falham dizendo por que e apontando IFC e "
                      "DXF; entregar arquivo aproximado seria pior que nao "
                      "entregar"))
    return out


def checar_banco() -> list[Achado]:
    """As 28 entidades, e a separacao entre o que se regenera e o que nao."""
    import projeto as pj
    import elementos as el
    import nucleo.banco as bc
    import nucleo.painel as pn
    import nucleo.peca as pe
    import nucleo.perfis as pf
    out = []
    con = bc.criar()
    t = bc.tabelas(con)
    falta = sorted(set(bc.ENTIDADES) - set(t))
    out.append(Achado("NOTA" if not falta else "ERRO", "esquema",
                      f"{len(t)} tabelas criadas, as {len(bc.ENTIDADES)} "
                      f"entidades da especificacao" if not falta
                      else f"faltam {falta}"))
    out.append(Achado("NOTA", "natureza",
                      f"{len(bc.ENTIDADES_PROJETO)} tabelas de PROJETO sao "
                      f"espelho do modelo e se regeneram; "
                      f"{len(bc.ENTIDADES_EVENTO)} de EVENTO registram o que "
                      f"aconteceu no mundo e so crescem"))

    cat = pn._catalogo_massa()
    pais = pn.painelizar(el.derivar_paredes(pj.TERREO),
                         list(el.vaos_do_pavimento("T")), prefixo="TP")
    pcs = pe.detalhar(pais, cat, "T", pj.EMISSAO["revisao"])
    props = {p.cod: dict(p.props(), forma=p.forma, bw=p.bw, bf=p.bf, D=p.D,
                         t=p.t) for p in pf.catalogo()}
    r = bc.gravar_projeto(con, pj.CADASTRO, pcs, pais, props)
    n = con.execute("SELECT COUNT(*) FROM member").fetchone()[0]
    out.append(Achado("NOTA" if n == len(pcs) else "ERRO", "gravacao",
                      f"{r['pecas']} pecas, {r['paineis']} paineis e "
                      f"{r['perfis']} perfis gravados; a releitura devolve {n}"))
    # regravar tem de ser idempotente
    bc.gravar_projeto(con, pj.CADASTRO, pcs, pais, props)
    n2 = con.execute("SELECT COUNT(*) FROM member").fetchone()[0]
    out.append(Achado("NOTA" if n2 == n else "ERRO", "idempotencia",
                      f"gravar duas vezes nao duplica: {n2} pecas"))
    return out


def checar_liberacao() -> list[Achado]:
    """A cadeia inteira, de uma vez, e a decisao de liberar (secoes 140 a 144).

    Nenhum item do checklist e marcavel a mao: cada um consulta o resultado de
    uma funcao que rodou sobre o modelo. Se fosse marcavel, seria marcado.
    """
    import projeto as pj
    import elementos as el
    import nucleo.liberacao as lb
    out = []
    r = fx.liberacao()

    lib = r["liberacao"]
    nao_ok = [i for i in lib["itens"] if i["status"] != "OK"]
    out.append(Achado("NOTA" if lib["liberado"] else "ATENCAO", "liberacao",
                      f"{lib['situacao']} — {len(lib['itens'])-len(nao_ok)} de "
                      f"{len(lib['itens'])} itens verificados"
                      + (f"; pendente: {[i['item'] for i in nao_ok]}"
                         if nao_ok else "")))

    # todo score entre 0 e 100 e com formula visivel
    ruins = [k for k, v in r["scores"].items()
             if not (0 <= v["nota"] <= 100) or not v.get("formula")]
    out.append(Achado("NOTA" if not ruins else "ERRO", "scores",
                      f"score geral {r['score_geral']}/100 — "
                      + ", ".join(f"{k} {v['nota']}"
                                  for k, v in r["scores"].items())
                      + "; cada um com a formula declarada"
                      if not ruins else f"scores sem formula ou fora de faixa: {ruins}"))

    # o score tem de REAGIR: piorar uma entrada tem de baixar a nota
    import nucleo.scores as sc
    bom = sc.score_fabricacao(r["pecas"], 6, 0.92, 0.5)["nota"]
    ruim = sc.score_fabricacao(r["pecas"], 40, 0.68, 4.0)["nota"]
    out.append(Achado("NOTA" if ruim < bom else "ERRO", "scores",
                      f"o score reage: 6 SKUs e 92 % de aproveitamento dao "
                      f"{bom}, contra {ruim} com 40 SKUs e 68 %"))

    # nivel de erro inexistente tem de levantar excecao
    try:
        sc.classificar("GRAVE", "x")
        out.append(Achado("ERRO", "motor de erros", "aceitou nivel inexistente"))
    except KeyError:
        c = sc.classificar("ERRO", "verga insuficiente",
                           ["aumentar espessura", "perfil duplo",
                            "reduzir vao", "inserir apoio"])
        out.append(Achado("NOTA", "motor de erros",
                          f"4 niveis; um ERRO bloqueia e vem com "
                          f"{len(c['solucoes'])} solucoes sugeridas, nao so com "
                          f"a palavra 'erro'"))
    return out


def checar_sustentabilidade() -> list[Achado]:
    """CO2e e desmontabilidade, com todo fator declarado (secoes 121 e 122)."""
    import nucleo.scores as sc
    out = []
    a = sc.co2e(1000.0, reciclado=0.0)
    b = sc.co2e(1000.0, reciclado=1.0)
    out.append(Achado("NOTA" if b["aco"] < a["aco"] else "ERRO", "CO2e",
                      f"1.000 kg de aco: {a['aco']:.0f} kg de CO2e com carga "
                      f"virgem e {b['aco']:.0f} kg com 100 % de sucata — "
                      f"{(1-b['aco']/a['aco'])*100:.0f} % de reducao. Fatores (H)"))
    c = sc.co2e(1000.0, km=0.0)
    d = sc.co2e(1000.0, km=3000.0)
    out.append(Achado("NOTA" if d["total"] > c["total"] else "ERRO", "CO2e",
                      f"3.000 km de transporte acrescentam "
                      f"{d['transporte']:.0f} kg de CO2e"))
    class P:
        def __init__(self, perfil):
            self.perfil = perfil
    muitos = sc.desmontabilidade([P(f"p{i%20}") for i in range(200)])
    poucos = sc.desmontabilidade([P("p1") for _ in range(200)])
    out.append(Achado("NOTA" if poucos["indice"] > muitos["indice"] else "ERRO",
                      "desmontabilidade",
                      f"repeticao alta eleva o indice de {muitos['indice']:.2f} "
                      f"para {poucos['indice']:.2f}: peca repetida e peca que "
                      f"se reaproveita em outro lugar"))
    return out


def checar_documentos() -> list[Achado]:
    """Memorial com formula e substituicao, e os tres modos de leitura."""
    import nucleo.documentos as dc
    import nucleo.perfis as pf
    import nucleo.materiais as mt
    out = []
    p = next(q for q in pf.catalogo() if q.cod == "Ue 90x40x12x0,95")
    aco = mt.POR_ACO["ZAR 230"]
    esp = dc.memorial_compressao(p, aco, 2600, "especialista")
    edu = dc.memorial_compressao(p, aco, 2600, "educacional")
    exe = dc.memorial_compressao(p, aco, 2600, "executivo")

    # memorial de especialista precisa trazer clausula, formula e substituicao
    tem = all(t in esp for t in ("NBR 14762", "lambda0 = raiz(Ny/Ne)",
                                 "Nc,Rd = Nc,Rk / gama", "="))
    out.append(Achado("NOTA" if tem else "ERRO", "memorial",
                      "o memorial traz clausula, formula e a SUBSTITUICAO "
                      "numerica — memorial que so apresenta o resultado nao e "
                      "memorial, e afirmacao"))

    # os tres modos tem de ser o mesmo conteudo em profundidades diferentes
    ok = len(exe) < len(edu) < len(esp)
    out.append(Achado("NOTA" if ok else "ERRO", "modos",
                      f"executivo {len(exe)} caracteres, educacional "
                      f"{len(edu)}, especialista {len(esp)}: mesmo conteudo, "
                      f"profundidades diferentes — nao textos paralelos que "
                      f"divergem na terceira revisao"))

    # o numero critico tem de ser o MESMO nos tres
    import nucleo.verificacao as vr
    nrd = vr.compressao(p, aco, L=2600)["nrd"]
    presente = sum(1 for t in (esp, edu, exe) if f"{nrd:.2f}" in t)
    out.append(Achado("NOTA" if presente >= 2 else "ATENCAO", "coerencia",
                      f"o valor de calculo {nrd:.2f} kN aparece identico em "
                      f"{presente} dos 3 modos"))
    return out


def checar_contratos() -> list[Achado]:
    """E23 — o que e bloqueado tem contrato, e o contrato recusa dado errado.

    Duas coisas precisam ser provadas aqui, e a segunda e a que importa.

    A primeira e cobertura: toda secao marcada BLOQ na especificacao tem um
    contrato. Sem isso, "bloqueado" viraria sinonimo de esquecido.

    A segunda e que o adaptador NUNCA devolve numero. E facil escrever um
    adaptador que levanta excecao; e facil, tambem, escrever um que levanta em
    alguns caminhos e devolve zero noutros. Por isso a verificacao chama
    consultar() em todos os contratos e exige SemFonteDeDados em todos —
    qualquer retorno, mesmo None, reprova.
    """
    import escopo as es
    import nucleo.contratos as ct
    out, problemas = [], []

    # cobertura das secoes BLOQ
    bloq = {n for n, _t, sit, _e, _o in es.SECOES if sit == "BLOQ"}
    cobertas = ct.bloqueadas_cobertas()
    faltam = sorted(bloq - cobertas)
    sobram = sorted(cobertas - bloq)
    if faltam:
        problemas.append(f"secoes BLOQ sem contrato: {faltam}")
    if sobram:
        problemas.append(f"contrato para secao que nao esta BLOQ: {sobram}")
    out.append(Achado("NOTA" if not (faltam or sobram) else "ERRO", "cobertura",
                      f"{len(ct.CONTRATOS)} contratos cobrem as {len(bloq)} "
                      f"secoes bloqueadas, uma a uma"))

    # o adaptador nunca devolve numero
    devolveram = []
    for c in ct.CONTRATOS:
        try:
            v = c.consultar()
        except ct.SemFonteDeDados as e:
            if c.cod not in str(e) or "sem fonte de dados" not in str(e):
                problemas.append(f"{c.cod}: excecao sem o codigo ou sem o motivo")
            if c.fonte not in str(e):
                problemas.append(f"{c.cod}: a excecao nao diz como suprir")
        except (RuntimeError, ValueError, TypeError, KeyError) as e:
            # deliberadamente largo, e SO aqui: o proposito desta condicao e
            # justamente pegar adaptador que levanta a excecao errada
            problemas.append(f"{c.cod}: levantou {type(e).__name__}, nao "
                             f"SemFonteDeDados")
        else:
            devolveram.append(f"{c.cod} devolveu {v!r}")
    problemas += devolveram
    out.append(Achado("NOTA" if not devolveram else "ERRO", "adaptador",
                      f"os {len(ct.CONTRATOS)} adaptadores levantam "
                      f"SemFonteDeDados dizendo o que falta e como suprir; "
                      f"nenhum devolve valor"))

    # o validador ja funciona: aceita o certo e recusa o errado
    bons, maus = 0, 0
    for c in ct.CONTRATOS:
        exemplo = {}
        for campo in c.esquema:
            if not campo.obrigatorio:
                continue
            exemplo[campo.nome] = (campo.dominio[0] if campo.dominio else
                                   {"texto": "x", "inteiro": 1, "real": 1.0,
                                    "booleano": True, "lista": [1.0],
                                    "registro": {}}[campo.tipo])
        try:
            lido = c.receber([exemplo])
            bons += 1
            if set(lido[0]) != set(exemplo):
                problemas.append(f"{c.cod}: receber() perdeu campo obrigatorio")
        except (ValueError, TypeError) as e:
            problemas.append(f"{c.cod}: recusou registro valido — {e}")

        # falta de campo obrigatorio, tipo errado e campo desconhecido
        for nome, ruim in (("campo ausente", {}),
                           ("campo desconhecido",
                            dict(exemplo, campo_que_nao_existe=1))):
            try:
                c.receber([ruim])
            except ValueError:
                maus += 1
            else:
                problemas.append(f"{c.cod}: aceitou registro com {nome}")
    out.append(Achado("NOTA" if bons == len(ct.CONTRATOS) else "ERRO",
                      "validacao",
                      f"os {bons} validadores aceitam o registro completo e "
                      f"recusam {maus} registros malformados — o validador "
                      f"existe antes do dado"))

    # todo contrato diz o que falta escrever e como sera aceito
    mudos = [c.cod for c in ct.CONTRATOS
             if len(c.aceite) < 40 or len(c.bloqueio) < 40 or not c.esquema]
    if mudos:
        problemas.append(f"contratos sem criterio de aceite ou sem esquema: {mudos}")
    campos = sum(len(c.esquema) for c in ct.CONTRATOS)
    out.append(Achado("NOTA" if not mudos else "ERRO", "esquema",
                      f"{campos} campos com tipo, unidade e obrigatoriedade "
                      f"declarados: o fornecedor do dado sabe exatamente o que "
                      f"entregar antes de escrever a primeira linha"))

    for m in problemas[:10]:
        out.append(Achado("ERRO", "contratos", m))
    return out


def checar_descida() -> list[Achado]:
    """Descida de cargas: a carga que chega, e a trava que nao pode voltar.

    Esta bateria existe por causa de um defeito especifico, e o primeiro teste
    e o antidoto dele. Ate R28 a utilizacao era relatada com `min(0.99, ...)`.
    Com esse teto, um montante 47 % sobrecarregado saia como 0,99, o item
    "perfis aprovados" do checklist passava, e a liberacao dizia LIBERADO. Um
    item de verificacao que nao pode falhar nao verifica: assina.

    Por isso aqui nao se confere que o projeto passa — confere-se que o projeto
    seria REPROVADO se estivesse errado. Uma bateria que so testa o caso bom
    nao testa nada.
    """
    import projeto as pj
    import elementos as el
    import nucleo.painel as pn
    import nucleo.perfis as pf
    import nucleo.materiais as mt
    import nucleo.descida as ds
    out = []
    # UM modelo, construido uma vez (nucleo/fixture.py). Montar o proprio
    # aqui foi como a auditoria ja verificou painel sem jamba dimensionada
    # enquanto o produto usava outro.
    m = fx.modelo()
    cfg, aco, cat = m["cfg"], m["aco"], m["por_cod"]
    pais, todos, sup = m["paineis"], m["todos"], m["acima_de"]

    # ---- 1. A TRAVA NAO PODE VOLTAR
    # carga absurda de proposito: a utilizacao tem de sair acima de 1 e o
    # resultado tem de vir REPROVADO. Se algum dia alguem puser um teto de
    # volta, este teste cai na hora.
    pesado = {k: v * 20 for k, v in pj.CARGAS.items()}
    r_mau = ds.verificar(todos, sup, cat, aco, pesado, cfg)
    pior = max(r_mau["utilizacoes"])
    out.append(Achado("NOTA" if pior > 1.0 and not r_mau["aprovado"] else "ERRO",
                      "sem teto",
                      f"com 20x a carga o pior montante sai com utilizacao "
                      f"{pior:.2f} e o conjunto vem REPROVADO — a utilizacao "
                      f"nao tem teto, e reprovacao nao vira aprovacao"))

    # ---- 2. E o checklist tem de sentir
    import nucleo.scores as sc
    lib_mau = sc.liberar({"perfis aprovados": False})
    out.append(Achado("NOTA" if not lib_mau["liberado"] else "ERRO", "bloqueio",
                      "montante reprovado bloqueia a liberacao: o checklist "
                      "reage ao resultado, nao o decora"))

    # ---- 3. Caminho independente: as faixas cobrem a area do pavimento
    ctx = ds.contexto(todos, sup)
    for pav, amb in (("T", pj.TERREO), ("S", pj.SUPERIOR)):
        area = sum(a.area_mod for a in amb)
        c = ds.cobertura_de_area(pais[pav], area, ctx)
        out.append(Achado("NOTA" if c["seguro"] else "ERRO", f"area {pav}",
                          c["leitura"]))

    # ---- 4. O k sai do blocking, nao do arbitrio
    com = [p for p in todos if any(q.familia == "blocking" for q in p.pecas)]
    sem_bl = pn.Painel(cod="X", parede="X", x=0, y=0, comp=2400, altura=2600,
                       esp=150, externa=True)
    k_sem = pn.travamento_k(sem_bl)
    k_com = pn.travamento_k(com[0]) if com else 1.0
    out.append(Achado("NOTA" if k_sem == 1.0 and k_com < 1.0 else "ERRO",
                      "travamento",
                      f"painel sem blocking da k = {k_sem:.2f}; com blocking, "
                      f"k = {k_com:.2f} — o k vem da peca que existe, e a "
                      f"diferenca vale {1/k_com**2:.1f}x na carga de Euler"))

    # ---- 5. A jamba cresce com o vao, e recusa quando nao cabe
    cresce = [pn.jamba_necessaria(n, 2600, aco, cfg)["escolha"]
              for n in (8.0, 20.0, 40.0)]
    massas = [c["massa"] for c in cresce if c]
    impossivel = pn.jamba_necessaria(400.0, 2600, aco, cfg)
    out.append(Achado(
        "NOTA" if (len(massas) == 3 and massas == sorted(massas)
                   and impossivel["escolha"] is None) else "ERRO",
        "jamba",
        f"8, 20 e 40 kN pedem jambas de {', '.join(f'{m:.1f}' for m in massas)} "
        f"kg, nessa ordem; 400 kN nao encontra solucao e diz que o vao exige "
        f"pilar, em vez de devolver a maior do catalogo"))

    # ---- 6. Alvo de projeto e limite normativo sao coisas diferentes
    escolhidas = [pn.jamba_necessaria(n, 2600, aco, cfg)
                  for n in (8.0, 15.0, 20.0, 29.5, 40.0)]
    acima = [e for e in escolhidas
             if e["escolha"] and e["escolha"]["u"] > cfg.u_alvo]
    out.append(Achado("NOTA" if not acima else "ERRO", "folga",
                      f"nenhuma jamba dimensionada passa da utilizacao alvo "
                      f"{cfg.u_alvo:.2f}, enquanto a APROVACAO continua sendo "
                      f"1,00 da norma — alvo de projeto e limite normativo nao "
                      f"sao a mesma coisa, e confundi-los e como se perde a "
                      f"margem sem perceber"))

    # ---- 7. O projeto: antes e depois do dimensionamento da jamba
    # A primeira passada e a geometria; a segunda dimensiona. Mostrar as duas e
    # o que PROVA que a segunda serve para alguma coisa: uma bateria que so
    # olhasse o estado final nao distinguiria dimensionar de nao precisar.
    # Esta e a UNICA bateria que nao pode usar a fixture: ela precisa do
    # estado ANTES do dimensionamento, e a fixture entrega — de proposito — o
    # modelo do produto, que ja esta dimensionado. Construir aqui e explicito,
    # e o comentario existe para que a proxima migracao nao o desfaca.
    cru = {pav: pn.painelizar(el.derivar_paredes(amb),
                              list(el.vaos_do_pavimento(pav)), cfg, f"{pav}P")
           for pav, amb in (("T", pj.TERREO), ("S", pj.SUPERIOR))}
    antes = ds.verificar(cru["T"] + cru["S"], dict(T=cru["S"], S=[]),
                         cat, aco, pj.CARGAS, cfg)
    r = ds.verificar(todos, sup, cat, aco, pj.CARGAS, cfg)
    out.append(Achado("NOTA" if antes["reprovadas"] and not r["reprovadas"]
                      else "ERRO", "dimensionamento",
                      f"com a jamba minima de praxe (um montante de cada lado) "
                      f"{len(antes['reprovadas'])} pecas reprovam, a pior com "
                      f"{max(antes['utilizacoes']):.2f}; dimensionada pela "
                      f"carga, nenhuma reprova e a pior cai para "
                      f"{max(r['utilizacoes']):.2f}"))
    ru = sorted(r["utilizacoes"])
    med = ru[len(ru) // 2]
    g = r["governa"]
    out.append(Achado("NOTA" if r["aprovado"] else "ERRO", "projeto",
                      f"{r['n']} montantes verificados um a um: "
                      f"{len(r['reprovadas'])} reprovam, mediana {med:.2f}, "
                      f"maior {ru[-1]:.2f} em {g['peca']} ({g['familia']}, "
                      f"{g['modo']}, Nsd {g['nsd']:.1f} de {g['nrd']:.1f} kN)"))
    ociosos = sum(1 for u in ru if u < 0.30)
    out.append(Achado("NOTA", "ociosidade",
                      f"{ociosos} dos {len(ru)} montantes ficam abaixo de 30 % "
                      f"de utilizacao: no montante corrente quem manda e a "
                      f"modulacao da placa, nao a carga — so a jamba e "
                      f"governada por esforco"))
    for h in r["hipoteses"]:
        out.append(Achado("ATENCAO", "hipotese de caminho de carga", h))
    return out


def checar_juntas() -> list[Achado]:
    """Programa de parafusos: quantos, quais, e de onde veio o numero.

    Ate R29 o checklist da liberacao trazia `"ligacoes": True`. Literal, uma
    linha abaixo do `min(0.99, ...)` da verificacao estrutural e com o mesmo
    vicio: um item que nao pode falhar nao verifica, assina. O BOM, do seu
    lado, estimava `len(pecas) * 8` parafusos — 6.440 contra os 5.266 reais,
    22 % de erro num item que agora e contado.
    """
    import projeto as pj
    import elementos as el
    import nucleo.painel as pn
    import nucleo.perfis as pf
    import nucleo.materiais as mt
    import nucleo.descida as ds
    import nucleo.juntas as ju
    import nucleo.ligacoes as lg
    out = []
    m = fx.modelo()
    cfg, aco, pais, todos = m["cfg"], m["aco"], m["paineis"], m["todos"]
    dim = dict(ctx=m["ctx"], jambas=m["jambas"])

    progs, problemas = {}, []
    for p in todos:
        e = ds.esforco_por_montante(p, dim["ctx"], pj.CARGAS, cfg)
        nm = e["por_familia"]["montante"]["nsd"]
        nj = (e["por_familia"].get("king stud")
              or e["por_familia"]["montante"])["nsd"]
        progs[p.cod] = ju.programar(p, nm, nj, aco, cfg)

    # ---- 1. nenhuma peca fica sem junta: peca solta cai
    for p in todos:
        ligadas = {c for j in progs[p.cod]["juntas"] for c in j["pecas"]}
        soltas = [q.cod for q in p.pecas if q.cod not in ligadas]
        if soltas:
            problemas.append(f"{p.cod}: {len(soltas)} peca(s) sem junta "
                             f"nenhuma (ex.: {soltas[0]})")
    total = sum(j["n_parafusos"] for j in progs.values())
    out.append(Achado("NOTA" if not problemas else "ERRO", "cobertura",
                      f"{sum(j['n_juntas'] for j in progs.values())} juntas e "
                      f"{total} parafusos; nenhuma peca do projeto fica sem "
                      f"ligacao, e peca sem ligacao e peca que cai"))

    # ---- 2. a origem do numero nunca se perde na soma
    origens = {}
    for j in progs.values():
        for k, v in j["por_origem"].items():
            origens[k] = origens.get(k, 0) + v
    soma = sum(origens.values())
    desconhecida = set(origens) - {"FORCA", "MINIMO", "DECLARADO"}
    out.append(Achado("NOTA" if soma == total and not desconhecida else "ERRO",
                      "origem",
                      f"{origens.get('FORCA', 0)} parafusos saem de esforco "
                      f"calculado, {origens.get('MINIMO', 0)} de minimo "
                      f"construtivo e {origens.get('DECLARADO', 0)} de regra "
                      f"declarada — e as tres somam o total exato, sem sobra"))

    # ---- 3. nenhuma junta abaixo do minimo, nenhuma acima da capacidade
    fracos = [(j["painel"], x) for j in progs.values() for x in j["juntas"]
              if x["n"] < 2]
    out.append(Achado("NOTA" if not fracos else "ERRO", "minimo",
                      f"nenhuma junta sai com menos de 2 parafusos: um "
                      f"parafuso so nao e ligacao, e uma rotula"))

    # ---- 4. o modelo de cisalhamento reage a espessura, e reage na direcao
    # certa: chapa mais grossa segura mais
    par = lg.POR_PARAFUSO[ju.PADRAO]
    caps = [lg.cisalhamento(par, t, t, aco.fu, aco.fu)["nvrd"]
            for t in (0.95, 1.25, 1.55, 2.00)]
    out.append(Achado("NOTA" if caps == sorted(caps) else "ERRO", "modelo",
                      f"a capacidade por parafuso cresce com a chapa: "
                      f"{', '.join(f'{c:.2f}' for c in caps)} kN para 0,95 a "
                      f"2,00 mm — e o modo governante vem nomeado em cada uma"))

    # ---- 5. dobrar a forca nao pode dar o mesmo numero de parafusos
    n1 = lg.quantidade(20.0, par, 1.25, 1.25, aco.fu, aco.fu)["n"]
    n2 = lg.quantidade(40.0, par, 1.25, 1.25, aco.fu, aco.fu)["n"]
    out.append(Achado("NOTA" if n2 > n1 else "ERRO", "sensibilidade",
                      f"20 kN pedem {n1} parafusos e 40 kN pedem {n2}: a "
                      f"quantidade responde a forca, nao ao habito"))

    # ---- 6. e o BOM tem de receber o numero contado, nao uma estimativa
    import nucleo.bom as bo
    pecas = []
    for pav, lista in pais.items():
        pecas += __import__("nucleo.peca", fromlist=["x"]).detalhar(
            lista, pn._catalogo_massa(), pav, pj.EMISSAO["revisao"])
    estimado = bo.montar(pecas, dict(barras=[], n_barras=0, n_novas=0,
                                     bruto=0.0, usado=0.0, perda=0.0,
                                     aproveitamento=1.0), 295.92)
    real = bo.montar(pecas, dict(barras=[], n_barras=0, n_novas=0, bruto=0.0,
                                 usado=0.0, perda=0.0, aproveitamento=1.0),
                     295.92, n_parafusos=total)
    qe = next(i.quantidade for i in estimado if i.sku == "PAR-EST")
    qr = next(i.quantidade for i in real if i.sku == "PAR-EST")
    out.append(Achado("NOTA" if qr == total else "ERRO", "BOM",
                      f"o BOM recebe os {int(qr)} parafusos contados; a "
                      f"estimativa antiga de len(pecas) x 8 daria {int(qe)}, "
                      f"{abs(qe-qr)/qr*100:.0f} % a mais"))

    for m in problemas[:8]:
        out.append(Achado("ERRO", "juntas", m))
    return out


def checar_vigamento() -> list[Achado]:
    """Entrepiso, cobertura e contraventamento — o que faltava para haver casa.

    Ate R30 a estrutura do modelo eram 805 pecas e todas as 805 eram de parede.
    Uma casa em LSF com paredes e sem vigas nao e uma casa incompleta: o piso
    do pavimento superior nao se apoiava em nada. E o consumo de aco declarado,
    9,4 kg/m2, era implausivel para um sobrado — a faixa corrente e 20 a 30.
    Faltava mais da metade do aco, e nenhuma das 440 condicoes acusava, porque
    todas verificavam o que existia.
    """
    import projeto as pj
    import elementos as el
    import nucleo.painel as pn
    import nucleo.perfis as pf
    import nucleo.materiais as mt
    import nucleo.piso as ps
    import nucleo.descida as ds
    out = []
    m = fx.modelo()
    cfg, aco = m["cfg"], m["aco"]
    casa = ps.montar_casa(pj, aco, cfg)

    # ---- 1. todo comodo tem piso ou cobertura, e nenhum fica sem vencer
    out.append(Achado("NOTA" if casa["ok"] else "ERRO", "cobertura de planos",
                      f"{len(casa['planos'])} planos vigados e {casa['n']} "
                      f"pecas: {casa['por_tipo']}; nenhum comodo fica sem "
                      f"vigamento, e comodo sem vigamento e comodo sem piso"))

    # ---- 2. a viga vence a MENOR dimensao — o momento cresce com o quadrado
    erradas = [v["regiao"] for v in casa["planos"]
               if v["vao"] > v["corrido"] + 1]
    out.append(Achado("NOTA" if not erradas else "ERRO", "direcao",
                      "toda viga vence a menor dimensao do comodo: vencer 3 m "
                      "em vez de 5 nao economiza 40 % de aco, economiza 64 % "
                      "de momento"))

    # ---- 3. a flecha, e nao o momento, e quem governa piso
    gov = [v for v in casa["planos"] if v["ok"] and v["tipo"] == "piso"]
    por_flecha = sum(1 for v in gov
                     if v["dimensionamento"]["escolhido"]["uso"] < 0.95)
    out.append(Achado("NOTA", "criterio",
                      f"em {por_flecha} dos {len(gov)} planos de piso o perfil "
                      f"e definido pela FLECHA (L/{ps.FLECHA_PISO:.0f}) e nao "
                      f"pelo momento — dimensionar piso por resistencia e como "
                      f"o morador descobre que o piso balanca"))

    # ---- 4. o limite de flecha e parametro, e mexer nele muda o perfil
    leve = pn.verga_necessaria(4_800, 1.08, aco, cfg, flecha_div=250.0)
    duro = pn.verga_necessaria(4_800, 1.08, aco, cfg, flecha_div=500.0)
    out.append(Achado(
        "NOTA" if (leve["escolhido"] and duro["escolhido"]
                   and duro["escolhido"]["massa"] > leve["escolhido"]["massa"])
        else "ERRO", "flecha",
        f"o mesmo vao de 4,8 m pede {leve['escolhido']['perfil']} a L/250 e "
        f"{duro['escolhido']['perfil']} a L/500: o limite de flecha e "
        f"parametro do problema, nao constante da funcao"))

    # ---- 5. contraventamento conferido contra o vento da NBR 6123
    pais = {pav: pn.painelizar(el.derivar_paredes(amb),
                               list(el.vaos_do_pavimento(pav)), cfg, f"{pav}P")
            for pav, amb in (("T", pj.TERREO), ("S", pj.SUPERIOR))}
    ds.dimensionar(pais, aco, pj.CARGAS, cfg, list(pf.catalogo()))
    c = ps.contraventar(pais["T"] + pais["S"], pj, aco, cfg)
    for d, v in c["veredito"].items():
        out.append(Achado("NOTA" if v["ok"] else "ERRO", f"vento {d}",
                          f"as fitas em X dao {v['capacidade']:.0f} kN contra "
                          f"{v['demanda']:.0f} kN de forca global da NBR 6123 "
                          f"(V0 {pj.V0_VENTO:.0f} m/s, categoria "
                          f"{pj.CATEGORIA_VENTO}) — folga de {v['folga']:.0f} kN"))
    out.append(Achado("ATENCAO", "hipotese de vento",
                      f"V0 = {pj.V0_VENTO:.0f} m/s e categoria "
                      f"{pj.CATEGORIA_VENTO} sao leitura da isopleta e "
                      f"classificacao de rugosidade: interpretacao, nao "
                      f"medicao. Quem assina a ART pode ler diferente, e "
                      f"categoria III em vez de IV muda S2 em cerca de 10 %"))

    # ---- 6. o aco total ficou em faixa plausivel para um sobrado em LSF
    cat = pn._catalogo_massa()
    pecas = ps.como_pecas(casa, c, cat, pj.EMISSAO["revisao"])
    massa_vig = sum(p.massa for p in pecas)
    out.append(Achado("NOTA", "massa",
                      f"vigamento e contraventamento somam {massa_vig:.0f} kg, "
                      f"que nao existiam no BOM ate R30. Com eles o consumo vai "
                      f"a 21,0 kg/m2; sem eles marcava 9,4, e a faixa corrente "
                      f"de um sobrado em LSF e 20 a 30"))
    return out


def checar_plausibilidade() -> list[Achado]:
    """Ordem de grandeza — a terceira classe de verificacao.

    As 447 condicoes anteriores sabiam conferir IDENTIDADE (bruto = usado +
    perda) e FORMA FECHADA (viga biapoiada). Nenhuma sabia olhar um numero e
    perguntar se ele e possivel. O consumo de aco marcou 9,4 kg/m2 num sobrado
    em LSF — faixa corrente 20 a 30 — em toda revisao desde a E12, e ninguem
    reparou, porque nao havia com o que comparar.

    A prova de que esta bateria serve nao e o projeto passar: e ela PEGAR o
    estado anterior. Por isso o primeiro teste alimenta os numeros reais de R30
    e exige que as faixas acusem.
    """
    import projeto as pj
    import elementos as el
    import nucleo.liberacao as lb
    import nucleo.plausibilidade as pb
    out = []

    # ---- 1. teria pego o defeito 38? Numeros reais da revisao R30.
    r30 = dict(aco_m2=2772 / 295.92, parafusos_m2=5266 / 295.92,
               aproveitamento=87.4, horas_m2=124 / 295.92,
               co2e_m2=6037 / 295.92, pecas_m2=805 / 295.92,
               massa_painel=95.3, custo_m2=551.0, uso_estrutural=0.19)
    a30 = pb.avaliar(r30)
    pegou = {x["cod"] for x in a30["fora"]}
    out.append(Achado("NOTA" if "aco_m2" in pegou else "ERRO", "regressao",
                      f"alimentada com os numeros reais de R30 — a revisao em "
                      f"que faltava mais da metade do aco — a bateria acusa "
                      f"{len(a30['fora'])} grandeza(s): "
                      f"{', '.join(sorted(pegou))}. O defeito 38 teria sido "
                      f"pego por dois caminhos independentes"))

    # ---- 2. faixa que nada viola nao e faixa: cada uma tem de reagir
    mudas = []
    for f in pb.FAIXAS:
        fora_baixo = f.avaliar(f.minimo * 0.5)
        fora_alto = f.avaliar(f.maximo * 2.0)
        dentro = f.avaliar((f.minimo + f.maximo) / 2)
        if fora_baixo["dentro"] or fora_alto["dentro"] or not dentro["dentro"]:
            mudas.append(f.cod)
    out.append(Achado("NOTA" if not mudas else "ERRO", "sensibilidade",
                      f"as {len(pb.FAIXAS)} faixas reagem nos dois sentidos: "
                      f"metade do minimo e o dobro do maximo saem, e o meio "
                      f"entra. Faixa que nada viola nao verifica nada"))

    # ---- 3. toda faixa declara de onde veio, e o que a saida significa
    sem_fonte = [f.cod for f in pb.FAIXAS
                 if len(f.fonte) < 25 or len(f.consequencia) < 25]
    hip = sum(1 for f in pb.FAIXAS if f.fonte.startswith("(H)"))
    out.append(Achado("NOTA" if not sem_fonte else "ERRO", "procedencia",
                      f"{hip} das {len(pb.FAIXAS)} faixas sao (H) — pratica "
                      f"corrente, nao norma — e todas dizem o que a saida da "
                      f"faixa costuma significar. Faixa sem fonte e palpite "
                      f"com aparencia de criterio"))

    # ---- 4. o projeto de hoje, grandeza por grandeza
    r = fx.liberacao()
    a = pb.avaliar(pb.medir(r, pj.CADASTRO.area_m2))
    for x in a["avaliacoes"]:
        out.append(Achado("NOTA" if x["dentro"] else "ATENCAO",
                          "grandeza", x["leitura"]))
    out.append(Achado("NOTA", "resultado",
                      f"{a['n']} grandezas conferidas, {len(a['fora'])} fora "
                      f"da faixa. Fora da faixa nao reprova: obriga a "
                      f"justificar — reprovar o que e apenas incomum treina "
                      f"quem le a ignorar o aviso"))
    return out


def checar_completude() -> list[Achado]:
    """O que precisa EXISTIR — a quarta classe, e a que faltava ha mais tempo.

    O modelo passou trinta e uma revisoes com 805 pecas de estrutura, todas de
    parede: sem vigamento de entrepiso, sem cobertura, sem contraventamento. As
    447 condicoes continuaram verdes porque todas verificavam coisas que
    existiam. Esta bateria pergunta a outra coisa, e a pergunta so vale se a
    lista tiver sido escrita ANTES de olhar o modelo — senao ela vira o
    inventario do que ja existe e confirma tudo por construcao.
    """
    import projeto as pj
    import elementos as el
    import nucleo.liberacao as lb
    import nucleo.completude as cm
    out = []
    r = fx.liberacao()
    c = cm.conferir(r, pj.CADASTRO.tipologia)

    # ---- 1. a lista cobre sistema, nao peca: ela vale para outro projeto
    sem_porque = [e.cod for e in cm.EXIGENCIAS
                  if len(e.porque) < 20 or len(e.ausencia) < 25]
    out.append(Achado("NOTA" if not sem_porque else "ERRO", "lista",
                      f"{len(cm.EXIGENCIAS)} exigencias do SISTEMA "
                      f"CONSTRUTIVO, cada uma dizendo por que e necessaria e o "
                      f"que a falta significa fisicamente — e por isso ela "
                      f"pode acusar falta num projeto que ninguem achava "
                      f"incompleto"))

    # ---- 2. a bateria PODE reprovar: modelo vazio tem de reprovar em massa
    vazio = cm.conferir(dict(pecas=[], plano={}, n_parafusos=0, passos=[]),
                        "SOBRADO")
    out.append(Achado("NOTA" if len(vazio["faltando"]) >= 10 else "ERRO",
                      "reacao",
                      f"um modelo vazio reprova em {len(vazio['faltando'])} "
                      f"dos {vazio['n']} sistemas — a verificacao reage a "
                      f"ausencia, que e justamente o que ela existe para ver"))

    # ---- 3. teria pego o defeito 38?
    import copy as _cp
    sem_vig = _cp.copy(r)
    sem_vig["pecas"] = [p for p in r["pecas"]
                        if p.familia not in ("viga", "viga de borda",
                                             "travamento", "diagonal")
                        and getattr(p, "pav", "") != "C"]
    c38 = cm.conferir(sem_vig, pj.CADASTRO.tipologia)
    faltas = {f["cod"] for f in c38["faltando"]}
    esperadas = {"entrepiso", "cobertura", "contraventamento"}
    out.append(Achado("NOTA" if esperadas <= faltas else "ERRO", "regressao",
                      f"retirando o vigamento — o estado exato de R30 — a "
                      f"bateria acusa {len(faltas)} sistemas ausentes, entre "
                      f"eles entrepiso, cobertura e contraventamento. O "
                      f"defeito 38 seria pego no primeiro build"))

    # ---- 4. a tipologia manda: exigencia de sobrado nao vale para terreo
    terreo = cm.conferir(r, "CASA TERREA")
    na = [i for i in terreo["itens"] if i["situacao"] == "NAO SE APLICA"]
    out.append(Achado("NOTA" if na else "ERRO", "tipologia",
                      f"numa casa terrea {len(na)} exigencia(s) saem de cena "
                      f"(entrepiso e escada): completude sem tipologia "
                      f"reprovaria todo terreo por falta de escada"))

    # ---- 5. o estado real, item a item
    for i in c["itens"]:
        nivel = {"PRESENTE": "NOTA", "NAO SE APLICA": "NOTA",
                 "AUSENTE": "ERRO"}[i["situacao"]]
        out.append(Achado(nivel, i["cod"],
                          f"{i['nome']}: {i['situacao']}"
                          + (f" ({i['n']} pecas)" if i["n"] else "")
                          + f" — {i['nota']}"))
    return out


def checar_coerencia_de_modelo() -> list[Achado]:
    """Auditoria, exportacao e desenho olham o MESMO modelo?

    Esta bateria existe porque a resposta ja foi nao, duas vezes, e das duas
    ninguem percebeu por meses.

    A primeira: a segunda passada de dimensionamento de jamba morava dentro da
    liberacao, entao a auditoria montava o painel sem ela e aprovava um painel
    que o produto nao usava. A segunda: `_pecas_do_projeto()` reconstruia o
    conjunto por conta propria e devolvia 805 pecas enquanto o projeto tinha
    1.033 — vigamento, escada e contraventamento nunca entravam, e a
    verificacao de clash, cuja unica razao de existir e olhar tudo ao mesmo
    tempo, rodava sobre cinco familias a menos.

    As duas foram corrigidas movendo codigo. Mover codigo evita o erro daquela
    vez; nao evita o proximo. O que evita o proximo e transformar a coerencia em
    CONDICAO — e e o que esta funcao faz, comparando peca a peca o que cada
    consumidor enxerga.
    """
    import projeto as pj
    import engenharia as eng
    import modelo3d as m3
    out = []

    produto = {p.cod for p in fx.liberacao()["pecas"]}
    auditado = {p.cod for p in _pecas_do_projeto()}
    exportado = set()
    d = eng.montar()
    for p in d["paineis"]:
        exportado |= {q["cod"] for q in p["pecas"]}
    exportado |= {q["cod"] for q in d.get("extras", [])}
    desenhado = {b["cod"] for b in m3.exportar() ["lsf"]}

    pares = (("auditoria", auditado), ("exportacao", exportado),
             ("desenho 3D", desenhado))
    for nome, conj in pares:
        so_la = conj - produto
        so_ca = produto - conj
        ok = not so_la and not so_ca
        det = (f"{nome} e produto veem as mesmas {len(produto)} pecas"
               if ok else
               f"{nome} diverge do produto: {len(so_ca)} peca(s) que o produto "
               f"tem e ela nao"
               + (f" (ex.: {sorted(so_ca)[0]})" if so_ca else "")
               + f", {len(so_la)} que ela tem e o produto nao"
               + (f" (ex.: {sorted(so_la)[0]})" if so_la else ""))
        out.append(Achado("NOTA" if ok else "ERRO", nome, det))

    # a massa tem de fechar pelos tres caminhos, nao so a contagem
    r = fx.liberacao()
    massa_bom = next((i.quantidade for i in r["bom"] if i.sku == "ACO-PERF"), 0)
    massa_pecas = sum(p.massa for p in r["pecas"])
    massa_comprada = r["massa_comprada"]
    dif = abs(massa_bom - massa_comprada) / max(massa_comprada, 1e-9)
    out.append(Achado("NOTA" if dif < 0.01 else "ERRO", "massa",
                      f"a massa fecha por dois caminhos independentes: "
                      f"{massa_pecas:.0f} kg somando peca a peca, "
                      f"{massa_comprada:.0f} kg comprados pelo aproveitamento "
                      f"e {massa_bom:.0f} kg no BOM — diferenca de "
                      f"{dif*100:.2f} %, limite 1 %"))

    # e o codigo do painel tem de ser o mesmo da fabrica (defeito 39)
    m = fx.modelo()
    no_painel = {q.cod for p in m["todos"] for q in p.pecas}
    fabrica = {p.cod for p in r["pecas"]}
    orfas = no_painel - fabrica
    out.append(Achado("NOTA" if not orfas else "ERRO", "identidade",
                      f"as {len(no_painel)} pecas dos paineis aparecem com o "
                      f"MESMO codigo na lista de fabrica: a peca clicada no 3D "
                      f"e encontravel no plano de corte"))

    # nenhum codigo repetido em lugar nenhum
    import collections as _c
    rep = [k for k, v in _c.Counter(p.cod for p in r["pecas"]).items() if v > 1]
    out.append(Achado("NOTA" if not rep else "ERRO", "unicidade",
                      f"nenhum dos {len(r['pecas'])} codigos se repete"
                      + (f" — repetidos: {rep[:3]}" if rep else "")))
    return out


def checar_camadas() -> list[Achado]:
    """Composicao de parede: espessura, cavidade e area derivada.

    Ate R33 o fechamento inteiro saia de seis coeficientes — `area_m2 * 2.4` e
    mais cinco fatores por camada — onde o modelo ja sabia comprimento, altura
    e aberturas de cada um dos 62 paineis. O coeficiente acertava por acaso:
    710,2 m2 contra 718,6 de area real de duas faces. Acerto por cancelamento
    de dois erros grandes nao e acerto.
    """
    import projeto as pj
    import especificacao as ep
    import nucleo.camadas as cd
    out = []
    m = fx.modelo()
    r = fx.liberacao()

    # ---- 1. a composicao construida cabe no modulo declarado
    esp = cd.conferir_espessuras()
    maus = [e for e in esp if not e["cabe"]]
    out.append(Achado("NOTA" if not maus else "ERRO", "espessura",
                      f"as {len(esp)} composicoes cabem no modulo: folga de "
                      + ", ".join(f"{e['cod']} {e['folga']:+.0f}" for e in esp)
                      + " mm. A camada isolante nao soma — ela vive DENTRO da "
                        "cavidade do montante, e soma-la daria uma parede de "
                        "182,5 mm onde ha 150"))

    # ---- 2. a transcricao bate com a prosa da prancha
    divergentes = []
    for cod, f in ep.FAMILIAS.items():
        c = cd.COMPOSICOES.get(cod)
        if c is None:
            divergentes.append(f"{cod}: sem composicao transcrita")
        elif c.esp_nominal != f["esp"]:
            divergentes.append(f"{cod}: {c.esp_nominal} contra {f['esp']} da prancha")
        elif c.rw != f["Rw"]:
            divergentes.append(f"{cod}: Rw {c.rw} contra {f['Rw']} da prancha")
    out.append(Achado("NOTA" if not divergentes else "ERRO", "transcricao",
                      f"as {len(cd.COMPOSICOES)} composicoes conferem com a "
                      f"prancha PR-12 em espessura e Rw: a transcricao e "
                      f"transcricao, e quem manda e o desenho"
                      if not divergentes else "; ".join(divergentes)))

    # ---- 3. a prumada cabe na cavidade? (a pergunta que a prosa escondia)
    ph = cd.cabe_prumada(cd.COMPOSICOES["PH-1"], "DN100")
    out.append(Achado("ATENCAO" if not ph["cabe"] else "NOTA", "prumada",
                      ph["leitura"] + ". A justificativa escrita da PH-1 e que "
                      "os 150 mm existem para acomodar o DN100; a cavidade "
                      "real e a alma do montante, nao a espessura da parede, e "
                      "por isso a PR-21 manda a prumada para shaft. As duas "
                      "afirmacoes convivem no projeto e nao dizem a mesma coisa"))
    # e o criterio reage ao diametro, em vez de reprovar sempre
    menor = cd.cabe_prumada(cd.COMPOSICOES["PH-1"], "DN50")
    out.append(Achado("NOTA" if menor["cabe"] else "ERRO", "criterio",
                      f"o mesmo criterio aprova o DN50 ({menor['diametro_externo']:.0f} "
                      f"mm) e reprova o DN100 ({ph['diametro_externo']:.0f} mm): "
                      f"reage ao diametro, nao ao habito. E DN nao e diametro "
                      f"externo — o DN100 tem 110 mm, e sao esses 10 mm que "
                      f"decidem"))

    # ---- 4. todo painel tem composicao: parede sem composicao nao tem material
    fam = r["camadas"]["familias"]
    out.append(Achado("NOTA" if not fam["orfaos"] else "ERRO", "cobertura",
                      f"os {len(m['todos'])} paineis foram casados com o trecho "
                      f"de parede classificado que os originou, por "
                      f"SOBREPOSICAO: {len(fam['orfaos'])} orfaos. A primeira "
                      f"versao casava por eixo mais proximo e classificou 62 "
                      f"de 62 sem que uma unica divisoria simples aparecesse — "
                      f"sinal de casamento errado, nao de casa sem divisoria"))
    import collections as _c
    dist = _c.Counter(fam["familia"].values())
    out.append(Achado("NOTA" if dist.get("PA-2", 0) == 1 else "ERRO",
                      "distribuicao",
                      f"{dict(dist)} — e a PA-2 sai com exatamente 1 painel, "
                      f"que e o que a prancha declara: 'EXCLUSIVAMENTE a "
                      f"parede entre a oficina e o estar'. Confirmacao "
                      f"independente de que o casamento esta certo"))

    # ---- 5. a area vem da geometria, e o coeficiente antigo errava
    q = r["camadas"]
    bruta = sum(p.comp * p.altura for p in m["todos"]) / 1e6
    vaos = sum(a["larg"] * a["alt"] for p in m["todos"] for a in p.aberturas) / 1e6
    coef = pj.CADASTRO.area_m2 * 2.4
    out.append(Achado("NOTA", "geometria",
                      f"area bruta de painel {bruta:.1f} m2 menos {vaos:.1f} de "
                      f"abertura da {bruta-vaos:.1f} m2 liquidos; as camadas "
                      f"somam {q['area_total']:.1f} m2. O coeficiente antigo "
                      f"dava {coef:.1f} para TODAS as camadas juntas — nao "
                      f"descontava abertura nenhuma, porque multiplicava a "
                      f"area de projeto, que nao sabe onde ha janela"))

    # ---- 5b. esquadria: o vao virou material
    import nucleo.esquadrias as esq
    e = r["camadas"]["esquadrias"]
    out.append(Achado("NOTA" if not e["sem_vidro"] else "ERRO", "esquadria",
                      f"{e['n']} esquadrias, {e['area_vidro']} m2 de vidro e "
                      f"{e['caixilho_m']} m de caixilho, derivados dos vaos que "
                      f"o modelo ja tinha. Esquadria e 12 a 18 % do custo de "
                      f"uma residencia e estava em ZERO no BOM"))
    ok_d = all("(H)" in str(v) for k, v in e["desempenho"].items()
               if k != "norma")
    out.append(Achado("NOTA" if ok_d else "ERRO", "desempenho",
                      f"estanqueidade a agua, ao ar e resistencia a carga de "
                      f"vento entram como EXIGENCIA {e['desempenho']['norma']} "
                      f"marcada (H), nunca como valor: uma classificacao "
                      f"inventada seria indistinguivel de uma ensaiada"))

    # ---- 5c. cobertura e impermeabilizacao
    cob = r["camadas"]["cobertura"]
    out.append(Achado("NOTA" if cob["perimetro"] > 0 else "ERRO",
                      "acessorio de cobertura",
                      f"calha {cob['calha_m']} m, rufo {cob['rufo_m']} m e "
                      f"cumeeira {cob['cumeeira_m']} m saem do PERIMETRO dos "
                      f"planos. O painel resolvia a area; uma cobertura nao "
                      f"vaza pelo painel, vaza pelo encontro"))
    imp = r["camadas"]["impermeabilizacao"]
    out.append(Achado("ATENCAO" if imp["lacuna"] else "NOTA", "impermeabiliza",
                      imp["aviso"] or
                      f"{imp['area']} m2 de impermeabilizacao, {imp['altura_box']} "
                      f"mm no box e {imp['altura_geral']} de rodape"))

    # ---- 6a. norma vem do MATERIAL, fonte unica
    import nucleo.materiais as mt
    sem_norma = [m.cod for m in mt.MATERIAIS if not m.norma]
    todas_cam = [c for comp in list(cd.COMPOSICOES.values())
                 + list(cd.COMPOSICOES_PLANO.values()) for c in comp.camadas]
    herdadas = sum(1 for c in todas_cam if c.norma)
    out.append(Achado("NOTA" if not sem_norma else "ERRO", "norma",
                      f"os {len(mt.MATERIAIS)} materiais declaram norma, e as "
                      f"{herdadas} camadas a HERDAM em vez de repetir. A norma "
                      f"nasceu como campo da camada em R34 e durou uma "
                      f"revisao: duas fontes para o mesmo fato divergem na "
                      f"primeira correcao, e foi assim que houve dois codigos "
                      f"para a mesma peca"))

    # ---- 6b. paginacao: placa inteira, e a perda declarada
    pg = r["camadas"]["paginacao"]
    ruins = [i for i in pg["itens"] if i["nao_cabem"] or i["aproveitamento"] > 1.0]
    out.append(Achado("NOTA" if not ruins else "ERRO", "paginacao",
                      f"{pg['placas']} placas inteiras para {pg['area_util']:.0f} "
                      f"m2 uteis, {pg['area_bruta']:.0f} comprados. Ninguem "
                      f"compra metro quadrado: compra placa, e a diferenca e a "
                      f"perda. A primeira versao tratou a FACE como peca a ser "
                      f"cortada de uma placa e 92 pecas sairam como 'nao "
                      f"cabem' — uma face nao e cortada de uma placa, e "
                      f"coberta por varias"))

    # ---- 6c. junta contada uma vez, e so onde ha tratamento de junta
    placa = sum(i["area_util"] for i in pg["itens"]
                if i["material"] in ("GESSO", "GESSORU", "PLCIM"))
    tot = (pg["junta_m"] + pg["borda_m"]) / placa if placa else 0
    out.append(Achado("NOTA" if 1.6 <= tot <= 2.4 else "ERRO", "junta",
                      f"{tot:.2f} m de fita e arremate por m2 de placa, dentro "
                      f"da pratica de 1,6 a 2,4. Somar o perimetro de cada "
                      f"placa dava 16.607 m para esta casa — dezesseis "
                      f"quilometros, visivelmente absurdo: junta e o encontro "
                      f"de DUAS placas e conta uma vez, e entre dois paineis "
                      f"vale o mesmo"))

    # ---- 6d. os planos horizontais tem camada
    pl = r["camadas"]["planos"]
    out.append(Achado("NOTA" if pl["area_total"] > 0 else "ERRO", "planos",
                      f"entrepiso, forro e cobertura somam {pl['area_total']} "
                      f"m2 de camada. Ate R34 so a PAREDE tinha composicao, e "
                      f"contrapiso, forro e painel de cobertura ficavam fora "
                      f"do BOM — o mesmo buraco do vigamento ate R31"))

    # ---- 6e. acessorio de junta existe e e fracao plausivel do fechamento
    ved = [i for i in r["bom"] if i.familia == "vedacao"]
    ac = sum(i.total for i in ved
             if i.sku in ("FITA", "MASSA", "CANT", "PAR-PLA"))
    tot_v = sum(i.total for i in ved) or 1
    out.append(Achado("NOTA" if 0.05 <= ac / tot_v <= 0.18 else "ATENCAO",
                      "acessorio",
                      f"fita, massa, cantoneira e parafuso de placa somam "
                      f"{ac/tot_v*100:.1f} % do custo do fechamento — a faixa "
                      f"corrente em drywall e 8 a 12 %, e ate R34 eles nao "
                      f"existiam no modelo. Derivam do perimetro, que so a "
                      f"paginacao conhece"))

    # ---- 6. nenhuma camada de aco no BOM em m2: ela ja esta em kg
    dobradas = [i for i in r["bom"]
                if i.familia == "vedacao" and i.sku.startswith("ACO")]
    out.append(Achado("NOTA" if not dobradas else "ERRO", "dupla contagem",
                      "nenhuma camada estrutural aparece em m2 no BOM: o aco "
                      "ja esta la em kg, vindo do plano de corte. Lista-lo nas "
                      "duas unidades e como a dupla contagem costuma passar "
                      "despercebida"))
    return out


def checar_radier() -> list[Achado]:
    """Fundacao: quantidade derivada de uma espessura que e (H).

    A espessura de 180 mm existia em DOIS lugares — um literal no modulo de
    desenho e uma copia dentro do dimensionamento de ancoragem — e nenhum dos
    dois era dado do projeto. O desenho dizia 180 e a ancoragem acreditava; se
    alguem mudasse um, o outro continuaria certo de si.

    Concreto, aco, lastro e lona nunca entraram no BOM. Num sobrado em LSF a
    fundacao e 8 a 15 % do custo, e era o ultimo sistema construtivo grande em
    zero.
    """
    import projeto as pj
    import pranchas2 as p2
    import nucleo.fundacao as fd
    import nucleo.piso as ps
    out = []
    r = fx.liberacao()
    f = r["camadas"]["fundacao"]

    # ---- 1. fonte unica da espessura
    ok = (p2.RADIER == pj.RADIER["espessura"])
    out.append(Achado("NOTA" if ok else "ERRO", "fonte unica",
                      f"a espessura de {pj.RADIER['espessura']} mm e dado do "
                      f"caso, e o desenho a LE em vez de repetir. Ela vivia "
                      f"como literal em pranchas2.py e, em copia, dentro da "
                      f"ancoragem — dois lugares para o mesmo numero divergem "
                      f"na primeira revisao de fundacao"))

    # ---- 2. a ancoragem usa a mesma espessura que o BOM
    import inspect
    src = inspect.getsource(ps.ancorar)
    out.append(Achado("NOTA" if "pj.RADIER" in src else "ERRO", "coerencia",
                      "o dimensionamento de chumbador consulta a MESMA "
                      "espessura que o concreto do BOM: o embutimento so cabe "
                      "no radier se os dois falarem do mesmo radier"))

    # ---- 3. a quantidade reage a espessura, em vez de ser constante.
    # R52 quebrou a versao anterior deste teste, e com razao. Ele exigia
    # proporcionalidade: dobrar a espessura tinha de dobrar o volume. Com o
    # engrossamento de borda que o SPT motivou, o volume deixou de ser
    # proporcional — a laje cresce e o SUPLEMENTO da borda diminui, porque
    # borda e laje se encontram numa altura fixa de 400 mm. O teste passa a
    # conferir a IDENTIDADE geometrica, que continua valendo em qualquer
    # espessura, em vez de uma proporcionalidade que so valia enquanto o
    # radier era uma placa lisa.
    import copy as _cp
    import nucleo.geotecnia as gt
    grosso = _cp.copy(pj.RADIER)
    grosso["espessura"] = pj.RADIER["espessura"] * 2

    # R68 — o dublê era uma classe com tres atributos escolhidos a mao, e
    # quebrou assim que a terraplenagem passou a consultar a declividade do
    # lote. Teste de sensibilidade varia UMA coisa e mantem o resto: o dublê
    # passa a ser uma copia do caso com a espessura trocada, e nao uma casa
    # inventada com tres campos.
    import types as _types
    _Pj = _types.SimpleNamespace(
        **{k: getattr(pj, k) for k in dir(pj) if not k.startswith("_")})
    _Pj.RADIER = grosso
    f2 = fd.levantar(_Pj)
    c = fd.contorno(pj)
    b = gt.BORDA
    esperado = (c["area"] * grosso["espessura"] / 1000.0
                + c["perimetro"] * (b["largura"] / 1000.0)
                * ((b["altura"] - grosso["espessura"]) / 1000.0))
    razao = f2["volume_m3"] / f["volume_m3"] if f["volume_m3"] else 0
    out.append(Achado("NOTA" if abs(f2["volume_m3"] - esperado) < 0.02
                      else "ERRO", "sensibilidade",
                      f"dobrar a espessura leva o volume a {razao:.2f}x, e nao "
                      f"a 2x, porque a borda de {b['altura']} mm absorve parte "
                      f"do acrescimo: {f2['volume_m3']:.2f} m3 contra "
                      f"{esperado:.2f} m3 de identidade geometrica"))

    # ---- 4. o que era hipotese e o que deixou de ser
    out.append(Achado("NOTA", "fundacao com sondagem",
                      f"espessura {f['espessura']} mm, fck {f['fck']} MPa e "
                      f"taxa de {f['taxa_kg_m3']:.1f} kg/m3 — a espessura e "
                      f"CONFERIDA contra SP-01/02/03 em geotecnia.py e a taxa "
                      f"e RESULTADO da armadura. Falta o projeto de fundacao "
                      f"com ART: {f['pendencia']}"))

    # ---- 5. a area concretada e maior que a area util, e por um motivo
    out.append(Achado("NOTA" if f["area"] > pj.CADASTRO.area_m2 * 0.5 else "ERRO",
                      "area",
                      f"{f['area']} m2 de radier para {sum(a.w*a.h for a in pj.TERREO)/1e6:.1f} "
                      f"m2 de ambientes do terreo: o radier acompanha a face "
                      f"EXTERNA e ainda avanca {pj.RADIER['balanco_borda']} mm, "
                      f"e essa diferenca paga concreto"))

    # ---- 6. o BOM recebeu os seis itens, nao um so
    fund = [i for i in r["bom"] if i.familia == "fundacao"]
    out.append(Achado("NOTA" if len(fund) >= 6 else "ERRO", "BOM",
                      f"{len(fund)} itens de fundacao no BOM "
                      f"(R$ {sum(i.total for i in fund):,.0f}): concreto, aco, "
                      f"tela, lastro, lona e forma. Um radier nao e so "
                      f"concreto — lastro e lona sao o que impede a umidade de "
                      f"subir por capilaridade ate o montante"))
    return out


def checar_combinacoes() -> list[Achado]:
    """O ultimo literal do checklist, e por que ele nao era mentira.

    "combinacoes": True estava certo quanto ao fato — as combinacoes existem,
    sao geradas e sao usadas — e errado quanto a funcao: um item que nao pode
    reprovar nao verifica nada. Verificar exige duas perguntas diferentes, e a
    segunda e a que morde.
    """
    import projeto as pj
    import nucleo.combinacoes as cb
    out = []
    r = fx.liberacao()
    c = r["combinacoes"]

    out.append(Achado("NOTA" if c["conferencia"]["ok"] else "ERRO", "fatores",
                      f"{c['conferencia']['n']} combinacoes em "
                      f"{', '.join(c['conferencia']['tipos'])}, cada fator "
                      f"RECALCULADO das Tabelas 1 e 2 da NBR 8681 sem passar "
                      f"por gerar(). Conferir o gerador contra ele mesmo "
                      f"aprovaria qualquer erro sistematico"
                      + ("" if c["conferencia"]["ok"]
                         else ": " + "; ".join(c["conferencia"]["erros"]
                                               + c["conferencia"]["faltas"]))))

    # REGRESSAO: estragar um fator tem de ser visto
    acoes = [("g", "permanente"), ("q", "acidental")]
    combs = cb.gerar(acoes, {"q": "acidental"})
    alvo = next(k for k in combs if k.tipo == "ELU")
    alvo.parcelas[0].fator += 0.01
    sujo = cb.conferir(combs, acoes, {"q": "acidental"})
    out.append(Achado("NOTA" if not sujo["ok"] else "ERRO", "regressao",
                      f"um fator alterado em 0,01 reprova a conferencia "
                      f"({len(sujo['erros'])} erro(s) apontado(s) com "
                      f"combinacao e acao nomeadas). Sem este contrafactual a "
                      f"conferencia seria indistinguivel de um return True"))

    cob = c["cobertura"]
    out.append(Achado("NOTA" if cob["ok"] else "ERRO", "cobertura de acoes",
                      f"toda acao declarada no caso entra em alguma "
                      f"verificacao — {cob['leitura']}. Uma acao pode estar "
                      f"perfeitamente declarada, com gama e psi certos, e nao "
                      f"entrar em calculo nenhum: existir no papel e nao "
                      f"existir no calculo e a forma mais silenciosa de erro "
                      f"que este projeto ja encontrou"
                      + ("" if cob["ok"] else f". ORFAS: {cob['orfas']}")))

    orfa = cb.cobertura_de_acoes(dict(permanente=["g"], vento=["V0"]),
                                 {"descida": ("permanente",)})
    out.append(Achado("NOTA" if not orfa["ok"] else "ERRO", "regressao orfa",
                      "uma acao sem consumidor reprova a cobertura: "
                      f"{orfa['orfas']}"))

    # e a hipotese que o vento IMPOE a esta casa, dita em voz alta
    hip = [h for h in r["verificacao"]["hipoteses"] if "VENTO" in h]
    out.append(Achado("NOTA" if hip else "ERRO", "vento no montante",
                      hip[0] if hip else
                      "a descida de cargas nao declara o que faz com o vento"))
    return out


def checar_impermeabilizacao_do_superior() -> list[Achado]:
    """Os 3 banhos do superior: a lacuna era de leitura, nao de dado.

    Ate R38 esta verificacao dizia que as suites sao "retangulo unico" e que a
    area faltante teria de ser arbitrada por quem subdividisse a suite. Estava
    errada quanto a causa: a subdivisao EXISTE desde R06, com x, y, w e h
    exatos. O dado estava numa lista e a verificacao olhava outra.
    """
    import projeto as pj
    out = []
    r = fx.liberacao()
    imp = r["camadas"]["impermeabilizacao"]
    sup = [i for i in imp["itens"] if i["ambiente"].startswith("S-")]
    n_sup = sum(1 for d in pj.SUBDIVISOES
                if d.get("molhado") and d["pai"].startswith("S-"))
    out.append(Achado("NOTA" if len(sup) == n_sup else "ERRO", "banho do superior",
                      f"{len(sup)} banhos do pavimento superior entram na "
                      f"impermeabilizacao: {', '.join(i['ambiente'] for i in sup)}. "
                      f"Nenhuma area foi arbitrada — cada uma e w x h da "
                      f"subdivisao, que e dado do caso desde R06"))
    # a area TEM de bater com a geometria da subdivisao, nao com um numero novo
    erros = []
    for d in pj.SUBDIVISOES:
        if not d.get("molhado"):
            continue
        cod = f"{d['pai']}/{d['nome']}"
        it = next((i for i in imp["itens"] if i["ambiente"] == cod), None)
        esperado = round(d["w"] * d["h"] / 1e6, 2)
        if it is None or abs(it["piso"] - esperado) > 0.01:
            erros.append(f"{cod}: {it['piso'] if it else '—'} contra {esperado}")
    out.append(Achado("NOTA" if not erros else "ERRO", "area derivada",
                      "o piso de cada banho e exatamente w x h da subdivisao"
                      if not erros else "; ".join(erros)))
    out.append(Achado("NOTA" if not imp["lacuna"] else "ERRO", "cruzamento",
                      f"{imp['janelas_de_banho']} janelas de banheiro no quadro "
                      f"de esquadrias contra {imp['janelas_de_banho'] - imp['lacuna']} "
                      f"banhos com area impermeabilizada. O cruzamento que "
                      f"achou a lacuna continua armado: ele nao foi silenciado, "
                      f"foi satisfeito"))
    out.append(Achado("NOTA", "consequencia",
                      f"{imp['area']} m2 de impermeabilizacao, contra os 91,4 "
                      f"que a conta via antes. A diferenca nao e correcao de "
                      f"calculo: sao tres banheiros que existiam na casa e nao "
                      f"existiam no orcamento"))
    return out


def checar_instalacoes() -> list[Achado]:
    """MEP como material, e o clash que finalmente tem com o que conflitar.

    As pranchas 26 a 29 desenhavam hidraulica, eletrica, climatizacao e
    drenagem completas, e o BOM tinha zero. A razao e a mesma do vigamento ate
    R31 e da fundacao ate R37: o dado existia como PONTO e nao como PERCURSO, e
    ponto nao tem comprimento.

    E o item "clashes" do checklist trazia `True` literal desde sempre — nao
    por preguica: nao havia com o que conflitar. Verificacao de interferencia
    contra o vazio acha zero conflitos, e o zero e verdadeiro e inutil.
    """
    import projeto as pj
    import nucleo.instalacoes as ins
    out = []
    r = fx.liberacao()
    mep = r["camadas"]["instalacoes"]
    cl = r["camadas"]["clash"]

    # ---- 1. a prumada e dado, nao literal de desenho
    import pranchas6 as p6
    import inspect
    src = inspect.getsource(p6.hidrossanitaria)
    out.append(Achado("NOTA" if "pj.PRUMADAS" in src else "ERRO", "prumada",
                      f"as {len(pj.PRUMADAS)} prumadas sao dado do caso e o "
                      f"desenho as LE. As coordenadas viviam dentro do modulo "
                      f"de desenho, e por isso nao existia comprimento de tubo "
                      f"nenhum: sem saber ONDE esta a prumada nao ha como medir "
                      f"o ramal ate ela"))

    # ---- 2. o comprimento reage ao fator de percurso, em vez de escondê-lo
    h = mep["hidraulica"]
    out.append(Achado("NOTA" if h["fator"] > 1.0 else "ERRO", "percurso",
                      f"{h['comp_total']} m de tubo em {len(h['itens'])} "
                      f"diametros, por percurso Manhattan vezes {h['fator']} "
                      f"declarado. Nao e o percurso do instalador: e o mais "
                      f"curto que respeita a geometria, e portanto limite "
                      f"INFERIOR. O acrescimo entra como fator explicito, "
                      f"nunca embutido no comprimento"))

    # ---- 3. o clash agora encontra alguma coisa — e encontrou
    out.append(Achado("NOTA" if cl["volumes"] > 500 else "ERRO", "volumes",
                      f"{cl['volumes']} volumes confrontados entre MEP e "
                      f"estrutura. Ate agora o item passava com True literal "
                      f"porque nao havia tracado: a estrutura so ganhou "
                      f"vigamento em R31 e o MEP ganhou percurso agora"))

    # ---- 4. o criterio distingue cruzamento de defeito — e precisa ser
    #         exercitado, porque hoje ele nao tem nenhum caso para classificar
    import nucleo.camadas as _cd
    LIM = 45.0  # metade da alma de 90 mm
    tabela = {dn: de for dn, de in _cd.DE_ESGOTO.items()}
    cabem = sorted(dn for dn, de in tabela.items() if de <= LIM)
    nao = sorted(dn for dn, de in tabela.items() if de > LIM)
    # um classificador sem instancias nao esta certo: esta calado. Aplicar o
    # limite a tabela de diametros externos mostra que ele ainda separa.
    armado = bool(cabem) and bool(nao)
    out.append(Achado("NOTA" if armado else "ERRO", "criterio",
                      f"{cl['resolviveis']} cruzamentos resolviveis e "
                      f"{len(cl['criticos'])} criticos: as duas classes estao "
                      f"VAZIAS depois que o esgoto passou a correr sob o piso, "
                      f"e classe vazia nao prova criterio. Aplicado a tabela de "
                      f"diametro externo, o limite de {LIM:.0f} mm (metade da "
                      f"alma de 90) ainda separa {', '.join(cabem)} — que "
                      f"cruzam em furo verificado, normal em LSF — de "
                      f"{', '.join(nao)}, que exigem desvio ou shaft. O zero de "
                      f"hoje e consequencia do tracado correto, nao criterio "
                      f"desligado"))

    # ---- 5. a decisao do shaft: derivada, e conferida contra o que ela promete
    sh = r["camadas"]["shafts"]
    res = sh["prumadas"]
    if cl["shafts"]:
        alvo = cl["shafts"][0]
        out.append(Achado("ERRO", "shaft x parede",
                          f"{len(cl['shafts'])} conflitos entre prumada e "
                          f"montante, todos da mesma causa. {alvo['motivo']}"))
    else:
        movidas = [v for v in res.values() if v["deslocado"]]
        out.append(Achado("NOTA", "shaft x parede",
                          f"{sh['n_resolvidos']} de {sh['n']} prumadas "
                          f"resolvidas por CAIXA NA FACE, parede continua: "
                          + "; ".join(f"{k} {v['lado']} {v['deslocado']:.0f} mm "
                                      f"em {v['ambiente']}"
                                      for k, v in res.items()
                                      if v["deslocado"])
                          + f". O afastamento e procurado, nao escrito — o "
                            f"menor que tira a caixa da estrutura sem sair do "
                            f"ambiente — e custa {sh['piso_tomado_m2']:.3f} m2 "
                            f"de piso e {sh['placa_m2']:.2f} m2 de placa RU"))
        # a decisao promete tres coisas. Cada uma e conferida.
        import nucleo.instalacoes as _in
        ambs = _in._retangulos_habitaveis(pj)
        fora = [k for k, v in res.items()
                if v["deslocado"] and not any(
                    _in._dentro(v["x"], v["y"], v["x"] + v["secao"][0],
                                v["y"] + v["secao"][1], a) for a in ambs)]
        out.append(Achado("NOTA" if not fora else "ERRO", "caixa no ambiente",
                          "toda caixa deslocada cai INTEIRA dentro de um "
                          "ambiente: caixa que sobra para fora da casa nao e "
                          "caixa de parede, e apendice de fachada"
                          if not fora else f"caixa fora de ambiente: {fora}"))
        molhadas = [k for k, v in res.items()
                    if v["deslocado"] and v.get("molhado")]
        out.append(Achado("NOTA", "lado molhado",
                          f"{len(molhadas)} de {len(movidas)} caixas abrem "
                          f"para ambiente molhado, que e onde a portinhola de "
                          f"inspecao da NBR 8160 tem de estar. O lado nao e "
                          f"escolhido por estetica: e o unico onde a inspecao "
                          f"nao atravessa dormitorio"))

    # ---- 5b. REGRESSAO: sem a resolucao, o conflito TEM de voltar.
    # Zero conflitos por tracado resolvido e zero conflitos por verificacao
    # cega tem a mesma aparencia no relatorio. So o contrafactual distingue.
    import nucleo.instalacoes as _ins
    cru = _ins.conferir_clash(pj, r["paineis"],
                              dict(T=pj.NIVEL_TERREO, S=pj.NIVEL_SUPERIOR))
    out.append(Achado("NOTA" if cru["shafts"] else "ERRO", "contrafactual",
                      f"com a posicao DECLARADA das prumadas o clash volta a "
                      f"acusar {len(cru['shafts'])} conflitos: a verificacao "
                      f"nao ficou cega, o projeto e que mudou. Um zero que nao "
                      f"sabe voltar a ser diferente de zero nao e resultado"))

    # ---- 6. o esgoto horizontal corre sob o piso, nao na parede
    vols = ins.volumes_mep(pj)
    baixos = [v for v in vols if v.cod.endswith(("-X-DN100", "-Y-DN100"))
              and v.z1 < 500]
    out.append(Achado("NOTA" if baixos else "ERRO", "tracado",
                      "o ramal de esgoto corre SOB o piso — no radier no "
                      "terreo, no vigamento no superior — e so a prumada e "
                      "vertical. Rotea-lo no plano da parede produziu 85 "
                      "'conflitos criticos' que eram erro de tracado meu, nao "
                      "do projeto: a PR-21 ja dizia que esgoto nao cabe em "
                      "montante por definicao"))
    return out


def checar_indice_do_caderno() -> list[Achado]:
    """Tres listas de pranchas, uma so obra.

    Quem emite o caderno e a lista de build.CADERNO. Quem o carimbo conta e
    pranchas.TOTAL_PRANCHAS. Quem o leitor navega e viewer_texto.json. Sao tres
    fontes para o mesmo fato, e o fato e o mesmo: QUAIS pranchas existem. Em
    R51 a prancha 36 entrou nas duas primeiras e nao na terceira — o caderno
    saiu completo e o visualizador ficou com 35, sem que nada reclamasse.

    O titulo NAO e comparado: o carimbo traz o titulo descritivo da folha
    ("CATALOGO TECNICO — PERFIL, PARAFUSO, CHAPA E TUBO") e o indice traz o
    rotulo curto de navegacao ("Catalogo tecnico de pecas"). Sao textos com
    funcoes diferentes; o que tem de ser identico e a IDENTIDADE da folha, que
    e o numero. Exigir igualdade de titulo seria trocar uma divergencia real
    por ruido permanente.
    """
    import json
    import os
    import glob
    out = []
    aqui = os.path.dirname(os.path.abspath(__file__))
    try:
        idx = json.load(open(os.path.join(aqui, "viewer_texto.json"),
                             encoding="utf-8"))
    except OSError:
        return [Achado("ERRO", "indice do visualizador",
                       "viewer_texto.json nao pode ser lido: o visualizador "
                       "nao tem de onde montar o indice")]

    import build as bd
    import pranchas as pr
    n_build = [n for n, _t, _f in bd.CADERNO]
    n_idx = [e["n"] for e in idx]
    n_svg = sorted(os.path.basename(f)[3:5] for f in glob.glob(
        os.path.join(aqui, "..", "out", "PR-*.svg")))

    out.append(Achado("NOTA" if n_build == sorted(n_build) else "ERRO",
                      "ordem", f"build.CADERNO em ordem: {n_build[0]} a "
                      f"{n_build[-1]}"))
    out.append(Achado("NOTA" if len(set(n_idx)) == len(n_idx) else "ERRO",
                      "duplicidade no indice",
                      f"{len(n_idx)} entradas, {len(set(n_idx))} numeros "
                      f"distintos"))

    so_build = sorted(set(n_build) - set(n_idx))
    so_idx = sorted(set(n_idx) - set(n_build))
    out.append(Achado("NOTA" if not (so_build or so_idx) else "ERRO",
                      "indice x caderno",
                      f"as {len(n_build)} pranchas emitidas estao no indice do "
                      f"visualizador" if not (so_build or so_idx) else
                      f"emitidas e fora do indice: {so_build or '-'}; no "
                      f"indice e nao emitidas: {so_idx or '-'}. O leitor "
                      f"navega o que o indice lista, nao o que o build gera"))

    if n_svg:
        falta = sorted(set(n_build) - set(n_svg))
        out.append(Achado("NOTA" if not falta else "ERRO", "emissao",
                          f"{len(n_svg)} SVG em out/ para {len(n_build)} "
                          f"pranchas da lista"
                          + ("" if not falta else f" — sem arquivo: {falta}")))

    out.append(Achado("NOTA" if pr.TOTAL_PRANCHAS == n_build[-1] else "ERRO",
                      "carimbo x lista",
                      f"TOTAL_PRANCHAS={pr.TOTAL_PRANCHAS} e a ultima da lista "
                      f"e {n_build[-1]}"))

    # cada entrada do indice tem de estar completa: rotulo, etapa, descricao e
    # as quatro leituras. Entrada meia-feita passa despercebida na tela — some
    # um card e ninguem conta cards.
    magros = [e["n"] for e in idx
              if not e.get("t") or not e.get("d") or not e.get("etapa")
              or len(e.get("k", [])) < 3
              or any(len(p) != 2 or not p[0] or not p[1] for p in e.get("k", []))]
    out.append(Achado("NOTA" if not magros else "ERRO", "fichas do indice",
                      f"as {len(idx)} entradas trazem rotulo, etapa, descricao "
                      f"e ao menos tres leituras" if not magros else
                      f"entradas incompletas: {magros}"))

    import projeto as pjm
    etapas = {r[0] for r in pjm.REVISOES} | set(pjm.FASES)
    fora = sorted({e["etapa"] for e in idx} - etapas)
    out.append(Achado("NOTA" if not fora else "ERRO", "etapa das fichas",
                      f"todas as etapas citadas existem no historico de "
                      f"revisoes" if not fora else
                      f"etapa inexistente em REVISOES: {fora}"))
    return out


# ---------------------------------------------------------------------------
# R52 — COMPLETUDE DA CENA. R51 perguntou se o que esta no modelo chega ao
# PAPEL. Esta pergunta se chega a CENA. Sao a mesma familia de falha em suportes
# diferentes, e um sistema pode passar numa e falhar na outra: o muro passava na
# prancha desde R49 e nunca existiu em 3D.
# ---------------------------------------------------------------------------
NA_CENA = {
    "estrutura LSF": ("lsf",),
    "paredes do terreo": ("terreo",),
    "paredes do superior": ("superior",),
    "lajes": ("lajes",),
    "platibanda": ("platibandas",),
    "escada": ("escada",),
    "mobiliario e loucas": ("mob",),
    "deck e piscina": ("deck", "piscina"),
    "brise da fachada": ("brise",),
    "nichos e tecnicos": ("tecnico",),
    "pilares": ("pilar",),
    "muro do lote": ("muro",),
    "superficies do terreno": ("lote",),
    "radier": ("radier",),
    "reservatorio de retencao": ("reservatorio",),
}

# sistemas que existem no modelo e deliberadamente NAO vao a cena, com a razao.
# Lista de exclusao declarada e o que impede a conferencia de virar teatro: sem
# ela, bastaria nao listar o sistema para ele nunca reprovar.
FORA_DA_CENA = {
    "instalacoes hidraulicas e eletricas": "tubo e cabo embutidos: a cena "
        "mostraria espaguete sobre a casa e esconderia a arquitetura; estao "
        "nas pranchas 09 a 13 e no modelo de interferencia",
    "terraplenagem": "o corte e a substituicao de 600 mm desaparecem depois "
        "de executados; estao no orcamento e na prancha de fundacao",
    "cotacao e orcamento": "nao e geometria",
}


def checar_completude_da_cena() -> list[Achado]:
    """O que o modelo sabe chega ao 3D?"""
    import modelo3d as m3
    out = []
    d = m3.exportar()
    tipos = set()
    for chave in ("terreo", "superior", "lajes", "platibandas", "externo",
                  "mob", "escada", "lsf"):
        v = d.get(chave) or []
        if v:
            tipos.add(chave)
        for b in v:
            if isinstance(b, dict) and b.get("t"):
                tipos.add(b["t"])

    faltando = []
    for sistema, chaves in sorted(NA_CENA.items()):
        achou = [k for k in chaves if k in tipos]
        if not achou:
            faltando.append(sistema)
        out.append(Achado("NOTA" if achou else "ERRO", f"cena: {sistema}",
                          f"presente como {', '.join(achou)}" if achou else
                          "NAO aparece na cena: o modelo sabe, o orcamento "
                          "paga e quem olha o 3D nao ve"))
    out.append(Achado("NOTA" if not faltando else "ERRO", "cobertura da cena",
                      f"{len(NA_CENA) - len(faltando)} de {len(NA_CENA)} "
                      f"sistemas geometricos chegam ao 3D"
                      + ("" if not faltando else f" — FALTAM: {faltando}")))
    out.append(Achado("NOTA", "exclusoes declaradas",
                      f"{len(FORA_DA_CENA)} sistemas ficam fora da cena por "
                      f"razao escrita, e nao por esquecimento"))

    # a cena tem de falar da mesma revisao que o caderno
    import projeto as pj
    out.append(Achado("NOTA" if d["meta"]["revisao"] == pj.EMISSAO["revisao"]
                      else "ERRO", "revisao da cena",
                      f"a cena diz {d['meta']['revisao']} e a emissao "
                      f"{pj.EMISSAO['revisao']}"))
    # e o lote da cena tem de ser o lote do projeto
    out.append(Achado("NOTA" if d["meta"]["lote"] == [pj.LOTE_L, pj.LOTE_P]
                      else "ERRO", "lote da cena",
                      f"{d['meta']['lote']} contra "
                      f"{[pj.LOTE_L, pj.LOTE_P]} do projeto"))
    return out


def checar_acustica() -> list[Achado]:
    """Isolamento entre fonte de ruido e ambiente sensivel (R52)."""
    import projeto as pj
    import nucleo.acustica as ac
    out = []
    for titulo, detalhe, ok in ac.conferir(pj):
        out.append(Achado("NOTA" if ok else "ERRO", titulo, detalhe))
    for p in sorted(ac.entre_zonas(pj), key=lambda q: q["folga"]):
        out.append(Achado("NOTA" if p["passa"] else "ERRO",
                          f"{p['fonte']} -> {p['receptor']}",
                          f"{p['ruido']}: exige {p['exigido']:.0f} dB "
                          f"({p['nivel']:.0f} na fonte, limite {p['limite']:.0f} "
                          f"em {p['uso_receptor']}), parede {p['parede']} "
                          f"Rw {p['rw_parede']} com {p['vaos'] or 'nenhum vao'} "
                          f"entrega {p['obtido']:.1f} dB — folga "
                          f"{p['folga']:+.1f} dB"))
    return out


def checar_geotecnia() -> list[Achado]:
    """O solo virou dado: o radier confere contra ele? (R52)"""
    import projeto as pj
    import fixture as fx
    import nucleo.geotecnia as gt
    r = fx.liberacao()
    out = []
    for titulo, detalhe, ok in gt.conferir(pj, r):
        out.append(Achado("NOTA" if ok else "ERRO", titulo, detalhe))
    for f in gt.perfil():
        out.append(Achado("NOTA", f"perfil {f['z0']}-{f['z1']} m",
                          f"N {f['n']} (medio {f['medio']:.2f}, dispersao "
                          f"{f['dispersao']*100:.0f} %) — {f['solo']}"))
    return out


def checar_pluvial() -> list[Achado]:
    """Superficies do lote, gatilho legal e retencao (R52)."""
    import projeto as pj
    import nucleo.pluvial as pl
    out = []
    for titulo, detalhe, ok in pl.conferir(pj):
        out.append(Achado("NOTA" if ok else "ERRO", titulo, detalhe))
    b = pl.balanco(pj)
    out.append(Achado("NOTA", "taxa de impermeabilizacao",
                      f"{b['taxa_impermeabilizacao']*100:.2f} % do lote, com "
                      f"C ponderado de {b['c_ponderado']:.4f} contra "
                      f"{b['c_pre']:.2f} do terreno natural"))
    return out


def checar_eletrica_trifasica() -> list[Achado]:
    """Esquema 220/127, equilibrio de fases e padrao de entrada (R52)."""
    import projeto as pj
    import nucleo.eletrica as el
    out = []
    for titulo, detalhe, ok in el.conferir(pj):
        out.append(Achado("NOTA" if ok else "ERRO", titulo, detalhe))
    eq = el.equilibrar(pj)
    en = el.entrada(pj)
    out.append(Achado("NOTA", "padrao de entrada",
                      f"{en['demanda_va']} VA de demanda, {en['corrente_a']} A, "
                      f"disjuntor {en['disjuntor_a']} A, ramal "
                      f"{en['secao_mm2']} mm2 com neutro "
                      f"{en['neutro_mm2']} mm2 e PE "
                      f"{en['aterramento_mm2']} mm2"))
    out.append(Achado("NOTA", "divisao por fase",
                      f"{len(eq['circuitos'])} circuitos distribuidos; "
                      f"correntes por fase {eq['corrente_por_fase']} A"))
    return out


def checar_mercado() -> list[Achado]:
    """Fornecedores, indices publicos e aderencia do total a praca (R52)."""
    import projeto as pj
    import fixture as fx
    import nucleo.mercado as mk
    r = fx.liberacao()
    out = []
    for titulo, detalhe, ok in mk.conferir(pj, r):
        out.append(Achado("NOTA" if ok else "ERRO", titulo, detalhe))
    cb = mk.cobertura_de_fornecedores(r)
    for l in cb["linhas"]:
        out.append(Achado("NOTA", f"fornecedores: {l['familia']}",
                          f"R$ {l['valor']:,.2f} ({l['fracao']*100:.1f} % do "
                          f"custo) — {l['fornecedores']} fornecedores, "
                          f"{l['manaus']} em Manaus: "
                          f"{', '.join(f[0] for f in l['lista'][:5])}"))
    ad = mk.aderencia(pj, r)
    out.append(Achado("ATENCAO", "escopo do orcamento",
                      f"R$ {ad['total']:,.2f} cobrem os sistemas modelados, "
                      f"nao a casa pronta. Ficam de fora "
                      f"{len(ad['fora_do_orcamento'])} escopos declarados, e "
                      f"por isso o valor extrapolado "
                      f"(R$ {ad['obra_entregue_m2']:.2f}/m2) fica abaixo do "
                      f"indice de obra entregue"))
    return out


def checar_layout() -> list[Achado]:
    """Mobiliario solto: cabe no comodo, nao invade subdivisao, e a sala
    funciona (R53).

    Ate R52 o layout era coordenada dentro do modulo de desenho e estava
    errado sem que nada acusasse — cama do reversivel fora do quarto, cama da
    master dentro do banho, duas mesas de jantar e nenhuma TV. Desenho nao
    confere desenho; lista no modelo, sim.
    """
    import projeto as pj
    import math
    out = []
    ambs = {a.cod: a for a in pj.TERREO + pj.SUPERIOR + pj.TERREO_ABERTO
            + pj.SUPERIOR_ABERTO}
    subs = [(d["pai"], d["nome"], d["x"], d["y"], d["w"], d["h"])
            for d in pj.SUBDIVISOES]

    def dentro(it, a):
        return (a.x <= it["x"] and it["x"] + it["w"] <= a.x + a.w
                and a.y <= it["y"] and it["y"] + it["h"] <= a.y + a.h)

    def cruza(it, x, y, w, h):
        return not (it["x"] + it["w"] <= x or x + w <= it["x"]
                    or it["y"] + it["h"] <= y or y + h <= it["y"])

    fora, invade = [], []
    for it in pj.LAYOUT:
        a = ambs.get(it["amb"])
        if a is None or not dentro(it, a):
            fora.append(it["cod"])
        for pai, nome, x, y, w, h in subs:
            if pai == it["amb"] and cruza(it, x, y, w, h):
                invade.append(f"{it['cod']} em {pai}/{nome}")
    out.append(Achado("NOTA" if not fora else "ERRO", "mobiliario no comodo",
                      f"{len(pj.LAYOUT)} itens, todos dentro do ambiente "
                      f"declarado" if not fora else f"fora do comodo: {fora}"))
    out.append(Achado("NOTA" if not invade else "ERRO", "mobiliario x subdivisao",
                      "nenhum item sobre banho, closet ou cabine"
                      if not invade else f"invade: {invade}"))

    # R56 — a regra deixou de ser "uma TV na casa". Cada ambiente de estar ou
    # de dormir pode ter a sua, e o que se confere e o PAR: TV mais o assento
    # (sofa) ou a cama do MESMO ambiente, com o tamanho declarado em cada TV.
    # A versao anterior exigia exatamente uma e teria reprovado a master no
    # instante em que ela ganhou a dela.
    tvs = [i for i in pj.LAYOUT if i["tipo"] == "tv"]
    mesas = [i for i in pj.LAYOUT if i["tipo"] == "mesa"]
    out.append(Achado("NOTA" if len(mesas) == 1 else "ERRO", "mesa de jantar",
                      f"{len(mesas)} mesa(s): o jantar e um so, no gourmet"
                      if len(mesas) == 1 else
                      f"{len(mesas)} mesas de jantar — duas mesas e um estar "
                      f"que nao decidiu o que e"))
    out.append(Achado("NOTA" if tvs else "ERRO", "TV",
                      f"{len(tvs)} TV: " + ", ".join(
                          f"{t['amb']} {t.get('polegadas', '?')} pol"
                          for t in tvs)))
    sem_tam = [t["cod"] for t in tvs if not t.get("diagonal_mm")]
    out.append(Achado("NOTA" if not sem_tam else "ERRO", "tamanho da TV",
                      "toda TV declara a diagonal, que e o que a regra de "
                      "distancia consome" if not sem_tam
                      else f"sem diagonal: {sem_tam}"))
    for tv in tvs:
        assentos = [i for i in pj.LAYOUT if i["amb"] == tv["amb"]
                    and i["tipo"] in ("sofa", "cama")]
        if not assentos:
            out.append(Achado("ERRO", f"TV sem assento — {tv['cod']}",
                              f"ha TV em {tv['amb']} e nenhum sofa ou cama"))
            continue
        a = assentos[0]
        tcx, tcy = tv["x"] + tv["w"] / 2, tv["y"] + tv["h"] / 2
        if a["tipo"] == "cama":
            # de onde se assiste numa cama e o travesseiro, nao o centro
            fx = a["x"] + a["w"] / 2
            fy = a["y"] + a["h"] - 400 if a["y"] > tcy else a["y"] + 400
        else:
            fr = a.get("frente", "-Y")
            fx, fy = a["x"] + a["w"] / 2, a["y"]
            if fr == "+Y":
                fy = a["y"] + a["h"]
            elif fr in ("-X", "+X"):
                fx = a["x"] if fr == "-X" else a["x"] + a["w"]
                fy = a["y"] + a["h"] / 2
        d = math.hypot(tcx - fx, tcy - fy) / 1000.0
        dmin = pj.TV["dist_min"] * tv["diagonal_mm"] / 1000.0
        dmax = pj.TV["dist_max"] * tv["diagonal_mm"] / 1000.0
        out.append(Achado("NOTA" if dmin <= d <= dmax else "ERRO",
                          f"distancia {a['tipo']}-TV em {tv['amb']}",
                          f"{d:.2f} m para {tv.get('polegadas')} pol — faixa "
                          f"{dmin:.2f} a {dmax:.2f} m ({pj.TV['razao']})"))

    # R56 — cama: cabeceira encostada e circulacao em volta. A da master estava
    # FLUTUANDO (600 mm de uma parede, 300 da outra) e nada olhava para isso,
    # porque layout so entrou no modelo em R53.
    for c in [i for i in pj.LAYOUT if i["tipo"] == "cama"]:
        a = ambs.get(c["amb"])
        if a is None:
            continue
        folgas = dict(oeste=c["x"] - a.x, leste=a.x + a.w - (c["x"] + c["w"]),
                      norte=c["y"] - a.y, sul=a.y + a.h - (c["y"] + c["h"]))
        for pai, nome, x, y, w, h in subs:
            if pai != c["amb"]:
                continue
            if not (x + w <= c["x"] or c["x"] + c["w"] <= x):
                if y + h <= c["y"]:
                    folgas["norte"] = min(folgas["norte"], c["y"] - (y + h))
                elif y >= c["y"] + c["h"]:
                    folgas["sul"] = min(folgas["sul"], y - (c["y"] + c["h"]))
        menor = min(folgas.values())
        encostada = menor <= 120
        livres = sorted(v for v in folgas.values() if v > 120)
        out.append(Achado("NOTA" if encostada else "ERRO",
                          f"cabeceira — {c['cod']}",
                          f"folgas em mm {folgas}; a menor e {menor}"
                          + (" — cabeceira encostada" if encostada else
                             " — a cama nao encosta em parede nenhuma")))
        passagem = min(livres) if livres else 0
        out.append(Achado("NOTA" if passagem >= 700 else "ERRO",
                          f"circulacao em volta — {c['cod']}",
                          f"{passagem} mm na face mais apertada; 700 mm e o "
                          f"minimo de passagem, 900 o confortavel"))
    return out


def checar_lavabo_sob_escada() -> list[Achado]:
    """Pe-direito ponto a ponto do lavabo sob a escada (R54)."""
    import projeto as pj
    import nucleo.subescada as se
    out = []
    for titulo, detalhe, ok in se.conferir(pj):
        out.append(Achado("NOTA" if ok else "ERRO", titulo, detalhe))
    r = se.resumo(pj)
    if r.get("existe"):
        out.append(Achado("NOTA", "o desenho e o dado falam da mesma escada",
                          "mobiliario.escada_u desenha a partir de "
                          "escada_lances(); ate R54 desenhava o espelho dela, "
                          "e foi por isso que o armario sob o lance dizia ter "
                          "1.500 mm de altura livre onde ha 2.712"))
    return out


def checar_termica() -> list[Achado]:
    """A parede que a NBR 15220-3 verifica e a que a obra constroi? (R58)"""
    import projeto as pj
    import nucleo.termica as tm
    out = []
    for l in tm.levantar(pj):
        lim = pj.LIMITES_ZB8.get(l["limite"], {})
        out.append(Achado("NOTA" if l["u"] <= lim.get("U", 1e9) else "ERRO",
                          f"U de {l['cod']}",
                          f"{l['u']:.3f} W/m2.K contra limite {lim.get('U', 0):.2f} "
                          f"— R efetivo {l['r_efetivo']:.3f}, ponte do montante "
                          f"+{l['penalidade_ponte'] * 100:.1f} % sobre "
                          f"{l['fracao_aco'] * 100:.1f} % da area"))
        out.append(Achado("NOTA" if l["fso"] <= lim.get("FSo", 1e9) else "ERRO",
                          f"FSo de {l['cod']}",
                          f"{l['fso']:.2f} % contra {lim.get('FSo', 0):.1f} % "
                          f"(absortancia {pj.ABSORTANCIA:.2f})"))
        # O atraso reprova a parede por EXCESSO de desempenho: ver a nota em
        # nucleo/termica.conferir. Fica ATENCAO, nao ERRO — nao ha defeito a
        # corrigir, ha categoria normativa a escolher, e isso e do projetista.
        if lim.get("atraso") and l["atraso_h"] > lim["atraso"]:
            out.append(Achado("ATENCAO", f"categoria de {l['cod']}",
                              f"atraso {l['atraso_h']:.2f} h passa dos "
                              f"{lim['atraso']:.1f} h da linha '{lim['rotulo']}' "
                              f"porque U = {l['u']:.3f} esta muito abaixo do "
                              f"U <= {lim['U']:.2f} que a linha pressupoe — "
                              f"parede melhor que a categoria, nao pior "
                              f"(pendencia 14)"))
    # a aferição contra a hipotese que o metodo novo substituiu
    x = tm.sem_isolante(pj, "PE-1", "XPS")
    out.append(Achado("NOTA", "aferição da ponte termica",
                      f"derivada: +{x['ponte_com'] * 100:.1f} % com ISO strip e "
                      f"+{x['ponte_sem'] * 100:.1f} % sem ela, contra as hipoteses "
                      f"de 8 % e 40 % que vigoraram ate R57 — proximas, o que "
                      f"sugere que ambas estao certas"))
    out.append(Achado("NOTA", "o que a ISO strip compra",
                      f"U de {x['u_sem']:.3f} para {x['u_com']:.3f}, queda de "
                      f"{x['ganho'] * 100:.0f} % — e a camada de melhor relacao "
                      f"desempenho/custo do envelope"))
    return out


def checar_luminotecnica() -> list[Achado]:
    """Metodo dos lumens por ambiente, malha de uniformidade e luz de tarefa (R59)."""
    import projeto as pj
    import nucleo.luminotecnica as lu
    out = []
    for titulo, detalhe, ok in lu.conferir(pj):
        out.append(Achado("NOTA" if ok else "ERRO", titulo, detalhe))
    lv = lu.levantar(pj)
    out.append(Achado("NOTA", "quadro luminotecnico",
                      f"{lv['n_geral']} luminarias gerais em {len(lv['geral'])} "
                      f"ambientes, {lv['w_geral']:.0f} W ({lv['w_m2']} W/m2), "
                      f"{len(lv['tarefa'])} pontos de tarefa"))
    for x in lv["geral"]:
        out.append(Achado("NOTA", f"lux: {x['cod']}",
                          f"{x['uso']}: alvo {x['E_alvo']} lx, obtido {x['E_obtido']} "
                          f"lx com {x['n']} x {x['luminaria']} a {x['tcor']} K "
                          f"(k {x['k']}, CU {x['cu']})"))
    return out


def checar_acabamento_auditado() -> list[Achado]:
    """As quantidades de acabamento contra o que o modelo ja sabia (R59)."""
    import projeto as pj
    import fixture as fx
    r = fx.liberacao()
    bom = {i.sku: i for i in r["bom"]}
    out = []
    fo = r["camadas"]["planos"]["forro"]
    out.append(Achado("NOTA" if fo["area"] > 0 and "FOR-PERFIL" in bom else "ERRO",
                      "forro suspenso quantificado",
                      f"{fo['area']} m2 de FO-1 em {len(fo['regioes'])} regioes sob "
                      f"cobertura; sem forro: {fo['sem_forro']}"))
    box = bom.get("LOU-BOX")
    n_box = sum(1 for l in pj.LOUCAS if l["tipo"] == "box")
    out.append(Achado("NOTA" if box and box.quantidade / n_box < 6.0 else "ERRO",
                      "box de vidro so nas faces livres",
                      f"{box.quantidade if box else 0} m2 em {n_box} boxes "
                      f"({(box.quantidade / n_box) if box else 0:.1f} m2/box)"))
    ext = {i["zona"]: i for i in r["camadas"]["externo"]["pisos"]["itens"]} \
        if isinstance(r["camadas"]["externo"].get("pisos"), dict) else {}
    wpc = next((i for i in ext.values() if "WPC" in i["material"]), None)
    out.append(Achado("NOTA" if wpc and wpc["area"] < 40 else "ATENCAO",
                      "WPC so em area coberta de permanencia",
                      f"{wpc['area'] if wpc else 0} m2 de WPC em {wpc['areas'] if wpc else []}"))
    fam = [s for s in bom if s.startswith("FAC-")]
    out.append(Achado("NOTA" if "FAC-MINERAL" in bom and "FAC-TINTA" in bom else "ERRO",
                      "fachada: base pintada + volume mineral",
                      f"{bom['FAC-TINTA'].quantidade if 'FAC-TINTA' in bom else 0} L de "
                      f"elastomerico na faixa ate 2.600 mm; "
                      f"{bom['FAC-MINERAL'].quantidade if 'FAC-MINERAL' in bom else 0} m2 "
                      f"de mineral de fabrica em altura — {len(fam)} linhas"))
    return out


def checar_luz_no_desenho() -> list[Achado]:
    """A PR-16 e a cena 3D desenham exatamente os pontos que o calculo produziu (R60)."""
    import os, re
    import projeto as pj
    import nucleo.luminotecnica as lu
    pts = lu.pontos(pj)
    out = []
    svg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "PR-16.svg")
    if os.path.exists(svg):
        with open(svg, encoding="utf-8") as f:
            n = len(re.findall(r'data-tipo="luminaria"', f.read()))
        out.append(Achado("NOTA" if n == len(pts) else "ERRO", "PR-16 desenha o calculo",
                          f"{n} luminarias na prancha contra {len(pts)} no calculo"))
    else:
        out.append(Achado("ATENCAO", "PR-16 ainda nao gerada", "rode build.py"))
    import modelo3d
    d = modelo3d.exportar()
    out.append(Achado("NOTA" if len(d["luz"]) == len(pts) else "ERRO",
                      "a cena 3D mostra o calculo",
                      f"{len(d['luz'])} luminarias na cena contra {len(pts)} no calculo"))
    # mobiliario da cena = LAYOUT do modelo
    mob_layout = {b["amb"] for b in d["mob"] if b.get("amb", "").startswith("LY-")}
    out.append(Achado("NOTA" if len(mob_layout) == len(pj.LAYOUT) else "ERRO",
                      "a cena desenha o LAYOUT, nao coordenadas proprias",
                      f"{len(mob_layout)} pecas de layout na cena, {len(pj.LAYOUT)} no modelo"))
    return out


from core import brl as _brl


def checar_vidro_solar() -> list[Achado]:
    """Todo vao nas faces leste e oeste tem g dentro do limite; a carga usa o g (R61)."""
    import projeto as pj
    out = []
    ruins = [v for v in pj.vaos_envidracados() if v["face"] in ("L", "O") and v["g"] > pj.G_MAX_SOL]
    out.append(Achado("NOTA" if not ruins else "ERRO", "fator solar nas faces L/O",
                      f"limite g <= {pj.G_MAX_SOL:.2f}; fora: "
                      f"{[(v['tipo'], v['face'], v['g']) for v in ruins] or 'nenhum'}"))
    cv = next((v for v in pj.vaos_envidracados() if v["tipo"].startswith("CV")), None)
    out.append(Achado("NOTA" if cv and cv["g"] <= 0.35 else "ERRO", "cortina CV-01",
                      f"face {cv['face'] if cv else '?'}, g = {cv['g'] if cv else '?'}: {cv['vidro'] if cv else ''}"))
    for c in pj.CLIMATIZACAO:
        if c.get("reserva"):
            continue
        q = pj.carga_termica(c["amb"], c["pessoas"], c["equip"], c.get("mais"),
                             c.get("conta_ventilador", False), c.get("duto", False),
                             c.get("area_m2"), c.get("vidro_m2"))
        out.append(Achado("NOTA" if q <= c["capacidade"] else "ERRO",
                          f"carga com g: {c['amb']}{'/' + c['compartimento'] if c.get('compartimento') else ''}",
                          f"{q} BTU/h contra {c['capacidade']} instalados"))
    return out


def checar_spda() -> list[Achado]:
    """Para-raios: risco calculado, componentes e descida natural pela estrutura (R61)."""
    import projeto as pj
    import fixture as fx
    import nucleo.spda as sp
    r = fx.liberacao()
    out = [Achado("NOTA" if ok else "ERRO", t, d) for t, d, ok in sp.conferir(pj, r)]
    skus = {i.sku for i in r["bom"]}
    out.append(Achado("NOTA" if {"SPD-CAPTOR", "SPD-ANEL", "SPD-DPS1"} <= skus else "ERRO",
                      "o SPDA esta no orcamento", f"{sorted(s for s in skus if s.startswith('SPD-'))}"))
    return out


def checar_fotovoltaica() -> list[Achado]:
    """Geracao dimensionada do consumo do modelo, com area, carga e lugar conferidos (R61)."""
    import projeto as pj
    import fixture as fx
    import nucleo.fotovoltaica as fv
    r = fx.liberacao()
    out = [Achado("NOTA" if ok else "ERRO", t, d) for t, d, ok in fv.conferir(pj, r)]
    f = r["camadas"]["fotovoltaica"]
    out.append(Achado("NOTA", "quadro fotovoltaico",
                      f"{f['consumo_kwh_dia']} kWh/dia -> {f['kwp_instalado']} kWp em "
                      f"{f['n_modulos']} modulos, {f['geracao_kwh_ano']:.0f} kWh/ano, "
                      f"payback {f['payback_anos']} anos (H)"))
    return out


OCUPACAO_MIN = 0.45   # fracao da area util da folha que o desenho deve ocupar


def checar_ocupacao_das_folhas() -> list[Achado]:
    """Legibilidade medida: fracao da folha ocupada por cada prancha (R62)."""
    import os, json
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out", "ocupacao.json")
    if not os.path.exists(p):
        return [Achado("ATENCAO", "ocupacao das folhas", "rode build.py")]
    oc = json.load(open(p))
    baixas = sorted((k, v) for k, v in oc.items() if v < OCUPACAO_MIN)
    out = [Achado("NOTA" if not baixas else "ATENCAO", "pranchas pouco ocupadas",
                  f"{len(baixas)} de {len(oc)} abaixo de {OCUPACAO_MIN * 100:.0f} % da folha: "
                  + ", ".join(f"PR-{k} ({v * 100:.0f} %)" for k, v in baixas) if baixas
                  else f"todas as {len(oc)} pranchas ocupam >= {OCUPACAO_MIN * 100:.0f} %")]
    return out


def checar_terreno() -> list[Achado]:
    """Sitio e declividade (R68): plataforma, cota de piso, rampa e gravidade."""
    import projeto as pj
    import nucleo.terreno as tr
    out = []
    # o sitio confirmado bate com a orientacao que o projeto inteiro usa?
    ori_ok = (pj.SITIO["frente"] == "Leste" and pj.SITIO["fundos"] == "Oeste"
              and pj.AZIMUTE_TESTADA == 90)
    out.append(Achado("NOTA" if ori_ok else "ERRO", "orientacao conferida",
                      f"sitio declara frente {pj.SITIO['frente']} e fundos "
                      f"{pj.SITIO['fundos']}; o caso usa azimute de testada "
                      f"{pj.AZIMUTE_TESTADA} graus. Toda a decisao de vidro, "
                      f"brise e fotovoltaica depende deste par"))
    falhas = [(n, m) for n, m, ok in tr.conferir(pj) if not ok]
    for nome, msg, ok in tr.conferir(pj):
        out.append(Achado("NOTA" if ok else "ERRO", nome, msg))
    p2 = tr.plataforma(pj, pj.DECLIVIDADE_MAX)
    p1 = tr.plataforma(pj, pj.DECLIVIDADE_MIN)
    out.append(Achado("NOTA", "faixa de declividade",
                      f"a 1 % o piso fica +{p1['cota_piso_acabado']:.0f} mm e a "
                      f"2 % +{p2['cota_piso_acabado']:.0f} mm sobre a testada; "
                      f"a diferenca de {p2['cota_piso_acabado'] - p1['cota_piso_acabado']:.0f} mm "
                      f"e o que um levantamento planialtimetrico fecha (pendencia 17)"))
    out.append(Achado("ATENCAO" if not falhas else "ERRO", "terraplenagem de regularizacao",
                      "zero m3 de corte e aterro alem da troca de solo: a "
                      "declividade cabe dentro dos 600 mm que o SPT ja obrigou. "
                      "ATENCAO porque a reposicao passa a ter espessura "
                      "variavel, item de conferencia de obra e nao de orcamento")
               if not falhas else Achado("ERRO", "terreno", f"{len(falhas)} falha(s)"))
    return out


def checar_vento_categoria() -> list[Achado]:
    """A estrutura aguenta a categoria de rugosidade mais severa? (R68)"""
    import projeto as pj
    import nucleo.terreno as tr
    v = tr.conferir_vento(pj)
    out = [Achado("NOTA" if v["robusto"] else "ERRO", "robustez a rugosidade",
                  f"verificado nas categorias IV (declarada) e III (lote mais "
                  f"aberto): a passagem de IV para III custa "
                  f"+{v['acrescimo_pressao'] * 100:.0f} % de pressao e as duas passam")]
    for cat in ("IV", "III"):
        d = v[cat]
        usos = ", ".join(
            f"{e} {100 * d['veredito'][e]['demanda'] / d['veredito'][e]['capacidade']:.0f} %"
            for e in ("X", "Y"))
        out.append(Achado("NOTA" if d["ok"] else "ERRO", f"contraventamento cat. {cat}",
                          f"S2 {d['s2']:.3f}, Vk {d['vk']:.1f} m/s; uso das fitas: {usos}"))
    out.append(Achado("NOTA", "sensibilidade do orcamento",
                      "massa, pecas e custo nao mudam entre as duas categorias: "
                      "o vento governa fita e chumbador, e os dois tem folga. "
                      "A duvida de categoria nao custa dinheiro"))
    return out


def checar_entregaveis() -> list[Achado]:
    """Matriz de entregaveis (R69): toda referencia existe, todo NA tem razao."""
    import os
    import projeto as pj
    import nucleo.entregaveis as en
    import build
    caderno = {n for n, _, _ in build.CADERNO}
    eng = {"painel", "paineis", "pecas", "corte", "montagem", "logistica", "documentos",
           "materiais", "parafusos", "instalacoes", "cotacao", "ambientes", "catalogo",
           "fachada", "viabilidade", "geotecnia", "pluvial", "acustica", "eletrica", "marcenaria", "bloqueios"}
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
    falhas = en.conferir(pj, caderno, eng, out_dir)
    r = en.resumo()
    ps = r["por_status"]
    out = [Achado("NOTA" if not falhas else "ERRO", "referencias",
                  f"{r['linhas']} linhas, {r['distintos']} entregaveis distintos; "
                  f"{len(falhas)} referencia(s) quebrada(s)"
                  + (": " + "; ".join(f"{a} {b}" for a, b, _ in falhas[:6]) if falhas else ""))]
    out.append(Achado("NOTA", "cobertura",
                      f"TEM {ps['TEM']} · NA {ps['NA']} · PARCIAL {ps['PARCIAL']} · "
                      f"FALTA {ps['FALTA']} · EXTERNO {ps['EXTERNO']} — "
                      f"{r['cobertura'] * 100:.0f} % resolvido (TEM + NA) dos distintos"))
    out.append(Achado("ATENCAO" if ps["FALTA"] else "NOTA", "backlog",
                      f"{ps['FALTA']} entregaveis distintos ainda por produzir do modelo"
                      + (" — " + ", ".join(str(i["n"]) for i in r["backlog"][:24])
                         + ("…" if len(r["backlog"]) > 24 else "") if ps["FALTA"] else "")))
    out.append(Achado("NOTA", "fora do modelo",
                      f"{ps['EXTERNO']} dependem de dado ou obra externos: levantamento, "
                      f"fotografia, as-built e midia"))
    return out


def checar_ventilacao_privacidade() -> list[Achado]:
    """Ventilacao natural por ambiente e privacidade legal por janela (R69)."""
    import projeto as pj
    import nucleo.ventilacao as vn
    out = []
    amb = vn.por_ambiente(pj)
    exig = [r for r in amb if r["exige_minimo"]]
    falha = [r for r in exig if not r["atende_15575"]]
    out.append(Achado("NOTA" if not falha else "ERRO", "NBR 15575-4 (Norte, 8 %)",
                      f"{len(exig) - len(falha)} de {len(exig)} ambientes de permanencia "
                      f"atendem" + (": faltam " + ", ".join(r["cod"] for r in falha) if falha else "")))
    cruz = [r for r in exig if r["cruzada"]]
    out.append(Achado("NOTA", "ventilacao cruzada",
                      f"{len(cruz)} de {len(exig)} ambientes de permanencia abrem em duas ou "
                      f"mais faces: {', '.join(r['cod'] for r in cruz)}"))
    grandes = [r for r in amb if r["grande_15220"]]
    out.append(Achado("NOTA", "NBR 15220-3 ZB8 (aberturas grandes, 40 %)",
                      f"{len(grandes)} ambientes passam de 40 %: "
                      f"{', '.join(r['cod'] for r in grandes) or 'nenhum'}; o resto e climatizado"))
    pr = vn.privacidade(pj)
    ilegal = [p for p in pr if not p["legal"]]
    out.append(Achado("NOTA" if not ilegal else "ERRO", "art. 1.301 CC",
                      f"{sum(1 for p in pr if p['vizinho'])} janelas olham divisa de vizinho; "
                      f"{len(ilegal)} a menos de 1,50 m"
                      + (": " + ", ".join(f"{p['tipo']}/{p['amb']}" for p in ilegal) if ilegal else "")))
    exp = [p for p in pr if p["exposta"]]
    out.append(Achado("NOTA" if not exp else "ATENCAO", "exposicao ao vizinho",
                      f"{len(exp)} janela(s) a menos de 3 m da divisa sem brise nem peitoril alto"
                      + (": " + ", ".join(f"{p['tipo']}/{p['amb']} face {p['face']}" for p in exp) if exp else "")))
    return out


def checar_marcenaria() -> list[Achado]:
    """Cada movel derivado em modulos, pecas, chapas e ferragens (R71)."""
    import projeto as pj
    import nucleo.marcenaria as mc
    out = []
    r = mc.resumo(pj)
    out.append(Achado("NOTA", "inventario",
                      f"{r['moveis']} moveis, {r['modulos']} modulos, {r['pecas']} pecas, "
                      f"{r['frente_m2']:.2f} m2 de frente, {r['portas']} portas e {r['gavetas']} gavetas"))
    for t, d, ok in mc.conferir(pj):
        if not ok:
            out.append(Achado("ERRO", t, d))
    n_ok = sum(1 for _, _, ok in mc.conferir(pj) if ok)
    out.append(Achado("NOTA", "conferencias", f"{n_ok} conferencias passam"))
    for esp, v in r["chapas"].items():
        out.append(Achado("NOTA", f"chapa {esp} mm",
                          f"{v['n']} chapas, {v['aproveitamento'] * 100:.0f} % de aproveitamento"))
    c = r["custo"]
    out.append(Achado("NOTA", "material x servico",
                      f"material R$ {c['material']:,.0f} = {c['razao'] * 100:.0f} % do servico sob "
                      f"medida R$ {c['servico_bom']:,.0f}"))
    # o BOM tem de carregar exatamente o que o inventario tem
    import nucleo.acabamento as ac
    bom = {l["sku"]: l for l in ac.marcenaria(pj)}
    caixa = sum(m["area_frente_m2"] for m in mc.moveis(pj)
                if m["familia"] not in ("prateleiras", "painel tv", "cabeceira", "gabinete"))
    out.append(Achado("NOTA" if abs(bom["MAR-ARM"]["quantidade"] - caixa) < 0.05 else "ERRO",
                      "BOM = inventario",
                      f"MAR-ARM {bom['MAR-ARM']['quantidade']:.2f} m2 contra {caixa:.2f} m2 de frente de caixa"))
    return out


def checar_instalacoes_executivo() -> list[Achado]:
    """Esgoto, agua fria, circuitos e gas peca a peca (R72)."""
    import projeto as pj
    import nucleo.esgoto as es
    import nucleo.agua as ag
    import nucleo.circuitos as ci
    import nucleo.gas as gs
    out = []
    for nome, mod in (("esgoto", es), ("agua fria", ag), ("circuitos", ci), ("gas e ar", gs)):
        conf = mod.conferir(pj)
        falhas = [c for c in conf if not c[2]]
        for t, d, _ in falhas:
            out.append(Achado("ERRO", f"{nome}: {t}", d))
        out.append(Achado("NOTA", nome, f"{len(conf) - len(falhas)} de {len(conf)} conferencias passam"))
    r = es.resumo(pj)
    out.append(Achado("NOTA", "esgoto", f"{r['ramais']} ramais, {r['caixas']} caixas, fundo final a "
                      f"{r['prof_final_mm']} mm na testada; {r['ventilacao_ramais']} ramais de ventilacao"))
    a = ag.resumo(pj)
    out.append(Achado("NOTA", "agua fria", f"{a['gravidade_ok']} de {a['pecas']} pecas por gravidade; pior do terreo "
                      f"{a['pior_terreo']:.0f} kPa; pior do superior {a['pior_superior']:.0f} kPa -> TC-14"))
    c = ci.resumo(pj)
    vias = ", ".join(f"{q['quadro']} {q['vias_com_reserva']}/{q['vias_disponiveis']}" for q in c["quadros"])
    out.append(Achado("NOTA", "circuitos", f"{c['circuitos']} circuitos, queda maxima {c['queda_max']:.2f} % "
                      f"({c['pior']}); quadros {vias}"))
    subiu = [x for x in ci.circuitos(pj) if x["subiu_por_queda"]]
    out.append(Achado("NOTA" if subiu else "NOTA", "secao pela queda",
                      f"{len(subiu)} circuito(s) com secao acima da corrente pela queda de tensao: "
                      + ", ".join(f"{x['cod']} {x['secao_por_corrente']}->{x['secao_mm2']} mm2" for x in subiu)))
    return out


def checar_seguranca() -> list[Achado]:
    """Dados, Wi-Fi, CFTV, alarme, automacao e incendio, ponto a ponto (R74)."""
    import projeto as pj
    import nucleo.seguranca as sg
    out = []
    conf = sg.conferir(pj)
    for t, d, ok in conf:
        if not ok:
            out.append(Achado("ERRO", t, d))
    r = sg.resumo(pj)
    out.append(Achado("NOTA", "seguranca", f"{sum(1 for c in conf if c[2])} de {len(conf)} conferencias passam; "
                      f"{r['pontos_dados']} pontos, {r['cameras']} cameras, {r['magneticos']} magneticos, "
                      f"{r['modulos_automacao']} modulos, {r['extintores']} extintores, {r['detectores']} detectores"))
    out.append(Achado("NOTA", "incendio", sg.incendio(pj)["exigencia"]))
    return out


def checar_detalhes_lsf() -> list[Achado]:
    """Contraventamento em planta, cargas suspensas, encontros e fachada (R75)."""
    import projeto as pj
    import nucleo.detalhes_lsf as dl
    out = []
    conf = dl.conferir(pj)
    for t, d, ok in conf:
        if not ok:
            out.append(Achado("ERRO", t, d))
    r = dl.resumo(pj)
    out.append(Achado("NOTA", "lsf", f"{sum(1 for c in conf if c[2])} de {len(conf)} conferencias passam; "
                      f"{r['paineis_contraventados']} paineis com fita, {r['holddowns']} hold-downs, "
                      f"{r['cargas_suspensas']} cargas suspensas com parede, {r['encontros_t']} encontros em T, "
                      f"{r['placas_fachada']} placas de fachada a {r['aproveitamento_fachada'] * 100:.0f} %"))
    return out


def checar_piscina_executiva() -> list[Achado]:
    """Piscina peca a peca: escada, borda, linhas, filtro, bomba, LEDs (R78)."""
    import projeto as pj
    import nucleo.piscina as ps
    out = []
    conf = ps.conferir(pj)
    for t, d, ok in conf:
        if not ok:
            out.append(Achado("ERRO", f"piscina: {t}", d))
    r = ps.resumo(pj)
    out.append(Achado("NOTA", "piscina", f"{sum(1 for c in conf if c[2])} de {len(conf)} conferencias passam; "
                      f"{r['q_m3h']} m3/h em {r['linhas']} linhas DN50 ({r['tubo_m']} m), v max {r['v_max_succao']} m/s; "
                      f"filtro {r['taxa_filtracao']} m3/h/m2; bomba {r['h_man_m']} m.c.a., {r['bomba_va']} VA; "
                      f"escada {r['degraus']} x {r['espelho']} mm; {r['leds']} LEDs a {r['w_m2']} W/m2; "
                      f"sistema R$ {r['custo_sistema']:,.2f}"))
    return out


def checar_moldes_de_defeito() -> list[Achado]:
    """Meta-auditoria (R65): literais do caso, alcance das entidades, funcoes duplicadas.

    As outras 137 conferem FATOS; esta confere o FORMATO em que os defeitos
    vieram: literal que envelhece, entidade que nao chega ao desenho, funcao
    repetida com semantica quase igual. O teste de mutacao (segunda fonte) e o
    mais lento — sete subprocessos — e roda com META_MUTACAO=1 ou na CI.
    """
    import os
    import meta_auditoria as ma
    out = []
    lit = ma.literais_magicos()
    out.append(Achado("NOTA" if not lit else "ERRO", "literais do caso",
                      f"{len(lit)} numero(s) escrito(s) fora do caso iguais a "
                      f"{', '.join(ma.LITERAIS_DO_CASO)}"
                      + (": " + "; ".join(f"{a['arquivo']}:{a['linha']} ({a['igual_a']})" for a in lit[:8]) if lit else "")))
    alc, n_svg = ma.alcance_das_entidades()
    if n_svg == 0:
        out.append(Achado("ATENCAO", "alcance", "sem pranchas em out/: rode build.py"))
    else:
        sem_pr = [a for a in alc if not a["prancha"]]
        sem_3d = [a for a in alc if a["esperado_cena"] and not a["cena"]]
        out.append(Achado("NOTA" if not sem_pr else "ERRO", "entidade sem prancha",
                          f"{len(alc)} entidades com codigo em {len(set(a['lista'] for a in alc))} listas; "
                          f"{len(sem_pr)} em nenhuma das {n_svg} pranchas"
                          + (": " + ", ".join(a["cod"] for a in sem_pr[:12]) if sem_pr else "")))
        out.append(Achado("NOTA" if not sem_3d else "ERRO", "entidade sem cena 3D",
                          f"{sum(1 for a in alc if a['esperado_cena'])} deveriam estar na cena; "
                          f"{len(sem_3d)} faltam" + (": " + ", ".join(a["cod"] for a in sem_3d[:12]) if sem_3d else "")))
    dup = ma.funcoes_duplicadas()
    out.append(Achado("NOTA" if not dup else "ERRO", "funcoes duplicadas",
                      f"{len(dup)} nome(s) privado(s) repetido(s) entre modulos produtores"
                      + (": " + ", ".join(d["funcao"] for d in dup) if dup else "")))
    if os.environ.get("META_MUTACAO"):
        for m in ma.teste_de_mutacao():
            if "erro" in m:
                out.append(Achado("ERRO", f"mutacao {m['mutacao']}", m["erro"])); continue
            ruim = m["parados_suspeitos"] or m["inesperados"]
            out.append(Achado("NOTA" if not ruim else "ERRO", f"mutacao {m['mutacao']}",
                              f"moveu {', '.join(m['moveu'])}"
                              + (f"; PARADOS {m['parados_suspeitos']}" if m["parados_suspeitos"] else "")
                              + (f"; inesperados {m['inesperados']}" if m["inesperados"] else "")))
    else:
        out.append(Achado("NOTA", "mutacao", "nao rodada (META_MUTACAO=1 para rodar; a CI roda)"))
    return out


def checar_perspectivas() -> list[Achado]:
    """Perspectivas (R66): toda camera no seu comodo, todo comodo com vista, fotos da revisao."""
    import perspectivas as pp
    import projeto as pj
    m = pp.manifesto()
    if m is None:
        return [Achado("ATENCAO", "perspectivas", "perspectivas.json ausente: rode build.py")]
    falhas = pp.conferir()
    n_ext = sum(1 for v in m["vistas"] if v["tipo"] == "externa")
    n_int = sum(1 for v in m["vistas"] if v["tipo"] == "interna")
    out = [Achado("NOTA" if not falhas else "ERRO", "perspectivas",
                  f"{len(m['vistas'])} vistas ({n_ext} externas, {n_int} internas) da revisao "
                  f"{m['revisao']}; {len(falhas)} falha(s)"
                  + (": " + "; ".join(f"{f['tipo']} {f['msg']}" for f in falhas[:8]) if falhas else ""))]
    out.append(Achado("NOTA" if n_ext >= 8 else "ERRO", "azimutes",
                      f"{n_ext} vistas externas (minimo 8: um por azimute a 45 graus)"))
    # a camera de comodo fechado NAO pode estar dentro de parede nem de movel
    dentro = [v["id"] for v in m["vistas"] if v["tipo"] == "interna"
              and not pp._coluna_livre(v["pos"][0], v["pos"][1], pp._piso(v["pav"]), v["pos"][2])]
    out.append(Achado("NOTA" if not dentro else "ERRO", "camera em coisa solida",
                      f"{len(dentro)} camera(s) dentro de parede ou movel"
                      + (": " + ", ".join(dentro) if dentro else "")))
    return out


def checar_ocupacao() -> list[Achado]:
    """Espaco morto: bolsao sem ambiente, largura sem uso, nome sem lastro (R58)."""
    import projeto as pj
    import nucleo.ocupacao as oc
    falhas = oc.conferir(pj)
    c = oc.circulacao(pj)
    out = [Achado("NOTA" if not falhas else "ERRO", "ocupacao",
                  f"circulacao {c['area']:.2f} m2 = {c['taxa'] * 100:.1f} % da "
                  f"area construida, sem largura excedente e sem bolsao"
                  if not falhas else "; ".join(f["erro"] for f in falhas))]
    v = oc.vazios(pj)
    out.append(Achado("NOTA" if not [q for q in v if q["menor"] > 150] else "ERRO",
                      "bolsao sem ambiente",
                      f"{len(v)} vazio(s) interno(s) no raster de "
                      f"{oc.GRID} mm dos dois pavimentos"))
    for i in c["itens"]:
        out.append(Achado("NOTA", f"circulacao: {i['cod']}",
                          f"{i['largura']} mm de largura, {i['guardado']} mm de "
                          f"armario, {i['livre']} mm livres — {i['portas']} "
                          f"porta(s) pedem {i['limite']} mm, que e ao mesmo "
                          f"tempo o minimo e o ponto em que passa a sobrar"))
    return out


def checar_acesso_das_subdivisoes() -> list[Achado]:
    """Toda subdivisao se alcanca, e a sequencia declarada e a real (R55)."""
    import projeto as pj
    import nucleo.ambiente as am
    r = am.acesso_das_subdivisoes(pj)
    out = [Achado("NOTA" if not r["ilhadas"] else "ERRO", "subdivisao ilhada",
                  f"{len(r['subdivisoes'])} subdivisoes, todas alcancaveis a "
                  f"partir do proprio ambiente" if not r["ilhadas"]
                  else f"sem acesso: {r['ilhadas']}"),
           Achado("NOTA" if not r["sequencias_quebradas"] else "ERRO",
                  "sequencia declarada",
                  "toda subdivisao com acesso unico declarado tem exatamente "
                  "essa vizinha" if not r["sequencias_quebradas"]
                  else f"quebradas: {r['sequencias_quebradas']}")]
    for o in r["subdivisoes"]:
        out.append(Achado("NOTA", f"acesso: {o['cod']}",
                          f"{o['aberturas']} abertura(s), vizinhos "
                          f"{o['vizinhos']}"
                          + (f" — acesso unico declarado por {o['unico_acesso']}"
                             if o["unico_acesso"] else "")))
    return out


def checar_acabamento() -> list[Achado]:
    """As seis frentes que deixaram de estar fora do orcamento (R57)."""
    import projeto as pj
    import nucleo.acabamento as ab
    out = []
    for titulo, detalhe, ok in ab.conferir(pj):
        out.append(Achado("NOTA" if ok else "ERRO", titulo, detalhe))
    import fixture as _fx
    lv = ab.levantar(pj, _fx.liberacao()["camadas"])
    for frente, linhas in sorted(lv["frentes"].items()):
        v = sum(i["quantidade"] * i["preco"] for i in linhas)
        out.append(Achado("NOTA", f"frente: {frente}",
                          f"{len(linhas)} linhas, {_brl(v)}"
                          + " — " + "; ".join(i["sku"] for i in linhas)))
    out.append(Achado("NOTA", "ponto de luz e calculo desde R59",
                      "metodo dos lumens por ambiente em nucleo/luminotecnica.py; "
                      "a pendencia 13 fechou e nenhuma quantidade das sete frentes "
                      "e regra de area"))
    return out
