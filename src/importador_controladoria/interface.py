import sys
import os
import platform
import getpass
from datetime import datetime
import pandas as pd
import threading
from google.cloud import bigquery
from google.oauth2 import service_account
from google.cloud import storage
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from werkzeug.utils import secure_filename
import tempfile
import uuid
import json
import logging
import time
import xml.etree.ElementTree as ET
import xml.dom.minidom
from pathlib import Path
import markdown
import webbrowser
from threading import Timer
from io import BytesIO
import logging.config
from .config import LOG_CONFIG

from .transformacoes import transformar_dados, validar_data
from .config import BIGQUERY_CONFIG, GCP_STORAGE_CONFIG

# Aplica a configuração de logging
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)

# Configuração do Flask
app = Flask(__name__, 
    template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.secret_key = str(uuid.uuid4())
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Diretório para salvar os arquivos processados (usando caminho absoluto)
def get_data_path():
    """
    Obtém o caminho para a pasta data, funcionando tanto em desenvolvimento quanto em produção.
    """
    try:
        # Verifica se está rodando como executável
        if getattr(sys, 'frozen', False):
            # Se estiver rodando como executável, a pasta data está no mesmo diretório do executável
            return os.path.join(os.path.dirname(sys.executable), "data")
        else:
            # Se estiver em desenvolvimento, volta 3 níveis para encontrar a pasta data
            return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
    except Exception as e:
        logger.error(f"Erro ao determinar caminho da pasta data: {str(e)}")
        # Fallback para o caminho de desenvolvimento
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))

def get_config_path():
    """
    Obtém o caminho para a pasta config, funcionando tanto em desenvolvimento quanto em produção.
    """
    try:
        # Verifica se está rodando como executável
        if getattr(sys, 'frozen', False):
            # Se estiver rodando como executável, a pasta config está no mesmo diretório do executável
            return os.path.join(os.path.dirname(sys.executable), "config")
        else:
            # Se estiver em desenvolvimento, volta 3 níveis para encontrar a pasta config
            return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config"))
    except Exception as e:
        logger.error(f"Erro ao determinar caminho da pasta config: {str(e)}")
        # Fallback para o caminho de desenvolvimento
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config"))

PROCESSED_DIR = Path(get_data_path()) / "processados"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
CREDENTIALS_DIR = Path(get_config_path())

# Caminho para o arquivo de credenciais do BigQuery
BIGQUERY_CREDENTIALS_PATH = CREDENTIALS_DIR / "bigquery-credentials.json"

# Dicionário para armazenar os status dos processamentos
processamentos = {}

