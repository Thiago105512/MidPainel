"""Imagens provisórias dos produtos, geradas em SVG até as fotos reais chegarem."""

import re
from html import escape


def _escurecer(cor, fator=0.62):
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", cor or ""):
        cor = "#1f5c45"
    r, g, b = (int(cor[i:i + 2], 16) for i in (1, 3, 5))
    return "#{:02x}{:02x}{:02x}".format(int(r * fator), int(g * fator), int(b * fator))


def svg_produto(nome, icone, cor):
    base = cor if re.fullmatch(r"#[0-9a-fA-F]{6}", cor or "") else "#1f5c45"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" role="img" aria-label="{escape(nome)}">
<defs>
<linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{base}"/><stop offset="1" stop-color="{_escurecer(base)}"/></linearGradient>
<pattern id="trama" width="28" height="28" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
<rect width="14" height="28" fill="#fff" fill-opacity=".06"/><rect y="0" width="28" height="14" fill="#000" fill-opacity=".05"/>
</pattern>
</defs>
<rect width="400" height="400" fill="url(#g)"/>
<rect width="400" height="400" fill="url(#trama)"/>
<circle cx="200" cy="200" r="118" fill="#fff" fill-opacity=".16"/>
<text x="200" y="208" font-size="132" text-anchor="middle" dominant-baseline="middle" font-family="'Noto Color Emoji','Apple Color Emoji','Segoe UI Emoji',sans-serif">{escape(icone or "📦")}</text>
</svg>"""
