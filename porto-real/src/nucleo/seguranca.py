"""DADOS, WI-FI, CFTV, ALARME, AUTOMACAO E INCENDIO — derivados do caso (R74).

O rack TC-07 dizia "8 cameras, 3 access points, 1 videoporteiro" desde R41 e
nada mais: eram numeros num texto. Aqui cada um vira ponto com coordenada,
cabo com comprimento e regra conferida.

  DADOS. Um ponto RJ45 por TV (LAYOUT), dois por posto de trabalho (mesa e
  office), um por dormitorio e um por ambiente social; tres access points
  nos centros que cobrem a casa (raio de 12 m em planta, H) e o cabo de cada
  ponto ate o rack por percurso Manhattan x 1,2, limitado a 90 m (Cat.6).
  CFTV. Oito cameras: os quatro cantos do lote (muro), o portao, a porta de
  entrada, o deck da piscina e a garagem. Alarme: sensor magnetico em todo
  vao externo de porta, IVP nos ambientes de passagem, sirene externa e
  central no rack. Videoporteiro no portao de pedestre, fechadura eletrica
  na porta de entrada e no portao.
  AUTOMACAO (H): sem fio (Zigbee) com hub local no rack — modulo por circuito
  de iluminacao social e externa, motor nas cortinas blackout dos
  dormitorios (MAR-CORT), quatro cenas. Sem KNX: cabeado dedicado em casa
  unifamiliar de R$ 1 M custa mais que o que automatiza.
  INCENDIO. Residencia unifamiliar: sem exigencia de projeto pelo CBM-AM;
  o que fica e boa pratica: extintor ABC 4 kg por pavimento mais garagem,
  detector de fumaca autonomo em cada dormitorio e circulacao, detector de
  calor na cozinha, manta na cozinha e no gourmet.
"""
from __future__ import annotations

import math

from nucleo.esgoto import _manh, _pav

RAIO_WIFI = 12_000
CABO_MAX = 90_000
FATOR_PERCURSO = 1.20
PROTOCOLO = "Zigbee 3.0 com hub local no rack; comandos por app e por interruptor de cena"
CENAS = ["chegar (portao + garagem + hall + circulacao)", "dormir (tudo off, cortinas fechadas, alarme perimetral)",
         "cinema (estar a 20 %, cortina do estar fechada)", "fora (tudo off, cameras em gravacao por movimento)"]
EXTINTOR = "extintor ABC 4 kg, a 1,60 m do piso, sinalizado"
DETECTOR = "detector de fumaca autonomo a bateria com interligacao sem fio"


def _rack(pj):
    return next(t for t in pj.TECNICOS if "rack" in t["nome"].lower())


def _cabo(pj, x, y, pav="T") -> int:
    r = _rack(pj)
    return round((_manh((x, y), (r["x"], r["y"])) + (pj.NIVEL_SUPERIOR if pav == "S" else 0) + 3_000) * FATOR_PERCURSO)


def pontos_dados(pj) -> list[dict]:
    out = []
    for it in pj.LAYOUT:
        if it["tipo"] == "tv":
            out.append(dict(cod=f"RJ-{it['cod']}", amb=it["amb"], uso="TV", x=it["x"], y=it["y"], n=1))
        if it["tipo"] == "rack" and "trabalho" in it.get("obs", ""):
            out.append(dict(cod=f"RJ-{it['cod']}", amb=it["amb"], uso="posto de trabalho", x=it["x"], y=it["y"], n=2))
    for d in pj.SUBDIVISOES:
        if d["nome"] == "OFFICE":
            out.append(dict(cod=f"RJ-{d['pai']}-OFF", amb=d["pai"], uso="office", x=d["x"] + d["w"] / 2, y=d["y"] + d["h"] / 2, n=2))
    for it in pj.LAYOUT:
        if it["tipo"] == "cama":
            out.append(dict(cod=f"RJ-{it['cod']}", amb=it["amb"], uso="cabeceira", x=it["x"], y=it["y"], n=1))
    for a in pj.TERREO + pj.SUPERIOR:
        if pj.CATEGORIA.get(a.cod) == "social" and a.cod not in {p["amb"] for p in out}:
            out.append(dict(cod=f"RJ-{a.cod}", amb=a.cod, uso="social", x=a.cx, y=a.cy, n=1))
    for p in out:
        p["pav"] = _pav(p["amb"]); p["cabo_mm"] = _cabo(pj, p["x"], p["y"], p["pav"])
    return out


