## Tabela de cores ANSI (Python) ##

# Fonte #
Mblack = '\033[1;30m'  # Preto
Ired = '\033[1;31m'  # Vermelho
Dgreen = '\033[1;32m'  # Verde
Nyellow = '\033[1;33m'  # Amarelo
Iblue = '\033[1;34m'  # Azul
Gpurple = '\033[1;35m'  # Roxo
Hcyan = '\033[1;36m'  # Ciano
Twhite = '\033[1;37m'  # Branco
VRCRM = '\033[0;0m'  # Remover

import os
import requests


def cls():
    os.system('cls' if os.name == 'nt' else 'clear')


def consulta_cpf(cpf_input):
    try:
        response = requests.get(f'http://ghostcenter.xyz/api/cpf/{cpf_input}', timeout=10)
        response.raise_for_status()  # Verifica se a resposta contém algum erro HTTP
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"{Ired}Erro HTTP: {http_err}{VRCRM}")
    except requests.exceptions.RequestException as req_err:
        print(f"{Ired}Erro de Requisição: {req_err}{VRCRM}")
    except ValueError:
        print(f"{Ired}Erro: Resposta inválida da API.{VRCRM}")
    return None


def validar_cpf(cpf_input):
    if len(cpf_input) != 11 or not cpf_input.isdigit():
        print(f'{Ired}!!! {Nyellow}CPF Inválido {Ired}!!!')
        return False
    return True


def exibir_resultado(rjson):
    if rjson['status'] == 404:
        print(f"{Ired}==> CPF NÃO ENCONTRADO <=={VRCRM}")
    else:
        print('\n\033[1;33m{:-^62}'.format(f' {Dgreen}==> CPF ENCONTRADO <=={Nyellow} '))
        i = rjson['dados']
        print(f'\n{Dgreen}PESSOA:{Nyellow}')
        print(f" CPF        >>> {i['cpf']}")
        print(f" Nome       >>> {i['nome']}")
        print(f" Nascimento >>> {i['nascimento']}")
        print(f" Sexo       >>> {i['sexo']}\n")
        print(f'\033[1;33m-' * 48)


def consultar():
    cls()
    print('')
    print(f'\n{Iblue}########## #################### ##########')
    print('########## ### Consulta CPF ### ##########')
    print('########## #################### ##########')
    restart = 'S'
    while restart == 'S':
        while True:
            cpf_input = str(input(f'\n{Hcyan}Digite o CPF para consulta: '
