"""Erros de validação e verificações de dados do cliente (CPF, e-mail, CEP, UF)."""

import re


class ErroValidacao(Exception):
    def __init__(self, campos, mensagem="Verifique os dados informados."):
        super().__init__(mensagem)
        self.campos = campos
        self.mensagem = mensagem


class NaoEncontrado(Exception):
    pass


UFS = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA",
    "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}


def so_digitos(valor):
    return re.sub(r"\D", "", str(valor or ""))


def cpf_valido(cpf):
    d = so_digitos(cpf)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        if (soma * 10) % 11 % 10 != int(d[n]):
            return False
    return True


def email_valido(email):
    return bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email or "")) and len(email) <= 254


def cep_digitos(cep):
    d = so_digitos(cep)
    if len(d) != 8:
        raise ErroValidacao({"cep": "Informe um CEP com 8 dígitos."})
    return d


def cnpj_valido(cnpj):
    d = so_digitos(cnpj)
    if len(d) != 14 or d == d[0] * 14:
        return False
    for n in (12, 13):
        pesos = list(range(n - 7, 1, -1)) + list(range(9, 1, -1))
        soma = sum(int(d[i]) * pesos[i] for i in range(n))
        resto = soma % 11
        if (0 if resto < 2 else 11 - resto) != int(d[n]):
            return False
    return True


def sem_quebras(texto, maximo=200):
    """Texto de uma linha só (sem CR/LF nem outros controles), aparado e cortado — seguro para cabeçalhos."""
    limpo = re.sub(r"[\x00-\x1f\x7f]+", " ", str(texto or "")).strip()
    return limpo[:maximo]
