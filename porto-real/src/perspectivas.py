"""PERSPECTIVAS — a casa vista de todos os lados, e cada comodo de dentro (R66).

O proprietario pediu "um desenho real de como vai ficar, de todos os angulos,
dos comodos". O que este modulo entrega e a MAQUETE ELETRONICA do modelo:
a mesma cena do visualizador (caixas com cor, sol de Manaus por hora e epoca,
sombra projetada, vidro translucido), fotografada de posicoes que sao
DERIVADAS do caso — a camera de cada comodo fica 700 mm para dentro da porta,
a 1.550 mm do piso, olhando para o centro; a camera externa gira em oito
azimutes em volta do envelope construido. Se um comodo mudar de lugar, a foto
muda junto. Nenhuma posicao e digitada.

O que NAO e: render fotorrealista. Nao ha textura, material nem iluminacao
global aqui. Para isso o modelo sai em OBJ (modelo3d.exportar_obj) e entra
num renderizador; a geometria e a mesma.

Saida: out/persp-<id>.png e out/perspectivas.json (o manifesto que as
pranchas 43 a 46 e a auditoria 139 leem — uma fonte).
"""
from __future__ import annotations

import glob
import json
import math
import os

import projeto as pj

AQUI = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(AQUI, "..", "out"))
MANIFESTO = os.path.join(OUT, "perspectivas.json")

OLHO = 1_550            # mm acima do piso: altura de olho de pe (NBR 9050 usa 1,50-1,60)
RECUO_PORTA = 700       # mm para dentro do comodo, a partir da porta
ALVO_Z = 1_300          # mm: para onde se olha, um pouco abaixo do olho
FOV_INTERNO = 62        # graus: dentro de um comodo o olho abrange mais
FOV_EXTERNO = 38        # graus: o mesmo do visualizador
AREA_MIN_ABERTO = 9.0   # m2: area aberta menor que isso nao rende uma vista
AREA_MIN_SUB = 4.0      # m2: subdivisao (banho, closet) que merece vista propria
CAMADAS_FOTO = ["terreo", "superior", "lajes", "platibandas", "cobertura",
                "externo", "tecnico", "mob", "escada", "luz"]


def _no_retangulo(a, x, y, folga=0) -> bool:
    return a.x + folga <= x <= a.x + a.w - folga and a.y + folga <= y <= a.y + a.h - folga


def _sub_de(cod: str) -> list[dict]:
    return [d for d in pj.SUBDIVISOES if d["pai"] == cod]


def _em_subdivisao(cod: str, x, y) -> bool:
    return any(d["x"] <= x <= d["x"] + d["w"] and d["y"] <= y <= d["y"] + d["h"]
               for d in _sub_de(cod))


def _piso(pav: str) -> int:
    return 0 if pav == "T" else pj.PISO_A_PISO


def _portas_do(a) -> list[tuple]:
    """(x, y, nx, ny) de cada porta do comodo: centro e normal para DENTRO."""
    out = []
    for tipo, x, y, ori, pav in pj.VAOS:
        if pav != a.pav or not tipo.startswith(("P", "PG", "PV")):
            continue
        if ori == "H":
            lados = ((0, 1), (0, -1))
        else:
            lados = ((1, 0), (-1, 0))
        for nx, ny in lados:
            if _no_retangulo(a, x + nx * 300, y + ny * 300):
                out.append((x, y, nx, ny))
                break
    return out


_CAIXAS = None


def _caixas() -> list[tuple]:
    """Toda caixa opaca da cena 3D (paredes, moveis, escada, tecnico): e contra
    ela que se testa se a camera esta dentro de algo ou olhando para algo."""
    global _CAIXAS
    if _CAIXAS is None:
        import modelo3d
        d = modelo3d.exportar()
        out = []
        for g in ("terreo", "superior", "mob", "escada", "externo"):
            for b in d.get(g, []):
                if b["t"] not in ("parede", "mob", "escada", "pilar", "tecnico", "muro", "brise"):
                    continue
                (cx, cy, cz), (sx, sy, sz) = b["p"], b["s"]
                out.append((cx - sx / 2, cy - sy / 2, cz - sz / 2, cx + sx / 2, cy + sy / 2, cz + sz / 2))
        _CAIXAS = out
    return _CAIXAS


