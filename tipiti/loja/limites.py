"""Limites de tentativas por IP (pedidos, consultas de pedido, avaliações e token do painel)."""

import threading
import time

MSG_LIMITE = "Muitas tentativas. Aguarde alguns minutos."


class LimiteTaxa:
    """Janela deslizante em memória: no máximo `maximo` eventos por IP a cada `janela` segundos."""

    def __init__(self, maximo, janela):
        self.maximo = maximo
        self.janela = janela
        self._eventos = {}
        self._trava = threading.Lock()
        self._proxima_limpeza = time.monotonic() + janela

    def _recentes(self, ip, agora):
        eventos = [t for t in self._eventos.get(ip, ()) if agora - t < self.janela]
        if eventos:
            self._eventos[ip] = eventos
        else:
            self._eventos.pop(ip, None)
        return eventos

    def excedido(self, ip):
        with self._trava:
            return len(self._recentes(ip, time.monotonic())) >= self.maximo

    def registrar(self, ip):
        with self._trava:
            agora = time.monotonic()
            self._eventos[ip] = (self._recentes(ip, agora) + [agora])[-self.maximo:]
            if agora >= self._proxima_limpeza:  # IPs que não voltaram não ficam na memória
                for outro in list(self._eventos):
                    self._recentes(outro, agora)
                self._proxima_limpeza = agora + self.janela


def limites_padrao():
    """Limites usados pelo servidor: por IP, no máximo N eventos por janela de tempo."""
    return {
        "pedidos": LimiteTaxa(10, 3600),
        "admin": LimiteTaxa(10, 15 * 60),
        "consulta": LimiteTaxa(30, 3600),
        "avaliacoes": LimiteTaxa(20, 3600),
        "cpf_cupom": LimiteTaxa(30, 3600),
        "revendedoras": LimiteTaxa(3, 3600),       # cadastros de revendedora
        "revenda": LimiteTaxa(10, 15 * 60),         # token errado do painel da revendedora (igual ao admin)
    }
