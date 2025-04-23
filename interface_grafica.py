"""
Interface gráfica do Importador Controladoria.
Este é o arquivo principal que será compilado para o executável.
"""

import os
import sys
from pathlib import Path

# Adiciona o diretório src ao PYTHONPATH
sys.path.append(str(Path(__file__).parent))

# Importa a aplicação Flask
from src.importador_controladoria.interface import app

def main():
    """Função principal que inicia a aplicação."""
    # Cria diretórios necessários
    for dir_path in ["data", "data/processados", "data/rejeitados", "logs"]:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    # Inicia o servidor Flask
    app.run(debug=False, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    main() 