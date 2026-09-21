#!/usr/bin/env python3
"""Pipeline: pranchas em SVG/PNG/PDF, modelo 3D e visualizador do caderno."""
from __future__ import annotations

import os
import json
import sys

import pranchas as pr
import pranchas2 as p2
import pranchas3 as p3
import desempenho as dp
import especificacao as ep
import pranchas4 as p4
import pranchas5 as p5
import pranchas6 as p6
import pranchas7 as p7
import pranchas8 as p8
import pranchas9 as p9
import pranchas10 as p10
import pranchas11 as p11
import pranchas12 as p12

OUT = os.path.join(os.path.dirname(__file__), "..", "out")

CADERNO = [
    ("01", "IMPLANTACAO E SITUACAO",            lambda: pr.implantacao()),
    ("02", "PLANTA BAIXA — TERREO",             lambda: pr.planta("T", "02")),
    ("03", "PLANTA BAIXA — SUPERIOR",           lambda: pr.planta("S", "03")),
    ("04", "PLANTA DE LAYOUT — TERREO",         lambda: pr.planta("T", "04", layout=True)),
    ("05", "PLANTA DE COBERTURA",               lambda: pr.cobertura()),
    ("06", "CORTES AA E BB",                    lambda: p2.cortes()),
    ("07", "FACHADAS",                          lambda: p2.fachadas()),
    ("08", "CROQUI AXONOMETRICO",               lambda: p2.axonometria()),
    ("09", "QUADROS GERAIS E PENDENCIAS",       lambda: p3.quadros()),
    ("10", "DETALHES CONSTRUTIVOS",             lambda: p3.detalhes()),
    ("11", "DESEMPENHO TERMICO E ACUSTICO",     lambda: dp.prancha()),
    ("12", "MAPA DE FAMILIAS DE VEDACAO",       lambda: ep.prancha_mapa()),
    ("13", "ESPECIFICACAO POR EXIGENCIA",       lambda: ep.prancha_especificacao()),
    ("14", "AUDITORIA DO MODELO",              lambda: p4.auditoria()),
    ("15", "ELEVACOES INTERNAS",               lambda: p4.elevacoes_internas()),
    ("16", "PLANTA DE FORRO E ILUMINACAO",     lambda: p4.forro()),
    ("17", "ACESSIBILIDADE E FLUXOS",          lambda: p4.acessibilidade()),
    ("18", "PAGINACAO DE PAINEIS LSF",         lambda: p4.paginacao_lsf()),
    ("19", "ESTUDO DE INSOLACAO",              lambda: p4.insolacao()),
    # ---- Etapa 2: detalhamento construtivo
    ("20", "INTERFACE LSF x LAMINADO",         lambda: p5.interface_estrutural()),
    ("21", "FURACAO E PENETRACOES",            lambda: p5.furacao()),
    ("22", "AMPLIACOES MOLHADAS — TERREO",     lambda: p5.ampliacoes("T", "22")),
    ("23", "AMPLIACOES MOLHADAS — SUPERIOR",   lambda: p5.ampliacoes("S", "23")),
    ("24", "PAGINACAO DE PISO",                lambda: p5.paginacao_piso()),
    ("25", "ESCADA EXECUTIVA",                 lambda: p5.escada()),
    # ---- Etapa 3: coordenacao de instalacoes
    ("26", "INSTALACOES HIDROSSANITARIAS",     lambda: p6.hidrossanitaria()),
    ("27", "ELETRICA, ILUMINACAO E DADOS",     lambda: p6.eletrica()),
    ("28", "CLIMATIZACAO — LINHAS E DUTOS",    lambda: p6.climatizacao()),
    ("29", "DRENAGEM PLUVIAL E DE PISO",       lambda: p6.drenagem()),
    # ---- Etapa 4: fechamento e emissao
    ("30", "ACABAMENTOS POR AMBIENTE",          lambda: p7.acabamentos()),
    ("31", "LOCACAO DE OBRA E GABARITO",        lambda: p7.locacao()),
    ("32", "PAISAGISMO E IRRIGACAO",            lambda: p7.paisagismo()),
    ("33", "EMISSAO: INDICE E PENDENCIAS",      lambda: p7.emissao()),
    # ---- R06: revisao do programa pelo YAML do proprietario
    ("34", "PISCINA, DECK E FACHADA",           lambda: p7.piscina_deck_fachada()),
    ("35", "EIXO SOCIAL E CORTINA DE VIDRO",    lambda: p7.eixo_social()),
    ("36", "CATALOGO TECNICO DE PECAS",         lambda: p7.catalogo_tecnico()),
    ("37", "SONDAGEM SPT E FUNDACAO",           lambda: p8.sondagem()),
    ("38", "RETENCAO PLUVIAL E SUPERFICIES",    lambda: p8.retencao_pluvial()),
    ("39", "DESEMPENHO ACUSTICO",               lambda: p8.acustica()),
    ("40", "CARGAS, FASES E MERCADO",           lambda: p8.cargas_e_mercado()),
    ("41", "ENERGIA: FOTOVOLTAICA, SPDA E VIDRO", lambda: p8.energia()),
    # R65 — a meta-auditoria achou LY-10 a LY-15 em nenhuma prancha: o layout
    # do superior existia no modelo e nao existia no caderno.
    ("42", "PLANTA DE LAYOUT — SUPERIOR",       lambda: pr.planta("S", "42", layout=True)),
    # R66 — a casa vista de fora em oito azimutes e cada comodo de dentro
    ("43", "PERSPECTIVAS EXTERNAS",             lambda: p8.perspectivas("externa")),
    ("44", "PERSPECTIVAS INTERNAS — TERREO",    lambda: p8.perspectivas("terreo")),
    ("45", "PERSPECTIVAS — AREAS ABERTAS",      lambda: p8.perspectivas("abertas")),
    ("46", "PERSPECTIVAS INTERNAS — SUPERIOR",  lambda: p8.perspectivas("superior")),
    # R68 — a declividade confirmada do lote vira plataforma, cota e rampa
    ("47", "TERRENO: PERFIL, PLATAFORMA E COTAS", lambda: p8.terreno()),
    # R69 — a lista de 621 entregaveis medida, e dois estudos que ela pedia
    ("48", "MATRIZ DE ENTREGAVEIS — PRANCHA MESTRE", lambda: p8.entregaveis()),
    ("49", "VENTILACAO NATURAL E PRIVACIDADE",   lambda: p8.ventilacao()),
    # R70 — lote 1 do backlog da matriz
    ("50", "CORTES POR AMBIENTE E DE FACHADA",   lambda: p9.cortes_por_ambiente()),
    ("51", "ELEVACOES INTERNAS II",              lambda: p9.elevacoes_derivadas()),
    ("52", "ESQUADRIAS: TIPOS E DETALHES",       lambda: p9.esquadrias()),
    ("53", "MAPA DE CORES, RODAPES E PEITORIS",  lambda: p9.mapa_de_cores()),
    ("54", "PLANTA HUMANIZADA",                  lambda: p9.humanizada()),
    ("55", "PLANTA DE MARCENARIA",                lambda: p10.planta_marcenaria()),
    ("56", "MARCENARIA I: GABINETES",              lambda: p10.detalhamento_1()),
    ("57", "MARCENARIA II: DORMITORIOS",           lambda: p10.detalhamento_2()),
    ("58", "MARCENARIA: CORTE E FURACAO",          lambda: p10.plano_de_corte()),
    ("59", "MARCENARIA: FERRAGENS E PECAS",        lambda: p10.ferragens_e_pecas()),
    ("60", "ELETRICA: UNIFILAR E QUADROS",        lambda: p11.unifilar()),
    ("61", "ELETRICA: MATERIAL E FOTOVOLTAICA",    lambda: p11.material_eletrico()),
    ("62", "ESGOTO E VENTILACAO: ISOMETRICO",      lambda: p11.esgoto()),
    ("63", "AGUA FRIA: ISOMETRICO E PRESSOES",     lambda: p11.agua_fria()),
    ("64", "PLUVIAL, GAS, AR NOVO E SUPORTES",     lambda: p11.complementares()),
    ("65", "DADOS, CFTV, ALARME E AUTOMACAO",     lambda: p12.seguranca_eletronica()),
    ("66", "PREVENCAO CONTRA INCENDIO",           lambda: p12.incendio()),
]


