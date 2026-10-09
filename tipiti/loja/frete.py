"""Tabela de frete por faixa de CEP, priorizando a Região Norte.

A expedição é considerada a partir de Manaus. Cada zona é uma faixa dos 5 primeiros dígitos do CEP;
a primeira faixa que casar vence, então as cidades vêm antes do "interior" do mesmo estado.
Valores e prazos são de referência e devem ser ajustados com a transportadora/Correios.
"""

from . import config

# (cep5_inicio, cep5_fim, id, nome, valor_centavos, prazo_dias)
ZONAS = [
    (69000, 69099, "manaus", "Manaus (AM)", 990, 2),
    (69150, 69159, "parintins", "Parintins (AM)", 1990, 5),
    (69300, 69339, "boa-vista", "Boa Vista (RR)", 1990, 4),
    (68000, 68109, "santarem", "Santarém (PA)", 1990, 5),
    (68900, 68914, "macapa", "Macapá (AP)", 2490, 6),
    (66000, 66999, "belem", "Belém (PA)", 2490, 6),
    (69900, 69923, "rio-branco", "Rio Branco (AC)", 2490, 6),
    (76800, 76834, "porto-velho", "Porto Velho (RO)", 2490, 6),
    (77000, 77270, "palmas", "Palmas (TO)", 2990, 7),
    (69100, 69299, "interior-am", "Interior do Amazonas", 2990, 10),
    (69400, 69899, "interior-am", "Interior do Amazonas", 2990, 10),
    (69300, 69399, "interior-rr", "Interior de Roraima", 2990, 8),
    (66000, 68899, "interior-pa", "Interior do Pará", 2990, 9),
    (68900, 68999, "interior-ap", "Interior do Amapá", 2990, 9),
    (69900, 69999, "interior-ac", "Interior do Acre", 3490, 10),
    (76800, 76999, "interior-ro", "Interior de Rondônia", 3490, 9),
    (77000, 77999, "interior-to", "Interior do Tocantins", 3490, 9),
]

ZONA_FORA_DO_NORTE = ("demais-regioes", "Demais regiões do Brasil", 3990, 12)

# Cidades em destaque na vitrine ("entregamos em...")
CIDADES_DESTAQUE = ["Manaus", "Parintins", "Boa Vista", "Santarém", "Macapá", "Belém", "Rio Branco", "Porto Velho"]


def zona_do_cep(cep_digitos):
    """Recebe 8 dígitos e devolve (id, nome, valor, prazo, regiao_norte)."""
    prefixo = int(cep_digitos[:5])
    for inicio, fim, zid, nome, valor, prazo in ZONAS:
        if inicio <= prefixo <= fim:
            return zid, nome, valor, prazo, True
    return (*ZONA_FORA_DO_NORTE, False)


def cotar(cep_digitos, subtotal_centavos):
    zid, nome, valor, prazo, norte = zona_do_cep(cep_digitos)
    gratis = norte and subtotal_centavos >= config.FRETE_GRATIS_A_PARTIR
    return {
        "cep": f"{cep_digitos[:5]}-{cep_digitos[5:]}",
        "zona": zid,
        "zona_nome": nome,
        "regiao_norte": norte,
        "valor_centavos": 0 if gratis else valor,
        "gratis": gratis,
        "prazo_dias": prazo + config.PRAZO_MANUSEIO_DIAS,
    }
