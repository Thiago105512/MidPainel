"""
ETAPA 3 — COORDENACAO DE INSTALACOES.

Quatro pranchas: hidrossanitaria, eletrica/iluminacao/dados, climatizacao
(linhas frigorigenas, dutos e drenos) e drenagem pluvial e de piso.

Cada diametro, bitola, secao de cabo e disjuntor sai de conta feita no modelo.
Nenhum numero e escolhido no desenho.
"""
from __future__ import annotations

import math

import projeto as pj
import elementos as el
import mobiliario as mob
import anotacao as an
from core import P, Canvas, View, TXT, CINZA, PRETO
from pranchas import base, _tabela


def _fundo(cv: Canvas, vw: View, pav: str, rotulos: bool = False) -> None:
    """Planta de fundo em linha leve, para receber a camada de instalacao."""
    ambs = pj.TERREO if pav == "T" else pj.SUPERIOR
    abertos = pj.TERREO_ABERTO if pav == "T" else pj.SUPERIOR_ABERTO
    for a in abertos:
        cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                   vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                  "cota", fechado=True, preenche="#fbfbfb", cor="#ddd")
    paredes = el.derivar_paredes(ambs)
    vaos = list(el.vaos_do_pavimento(pav))
    for p in paredes:
        e = p.esp / 2
        if p.horizontal:
            x0, y0, x1, y1 = p.x1, p.y1 - e, p.x2, p.y1 + e
        else:
            x0, y0, x1, y1 = p.x1 - e, p.y1, p.x1 + e, p.y2
        cv.poli_p([vw.pt(P(x0, y0)), vw.pt(P(x1, y0)), vw.pt(P(x1, y1)),
                   vw.pt(P(x0, y1))], "fino", fechado=True,
                  preenche="#e4e4e4", cor="#bbb")
    for a in ambs:
        cv.texto_p(vw.pt(P(a.cx, a.cy)), a.cod, TXT["micro"], "middle", cor="#aaa")
        if rotulos:
            cv.texto_p(vw.pt(P(a.cx, a.cy + 400)), a.nome[:16], TXT["micro"],
                       "middle", cor="#ccc")


def _simbolo(cv: Canvas, vw: View, x, y, letra: str, cor: str, r: float = 2.2) -> None:
    c = vw.pt(P(x, y))
    cv.circ_p(c, r, "vista", preenche="#fff", cor=cor)
    cv.texto_p((c[0], c[1] + 0.8), letra, TXT["micro"], "middle", cor=cor)


