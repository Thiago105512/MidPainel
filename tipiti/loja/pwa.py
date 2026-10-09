"""App instalável (PWA): manifesto e service worker.

O service worker é o modelo `modelos/sw.js` com as URLs versionadas do app.js e do estilo.css preenchidas pelo
servidor; é entregue em /sw.js (raiz, para controlar o site todo).
"""

import hashlib
import json
import re
from pathlib import Path

from . import config

MODELO_SW = Path(__file__).resolve().parent / "modelos" / "sw.js"
TEMA = "#1f5c45"
FUNDO = "#f6f5f0"
ICONES = {
    "192": "/static/pwa/icone-192.png",
    "512": "/static/pwa/icone-512.png",
    "512_maskable": "/static/pwa/icone-512-maskable.png",
}
IMAGEM_COMPARTILHAR = "/static/pwa/compartilhar.png"


def manifesto():
    return {
        "id": "/",
        "name": config.NOME_LOJA,
        "short_name": config.NOME_LOJA,
        "description": "Importados com entrega rápida no Norte: Manaus, Parintins, Boa Vista, Santarém e região.",
        "start_url": "/?origem=app",
        "scope": "/",
        "display": "standalone",
        "theme_color": TEMA,
        "background_color": FUNDO,
        "lang": "pt-BR",
        "dir": "ltr",
        "categories": ["shopping"],
        "icons": [
            {"src": ICONES["192"], "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": ICONES["512"], "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": ICONES["512_maskable"], "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }


def service_worker(app_js, estilo_css):
    """Texto do /sw.js com as URLs informadas (ex.: "/static/js/app.js?v=abc123")."""
    modelo = MODELO_SW.read_text(encoding="utf-8")
    versao = hashlib.sha256("\n".join((modelo, app_js, estilo_css)).encode()).hexdigest()[:12]
    valores = {"VERSAO": versao, "APP_JS": app_js, "ESTILO_CSS": estilo_css}
    # json.dumps gera literais de string JS válidos; "</" não importa aqui (não é HTML), mas fica escapado mesmo assim
    return re.sub(r"\b__(VERSAO|APP_JS|ESTILO_CSS)__\b",
                  lambda m: json.dumps(valores[m.group(1)]).replace("<", "\\u003c"), modelo)
