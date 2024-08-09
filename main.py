# main.py

# Se necessário, adicione o diretório raiz ao sys.path
import sys
import os

# Adiciona o diretório raiz ao sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importação do módulo principal
from database.api.api_script import main

# Chame a função principal
if __name__ == "__main__":
    main()
