import os
import logging
import logging.config
from pathlib import Path
import pandas as pd
from datetime import datetime
from google.cloud import bigquery
from google.oauth2 import service_account
from great_expectations.data_context import DataContext
from great_expectations.dataset import PandasDataset

from .config import (
    BASE_DIR, DATA_DIR, LOG_DIR, CONFIG_DIR,
    BIGQUERY_CREDENTIALS, BIGQUERY_CONFIG,
    VALIDATION_CONFIG, LOG_CONFIG
)

# Configurar logging
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)

def configurar_contexto_gx():
    """Configura o contexto do Great Expectations."""
    context = DataContext(
        context_root_dir=str(CONFIG_DIR / "great_expectations")
    )
    return context

def criar_expectations(context, df):
    """Cria as expectativas para validação dos dados."""
    dataset = PandasDataset(df)
    
    # Validar colunas obrigatórias
    for coluna in VALIDATION_CONFIG["required_columns"]:
        dataset.expect_column_to_exist(coluna)
    
    # Validar tipos de dados
    for coluna, tipo in VALIDATION_CONFIG["column_types"].items():
        dataset.expect_column_values_to_be_of_type(coluna, tipo)
    
    # Validar valores não nulos
    for coluna in VALIDATION_CONFIG["required_columns"]:
        dataset.expect_column_values_to_not_be_null(coluna)
    
    # Validar regras específicas
    if "valor" in VALIDATION_CONFIG["validation_rules"]:
        dataset.expect_column_values_to_be_greater_than(
            "valor", 
            VALIDATION_CONFIG["validation_rules"]["valor"]["min"]
        )
    
    if "descricao" in VALIDATION_CONFIG["validation_rules"]:
        dataset.expect_column_values_to_match_regex(
            "descricao",
            VALIDATION_CONFIG["validation_rules"]["descricao"]["regex"]
        )
    
    # Salvar expectativas
    context.save_expectation_suite(
        expectation_suite_name="orcamento_suite",
        expectations=dataset.get_expectation_suite()
    )

def validar_dados(context, df):
    """Valida os dados usando Great Expectations."""
    try:
        validation_result = context.run_validation_operator(
            "action_list_operator",
            assets_to_validate=[PandasDataset(df)],
            expectation_suite_name="orcamento_suite"
        )
        return validation_result.success
    except Exception as e:
        logger.error(f"Erro na validação dos dados: {str(e)}")
        raise

def carregar_dados_bigquery(df):
    """Carrega os dados validados no BigQuery."""
    try:
        credentials = service_account.Credentials.from_service_account_info(
            BIGQUERY_CREDENTIALS
        )
        client = bigquery.Client(
            project=BIGQUERY_CONFIG["project_id"],
            credentials=credentials
        )
        
        table_id = f"{BIGQUERY_CONFIG['dataset_id']}.{BIGQUERY_CONFIG['table_id']}"
        job_config = bigquery.LoadJobConfig(
            write_disposition="WRITE_APPEND"
        )
        
        job = client.load_table_from_dataframe(
            df, table_id, job_config=job_config
        )
        job.result()
        
        logger.info(f"Dados carregados com sucesso na tabela {table_id}")
    except Exception as e:
        logger.error(f"Erro ao carregar dados no BigQuery: {str(e)}")
        raise

def main():
    """Função principal do importador."""
    try:
        # Configurar contexto do Great Expectations
        context = configurar_contexto_gx()
        
        # Carregar dados
        arquivo = DATA_DIR / "dados.csv"
        df = pd.read_csv(arquivo)
        
        # Validar dados
        if validar_dados(context, df):
            logger.info("Validação dos dados concluída com sucesso")
            
            # Carregar dados no BigQuery
            carregar_dados_bigquery(df)
        else:
            logger.error("Falha na validação dos dados")
            raise ValueError("Dados não passaram na validação")
            
    except Exception as e:
        logger.error(f"Erro no processamento: {str(e)}")
        raise

if __name__ == "__main__":
    main()