# =========================================================================
# PR-26 — INSTALACOES HIDROSSANITARIAS
# =========================================================================
def hidrossanitaria() -> Canvas:
    pru = pj.prumadas_hidraulicas()
    geral = next(p for p in pru if p["pav"] == "GERAL")
    cv = base("INSTALACOES HIDROSSANITARIAS", "1:100", "26", notas=[
        f"Agua fria por metodo dos pesos (NBR 5626): Q = 0,30 x raiz(soma dos pesos) "
        f"= {geral['q']} L/s com {geral['pesos']} pesos.",
        f"Alimentador DN{geral['dn_agua']} a {geral['v']} m/s — limitado pelo conforto "
        f"({pj.VEL_CONFORTO} m/s), nao pela norma ({pj.VEL_MAX_AGUA} m/s).",
        f"Esgoto por UHC (NBR 8160): {geral['uhc']} UHC, tubo de queda "
        f"DN{geral['dn_esgoto']}, ventilacao DN50.",
        f"Chuveiro ELETRICO tem peso 0,10, nao 0,40: a decisao do aquecimento "
        f"reaparece aqui como diametro menor em toda a casa.",
    ])
    pecas = pj.pecas_hidraulicas()
    for pav, ox, num in (("T", 40, "1"), ("S", 330, "2")):
        vw = View(100, ox, 340, 1_800, 6_800)
        an.titulo_desenho(cv, (ox - 10, 372), num,
                          f"PONTOS HIDRAULICOS — {'TERREO' if pav == 'T' else 'SUPERIOR'}",
                          "1:100")
        _fundo(cv, vw, pav)
        for p in pecas:
            if (p["amb"].startswith("S-")) != (pav == "S"):
                continue
            _simbolo(cv, vw, p["x"], p["y"], "AF", "#06c", 1.9)
            cv.texto_p(vw.pt(P(p["x"], p["y"] - 500)),
                       f"{p['cod']} p={p['peso']:.2f}".replace(".", ","),
                       TXT["micro"], "middle", cor="#06c")
            if p["quente"]:
                _simbolo(cv, vw, p["x"] + 400, p["y"], "E", "#c00", 1.6)
        for r in pj.RALOS:
            if (r["amb"].startswith("S-")) != (pav == "S"):
                continue
            c = vw.pt(P(r["x"], r["y"]))
            cv.poli_p([(c[0] - 1.8, c[1] - 1.8), (c[0] + 1.8, c[1] - 1.8),
                       (c[0] + 1.8, c[1] + 1.8), (c[0] - 1.8, c[1] + 1.8)],
                      "vista", fechado=True, preenche="#fff", cor="#0a6")
            cv.texto_p((c[0], c[1] + 0.8), "R", TXT["micro"], "middle", cor="#0a6")
        # shaft e prumadas
        # do caso, nao literal: sem a posicao como dado nao ha comprimento de
        # ramal, e era por isso que o MEP nao tinha material nenhum no BOM.
        # E a posicao que o desenho mostra e a RESOLVIDA, a mesma que mede o
        # ramal e a mesma que confere o clash: o eixo declarado cai dentro da
        # linha de parede, e desenhar o declarado enquanto o modelo usa o
        # resolvido seria voltar a ter duas fontes para o mesmo fato.
        import fixture as _fx
        _res = _fx.shafts()["prumadas"]
        for pr in (q for q in pj.PRUMADAS if q["tipo"] == "esgoto"):
            r = _res.get(pr["cod"], pr)
            sc, sx, sy = pr["cod"], r["x"], r["y"]
            c = vw.pt(P(sx + 150, sy + 150))
            cv.circ_p(c, 3.0, "corte", preenche="#fff3d6", cor="#b5651d")
            cv.texto_p((c[0], c[1] + 0.8), "S", TXT["micro"], "middle", cor="#b5651d")
            if r.get("deslocado"):
                cv.texto_p((c[0], c[1] + 4.6),
                           f"{sc} caixa {r['lado']} {r['deslocado']:.0f}",
                           TXT["micro"], "middle", cor="#b5651d")
        an.norte(cv, (ox + 210, 120), 7, pj.NORTE_EM_PLANTA)

    linhas = []
    for p in pru:
        linhas.append([
            {"T": "Terreo", "S": "Superior", "GERAL": "GERAL"}[p["pav"]],
            str(p["pecas"]), f"{p['pesos']:.2f}".replace(".", ","),
            f"{p['q']:.3f}".replace(".", ","), f"DN{p['dn_agua']}",
            f"{p['v']}".replace(".", ","), str(p["uhc"]), f"DN{p['dn_esgoto']}",
            "pressurizado" if p["pressurizado"] else "gravidade"])
    _tabela(cv, (35, 500), "DIMENSIONAMENTO — AGUA FRIA E ESGOTO",
            ["TRECHO", "PECAS", "PESOS", "Q (L/s)", "DN AGUA", "v (m/s)", "UHC",
             "DN ESGOTO", "REGIME"], linhas,
            larguras=[30, 20, 20, 24, 24, 22, 18, 26, 34])

    linhas = []
    for p in pecas:
        linhas.append([p["cod"], p["amb"], p["tipo"],
                       f"{p['peso']:.2f}".replace(".", ","), str(p["uhc"]),
                       f"DN{pj.dn_agua(pj.vazao_ls(p['peso']))}",
                       f"DN{pj.dn_esgoto(p['uhc'])}",
                       "sim" if p["quente"] else "—"])
    _tabela(cv, (35, 545), "PECAS DE UTILIZACAO",
            ["COD", "AMB", "TIPO", "PESO", "UHC", "DN AF", "DN ESG", "QUENTE"],
            linhas, larguras=[18, 18, 26, 18, 16, 20, 22, 20])

    _tabela(cv, (300, 500), "DECISOES QUE O DIAMETRO REVELA",
            ["DECISAO", "CONSEQUENCIA HIDRAULICA"],
            [["Chuveiro eletrico em vez de aquecimento central",
              f"peso 0,10 por chuveiro em vez de 0,40: a soma cai de 8,2 para "
              f"{geral['pesos']} pesos e o alimentador de DN40 para DN{geral['dn_agua']}"],
             ["Limite de velocidade por conforto, nao por norma",
              f"DN25 atenderia a norma a 2,17 m/s; a {pj.VEL_CONFORTO} m/s o tubo nao "
              f"assobia. Custa alguns metros de tubo"],
             ["Pressurizador no ramal superior",
              f"{pj.carga_hidraulica_mca('S')} mca por gravidade nao aciona chuveiro "
              f"eletrico; {pj.PRESSURIZADOR['cod']} entrega "
              f"{pj.PRESSURIZADOR['pressao_mca']:.0f} mca"],
             ["Reuso pluvial sem ligacao a vasos",
              "rede de reuso e fisicamente separada, com cor e identificacao "
              "propria: nao ha ponto de conexao cruzada possivel"],
             ["Caixa de gordura antes da inspecao",
              f"cozinha -> TC-11 (30 L) -> TC-12 -> rede; DN{geral['dn_esgoto']} "
              f"com caimento de 2 %"]],
            larguras=[74, 186])
    return cv