def access_points(pj) -> list[dict]:
    ambs = {a.cod: a for a in pj.TERREO + pj.SUPERIOR}
    aps = [dict(cod="AP-01", amb="T-SOC", x=ambs["T-SOC"].cx, y=ambs["T-SOC"].cy, pav="T", onde="forro do estar"),
           dict(cod="AP-02", amb="S-HAL", x=ambs["S-HAL"].cx, y=ambs["S-HAL"].cy, pav="S", onde="forro do hall superior"),
           dict(cod="AP-03", amb="T-GOU", x=ambs["T-GOU"].cx, y=ambs["T-GOU"].cy + 3_000, pav="T", onde="forro do patio do gourmet, IP65")]
    for a in aps:
        a["cabo_mm"] = _cabo(pj, a["x"], a["y"], a["pav"])
    return aps


def cobertura_wifi(pj) -> list[dict]:
    aps = access_points(pj)
    out = []
    for a in pj.TERREO + pj.SUPERIOR + pj.TERREO_ABERTO:
        pav = "S" if a.cod.startswith("S-") else "T"
        d = min(math.hypot(a.cx - ap["x"], a.cy - ap["y"]) + (0 if ap["pav"] == pav else 3_000) for ap in aps)
        out.append(dict(amb=a.cod, nome=a.nome, d_m=round(d / 1000, 1), coberto=d <= RAIO_WIFI))
    return out


def cameras(pj) -> list[dict]:
    L, Pf = pj.LOTE_L, pj.LOTE_P
    pt = pj.ACESSO_TESTADA
    p01 = next((x, y) for t, x, y, o, p in pj.VAOS if t == "P01")
    gar = next(a for a in pj.TERREO if a.cod == "T-GAR")
    ps = pj.PISCINA
    cams = [dict(cod="CAM-01", onde="canto sul-leste do muro", x=600, y=600, olha="testada e recuo sul"),
            dict(cod="CAM-02", onde="canto norte-leste do muro", x=L - 600, y=600, olha="testada e faixa tecnica"),
            dict(cod="CAM-03", onde="canto sul-oeste do muro", x=600, y=Pf - 600, olha="fundo e recuo sul"),
            dict(cod="CAM-04", onde="canto norte-oeste do muro", x=L - 600, y=Pf - 600, olha="fundo e faixa tecnica"),
            dict(cod="CAM-05", onde="frente da garagem, sobre o PG01", x=pt["veiculo_x"], y=pj.RECUO_FRENTE - 300, olha="acesso, rua e testada aberta"),
            dict(cod="CAM-06", onde="portico de entrada", x=p01[0], y=p01[1] - 1_200, olha="porta de entrada e varanda"),
            dict(cod="CAM-07", onde="deck da piscina", x=ps["x"] + ps["w"] / 2, y=ps["y"] - 1_500, olha="piscina (seguranca de criancas)"),
            dict(cod="CAM-08", onde="garagem", x=gar.x + gar.w / 2, y=gar.y + gar.h - 600, olha="veiculos e rack")]
    for c in cams:
        c["cabo_mm"] = _cabo(pj, c["x"], c["y"])
        c["tipo"] = "IP 4 MP, IR 30 m, IP67, PoE"
    return cams


