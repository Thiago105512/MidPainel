"""Verificação de saúde da loja: sai com 0 se GET /api/loja responde 200 em até 4 s, senão com 1.

Usada pelo HEALTHCHECK do Docker, pelo CI e por quem quiser testar à mão:
    python3 deploy/saude.py                 (porta de TIPITI_PORT, padrão 8000)
    python3 deploy/saude.py http://127.0.0.1:8799/api/loja
"""

import os
import sys
import urllib.request


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else f"http://127.0.0.1:{os.environ.get('TIPITI_PORT', '8000')}/api/loja"
    # sem proxy: a pergunta é sobre este servidor, mesmo que HTTP_PROXY esteja definido no ambiente
    abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with abridor.open(url, timeout=4) as resposta:
            ok = resposta.status == 200
    except Exception as erro:  # noqa: BLE001 — qualquer falha conta como "fora do ar"
        print(f"loja fora do ar: {erro}", file=sys.stderr)
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
