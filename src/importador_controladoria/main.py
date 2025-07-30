import os
import logging
import logging.config
from pathlib import Path
import pandas as pd
from datetime import datetime
from google.cloud import bigquery
from google.oauth2 import service_account
# import great_expectations as gx

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
    # Criar o diretório de configuração do Great Expectations se não existir
    gx_dir = CONFIG_DIR / "great_expectations"
    gx_dir.mkdir(exist_ok=True)
    
    # Obter ou criar um contexto do GX
    try:
        context = gx.get_context(
            context_root_dir=str(gx_dir)
        )
        
        # Verificar se o datasource pandas_default existe
        if 'pandas_default' not in context.list_datasources():
            # Criar um datasource pandas_default
            datasource = context.sources.add_pandas(
                name="pandas_default",
                batch_spec_passthrough={
                    "reader_method": "read_excel",
                    "reader_options": {
                        "engine": "openpyxl"
                    }
                }
            )
            logger.info("Configurado datasource pandas_default para o Great Expectations")
    except Exception as e:
        # Se falhar, usar um contexto efêmero
        logger.warning(f"Erro ao configurar contexto do Great Expectations: {str(e)}")
        logger.warning("Usando um contexto efêmero.")
        context = gx.get_context(mode="ephemeral")
        
        # Configurar datasource pandas_default no contexto efêmero
        datasource = context.sources.add_pandas(
            name="pandas_default",
            batch_spec_passthrough={
                "reader_method": "read_excel",
                "reader_options": {
                    "engine": "openpyxl"
                }
            }
        )
        logger.info("Configurado datasource pandas_default para o contexto efêmero")
    
    return context

def criar_expectations(context, df):
    """Cria as expectativas para validação dos dados."""
    # Criar um batch request para o dataframe
    batch_request = {
        "datasource_name": "pandas_default",
        "data_asset_name": "dados_validacao",
        "batch_data": df,
        "batch_identifiers": {
            "default_identifier_name": "default_identifier"
        }
    }
    
    # Criar uma suite de expectativas
    suite = context.create_expectation_suite(expectation_suite_name="orcamento_suite", overwrite_existing=True)
    
    # Obter um validator para o batch
    validator = context.get_validator(
        batch_request=batch_request,
        expectation_suite_name="orcamento_suite"
    )
    
    # Validar colunas obrigatórias
    for coluna in VALIDATION_CONFIG["required_columns"]:
        validator.expect_column_to_exist(coluna)
    
    # Validar tipos de dados
    for coluna, tipo in VALIDATION_CONFIG["column_types"].items():
        validator.expect_column_values_to_be_of_type(coluna, tipo)
    
    # Validar valores não nulos
    for coluna in VALIDATION_CONFIG["required_columns"]:
        validator.expect_column_values_to_not_be_null(coluna)
    
    # Validar regras específicas
    if "valor" in VALIDATION_CONFIG["validation_rules"]:
        validator.expect_column_values_to_be_greater_than(
            "valor", 
            VALIDATION_CONFIG["validation_rules"]["valor"]["min"]
        )
    
    if "descricao" in VALIDATION_CONFIG["validation_rules"]:
        validator.expect_column_values_to_match_regex(
            "descricao",
            VALIDATION_CONFIG["validation_rules"]["descricao"]["regex"]
        )
    
    # Salvar expectativas
    validator.save_expectation_suite(discard_failed_expectations=False)
    
    logger.info("Expectativas criadas e salvas com sucesso.")
    
    return suite

def validar_dados(context, df):
    """Valida os dados usando Great Expectations."""
    try:
        # Criar um validator para o dataframe
        batch_request = {
            "datasource_name": "pandas_default",
            "data_asset_name": "dados_validacao",
            "batch_data": df,
            "batch_identifiers": {
                "default_identifier_name": "default_identifier"
            }
        }
        
        validator = context.get_validator(
            batch_request=batch_request,
            expectation_suite_name="orcamento_suite"
        )
        
        # Executar validação
        validation_result = validator.validate()
        
        logger.info(f"Validação concluída: {validation_result.success}")
        
        if not validation_result.success:
            # Log das expectativas que falharam
            falhas = []
            for result in validation_result.results:
                if not result.success:
                    falhas.append(f"{result.expectation_config.expectation_type}: {result.exception_info.get('exception_message', 'Falha na validação')}")
            
            logger.error(f"Falhas na validação: {falhas}")
            
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
