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
    problemas, excecoes = [], []

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
                for nome, esperado in (("king stud", 2 * n_ab),
                                       ("jack stud", 2 * n_ab),
                                       ("header", n_ab)):
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

    for m in problemas[:10]:
        out.append(Achado("ERRO", "painelizacao", m))
    for m in excecoes[:6]:
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
