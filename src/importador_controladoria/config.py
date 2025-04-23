"""
Configurações do importador de dados.
"""

import os
from pathlib import Path

# Configurações de diretórios
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "logs"
CONFIG_DIR = BASE_DIR / "config"

# Criar diretórios se não existirem
for dir_path in [DATA_DIR, LOG_DIR, CONFIG_DIR]:
    dir_path.mkdir(exist_ok=True)

# Configurações do BigQuery
BIGQUERY_CONFIG = {
    "project_id": "gcp-sian-proj-controladoria",
    "dataset_id": "silver",
    "table_id": "orcado",
    "metadata_table_id": "orcado-metadata"
}

# Configurações de credenciais
BIGQUERY_CREDENTIALS = {
    "type": "service_account",
    "project_id": BIGQUERY_CONFIG["project_id"],
    "private_key_id": os.getenv("BIGQUERY_PRIVATE_KEY_ID"),
    "private_key": os.getenv("BIGQUERY_PRIVATE_KEY"),
    "client_email": os.getenv("BIGQUERY_CLIENT_EMAIL"),
    "client_id": os.getenv("BIGQUERY_CLIENT_ID"),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.getenv("BIGQUERY_CLIENT_CERT_URL")
}

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