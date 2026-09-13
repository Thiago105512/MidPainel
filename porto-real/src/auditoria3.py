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