# =========================================================================
# PR-27 — ELETRICA, ILUMINACAO E DADOS
# =========================================================================
def eletrica() -> Canvas:
    d = pj.demanda_eletrica()
    prev = pj.previsao_iluminacao_tug()
    cv = base("ELETRICA, ILUMINACAO E DADOS", "1:100", "27", notas=[
        f"Previsao de carga conforme NBR 5410 9.5.2. Instalada "
        f"{d['instalada_va']:,} VA; demanda provavel {d['demanda_va']:,} VA."
        .replace(",", "."),
        f"Entrada {pj.TENSAO['esquema']}: {d['corrente_a']} A -> padrao "
        f"{d['padrao_a']} A com cabo de {d['secao_mm2']} mm2.",
        "Fator de demanda do ar condicionado adotado 1,00 — em Manaus ele e carga "
        "continua, nao intermitente. Ver justificativa no quadro.",
        f"Quadro geral {pj.TECNICOS[4]['nome'].split('(')[0].strip()} na garagem; "
        f"quadro do superior no hall.",
    ])
    for pav, ox, num in (("T", 40, "1"), ("S", 330, "2")):
        vw = View(100, ox, 340, 1_800, 6_800)
        an.titulo_desenho(cv, (ox - 10, 372), num,
                          f"PONTOS ELETRICOS — {'TERREO' if pav == 'T' else 'SUPERIOR'}",
                          "1:100")
        _fundo(cv, vw, pav)
        ambs = pj.TERREO if pav == "T" else pj.SUPERIOR
        for a in ambs:
            p = next(x for x in prev if x["amb"] == a.cod)
            # luminarias distribuidas na diagonal do ambiente
            n = max(1, p["ilum_va"] // 100)
            for i in range(min(n, 4)):
                fx = a.x + a.w * (i + 1) / (min(n, 4) + 1)
                fy = a.cy
                c = vw.pt(P(fx, fy))
                cv.circ_p(c, 1.5, "vista", preenche="#fffbe6", cor="#e0a800")
                cv.linha_p((c[0] - 2.2, c[1]), (c[0] + 2.2, c[1]), "fino", cor="#e0a800")
            # tomadas no perimetro
            for i in range(p["tugs"]):
                t = (i + 0.5) / p["tugs"]
                per = 2 * (a.w + a.h)
                s = t * per
                if s < a.w:
                    tx, ty = a.x + s, a.y + 120
                elif s < a.w + a.h:
                    tx, ty = a.x + a.w - 120, a.y + (s - a.w)
                elif s < 2 * a.w + a.h:
                    tx, ty = a.x + a.w - (s - a.w - a.h), a.y + a.h - 120
                else:
                    tx, ty = a.x + 120, a.y + a.h - (s - 2 * a.w - a.h)
                c = vw.pt(P(tx, ty))
                cv.arco_p(c, 1.6, 0, 180, "vista", cor="#c00")
            cv.texto_p(vw.pt(P(a.cx, a.cy + 700)),
                       f"{p['ilum_va']}+{p['tug_va']} VA", TXT["micro"],
                       "middle", cor="#666")
        # quadros, rack e pontos de dados
        for t in pj.TECNICOS:
            if t.get("zona") != "INT":
                continue
            amb = t.get("amb", "")
            if (amb.startswith("S-")) != (pav == "S"):
                continue
            c = vw.pt(P(t["x"], t["y"]))
            cv.poli_p([(c[0] - 2.4, c[1] - 2.4), (c[0] + 2.4, c[1] - 2.4),
                       (c[0] + 2.4, c[1] + 2.4), (c[0] - 2.4, c[1] + 2.4)],
                      "corte", fechado=True, preenche="#fff", cor="#06c")
            cv.texto_p((c[0], c[1] + 0.8), t["cod"][-2:], TXT["micro"], "middle",
                       cor="#06c")
        an.norte(cv, (ox + 210, 120), 7, pj.NORTE_EM_PLANTA)

    linhas = []
    for c in pj.CARGAS_ESPECIAIS:
        linhas.append([c["cod"], c["desc"][:46], f"{c['va']:,}".replace(",", "."),
                       f"{c['v']} V", c["grupo"], f"{c['fd']:.2f}".replace(".", ","),
                       f"{c['va']*c['fd']:,.0f}".replace(",", ".")])
    linhas.append(["—", "Iluminacao + tomadas de uso geral",
                   f"{d['base_va']:,}".replace(",", "."), "127 V", "base",
                   f"{d['fd_base']:.2f}".replace(".", ","),
                   f"{d['base_va']*d['fd_base']:,.0f}".replace(",", ".")])
    linhas.append(["", "TOTAL", f"{d['instalada_va']:,}".replace(",", "."), "", "",
                   f"{d['demanda_va']/d['instalada_va']:.2f}".replace(".", ","),
                   f"{d['demanda_va']:,}".replace(",", ".")])
    _tabela(cv, (35, 500), "QUADRO DE CARGAS E DEMANDA",
            ["COD", "CARGA", "VA", "TENSAO", "GRUPO", "fd", "DEMANDA (VA)"],
            linhas, larguras=[18, 92, 26, 20, 26, 16, 30])

    _tabela(cv, (300, 500), "POR QUE fd = 1,00 NA CLIMATIZACAO",
            ["ARGUMENTO", "DESENVOLVIMENTO"],
            [["O que a tabela assume",
              "os fatores de demanda da NBR 5410 vem de media nacional, onde ar "
              "condicionado e carga intermitente e sazonal"],
             ["O que acontece em Manaus",
              "os cinco equipamentos funcionam juntos em todas as tardes do ano; "
              "nao existe a diversidade que o fator pressupoe"],
             ["O que custa errar",
              "com fd 0,70 a demanda cairia 2.370 VA e o padrao desceria de "
              f"{d['padrao_a']} A — o ramal aquece e o disjuntor geral desliga "
              "exatamente na hora de maior calor"],
             ["O que o proprietario faria",
              "trocaria o disjuntor por um maior em vez do cabo, transformando "
              "uma protecao em um risco de incendio"],
             ["Custo de acertar",
              f"cabo de {d['secao_mm2']} mm2 em vez de 25 mm2 no ramal de entrada: "
              "dezenas de metros, uma vez na vida da casa"]],
            larguras=[48, 212])

    linhas = []
    for p in sorted(prev, key=lambda x: -x["area"])[:12]:
        linhas.append([p["amb"], p["nome"][:24],
                       f"{p['area']:.2f}".replace(".", ","),
                       f"{p['perim']/1000:.1f}".replace(".", ","),
                       f"{p['ilum_va']}", f"{p['tugs']}", f"{p['tug_va']}",
                       "molhada" if p["molhada"] else "seca"])
    _tabela(cv, (35, 545), "PREVISAO DE CARGA POR AMBIENTE (12 MAIORES)",
            ["AMB", "AMBIENTE", "AREA", "PERIM (m)", "ILUM (VA)", "TUG", "TUG (VA)",
             "CLASSE"], linhas, larguras=[18, 52, 22, 26, 26, 16, 26, 26])
    return cv


# =========================================================================
# PR-28 — CLIMATIZACAO: LINHAS, DUTOS E DRENOS
# =========================================================================
def climatizacao() -> Canvas:
    linhas_f = pj.linhas_frigorigenas()
    cv = base("CLIMATIZACAO — LINHAS FRIGORIGENAS, DUTOS E DRENOS", "1:100", "28",
              notas=[
        f"Dois nichos de condensadoras. Linha mais longa {max(l['comp'] for l in linhas_f)/1000:.1f} m, "
        f"contra o limite de conforto de {pj.LINHA_FRIG_MAX/1000:.0f} m.",
        f"Dreno DN{pj.DRENO_DN} com caimento minimo de {pj.DRENO_CAIMENTO:.0%} e sifao "
        f"antes da descida; nunca ligado a esgoto sem sifao.",
        f"Duto de insuflamento no entreforro de {pj.ENTREFORRO} mm — nunca atravessa "
        f"montante.",
        "Isolamento continuo na travessia de parede, com bucha de passagem: corte de "
        "isolamento na parede condensa dentro do montante.",
    ])
    vw = View(100, 40, 430, 800, 6_800)
    an.titulo_desenho(cv, (30, 462), "1", "PERCURSO DAS LINHAS E DUTOS", "1:100")
    _fundo(cv, vw, "T")
    # superior em tracejado
    for a in pj.SUPERIOR:
        cv.poli_p([vw.pt(P(a.x, a.y)), vw.pt(P(a.x + a.w, a.y)),
                   vw.pt(P(a.x + a.w, a.y + a.h)), vw.pt(P(a.x, a.y + a.h))],
                  "oculto", fechado=True, preenche="none", cor="#c9c9c9")
    # nichos
    for t in pj.TECNICOS:
        if "condensadoras" not in t["nome"]:
            continue
        cv.poli_p([vw.pt(P(t["x"], t["y"])), vw.pt(P(t["x"] + t["w"], t["y"])),
                   vw.pt(P(t["x"] + t["w"], t["y"] + t["h"])),
                   vw.pt(P(t["x"], t["y"] + t["h"]))], "corte", fechado=True,
                  preenche="#fff3d6", cor="#b5651d")
        cv.texto_p(vw.pt(P(t["x"] + t["w"] / 2, t["y"] + t["h"] / 2)), t["cod"],
                   TXT["micro"], "middle", rot=90, cor="#b5651d")
    # percursos em L do nicho ao ambiente
    for l in linhas_f:
        amb = next(a for a in pj.TERREO + pj.SUPERIOR if a.cod == l["amb"])
        t = next(x for x in pj.TECNICOS if x["cod"] == l["nicho"])
        a0 = (t["x"] + t["w"] / 2, t["y"] + t["h"] / 2)
        a1 = (amb.cx, amb.cy)
        cor = "#999" if l["reserva"] else "#06c"
        cv.linha_p(vw.pt(P(a0[0], a0[1])), vw.pt(P(a0[0], a1[1])), "cota", cor=cor)
        cv.linha_p(vw.pt(P(a0[0], a1[1])), vw.pt(P(a1[0], a1[1])), "cota", cor=cor)
        mx = vw.pt(P((a0[0] + a1[0]) / 2, a1[1]))
        cv.texto_p((mx[0], mx[1] - 1.5),
                   f"{l['suc']}\"+{l['liq']}\"  {l['comp']/1000:.1f} m",
                   TXT["micro"], "middle", cor=cor)
    # evaporadora de duto e difusores
    ev = pj.EVAPORADORA_DUTO
    cv.poli_p([vw.pt(P(ev["x"], ev["y"])), vw.pt(P(ev["x"] + ev["w"], ev["y"])),
               vw.pt(P(ev["x"] + ev["w"], ev["y"] + ev["h"])),
               vw.pt(P(ev["x"], ev["y"] + ev["h"]))], "corte", fechado=True,
              preenche="#e8f4fb", cor="#06c")
    cv.texto_p(vw.pt(P(ev["x"] + ev["w"] / 2, ev["y"] - 300)), "EVAP. DUTO",
               TXT["micro"], "middle", cor="#06c")
    for df in pj.DIFUSORES:
        cor = "#06c" if df["tipo"] == "insuflamento" else "#c00"
        cv.poli_p([vw.pt(P(df["x"], df["y"])), vw.pt(P(df["x"] + df["w"], df["y"])),
                   vw.pt(P(df["x"] + df["w"], df["y"] + df["h"])),
                   vw.pt(P(df["x"], df["y"] + df["h"]))], "vista", fechado=True,
                  preenche="#fff", cor=cor)
        cv.texto_p(vw.pt(P(df["x"] + df["w"] / 2, df["y"] - 250)),
                   f"{df['cod']} {df['vazao_m3h']}", TXT["micro"], "middle", cor=cor)
        cv.linha_p(vw.pt(P(ev["x"] + ev["w"] / 2, ev["y"] + ev["h"] / 2)),
                   vw.pt(P(df["x"] + df["w"] / 2, df["y"] + df["h"] / 2)),
                   "cota", cor="#9cf")
    # fronteira climatica
    fr = pj.FRONTEIRA_CLIMATICA
    cv.linha_p(vw.pt(P(fr["x"], fr["y"])),
               vw.pt(P(fr["x"] + fr["comprimento"], fr["y"])), "corte", cor="#e0a")
    cv.texto_p(vw.pt(P(fr["x"] + fr["comprimento"] / 2, fr["y"] - 400)),
               f"FRONTEIRA CLIMATICA — rebaixo {fr['rebaixo']} mm", TXT["micro"],
               "middle", cor="#e0a")
    # ventiladores
    for v in pj.VENTILADORES:
        amb = next((a for a in pj.TERREO + pj.TERREO_ABERTO if a.cod == v["amb"]), None)
        if amb is None:
            continue
        c = vw.pt(P(amb.cx, amb.cy - 600))
        cv.circ_p(c, vw.d(v["diam"]) / 2, "cota", preenche="none", cor="#0a6")
        cv.texto_p((c[0], c[1] + 0.8), f"{v['qtd']}x{v['diam']}", TXT["micro"],
                   "middle", cor="#0a6")
    an.norte(cv, (250, 120), 7, pj.NORTE_EM_PLANTA)

    linhas = []
    for l in linhas_f:
        linhas.append([l["cod"][-5:], l["amb"], l["nicho"],
                       f"{l['capacidade']:,}".replace(",", "."),
                       f"{l['horizontal']/1000:.1f}".replace(".", ","),
                       f"{l['subida']/1000:.1f}".replace(".", ","),
                       f"{l['comp']/1000:.1f}".replace(".", ","),
                       f'{l["suc"]}" / {l["liq"]}"', f"DN{l['dreno']}",
                       f"{l['carga_extra_g']} g" if l["carga_extra_g"] else "—",
                       "reserva" if l["reserva"] else "ativo"])
    _tabela(cv, (35, 520), "LINHAS FRIGORIGENAS — PERCURSO E BITOLA",
            ["LINHA", "AMB", "NICHO", "BTU/h", "HORIZ (m)", "SUBIDA (m)",
             "TOTAL (m)", "SUCCAO/LIQ", "DRENO", "CARGA EXTRA", "FASE"],
            linhas, larguras=[22, 18, 18, 22, 26, 28, 24, 30, 20, 28, 22])

    _tabela(cv, (35, 570), "DUTOS, DIFUSORES E EXAUSTAO",
            ["ELEMENTO", "VAZAO (m3/h)", "ONDE", "OBSERVACAO"],
            [[f"{df['cod']} — {df['tipo']}", f"{df['vazao_m3h']}", df["amb"],
              df.get("obs", "")[:60]] for df in pj.DIFUSORES] +
            [[f"{e['cod']} — {e['fonte']}", f"{e['vazao_m3h']}", e["amb"],
              f"DN{e['dn']}. " + e.get("obs", "")[:50]] for e in pj.EXAUSTAO],
            larguras=[52, 28, 20, 160])
    return cv


# =========================================================================
# PR-29 — DRENAGEM PLUVIAL E DE PISO
# =========================================================================
def drenagem() -> Canvas:
    cb, pl = pj.COBERTURA, pj.PLUVIAL
    bal = pj.balanco_pluvial() if hasattr(pj, "balanco_pluvial") else {}
    cv = base("DRENAGEM PLUVIAL E DE PISO", "1:100", "29", notas=[
        f"Cobertura: {pj.area_contribuicao_m2():.2f} m2 de contribuicao, i = "
        f"{cb['intensidade_mm_h']} mm/h, C = {cb['coef_escoamento']} -> Q = "
        f"{pj.vazao_pluvial_ls():.4f} L/s em {cb['descidas']} descidas DN{cb['dn_descida']}.",
        f"Caimento de {pj.CAIMENTO_AREA_MOLHADA:.1%} em area molhada interna e "
        f"{pj.CAIMENTO_AREA_EXTERNA:.0%} em area externa.",
        f"Impermeabilizacao: {pj.IMPERMEABILIZACAO['sistema']}, subindo "
        f"{pj.IMPERMEABILIZACAO['subida_parede']} mm na parede e "
        f"{pj.IMPERMEABILIZACAO['subida_box']} mm no box.",
        f"Reuso de {pl['volume_l']} L sem nenhuma ligacao a vasos sanitarios: "
        f"rede fisicamente separada e identificada.",
    ])
    vw = View(100, 40, 440, 800, 0)
    an.titulo_desenho(cv, (30, 472), "1", "DRENAGEM — IMPLANTACAO", "1:100")
    L, Pf = pj.LOTE_L, pj.LOTE_P
    cv.poli_p([vw.pt(P(0, 0)), vw.pt(P(L, 0)), vw.pt(P(L, Pf)), vw.pt(P(0, Pf))],
              "fino", fechado=True, preenche="#fdfdfd", cor="#ccc")
    _fundo(cv, vw, "T")
    # ralos e canaletas
    for r in pj.RALOS:
        c = vw.pt(P(r["x"], r["y"]))
        cv.poli_p([(c[0] - 1.8, c[1] - 1.8), (c[0] + 1.8, c[1] - 1.8),
                   (c[0] + 1.8, c[1] + 1.8), (c[0] - 1.8, c[1] + 1.8)],
                  "vista", fechado=True, preenche="#fff", cor="#0a6")
        cv.texto_p((c[0] + 3, c[1] + 0.8), f"{r['cod']} DN{r['dn']}", TXT["micro"],
                   "start", cor="#0a6")
    # descidas pluviais e reservatorios
    for t in pj.TECNICOS:
        if "pluvial" not in t["nome"].lower() and "Cisterna" not in t["nome"]:
            continue
        cv.poli_p([vw.pt(P(t["x"], t["y"])), vw.pt(P(t["x"] + t["w"], t["y"])),
                   vw.pt(P(t["x"] + t["w"], t["y"] + t["h"])),
                   vw.pt(P(t["x"], t["y"] + t["h"]))], "oculto", fechado=True,
                  preenche="none", cor="#06c")
        cv.texto_p(vw.pt(P(t["x"] + t["w"] / 2, t["y"] + t["h"] / 2)), t["cod"],
                   TXT["micro"], "middle", cor="#06c")
    # caixas de esgoto e vala de infiltracao
    for t in pj.TECNICOS:
        if "Caixa" not in t["nome"]:
            continue
        c = vw.pt(P(t["x"] + t["w"] / 2, t["y"] + t["h"] / 2))
        cv.circ_p(c, 2.2, "vista", preenche="#fff", cor="#b5651d")
        cv.texto_p((c[0] + 3.2, c[1] + 0.8), t["cod"], TXT["micro"], "start",
                   cor="#b5651d")
    an.norte(cv, (250, 120), 7, pj.NORTE_EM_PLANTA)

    linhas = []
    for r in pj.RALOS:
        amb = next((a for a in pj.TERREO + pj.TERREO_ABERTO + pj.SUPERIOR
                    if a.cod == r["amb"]), None)
        cai = (pj.CAIMENTO_AREA_MOLHADA if r["amb"] in
               ("T-BWC", "S-S02", "S-S03", "S-MAS", "T-LAV", "T-COZ")
               else pj.CAIMENTO_AREA_EXTERNA)
        linhas.append([r["cod"], r["amb"], amb.nome[:20] if amb else "—", r["tipo"],
                       f"DN{r['dn']}", f"{cai:.1%}".replace(".", ","),
                       f"{amb.area_mod:.2f}".replace(".", ",") if amb else "—"])
    _tabela(cv, (300, 150), "RALOS E CAIMENTOS",
            ["COD", "AMB", "AMBIENTE", "TIPO", "DN", "CAIMENTO", "AREA (m2)"],
            linhas, larguras=[18, 18, 44, 44, 18, 24, 26])

    _tabela(cv, (300, 230), "BALANCO PLUVIAL",
            ["ITEM", "VALOR"],
            [["Area de contribuicao da cobertura", f"{pj.area_contribuicao_m2():.2f} m2"],
             ["Intensidade de projeto", f"{cb['intensidade_mm_h']} mm/h (TR 25 anos, H)"],
             ["Vazao total / por descida",
              f"{pj.vazao_pluvial_ls():.4f} L/s | {pj.vazao_pluvial_ls()/cb['descidas']:.4f} L/s"],
             ["Calha externa", f"{cb['calha_l']} x {cb['calha_h']} mm"],
             ["Descidas", f"{cb['descidas']} x DN{cb['dn_descida']}"],
             ["Precipitacao anual", f"{pl['precipitacao_mm_ano']} mm"],
             ["Volume de reuso", f"{pl['volume_l']} L"],
             ["Usos previstos",
              ", ".join(f"{u[0].split()[0].lower()} {u[1]:.0f} L" for u in pj.usos_pluviais())],
             ["Demanda diaria de reuso",
              f"{sum(u[1] for u in pj.usos_pluviais()):.1f} L/dia"],
             ["Area externa drenada", f"{pj.area_drenada_externa_m2():.2f} m2"],
             ["Nao estender a", pl["nao_estender_a"]]],
            larguras=[74, 120])

    _tabela(cv, (300, 330), "IMPERMEABILIZACAO E DETALHES DE AGUA",
            ["ITEM", "ESPECIFICACAO", "RAZAO"],
            [["Sistema", pj.IMPERMEABILIZACAO["sistema"],
              "flexivel: acompanha a movimentacao do contrapiso seco sobre LSF"],
             ["Subida na parede", f"{pj.IMPERMEABILIZACAO['subida_parede']} mm",
              "respingo de piso molha o rodape, e em LSF o rodape e gesso"],
             ["Subida no box", f"{pj.IMPERMEABILIZACAO['subida_box']} mm",
              "altura do chuveiro: e ali que a agua bate todos os dias"],
             ["Soleira do box", f"{pj.SOLEIRA_BOX} mm",
              "desnivel suficiente para conter, baixo o bastante para nao tropecar"],
             ["Teste de estanqueidade", pj.IMPERMEABILIZACAO["teste"],
              "em LSF o vazamento nao mancha: apodrece o OSB por dentro, sem aviso"],
             ["Ralo linear no box", "600 a 900 mm",
              "caimento em uma direcao so: menos recorte de piso e menos erro de obra"]],
            larguras=[44, 66, 150])
    return cv
