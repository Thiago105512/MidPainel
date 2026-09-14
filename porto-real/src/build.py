#!/usr/bin/env python3
"""Pipeline: pranchas em SVG/PNG/PDF, modelo 3D e visualizador do caderno."""
from __future__ import annotations

import os
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
]


def main(png: bool = True, pdf: bool = True) -> None:
    os.makedirs(OUT, exist_ok=True)
    svgs = []
    for num, nome, fn in CADERNO:
        cv = fn()
        caminho = os.path.join(OUT, f"PR-{num}.svg")
        cv.salvar(caminho)
        svgs.append(caminho)
        print(f"  PR-{num}  {nome:<34} {os.path.getsize(caminho)//1024:>4} KB")

    if png or pdf:
        import cairosvg
        for c in svgs:
            if png:
                cairosvg.svg2png(url=c, write_to=c.replace(".svg", ".png"), output_width=2400)
            if pdf:
                cairosvg.svg2pdf(url=c, write_to=c.replace(".svg", ".pdf"))

    import modelo3d
    import engenharia
    import viewer
    modelo3d.exportar(os.path.join(OUT, "modelo3d.json"))
    engenharia.main()
    viewer.main()

    if pdf:
        import pymupdf
        doc = pymupdf.open()
        for c in svgs:
            doc.insert_pdf(pymupdf.open(c.replace(".svg", ".pdf")))
        alvo = os.path.join(OUT, "PORTO_REAL_CADERNO_ARQUITETURA.pdf")
        doc.save(alvo)
        print(f"\n  caderno unico: {alvo} ({doc.page_count} pranchas)")


if __name__ == "__main__":
    main(png="--no-png" not in sys.argv, pdf="--no-pdf" not in sys.argv)
