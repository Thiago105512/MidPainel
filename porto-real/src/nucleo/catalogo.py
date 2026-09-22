"""CATALOGO TECNICO — o desenho de cada peca, gerado da propria peca.

Por que DESENHAR e nao buscar a imagem do fabricante. A imagem de catalogo e de
um perfil generico, tem a marca de quem a publicou e nao responde pela peca
DESTE projeto: se a auditoria mudar uma espessura, a imagem continua a mesma e
passa a mentir em silencio. O desenho aqui sai das mesmas dimensoes que
alimentam o solver da NBR 14762 — o mesmo bw, o mesmo bf, o mesmo t — e por
isso nao existe estado em que o desenho e o calculo discordem.

A designacao ja E a dimensao: "Ue 90x40x12x0,95" diz alma 90, aba 40, labio 12,
espessura 0,95 mm. Nao ha nada a buscar. O que NAO se deduz da designacao — a
geometria exata da cabeca de um parafuso de um fabricante, a curva de
resistencia ensaiada de um sistema — continua (H) e continua pendencia, como
todo dado externo neste projeto.

O QUE ESTE MODULO NAO E. Nao e desenho de fabricacao. Ele nao traz tolerancia
de dobra, nao traz raio de ferramenta real e nao substitui o desenho do
perfilador. E o desenho de PROJETO: o que precisa ser verdade para o calculo
fechar e para quem compra saber o que esta comprando.
"""
from __future__ import annotations

# Escala do desenho em unidades de viewBox por milimetro de peca. Nao e escala
# de prancha: e o quanto o SVG amplia para a secao de um perfil de 90 mm caber
# legivel numa caixa de tela.
ESC_PERFIL = 1.6
ESC_PARAFUSO = 3.2


def _txt(x, y, s, cls="cota", anchor="middle", extra=""):
    return (f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" '
            f'text-anchor="{anchor}"{extra}>{s}</text>')


def _cota(x1, y1, x2, y2, rot, desloc=0, vertical=False):
    """Linha de cota com extremidades e texto, no estilo da prancha."""
    if vertical:
        x = x1 + desloc
        return (f'<path class="cota-l" d="M{x1:.1f} {y1:.1f} H{x:.1f} '
                f'M{x2:.1f} {y2:.1f} H{x:.1f} M{x:.1f} {y1:.1f} V{y2:.1f}"/>'
                + _txt(x, (y1 + y2) / 2, rot, "cota", "middle",
                       f' transform="rotate(-90 {x:.1f} {(y1 + y2) / 2:.1f})" dy="-3"'))
    y = y1 + desloc
    return (f'<path class="cota-l" d="M{x1:.1f} {y1:.1f} V{y:.1f} '
            f'M{x2:.1f} {y2:.1f} V{y:.1f} M{x1:.1f} {y:.1f} H{x2:.1f}"/>'
            + _txt((x1 + x2) / 2, y - 3, rot))


def desenho_perfil(p, esc: float = ESC_PERFIL) -> str:
    """Secao do perfil, cotada, a partir da linha media e da espessura.

    A poligonal e a MESMA que o solver integra para achar A, Ix e Wx. Desenhar
    de outra fonte seria abrir a porta para o desenho dizer 90 e o calculo usar
    92 — que e o defeito que este projeto passou quarenta revisoes eliminando.
    """
    import nucleo.perfis as pf
    pts, fech = pf.linha_media(p.forma, p.bw, p.bf, p.D, p.t, p.r)
    xs = [q[0] for q in pts]
    ys = [q[1] for q in pts]
    mx, My = min(xs), min(ys)
    W = (max(xs) - mx) * esc
    H = (max(ys) - My) * esc
    MG = 46
    def X(v): return MG + (v - mx) * esc
    def Y(v): return MG + (max(ys) - v) * esc
    d = "M" + " L".join(f"{X(a):.1f} {Y(b):.1f}" for a, b in pts)
    if fech:
        d += " Z"
    vb_w, vb_h = W + 2 * MG, H + 2 * MG
    pr = p.props()
    # a espessura vira largura de traco: e a unica forma honesta de mostrar
    # 0,95 mm numa secao de 90 — desenhar duas linhas paralelas a 0,95 daria
    # um fio indistinguivel da propria linha
    return f'''<svg class="pecadesenho" viewBox="0 0 {vb_w:.0f} {vb_h:.0f}"
      role="img" aria-label="Secao do perfil {p.cod}">
      <path class="secao" d="{d}" style="stroke-width:{max(1.4, p.t * esc):.2f}"/>
      {_cota(X(mx), Y(My) + 14, X(max(xs)), Y(My) + 14, f"{p.bf:g}", 14)}
      {_cota(X(mx) - 14, Y(max(ys)), X(mx) - 14, Y(My), f"{p.bw:g}", -14, True)}
      {_txt(vb_w / 2, 18, p.cod, "titulo")}
      {_txt(vb_w / 2, vb_h - 10, f"t = {p.t:.2f} mm · A = {pr['A']:.0f} mm² · "
            f"Ix = {pr['Ix'] / 1e4:.1f} cm⁴ · {pr['massa_m']:.2f} kg/m")}
    </svg>'''


