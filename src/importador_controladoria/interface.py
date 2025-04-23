import sys
import os
import platform
import getpass
from datetime import datetime
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QPushButton, QFileDialog, QLabel, QProgressBar,
                            QMessageBox, QTextEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from google.cloud import bigquery
from google.oauth2 import service_account
from .main import configurar_contexto_gx, criar_expectations, validar_dados
from .transformacoes import transformar_dados
from .config import BIGQUERY_CREDENTIALS, BIGQUERY_CONFIG

class WorkerThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str, list)
    
    def __init__(self, arquivo_path):
        super().__init__()
        self.arquivo_path = arquivo_path
        
    def run(self):
        try:
            # Carrega os dados
            self.progress.emit(10)
            df = pd.read_excel(self.arquivo_path)
            
            # Aplica transformações e validações
            self.progress.emit(30)
            df_transformado, erros = transformar_dados(df)
            
            if erros:
                self.finished.emit(False, "Erros encontrados durante a transformação", erros)
                return
            
            # Valida os dados com Great Expectations
            self.progress.emit(50)
            context = configurar_contexto_gx()
            criar_expectations(context, df_transformado)
            validar_dados(context, df_transformado)
            
            # Exporta para BigQuery
            self.progress.emit(70)
            self.exportar_para_bigquery(df_transformado)
            
            self.progress.emit(100)
            self.finished.emit(True, "Processo concluído com sucesso!", [])
            
        except Exception as e:
            self.finished.emit(False, f"Erro: {str(e)}", [])
    
    def exportar_para_bigquery(self, df):
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
            df, table_ref, job_config=job_config
        )
        job.result()  # Aguarda a conclusão do job
        
        # Cria e carrega os metadados
        metadata = {
            "data_importacao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "usuario": getpass.getuser(),
            "sistema_operacional": platform.system(),
            "versao_sistema": platform.version(),
            "arquivo_origem": os.path.basename(self.arquivo_path),
            "total_registros": len(df),
            "status": "SUCESSO"
        }
        
        df_metadata = pd.DataFrame([metadata])
        
        # Carrega os metadados
        metadata_table_ref = client.dataset(dataset_id).table(metadata_table_id)
        metadata_job = client.load_table_from_dataframe(
            df_metadata, metadata_table_ref, job_config=job_config
        )
        metadata_job.result()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Importador de Dados - Controladoria")
        self.setMinimumSize(800, 600)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Labels
        self.label_arquivo = QLabel("Nenhum arquivo selecionado")
        
        # Botões
        self.btn_arquivo = QPushButton("Selecionar Arquivo Excel")
        self.btn_processar = QPushButton("Processar")
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        
        # Área de texto para erros
        self.texto_erros = QTextEdit()
        self.texto_erros.setReadOnly(True)
        self.texto_erros.setPlaceholderText("Os erros encontrados serão exibidos aqui...")
        
        # Adiciona widgets ao layout
        layout.addWidget(QLabel("Arquivo Excel:"))
        layout.addWidget(self.btn_arquivo)
        layout.addWidget(self.label_arquivo)
        layout.addSpacing(20)
        
        layout.addWidget(self.btn_processar)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("Erros encontrados:"))
        layout.addWidget(self.texto_erros)
        
        # Conecta os botões aos métodos
        self.btn_arquivo.clicked.connect(self.selecionar_arquivo)
        self.btn_processar.clicked.connect(self.processar)
        
        # Inicializa variáveis
        self.arquivo_path = None
        
    def selecionar_arquivo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Arquivo Excel",
            "",
            "Excel Files (*.xlsx *.xls)"
        )
        if file_path:
            self.arquivo_path = file_path
            self.label_arquivo.setText(os.path.basename(file_path))
    
    def processar(self):
        if not self.arquivo_path:
            QMessageBox.warning(self, "Aviso", "Selecione um arquivo Excel!")
            return
        
        # Limpa a área de erros
        self.texto_erros.clear()
        
        # Desabilita os botões durante o processamento
        self.btn_processar.setEnabled(False)
        self.btn_arquivo.setEnabled(False)
        
        # Inicia a thread de processamento
        self.worker = WorkerThread(self.arquivo_path)
        self.worker.progress.connect(self.atualizar_progresso)
        self.worker.finished.connect(self.processamento_finalizado)
        self.worker.start()
    
    def atualizar_progresso(self, valor):
        self.progress_bar.setValue(valor)
    
    def processamento_finalizado(self, sucesso, mensagem, erros):
        # Reabilita os botões
        self.btn_processar.setEnabled(True)
        self.btn_arquivo.setEnabled(True)
        
        # Mostra erros se houver
        if erros:
            self.texto_erros.setText("\n".join(erros))
        
        # Mostra mensagem de resultado
        if sucesso:
            QMessageBox.information(self, "Sucesso", mensagem)
        else:
            QMessageBox.critical(self, "Erro", mensagem)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 