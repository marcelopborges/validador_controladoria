import pandas as pd
import os
from pathlib import Path

def criar_excel_exemplo():
    """
    Cria um arquivo Excel de exemplo que segue o formato esperado pelo importador.
    Garante que todos os dados são 100% válidos para as regras de validação.
    """
    # Dados de exemplo válidos
    dados = [
        {
            "FILIAL": "0101",
            "DATA": "01/01/2024",
            "N_CONTA": "12345678",
            "N_CENTRO_CUSTO": "123456789",
            "OPERACAO": "OP1234567",
            "VALOR": 1000.50,
            "DESCRICAO": "CONTA DE LUZ",
            "TIPO": "NORMAL",
            "VERSAO": "2024 - V1"
        },
        {
            "FILIAL": "0102",
            "DATA": "02/01/2024",
            "N_CONTA": "87654321",
            "N_CENTRO_CUSTO": "987654321",
            "OPERACAO": "OP7654321",
            "VALOR": 2500.75,
            "DESCRICAO": "FOLHA DE PAGAMENTO",
            "TIPO": "NORMAL",
            "VERSAO": "2024 - V1"
        },
        {
            "FILIAL": "0103",
            "DATA": "03/01/2024",
            "N_CONTA": "11223344",
            "N_CENTRO_CUSTO": "112233445",
            "OPERACAO": "",  # Campo que pode ser nulo
            "VALOR": 3750.25,
            "DESCRICAO": "ALUGUEL",
            "TIPO": "NORMAL",
            "VERSAO": "2024 - V1"
        },
        {
            "FILIAL": "0104",
            "DATA": "04/01/2024",
            "N_CONTA": "12345678",
            "N_CENTRO_CUSTO": "123456789",
            "OPERACAO": "OP1234567",
            "VALOR": 1000.50,
            "DESCRICAO": "DESPESAS GERAIS",
            "TIPO": "NORMAL",
            "VERSAO": "2024 - V1"
        },
        {
            "FILIAL": "0105",
            "DATA": "05/01/2024",
            "N_CONTA": "98765432",
            "N_CENTRO_CUSTO": "987654321",
            "OPERACAO": "OP9876543",
            "VALOR": 5000.00,
            "DESCRICAO": "FORNECEDORES",
            "TIPO": "NORMAL",
            "VERSAO": "2024 - V1"
        },
        {
            "FILIAL": "0110",
            "DATA": "10/01/2024",
            "N_CONTA": "12345678",
            "N_CENTRO_CUSTO": "123456789",
            "OPERACAO": "",
            "VALOR": 750.00,
            "DESCRICAO": "MANUTENÇÃO PREDIAL",
            "TIPO": "NORMAL",
            "VERSAO": "2024 - V1"
        },
        {
            "FILIAL": "0111",
            "DATA": "15/01/2024",
            "N_CONTA": "11111111",
            "N_CENTRO_CUSTO": "222222222",
            "OPERACAO": "OP1111111",
            "VALOR": 3200.00,
            "DESCRICAO": "COMPRA DE MATERIAL",
            "TIPO": "NORMAL",
            "VERSAO": "2024 - V1"
        },
        {
            "FILIAL": "0112",
            "DATA": "20/01/2024",
            "N_CONTA": "22222222",
            "N_CENTRO_CUSTO": "333333333",
            "OPERACAO": "OP2222222",
            "VALOR": 4800.00,
            "DESCRICAO": "SERVIÇOS TERCEIRIZADOS",
            "TIPO": "NORMAL",
            "VERSAO": "2024 - V1"
        },
        {
            "FILIAL": "0113",
            "DATA": "25/01/2024",
            "N_CONTA": "33333333",
            "N_CENTRO_CUSTO": "444444444",
            "OPERACAO": "",
            "VALOR": 1200.00,
            "DESCRICAO": "MATERIAL DE ESCRITÓRIO",
            "TIPO": "NORMAL",
            "VERSAO": "2024 - V1"
        },
        {
            "FILIAL": "0114",
            "DATA": "30/01/2024",
            "N_CONTA": "44444444",
            "N_CENTRO_CUSTO": "555555555",
            "OPERACAO": "OP4444444",
            "VALOR": 9500.00,
            "DESCRICAO": "CONSULTORIA",
            "TIPO": "NORMAL",
            "VERSAO": "2024 - V1"
        }
    ]
    
    # Cria o DataFrame
    df = pd.DataFrame(dados)
    
    # Garante que o diretório data existe
    Path("data").mkdir(exist_ok=True)
    
    # Salva como XLSX
    arquivo_xlsx = os.path.join("data", "modelo_importacao.xlsx")
    df.to_excel(arquivo_xlsx, index=False)
    print(f"Arquivo Excel de exemplo criado: {arquivo_xlsx}")
    
    # Salva como CSV também para compatibilidade
    arquivo_csv = os.path.join("data", "modelo_importacao.csv")
    df.to_csv(arquivo_csv, index=False)
    print(f"Arquivo CSV de exemplo criado: {arquivo_csv}")
    
    # Para o pacote de distribuição
    Path("dist_package/data").mkdir(parents=True, exist_ok=True)
    if os.path.exists("dist_package"):
        df.to_excel(os.path.join("dist_package", "data", "modelo_importacao.xlsx"), index=False)
        print(f"Arquivo Excel de exemplo copiado para o pacote de distribuição")
        
    return arquivo_xlsx

if __name__ == "__main__":
    criar_excel_exemplo() 