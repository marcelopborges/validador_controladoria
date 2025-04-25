import sys
import os
import platform
import getpass
from datetime import datetime
import pandas as pd
import threading
from google.cloud import bigquery
from google.oauth2 import service_account
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

from .transformacoes import transformar_dados
from .config import BIGQUERY_CONFIG

# Configuração do Flask
app = Flask(__name__, 
    template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.secret_key = str(uuid.uuid4())
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))
    except Exception as e:
        logger.error(f"Erro ao determinar caminho da pasta data: {str(e)}")
        # Fallback para o caminho de desenvolvimento
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data"))

PROCESSED_DIR = Path(get_data_path()) / "processados"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
CREDENTIALS_DIR = Path(__file__).parent.parent.parent / "config"

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
                self.finalizar(True, f"Processo concluído com sucesso! Arquivos salvos em {PROCESSED_DIR} (BigQuery não configurado)", [])
            
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
            # Verifica se o arquivo de credenciais existe
            if not BIGQUERY_CREDENTIALS_PATH.exists():
                logger.warning(f"Arquivo de credenciais do BigQuery não encontrado em: {BIGQUERY_CREDENTIALS_PATH}")
                self.atualizar_etapa("upload", completed=True, message="Exportação para BigQuery pulada (credenciais não encontradas)")
                return True
                
            # Limpa os dados para remover valores nulos ou problemáticos
            # Substitui None por string vazia em todas as colunas de texto
            for col in df.select_dtypes(include=['object']).columns:
                df[col] = df[col].fillna('')
            
            # Substitui None por 0 em colunas numéricas
            for col in df.select_dtypes(include=['number']).columns:
                df[col] = df[col].fillna(0)
                
            # Garante que a coluna OPERACAO está preenchida
            if 'OPERACAO' in df.columns:
                df['OPERACAO'] = df['OPERACAO'].fillna('')
                
            logger.info(f"Dados limpos para BigQuery. Shape: {df.shape}")
            logger.info(f"Colunas do DataFrame: {df.columns.tolist()}")
            
            # Mapeia as colunas do DataFrame para o schema do BigQuery
            df_bigquery = pd.DataFrame()
            
            # Log das colunas originais
            logger.info(f"Colunas originais do DataFrame: {df.columns.tolist()}")
            
            # Converte todas as colunas para maiúsculo
            df.columns = [col.upper() for col in df.columns]
            logger.info(f"Colunas convertidas para maiúsculo: {df.columns.tolist()}")
            
            # Cria o DataFrame df_bigquery com as colunas corretas
            df_bigquery = pd.DataFrame({
                'N_CONTA': df['N_CONTA'].astype(str) if 'N_CONTA' in df.columns else df['N CONTA'].astype(str),
                'N_CENTRO_CUSTO': df['N_CENTRO_CUSTO'].astype(str) if 'N_CENTRO_CUSTO' in df.columns else df['N CENTRO CUSTO'].astype(str),
                'DESCRICAO': df['DESCRICAO'].astype(str) if 'DESCRICAO' in df.columns else df['descricao'].astype(str),
                'VALOR': df['VALOR'].astype(float) if 'VALOR' in df.columns else df['valor'].astype(float),
                'DATA': pd.to_datetime(df['DATA']).dt.date if 'DATA' in df.columns else pd.to_datetime(df['data']).dt.date,
                'VERSAO': df['VERSAO'].astype(str) if 'VERSAO' in df.columns else df['versao'].astype(str),
                'DATA_ATUALIZACAO': pd.Timestamp.now()
            })
            
            logger.info(f"Dados mapeados para BigQuery. Shape: {df_bigquery.shape}")
            logger.info(f"Colunas do DataFrame original: {df.columns.tolist()}")
            logger.info(f"Colunas do DataFrame BigQuery: {df_bigquery.columns.tolist()}")
            
            # Verifica se todas as colunas necessárias estão presentes
            colunas_necessarias = ['N_CONTA', 'N_CENTRO_CUSTO', 'DESCRICAO', 'VALOR', 'DATA', 'VERSAO', 'DATA_ATUALIZACAO']
            colunas_faltantes = [col for col in colunas_necessarias if col not in df_bigquery.columns]
            if colunas_faltantes:
                logger.error(f"Colunas faltando no DataFrame BigQuery: {colunas_faltantes}")
                self.atualizar_etapa("upload", error=True, message=f"Erro: Colunas faltando no DataFrame BigQuery: {colunas_faltantes}")
                return False
            
            # Verifica se há dados no DataFrame
            if df_bigquery.empty:
                logger.error("DataFrame BigQuery está vazio")
                self.atualizar_etapa("upload", error=True, message="Erro: DataFrame BigQuery está vazio")
                return False
                
            # Verifica se há valores nulos
            for col in df_bigquery.columns:
                nulos = df_bigquery[col].isnull().sum()
                if nulos > 0:
                    logger.error(f"Coluna {col} tem {nulos} valores nulos")
                    self.atualizar_etapa("upload", error=True, message=f"Erro: Coluna {col} tem {nulos} valores nulos")
                    return False
            
            # Cria as credenciais a partir do arquivo JSON
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    BIGQUERY_CREDENTIALS_PATH,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                logger.info("Credenciais do BigQuery carregadas com sucesso")
            except Exception as e:
                logger.error(f"Erro ao carregar credenciais do BigQuery: {str(e)}")
                self.atualizar_etapa("upload", error=True, message=f"Erro ao carregar credenciais do BigQuery: {str(e)}")
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
                self.atualizar_etapa("upload", error=True, message=f"Erro ao inicializar cliente BigQuery: {str(e)}")
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
                bigquery.SchemaField("DATA_ATUALIZACAO", "TIMESTAMP", mode="REQUIRED")
            ]
            
            # Verifica se o dataset existe
            try:
                client.get_dataset(dataset_id)
                logger.info(f"Dataset {dataset_id} encontrado")
            except Exception as e:
                logger.error(f"Dataset {dataset_id} não encontrado: {str(e)}")
                self.atualizar_etapa("upload", error=True, message=f"Dataset {dataset_id} não encontrado. Verifique as configurações.")
                return False
            
            # Verifica se a tabela existe
            table_ref = client.dataset(dataset_id).table(table_id)
            try:
                table = client.get_table(table_ref)
                logger.info(f"Tabela {table_id} encontrada")
                
                # Verifica se o schema está correto
                schema_atual = [field.name for field in table.schema]
                schema_esperado = ['N_CONTA', 'N_CENTRO_CUSTO', 'DESCRICAO', 'VALOR', 'DATA', 'VERSAO', 'DATA_ATUALIZACAO']
                
                if set(schema_atual) != set(schema_esperado):
                    logger.warning(f"Schema da tabela {table_id} não está correto. Recriando tabela...")
                    client.delete_table(table_ref)
                    raise Exception("Schema incorreto")
                    
            except Exception as e:
                logger.info(f"Criando tabela {table_id} com schema correto...")
                # Cria a tabela com o schema correto
                table = bigquery.Table(table_ref, schema=schema)
                table = client.create_table(table)
                logger.info(f"Tabela {table_id} criada com sucesso")
            
            # Cria uma tabela temporária para os novos dados
            temp_table_id = f"temp_{table_id}_{int(time.time())}"
            temp_table_ref = client.dataset(dataset_id).table(temp_table_id)
            
            try:
                # Configura o job para a tabela temporária
                job_config = bigquery.LoadJobConfig(
                    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                    schema=schema
                )
                
                # Carrega os dados na tabela temporária
                job = client.load_table_from_dataframe(
                    df_bigquery, temp_table_ref, job_config=job_config
                )
                job.result()  # Aguarda a conclusão do job
                
                # Query para fazer o merge dos dados
                merge_query = f"""
                MERGE `{dataset_id}.{table_id}` T
                USING (
                    SELECT 
                        N_CONTA,
                        N_CENTRO_CUSTO,
                        DATA,
                        DESCRICAO,
                        VALOR,
                        VERSAO,
                        CURRENT_TIMESTAMP() as DATA_ATUALIZACAO
                    FROM `{dataset_id}.{temp_table_id}`
                    QUALIFY ROW_NUMBER() OVER (
                        PARTITION BY N_CONTA, N_CENTRO_CUSTO, DATA, VERSAO 
                        ORDER BY DATA_ATUALIZACAO DESC
                    ) = 1
                ) S
                ON T.N_CONTA = S.N_CONTA 
                AND T.N_CENTRO_CUSTO = S.N_CENTRO_CUSTO 
                AND T.DATA = S.DATA
                AND T.VERSAO = S.VERSAO
                WHEN MATCHED THEN
                    UPDATE SET
                        DESCRICAO = S.DESCRICAO,
                        VALOR = S.VALOR,
                        DATA_ATUALIZACAO = CURRENT_TIMESTAMP()
                WHEN NOT MATCHED THEN
                    INSERT (N_CONTA, N_CENTRO_CUSTO, DESCRICAO, VALOR, DATA, VERSAO, DATA_ATUALIZACAO)
                    VALUES (S.N_CONTA, S.N_CENTRO_CUSTO, S.DESCRICAO, S.VALOR, S.DATA, S.VERSAO, CURRENT_TIMESTAMP())
                """
                
                # Executa o merge
                query_job = client.query(merge_query)
                query_job.result()
                
            finally:
                # Garante que a tabela temporária seja removida mesmo em caso de erro
                try:
                    client.delete_table(temp_table_ref)
                    logger.info(f"Tabela temporária {temp_table_id} removida com sucesso")
                except Exception as e:
                    logger.error(f"Erro ao remover tabela temporária {temp_table_id}: {str(e)}")
            
            # Limpa tabelas temporárias antigas (mais de 1 hora)
            try:
                cleanup_query = f"""
                DELETE FROM `{dataset_id}.__TABLES__`
                WHERE table_id LIKE 'temp_{table_id}_%'
                AND creation_time < TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
                """
                client.query(cleanup_query).result()
                logger.info("Limpeza de tabelas temporárias antigas concluída")
            except Exception as e:
                logger.error(f"Erro ao limpar tabelas temporárias antigas: {str(e)}")
            
            # Cria e carrega os metadados
            metadata = {
                "DATA_IMPORTACAO": pd.Timestamp.now(),
                "USUARIO": str(getpass.getuser()),
                "SISTEMA_OPERACIONAL": str(platform.system()),
                "VERSAO_SISTEMA": str(platform.version()),
                "ARQUIVO_ORIGEM": str(os.path.basename(self.arquivo_path)),
                "TOTAL_REGISTROS": int(len(df)),
                "STATUS": "SUCESSO"
            }
            
            # Cria o DataFrame com tipos explícitos
            df_metadata = pd.DataFrame({
                "DATA_IMPORTACAO": [metadata["DATA_IMPORTACAO"]],
                "USUARIO": [metadata["USUARIO"]],
                "SISTEMA_OPERACIONAL": [metadata["SISTEMA_OPERACIONAL"]],
                "VERSAO_SISTEMA": [metadata["VERSAO_SISTEMA"]],
                "ARQUIVO_ORIGEM": [metadata["ARQUIVO_ORIGEM"]],
                "TOTAL_REGISTROS": [metadata["TOTAL_REGISTROS"]],
                "STATUS": [metadata["STATUS"]]
            })
            
            # Define o schema da tabela de metadados
            metadata_schema = [
                bigquery.SchemaField("DATA_IMPORTACAO", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("USUARIO", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("SISTEMA_OPERACIONAL", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("VERSAO_SISTEMA", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("ARQUIVO_ORIGEM", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("TOTAL_REGISTROS", "INTEGER", mode="REQUIRED"),
                bigquery.SchemaField("STATUS", "STRING", mode="REQUIRED")
            ]
            
            # Carrega os metadados
            metadata_table_ref = client.dataset(dataset_id).table(metadata_table_id)
            
            # Verifica se a tabela de metadados existe
            try:
                metadata_table = client.get_table(metadata_table_ref)
                logger.info(f"Tabela de metadados {metadata_table_id} encontrada")
            except Exception as e:
                logger.info(f"Criando tabela de metadados {metadata_table_id}...")
                metadata_table = bigquery.Table(metadata_table_ref, schema=metadata_schema)
                metadata_table = client.create_table(metadata_table)
                logger.info(f"Tabela de metadados {metadata_table_id} criada com sucesso")
            
            # Configura o job para os metadados
            metadata_job_config = bigquery.LoadJobConfig(
                write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
                schema=metadata_schema
            )
            
            # Carrega os metadados
            metadata_job = client.load_table_from_dataframe(
                df_metadata, metadata_table_ref, job_config=metadata_job_config
            )
            metadata_job.result()
            
            self.atualizar_etapa("upload", completed=True, message="Dados exportados com sucesso para o BigQuery")
            logger.info("Dados exportados com sucesso para o BigQuery")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao exportar para BigQuery: {str(e)}")
            self.atualizar_etapa("upload", error=True, message=f"Erro ao exportar para BigQuery: {str(e)}")
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
    """Rota para download do arquivo de exemplo."""
    try:
        # Obtém o caminho da pasta data
        data_path = get_data_path()
        arquivo_exemplo = os.path.join(data_path, "modelo_importacao.xlsx")
        
        logger.info(f"Procurando arquivo de exemplo em: {arquivo_exemplo}")
        
        if not os.path.exists(arquivo_exemplo):
            logger.error(f"Arquivo de exemplo não encontrado em: {arquivo_exemplo}")
            flash("Arquivo de exemplo não encontrado", "error")
            return redirect(url_for('index'))
        
        logger.info(f"Enviando arquivo de exemplo: {arquivo_exemplo}")
        
        # Retorna o arquivo para download
        return send_file(
            arquivo_exemplo,
            as_attachment=True,
            download_name="modelo_importacao.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        logger.error(f"Erro ao gerar arquivo de exemplo: {str(e)}")
        flash("Erro ao gerar arquivo de exemplo", "error")
        return redirect(url_for('index'))

def processar_em_linha_de_comando(arquivo_path):
    """Processa um arquivo no modo de linha de comando."""
    try:
        print(f"Processando arquivo: {arquivo_path}")
        
        # Carrega os dados
        print("Carregando dados do Excel...")
        df = pd.read_excel(arquivo_path)
        
        # Aplica transformações
        print("Aplicando transformações...")
        df_transformado, erros = transformar_dados(df)
        
        if erros:
            print("Erros encontrados durante a transformação:")
            for erro in erros:
                print(f"- {erro}")
            return
        
        # Valida os dados com Great Expectations
        print("Validando dados com Great Expectations...")
        context = configurar_contexto_gx()
        criar_expectations(context, df_transformado)
        resultado = validar_dados(context, df_transformado)
        
        if not resultado:
            print("Erros encontrados na validação. Processo interrompido.")
            return
        
        # Exporta para BigQuery
        print("Exportando para BigQuery...")
        
        # Cria as credenciais a partir do dicionário
        credentials = service_account.Credentials.from_service_account_info(
            BIGQUERY_CREDENTIALS,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        
        # Inicializa o cliente do BigQuery
        client = bigquery.Client(credentials=credentials)
        
        # Define o ID do dataset e tabela
        dataset_id = BIGQUERY_CONFIG["dataset_id"]
        table_id = BIGQUERY_CONFIG["table_id"]
        metadata_table_id = BIGQUERY_CONFIG["metadata_table_id"]
        
        # Cria o job de carga para os dados
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            autodetect=True
        )
        
        # Carrega os dados
        table_ref = client.dataset(dataset_id).table(table_id)
        job = client.load_table_from_dataframe(
            df_transformado, table_ref, job_config=job_config
        )
        job.result()  # Aguarda a conclusão do job
        
        # Cria e carrega os metadados
        metadata = {
            "data_importacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "usuario": getpass.getuser(),
            "sistema_operacional": platform.system(),
            "versao_sistema": platform.version(),
            "arquivo_origem": os.path.basename(arquivo_path),
            "total_registros": len(df_transformado),
            "status": "SUCESSO"
        }
        
        df_metadata = pd.DataFrame([metadata])
        
        # Carrega os metadados
        metadata_table_ref = client.dataset(dataset_id).table(metadata_table_id)
        metadata_job = client.load_table_from_dataframe(
            df_metadata, metadata_table_ref, job_config=job_config
        )
        metadata_job.result()
        
        print("Processo concluído com sucesso!")
        
    except Exception as e:
        print(f"Erro durante o processamento: {str(e)}")
        raise

def open_browser():
    """Abre o navegador no endereço do Flask."""
    webbrowser.open('http://localhost:5000/')

def main():
    # Verificar argumentos de linha de comando
    if len(sys.argv) > 1:
        # Modo linha de comando
        arquivo_path = sys.argv[1]
        if os.path.exists(arquivo_path):
            processar_em_linha_de_comando(arquivo_path)
        else:
            print(f"Erro: O arquivo {arquivo_path} não existe.")
    else:
        # Modo interface web
        print("Iniciando servidor web na porta 5000...")
        print("Acesse http://localhost:5000 no seu navegador")
        # Abre o navegador após 1.5 segundos (tempo para o servidor iniciar)
        Timer(1.5, open_browser).start()
        app.run(debug=False, host='0.0.0.0', port=5000)

if __name__ == "__main__":
    main() 