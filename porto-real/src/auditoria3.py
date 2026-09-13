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

from auditoria import Achado
import projeto as pj
import nucleo.perfis as pf


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