def _em_caixa(x, y, z) -> bool:
    return any(x0 <= x <= x1 and y0 <= y <= y1 and z0 <= z <= z1 for x0, y0, z0, x1, y1, z1 in _caixas())


def _coluna_livre(x, y, z_piso, z_olho) -> bool:
    """Ninguem fica de pe dentro de um carro ou de uma bancada: a coluna do
    joelho ao olho tem de estar fora de qualquer caixa."""
    return not any(x0 <= x <= x1 and y0 <= y <= y1 and z0 < z_olho and z1 > z_piso + 250
                   for x0, y0, z0, x1, y1, z1 in _caixas())


def _abertura(px, py, pz, tx, ty, alcance=8_000) -> float:
    """Profundidade media do olhar num leque de 60 graus: uma fresta entre dois
    armarios altos nao e vista; um comodo aberto e."""
    ang = math.atan2(ty - py, tx - px)
    tot = 0.0
    for da in (-30, -15, 0, 15, 30):
        a = ang + math.radians(da)
        tot += _profundidade(px, py, pz, px + math.cos(a) * 1000, py + math.sin(a) * 1000, alcance)
    return tot / 5


def _profundidade(px, py, pz, tx, ty, alcance=8_000) -> float:
    """Quantos mm o olhar avanca de (px,py) para (tx,ty) antes de bater em algo."""
    d = math.hypot(tx - px, ty - py) or 1
    ux, uy = (tx - px) / d, (ty - py) / d
    for s in range(150, alcance + 1, 150):
        if _em_caixa(px + ux * s, py + uy * s, pz):
            return s
    return alcance


def _vista_comodo(a) -> dict:
    """Camera de um comodo: entre as portas (700 mm para dentro), os cantos e o
    meio das paredes, fica o ponto de onde o olhar vai mais longe em direcao
    ao centro sem bater em parede ou movel. Porta ganha o empate: e a vista de
    quem entra."""
    cx, cy = a.x + a.w / 2, a.y + a.h / 2
    z0 = _piso(a.pav); pz = z0 + OLHO
    cands = []
    for x, y, nx, ny in _portas_do(a):
        cands.append((x + nx * RECUO_PORTA, y + ny * RECUO_PORTA, "porta"))
    r = 500
    for px, py in ((a.x + r, a.y + r), (a.x + a.w - r, a.y + r),
                   (a.x + r, a.y + a.h - r), (a.x + a.w - r, a.y + a.h - r),
                   (cx, a.y + r), (cx, a.y + a.h - r), (a.x + r, cy), (a.x + a.w - r, cy)):
        cands.append((px, py, "canto"))
    melhor = None
    for px, py, origem in cands:
        if (not _no_retangulo(a, px, py, 100) or _em_subdivisao(a.cod, px, py)
                or not _coluna_livre(px, py, z0, pz)):
            continue
        prof = _abertura(px, py, pz, cx, cy)
        score = prof + (400 if origem == "porta" else 0)
        if melhor is None or score > melhor[0]:
            melhor = (score, px, py, origem)
    if melhor is None:                       # comodo todo ocupado: o centro mesmo
        melhor = (0, cx, cy, "centro")
    _, px, py, origem = melhor
    d = math.hypot(cx - px, cy - py)
    # alvo: o centro, empurrado para longe da camera para nao olhar para os pes
    ux, uy = (cx - px) / (d or 1), (cy - py) / (d or 1)
    tx, ty = cx + ux * min(a.w, a.h) / 4, cy + uy * min(a.w, a.h) / 4
    return dict(id=a.cod, titulo=a.nome.title(), grupo="terreo" if a.pav == "T" else "superior",
                amb=a.cod, pav=a.pav, tipo="interna", origem=origem,
                pos=[round(px), round(py), z0 + OLHO], alvo=[round(tx), round(ty), z0 + ALVO_Z],
                fov=FOV_INTERNO, hora=10.0 if a.pav == "T" else 15.0, camadas=CAMADAS_FOTO)


