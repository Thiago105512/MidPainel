## Tabela de cores ANSI (Python) ##

# Fonte #
Mblack = '\033[1;30m'   # Preto
Ired = '\033[1;31m'     # Vermelho
Dgreen = '\033[1;32m'   # Verde
Nyellow = '\033[1;33m'  # Amarelo
Iblue = '\033[1;34m'    # Azul
Gpurple = '\033[1;35m'  # Roxo
Hcyan = '\033[1;36m'    # Ciano
Twhite = '\033[1;37m'   # Branco
VRCRM = '\033[0;0m'     # Remover

import os

def cls():
    os.system('cls' if os.name == 'nt' else 'clear')

# Exemplo de uso da tabela de cores e da função cls:
if __name__ == "__main__":
    cls()  # Limpa a tela
    print(f"{Iblue}Este é um exemplo de banner em azul{VRCRM}")
    print(f"{Ired}Este é um exemplo de banner em vermelho{VRCRM}")
    print(f"{Dgreen}Este é um exemplo de banner em verde{VRCRM}")
