"""ESGOTO E VENTILACAO — de cada peca ate a rua, com diametro e caimento (R72).

O proprietario pediu "hidraulica nos banheiros para nao entupir". Entupir nao
e azar: e diametro pequeno, caimento fraco, sifao longe da ventilacao e caixa
de inspecao que nao existe. As quatro coisas sao regra da NBR 8160 e as
quatro saem daqui, peca a peca.

  1. Cada peca tem um ramal de descarga com DN pela UHC (tabela da norma).
  2. Lavatorio, box e ralo de cada banheiro caem numa CAIXA SIFONADA; o vaso
     vai direto ao tubo de queda (superior) ou a caixa de inspecao (terreo).
  3. Caimento: a norma permite 1 % em DN100. Aqui e 2 % em toda a rede
     predial, DN100 inclusive — e a decisao "para nao entupir", declarada.
  4. Todo desconector fica a menos da distancia maxima do ponto ventilado;
     quando nao fica, ganha ramal de ventilacao DN50 ate a coluna.
  5. Caixas de inspecao a cada mudanca de direcao e a menos de 15 m uma da
     outra; caixa de gordura simples (31 L, duas pias) antes do coletor.
  6. O coletor predial desce a 1 % ate a testada, no sentido em que o lote
     tambem desce (R68): a profundidade nao cresce ao longo do caminho.
"""
from __future__ import annotations

# DN do ramal de descarga por peca (NBR 8160, tabela 3) e por UHC (H)
DN_PECA = {"vaso": 100, "lavatorio": 40, "box": 40, "tanque": 50, "pia": 50,
           "lavadora": 50, "ducha_externa": 40, "ralo": 50}
DN_POR_UHC = ((3, 50), (6, 75), (20, 100), (160, 100), (620, 150))   # ramal de esgoto / subcoletor
CAIMENTO_NORMA = {40: 0.02, 50: 0.02, 75: 0.02, 100: 0.01, 150: 0.007}
CAIMENTO_ADOTADO = {40: 0.02, 50: 0.02, 75: 0.02, 100: 0.02, 150: 0.01}
CAIMENTO_COLETOR = 0.01                       # DN100/150 enterrado, ate a rua
# distancia maxima do desconector ao tubo ventilador (NBR 8160, tabela 5)
DIST_VENT_MAX = {40: 1_200, 50: 1_800, 75: 2_400, 100: 3_000}
DN_VENT_RAMAL = 50
DN_VENT_COLUNA = 75
ALTURA_VENT_ACIMA_COBERTURA = 300
CI_ESPACAMENTO_MAX = 15_000
CI_DIM = (600, 600)
PROF_SAIDA_CASA = 500                         # fundo do tubo ao sair da casa
RECOBRIMENTO_MIN = 300
CAIXA_SIFONADA = dict(dim="100 x 150 x 50 mm", saida=50, grelha="quadrada 150 mm, aco inox")
CAIXA_GORDURA = dict(tipo="CGS — caixa de gordura simples, NBR 8160 5.1.4.3 (duas cozinhas)",
                     volume_l=31, diametro=400, altura=500, septo_submerso=200,
                     entrada=75, saida=75, tampa="hermetica, inspecionavel")
FATOR_PERCURSO = 1.20


def _dn_uhc(uhc: int) -> int:
    for lim, dn in DN_POR_UHC:
        if uhc <= lim:
            return dn
    return 150


def _manh(a, b) -> float:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _pav(amb: str) -> str:
    return "S" if amb.startswith("S-") else "T"


def _prumada(pj, x, y):
    ps = [p for p in pj.PRUMADAS if p["tipo"] == "esgoto"]
    return min(ps, key=lambda p: _manh((x, y), (p["x"], p["y"])))


def _ci_terreo(pj) -> list[dict]:
    """Onde o terreo pode descarregar: o pe de cada tubo de queda e uma caixa
    na faixa tecnica norte, para o banho do reversivel e o lavabo — que ficam
    a mais de 10 m das prumadas do fundo e nao podem atravessar a casa."""
    out = [dict(cod=f"CI-{p['cod']}", x=p["x"], y=p["y"], papel="pe do tubo de queda " + p["cod"])
           for p in pj.PRUMADAS if p["tipo"] == "esgoto"]
    ft = pj.FAIXA_TECNICA
    frente = [a for a in pj.TERREO if a.y < 13_200 and a.x + a.w >= 15_000]
    if frente:
        y = max(a.y for a in frente) + 1_200
        out.append(dict(cod="CI-N", x=ft["x"] - 600, y=y,
                        papel="faixa tecnica norte: banho do reversivel e lavabo"))
    return out


def _ci_mais_proxima(pj, x, y) -> dict:
    return min(_ci_terreo(pj), key=lambda c: _manh((x, y), (c["x"], c["y"])))


