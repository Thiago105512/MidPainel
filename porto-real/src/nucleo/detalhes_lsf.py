"""DETALHES DO LIGHT STEEL FRAME QUE FALTAVAM — do modelo, nao do catalogo (R75).

  CONTRAVENTAMENTO EM PLANTA. piso.contraventar escolhe os paineis com fita
  em X e prova que dao conta do vento; faltava a planta com cada um, o
  hold-down nas extremidades e o chumbador, que sao o que a obra executa.
  CARGA SUSPENSA. A marcenaria (R71) tem 11 moveis pendurados em parede —
  gabinetes de banho, paineis de TV, cabeceiras — e a TV do estar. Parede de
  LSF nao segura bucha: precisa de reforco entre montantes (OSB 18 mm ou
  travessa) na altura certa. Cada item e locado na parede que o recebe.
  ENCONTROS EM T. Derivados das paredes: onde uma parede termina dentro de
  outra. O detalhe e um so (montante adicional na parede continua, clip na
  guia); o que muda e a quantidade.
  TOLERANCIAS (H). Da NBR 16970 e da pratica de montagem: o que se mede, com
  que instrumento e quanto pode variar.
  JUNTAS E PAGINACAO DE FACHADA. Placa cimenticia 1.200 x 2.400 com junta
  seca de 6 mm em cada painel externo; junta de movimentacao a cada 6 m e
  em cada mudanca de plano (H, fabricante).
"""
from __future__ import annotations

import math

import nucleo.painel as pn
import nucleo.piso as ps
import nucleo.materiais as mt
import elementos as el
from nucleo.esgoto import _pav

PLACA = dict(larg=1_200, alt=2_400, junta=6)
JUNTA_MOV_MAX = 6_000
REFORCO = {"gabinete banho": dict(z0=600, z1=1_000, tipo="OSB 18 mm entre montantes, 2 parafusos 4,2 x 32 a cada 200 mm", carga_kg=90),
           "painel tv": dict(z0=900, z1=2_300, tipo="OSB 18 mm entre montantes + travessa Ue 90 a 1.100 e 1.500", carga_kg=70),
           "cabeceira": dict(z0=300, z1=1_500, tipo="OSB 18 mm entre montantes", carga_kg=25),
           "tv": dict(z0=900, z1=1_500, tipo="travessa Ue 90 x 40 entre montantes, chapa 2 mm de apoio do suporte", carga_kg=35)}
TOLERANCIAS = [
    ("prumo do painel", "3 mm em 2.900 mm (1/1000)", "prumo laser ou nivel de 2 m", "montagem, antes de fixar a guia superior"),
    ("nivel da guia inferior", "± 3 mm em 10 m", "nivel laser", "antes de chumbar"),
    ("posicao do chumbador", "± 10 mm no plano; ± 5 mm da borda", "trena e gabarito", "no radier, antes de posicionar o painel"),
    ("alinhamento de paineis", "± 5 mm entre paineis; ± 10 mm no total da parede", "linha de nylon", "montagem"),
    ("esquadro do painel", "diferenca de diagonais <= 5 mm", "trena", "na fabrica e na montagem"),
    ("espacamento de montantes", "± 3 mm", "trena", "fabrica"),
    ("planicidade da parede", "3 mm em regua de 2 m", "regua de aluminio", "antes das placas"),
    ("folga entre placas", "3 mm (gesso) / 6 mm junta seca (cimenticia)", "espacador", "fechamento"),
    ("emenda da fita X", "sem folga; pre-tensao pela chave", "inspecao visual", "antes do fechamento"),
    ("cota do piso acabado", "± 5 mm", "nivel laser", "apos contrapiso"),
]


def _paineis(pj):
    cfg = pn.Config(altura=pj.PE_DIREITO, modulacao=pj.MONTANTE_ESPACAMENTO)
    pT = pn.painelizar(el.derivar_paredes(pj.TERREO), list(el.vaos_do_pavimento("T")), cfg, "TP")
    pS = pn.painelizar(el.derivar_paredes(pj.SUPERIOR), list(el.vaos_do_pavimento("S")), cfg, "SP")
    return pT, pS, cfg