def desenho_parafuso(b, comp_mm: float, esc: float = ESC_PARAFUSO) -> str:
    """Elevacao do parafuso: cabeca, haste, rosca e ponta.

    A rosca e desenhada como serrilha, nao como helice: numa elevacao tecnica a
    helice e ruido. O que a peca precisa comunicar e diametro nominal, diametro
    da cabeca, comprimento e TIPO DE PONTA — broca ou agulha —, que e o que
    decide se ela atravessa aco ou so gesso.
    """
    L = comp_mm * esc
    dn = b.d * esc
    dw = b.dw * esc
    MG = 34
    vb_w, vb_h = L + 2 * MG + 30, dw + 2 * MG + 14
    y0 = MG + dw / 2
    cab_l = max(3.0, 2.2 * esc)
    ponta = 2.2 * esc
    x0 = MG
    corpo = x0 + cab_l
    fim = x0 + L
    broca = b.tipo.startswith("auto-b")
    # serrilha da rosca
    passo = max(2.4, 1.2 * esc)
    n = int((fim - ponta - corpo) / passo)
    rosca = "".join(
        f"M{corpo + i * passo:.1f} {y0 - dn / 2:.1f} "
        f"L{corpo + (i + 0.5) * passo:.1f} {y0 + dn / 2:.1f} "
        for i in range(max(0, n)))
    pta = (f"M{fim - ponta:.1f} {y0 - dn / 2:.1f} L{fim:.1f} {y0:.1f} "
           f"L{fim - ponta:.1f} {y0 + dn / 2:.1f}" if broca else
           f"M{fim - ponta:.1f} {y0 - dn / 2:.1f} L{fim:.1f} {y0:.1f} "
           f"L{fim - ponta:.1f} {y0 + dn / 2:.1f} Z")
    return f'''<svg class="pecadesenho" viewBox="0 0 {vb_w:.0f} {vb_h:.0f}"
      role="img" aria-label="Elevacao do parafuso {b.cod}">
      <rect class="secao-cheia" x="{x0:.1f}" y="{y0 - dw / 2:.1f}"
            width="{cab_l:.1f}" height="{dw:.1f}"/>
      <rect class="secao" x="{corpo:.1f}" y="{y0 - dn / 2:.1f}"
            width="{fim - corpo - ponta:.1f}" height="{dn:.1f}"/>
      <path class="rosca" d="{rosca}"/>
      <path class="{'secao' if broca else 'secao-cheia'}" d="{pta}"/>
      {_cota(x0, y0 + dw / 2 + 10, fim, y0 + dw / 2 + 10, f"{comp_mm:g}", 12)}
      {_cota(x0 - 10, y0 - dw / 2, x0 - 10, y0 + dw / 2, f"⌀{b.dw:g}", -10, True)}
      {_txt(vb_w / 2, 16, b.cod, "titulo")}
      {_txt(vb_w / 2, vb_h - 8, f"⌀ rosca {b.d:g} mm · ponta "
            f"{'broca' if broca else 'agulha'} · Rv {b.rv_fab:g} kN (H)")}
    </svg>'''


def desenho_chapa(m, esp: float, larg: float, alt: float) -> str:
    """A chapa em planta, com formato comercial e espessura cotada."""
    esc = 0.09
    W, H = larg * esc, alt * esc
    MG = 40
    vb_w, vb_h = W + 2 * MG, H + 2 * MG + 10
    return f'''<svg class="pecadesenho" viewBox="0 0 {vb_w:.0f} {vb_h:.0f}"
      role="img" aria-label="Chapa {m.nome} {esp:g} mm">
      <rect class="secao" x="{MG}" y="{MG}" width="{W:.1f}" height="{H:.1f}"/>
      <rect class="secao-cheia" x="{MG}" y="{MG + H:.1f}"
            width="{W:.1f}" height="{max(1.6, esp * 0.6):.1f}"/>
      {_cota(MG, MG + H + 16, MG + W, MG + H + 16, f"{larg:g}", 14)}
      {_cota(MG - 14, MG, MG - 14, MG + H, f"{alt:g}", -14, True)}
      {_txt(vb_w / 2, 16, f"{m.nome} {esp:g} mm", "titulo")}
      {_txt(vb_w / 2, vb_h - 6, f"{m.norma} · {m.densidade:g} kg/m³ · "
            f"λ {m.lambda_t:g} W/mK")}
    </svg>'''