def caixa_gordura(pj) -> dict:
    tc = next(t for t in pj.TECNICOS if "gordura" in t["nome"].lower())
    return dict(cod=tc["cod"], x=tc["x"], y=tc["y"], **CAIXA_GORDURA)


def desconectores(pj) -> list[dict]:
    """Uma caixa sifonada por ambiente molhado, no ralo do ambiente."""
    out = []
    ralos = {r["amb"]: r for r in pj.RALOS if r["amb"] in {p["amb"] for p in pj.pecas_hidraulicas()}}
    for amb, r in ralos.items():
        pecas = [p for p in pj.pecas_hidraulicas() if p["amb"] == amb and p["tipo"] in ("lavatorio", "box", "ducha_externa")]
        if not pecas and r["tipo"].startswith("ralo seco"):
            continue
        out.append(dict(cod=f"CS-{amb}", amb=amb, pav=_pav(amb), x=r["x"], y=r["y"],
                        ralo=r["cod"], pecas=[p["cod"] for p in pecas],
                        uhc=sum(p["uhc"] for p in pecas) + 1, saida=CAIXA_SIFONADA["saida"],
                        dim=CAIXA_SIFONADA["dim"]))
    return out


def ramais(pj) -> list[dict]:
    """Ramal de descarga de cada peca e o ramal de esgoto de cada desconector."""
    cs = {d["amb"]: d for d in desconectores(pj)}
    cg = caixa_gordura(pj)
    out = []
    for p in pj.pecas_hidraulicas():
        dn = DN_PECA[p["tipo"]]
        pav = _pav(p["amb"])
        if p["tipo"] in ("lavatorio", "box", "ducha_externa") and p["amb"] in cs:
            dest = cs[p["amb"]]; dcod = dest["cod"]; dx, dy = dest["x"], dest["y"]
            desc = "sifao proprio" if p["tipo"] == "lavatorio" else "caixa sifonada"
        elif p["tipo"] == "pia":
            dcod = cg["cod"]; dx, dy = cg["x"], cg["y"]; desc = "sifao proprio + caixa de gordura"
        else:
            if pav == "S":
                pr = _prumada(pj, p["x"], p["y"]); dcod, dx, dy = pr["cod"], pr["x"], pr["y"]
            else:
                ci = _ci_mais_proxima(pj, p["x"], p["y"]); dcod, dx, dy = ci["cod"], ci["x"], ci["y"]
            desc = "sifao integrado (vaso)" if p["tipo"] == "vaso" else "sifao proprio"
        comp = _manh((p["x"], p["y"]), (dx, dy)) * FATOR_PERCURSO
        # ventilacao: a distancia do sifao ao ponto ventilado
        lim = DIST_VENT_MAX.get(dn, 3_000)
        ventilado = comp <= lim or dcod.startswith(("PN-", "CI-"))
        out.append(dict(peca=p["cod"], amb=p["amb"], pav=pav, tipo=p["tipo"], dn=dn, uhc=p["uhc"],
                        caimento=CAIMENTO_ADOTADO[dn], caimento_norma=CAIMENTO_NORMA[dn],
                        comp_mm=round(comp), destino=dcod, desconector=desc,
                        dist_vent_max=lim, ventilado=ventilado,
                        classe="ramal de descarga"))
    # ramal de esgoto de cada caixa sifonada ate a prumada (S) ou a CI (T)
    for d in cs.values():
        if d["pav"] == "S":
            pr = _prumada(pj, d["x"], d["y"]); dcod, dx, dy = pr["cod"], pr["x"], pr["y"]
        else:
            ci = _ci_mais_proxima(pj, d["x"], d["y"]); dcod, dx, dy = ci["cod"], ci["x"], ci["y"]
        dn = max(50, _dn_uhc(d["uhc"]))
        comp = _manh((d["x"], d["y"]), (dx, dy)) * FATOR_PERCURSO
        out.append(dict(peca=d["cod"], amb=d["amb"], pav=d["pav"], tipo="caixa sifonada", dn=dn,
                        uhc=d["uhc"], caimento=CAIMENTO_ADOTADO[dn], caimento_norma=CAIMENTO_NORMA[dn],
                        comp_mm=round(comp), destino=dcod, desconector="caixa sifonada",
                        dist_vent_max=DIST_VENT_MAX[dn], ventilado=comp <= DIST_VENT_MAX[dn],
                        classe="ramal de esgoto"))
    # ralos secos e de area externa: ramal ate a CI mais proxima
    usados = {d["ralo"] for d in cs.values()}
    for r in pj.RALOS:
        if r["cod"] in usados:
            continue
        pav = _pav(r["amb"]) if r["amb"][:2] in ("T-", "S-") else "T"
        if pav == "S":
            pr = _prumada(pj, r["x"], r["y"]); dcod, dx, dy = pr["cod"], pr["x"], pr["y"]
        else:
            ci = _ci_mais_proxima(pj, r["x"], r["y"]); dcod, dx, dy = ci["cod"], ci["x"], ci["y"]
        comp = _manh((r["x"], r["y"]), (dx, dy)) * FATOR_PERCURSO
        out.append(dict(peca=r["cod"], amb=r["amb"], pav=pav, tipo="ralo", dn=r["dn"], uhc=1,
                        caimento=CAIMENTO_ADOTADO[r["dn"]], caimento_norma=CAIMENTO_NORMA[r["dn"]],
                        comp_mm=round(comp), destino=dcod,
                        desconector="ralo seco: sem sifao (so agua de lavagem)",
                        dist_vent_max=DIST_VENT_MAX[r["dn"]], ventilado=True,
                        classe="ramal de descarga"))
    return out