def contraventamento(pj) -> dict:
    """Paineis com fita, hold-down e chumbador, em planta."""
    pT, pS, cfg = _paineis(pj)
    aco = mt.POR_ACO["ZAR 230"]
    c = ps.contraventar(pT + pS, pj, aco, cfg)
    por_cod = {p.cod: p for p in pT + pS}
    a = ps.ancorar(c, pT + pS, pn._catalogo_massa(), pj, cfg)
    anc = a["paineis"]
    out = []
    for e in c["paineis"]:
        p = por_cod[e["painel"]]
        x1, y1 = p.x, p.y
        x2, y2 = (p.x + p.comp, p.y) if p.horizontal else (p.x, p.y + p.comp)
        a = anc.get(p.cod, {})
        out.append(dict(cod=p.cod, pav=p.pav, x1=x1, y1=y1, x2=x2, y2=y2, comp=p.comp,
                        vrd=e["vrd"], aspecto=e["aspecto"], direcao="X" if p.horizontal else "Y",
                        holddown=a.get("precisa", False), chumbador=a.get("chumbador", "—"),
                        uplift=a.get("uplift", 0.0), v_kn=a.get("v_kn", 0.0)))
    return dict(paineis=out, veredito=c["veredito"], sistema=c["sistema"], n_fitas=c["n"], ok=c["ok"] and not a.get("problemas"),
                holddowns=2 * sum(1 for p in out if p["holddown"]), problemas=a.get("problemas", []))


def _paredes_com_subdivisoes(pj, pav):
    """As paredes dos ambientes mais as quatro faces de cada subdivisao (banho,
    closet, office): e nelas que os gabinetes de banho e o painel da master
    se penduram, e derivar_paredes nao as ve."""
    ambs = pj.TERREO if pav == "T" else pj.SUPERIOR
    out = list(el.derivar_paredes(ambs))
    for d in pj.SUBDIVISOES:
        if (d["pai"].startswith("S-")) != (pav == "S"):
            continue
        x0, y0, x1, y1 = d["x"], d["y"], d["x"] + d["w"], d["y"] + d["h"]
        out += [el.Parede(x0, y0, x1, y0, 100, False), el.Parede(x0, y1, x1, y1, 100, False),
                el.Parede(x0, y0, x0, y1, 100, False), el.Parede(x1, y0, x1, y1, 100, False)]
    return out


def _parede_de(pj, pav, x, y, w, h):
    """A parede a menos de 300 mm de uma das faces do retangulo."""
    melhor = None
    for pr in _paredes_com_subdivisoes(pj, pav):
        if pr.horizontal:
            if min(pr.x1, pr.x2) - 100 <= x + w / 2 <= max(pr.x1, pr.x2) + 100:
                d = min(abs(pr.y1 - y), abs(pr.y1 - (y + h)))
                if d <= 300 and (melhor is None or d < melhor[0]):
                    melhor = (d, pr, "H")
        else:
            if min(pr.y1, pr.y2) - 100 <= y + h / 2 <= max(pr.y1, pr.y2) + 100:
                d = min(abs(pr.x1 - x), abs(pr.x1 - (x + w)))
                if d <= 300 and (melhor is None or d < melhor[0]):
                    melhor = (d, pr, "V")
    return melhor


