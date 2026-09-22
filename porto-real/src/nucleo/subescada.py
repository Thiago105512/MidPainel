"""SUBESCADA — o unico comodo da casa em que o pe-direito e uma funcao de x.

O proprietario mandou tirar o lavabo da entrada e perguntou se nao cabia sob a
escada. Cabe — e e o melhor destino que aquele espaco tem, porque nao serve
para mais nada. Mas "cabe" nao e afirmacao de arquiteto: e conta.

Sob um lance que sobe, a altura livre cresce com a distancia. Isso muda a
regra de projeto: nao existe UMA altura para verificar, existe uma altura
POR PONTO, e cada peca do lavabo tem a sua exigencia.

  vaso     — usado SENTADO: o que se exige e altura sobre o assento, e a
             cabeca de quem senta fica a cerca de 1,30 m do piso.
  frente   — de pe para levantar e dar descarga: 2,00 m.
  bancada  — de pe, lavando as maos: 2,00 m.
  porta    — passagem: 2,10 m, que e o valor da NBR 9077 para circulacao.

E por isso que o vaso vai no FUNDO, onde o teto e mais baixo, e a porta na
boca, onde e mais alto. Inverter os dois e o erro classico do lavabo sob
escada: fica bonito em planta e impossivel em corte.

O QUE ESTE MODULO NAO FAZ: ele nao desenha a escada nem dimensiona o lance.
Ele le os lances que o modelo ja tem e responde, ponto a ponto, quanto sobra
debaixo deles.
"""
from __future__ import annotations

# alma do perfil U 200 que forma o lance, mais o forro sob ele. A estrutura da
# escada esta declarada em ESCADA_EXEC: "dois perfis U 200 laterais com degraus
# em chapa dobrada 3 mm". O que rouba altura nao e o degrau: e a alma.
ESTRUTURA_LANCE = 200
FORRO = 25

EXIGENCIAS = {
    "vaso": (1_500, "usado sentado: a cabeca de quem senta fica a ~1,30 m"),
    "frente": (2_000, "de pe, para levantar e dar descarga"),
    "bancada": (2_000, "de pe, lavando as maos"),
    "porta": (2_100, "passagem — o valor da NBR 9077 para circulacao"),
    "janela": (0, "o topo do vao tem de caber sob o lance"),
}


def lance_sobre(pj, x: float, y: float) -> dict | None:
    """Qual lance passa por cima deste ponto, e em que cota."""
    for l in pj.escada_lances():
        if not (l["x"] <= x <= l["x"] + l["w"] and l["y"] <= y <= l["y"] + l["h"]):
            continue
        if l["sentido"] == "patamar":
            return dict(cod=l["cod"], z=l["z_ini"])
        # a cota sobe linearmente ao longo do lance, no sentido declarado
        t = ((y - l["y"]) / l["h"] if l["sentido"] == "+Y"
             else 1 - (y - l["y"]) / l["h"])
        return dict(cod=l["cod"], z=l["z_ini"] + t * (l["z_fim"] - l["z_ini"]))
    return None


def altura_livre(pj, x: float, y: float) -> float:
    """Pe-direito util no ponto. Sem lance em cima, vale o pe-direito da casa."""
    l = lance_sobre(pj, x, y)
    if l is None:
        return float(pj.PE_DIREITO)
    return max(0.0, l["z"] - ESTRUTURA_LANCE - FORRO)


def _lavabo(pj):
    return next((d for d in pj.SUBDIVISOES
                 if f"{d['pai']}/{d['nome']}" in pj.LAVABOS), None)