def main(png: bool = True, pdf: bool = True, so: set | None = None, persp: bool = True) -> None:
    """Gera o caderno inteiro, ou so as pranchas em `so` (R61: --so 16,41).

    Gerar as 41 pranchas leva minutos; corrigir UMA prancha exigia as 41.
    Com --so, o SVG/PNG/PDF das outras fica como esta e o caderno unico e o
    visualizador sao remontados a partir do que ha em out/.
    """
    os.makedirs(OUT, exist_ok=True)
    # R66 — o visualizador nao depende das pranchas (le PR-xx.svg em tempo de
    # execucao), e as perspectivas dependem do visualizador: cena e viewer
    # saem primeiro, as fotos depois, e so entao as pranchas 43 a 46 as embutem.
    import modelo3d
    import viewer
    modelo3d.exportar(os.path.join(OUT, "modelo3d.json"))
    modelo3d.exportar_obj(os.path.join(OUT, "porto-real.obj"))
    viewer.main()
    if persp and (not so or so & {"43", "44", "45", "46"}):
        try:
            import perspectivas
            m = perspectivas.renderizar()
            print(f"  perspectivas: {len(m['vistas'])} vistas renderizadas")
        except Exception as e:
            print(f"  perspectivas NAO renderizadas: {e}")
    svgs = []
    ocup_path = os.path.join(OUT, "ocupacao.json")
    ocup = json.load(open(ocup_path)) if os.path.exists(ocup_path) else {}
    for num, nome, fn in CADERNO:
        caminho = os.path.join(OUT, f"PR-{num}.svg")
        if so and num not in so:
            if os.path.exists(caminho):
                svgs.append(caminho)
            continue
        cv = fn()
        cv.salvar(caminho)
        svgs.append(caminho)
        # R62 — quanto da folha o desenho ocupa. A folha de contato mostrou
        # pranchas usando 20 % da A1; um olho ve, a auditoria passa a medir.
        try:
            x0, y0, x1, y1 = cv.caixa_desenho()
            util = (cv.larg - cv.marg - 25) * (cv.alt - 2 * cv.marg)
            ocup[num] = round(max(0.0, (x1 - x0) * (y1 - y0)) / util, 3)
        except Exception:
            pass
        print(f"  PR-{num}  {nome:<34} {os.path.getsize(caminho)//1024:>4} KB"
              f"  ocupa {ocup.get(num, 0) * 100:3.0f} %")
    json.dump(ocup, open(ocup_path, "w"), indent=1)

    if png or pdf:
        import cairosvg
        for c in svgs:
            if so and c.split("PR-")[-1][:2] not in so:
                continue
            if png:
                cairosvg.svg2png(url=c, write_to=c.replace(".svg", ".png"), output_width=2400)
            if pdf:
                cairosvg.svg2pdf(url=c, write_to=c.replace(".svg", ".pdf"))

    import engenharia
    engenharia.main()

    # a planilha de cotacao sai do mesmo modelo que o caderno: quantidade que
    # muda na planta muda na planilha na proxima geracao, sem ninguem digitar
    try:
        import planilha_cotacao          # noqa: F401
    except ImportError as e:
        print(f"  planilha de cotacao NAO gerada: {e} (pip install openpyxl)")

    if pdf:
        import pymupdf
        doc = pymupdf.open()
        for c in svgs:
            doc.insert_pdf(pymupdf.open(c.replace(".svg", ".pdf")))
        alvo = os.path.join(OUT, "PORTO_REAL_CADERNO_ARQUITETURA.pdf")
        doc.save(alvo)
        print(f"\n  caderno unico: {alvo} ({doc.page_count} pranchas)")


if __name__ == "__main__":
    _so = None
    for _a in sys.argv[1:]:
        if _a.startswith("--so="):
            _so = {x.strip().zfill(2) for x in _a[5:].split(",") if x.strip()}
    main(png="--no-png" not in sys.argv, pdf="--no-pdf" not in sys.argv, so=_so,
         persp="--no-persp" not in sys.argv)