def cargas_suspensas(pj) -> list[dict]:
    import nucleo.marcenaria as mc
    itens = [(m["cod"], m["amb"], m["familia"], m["x"], m["y"], m["w"], m["h"], m["frente"]) for m in mc.moveis(pj) if m["suspenso"]]
    itens += [(l["cod"], l["amb"], "tv", l["x"], l["y"], l["w"], l["h"], l["w"]) for l in pj.LAYOUT if l["tipo"] == "tv"]
    out = []
    for cod, amb, fam, x, y, w, h, frente in itens:
        pav = _pav(amb)
        par = _parede_de(pj, pav, x, y, w, h)
        r = REFORCO[fam]
        n_mont = int(frente // pj.MONTANTE_ESPACAMENTO) + 2
        out.append(dict(cod=cod, amb=amb, pav=pav, familia=fam, x=x, y=y, w=w, h=h, frente=frente,
                        parede=(f"{'H' if par[2] == 'H' else 'V'} em {par[1].y1 if par[2] == 'H' else par[1].x1}" if par else None),
                        encontrada=par is not None, z0=r["z0"], z1=r["z1"], reforco=r["tipo"], carga_kg=r["carga_kg"],
                        montantes=n_mont, osb_m2=round(frente * (r["z1"] - r["z0"]) / 1e6, 2)))
    return out


def encontros_t(pj) -> list[dict]:
    out = []
    for pav, ambs in (("T", pj.TERREO), ("S", pj.SUPERIOR)):
        ps_ = el.derivar_paredes(ambs)
        for a in ps_:
            for (px, py) in ((a.x1, a.y1), (a.x2, a.y2)):
                for b in ps_:
                    if b is a:
                        continue
                    if b.horizontal and a.horizontal:
                        continue
                    if not b.horizontal and not a.horizontal:
                        continue
                    if b.horizontal:
                        dentro = min(b.x1, b.x2) + 50 < px < max(b.x1, b.x2) - 50 and abs(py - b.y1) <= 100
                    else:
                        dentro = min(b.y1, b.y2) + 50 < py < max(b.y1, b.y2) - 50 and abs(px - b.x1) <= 100
                    if dentro:
                        out.append(dict(pav=pav, x=px, y=py, continua=("H" if b.horizontal else "V"),
                                        externa=b.externa,
                                        detalhe="montante adicional na parede continua + clip de guia; 4 parafusos 4,8 x 19 por metro"))
    # remove duplicatas por posicao
    vistos, uniq = set(), []
    for e in out:
        k = (e["pav"], e["x"], e["y"])
        if k not in vistos:
            vistos.add(k); uniq.append(e)
    return uniq


def paginacao_fachada(pj) -> dict:
    """Grade de placas por painel externo (para desenhar) e os totais do
    nesting da casa inteira (camadas.paginar), que reaproveita os retalhos:
    contar placa por painel dava 228 e 44 % de perda; o nesting da 122."""
    import nucleo.camadas as cd
    import especificacao as ep
    pT, pS, _ = _paineis(pj)
    todos = pT + pS
    out = []
    for p in todos:
        if not p.externa:
            continue
        cols = math.ceil(p.comp / PLACA["larg"]); rows = math.ceil(p.altura / PLACA["alt"])
        out.append(dict(cod=p.cod, pav=p.pav, comp=p.comp, alt=p.altura, cols=cols, rows=rows,
                        area_m2=round(p.comp * p.altura / 1e6, 2), horizontal=p.horizontal, x=p.x, y=p.y))
    segs = ep.paredes_classificadas(pj.TERREO) + ep.paredes_classificadas(pj.SUPERIOR)
    fam = cd.familia_por_painel(todos, segs)
    pg = cd.paginar(todos, fam["familia"])
    cim = next((i for i in pg["itens"] if i["material"] == "PLCIM"), None)
    # juntas de movimentacao: por parede externa, a cada 6 m, mais uma em cada canto
    juntas = []
    for pav, ambs in (("T", pj.TERREO), ("S", pj.SUPERIOR)):
        for pr in el.derivar_paredes(ambs):
            if not pr.externa:
                continue
            L = abs(pr.x2 - pr.x1) + abs(pr.y2 - pr.y1)
            n = max(0, math.ceil(L / JUNTA_MOV_MAX) - 1)
            for k in range(1, n + 1):
                t = k * L / (n + 1)
                juntas.append(dict(pav=pav, x=pr.x1 + (t if pr.horizontal else 0), y=pr.y1 + (0 if pr.horizontal else t),
                                   tipo="junta de movimentacao intermediaria"))
            juntas.append(dict(pav=pav, x=pr.x2, y=pr.y2, tipo="junta de canto (mudanca de plano)"))
    return dict(paineis=out, placas=cim["placas"] if cim else 0, inteiras=cim["inteiras"] if cim else 0,
                de_retalho=cim["de_retalho"] if cim else 0,
                area_m2=cim["area_util"] if cim else 0, aproveitamento=round(cim["aproveitamento"], 3) if cim else 0,
                junta_seca_m=cim["junta_m"] if cim else 0, juntas=juntas, juntas_mov=len(juntas),
                junta_mov=dict(largura=10, selante="poliuretano com tarucel", apoio="montante duplo, placas nao passam pela junta"))


def resumo(pj) -> dict:
    c = contraventamento(pj); cs = cargas_suspensas(pj); t = encontros_t(pj); pf = paginacao_fachada(pj)
    return dict(paineis_contraventados=len(c["paineis"]), fitas=c["n_fitas"], holddowns=c["holddowns"], veredito=c["veredito"],
                cargas_suspensas=len(cs), sem_parede=[x["cod"] for x in cs if not x["encontrada"]],
                osb_m2=round(sum(x["osb_m2"] for x in cs), 1), encontros_t=len(t),
                placas_fachada=pf["placas"], aproveitamento_fachada=pf["aproveitamento"], juntas_mov=pf["juntas_mov"])


def conferir(pj) -> list[tuple[str, str, bool]]:
    out = []
    c = contraventamento(pj)
    for d, v in c["veredito"].items():
        out.append((f"vento {d}", f"capacidade {v['capacidade']} kN, demanda {v['demanda']} kN", v["ok"]))
    for x in cargas_suspensas(pj):
        out.append((f"reforco {x['cod']}", f"{x['familia']} de {x['carga_kg']} kg: {x['reforco'][:40]} em {x['parede'] or 'PAREDE NAO ENCONTRADA'}",
                    x["encontrada"]))
    pf = paginacao_fachada(pj)
    out.append(("aproveitamento da placa de fachada", f"{pf['aproveitamento'] * 100:.0f} % em {pf['placas']} placas com retalho reaproveitado (minimo 70 %)", pf["aproveitamento"] >= 0.70))
    out.append(("hold-down resolvido", f"{c['holddowns']} hold-downs; {len(c['problemas'])} sem solucao", not c["problemas"]))
    out.append(("encontros em T", f"{len(encontros_t(pj))} encontros derivados das paredes", len(encontros_t(pj)) > 0))
    return out