def pontos(pj) -> list[dict]:
    """Cada exigencia do lavabo, no ponto em que ela e exigida."""
    d = _lavabo(pj)
    if d is None:
        return []
    out = []
    loucas = [p for p in pj.LOUCAS if p["amb"] == d["pai"]
              and d["x"] <= p["x"] <= d["x"] + d["w"]
              and d["y"] <= p["y"] <= d["y"] + d["h"]]
    for p in loucas:
        cx = p["x"] + p["w"] / 2
        if p["tipo"] == "vaso":
            out.append(dict(item=f"{p['cod']} assento", regra="vaso",
                            x=cx, y=p["y"] + p["h"] / 2))
            # de pe na frente do vaso: 600 mm alem da borda
            out.append(dict(item=f"{p['cod']} frente", regra="frente",
                            x=cx, y=p["y"] + p["h"] + 600))
        elif p["tipo"] == "lavatorio":
            out.append(dict(item=f"{p['cod']} uso", regra="bancada",
                            x=cx, y=p["y"] + p["h"] / 2))
    # a porta, na face declarada da subdivisao
    if d["face"] in ("L", "O"):
        py = d["y"] if d["face"] == "L" else d["y"] + d["h"]
        out.append(dict(item="porta", regra="porta", x=d["pos"], y=py - 100))
    else:
        px = d["x"] if d["face"] == "S" else d["x"] + d["w"]
        out.append(dict(item="porta", regra="porta", x=px, y=d["pos"]))
    for o in out:
        o["altura"] = round(altura_livre(pj, o["x"], o["y"]), 1)
        o["minimo"] = EXIGENCIAS[o["regra"]][0]
        o["razao"] = EXIGENCIAS[o["regra"]][1]
        o["passa"] = o["altura"] >= o["minimo"]
        l = lance_sobre(pj, o["x"], o["y"])
        o["sob"] = l["cod"] if l else "—"
    return out


def janela(pj) -> dict | None:
    """A janela do lavabo cabe sob o lance, no ponto em que esta?"""
    d = _lavabo(pj)
    if d is None:
        return None
    for t, x, y, ori, pav in pj.VAOS:
        if pav != "T" or not t.startswith("J"):
            continue
        if not (d["x"] - 200 <= x <= d["x"] + d["w"] + 200
                and d["y"] <= y <= d["y"] + d["h"]):
            continue
        larg, alt, peit, _fam = pj.ESQUADRIAS[t]
        h = altura_livre(pj, d["x"] + d["w"] / 2, y)
        return dict(tipo=t, topo=peit + alt, altura_livre=round(h, 1),
                    cabe=peit + alt <= h, area=larg * alt / 1e6,
                    area_minima=round(d["w"] * d["h"] / 1e6 / 8, 3))
    return None


def resumo(pj) -> dict:
    d = _lavabo(pj)
    if d is None:
        return dict(existe=False)
    ps = pontos(pj)
    j = janela(pj)
    ys = [d["y"], d["y"] + d["h"]]
    return dict(existe=True, cod=f"{d['pai']}/{d['nome']}",
                area=round(d["w"] * d["h"] / 1e6, 2),
                largura=d["w"], profundidade=d["h"],
                altura_no_fundo=round(altura_livre(pj, d["x"] + d["w"] / 2,
                                                   ys[0] + 100), 1),
                altura_na_porta=round(altura_livre(pj, d["x"] + d["w"] / 2,
                                                   ys[1] - 100), 1),
                pontos=ps, janela=j,
                ok=all(p["passa"] for p in ps) and (j is None or j["cabe"]))


def conferir(pj) -> list[tuple[str, str, bool]]:
    r = resumo(pj)
    if not r["existe"]:
        return [("lavabo sob escada", "nao ha lavabo declarado sob a escada",
                 True)]
    out = [("o lavabo esta sob a escada",
            f"{r['cod']}: {r['largura']} x {r['profundidade']} mm = "
            f"{r['area']:.2f} m2, com pe-direito de "
            f"{r['altura_no_fundo']:.0f} mm no fundo a "
            f"{r['altura_na_porta']:.0f} mm na porta",
            r["area"] > 0)]
    for p in r["pontos"]:
        out.append((f"altura livre — {p['item']}",
                    f"{p['altura']:.0f} mm sob {p['sob']} contra "
                    f"{p['minimo']} exigidos ({p['razao']})",
                    p["passa"]))
    j = r["janela"]
    if j:
        out.append(("a janela cabe sob o lance",
                    f"{j['tipo']} topa em {j['topo']} mm e ha "
                    f"{j['altura_livre']:.0f} mm de altura livre",
                    j["cabe"]))
        out.append(("ventilacao do lavabo",
                    f"{j['area']:.2f} m2 de vao contra {j['area_minima']:.3f} "
                    f"m2 de minimo (1/8 do piso)",
                    j["area"] >= j["area_minima"]))
    return out