def _vista_sub(d) -> dict:
    """Subdivisao (banho, closet, office): mesma regra, no retangulo dela."""
    x, y, w, h = d["x"], d["y"], d["w"], d["h"]
    cx, cy = x + w / 2, y + h / 2
    pav = d["pai"][0]; z0 = _piso(pav); pz = z0 + OLHO
    r = 400
    melhor = None
    for px, py in ((x + r, y + r), (x + w - r, y + r), (x + r, y + h - r), (x + w - r, y + h - r),
                   (cx, y + r), (cx, y + h - r), (x + r, cy), (x + w - r, cy)):
        if not _coluna_livre(px, py, z0, pz):
            continue
        prof = _abertura(px, py, pz, cx, cy, 6_000)
        if melhor is None or prof > melhor[0]:
            melhor = (prof, px, py)
    _, px, py = melhor if melhor else (0, cx, cy)
    cod = f"{d['pai']}/{d['nome']}"
    pai = next(a for a in pj.TERREO + pj.SUPERIOR if a.cod == d["pai"])
    return dict(id=cod.replace("/", "-"), titulo=f"{d['nome'].title()} — {pai.nome.title()}",
                grupo="terreo" if pav == "T" else "superior", amb=cod, pav=pav,
                tipo="interna", origem="canto",
                pos=[round(px), round(py), z0 + OLHO], alvo=[round(cx), round(cy), z0 + ALVO_Z],
                fov=FOV_INTERNO + 8, hora=10.0 if pav == "T" else 15.0, camadas=CAMADAS_FOTO)


def _envelope():
    ambs = pj.TERREO + pj.SUPERIOR
    return (min(a.x for a in ambs), min(a.y for a in ambs),
            max(a.x + a.w for a in ambs), max(a.y + a.h for a in ambs))


def _centro_casa():
    x0, y0, x1, y1 = _envelope()
    return (x0 + x1) / 2, (y0 + y1) / 2


# +x = NORTE, +y = OESTE (piscina), x = 0 SUL, y = 0 LESTE (testada)
AZIMUTES = [(0, "do norte (faixa tecnica)", 12.0), (45, "do noroeste", 15.0),
            (90, "do oeste (piscina)", 16.0), (135, "do sudoeste", 15.0),
            (180, "do sul (loggia)", 12.0), (225, "do sudeste", 10.0),
            (270, "do leste (rua)", 9.0), (315, "do nordeste", 10.0)]


def _vistas_externas() -> list[dict]:
    x0, y0, x1, y1 = _envelope()
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    diag = math.hypot(x1 - x0, y1 - y0)
    dist = diag * 1.15
    out = []
    for az, nome, hora in AZIMUTES:
        a = math.radians(az)
        out.append(dict(id=f"ext-{az:03d}", titulo=f"Vista {nome}", grupo="externa",
                        amb="-", pav="T", tipo="externa", origem="azimute",
                        pos=[round(cx + dist * math.cos(a)), round(cy + dist * math.sin(a)), 6_500],
                        alvo=[round(cx), round(cy), 2_500], fov=FOV_EXTERNO + 8, hora=hora,
                        camadas=CAMADAS_FOTO))
    for az, nome, hora in ((225, "aerea do sudeste", 10.0), (45, "aerea do noroeste", 15.0)):
        a = math.radians(az)
        out.append(dict(id=f"aer-{az:03d}", titulo=f"Vista {nome}", grupo="externa",
                        amb="-", pav="T", tipo="externa", origem="azimute",
                        pos=[round(cx + dist * 1.1 * math.cos(a)), round(cy + dist * 1.1 * math.sin(a)),
                             round(dist * 0.9)],
                        alvo=[round(cx), round(cy), 1_500], fov=FOV_EXTERNO, hora=hora,
                        camadas=CAMADAS_FOTO))
    return out