def desenho_tubo(dn: str, de: float, material: str, norma: str) -> str:
    """Secao do tubo: diametro EXTERNO, que e o que precisa caber no furo."""
    esc = 1.5
    R = de * esc / 2
    MG = 40
    vb = 2 * R + 2 * MG
    c = vb / 2
    par = max(2.0, de * 0.055 * esc)
    return f'''<svg class="pecadesenho" viewBox="0 0 {vb:.0f} {vb:.0f}"
      role="img" aria-label="Secao do tubo {dn}">
      <circle class="secao" cx="{c:.1f}" cy="{c:.1f}" r="{R:.1f}"
              style="stroke-width:{par:.1f}"/>
      {_cota(c - R, c + R + 16, c + R, c + R + 16, f"⌀ {de:g}", 14)}
      {_txt(c, 16, dn, "titulo")}
      {_txt(c, vb - 6, f"{material} · {norma}")}
    </svg>'''


def montar(pj, r: dict) -> dict:
    """O catalogo inteiro: desenho, ficha e ONDE CADA PECA E USADA.

    A terceira coluna e a que transforma catalogo em documento de obra. Um
    desenho sem quantidade e folheto; com quantidade e com o painel em que a
    peca entra, vira ordem de compra e conferencia de recebimento.
    """
    import nucleo.perfis as pf
    import nucleo.ligacoes as lg
    import nucleo.materiais as mt
    import nucleo.camadas as cd

    por_perfil: dict = {}
    for q in r["pecas"]:
        d = por_perfil.setdefault(q.perfil, dict(n=0, massa=0.0, familias=set()))
        d["n"] += 1
        d["massa"] += q.massa
        d["familias"].add(q.familia)
    cat = {p.cod: p for p in pf.catalogo()}
    perfis = []
    for cod, uso in sorted(por_perfil.items(), key=lambda kv: -kv[1]["massa"]):
        p = cat.get(cod)
        if p is None:
            continue
        pr = p.props()
        perfis.append(dict(
            cod=cod, forma=p.forma, bw=p.bw, bf=p.bf, D=p.D, t=p.t,
            area=round(pr["A"], 1), ix=round(pr["Ix"] / 1e4, 2),
            wx=round(pr.get("Wx", 0) / 1e3, 2), massa_m=round(pr["massa_m"], 3),
            n=uso["n"], massa=round(uso["massa"], 1),
            familias=sorted(uso["familias"]),
            norma="NBR 15253 / NBR 6355", svg=desenho_perfil(p)))

    por_par: dict = {}
    for j in r["juntas"].values():
        for x in j["juntas"]:
            por_par[x["parafuso"]] = por_par.get(x["parafuso"], 0) + x["n"]
    parafusos = []
    for cod, n in sorted(por_par.items(), key=lambda kv: -kv[1]):
        b = lg.POR_PARAFUSO.get(cod)
        if b is None:
            continue
        comp = float(cod.split("x")[1].split()[0].replace(",", "."))
        parafusos.append(dict(
            cod=cod, d=b.d, dw=b.dw, comp=comp, tipo=b.tipo,
            rv=b.rv_fab, rt=b.rt_fab, n=n, norma="NBR 14762 item 8.4",
            svg=desenho_parafuso(b, comp)))

    chapas = []
    for it in (r["camadas"].get("itens") or []):
        m = mt.POR_MATERIAL.get(it["material"])
        if m is None or not m.chapa:
            continue
        chapas.append(dict(
            cod=f"{it['material']}-{it['espessura']:g}".replace(".", ","),
            material=m.cod, nome=m.nome, espessura=it["espessura"],
            formato=list(m.chapa), norma=m.norma, area=it["area"],
            svg=desenho_chapa(m, it["espessura"], m.chapa[0], m.chapa[1])))

    tubos = []
    h = r["camadas"]["instalacoes"]["hidraulica"]
    vistos = set()
    for i in h["itens"]:
        dn = f"DN{i['dn']}"
        if dn in vistos:
            continue
        vistos.add(dn)
        de = cd.DE_ESGOTO.get(dn, float(i["dn"]))
        esgoto = "esgoto" in i["sistema"]
        tubos.append(dict(
            cod=dn, dn=i["dn"], de=de, sistema=i["sistema"],
            comp=i["comp_m"], conexoes=i["conexoes"],
            norma="NBR 5688" if esgoto else "NBR 5648",
            svg=desenho_tubo(dn, de, "PVC serie normal" if esgoto
                             else "PVC soldavel", 
                             "NBR 5688" if esgoto else "NBR 5648")))

    return dict(
        perfis=perfis, parafusos=parafusos, chapas=chapas, tubos=tubos,
        n=len(perfis) + len(parafusos) + len(chapas) + len(tubos),
        metodo="cada desenho sai das dimensoes que alimentam o calculo: a "
               "mesma poligonal de linha media que o solver da NBR 14762 "
               "integra para achar A, Ix e Wx. Nao ha estado em que o desenho "
               "e o calculo discordem, porque sao a mesma fonte",
        limite="desenho de PROJETO, nao de fabricacao: sem tolerancia de dobra, "
               "sem raio de ferramenta real, sem detalhe de cabeca de "
               "fabricante. O que nao se deduz da designacao continua (H)")