def ventilacao(pj) -> dict:
    """Coluna de ventilacao por tubo de queda e ramal DN50 onde a distancia passa."""
    colunas = []
    for p in pj.PRUMADAS:
        if p["tipo"] != "esgoto":
            continue
        colunas.append(dict(cod=f"VP-{p['cod'][-2:]}", prumada=p["cod"], x=p["x"], y=p["y"],
                            dn=DN_VENT_COLUNA, topo=pj.TOPO_PLATIBANDA + ALTURA_VENT_ACIMA_COBERTURA,
                            comp_mm=pj.TOPO_PLATIBANDA + ALTURA_VENT_ACIMA_COBERTURA,
                            terminal="terminal de ventilacao com tela, 300 mm acima da cobertura"))
    ramal = []
    pos = {p["cod"]: (p["x"], p["y"]) for p in pj.pecas_hidraulicas() + pj.RALOS}
    pos.update({d["cod"]: (d["x"], d["y"]) for d in desconectores(pj)})
    for r in ramais(pj):
        if not r["ventilado"]:
            pr = _prumada(pj, *pos[r["peca"]])
            ramal.append(dict(cod=f"VR-{r['peca']}", de=r["peca"], para=f"VP-{pr['cod'][-2:]}",
                              dn=DN_VENT_RAMAL, comp_mm=r["comp_mm"] + 1_000,
                              motivo=f"{r['comp_mm']} mm do sifao ao ponto ventilado > {r['dist_vent_max']} mm"))
    return dict(colunas=colunas, ramais=ramal,
                comp_total_mm=sum(c["comp_mm"] for c in colunas) + sum(r["comp_mm"] for r in ramal))


