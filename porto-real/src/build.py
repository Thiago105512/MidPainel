#!/usr/bin/env python3
"""Pipeline: gera todas as pranchas em SVG, PNG e um PDF unico do caderno."""
from __future__ import annotations

import os
import sys

import pranchas as pr
import pranchas2 as p2
import pranchas3 as p3

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
