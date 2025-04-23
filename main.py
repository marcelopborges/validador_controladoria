import os
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
from dotenv import load_dotenv

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/importador_{datetime.now().strftime("%Y-%m-%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente
load_dotenv()

# Configurações do BigQuery
PROJECT_ID = os.getenv('BIGQUERY_PROJECT_ID')
DATASET_ID = os.getenv('BIGQUERY_DATASET_ID')
TABLE_ID = os.getenv('BIGQUERY_TABLE_ID')

def setup_directories() -> None:
    """Cria os diretórios necessários se não existirem."""
    Path("data").mkdir(exist_ok=True)
    Path("logs").mkdir(exist_ok=True)

def get_csv_files() -> List[str]:
    """Retorna lista de arquivos CSV no diretório data."""
    return list(Path("data").glob("*.csv"))

def validate_data(df: pd.DataFrame) -> bool:
    """Valida os dados usando pandas."""
    try:
        # Verifica valores nulos
        if df["DATA"].isnull().any():
            logger.error("Existem valores nulos na coluna DATA")
            return False
            
        # Verifica formato da data
        data_pattern = r"^\d{2}/\d{2}/\d{4}$"
        if not df["DATA"].str.match(data_pattern).all():
            logger.error("Formato de data inválido. Use o formato dd/mm/yyyy")
            return False
            
        # Verifica valores permitidos para TIPO
        tipos_validos = ["ENTRADA", "SAÍDA"]
        if not df["TIPO"].isin(tipos_validos).all():
            logger.error(f"Valores inválidos na coluna TIPO. Valores permitidos: {tipos_validos}")
            return False
            
        # Verifica valores permitidos para VERSÃO
        versoes_validas = ["1.0", "2.0"]
        if not df["VERSÃO"].isin(versoes_validas).all():
            logger.error(f"Valores inválidos na coluna VERSÃO. Valores permitidos: {versoes_validas}")
            return False
            
        # Verifica se VALOR é numérico
        if not pd.to_numeric(df["VALOR"], errors="coerce").notnull().all():
            logger.error("Valores inválidos na coluna VALOR. Use apenas números")
            return False
            
        logger.info("Validação concluída com sucesso!")
        return True
            
    except Exception as e:
        logger.error(f"Erro na validação dos dados: {str(e)}")
        return False

def load_to_bigquery(df: pd.DataFrame) -> bool:
    """Carrega os dados validados para o BigQuery."""
    try:
        # Converte a coluna DATA para o formato do BigQuery
        df["DATA"] = pd.to_datetime(df["DATA"], format="%d/%m/%Y").dt.strftime("%Y-%m-%d")
        
        client = bigquery.Client()
        table_ref = client.dataset(DATASET_ID).table(TABLE_ID)
        
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=[
                bigquery.SchemaField("DATA", "DATE"),
                bigquery.SchemaField("TIPO", "STRING"),
                bigquery.SchemaField("VERSÃO", "STRING"),
                bigquery.SchemaField("VALOR", "FLOAT")
            ]
        )
        
        job = client.load_table_from_dataframe(
            df, table_ref, job_config=job_config
        )
        job.result()
        
        logger.info(f"Dados carregados com sucesso para {DATASET_ID}.{TABLE_ID}")
        return True
        
    except GoogleCloudError as e:
        logger.error(f"Erro ao carregar dados para o BigQuery: {str(e)}")
        return False

def main() -> None:
    """Função principal do importador."""
    try:
        setup_directories()
        csv_files = get_csv_files()
        
        if not csv_files:
            logger.warning("Nenhum arquivo CSV encontrado no diretório data/")
            return
            
        for csv_file in csv_files:
            logger.info(f"Processando arquivo: {csv_file}")
            
            # Lê o arquivo CSV
            df = pd.read_csv(csv_file)
            
            # Valida os dados
            if not validate_data(df):
                logger.error(f"Validação falhou para o arquivo {csv_file}")
                continue
                
            # Carrega para o BigQuery
            if load_to_bigquery(df):
                logger.info(f"Arquivo {csv_file} processado com sucesso")
            else:
                logger.error(f"Falha ao processar o arquivo {csv_file}")
                
    except Exception as e:
        logger.error(f"Erro inesperado: {str(e)}")

if __name__ == "__main__":
    main() 