def vistas() -> list[dict]:
    """Toda vista, derivada do caso. Ordem: externas, terreo, abertas, superior."""
    out = _vistas_externas()
    for a in pj.TERREO:
        out.append(_vista_comodo(a))
    for d in pj.SUBDIVISOES:
        if d["pai"].startswith("T-") and d["w"] * d["h"] / 1e6 >= AREA_MIN_SUB:
            out.append(_vista_sub(d))
    abertas = []
    for a in pj.TERREO_ABERTO:
        if a.w * a.h / 1e6 >= AREA_MIN_ABERTO:
            v = _vista_comodo(a); v["grupo"] = "abertas"; abertas.append(v)
    out += abertas
    for a in pj.SUPERIOR:
        out.append(_vista_comodo(a))
    vistos = set()
    for d in pj.SUBDIVISOES:
        if d["pai"].startswith("S-") and d["w"] * d["h"] / 1e6 >= AREA_MIN_SUB:
            chave = (d["nome"], round(d["w"] * d["h"]))
            if chave in vistos and d["pai"] in ("S-S03",):   # espelho da suite 02
                continue
            vistos.add(chave)
            out.append(_vista_sub(d))
    return out


def _orbita(v: dict) -> dict:
    (px, py, pz), (tx, ty, tz) = v["pos"], v["alvo"]
    d = math.dist(v["pos"], v["alvo"])
    return dict(dist=d, azim=math.degrees(math.atan2(py - ty, px - tx)),
                elev=math.degrees(math.asin((pz - tz) / d)))