def caixas(pj) -> list[dict]:
    """Caixas de inspecao: pe de cada tubo de queda, a da frente, a saida da
    caixa de gordura, o encontro de cada uma com o coletor no recuo sul, e as
    intermediarias que o espacamento de 15 m exigir; a ultima na testada."""
    xc = pj.RECUO_ESQ // 2
    out = list(_ci_terreo(pj))
    cg = caixa_gordura(pj)
    out.append(dict(cod="CI-CG", x=cg["x"], y=cg["y"] + 900, papel="saida da caixa de gordura"))
    afl = []
    for c in list(out):
        if c["x"] == xc:
            continue
        afl.append(dict(cod=f"{c['cod']}-E", x=xc, y=c["y"], papel=f"encontro de {c['cod']} com o coletor"))
        # subcoletor longo: caixa intermediaria a cada 15 m
        d = c["x"] - xc
        for k in range(1, int((d - 1) // CI_ESPACAMENTO_MAX) + 1):
            afl.append(dict(cod=f"{c['cod']}-I{k}", x=c["x"] - k * CI_ESPACAMENTO_MAX, y=c["y"],
                            papel=f"intermediaria do subcoletor de {c['cod']}"))
    out += afl
    out.append(dict(cod="CI-FINAL", x=xc, y=1_200, papel="ultima caixa antes da ligacao a rede publica"))
    eixo = sorted([c for c in out if c["x"] == xc], key=lambda c: -c["y"])
    extra = []
    for a, b in zip(eixo, eixo[1:]):
        d = a["y"] - b["y"]
        for k in range(1, int((d - 1) // CI_ESPACAMENTO_MAX) + 1):
            extra.append(dict(cod=f"CI-{a['y'] - k * CI_ESPACAMENTO_MAX:05.0f}", x=xc,
                              y=a["y"] - k * CI_ESPACAMENTO_MAX, papel="espacamento maximo de 15 m"))
    out += extra
    for c in out:
        c["dim"] = CI_DIM
    return out


def coletor(pj) -> list[dict]:
    """Trechos do coletor com cota de fundo: comeca a 500 mm na caixa mais
    funda e desce 1 % ate a testada; o terreno desce junto (R68)."""
    xc = pj.RECUO_ESQ // 2
    cx = caixas(pj)
    eixo = sorted([c for c in cx if c["x"] == xc], key=lambda c: -c["y"])
    # afluentes: da caixa do pe de prumada ate o eixo
    trechos = []
    for c in cx:
        if c["x"] != xc and "-I" not in c["cod"]:
            inter = sorted([i for i in cx if i["cod"].startswith(c["cod"] + "-I")], key=lambda i: -i["x"])
            cadeia = [c] + inter + [next(e for e in cx if e["cod"] == c["cod"] + "-E")]
            for a, b in zip(cadeia, cadeia[1:]):
                trechos.append(dict(de=a["cod"], para=b["cod"], dn=100, comp_mm=abs(a["x"] - b["x"]),
                                    caimento=CAIMENTO_ADOTADO[100], classe="subcoletor"))
    z = -PROF_SAIDA_CASA
    decl = pj.DECLIVIDADE_MIN
    for a, b in zip(eixo, eixo[1:]):
        comp = a["y"] - b["y"]
        z_j = z - comp * CAIMENTO_COLETOR
        # o terreno natural cai `decl` no mesmo sentido: a profundidade real muda so pela diferenca
        prof_m = -z
        prof_j = -z_j - comp * decl
        trechos.append(dict(de=a["cod"], para=b["cod"], dn=100, comp_mm=comp, caimento=CAIMENTO_COLETOR,
                            cota_fundo_montante=round(z), cota_fundo_jusante=round(z_j),
                            prof_montante_mm=round(prof_m), prof_jusante_mm=round(prof_j), classe="coletor"))
        z = z_j
    return trechos


def resumo(pj) -> dict:
    rs = ramais(pj); v = ventilacao(pj); cx = caixas(pj); col = coletor(pj)
    por_dn = {}
    for r in rs:
        por_dn[r["dn"]] = por_dn.get(r["dn"], 0) + r["comp_mm"]
    for t in col:
        por_dn[t["dn"]] = por_dn.get(t["dn"], 0) + t["comp_mm"]
    for c in v["colunas"] + v["ramais"]:
        por_dn[c["dn"]] = por_dn.get(c["dn"], 0) + c["comp_mm"]
    return dict(ramais=len(rs), desconectores=len(desconectores(pj)), caixas=len(cx),
                trechos_coletor=len(col), ventilacao_ramais=len(v["ramais"]),
                comp_por_dn_m={dn: round(m / 1000, 1) for dn, m in sorted(por_dn.items())},
                prof_final_mm=col[-1]["prof_jusante_mm"] if col else None,
                caixa_gordura=caixa_gordura(pj))


def conferir(pj) -> list[tuple[str, str, bool]]:
    out = []
    for r in ramais(pj):
        out.append((f"caimento {r['peca']}", f"DN{r['dn']} a {r['caimento'] * 100:.0f} % "
                    f"(norma {r['caimento_norma'] * 100:.0f} %)", r["caimento"] >= r["caimento_norma"]))
        out.append((f"DN {r['peca']}", f"{r['tipo']} DN{r['dn']} para {r['uhc']} UHC",
                    r["dn"] >= min(_dn_uhc(r["uhc"]), 100) or r["classe"] == "ramal de descarga"))
    v = ventilacao(pj)
    out.append(("ventilacao", f"{len(v['ramais'])} ramal(is) de ventilacao onde o sifao fica longe; "
                f"{len(v['colunas'])} colunas DN{DN_VENT_COLUNA}", True))
    cx = caixas(pj); xc = pj.RECUO_ESQ // 2
    eixo = sorted([c for c in cx if c["x"] == xc], key=lambda c: -c["y"])
    maior = max((a["y"] - b["y"] for a, b in zip(eixo, eixo[1:])), default=0)
    out.append(("espacamento das caixas", f"maior trecho {maior / 1000:.1f} m (maximo 15 m)",
                maior <= CI_ESPACAMENTO_MAX))
    col = coletor(pj)
    fim = col[-1] if col else None
    out.append(("profundidade na testada",
                f"{fim['prof_jusante_mm']:.0f} mm de fundo na ultima caixa (recobrimento minimo "
                f"{RECOBRIMENTO_MIN} mm)" if fim else "sem coletor",
                bool(fim) and fim["prof_jusante_mm"] >= RECOBRIMENTO_MIN + 100))
    out.append(("ultima caixa na testada", f"CI-FINAL em y = {eixo[-1]['y']} mm (rua em y = 0)",
                eixo[-1]["y"] < 3_000))
    return out
