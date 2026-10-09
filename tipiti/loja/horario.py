"""Datas e horários: o banco guarda UTC ('AAAA-MM-DD HH:MM:SS'); a API fala ISO com Z; a loja vive em Manaus.

Manaus (America/Manaus) fica em UTC−4 o ano inteiro, sem horário de verão: um fuso fixo basta e dispensa
a base de fusos do sistema.
"""

from datetime import datetime, timedelta, timezone

FUSO_LOJA = timezone(timedelta(hours=-4), "America/Manaus")
_FORMATO_DB = "%Y-%m-%d %H:%M:%S"


def agora():
    """Momento atual em UTC (função própria para os testes poderem fixar o relógio)."""
    return datetime.now(timezone.utc)


def texto_db(momento):
    return momento.astimezone(timezone.utc).strftime(_FORMATO_DB)


def de_db(texto):
    return datetime.strptime(texto, _FORMATO_DB).replace(tzinfo=timezone.utc)


def iso_z(texto):
    """'2026-10-09 15:00:00' (UTC, do banco) -> '2026-10-09T15:00:00Z'; vazio -> None."""
    return f"{texto.replace(' ', 'T')}Z" if texto else None


def ler_data(valor):
    """Aceita '2026-10-09T15:00:00Z', com fuso (+00:00, -04:00) ou '2026-10-09 15:00:00' (UTC).

    Devolve o texto no formato do banco, em UTC. ValueError se não for uma data.
    """
    if not isinstance(valor, str) or not 10 <= len(valor.strip()) <= 40:
        raise ValueError("data inválida")
    texto = valor.strip()
    if texto[-1:] in ("Z", "z"):
        texto = texto[:-1] + "+00:00"
    momento = datetime.fromisoformat(texto)
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return texto_db(momento.replace(microsecond=0))