class ProcessamentoThread(threading.Thread):
    def __init__(self, arquivo_path, processamento_id):
        super().__init__()
        self.arquivo_path = arquivo_path
        self.processamento_id = processamento_id
        self.status = {
            "concluido": False,
            "sucesso": False,
            "mensagem": "",
            "erros": [],
            "progresso": 0,
            "arquivo": arquivo_path,
            "start_time": datetime.now().strftime('%H:%M:%S'),
            "end_time": "",
            "processing_time": "",
            "current_step": "load",
            "steps": {
                "load": {"completed": False, "error": False, "message": "Carregando dados..."},
                "validation": {"completed": False, "error": False, "message": "Aguardando validação..."},
                "upload": {"completed": False, "error": False, "message": "Aguardando upload..."},
                "metadata": {"completed": False, "error": False, "message": "Aguardando metadados..."}
            }
        }
        processamentos[processamento_id] = self.status
        
    def atualizar_etapa(self, etapa, completed=False, error=False, message=None):
        """Atualiza o status de uma etapa específica."""
        if etapa in self.status["steps"]:
            # Mantém a mensagem atual se não for fornecida uma nova
            if message is None:
                message = self.status["steps"][etapa]["message"]
            
            self.status["steps"][etapa]["completed"] = completed
            self.status["steps"][etapa]["error"] = error
            self.status["steps"][etapa]["message"] = message
            self.status["current_step"] = etapa
            logger.info(f"Etapa {etapa} atualizada: completed={completed}, error={error}, message={message}")
    
    def run(self):
        """Executa o processamento do arquivo."""
        try:
            # Etapa 1: Carregamento dos dados (0-30%)
            self.atualizar_etapa("load", message="Carregando dados do Excel...")
            self.atualizar_progresso(10, "Carregando dados do Excel...")
            logger.info(f"Carregando arquivo: {self.arquivo_path}")
            df = pd.read_excel(self.arquivo_path)
            logger.info(f"Dados carregados com sucesso. Shape: {df.shape}")
            
            # Converte todas as colunas para maiúsculo
            df.columns = [col.upper() for col in df.columns]
            logger.info(f"Colunas convertidas para maiúsculo: {df.columns.tolist()}")
            
            self.atualizar_etapa("load", completed=True, message="Dados carregados com sucesso")
            self.atualizar_progresso(30, "Dados carregados e colunas convertidas para maiúsculo")
            
            # Etapa 2: Transformação e Validação (30-60%)
            self.atualizar_etapa("validation", message="Aplicando transformações...")
            self.atualizar_progresso(40, "Aplicando transformações...")
            logger.info("Iniciando transformação dos dados...")
            df_transformado, erros = transformar_dados(df)
            
            if erros:
                logger.error(f"Erros encontrados durante a transformação: {erros}")
                self.status['erros'] = erros
                self.atualizar_etapa("validation", error=True, message="Erros encontrados na validação")
                self.finalizar(False, "Foram encontrados erros de validação nos dados", erros)
                return
            
            self.atualizar_etapa("validation", completed=True, message="Transformações e validações concluídas")
            self.atualizar_progresso(60, "Transformações e validações concluídas")
            
            # Etapa 3: Exportação para BigQuery (60-90%)
            self.atualizar_etapa("upload", message="Exportando para BigQuery...")
            self.atualizar_progresso(70, "Exportando para BigQuery...")
            logger.info("Iniciando exportação para BigQuery...")
            
            # Tenta exportar para o BigQuery
            exportou_bigquery = self.exportar_para_bigquery(df_transformado)
            
            if exportou_bigquery:
                self.atualizar_etapa("upload", completed=True, message="Dados exportados com sucesso para o BigQuery")
                self.atualizar_progresso(90, "Dados exportados com sucesso para o BigQuery")
            else:
                self.atualizar_etapa("upload", error=True, message="Erro ao exportar para o BigQuery")
                self.atualizar_progresso(90, "Erro ao exportar para o BigQuery")
            
            # Etapa 4: Salvamento dos arquivos processados (90-100%)
            self.atualizar_etapa("metadata", message="Salvando arquivos processados...")
            logger.info("Salvando arquivos processados...")
            
            # Define o prefixo para arquivos processados
            nome_base = os.path.splitext(os.path.basename(self.arquivo_path))[0]
            prefixo = f"processado_{nome_base}"
            
            # Salva os dados processados em CSV
            arquivo_csv = PROCESSED_DIR / f"{prefixo}.csv"
            df_transformado.to_csv(arquivo_csv, index=False)
            logger.info(f"Dados processados salvos em CSV: {arquivo_csv}")
            
            # Salva os dados processados em XML
            arquivo_xml = PROCESSED_DIR / f"{prefixo}.xml"
            self.exportar_para_xml(df_transformado, arquivo_xml)
            logger.info(f"Dados processados salvos em XML: {arquivo_xml}")
            
            # Atualiza o status final
            self.atualizar_etapa("metadata", completed=True, message="Metadados gerados com sucesso")
            self.atualizar_progresso(100, "Processamento concluído com sucesso")
            
            # Mensagem final
            if exportou_bigquery:
                self.finalizar(True, f"Processo concluído com sucesso! Arquivos salvos em {PROCESSED_DIR} e enviados para o BigQuery", [])
            else:
                # Verifica o motivo específico do problema
                motivo_bigquery = "Arquivo de credenciais não encontrado"
                if credentials_path.exists():
                    motivo_bigquery = "Erro na configuração das credenciais"
                    # Adiciona informações sobre o caminho para debug
                    motivo_bigquery += f" (Caminho: {credentials_path})"
                
                mensagem_final = f"Processo concluído com sucesso! Arquivos salvos em {PROCESSED_DIR} (BigQuery: {motivo_bigquery})"
                self.finalizar(True, mensagem_final, [])
            
        except Exception as e:
            logger.error(f"Erro no processamento: {str(e)}")
            self.finalizar(False, f"Erro: {str(e)}", [str(e)])
    
    def atualizar_progresso(self, valor, mensagem):
        self.status["progresso"] = valor
        self.status["mensagem"] = mensagem
        
        # Atualiza o estado das etapas baseado no progresso
        if valor <= 30:
            self.atualizar_etapa("load", message=mensagem)
        elif valor <= 60:
            self.atualizar_etapa("load", completed=True, message="Dados carregados com sucesso")
            self.atualizar_etapa("validation", message=mensagem)
        elif valor <= 90:
            self.atualizar_etapa("load", completed=True, message="Dados carregados com sucesso")
            self.atualizar_etapa("validation", completed=True, message="Validação concluída")
            self.atualizar_etapa("upload", message=mensagem)
        else:
            self.atualizar_etapa("load", completed=True, message="Dados carregados com sucesso")
            self.atualizar_etapa("validation", completed=True, message="Validação concluída")
            self.atualizar_etapa("upload", completed=True, message="Upload concluído")
            self.atualizar_etapa("metadata", message=mensagem)
        
        logger.info(f"Progresso: {valor}% - {mensagem}")
    
    def finalizar(self, sucesso, mensagem, erros):
        self.status["concluido"] = True
        self.status["sucesso"] = sucesso
        self.status["mensagem"] = mensagem
        self.status["erros"] = erros
        self.status["progresso"] = 100 if sucesso else self.status["progresso"]
        self.status["end_time"] = datetime.now().strftime('%H:%M:%S')
        
        # Calcula o tempo de processamento
        start = datetime.strptime(self.status["start_time"], '%H:%M:%S')
        end = datetime.strptime(self.status["end_time"], '%H:%M:%S')
        duration = end - start
        self.status["processing_time"] = str(duration)
        
        # Garante que todas as etapas estejam marcadas como concluídas
        for etapa in self.status["steps"]:
            if not self.status["steps"][etapa]["error"]:
                self.status["steps"][etapa]["completed"] = True
        
        logger.info(f"Processamento finalizado - Sucesso: {sucesso} - Mensagem: {mensagem}")
    
    def exportar_para_bigquery(self, df):
        """Exporta os dados para o BigQuery."""
        try:
            # Logs específicos para debug do contexto
            logger.info("=== INÍCIO EXPORTAÇÃO BIGQUERY ===")
            logger.info(f"Thread atual: {threading.current_thread().name}")
            logger.info(f"Thread ID: {threading.current_thread().ident}")
            logger.info(f"Executável congelado: {getattr(sys, 'frozen', False)}")
            logger.info(f"Executável: {sys.executable}")
            logger.info(f"Diretório atual: {os.getcwd()}")
            
            # Detecta o caminho dinamicamente (em vez de usar a variável global)
            config_path = get_config_path()
            credentials_path = Path(config_path) / "bigquery-credentials.json"
            
            logger.info(f"get_config_path(): {config_path}")
            logger.info(f"CREDENTIALS_DIR: {Path(config_path)}")
            logger.info(f"BIGQUERY_CREDENTIALS_PATH (dinâmico): {credentials_path}")
            
            # Verifica se o arquivo de credenciais existe
            if not credentials_path.exists():
                logger.warning(f"Arquivo de credenciais do BigQuery não encontrado em: {credentials_path}")
                self.atualizar_etapa("upload", completed=True, message="BigQuery: Arquivo de credenciais não encontrado")
                return True
                
            # Limpa os dados para remover valores nulos ou problemáticos
            # Substitui None por string vazia em todas as colunas de texto
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].fillna('')
            
            # Substitui None por 0 em colunas numéricas
            for col in df.select_dtypes(include=['number']).columns:
                df[col] = df[col].fillna(0)
                
            # Garante que as colunas opcionais estão preenchidas
            if 'OPERACAO' in df.columns:
                df['OPERACAO'] = df['OPERACAO'].astype(str)
            if 'RATEIO' in df.columns:
                df['RATEIO'] = df['RATEIO'].astype(str)
            if 'ORIGEM' in df.columns:
                df['ORIGEM'] = df['ORIGEM'].astype(str)
                
            logger.info(f"Dados limpos para BigQuery. Shape: {df.shape}")
            logger.info(f"Colunas do DataFrame: {df.columns.tolist()}")
            
            # Mapeia as colunas do DataFrame para o schema do BigQuery
            df_bigquery = pd.DataFrame({
                'N_CONTA': df['N_CONTA'].astype(str) if 'N_CONTA' in df.columns else df['N CONTA'].astype(str),
                'N_CENTRO_CUSTO': df['N_CENTRO_CUSTO'].astype(str) if 'N_CENTRO_CUSTO' in df.columns else df['N CENTRO CUSTO'].astype(str),
                'DESCRICAO': df['DESCRICAO'].astype(str) if 'DESCRICAO' in df.columns else df['descricao'].astype(str),
                'VALOR': df['VALOR'].astype(float) if 'VALOR' in df.columns else df['valor'].astype(float),
                'DATA': pd.to_datetime(df['DATA']).dt.date if 'DATA' in df.columns else pd.to_datetime(df['data']).dt.date,
                'VERSAO': df['VERSAO'].astype(str) if 'VERSAO' in df.columns else df['versao'].astype(str),
                'OPERACAO': df['OPERACAO'].astype(str) if 'OPERACAO' in df.columns else '',
                'DATA_ATUALIZACAO': pd.Timestamp.now(),
                'FILIAL': df['FILIAL'].astype(str) if 'FILIAL' in df.columns else '',
                'RATEIO': df['RATEIO'].astype(str) if 'RATEIO' in df.columns else '',
                'ORIGEM': df['ORIGEM'].astype(str) if 'ORIGEM' in df.columns else ''
            })
            
            # Verifica se todos os centros de custo têm 9 dígitos
            centros_custo_invalidos = df_bigquery[~df_bigquery['N_CENTRO_CUSTO'].str.len().isin([9])]
            if not centros_custo_invalidos.empty:
                logger.error(f"Centros de custo com formato inválido: {centros_custo_invalidos['N_CENTRO_CUSTO'].tolist()}")
                self.atualizar_etapa("upload", error=True, message="BigQuery: Centros de custo com formato inválido")
                return False
            
            logger.info(f"Dados mapeados para BigQuery. Shape: {df_bigquery.shape}")
            logger.info(f"Colunas do DataFrame original: {df.columns.tolist()}")
            logger.info(f"Colunas do DataFrame BigQuery: {df_bigquery.columns.tolist()}")
            
            # Verifica se todas as colunas necessárias estão presentes
            colunas_necessarias = ['N_CONTA', 'N_CENTRO_CUSTO', 'DESCRICAO', 'VALOR', 'DATA', 'VERSAO', 'OPERACAO', 'DATA_ATUALIZACAO', 'FILIAL', 'RATEIO', 'ORIGEM']
            colunas_faltantes = [col for col in colunas_necessarias if col not in df_bigquery.columns]
            if colunas_faltantes:
                logger.error(f"Colunas faltando no DataFrame BigQuery: {colunas_faltantes}")
                self.atualizar_etapa("upload", error=True, message="BigQuery: Estrutura de dados incompleta")
                return False
            
            # Verifica se há dados no DataFrame
            if df_bigquery.empty:
                logger.error("DataFrame BigQuery está vazio")
                self.atualizar_etapa("upload", error=True, message="BigQuery: Nenhum dado para exportar")
                return False
                
            # Verifica se há valores nulos
            for col in df_bigquery.columns:
                nulos = df_bigquery[col].isnull().sum()
                if nulos > 0:
                    logger.error(f"Coluna {col} tem {nulos} valores nulos")
                    self.atualizar_etapa("upload", error=True, message="BigQuery: Dados com valores nulos")
                    return False
            
            # Cria as credenciais a partir do arquivo JSON
            try:
                logger.info(f"Tentando carregar credenciais de: {credentials_path}")
                logger.info(f"Arquivo existe: {credentials_path.exists()}")
                logger.info(f"Caminho absoluto: {credentials_path.absolute()}")
                logger.info(f"Executável congelado: {getattr(sys, 'frozen', False)}")
                logger.info(f"Executável: {sys.executable}")
                logger.info(f"get_config_path(): {config_path}")
                logger.info(f"CREDENTIALS_DIR: {Path(config_path)}")
                
                # Usa a mesma abordagem simples da rota /registros
                credentials = service_account.Credentials.from_service_account_file(
                    str(credentials_path),
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                logger.info("Credenciais do BigQuery carregadas com sucesso")
                
            except Exception as e:
                logger.error(f"Erro ao carregar credenciais do BigQuery: {str(e)}")
                logger.error(f"Tipo do erro: {type(e).__name__}")
                import traceback
                logger.error(f"Stack trace completo: {traceback.format_exc()}")
                
                # Mensagem mais detalhada para a interface web
                erro_detalhado = f"BigQuery: Erro na configuração das credenciais - {type(e).__name__}: {str(e)}"
                self.atualizar_etapa("upload", error=True, message=erro_detalhado)
                return False
            
            # Inicializa o cliente do BigQuery
            try:
                client = bigquery.Client(
                    project=BIGQUERY_CONFIG.get("project_id", "projeto-teste"),
                    credentials=credentials
                )
                logger.info(f"Cliente BigQuery inicializado com projeto: {BIGQUERY_CONFIG.get('project_id')}")
            except Exception as e:
                logger.error(f"Erro ao inicializar cliente BigQuery: {str(e)}")
                self.atualizar_etapa("upload", error=True, message="BigQuery: Erro ao conectar com o serviço")
                return False
            
            # Define o ID do dataset e tabela
            dataset_id = BIGQUERY_CONFIG.get("dataset_id", "silver")
            table_id = BIGQUERY_CONFIG.get("table_id", "ORCADO")
            metadata_table_id = BIGQUERY_CONFIG.get("metadata_table_id", "ORCADO_METADATA")
            
            # Define o schema da tabela
            schema = [
                bigquery.SchemaField("N_CONTA", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("N_CENTRO_CUSTO", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("DESCRICAO", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("VALOR", "FLOAT64", mode="REQUIRED"),
                bigquery.SchemaField("DATA", "DATE", mode="REQUIRED"),
                bigquery.SchemaField("VERSAO", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("OPERACAO", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("DATA_ATUALIZACAO", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("FILIAL", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("RATEIO", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("ORIGEM", "STRING", mode="NULLABLE")
            ]
            
            # Obtém a versão dos dados que estão sendo importados
            versao_importacao = df_bigquery['VERSAO'].iloc[0]
            logger.info(f"Importando dados da versão: {versao_importacao}")
            
            # Verifica se é uma importação completa ou parcial
            try:
                # Conta quantos registros existem na versão atual
                count_query = f"""
                SELECT COUNT(*) as total
                FROM `{dataset_id}.{table_id}`
                WHERE VERSAO = '{versao_importacao}'
                """
                count_job = client.query(count_query)
                count_result = count_job.result()
                registros_existentes = next(count_result).total
                
                # Se não existem registros, é uma importação completa
                is_importacao_completa = registros_existentes == 0
                logger.info(f"Registros existentes na versão {versao_importacao}: {registros_existentes}")
                logger.info(f"É importação completa? {is_importacao_completa}")
            except Exception as e:
                # Se der erro ao contar (tabela não existe), considera como importação completa
                is_importacao_completa = True
                logger.info(f"Erro ao verificar registros existentes: {str(e)}. Considerando como importação completa.")
            
            # Cria uma tabela temporária para os novos dados
            temp_table_id = f"temp_{table_id}_{int(time.time())}"
            temp_table_ref = client.dataset(dataset_id).table(temp_table_id)
            
            try:
                # Configura o job para a tabela temporária
                job_config = bigquery.LoadJobConfig(
                    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                    schema=schema
                )
                
                logger.info(f"Iniciando carregamento dos dados na tabela temporária {temp_table_id}")
                # Carrega os dados na tabela temporária
                job = client.load_table_from_dataframe(
                    df_bigquery, temp_table_ref, job_config=job_config
                )
                job.result()  # Aguarda a conclusão do job
                logger.info("Dados carregados com sucesso na tabela temporária")
                
                # Verifica se a tabela principal existe, se não, cria ela
                try:
                    table_ref = client.dataset(dataset_id).table(table_id)
                    table = client.get_table(table_ref)
                    logger.info(f"Tabela {table_id} já existe")
                    
                    # Verificar se as colunas RATEIO e ORIGEM existem
                    existing_fields = [field.name for field in table.schema]
                    missing_fields = []
                    
                    if 'RATEIO' not in existing_fields:
                        missing_fields.append(bigquery.SchemaField("RATEIO", "STRING", mode="NULLABLE"))
                        logger.info("Coluna RATEIO não encontrada, será adicionada")
                    if 'ORIGEM' not in existing_fields:
                        missing_fields.append(bigquery.SchemaField("ORIGEM", "STRING", mode="NULLABLE"))
                        logger.info("Coluna ORIGEM não encontrada, será adicionada")
                    
                    if missing_fields:
                        logger.info(f"Adicionando colunas faltantes: {[f.name for f in missing_fields]}")
                        new_schema = table.schema + missing_fields
                        table.schema = new_schema
                        table = client.update_table(table, ["schema"])
                        logger.info("Schema da tabela atualizado com sucesso")
                        
                except Exception as e:
                    logger.info(f"Criando tabela {table_id} com o schema definido")
                    table_ref = client.dataset(dataset_id).table(table_id)
                    table = bigquery.Table(table_ref, schema=schema)
                    client.create_table(table)
                    logger.info(f"Tabela {table_id} criada com sucesso")
                
                # Se for importação completa, deleta os registros existentes da versão
                if is_importacao_completa:
                    delete_query = f"""
                    DELETE FROM `{dataset_id}.{table_id}`
                    WHERE VERSAO = '{versao_importacao}'
                    """
                    logger.info(f"Executando DELETE para importação completa da versão {versao_importacao}")
                    delete_job = client.query(delete_query)
                    delete_job.result()
                
                # Cria uma query para atualizar apenas os registros que existem na tabela temporária
                merge_query = f"""
                MERGE `{dataset_id}.{table_id}` T
                USING `{dataset_id}.{temp_table_id}` S
                ON T.N_CONTA = S.N_CONTA 
                   AND T.N_CENTRO_CUSTO = S.N_CENTRO_CUSTO 
                   AND T.DATA = S.DATA 
                   AND T.VERSAO = S.VERSAO
                WHEN MATCHED THEN
                    UPDATE SET
                        T.DESCRICAO = S.DESCRICAO,
                        T.VALOR = S.VALOR,
                        T.OPERACAO = S.OPERACAO,
                        T.DATA_ATUALIZACAO = CURRENT_TIMESTAMP(),
                        T.FILIAL = S.FILIAL,
                        T.RATEIO = S.RATEIO,
                        T.ORIGEM = S.ORIGEM
                WHEN NOT MATCHED THEN
                    INSERT (N_CONTA, N_CENTRO_CUSTO, DESCRICAO, VALOR, DATA, VERSAO, OPERACAO, DATA_ATUALIZACAO, FILIAL, RATEIO, ORIGEM)
                    VALUES (S.N_CONTA, S.N_CENTRO_CUSTO, S.DESCRICAO, S.VALOR, S.DATA, S.VERSAO, S.OPERACAO, CURRENT_TIMESTAMP(), S.FILIAL, S.RATEIO, S.ORIGEM)
                """
                
                logger.info(f"Executando MERGE para {'importação completa' if is_importacao_completa else 'atualização parcial'}")
                logger.info(f"Query MERGE: {merge_query}")
                merge_job = client.query(merge_query)
                merge_job.result()
                
                # Registra nos metadados
                metadata = {
                    "DATA_IMPORTACAO": pd.Timestamp.now(),
                    "USUARIO": str(getpass.getuser()),
                    "SISTEMA_OPERACIONAL": str(platform.system()),
                    "VERSAO_SISTEMA": str(platform.version()),
                    "ARQUIVO_ORIGEM": f"{'IMPORTACAO_COMPLETA' if is_importacao_completa else 'ATUALIZACAO_PARCIAL'}: {os.path.basename(self.arquivo_path)}",
                    "TOTAL_REGISTROS": int(len(df_bigquery)),
                    "STATUS": "IMPORTACAO_COMPLETA" if is_importacao_completa else "ATUALIZACAO_PARCIAL",
                    "DETALHES": f"{'Importação completa' if is_importacao_completa else 'Atualização parcial'} de {len(df_bigquery)} registros da versão {versao_importacao}"
                }
                
                logger.info(f"Registrando metadados: {metadata}")
                
                # Cria o DataFrame com tipos explícitos
                df_metadata = pd.DataFrame({
                    "DATA_IMPORTACAO": [metadata["DATA_IMPORTACAO"]],
                    "USUARIO": [metadata["USUARIO"]],
                    "SISTEMA_OPERACIONAL": [metadata["SISTEMA_OPERACIONAL"]],
                    "VERSAO_SISTEMA": [metadata["VERSAO_SISTEMA"]],
                    "ARQUIVO_ORIGEM": [metadata["ARQUIVO_ORIGEM"]],
                    "TOTAL_REGISTROS": [metadata["TOTAL_REGISTROS"]],
                    "STATUS": [metadata["STATUS"]],
                    "DETALHES": [metadata["DETALHES"]]
                })
                
                # Define o schema da tabela de metadados
                metadata_schema = [
                    bigquery.SchemaField("DATA_IMPORTACAO", "TIMESTAMP", mode="REQUIRED"),
                    bigquery.SchemaField("USUARIO", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("SISTEMA_OPERACIONAL", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("VERSAO_SISTEMA", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("ARQUIVO_ORIGEM", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("TOTAL_REGISTROS", "INTEGER", mode="REQUIRED"),
                    bigquery.SchemaField("STATUS", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("DETALHES", "STRING", mode="REQUIRED")
                ]
                
                # Configura o job para os metadados
                metadata_job_config = bigquery.LoadJobConfig(
                    write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
                    schema=metadata_schema
                )
                
                # Carrega os metadados
                metadata_table_ref = client.dataset(dataset_id).table(metadata_table_id)
                logger.info(f"Iniciando inserção dos metadados na tabela {metadata_table_id}")
                metadata_job = client.load_table_from_dataframe(
                    df_metadata, metadata_table_ref, job_config=metadata_job_config
                )
                metadata_job.result()
                logger.info("Metadados inseridos com sucesso")
                
            except Exception as e:
                logger.error(f"Erro detalhado durante a exportação para BigQuery: {str(e)}")
                logger.error(f"Tipo do erro: {type(e).__name__}")
                import traceback
                logger.error(f"Stack trace: {traceback.format_exc()}")
                self.atualizar_etapa("upload", error=True, message="BigQuery: Erro durante a exportação dos dados")
                return False
                
            finally:
                # Garante que a tabela temporária seja removida mesmo em caso de erro
                try:
                    client.delete_table(temp_table_ref)
                    logger.info(f"Tabela temporária {temp_table_id} removida com sucesso")
                except Exception as e:
                    logger.error(f"Erro ao remover tabela temporária {temp_table_id}: {str(e)}")
            
            self.atualizar_etapa("upload", completed=True, message="Dados exportados com sucesso para o BigQuery")
            logger.info("Processo de exportação concluído com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao exportar para BigQuery: {str(e)}")
            self.atualizar_etapa("upload", error=True, message="BigQuery: Erro geral na exportação")
            return False

    def exportar_para_xml(self, df, arquivo_xml):
        """Exporta os dados para um arquivo XML formatado."""
        try:
            # Cria a raiz do XML
            root = ET.Element("DadosProcessados")
            
            # Adiciona informações de metadados
            metadata = ET.SubElement(root, "Metadados")
            ET.SubElement(metadata, "DataProcessamento").text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ET.SubElement(metadata, "ArquivoOrigem").text = os.path.basename(self.arquivo_path)
            ET.SubElement(metadata, "TotalRegistros").text = str(len(df))
            
            # Adiciona os registros
            registros = ET.SubElement(root, "Registros")
            
            # Converte cada linha do DataFrame em um elemento XML
            for _, row in df.iterrows():
                registro = ET.SubElement(registros, "Registro")
                
                # Adiciona cada coluna como um elemento
                for coluna, valor in row.items():
                    # Converte valor para string
                    if pd.isna(valor):
                        valor_str = ""
                    elif isinstance(valor, (int, float)):
                        valor_str = str(valor)
                    else:
                        valor_str = str(valor)
                    
                    # Adiciona o elemento
                    ET.SubElement(registro, coluna).text = valor_str
            
            # Converte para string e formata para melhor legibilidade
            xml_str = ET.tostring(root, encoding='utf-8')
            dom = xml.dom.minidom.parseString(xml_str)
            xml_formatado = dom.toprettyxml(indent="  ")
            
            # Salva no arquivo
            with open(arquivo_xml, 'w', encoding='utf-8') as f:
                f.write(xml_formatado)
                
            logger.info(f"XML criado com sucesso: {arquivo_xml}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao criar XML: {str(e)}")
            return False

def get_resource_path(relative_path):
    """
    Obtém o caminho absoluto para um recurso, funcionando tanto em desenvolvimento quanto em produção (PyInstaller).
    """
    try:
        # PyInstaller cria um diretório temporário e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Se não estiver em um executável, usa o diretório do projeto
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    return os.path.join(base_path, relative_path)

def parse_data_flexivel(data_str):
    """
    Faz o parse de uma string de data em múltiplos formatos.
    
    Args:
        data_str (str): String contendo a data
        
    Returns:
        datetime.date: Objeto date com a data parseada
        
    Raises:
        ValueError: Se nenhum formato for reconhecido
    """
    if not data_str:
        raise ValueError("String de data não pode ser vazia")
    
    formatos_data = ['%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y']
    
    for formato in formatos_data:
        try:
            return datetime.strptime(data_str, formato).date()
        except ValueError:
            continue
    
    raise ValueError(f"Formato de data inválido: {data_str}. Formatos aceitos: YYYY-MM-DD, DD/MM/YYYY, YYYY/MM/DD, DD-MM-YYYY")

@app.route('/')
def index():
    return render_template('index.html', now=datetime.now())

@app.route('/regras')
def regras():
    """Serve o arquivo REGRAS_VALIDACAO.md."""
    try:
        # Tenta primeiro encontrar o arquivo no diretório de recursos do PyInstaller
        regras_path = get_resource_path("REGRAS_VALIDACAO.md")
        
        if not os.path.exists(regras_path):
            # Se não encontrar, tenta no diretório do projeto
            regras_path = os.path.join(os.path.dirname(__file__), "..", "..", "REGRAS_VALIDACAO.md")
        
        if not os.path.exists(regras_path):
            logger.error(f"Arquivo de regras não encontrado em: {regras_path}")
            flash('Arquivo de regras não encontrado', 'error')
            return redirect(url_for('index'))
            
        logger.info(f"Carregando arquivo de regras de: {regras_path}")
        with open(regras_path, 'r', encoding='utf-8') as f:
            conteudo_md = f.read()
            
        # Converte o conteúdo MARKDOWN para HTML
        conteudo_html = markdown.markdown(conteudo_md, extensions=['tables', 'fenced_code'])
            
        return render_template('regras.html', conteudo=conteudo_html, now=datetime.now())
    except Exception as e:
        logger.error(f"Erro ao carregar regras: {str(e)}")
        flash('Erro ao carregar regras de validação', 'error')
        return redirect(url_for('index'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'GET':
        return redirect(url_for('index'))
        
    try:
        if 'arquivo' not in request.files:
            logger.error("Nenhum arquivo enviado")
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(url_for('index'))
        
        arquivo = request.files['arquivo']
        
        if arquivo.filename == '':
            logger.error("Nome do arquivo vazio")
            flash('Nenhum arquivo selecionado', 'error')
            return redirect(url_for('index'))
        
        if arquivo and arquivo.filename.endswith(('.xlsx', '.xls', '.csv')):
            # Salva o arquivo temporariamente
            filename = secure_filename(arquivo.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            arquivo.save(filepath)
            
            # Cria um ID para o processamento
            processamento_id = str(uuid.uuid4())
            
            # Inicia o processamento em background
            thread = ProcessamentoThread(filepath, processamento_id)
            thread.start()
            
            # Redireciona para a página de status
            return redirect(url_for('status', processamento_id=processamento_id))
        
        logger.error(f"Tipo de arquivo não suportado: {arquivo.filename}")
        flash('Tipo de arquivo não suportado. Por favor, envie um arquivo Excel (.xlsx, .xls) ou CSV (.csv)', 'error')
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Erro no upload: {str(e)}")
        flash(f'Erro ao processar o arquivo: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/status/<processamento_id>')
def status(processamento_id):
    if processamento_id not in processamentos:
        flash('Processamento não encontrado', 'error')
        return redirect(url_for('index'))
    
    status = processamentos[processamento_id]
    
    # Prepara os dados para o template
    template_data = {
        'processamento_id': processamento_id,
        'status': status,
        'filename': os.path.basename(status.get('arquivo', '')),
        'start_time': status.get('start_time', datetime.now().strftime('%H:%M:%S')),
        'end_time': status.get('end_time', ''),
        'processing_time': status.get('processing_time', ''),
        'progress': status.get('progresso', 0),
        'error_message': status.get('mensagem', ''),
        'erros': status.get('erros', []),
        'now': datetime.now(),
        'steps': {
            'load_completed': status['steps']['load']['completed'],
            'current_step': status['current_step'],
            'load_error': status['steps']['load']['error'],
            'load_message': status['steps']['load']['message'],
            'validation_completed': status['steps']['validation']['completed'],
            'validation_error': status['steps']['validation']['error'],
            'validation_message': status['steps']['validation']['message'],
            'upload_completed': status['steps']['upload']['completed'],
            'upload_error': status['steps']['upload']['error'],
            'upload_message': status['steps']['upload']['message'],
            'metadata_completed': status['steps']['metadata']['completed'],
            'metadata_error': status['steps']['metadata']['error'],
            'metadata_message': status['steps']['metadata']['message']
        }
    }
    
    # Se o processamento estiver em andamento, não mostra erros
    if not status.get('concluido', False):
        template_data['error_message'] = ''
        template_data['erros'] = []
    
    return render_template('processamento.html', **template_data)

@app.route('/progresso/<processamento_id>')
def progresso(processamento_id):
    if processamento_id not in processamentos:
        return jsonify({"erro": "Processamento não encontrado"}), 404
    
    status = processamentos[processamento_id]
    
    # Se o processamento estiver em andamento, não retorna erros
    if not status.get('concluido', False):
        status['mensagem'] = ''
        status['erros'] = []
    
    return jsonify(status)

@app.route('/download_modelo')
def download_modelo():
    """Rota para download do arquivo de exemplo do GCP Storage."""
    try:
        # Verifica se o arquivo de credenciais existe
        if not BIGQUERY_CREDENTIALS_PATH.exists():
            logger.error(f"Arquivo de credenciais não encontrado em: {BIGQUERY_CREDENTIALS_PATH}")
            flash("Credenciais do GCP não encontradas", "error")
            return redirect(url_for('index'))
            
        # Logs de debug para comparação
        logger.info(f"[REGISTROS] Caminho credenciais: {BIGQUERY_CREDENTIALS_PATH}")
        logger.info(f"[REGISTROS] Arquivo existe: {BIGQUERY_CREDENTIALS_PATH.exists()}")
        logger.info(f"[REGISTROS] Caminho absoluto: {BIGQUERY_CREDENTIALS_PATH.absolute()}")
        logger.info(f"[REGISTROS] Executável congelado: {getattr(sys, 'frozen', False)}")
        logger.info(f"[REGISTROS] Executável: {sys.executable}")
        logger.info(f"[REGISTROS] get_config_path(): {get_config_path()}")
        logger.info(f"[REGISTROS] CREDENTIALS_DIR: {CREDENTIALS_DIR}")
            
        # Cria as credenciais a partir do arquivo JSON
        credentials = service_account.Credentials.from_service_account_file(
            BIGQUERY_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        logger.info("Credenciais do GCP carregadas com sucesso")
        
        # Inicializa o cliente do Storage
        storage_client = storage.Client(
            project=BIGQUERY_CONFIG.get("project_id", "projeto-teste"),
            credentials=credentials
        )
        logger.info(f"Cliente Storage inicializado com projeto: {BIGQUERY_CONFIG.get('project_id')}")
        
        # Obtém o bucket
        bucket = storage_client.bucket(GCP_STORAGE_CONFIG["bucket_name"])
        blob = bucket.blob(GCP_STORAGE_CONFIG["modelo_path"])
        
        # Cria um arquivo temporário
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        
        # Download do arquivo
        blob.download_to_filename(temp_file.name)
        logger.info(f"Arquivo modelo baixado com sucesso do GCP Storage: {GCP_STORAGE_CONFIG['modelo_path']}")
        
        # Retorna o arquivo para download
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name="modelo_importacao.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        logger.error(f"Erro ao baixar arquivo modelo do GCP Storage: {str(e)}")
        flash("Erro ao baixar arquivo modelo", "error")
        return redirect(url_for('index'))

@app.route('/registros')
def listar_registros():
    """Lista os registros da tabela ORCADO."""
    try:
        # Logs específicos para debug do contexto
        logger.info("=== INÍCIO VISUALIZAÇÃO REGISTROS ===")
        logger.info(f"Thread atual: {threading.current_thread().name}")
        logger.info(f"Thread ID: {threading.current_thread().ident}")
        logger.info(f"Executável congelado: {getattr(sys, 'frozen', False)}")
        logger.info(f"Executável: {sys.executable}")
        logger.info(f"Diretório atual: {os.getcwd()}")
        
        # Obtém os filtros da query string
        n_conta = request.args.get('n_conta', '')
        n_centro_custo = request.args.get('n_centro_custo', '')
        data_inicio = request.args.get('data_inicio', '')
        data_fim = request.args.get('data_fim', '')
        versao = request.args.get('versao', '')
        operacao = request.args.get('operacao', '')
        filial = request.args.get('filial', '')
        rateio = request.args.get('rateio', '')
        origem = request.args.get('origem', '')
        
        # Verifica se o arquivo de credenciais existe
        if not BIGQUERY_CREDENTIALS_PATH.exists():
            flash("Credenciais do BigQuery não encontradas", "error")
            return redirect(url_for('index'))
            
        # Logs de debug para comparação
        logger.info(f"[REGISTROS] Caminho credenciais: {BIGQUERY_CREDENTIALS_PATH}")
        logger.info(f"[REGISTROS] Arquivo existe: {BIGQUERY_CREDENTIALS_PATH.exists()}")
        logger.info(f"[REGISTROS] Caminho absoluto: {BIGQUERY_CREDENTIALS_PATH.absolute()}")
        logger.info(f"[REGISTROS] Executável congelado: {getattr(sys, 'frozen', False)}")
        logger.info(f"[REGISTROS] Executável: {sys.executable}")
        logger.info(f"[REGISTROS] get_config_path(): {get_config_path()}")
        logger.info(f"[REGISTROS] CREDENTIALS_DIR: {CREDENTIALS_DIR}")
            
        # Cria as credenciais a partir do arquivo JSON
        credentials = service_account.Credentials.from_service_account_file(
            BIGQUERY_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        
        # Inicializa o cliente do BigQuery
        client = bigquery.Client(
            project=BIGQUERY_CONFIG.get("project_id", "projeto-teste"),
            credentials=credentials
        )
        
        # Define o ID do dataset e tabela
        dataset_id = BIGQUERY_CONFIG.get("dataset_id", "silver")
        table_id = BIGQUERY_CONFIG.get("table_id", "ORCADO")
        
        # Constrói a query base
        query = f"""
            SELECT 
                N_CONTA,
                N_CENTRO_CUSTO,
                DESCRICAO,
                VALOR,
                DATA,
                VERSAO,
                OPERACAO,
                DATA_ATUALIZACAO,
                FILIAL,
                RATEIO,
                ORIGEM
            FROM `{dataset_id}.{table_id}`
            WHERE 1=1
        """
        
        # Adiciona os filtros
        if n_conta:
            query += f" AND CAST(N_CONTA AS STRING) = '{n_conta}'"
        if n_centro_custo:
            query += f" AND CAST(N_CENTRO_CUSTO AS STRING) = '{n_centro_custo}'"
        if data_inicio:
            query += f" AND DATA >= '{data_inicio}'"
        if data_fim:
            query += f" AND DATA <= '{data_fim}'"
        if versao:
            query += f" AND VERSAO = '{versao}'"
        if operacao:
            query += f" AND OPERACAO = '{operacao}'"
        if filial:
            query += f" AND CAST(FILIAL AS STRING) = '{filial}'"
        if rateio:
            query += f" AND RATEIO = '{rateio}'"
        if origem:
            query += f" AND ORIGEM LIKE '%{origem}%'"
        
        # Query para contar o total de registros
        count_query = f"""
            SELECT COUNT(*) as total
            FROM `{dataset_id}.{table_id}`
            WHERE 1=1
        """
        
        # Adiciona os mesmos filtros na query de contagem
        if n_conta:
            count_query += f" AND CAST(N_CONTA AS STRING) = '{n_conta}'"
        if n_centro_custo:
            count_query += f" AND CAST(N_CENTRO_CUSTO AS STRING) = '{n_centro_custo}'"
        if data_inicio:
            count_query += f" AND DATA >= '{data_inicio}'"
        if data_fim:
            count_query += f" AND DATA <= '{data_fim}'"
        if versao:
            count_query += f" AND VERSAO = '{versao}'"
        if operacao:
            count_query += f" AND OPERACAO = '{operacao}'"
        if filial:
            count_query += f" AND CAST(FILIAL AS STRING) = '{filial}'"
        if rateio:
            count_query += f" AND RATEIO = '{rateio}'"
        if origem:
            count_query += f" AND ORIGEM LIKE '%{origem}%'"
        
        # Executa a query de contagem
        count_job = client.query(count_query)
        total_registros = next(count_job.result()).total
        
        # Adiciona ordenação e limite na query principal
        query += " ORDER BY DATA_ATUALIZACAO DESC LIMIT 100"
        
        # Executa a query principal
        query_job = client.query(query)
        registros = [dict(row) for row in query_job]
        
        # Obtém a lista de versões para o filtro
        versoes_query = f"""
            SELECT DISTINCT VERSAO 
            FROM `{dataset_id}.{table_id}`
            ORDER BY VERSAO DESC
        """
        
        versoes_job = client.query(versoes_query)
        versoes = [row.VERSAO for row in versoes_job]
        
        # Prepara os filtros para o template
        filtros = {
            'n_conta': n_conta,
            'n_centro_custo': n_centro_custo,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'versao': versao,
            'operacao': operacao,
            'filial': filial,
            'rateio': rateio,
            'origem': origem
        }
        
        return render_template('registros.html', 
                             registros=registros, 
                             versoes=versoes,
                             filtros=filtros,
                             total_registros=total_registros,
                             now=datetime.now())
                             
    except Exception as e:
        logger.error(f"Erro ao listar registros: {str(e)}")
        flash(f"Erro ao listar registros: {str(e)}", "danger")
        return redirect(url_for('index'))

@app.route('/registros/editar', methods=['POST'])
def editar_registro():
    """Edita um registro na tabela ORCADO e registra a alteração nos metadados."""
    try:
        # Obtém os dados do formulário
        filial = request.form.get('FILIAL')
        n_conta = request.form.get('N_CONTA_DISPLAY')
        n_centro_custo = request.form.get('N_CENTRO_CUSTO_DISPLAY')
        
        # Faz o parse da data usando a função utilitária
        data_str = request.form.get('DATA_DISPLAY')
        data = parse_data_flexivel(data_str)
        
        versao = request.form.get('VERSAO_DISPLAY')
        descricao = request.form.get('DESCRICAO')
        valor = float(request.form.get('VALOR'))
        operacao = request.form.get('OPERACAO', '')
        rateio = request.form.get('RATEIO', '')
        origem = request.form.get('ORIGEM', '')
        
        # Verifica se o arquivo de credenciais existe
        if not BIGQUERY_CREDENTIALS_PATH.exists():
            flash("Credenciais do BigQuery não encontradas", "error")
            return redirect(url_for('listar_registros'))
            
        # Logs de debug para comparação
        logger.info(f"[EDITAR] Caminho credenciais: {BIGQUERY_CREDENTIALS_PATH}")
        logger.info(f"[EDITAR] Arquivo existe: {BIGQUERY_CREDENTIALS_PATH.exists()}")
        logger.info(f"[EDITAR] Caminho absoluto: {BIGQUERY_CREDENTIALS_PATH.absolute()}")
        logger.info(f"[EDITAR] Executável congelado: {getattr(sys, 'frozen', False)}")
        logger.info(f"[EDITAR] Executável: {sys.executable}")
        logger.info(f"[EDITAR] get_config_path(): {get_config_path()}")
        logger.info(f"[EDITAR] CREDENTIALS_DIR: {CREDENTIALS_DIR}")
            
        # Cria as credenciais a partir do arquivo JSON
        credentials = service_account.Credentials.from_service_account_file(
            BIGQUERY_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        
        # Inicializa o cliente do BigQuery
        client = bigquery.Client(
            project=BIGQUERY_CONFIG.get("project_id", "projeto-teste"),
            credentials=credentials
        )
        
        # Define o ID do dataset e tabela
        dataset_id = BIGQUERY_CONFIG.get("dataset_id", "silver")
        table_id = BIGQUERY_CONFIG.get("table_id", "ORCADO")
        metadata_table_id = BIGQUERY_CONFIG.get("metadata_table_id", "ORCADO_METADATA")
        
        # Obtém os valores originais dos campos hidden
        n_conta_original = request.form.get('N_CONTA')
        n_centro_custo_original = request.form.get('N_CENTRO_CUSTO')
        data_original = request.form.get('DATA')
        versao_original = request.form.get('VERSAO')
        
        # Busca o registro original para comparar as alterações
        query_original = f"""
        SELECT FILIAL, N_CONTA, N_CENTRO_CUSTO, DESCRICAO, VALOR, OPERACAO, RATEIO, ORIGEM
        FROM `{dataset_id}.{table_id}`
        WHERE 
            N_CONTA = '{n_conta_original}'
            AND N_CENTRO_CUSTO = '{n_centro_custo_original}'
            AND DATA = DATE('{data_original}')
            AND VERSAO = '{versao_original}'
        """
        query_job = client.query(query_original)
        resultado = query_job.result()
        registro_original = next(resultado, None)
        
        if registro_original:
            # Prepara o registro de metadados com as alterações
            alteracoes = []
            if registro_original.FILIAL != filial:
                alteracoes.append(f"FILIAL: '{registro_original.FILIAL}' -> '{filial}'")
            if registro_original.N_CONTA != n_conta:
                alteracoes.append(f"N_CONTA: '{registro_original.N_CONTA}' -> '{n_conta}'")
            if registro_original.N_CENTRO_CUSTO != n_centro_custo:
                alteracoes.append(f"N_CENTRO_CUSTO: '{registro_original.N_CENTRO_CUSTO}' -> '{n_centro_custo}'")
            if registro_original.DESCRICAO != descricao:
                alteracoes.append(f"DESCRICAO: '{registro_original.DESCRICAO}' -> '{descricao}'")
            if float(registro_original.VALOR) != valor:
                alteracoes.append(f"VALOR: {registro_original.VALOR} -> {valor}")
            if registro_original.OPERACAO != operacao:
                alteracoes.append(f"OPERACAO: '{registro_original.OPERACAO}' -> '{operacao}'")
            if registro_original.RATEIO != rateio:
                alteracoes.append(f"RATEIO: '{registro_original.RATEIO}' -> '{rateio}'")
            if registro_original.ORIGEM != origem:
                alteracoes.append(f"ORIGEM: '{registro_original.ORIGEM}' -> '{origem}'")
            
            # Query para atualizar o registro
            query = f"""
            UPDATE `{dataset_id}.{table_id}`
            SET 
                FILIAL = '{filial}',
                N_CONTA = '{n_conta}',
                N_CENTRO_CUSTO = '{n_centro_custo}',
                DESCRICAO = '{descricao}',
                VALOR = {valor},
                OPERACAO = '{operacao}',
                RATEIO = '{rateio}',
                ORIGEM = '{origem}',
                DATA_ATUALIZACAO = CURRENT_TIMESTAMP()
            WHERE 
                N_CONTA = '{n_conta_original}'
                AND N_CENTRO_CUSTO = '{n_centro_custo_original}'
                AND DATA = DATE('{data_original}')
                AND VERSAO = '{versao_original}'
            """
            
            # Executa a query
            query_job = client.query(query)
            query_job.result()
            
            # Registra a alteração nos metadados
            if alteracoes:
                metadata = {
                    "DATA_IMPORTACAO": pd.Timestamp.now(),
                    "USUARIO": str(getpass.getuser()),
                    "SISTEMA_OPERACIONAL": str(platform.system()),
                    "VERSAO_SISTEMA": str(platform.version()),
                    "ARQUIVO_ORIGEM": f"EDITADO: {n_conta}/{n_centro_custo}/{data}/{versao}",
                    "TOTAL_REGISTROS": 1,
                    "STATUS": "EDITADO",
                    "DETALHES": f"Alterações: {', '.join(alteracoes)}"
                }
                
                # Cria o DataFrame com tipos explícitos
                df_metadata = pd.DataFrame({
                    "DATA_IMPORTACAO": [metadata["DATA_IMPORTACAO"]],
                    "USUARIO": [metadata["USUARIO"]],
                    "SISTEMA_OPERACIONAL": [metadata["SISTEMA_OPERACIONAL"]],
                    "VERSAO_SISTEMA": [metadata["VERSAO_SISTEMA"]],
                    "ARQUIVO_ORIGEM": [metadata["ARQUIVO_ORIGEM"]],
                    "TOTAL_REGISTROS": [metadata["TOTAL_REGISTROS"]],
                    "STATUS": [metadata["STATUS"]],
                    "DETALHES": [metadata["DETALHES"]]
                })
                
                # Define o schema da tabela de metadados
                metadata_schema = [
                    bigquery.SchemaField("DATA_IMPORTACAO", "TIMESTAMP", mode="REQUIRED"),
                    bigquery.SchemaField("USUARIO", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("SISTEMA_OPERACIONAL", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("VERSAO_SISTEMA", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("ARQUIVO_ORIGEM", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("TOTAL_REGISTROS", "INTEGER", mode="REQUIRED"),
                    bigquery.SchemaField("STATUS", "STRING", mode="REQUIRED"),
                    bigquery.SchemaField("DETALHES", "STRING", mode="REQUIRED")
                ]
                
                # Configura o job para os metadados
                metadata_job_config = bigquery.LoadJobConfig(
                    write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
                    schema=metadata_schema
                )
                
                # Carrega os metadados
                metadata_table_ref = client.dataset(dataset_id).table(metadata_table_id)
                metadata_job = client.load_table_from_dataframe(
                    df_metadata, metadata_table_ref, job_config=metadata_job_config
                )
                metadata_job.result()
            
            flash("Registro atualizado com sucesso", "success")
        else:
            flash("Registro não encontrado", "error")
        
    except Exception as e:
        logger.error(f"Erro ao editar registro no BigQuery: {str(e)}")
        flash(f"Erro ao editar registro: {str(e)}", "error")
        
    return redirect(url_for('listar_registros'))

@app.route('/registros/deletar', methods=['POST'])
def deletar_registro():
    """Deleta um registro da tabela ORCADO e registra a deleção nos metadados."""
    try:
        # Obtém os dados do formulário
        n_conta = request.form.get('N_CONTA')
        n_centro_custo = request.form.get('N_CENTRO_CUSTO')
        data_str = request.form.get('DATA')
        try:
            data = parse_data_flexivel(data_str)
        except ValueError as e:
            logger.error(f"Formato de data inválido: {data_str}")
            flash(f"Formato de data inválido: {str(e)}", "error")
            return redirect(url_for('listar_registros'))
        versao = request.form.get('VERSAO')
        
        logger.info(f"Iniciando deleção de registro: N_CONTA={n_conta}, N_CENTRO_CUSTO={n_centro_custo}, DATA={data}, VERSAO={versao}")
        
        # Verifica se o arquivo de credenciais existe
        if not BIGQUERY_CREDENTIALS_PATH.exists():
            logger.error(f"Arquivo de credenciais não encontrado em: {BIGQUERY_CREDENTIALS_PATH}")
            flash("Credenciais do BigQuery não encontradas", "error")
            return redirect(url_for('listar_registros'))
            
        # Logs de debug para comparação
        logger.info(f"[DELETAR] Caminho credenciais: {BIGQUERY_CREDENTIALS_PATH}")
        logger.info(f"[DELETAR] Arquivo existe: {BIGQUERY_CREDENTIALS_PATH.exists()}")
        logger.info(f"[DELETAR] Caminho absoluto: {BIGQUERY_CREDENTIALS_PATH.absolute()}")
        logger.info(f"[DELETAR] Executável congelado: {getattr(sys, 'frozen', False)}")
        logger.info(f"[DELETAR] Executável: {sys.executable}")
        logger.info(f"[DELETAR] get_config_path(): {get_config_path()}")
        logger.info(f"[DELETAR] CREDENTIALS_DIR: {CREDENTIALS_DIR}")
            
        # Cria as credenciais a partir do arquivo JSON
        credentials = service_account.Credentials.from_service_account_file(
            BIGQUERY_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        logger.info("Credenciais do BigQuery carregadas com sucesso")
        
        # Inicializa o cliente do BigQuery
        client = bigquery.Client(
            project=BIGQUERY_CONFIG.get("project_id", "projeto-teste"),
            credentials=credentials
        )
        logger.info(f"Cliente BigQuery inicializado com projeto: {BIGQUERY_CONFIG.get('project_id')}")
        
        # Define o ID do dataset e tabela
        dataset_id = BIGQUERY_CONFIG.get("dataset_id", "silver")
        table_id = BIGQUERY_CONFIG.get("table_id", "ORCADO")
        metadata_table_id = BIGQUERY_CONFIG.get("metadata_table_id", "ORCADO_METADATA")
        
        # Query para deletar o registro
        query = f"""
        DELETE FROM `{dataset_id}.{table_id}`
        WHERE 
            N_CONTA = '{n_conta}'
            AND N_CENTRO_CUSTO = '{n_centro_custo}'
            AND DATA = DATE('{data}')
            AND VERSAO = '{versao}'
        """
        
        logger.info(f"Executando query de deleção: {query}")
        
        # Executa a query
        query_job = client.query(query)
        query_job.result()
        logger.info("Query de deleção executada com sucesso")
        
        # Registra a deleção nos metadados
        metadata = {
            "DATA_IMPORTACAO": pd.Timestamp.now(),
            "USUARIO": str(getpass.getuser()),
            "SISTEMA_OPERACIONAL": str(platform.system()),
            "VERSAO_SISTEMA": str(platform.version()),
            "ARQUIVO_ORIGEM": f"DELETADO: {n_conta}/{n_centro_custo}/{data}/{versao}",
            "TOTAL_REGISTROS": 1,
            "STATUS": "DELETADO",
            "DETALHES": "Registro deletado manualmente"
        }
        
        logger.info(f"Registrando metadados da deleção: {metadata}")
        
        # Cria o DataFrame com tipos explícitos
        df_metadata = pd.DataFrame({
            "DATA_IMPORTACAO": [metadata["DATA_IMPORTACAO"]],
            "USUARIO": [metadata["USUARIO"]],
            "SISTEMA_OPERACIONAL": [metadata["SISTEMA_OPERACIONAL"]],
            "VERSAO_SISTEMA": [metadata["VERSAO_SISTEMA"]],
            "ARQUIVO_ORIGEM": [metadata["ARQUIVO_ORIGEM"]],
            "TOTAL_REGISTROS": [metadata["TOTAL_REGISTROS"]],
            "STATUS": [metadata["STATUS"]],
            "DETALHES": [metadata["DETALHES"]]
        })
        
        # Define o schema da tabela de metadados
        metadata_schema = [
            bigquery.SchemaField("DATA_IMPORTACAO", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("USUARIO", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("SISTEMA_OPERACIONAL", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("VERSAO_SISTEMA", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("ARQUIVO_ORIGEM", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("TOTAL_REGISTROS", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("STATUS", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("DETALHES", "STRING", mode="REQUIRED")
        ]
        
        # Configura o job para os metadados
        metadata_job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=metadata_schema
        )
        
        # Carrega os metadados
        metadata_table_ref = client.dataset(dataset_id).table(metadata_table_id)
        metadata_job = client.load_table_from_dataframe(
            df_metadata, metadata_table_ref, job_config=metadata_job_config
        )
        metadata_job.result()
        
        flash("Registro deletado com sucesso", "success")
        
    except Exception as e:
        logger.error(f"Erro ao deletar registro no BigQuery: {str(e)}")
        flash(f"Erro ao deletar registro: {str(e)}", "error")
        
    return redirect(url_for('listar_registros'))

@app.route('/registros/deletar_versao', methods=['POST'])
def deletar_por_versao():
    """Deleta todos os registros de uma versão específica."""
    try:
        versao = request.form.get('VERSAO')
        
        if not versao:
            flash("Versão não especificada", "error")
            return redirect(url_for('listar_registros'))
        
        # Verifica se o arquivo de credenciais existe
        if not BIGQUERY_CREDENTIALS_PATH.exists():
            flash("Credenciais do BigQuery não encontradas", "error")
            return redirect(url_for('listar_registros'))
            
        # Logs de debug para comparação
        logger.info(f"[DELETAR_VERSAO] Caminho credenciais: {BIGQUERY_CREDENTIALS_PATH}")
        logger.info(f"[DELETAR_VERSAO] Arquivo existe: {BIGQUERY_CREDENTIALS_PATH.exists()}")
        logger.info(f"[DELETAR_VERSAO] Caminho absoluto: {BIGQUERY_CREDENTIALS_PATH.absolute()}")
        logger.info(f"[DELETAR_VERSAO] Executável congelado: {getattr(sys, 'frozen', False)}")
        logger.info(f"[DELETAR_VERSAO] Executável: {sys.executable}")
        logger.info(f"[DELETAR_VERSAO] get_config_path(): {get_config_path()}")
        logger.info(f"[DELETAR_VERSAO] CREDENTIALS_DIR: {CREDENTIALS_DIR}")
            
        # Cria as credenciais a partir do arquivo JSON
        credentials = service_account.Credentials.from_service_account_file(
            BIGQUERY_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        
        # Inicializa o cliente do BigQuery
        client = bigquery.Client(
            project=BIGQUERY_CONFIG.get("project_id", "projeto-teste"),
            credentials=credentials
        )
        
        # Define o ID do dataset e tabela
        dataset_id = BIGQUERY_CONFIG.get("dataset_id", "silver")
        table_id = BIGQUERY_CONFIG.get("table_id", "ORCADO")
        
        # Query para deletar os registros
        query = f"""
        DELETE FROM `{dataset_id}.{table_id}`
        WHERE VERSAO = '{versao}'
        """
        
        # Executa a query
        query_job = client.query(query)
        query_job.result()
        
        flash(f"Todos os registros da versão {versao} foram deletados com sucesso", "success")
        
    except Exception as e:
        logger.error(f"Erro ao deletar registros por versão: {str(e)}")
        flash(f"Erro ao deletar registros: {str(e)}", "error")
        
    return redirect(url_for('listar_registros'))

@app.route('/registros/deletar_filial', methods=['POST'])
def deletar_por_filial():
    """Deleta todos os registros de uma filial específica."""
    try:
        filial = request.form.get('FILIAL')
        
        if not filial:
            flash("Filial não especificada", "error")
            return redirect(url_for('listar_registros'))
        
        # Verifica se o arquivo de credenciais existe
        if not BIGQUERY_CREDENTIALS_PATH.exists():
            flash("Credenciais do BigQuery não encontradas", "error")
            return redirect(url_for('listar_registros'))
            
        # Logs de debug para comparação
        logger.info(f"[DELETAR_FILIAL] Caminho credenciais: {BIGQUERY_CREDENTIALS_PATH}")
        logger.info(f"[DELETAR_FILIAL] Arquivo existe: {BIGQUERY_CREDENTIALS_PATH.exists()}")
        logger.info(f"[DELETAR_FILIAL] Caminho absoluto: {BIGQUERY_CREDENTIALS_PATH.absolute()}")
        logger.info(f"[DELETAR_FILIAL] Executável congelado: {getattr(sys, 'frozen', False)}")
        logger.info(f"[DELETAR_FILIAL] Executável: {sys.executable}")
        logger.info(f"[DELETAR_FILIAL] get_config_path(): {get_config_path()}")
        logger.info(f"[DELETAR_FILIAL] CREDENTIALS_DIR: {CREDENTIALS_DIR}")
            
        # Cria as credenciais a partir do arquivo JSON
        credentials = service_account.Credentials.from_service_account_file(
            BIGQUERY_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        
        # Inicializa o cliente do BigQuery
        client = bigquery.Client(
            project=BIGQUERY_CONFIG.get("project_id", "projeto-teste"),
            credentials=credentials
        )
        
        # Define o ID do dataset e tabela
        dataset_id = BIGQUERY_CONFIG.get("dataset_id", "silver")
        table_id = BIGQUERY_CONFIG.get("table_id", "ORCADO")
        metadata_table_id = BIGQUERY_CONFIG.get("metadata_table_id", "ORCADO_METADATA")
        
        # Query para deletar os registros
        query = f"""
        DELETE FROM `{dataset_id}.{table_id}`
        WHERE FILIAL = '{filial}'
        """
        
        # Executa a query
        query_job = client.query(query)
        query_job.result()
        
        # Registra a deleção nos metadados
        metadata = {
            "DATA_IMPORTACAO": pd.Timestamp.now(),
            "USUARIO": str(getpass.getuser()),
            "SISTEMA_OPERACIONAL": str(platform.system()),
            "VERSAO_SISTEMA": str(platform.version()),
            "ARQUIVO_ORIGEM": f"DELETADO: Filial {filial}",
            "TOTAL_REGISTROS": 0,  # Não sabemos o número exato de registros deletados
            "STATUS": "DELETADO",
            "DETALHES": f"Registros deletados para filial {filial}"
        }
        
        # Cria o DataFrame com tipos explícitos
        df_metadata = pd.DataFrame({
            "DATA_IMPORTACAO": [metadata["DATA_IMPORTACAO"]],
            "USUARIO": [metadata["USUARIO"]],
            "SISTEMA_OPERACIONAL": [metadata["SISTEMA_OPERACIONAL"]],
            "VERSAO_SISTEMA": [metadata["VERSAO_SISTEMA"]],
            "ARQUIVO_ORIGEM": [metadata["ARQUIVO_ORIGEM"]],
            "TOTAL_REGISTROS": [metadata["TOTAL_REGISTROS"]],
            "STATUS": [metadata["STATUS"]],
            "DETALHES": [metadata["DETALHES"]]
        })
        
        # Define o schema da tabela de metadados
        metadata_schema = [
            bigquery.SchemaField("DATA_IMPORTACAO", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("USUARIO", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("SISTEMA_OPERACIONAL", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("VERSAO_SISTEMA", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("ARQUIVO_ORIGEM", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("TOTAL_REGISTROS", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("STATUS", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("DETALHES", "STRING", mode="REQUIRED")
        ]
        
        # Configura o job para os metadados
        metadata_job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=metadata_schema
        )
        
        # Carrega os metadados
        metadata_table_ref = client.dataset(dataset_id).table(metadata_table_id)
        metadata_job = client.load_table_from_dataframe(
            df_metadata, metadata_table_ref, job_config=metadata_job_config
        )
        metadata_job.result()
        
        flash(f"Registros da filial {filial} foram deletados com sucesso", "success")
        
    except Exception as e:
        logger.error(f"Erro ao deletar registros por filial: {str(e)}")
        flash(f"Erro ao deletar registros: {str(e)}", "error")
        
    return redirect(url_for('listar_registros'))

@app.route('/exportar-excel')
def exportar_excel():
    """Exporta os registros filtrados para Excel."""
    try:
        # Obtém os filtros da query string
        n_conta = request.args.get('n_conta', '')
        n_centro_custo = request.args.get('n_centro_custo', '')
        data_inicio = request.args.get('data_inicio', '')
        data_fim = request.args.get('data_fim', '')
        versao = request.args.get('versao', '')
        operacao = request.args.get('operacao', '')
        filial = request.args.get('filial', '')
        rateio = request.args.get('rateio', '')
        origem = request.args.get('origem', '')
        
        # Verifica se o arquivo de credenciais existe
        if not BIGQUERY_CREDENTIALS_PATH.exists():
            flash("Credenciais do BigQuery não encontradas", "error")
            return redirect(url_for('listar_registros'))
            
        # Logs de debug para comparação
        logger.info(f"[EXPORTAR_EXCEL] Caminho credenciais: {BIGQUERY_CREDENTIALS_PATH}")
        logger.info(f"[EXPORTAR_EXCEL] Arquivo existe: {BIGQUERY_CREDENTIALS_PATH.exists()}")
        logger.info(f"[EXPORTAR_EXCEL] Caminho absoluto: {BIGQUERY_CREDENTIALS_PATH.absolute()}")
        logger.info(f"[EXPORTAR_EXCEL] Executável congelado: {getattr(sys, 'frozen', False)}")
        logger.info(f"[EXPORTAR_EXCEL] Executável: {sys.executable}")
        logger.info(f"[EXPORTAR_EXCEL] get_config_path(): {get_config_path()}")
        logger.info(f"[EXPORTAR_EXCEL] CREDENTIALS_DIR: {CREDENTIALS_DIR}")
            
        # Cria as credenciais a partir do arquivo JSON
        credentials = service_account.Credentials.from_service_account_file(
            BIGQUERY_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        
        # Inicializa o cliente do BigQuery
        client = bigquery.Client(
            project=BIGQUERY_CONFIG.get("project_id", "projeto-teste"),
            credentials=credentials
        )
        
        # Define o ID do dataset e tabela
        dataset_id = BIGQUERY_CONFIG.get("dataset_id", "silver")
        table_id = BIGQUERY_CONFIG.get("table_id", "ORCADO")
        
        # Constrói a query base
        query = f"""
            SELECT 
                N_CONTA,
                N_CENTRO_CUSTO,
                DESCRICAO,
                VALOR,
                DATA,
                VERSAO,
                OPERACAO,
                DATA_ATUALIZACAO,
                FILIAL,
                RATEIO,
                ORIGEM
            FROM `{BIGQUERY_CONFIG.get('project_id')}.{dataset_id}.{table_id}`
            WHERE 1=1
        """
        
        # Adiciona os filtros
        if n_conta:
            query += f" AND CAST(N_CONTA AS STRING) = '{n_conta}'"
        if n_centro_custo:
            query += f" AND CAST(N_CENTRO_CUSTO AS STRING) = '{n_centro_custo}'"
        if data_inicio:
            query += f" AND DATA >= DATE('{data_inicio}')"
        if data_fim:
            query += f" AND DATA <= DATE('{data_fim}')"
        if versao:
            query += f" AND VERSAO = '{versao}'"
        if operacao:
            query += f" AND OPERACAO = '{operacao}'"
        if filial:
            query += f" AND CAST(FILIAL AS STRING) = '{filial}'"
        if rateio:
            query += f" AND RATEIO = '{rateio}'"
        if origem:
            query += f" AND ORIGEM LIKE '%{origem}%'"
        
        # Adiciona ordenação
        query += " ORDER BY DATA_ATUALIZACAO DESC"
        
        # Executa a query
        query_job = client.query(query)
        registros = [dict(row) for row in query_job]
        
        # Cria um DataFrame com os registros
        df = pd.DataFrame(registros)
        
        # Formata as colunas
        df['DATA'] = pd.to_datetime(df['DATA']).dt.strftime('%d/%m/%Y')
        df['DATA_ATUALIZACAO'] = pd.to_datetime(df['DATA_ATUALIZACAO']).dt.strftime('%d/%m/%Y %H:%M:%S')
        df['VALOR'] = df['VALOR'].apply(lambda x: f"R$ {x:,.2f}")
        
        # Renomeia as colunas
        df = df.rename(columns={
            'N_CONTA': 'Conta',
            'N_CENTRO_CUSTO': 'Centro de Custo',
            'DESCRICAO': 'Descrição',
            'VALOR': 'Valor',
            'DATA': 'Data',
            'VERSAO': 'Versão',
            'OPERACAO': 'Operação',
            'DATA_ATUALIZACAO': 'Data de Atualização',
            'FILIAL': 'Filial',
            'RATEIO': 'Rateio',
            'ORIGEM': 'Origem'
        })
        
        # Cria o arquivo Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Registros', index=False)
            
            # Ajusta a largura das colunas
            worksheet = writer.sheets['Registros']
            for i, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).apply(len).max(), len(col)) + 2
                worksheet.set_column(i, i, max_length)
        
        output.seek(0)
        
        # Gera o nome do arquivo com timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'registros_{timestamp}.xlsx'
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"Erro ao exportar para Excel: {str(e)}")
        flash(f"Erro ao exportar para Excel: {str(e)}", "danger")
        return redirect(url_for('listar_registros'))

@app.route('/registros/deletar_filtros', methods=['POST'])
def deletar_por_filtros():
    """Deleta registros baseado nos filtros aplicados."""
    try:
        # Obtém os parâmetros de filtro
        n_conta = request.form.get('n_conta', '')
        n_centro_custo = request.form.get('n_centro_custo', '')
        data_inicio = request.form.get('data_inicio', '')
        data_fim = request.form.get('data_fim', '')
        versao = request.form.get('versao', '')
        filial = request.form.get('filial', '')
        operacao = request.form.get('operacao', '')
        rateio = request.form.get('rateio', '')
        origem = request.form.get('origem', '')
        
        # Verifica se pelo menos um filtro foi aplicado
        if not any([n_conta, n_centro_custo, data_inicio, data_fim, versao, filial, operacao, rateio, origem]):
            flash("É necessário aplicar pelo menos um filtro para deletar registros", "error")
            return redirect(url_for('listar_registros'))
        
        # Verifica se o arquivo de credenciais existe
        if not BIGQUERY_CREDENTIALS_PATH.exists():
            flash("Credenciais do BigQuery não encontradas", "error")
            return redirect(url_for('listar_registros'))
            
        # Logs de debug para comparação
        logger.info(f"[DELETAR_FILTROS] Caminho credenciais: {BIGQUERY_CREDENTIALS_PATH}")
        logger.info(f"[DELETAR_FILTROS] Arquivo existe: {BIGQUERY_CREDENTIALS_PATH.exists()}")
        logger.info(f"[DELETAR_FILTROS] Caminho absoluto: {BIGQUERY_CREDENTIALS_PATH.absolute()}")
        logger.info(f"[DELETAR_FILTROS] Executável congelado: {getattr(sys, 'frozen', False)}")
        logger.info(f"[DELETAR_FILTROS] Executável: {sys.executable}")
        logger.info(f"[DELETAR_FILTROS] get_config_path(): {get_config_path()}")
        logger.info(f"[DELETAR_FILTROS] CREDENTIALS_DIR: {CREDENTIALS_DIR}")
            
        # Cria as credenciais a partir do arquivo JSON
        credentials = service_account.Credentials.from_service_account_file(
            BIGQUERY_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        
        # Inicializa o cliente do BigQuery
        client = bigquery.Client(
            project=BIGQUERY_CONFIG.get("project_id", "projeto-teste"),
            credentials=credentials
        )
        
        # Define o ID do dataset e tabela
        dataset_id = BIGQUERY_CONFIG.get("dataset_id", "silver")
        table_id = BIGQUERY_CONFIG.get("table_id", "ORCADO")
        metadata_table_id = BIGQUERY_CONFIG.get("metadata_table_id", "ORCADO_METADATA")
        
        # Primeiro, verifica quantos registros serão afetados
        count_query = f"""
        SELECT COUNT(*) as total
        FROM `{dataset_id}.{table_id}`
        WHERE 1=1
        """
        
        if n_conta:
            count_query += f" AND CAST(N_CONTA AS STRING) = '{n_conta}'"
        if n_centro_custo:
            count_query += f" AND CAST(N_CENTRO_CUSTO AS STRING) = '{n_centro_custo}'"
        if data_inicio:
            count_query += f" AND DATA >= DATE('{data_inicio}')"
        if data_fim:
            count_query += f" AND DATA <= DATE('{data_fim}')"
        if versao:
            count_query += f" AND VERSAO = '{versao}'"
        if filial:
            count_query += f" AND CAST(FILIAL AS STRING) = '{filial}'"
        if operacao:
            count_query += f" AND OPERACAO = '{operacao}'"
        if rateio:
            count_query += f" AND RATEIO = '{rateio}'"
        if origem:
            count_query += f" AND ORIGEM LIKE '%{origem}%'"
        
        # Executa a query de contagem
        count_job = client.query(count_query)
        count_result = count_job.result()
        total_registros = next(count_result).total
        
        if total_registros == 0:
            flash("Nenhum registro encontrado com os filtros aplicados", "warning")
            return redirect(url_for('listar_registros'))
        
        # Constrói a query de deleção com os filtros
        delete_query = f"""
        DELETE FROM `{dataset_id}.{table_id}`
        WHERE 1=1
        """
        
        if n_conta:
            delete_query += f" AND CAST(N_CONTA AS STRING) = '{n_conta}'"
        if n_centro_custo:
            delete_query += f" AND CAST(N_CENTRO_CUSTO AS STRING) = '{n_centro_custo}'"
        if data_inicio:
            delete_query += f" AND DATA >= DATE('{data_inicio}')"
        if data_fim:
            delete_query += f" AND DATA <= DATE('{data_fim}')"
        if versao:
            delete_query += f" AND VERSAO = '{versao}'"
        if filial:
            delete_query += f" AND CAST(FILIAL AS STRING) = '{filial}'"
        if operacao:
            delete_query += f" AND OPERACAO = '{operacao}'"
        if rateio:
            delete_query += f" AND RATEIO = '{rateio}'"
        if origem:
            delete_query += f" AND ORIGEM LIKE '%{origem}%'"
        
        # Executa a query de deleção
        delete_job = client.query(delete_query)
        delete_job.result()
        
        # Registra a deleção nos metadados
        metadata = {
            "DATA_IMPORTACAO": pd.Timestamp.now(),
            "USUARIO": str(getpass.getuser()),
            "SISTEMA_OPERACIONAL": str(platform.system()),
            "VERSAO_SISTEMA": str(platform.version()),
            "ARQUIVO_ORIGEM": f"DELETADO: Filtros aplicados",
            "TOTAL_REGISTROS": total_registros,
            "STATUS": "DELETADO",
            "DETALHES": f"Registros deletados com filtros: Filial={filial}, Conta={n_conta}, Centro Custo={n_centro_custo}, Data Início={data_inicio}, Data Fim={data_fim}, Versão={versao}, Operação={operacao}, Rateio={rateio}, Origem={origem}"
        }
        
        # Cria o DataFrame com tipos explícitos
        df_metadata = pd.DataFrame({
            "DATA_IMPORTACAO": [metadata["DATA_IMPORTACAO"]],
            "USUARIO": [metadata["USUARIO"]],
            "SISTEMA_OPERACIONAL": [metadata["SISTEMA_OPERACIONAL"]],
            "VERSAO_SISTEMA": [metadata["VERSAO_SISTEMA"]],
            "ARQUIVO_ORIGEM": [metadata["ARQUIVO_ORIGEM"]],
            "TOTAL_REGISTROS": [metadata["TOTAL_REGISTROS"]],
            "STATUS": [metadata["STATUS"]],
            "DETALHES": [metadata["DETALHES"]]
        })
        
        # Define o schema da tabela de metadados
        metadata_schema = [
            bigquery.SchemaField("DATA_IMPORTACAO", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("USUARIO", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("SISTEMA_OPERACIONAL", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("VERSAO_SISTEMA", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("ARQUIVO_ORIGEM", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("TOTAL_REGISTROS", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("STATUS", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("DETALHES", "STRING", mode="REQUIRED")
        ]
        
        # Configura o job para os metadados
        metadata_job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
            schema=metadata_schema
        )
        
        # Carrega os metadados
        metadata_table_ref = client.dataset(dataset_id).table(metadata_table_id)
        metadata_job = client.load_table_from_dataframe(
            df_metadata, metadata_table_ref, job_config=metadata_job_config
        )
        metadata_job.result()
        
        flash(f"{total_registros} registros foram deletados com sucesso", "success")
        
    except Exception as e:
        logger.error(f"Erro ao deletar registros por filtros: {str(e)}")
        flash(f"Erro ao deletar registros: {str(e)}", "error")
        
    return redirect(url_for('listar_registros'))

@app.route('/diagnostico_bigquery')
def diagnostico_bigquery():
    """Página de diagnóstico do BigQuery."""
    try:
        # Informações de diagnóstico
        diagnostico = {
            "arquivo_existe": BIGQUERY_CREDENTIALS_PATH.exists(),
            "caminho_arquivo": str(BIGQUERY_CREDENTIALS_PATH),
            "executavel_congelado": getattr(sys, 'frozen', False),
            "executavel": sys.executable,
            "config_path": get_config_path(),
            "data_path": get_data_path()
        }
        
        # Tenta carregar as credenciais
        if BIGQUERY_CREDENTIALS_PATH.exists():
            try:
                with open(BIGQUERY_CREDENTIALS_PATH, 'r', encoding='utf-8') as f:
                    content = f.read()
                    diagnostico["tamanho_arquivo"] = len(content)
                    diagnostico["arquivo_valido"] = True
                    
                    # Verifica campos obrigatórios
                    import json
                    cred_dict = json.loads(content)
                    required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
                    missing_fields = [field for field in required_fields if field not in cred_dict]
                    diagnostico["campos_faltando"] = missing_fields
                    diagnostico["campos_presentes"] = list(cred_dict.keys())
                    
            except Exception as e:
                diagnostico["arquivo_valido"] = False
                diagnostico["erro_leitura"] = str(e)
        else:
            diagnostico["arquivo_valido"] = False
            diagnostico["erro_leitura"] = "Arquivo não encontrado"
        
        return render_template('diagnostico_bigquery.html', diagnostico=diagnostico, now=datetime.now())
    except Exception as e:
        return render_template('diagnostico_bigquery.html', 
                             diagnostico={"erro_geral": str(e)}, 
                             now=datetime.now())

if __name__ == "__main__":
    app.run(debug=True) 