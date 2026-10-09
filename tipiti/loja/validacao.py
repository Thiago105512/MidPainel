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
