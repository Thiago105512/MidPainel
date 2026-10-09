"""Configuração da loja. Tudo pode ser sobrescrito por variáveis de ambiente."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

NOME_LOJA = "Tipiti"
SITE_URL = os.environ.get("TIPITI_SITE_URL", "https://tipiti.com.br").rstrip("/")
EMAIL_CONTATO = os.environ.get("TIPITI_EMAIL", "contato@tipiti.com.br")

DB_PATH = Path(os.environ.get("TIPITI_DB", BASE_DIR / "data" / "tipiti.db"))
HOST = os.environ.get("TIPITI_HOST", "127.0.0.1")
PORT = int(os.environ.get("TIPITI_PORT", "8000"))

# Token do painel administrativo (mínimo de 24 caracteres). Se vazio, um token aleatório é gerado ao subir
# o servidor — só quando ele escuta apenas no próprio computador.
ADMIN_TOKEN = os.environ.get("TIPITI_ADMIN_TOKEN", "")
ADMIN_TOKEN_MINIMO = 24

# Atrás de um proxy reverso (nginx, Caddy…), o IP do cliente vem no último valor de X-Forwarded-For.
CONFIAR_PROXY = os.environ.get("TIPITI_TRUST_PROXY", "") == "1"

# Regras comerciais (valores em centavos)
FRETE_GRATIS_A_PARTIR = 19900
DESCONTO_PIX_PCT = 5
PARCELAS_MAX = 6
PARCELA_MINIMA = 3000
QTD_MAX_POR_ITEM = 10
PRAZO_MANUSEIO_DIAS = 1
ESTOQUE_BAIXO = 3
FOTOS_POR_PRODUTO = 8
# Pedido não pago em até tantas horas é cancelado e devolve as unidades ao estoque.
PRAZO_RESERVA_HORAS = 24

# WhatsApp da loja (só dígitos, com 55 + DDD). Também pode ser definido no painel, em Configurações.
WHATSAPP = os.environ.get("TIPITI_WHATSAPP", "")