def alarme(pj) -> dict:
    mag = [dict(cod=f"MG-{t}-{i}", vao=t, amb=pj.amb_do_vao(x, y, p), x=x, y=y, pav=p)
           for i, (t, x, y, o, p) in enumerate(pj.VAOS, 1)
           if pj.vao_externo(x, y, o, p) and not t.startswith("J")]
    ivp = [dict(cod=f"IVP-{a.cod}", amb=a.cod, x=a.cx, y=a.cy, pav=_pav(a.cod))
           for a in pj.TERREO + pj.SUPERIOR if pj.CATEGORIA.get(a.cod) in ("circulacao", "social", "apoio")]
    import nucleo.externo as _ex
    p01 = next((x, y) for t, x, y, o, p in pj.VAOS if t == "P01")
    # R83 — testada aberta: nao ha portao de pedestre. O videoporteiro vai para
    # o portico da P01 e as fechaduras eletricas para os portoes laterais.
    acesso = [dict(cod="VP-01", onde="portico da porta P01", x=p01[0] + 900, y=p01[1] - 150, item="videoporteiro IP com abertura remota"),
              dict(cod="FE-02", onde="porta de entrada P01", x=p01[0], y=p01[1], item="fechadura eletronica biometrica + senha")]
    acesso += [dict(cod=f"FE-{pg['cod']}", onde=f"portao lateral {pg['cod']}", x=(pg["x0"] + pg["x1"]) / 2, y=pg["y"],
                    item="fechadura eletromagnetica 12 V, botoeira interna") for pg in _ex.portoes_laterais(pj)]
    acesso += [
              dict(cod="SR-01", onde="fachada norte, sob o beiral", x=16_800, y=9_000, item="sirene externa 120 dB com bateria")]
    mag += [dict(cod=f"MG-{pg['cod']}", vao=pg["cod"], amb="externo", x=(pg["x0"] + pg["x1"]) / 2, y=pg["y"], pav="T")
            for pg in _ex.portoes_laterais(pj)]
    return dict(magneticos=mag, ivp=ivp, acesso=acesso, central="central de alarme no rack TC-07, GPRS + Wi-Fi, 16 zonas",
                zonas=len(mag) + len(ivp))


def automacao(pj) -> dict:
    import nucleo.circuitos as ci
    ilum = [c for c in ci.circuitos(pj) if c["tipo"] == "iluminacao"
            and pj.CATEGORIA.get(c["amb"]) in ("social", "circulacao", "apoio")]
    modulos = [dict(cod=f"AUT-{c['cod']}", circuito=c["cod"], amb=c["amb"], tipo="dimmer Zigbee 200 W" if pj.CATEGORIA.get(c["amb"]) == "social" else "rele Zigbee 10 A")
               for c in ilum]
    modulos.append(dict(cod="AUT-IF", circuito="iluminacao de fachada", amb="externo", tipo="rele Zigbee 16 A + relogio astronomico"))
    modulos.append(dict(cod="AUT-PORTAO", circuito="TUE-20", amb="T-GAR", tipo="contato seco no motor do portao"))
    cortinas = [dict(cod=f"CORT-{a.cod}", amb=a.cod, tipo="motor tubular Zigbee 1,2 N.m no trilho da blackout")
                for a in pj.TERREO + pj.SUPERIOR if pj.CATEGORIA.get(a.cod) == "intimo" and a.cod != "T-ALC"]
    sensores = [dict(cod=f"PRES-{a.cod}", amb=a.cod, tipo="presenca + luminosidade Zigbee, acende a circulacao a noite")
                for a in pj.TERREO + pj.SUPERIOR if pj.CATEGORIA.get(a.cod) == "circulacao"]
    return dict(protocolo=PROTOCOLO, hub="hub Zigbee no rack, com backup de bateria", modulos=modulos,
                cortinas=cortinas, sensores=sensores, cenas=CENAS,
                comandos=[dict(cod=f"CENA-{k}", onde=o) for k, o in (("1", "hall de entrada"), ("2", "cabeceira da master"),
                                                                    ("3", "hall superior"), ("4", "estar"))])


