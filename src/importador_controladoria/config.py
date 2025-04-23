"""
Configurações do importador de dados.
"""

import os
from pathlib import Path
import json

# Diretórios base
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
CONFIG_DIR = BASE_DIR / "config"

# Criar diretórios se não existirem
for dir_path in [DATA_DIR, LOG_DIR, CONFIG_DIR]:
    dir_path.mkdir(exist_ok=True)

# Configuração do BigQuery
BIGQUERY_CONFIG = {
    "project_id": os.getenv("BIGQUERY_PROJECT_ID", "seu-projeto-id"),
    "dataset_id": os.getenv("BIGQUERY_DATASET_ID", "seu-dataset-id"),
    "table_id": os.getenv("BIGQUERY_TABLE_ID", "sua-tabela-id"),
    "metadata_table_id": os.getenv("BIGQUERY_METADATA_TABLE_ID", "sua-tabela-metadata-id")
}

# Tenta carregar credenciais do arquivo ou usa variáveis de ambiente
try:
    credentials_path = CONFIG_DIR / "bigquery-credentials.json"
    if credentials_path.exists():
        with open(credentials_path) as f:
            BIGQUERY_CREDENTIALS = json.load(f)
    else:
        # Usa variáveis de ambiente
        BIGQUERY_CREDENTIALS = {
            "type": "service_account",
            "project_id": os.getenv("BIGQUERY_PROJECT_ID"),
            "private_key_id": os.getenv("BIGQUERY_PRIVATE_KEY_ID"),
            "private_key": os.getenv("BIGQUERY_PRIVATE_KEY", "").replace("\\n", "\n"),
            "client_email": os.getenv("BIGQUERY_CLIENT_EMAIL"),
            "client_id": os.getenv("BIGQUERY_CLIENT_ID"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.getenv("BIGQUERY_CLIENT_X509_CERT_URL")
        }
except Exception as e:
    print(f"Erro ao carregar credenciais: {e}")
    BIGQUERY_CREDENTIALS = None

# Configurações de validação
VALIDATION_CONFIG = {
    "required_columns": ["codigo", "descricao", "valor", "data"],
    "column_types": {
        "codigo": "int64",
        "descricao": "str",
        "valor": "float64",
        "data": "datetime64[ns]"
    },
    "validation_rules": {
        "valor": {"min": 0},
        "descricao": {"regex": r"^[A-Za-z0-9\s\-\.]+$"}
    }
}

# Configurações de logging
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        }
    },
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "level": "INFO",
            "formatter": "standard",
            "filename": LOG_DIR / "importador.log",
            "mode": "a"
        },
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard"
        }
    },
    "root": {
        "handlers": ["file", "console"],
        "level": "INFO"
    }
} 