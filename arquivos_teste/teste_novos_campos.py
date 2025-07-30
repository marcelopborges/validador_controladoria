#!/usr/bin/env python3
"""
Script para criar arquivos de teste Excel com os novos campos RATEIO e ORIGEM
"""

import pandas as pd
import os
from datetime import datetime, timedelta

def criar_pasta_teste():
    """Cria a pasta de arquivos de teste se não existir"""
    if not os.path.exists('arquivos_teste'):
        os.makedirs('arquivos_teste')

def criar_arquivo_teste_completo():
    """Cria um arquivo de teste com todos os campos incluindo RATEIO e ORIGEM"""
    
    # Dados de teste com os novos campos
    dados = {
        'FILIAL': ['0101', '0102', '0103', '0101', '0102'],
        'N_CONTA': ['12345678', '87654321', '11111111', '22222222', '33333333'],
        'N_CENTRO_CUSTO': ['101100101', '102100201', '103100301', '101100102', '102100202'],
        'DESCRICAO': ['Material de Escritório', 'Serviços de TI', 'Manutenção Predial', 'Combustível', 'Energia Elétrica'],
        'VALOR': [1500.50, 2800.75, 950.00, 1200.30, 3500.00],
        'DATA': ['01/01/2025', '15/01/2025', '30/01/2025', '05/02/2025', '20/02/2025'],
        'VERSAO': ['2025 - V1', '2025 - V1', '2025 - V1', '2025 - V1', '2025 - V1'],
        'OPERACAO': ['INSERT', 'UPDATE', '', 'INSERT', 'DELETE'],
        'RATEIO': ['SIM', 'NÃO', 'SIM', '', 'NAO'],
        'ORIGEM': ['SISTEMA FINANCEIRO', 'PLANILHA MANUAL', 'IMPORTACAO AUTOMATICA', 'SISTEMA ERP', '']
    }
    
    df = pd.DataFrame(dados)
    
    # Salva o arquivo
    arquivo = 'arquivos_teste/teste_completo_novos_campos.xlsx'
    df.to_excel(arquivo, index=False)
    print(f"✓ Arquivo criado: {arquivo}")
    return arquivo

def criar_arquivo_teste_validacao_rateio():
    """Cria arquivo para testar validações do campo RATEIO"""
    
    dados = {
        'FILIAL': ['0101', '0102', '0103', '0104', '0105'],
        'N_CONTA': ['12345678', '87654321', '11111111', '22222222', '33333333'],
        'N_CENTRO_CUSTO': ['101100101', '102100201', '103100301', '101100102', '102100202'],
        'DESCRICAO': ['Teste Rateio Válido 1', 'Teste Rateio Válido 2', 'Teste Rateio Inválido', 'Teste Rateio Vazio', 'Teste Rateio Minúsculo'],
        'VALOR': [100.00, 200.00, 300.00, 400.00, 500.00],
        'DATA': ['01/01/2025', '02/01/2025', '03/01/2025', '04/01/2025', '05/01/2025'],
        'VERSAO': ['2025 - V1', '2025 - V1', '2025 - V1', '2025 - V1', '2025 - V1'],
        'OPERACAO': ['', '', '', '', ''],
        'RATEIO': ['SIM', 'NÃO', 'TALVEZ', '', 'sim'],  # TALVEZ deve dar erro
        'ORIGEM': ['TESTE', 'TESTE', 'TESTE', 'TESTE', 'TESTE']
    }
    
    df = pd.DataFrame(dados)
    arquivo = 'arquivos_teste/teste_validacao_rateio.xlsx'
    df.to_excel(arquivo, index=False)
    print(f"✓ Arquivo criado: {arquivo}")
    return arquivo

def criar_arquivo_teste_validacao_origem():
    """Cria arquivo para testar validações do campo ORIGEM"""
    
    dados = {
        'FILIAL': ['0101', '0102', '0103'],
        'N_CONTA': ['12345678', '87654321', '11111111'],
        'N_CENTRO_CUSTO': ['101100101', '102100201', '103100301'],
        'DESCRICAO': ['Teste Origem Válida', 'Teste Origem Muito Longa', 'Teste Origem com Acentos'],
        'VALOR': [100.00, 200.00, 300.00],
        'DATA': ['01/01/2025', '02/01/2025', '03/01/2025'],
        'VERSAO': ['2025 - V1', '2025 - V1', '2025 - V1'],
        'OPERACAO': ['', '', ''],
        'RATEIO': ['SIM', 'NÃO', 'SIM'],
        'ORIGEM': [
            'SISTEMA FINANCEIRO',  # Válida
            'ESTA É UMA ORIGEM MUITO LONGA QUE EXCEDE OS 60 CARACTERES PERMITIDOS PELO SISTEMA',  # Deve dar erro
            'Sístema Fínanceíro com Açéntos'  # Deve ser normalizada
        ]
    }
    
    df = pd.DataFrame(dados)
    arquivo = 'arquivos_teste/teste_validacao_origem.xlsx'
    df.to_excel(arquivo, index=False)
    print(f"✓ Arquivo criado: {arquivo}")
    return arquivo

def criar_arquivo_sem_novos_campos():
    """Cria arquivo sem os novos campos para testar compatibilidade"""
    
    dados = {
        'FILIAL': ['0101', '0102'],
        'N_CONTA': ['12345678', '87654321'],
        'N_CENTRO_CUSTO': ['101100101', '102100201'],
        'DESCRICAO': ['Teste Compatibilidade 1', 'Teste Compatibilidade 2'],
        'VALOR': [100.00, 200.00],
        'DATA': ['01/01/2025', '02/01/2025'],
        'VERSAO': ['2025 - V1', '2025 - V1'],
        'OPERACAO': ['INSERT', 'UPDATE']
        # Sem RATEIO e ORIGEM
    }
    
    df = pd.DataFrame(dados)
    arquivo = 'arquivos_teste/teste_compatibilidade_antigo.xlsx'
    df.to_excel(arquivo, index=False)
    print(f"✓ Arquivo criado: {arquivo}")
    return arquivo

def main():
    """Função principal para criar todos os arquivos de teste"""
    print("Criando arquivos de teste para validar os novos campos RATEIO e ORIGEM...")
    
    criar_pasta_teste()
    
    arquivos_criados = []
    arquivos_criados.append(criar_arquivo_teste_completo())
    arquivos_criados.append(criar_arquivo_teste_validacao_rateio())
    arquivos_criados.append(criar_arquivo_teste_validacao_origem())
    arquivos_criados.append(criar_arquivo_sem_novos_campos())
    
    print(f"\n✅ Total de {len(arquivos_criados)} arquivos de teste criados:")
    for arquivo in arquivos_criados:
        print(f"   - {arquivo}")
    
    print("\n📋 Próximos passos para testar:")
    print("1. Execute o sistema: python -m src.importador_controladoria.main")
    print("2. Teste cada arquivo na interface web")
    print("3. Verifique as validações e funcionalidades")

if __name__ == "__main__":
    main()