def incendio(pj) -> dict:
    ambs = {a.cod: a for a in pj.TERREO + pj.SUPERIOR}
    ext = [dict(cod="EXT-01", amb="T-GAR", x=ambs["T-GAR"].x + 600, y=ambs["T-GAR"].y + 3_000, pav="T", item=EXTINTOR + " (garagem)"),
           dict(cod="EXT-02", amb="T-COZ", x=ambs["T-COZ"].x + 1_500, y=ambs["T-COZ"].y + 600, pav="T", item=EXTINTOR + " (cozinha)"),
           dict(cod="EXT-03", amb="S-HAL", x=ambs["S-HAL"].cx, y=ambs["S-HAL"].cy, pav="S", item=EXTINTOR + " (hall superior)")]
    det = []
    for a in pj.TERREO + pj.SUPERIOR:
        cat = pj.CATEGORIA.get(a.cod)
        if cat in ("intimo", "circulacao"):
            det.append(dict(cod=f"DF-{a.cod}", amb=a.cod, x=a.cx, y=a.cy, pav=_pav(a.cod), tipo=DETECTOR))
    det.append(dict(cod="DC-T-COZ", amb="T-COZ", x=ambs["T-COZ"].cx, y=ambs["T-COZ"].cy, pav="T",
                    tipo="detector de calor (a fumaca da coccao daria alarme falso)"))
    outros = [dict(cod="MT-01", amb="T-COZ", item="manta antichamas 1,2 x 1,2 m"), dict(cod="MT-02", amb="T-GOU", item="manta antichamas 1,2 x 1,2 m"),
              dict(cod="GAS", amb="T-COZ", item="detector de GLP a 300 mm do piso, junto ao cooktop, com corte automatico na central")]
    return dict(extintores=ext, detectores=det, outros=outros,
                exigencia="residencia unifamiliar: dispensada de projeto de prevencao (CBM-AM); o que esta aqui e boa pratica, "
                          "nao exigencia — e por isso e declarado assim")


def resumo(pj) -> dict:
    pd = pontos_dados(pj); al = alarme(pj); au = automacao(pj); inc = incendio(pj)
    cab = sum(p["cabo_mm"] * p["n"] for p in pd) + sum(a["cabo_mm"] for a in access_points(pj)) + sum(c["cabo_mm"] for c in cameras(pj))
    return dict(pontos_dados=sum(p["n"] for p in pd), access_points=len(access_points(pj)), cameras=len(cameras(pj)),
                cabo_utp_m=round(cab / 1000, 0), magneticos=len(al["magneticos"]), ivp=len(al["ivp"]),
                modulos_automacao=len(au["modulos"]), cortinas=len(au["cortinas"]),
                extintores=len(inc["extintores"]), detectores=len(inc["detectores"]),
                cobertos=sum(1 for c in cobertura_wifi(pj) if c["coberto"]), ambientes=len(cobertura_wifi(pj)))


def conferir(pj) -> list[tuple[str, str, bool]]:
    out = []
    for c in cobertura_wifi(pj):
        out.append((f"wi-fi {c['amb']}", f"{c['d_m']} m do AP mais proximo (raio {RAIO_WIFI / 1000:.0f} m)", c["coberto"]))
    for p in pontos_dados(pj) + cameras(pj) + access_points(pj):
        out.append((f"cabo {p['cod']}", f"{p['cabo_mm'] / 1000:.1f} m ate o rack (maximo {CABO_MAX / 1000:.0f})", p["cabo_mm"] <= CABO_MAX))
    al = alarme(pj)
    n_ext = sum(1 for t, x, y, o, p in pj.VAOS if pj.vao_externo(x, y, o, p) and not t.startswith("J"))
    n_pg = len(getattr(pj, "PORTOES_LATERAIS", []))     # R83: portoes laterais tambem levam sensor
    out.append(("todo vao externo de porta e portao lateral com sensor", f"{len(al['magneticos'])} de {n_ext + n_pg}", len(al["magneticos"]) == n_ext + n_pg))
    inc = incendio(pj)
    pavs = {e["pav"] for e in inc["extintores"]}
    out.append(("extintor por pavimento", f"{len(inc['extintores'])} extintores em {sorted(pavs)}", pavs == {"T", "S"}))
    dorm = [a.cod for a in pj.TERREO + pj.SUPERIOR if pj.CATEGORIA.get(a.cod) == "intimo"]
    det = {d["amb"] for d in inc["detectores"]}
    out.append(("detector em todo dormitorio", f"{len(set(dorm) & det)} de {len(dorm)}", set(dorm) <= det))
    return out
