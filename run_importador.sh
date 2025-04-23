#!/bin/bash
# Instala dependências usando uv
echo "Instalando dependências com uv..."
uv pip install -r requirements.txt

# Executa o importador
echo "Executando o importador..."
python interface_grafica.py