def renderizar(so: set | None = None, largura: int = 1400, altura: int = 900) -> dict:
    """Fotografa cada vista no visualizador headless e grava o manifesto."""
    from playwright.sync_api import sync_playwright
    import viewer_teste as vt
    srv, porta = vt.servir(OUT)
    lista = vistas()
    with sync_playwright() as p:
        nav = p.chromium.launch(executable_path=vt.CHROME,
                                args=["--no-sandbox", "--use-gl=angle", "--use-angle=swiftshader",
                                      "--enable-unsafe-swiftshader"])
        pag = nav.new_page(viewport={"width": largura + 360, "height": altura + 120})
        tres = next((c for c in vt.TRES_LOCAL if os.path.exists(c)), None)
        if tres:
            pag.route("**/three.min.js", lambda r: r.fulfill(path=tres))
        pag.goto(f"http://127.0.0.1:{porta}/porto-real-caderno.html")
        pag.click(".modos button[data-modo='3d']")
        pag.wait_for_function("() => typeof R !== 'undefined' && R && R.solidos.length > 0",
                              timeout=60_000)
        pag.wait_for_timeout(400)
        pag.evaluate("""() => {
          // a foto e a cena, nao a interface: some tudo que nao e o canvas
          const st = document.getElementById('stage3d');
          [...st.querySelectorAll('*')].forEach(e => {
            if (e.tagName !== 'CANVAS' && !e.querySelector('canvas')) e.style.visibility = 'hidden';
          });
          R.solTrajeto.visible = false; R.solMarca.visible = false;
        }""")
        for v in lista:
            if so and v["id"] not in so:
                continue
            c = _orbita(v)
            pag.evaluate("""(q) => {
              R.alvo.set(q.alvo[0], q.alvo[1], q.alvo[2]);
              R.dist = q.dist; R.azim = q.azim; R.elev = q.elev;
              R.cam.fov = q.fov; R.cam.updateProjectionMatrix();
              const mostra = new Set(q.camadas);
              CAMADAS.forEach(([id], i) => {
                R.grupos[id].visible = mostra.has(id);
                const inp = document.querySelectorAll('#camadas input')[i];
                if (inp) inp.checked = mostra.has(id);
              });
              const corte = document.getElementById('corte');
              corte.value = corte.max; corte.dispatchEvent(new Event('input'));
              const hr = document.getElementById('solHora');
              hr.value = q.hora; hr.dispatchEvent(new Event('input'));
              R.cena.traverse(o => { if (o.isHemisphereLight) {
                o.intensity = q.interna ? 1.0 : 0.5;
                o.groundColor.set(q.interna ? 0xd6d0c6 : 0x6b6257); } });
              R.solTrajeto.visible = false; R.solMarca.visible = false;
              R.render();
            }""", dict(alvo=v["alvo"], dist=c["dist"], azim=c["azim"], elev=c["elev"],
                       fov=v["fov"], camadas=v["camadas"], hora=v["hora"],
                       interna=v["tipo"] == "interna"))
            pag.wait_for_timeout(120)
            pag.locator("#stage3d canvas").first.screenshot(
                path=os.path.join(OUT, f"persp-{v['id']}.png"))
        nav.close()
    srv.shutdown()
    man = dict(revisao=pj.EMISSAO["revisao"], olho=OLHO, recuo_porta=RECUO_PORTA, vistas=lista)
    json.dump(man, open(MANIFESTO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return man


def manifesto() -> dict | None:
    return json.load(open(MANIFESTO, encoding="utf-8")) if os.path.exists(MANIFESTO) else None


def conferir() -> list[dict]:
    """Toda vista tem foto, toda camera esta no seu comodo, todo comodo tem vista."""
    falhas = []
    m = manifesto()
    if m is None:
        return [dict(tipo="manifesto", msg="perspectivas.json ausente: rode build.py")]
    if m["revisao"] != pj.EMISSAO["revisao"]:
        falhas.append(dict(tipo="revisao", msg=f"fotos de {m['revisao']}, caso em {pj.EMISSAO['revisao']}"))
    ambs = {a.cod: a for a in pj.TERREO + pj.SUPERIOR + pj.TERREO_ABERTO}
    com_vista = {v["amb"] for v in m["vistas"]}
    for a in pj.TERREO + pj.SUPERIOR:
        if a.cod not in com_vista:
            falhas.append(dict(tipo="sem vista", msg=a.cod))
    for a in pj.TERREO_ABERTO:
        if a.w * a.h / 1e6 >= AREA_MIN_ABERTO and a.cod not in com_vista:
            falhas.append(dict(tipo="sem vista", msg=a.cod))
    for v in m["vistas"]:
        if not os.path.exists(os.path.join(OUT, f"persp-{v['id']}.png")):
            falhas.append(dict(tipo="sem foto", msg=v["id"]))
        if v["tipo"] == "interna":
            px, py, pz = v["pos"]
            if "/" in v["amb"]:
                d = next(x for x in pj.SUBDIVISOES if f"{x['pai']}/{x['nome']}" == v["amb"])
                ok = d["x"] <= px <= d["x"] + d["w"] and d["y"] <= py <= d["y"] + d["h"]
            else:
                a = ambs[v["amb"]]
                ok = _no_retangulo(a, px, py) and not _em_subdivisao(a.cod, px, py)
            if not ok:
                falhas.append(dict(tipo="camera fora do comodo", msg=v["id"]))
            if pz - _piso(v["pav"]) != OLHO:
                falhas.append(dict(tipo="altura de olho", msg=v["id"]))
    return falhas


if __name__ == "__main__":
    import sys
    so = {x for x in sys.argv[1:] if not x.startswith("--")} or None
    m = renderizar(so)
    print(f"{len(m['vistas'])} vistas; fotos em {OUT}/persp-*.png")
    for f in conferir():
        print("  !!", f)
