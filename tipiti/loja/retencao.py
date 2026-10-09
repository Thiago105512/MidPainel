"""Apaga o que passou do prazo de guarda (como a expiração de pedidos não pagos, feita de passagem).

Chamado pelas rotas de conta/carrinho/painel e pela thread de fundo, no máximo uma vez a cada INTERVALO_S.
"""

import threading
import time

from . import horario
from .carrinhos import RETENCAO_DIAS as RETENCAO_CARRINHO_DIAS
from .legal import RETENCAO_AVISE_ME_DIAS

INTERVALO_S = 600
RETENCAO_EMAILS_DIAS = 180
RETENCAO_LINKS_DIAS = 1

_trava = threading.Lock()
_proxima = 0.0


def purgar(conn, forcar=False):
    """Devolve {tabela: linhas apagadas} ou None se ainda não era hora."""
    global _proxima
    with _trava:
        agora_s = time.monotonic()
        if not forcar and agora_s < _proxima:
            return None
        _proxima = agora_s + INTERVALO_S
    agora = horario.agora_db()
    return {
        "carrinhos": conn.execute("DELETE FROM carrinhos WHERE atualizado_em < ?",
                                  (horario.agora_db(days=-RETENCAO_CARRINHO_DIAS),)).rowcount,
        "links_conta": conn.execute("DELETE FROM links_conta WHERE expira_em < ?",
                                    (horario.agora_db(days=-RETENCAO_LINKS_DIAS),)).rowcount,
        "sessoes_conta": conn.execute("DELETE FROM sessoes_conta WHERE expira_em < ?", (agora,)).rowcount,
        "sessoes_admin": conn.execute("DELETE FROM sessoes_admin WHERE expira_em < ?", (agora,)).rowcount,
        "avise_me": conn.execute("DELETE FROM avise_me WHERE status = 'avisado' AND COALESCE(avisado_em, criado_em) < ?",
                                 (horario.agora_db(days=-RETENCAO_AVISE_ME_DIAS),)).rowcount,
        "emails_saida": conn.execute("DELETE FROM emails_saida WHERE criado_em < ? AND status IN ('enviado', 'falhou')",
                                     (horario.agora_db(days=-RETENCAO_EMAILS_DIAS),)).rowcount,
    }
