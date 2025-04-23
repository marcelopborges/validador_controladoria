import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import os
import sys
from pathlib import Path
import logging
import datetime
import re
from colorama import Fore, Style, init
import webbrowser
from PIL import Image, ImageTk
import traceback
import platform

# Inicializa colorama para cores (útil para logs no console)
init()

# Adiciona o diretório src ao PYTHONPATH
sys.path.append(str(Path(__file__).parent))

# Importa as funções de transformação
from src.importador_controladoria.transformacoes import transformar_dados

# Configuração de logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/processamento_{datetime.datetime.now().strftime("%Y-%m-%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Cores da interface
COLORS = {
    "primary": "#1a5276",  # Azul escuro
    "secondary": "#2980b9",  # Azul médio
    "accent": "#3498db",  # Azul claro
    "background": "#f5f5f5",  # Cinza claro
    "success": "#27ae60",  # Verde
    "warning": "#f39c12",  # Laranja
    "error": "#c0392b",  # Vermelho
    "text": "#333333",  # Texto escuro
    "light_text": "#ffffff"  # Texto claro
}

class ModernButton(ttk.Button):
    """Botão com estilo moderno"""
    pass

class ImportadorControladoriaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Importador de dados orçados para controladoria v")
        self.root.geometry("1000x700")
        self.root.minsize(900, 650)
        
        # Configuração do tema
        self.estilizar_interface()
        
        # Garante que diretórios necessários existam
        Path("data/processados").mkdir(parents=True, exist_ok=True)
        Path("data/rejeitados").mkdir(parents=True, exist_ok=True)
        
        # Variáveis
        self.arquivo_path = tk.StringVar()
        self.status_texto = tk.StringVar(value="Aguardando seleção de arquivo...")
        self.ano_selecionado = tk.StringVar(value="2024")
        self.versao_selecionada = tk.StringVar(value="V1")
        
        # Cria o layout
        self.criar_layout()
        
    def estilizar_interface(self):
        """Estiliza a interface com cores e fontes modernas"""
        self.style = ttk.Style()
        
        # Configura cores de fundo e fonte
        self.root.configure(bg=COLORS["background"])
        
        # Estilo para os frames
        self.style.configure("TFrame", background=COLORS["background"])
        self.style.configure("Card.TFrame", background="#ffffff", relief="flat", borderwidth=0)
        
        # Estilo para os botões
        self.style.configure("TButton", 
                             font=("Segoe UI", 10),
                             background=COLORS["secondary"],
                             foreground=COLORS["light_text"])
        
        self.style.configure("Accent.TButton", 
                             font=("Segoe UI", 10, "bold"),
                             background=COLORS["accent"],
                             foreground=COLORS["light_text"])
        
        self.style.configure("Success.TButton", 
                             font=("Segoe UI", 10, "bold"),
                             background=COLORS["success"],
                             foreground=COLORS["light_text"])
        
        # Estilo para labels
        self.style.configure("TLabel", 
                             font=("Segoe UI", 10),
                             background=COLORS["background"],
                             foreground=COLORS["text"])
        
        self.style.configure("Title.TLabel", 
                             font=("Segoe UI", 16, "bold"),
                             background=COLORS["background"],
                             foreground=COLORS["primary"])
        
        self.style.configure("Header.TLabel", 
                             font=("Segoe UI", 12, "bold"),
                             background=COLORS["background"],
                             foreground=COLORS["secondary"])
        
        # Estilo para combobox e entry
        self.style.configure("TCombobox", 
                             font=("Segoe UI", 10),
                             background="#ffffff")
        
        self.style.configure("TEntry", 
                             font=("Segoe UI", 10),
                             background="#ffffff")
        
        # Estilo para os frames com título
        self.style.configure("Card.TLabelframe", 
                             font=("Segoe UI", 11, "bold"),
                             background="#ffffff",
                             foreground=COLORS["primary"])
        
        self.style.configure("Card.TLabelframe.Label", 
                             font=("Segoe UI", 11, "bold"),
                             background="#ffffff",
                             foreground=COLORS["primary"])
        
    def criar_layout(self):
        """Cria o layout da interface"""
        # Frame principal usando grid
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # ========= HEADER =========
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Logo e Título
        logo_frame = ttk.Frame(header_frame)
        logo_frame.pack(side=tk.LEFT)
        
        # Tenta carregar o logo se existir
        logo_path = "assets/logo.png"
        if os.path.exists(logo_path):
            try:
                logo_img = Image.open(logo_path)
                logo_img = logo_img.resize((150, 50), Image.LANCZOS)
                self.logo = ImageTk.PhotoImage(logo_img)
                logo_label = ttk.Label(logo_frame, image=self.logo)
                logo_label.pack(side=tk.LEFT, padx=5)
            except Exception as e:
                print(f"Erro ao carregar logo: {e}")
        
        title_label = ttk.Label(header_frame, text="Importador Controladoria", 
                               font=("Helvetica", 16, "bold"))
        title_label.pack(side=tk.LEFT, padx=10)
        
        # Barra de status
        self.status_texto = tk.StringVar()
        self.status_texto.set("Aguardando seleção de arquivo...")
        status_label = ttk.Label(header_frame, textvariable=self.status_texto, 
                               font=("Helvetica", 10))
        status_label.pack(side=tk.RIGHT, padx=10)
        
        # ========= CONTENT =========
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Lado Esquerdo - Seleção e visualização de dados
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Card de Seleção de Arquivo
        selecao_card = ttk.LabelFrame(left_frame, text="Seleção de Arquivo", style="Card.TLabelframe")
        selecao_card.pack(fill=tk.X, padx=5, pady=5)
        
        selecao_frame = ttk.Frame(selecao_card)
        selecao_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.arquivo_path = tk.StringVar()
        arquivo_entry = ttk.Entry(selecao_frame, textvariable=self.arquivo_path, width=50)
        arquivo_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        procurar_button = ttk.Button(selecao_frame, text="Procurar...", 
                                    command=self.selecionar_arquivo)
        procurar_button.pack(side=tk.LEFT)
        
        botoes_frame = ttk.Frame(selecao_card)
        botoes_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        carregar_button = ttk.Button(botoes_frame, text="Carregar", 
                                    command=self.carregar_arquivo_botao)
        carregar_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # Card de Visualização de Dados
        tabela_card = ttk.LabelFrame(left_frame, text="Visualização de Dados", style="Card.TLabelframe")
        tabela_card.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Criar frame para a tabela com scrollbars
        tabela_frame = ttk.Frame(tabela_card)
        tabela_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbars
        y_scrollbar = ttk.Scrollbar(tabela_frame)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        x_scrollbar = ttk.Scrollbar(tabela_frame, orient='horizontal')
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Tabela (Treeview)
        self.tree = ttk.Treeview(tabela_frame, show="headings", 
                               yscrollcommand=y_scrollbar.set,
                               xscrollcommand=x_scrollbar.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        y_scrollbar.config(command=self.tree.yview)
        x_scrollbar.config(command=self.tree.xview)
        
        # Lado Direito - Ações e configurações
        right_frame = ttk.Frame(content_frame, width=200)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        # Card de Configurações
        config_card = ttk.LabelFrame(right_frame, text="Configurações", style="Card.TLabelframe")
        config_card.pack(fill=tk.X, pady=5)
        
        config_frame = ttk.Frame(config_card)
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(config_frame, text="Ano:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.ano_selecionado = tk.StringVar(value="2024")
        anos = ["2023", "2024", "2025", "2026"]
        ano_combo = ttk.Combobox(config_frame, textvariable=self.ano_selecionado, values=anos, state="readonly", width=10)
        ano_combo.grid(row=0, column=1, sticky=tk.W, pady=2)
        
        ttk.Label(config_frame, text="Versão:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.versao_selecionada = tk.StringVar(value="V1")
        versoes = ["V1", "V2", "V3", "V4"]
        versao_combo = ttk.Combobox(config_frame, textvariable=self.versao_selecionada, values=versoes, state="readonly", width=10)
        versao_combo.grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # Card de ações
        acoes_card = ttk.LabelFrame(right_frame, text="Ações", style="Card.TLabelframe")
        acoes_card.pack(fill=tk.X, pady=5)
        
        acoes_frame = ttk.Frame(acoes_card)
        acoes_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(acoes_frame, text="Validar e Processar", 
                   command=self.processar_dados).pack(fill=tk.X, pady=5)
        
        self.botao_salvar = ttk.Button(acoes_frame, text="Salvar Processado", 
                   command=self.salvar_alteracoes)
        self.botao_salvar.pack(fill=tk.X, pady=5)
        
        # Botão para enviar dados para o BigQuery
        self.botao_bigquery = ttk.Button(acoes_frame, text="Exportar Excel/XML", 
                                  command=self.enviar_para_bigquery, state='disabled')
        self.botao_bigquery.pack(fill=tk.X, pady=5)
        
        ttk.Button(acoes_frame, text="Limpar", 
                   command=self.limpar_dados).pack(fill=tk.X, pady=5)
        ttk.Button(acoes_frame, text="Voltar à Tela Inicial", 
                   command=self.reiniciar_aplicacao).pack(fill=tk.X, pady=5)
        ttk.Button(acoes_frame, text="Abrir Documentação", 
                   command=self.abrir_documentacao).pack(fill=tk.X, pady=5)
        ttk.Button(acoes_frame, text="Abrir Arquivo Exemplo", 
                   command=self.abrir_exemplo).pack(fill=tk.X, pady=5)
        
        # Console para exibir resultados e logs
        console_card = ttk.LabelFrame(main_frame, text="Console (Logs e Resultados)", style="Card.TLabelframe")
        console_card.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.console = scrolledtext.ScrolledText(console_card, wrap=tk.WORD, height=10, font=("Consolas", 9))
        self.console.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.console.config(state="disabled")
        
        # Configura as tags de cores para o console
        self.console.tag_config("info", foreground="black")
        self.console.tag_config("error", foreground="red")
        self.console.tag_config("warning", foreground="orange")
        self.console.tag_config("success", foreground="green")
        
        # Rodapé
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill=tk.X, pady=(10, 0))
        
        footer_text = ttk.Label(footer_frame, 
                               text="Importador Controladoria v1.0 - Desenvolvido pelo Departamento de TI")
        footer_text.pack(side=tk.LEFT)
        
        # Log inicial
        self.log_info("Aplicação iniciada. Selecione um arquivo Excel (.xlsx) para começar.")
        
    def selecionar_arquivo(self):
        """Abre o seletor de arquivo para escolher um arquivo Excel."""
        filetypes = [
            ("Arquivos Excel", "*.xlsx *.xls"),
            ("Arquivos CSV", "*.csv"),
            ("Todos os arquivos", "*.*")
        ]
        
        # Mostra que está aguardando seleção
        self.status_texto.set("Aguardando seleção de arquivo...")
        
        arquivo = filedialog.askopenfilename(
            title="Selecione um arquivo Excel ou CSV",
            filetypes=filetypes
        )
        
        if arquivo:
            self.arquivo_path.set(arquivo)
            self.status_texto.set(f"Arquivo selecionado: {os.path.basename(arquivo)}")
            self.log_info(f"Arquivo selecionado: {arquivo}")
            
            # Carrega o arquivo diretamente sem perguntar
            self.carregar_arquivo_botao()
        else:
            self.status_texto.set("Nenhum arquivo selecionado.")
            self.log_info("Operação de seleção de arquivo cancelada pelo usuário.")
    
    def carregar_dados(self):
        """Carrega os dados do arquivo Excel selecionado."""
        arquivo = self.arquivo_path.get()
        if not arquivo:
            messagebox.showwarning("Aviso", "Selecione um arquivo Excel primeiro.")
            return
        
        if not os.path.exists(arquivo):
            messagebox.showerror("Erro", f"Arquivo não encontrado: {arquivo}")
            return
        
        try:
            # Limpa os dados atuais
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Atualiza o status
            self.status_texto.set(f"Carregando arquivo: {os.path.basename(arquivo)}")
            self.log_info(f"Tentando carregar arquivo: {arquivo}")
            
            # Diferencia entre CSV e Excel com base na extensão
            extensao = os.path.splitext(arquivo)[1].lower()
            
            # Variável para armazenar o DataFrame
            df_temp = None
            
            if extensao in ['.xlsx', '.xls']:
                # Carrega arquivo Excel
                df_temp = pd.read_excel(arquivo)
                self.log_info(f"Arquivo Excel carregado: {len(df_temp)} registros.")
                self.log_info(f"Colunas encontradas: {list(df_temp.columns)}")
            elif extensao == '.csv':
                # Carrega arquivo CSV para compatibilidade com versões anteriores
                try:
                    df_temp = pd.read_csv(arquivo, encoding='utf-8')
                except:
                    df_temp = pd.read_csv(arquivo, encoding='latin1')
                self.log_info(f"Arquivo CSV carregado: {len(df_temp)} registros.")
                self.log_info(f"Colunas encontradas: {list(df_temp.columns)}")
            else:
                messagebox.showerror("Erro", f"Formato de arquivo não suportado: {extensao}. Por favor, use arquivos Excel (.xlsx, .xls).")
                return
                
            # Após carregar com sucesso, renomeia colunas se necessário
            if df_temp is not None:
                # Renomeia colunas se necessário, substituindo espaços por underscores
                colunas_renomeadas = {}
                for coluna in df_temp.columns:
                    if ' ' in coluna:
                        nova_coluna = coluna.replace(' ', '_')
                        colunas_renomeadas[coluna] = nova_coluna
                
                if colunas_renomeadas:
                    self.log_info(f"Colunas sendo renomeadas: {colunas_renomeadas}")
                    df_temp = df_temp.rename(columns=colunas_renomeadas)
                    self.log_info(f"Colunas após renomeação: {list(df_temp.columns)}")
                
                # Verifica se todas as colunas necessárias estão presentes
                colunas_necessarias = ["FILIAL", "DATA", "N_CONTA", "N_CENTRO_CUSTO", "VALOR", "DESCRICAO"]
                colunas_faltantes = [col for col in colunas_necessarias if col not in df_temp.columns]
                
                if colunas_faltantes:
                    self.log_error(f"Colunas obrigatórias faltando: {colunas_faltantes}")
                    self.log_info(f"Colunas encontradas: {list(df_temp.columns)}")
                    messagebox.showerror("Erro", f"Colunas obrigatórias faltando no arquivo: {', '.join(colunas_faltantes)}\n"
                                        f"Consulte o formato de arquivo esperado no botão 'Abrir Documentação'.")
                    return
                
                # Atribui o DataFrame carregado à variável da classe
                self.df = df_temp
                
                # Exibe os dados na tabela
                self.mostrar_dados_na_tabela()
                
                # Atualiza o status
                self.status_texto.set(f"Dados carregados: {len(self.df)} linhas")
                self.log_success(f"Dados carregados com sucesso. Total de registros: {len(self.df)}")
            
        except Exception as e:
            self.log_error(f"Erro ao carregar dados: {str(e)}")
            messagebox.showerror("Erro", f"Falha ao carregar o arquivo: {str(e)}")
    
    def mostrar_dados_na_tabela(self):
        """Exibe os dados na tabela (Treeview)."""
        # Limpa a tabela
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        # Configura as colunas
        colunas = list(self.df.columns)
        self.tree["columns"] = colunas
        self.tree["show"] = "headings"  # Oculta a coluna ID
        
        # Atualiza periodicamente a interface para não bloquear
        self.root.update_idletasks()
        
        # Define os cabeçalhos e larguras
        for col in colunas:
            self.tree.heading(col, text=col)
            # Calcula a largura ideal para a coluna (limitado a 10 primeiras linhas)
            amostra = self.df[col].head(10).fillna("")
            max_sample_width = max([len(str(x)) for x in amostra]) if len(amostra) > 0 else 10
            col_width = max(len(str(col)) * 10, max_sample_width * 10)
            col_width = min(col_width, 300)  # Limita a largura máxima
            self.tree.column(col, width=col_width, minwidth=50)
        
        # Atualiza novamente a interface
        self.root.update_idletasks()
            
        # Adiciona os dados (limitado a 1000 linhas para performance)
        row_limit = min(1000, len(self.df))
        if len(self.df) > row_limit:
            self.log_warning(f"Exibindo apenas as primeiras {row_limit} linhas para melhor performance.")
        
        # Para arquivos grandes, apresenta as linhas em lotes para não bloquear a interface
        batch_size = 100  # Processa 100 linhas por vez
        
        for batch_start in range(0, row_limit, batch_size):
            batch_end = min(batch_start + batch_size, row_limit)
            batch = self.df.iloc[batch_start:batch_end]
            
            for i, row in batch.iterrows():
                values = [str(row.get(col, "")) for col in colunas]
                self.tree.insert("", "end", values=values, tags=(f"{i}",))
            
            # Atualiza a interface a cada lote
            self.root.update_idletasks()
            
        # Indica que o carregamento foi concluído
        self.status_texto.set(f"Exibindo {row_limit} de {len(self.df)} linhas")
        self.root.update()
    
    def processar_dados(self):
        """Processa os dados do dataframe e valida."""
        try:
            if self.df is None or self.df.empty:
                messagebox.showerror("Erro", "Não há dados para processar. Por favor, carregue um arquivo primeiro.")
                self.console.insert(tk.END, "Erro: Não há dados para processar.\n")
                return
            
            self.console.insert(tk.END, f"Processando dados... Colunas encontradas: {list(self.df.columns)}\n")
            
            # Não renomeamos colunas aqui para manter a compatibilidade com transformar_dados
            # que já espera colunas com espaços como "N CONTA" e "N CENTRO CUSTO"
            
            # Configurar cursor de espera
            try:
                self.root.config(cursor="watch")
            except:
                # Fallback para sistemas que não suportam "watch"
                pass
            self.root.update()
            
            # Processar dados com a função transformar_dados do módulo transformacoes
            self.console.insert(tk.END, "Aplicando transformações e validações...\n")
            df_transformado, erros = transformar_dados(self.df)
            
            # Verificar se houve erros
            if erros:
                # Habilita a visualização no console
                self.console.config(state="normal")
                
                self.console.insert(tk.END, f"Foram encontrados {len(erros)} erros nos dados:\n", "error")
                
                # Mostra todos os erros no console, não apenas os primeiros 10
                for i, erro in enumerate(erros):
                    if i < 100:  # Limita a 100 erros mostrados diretamente no console para não travar
                        self.console.insert(tk.END, f"- {erro}\n", "error")
                    elif i == 100:
                        self.console.insert(tk.END, f"... e mais {len(erros) - 100} erros. Verifique abaixo o resumo dos problemas.\n", "error")
                        break
                
                # Analisa os erros para fornecer um resumo útil
                resumo = self.analisar_erros(erros)
                
                # Adiciona o resumo ao console
                self.console.insert(tk.END, "\n=== RESUMO DOS ERROS ===\n", "error")
                for tipo, quantidade in resumo.items():
                    self.console.insert(tk.END, f"{tipo}: {quantidade} ocorrências\n", "error")
                self.console.insert(tk.END, "\nCorrija os problemas e tente novamente.\n", "error")
                
                # Volta à posição inicial do console
                self.console.see("1.0")
                
                # Desabilita a edição do console
                self.console.config(state="disabled")
                
                # Registra no log
                self.log_error(f"Processamento falhou: {len(erros)} erros encontrados")
                
                messagebox.showerror("Erros de validação", 
                                    f"Foram encontrados {len(erros)} erros nos dados.\nVerifique o resumo no console da aplicação.")
                
                # Restaurar cursor
                try:
                    self.root.config(cursor="")
                except:
                    pass
                return
            
            # Se não houve erros, atualiza o dataframe e mostra na tabela
            self.df = df_transformado
            self.console.insert(tk.END, "Dados processados com sucesso!\n")
            self.log_success("Dados processados com sucesso!")
            self.mostrar_dados_na_tabela()
            messagebox.showinfo("Sucesso", "Dados processados com sucesso!")
            
            # Habilitar o botão de salvar
            # Procurar o botão na interface
            for widget in self.root.winfo_children():
                if hasattr(widget, 'winfo_children'):
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.Button) and child.winfo_children() and "Salvar" in str(child['text']):
                            child.config(state='normal')
                            break
                            
            # Habilitar o botão de exportação
            self.botao_bigquery.config(state='normal')
        
        except Exception as e:
            self.console.insert(tk.END, f"Erro ao processar dados: {str(e)}\n")
            self.log_error(f"Erro ao processar dados: {str(e)}")
            traceback.print_exc()
            messagebox.showerror("Erro", f"Ocorreu um erro ao processar os dados: {str(e)}")
        finally:
            # Restaurar cursor
            try:
                self.root.config(cursor="")
            except:
                pass
    
    def analisar_erros(self, erros):
        """Analisa a lista de erros e gera um resumo por tipo de erro."""
        resumo = {}
        
        # Padrões comuns de erro para identificar
        padroes = [
            ("Filial inválida", "filial deve"),
            ("Data inválida", "data inválida"),
            ("Número de conta inválido", "número da conta deve"),
            ("Centro de custo inválido", "centro de custo deve"),
            ("Valor inválido", "valor inválido"),
            ("Descrição vazia", "descrição não pode"),
            ("Coluna faltando", "coluna"),
        ]
        
        # Conta ocorrências por tipo
        for erro in erros:
            erro_lower = erro.lower()
            tipo_encontrado = False
            
            for tipo, padrao in padroes:
                if padrao in erro_lower:
                    if tipo not in resumo:
                        resumo[tipo] = 0
                    resumo[tipo] += 1
                    tipo_encontrado = True
                    break
            
            if not tipo_encontrado:
                if "Outro" not in resumo:
                    resumo["Outro"] = 0
                resumo["Outro"] += 1
        
        return resumo
    
    def salvar_alteracoes(self):
        """Salva as alterações em um novo arquivo Excel."""
        if not hasattr(self, 'df') or self.df is None:
            messagebox.showerror("Erro", "Nenhum dado para salvar!")
            return
            
        try:
            # Pede local para salvar
            arquivo_salvar = filedialog.asksaveasfilename(
                title="Salvar arquivo processado",
                defaultextension=".xlsx",
                filetypes=[("Arquivos Excel", "*.xlsx"), ("Todos os arquivos", "*.*")],
                initialdir="data/processados"
            )
            
            if not arquivo_salvar:
                return
                
            # Salva o DataFrame
            self.df.to_excel(arquivo_salvar, index=False)
            
            self.log_success(f"Arquivo salvo com sucesso em: {arquivo_salvar}")
            messagebox.showinfo("Sucesso", f"Arquivo salvo com sucesso em:\n{arquivo_salvar}")
            
        except Exception as e:
            mensagem = f"Erro ao salvar o arquivo: {str(e)}"
            messagebox.showerror("Erro", mensagem)
            self.log_error(mensagem)
    
    def limpar_dados(self):
        """Limpa os dados carregados."""
        # Limpa a tabela
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        # Reseta o DataFrame
        if hasattr(self, 'df'):
            del self.df
            
        # Atualiza o status
        self.status_texto.set("Dados limpos")
        self.log_info("Dados limpos")
    
    def abrir_documentacao(self):
        """Abre o arquivo de documentação de regras."""
        try:
            doc_path = os.path.abspath("REGRAS_VALIDACAO.md")
            if os.path.exists(doc_path):
                if sys.platform == 'win32':
                    os.startfile(doc_path)
                else:
                    # Para Linux e Mac
                    webbrowser.open('file://' + doc_path)
                self.log_info(f"Documentação aberta: {doc_path}")
            else:
                messagebox.showwarning("Aviso", "Arquivo de documentação não encontrado.")
        except Exception as e:
            self.log_error(f"Erro ao abrir documentação: {str(e)}")
    
    def abrir_exemplo(self):
        """Abre o arquivo Excel de exemplo."""
        try:
            exemplo_paths = [
                os.path.abspath("data/modelo_importacao.xlsx"),  # Local padrão
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "modelo_importacao.xlsx")  # Ao lado do executável
            ]
            
            for exemplo_path in exemplo_paths:
                if os.path.exists(exemplo_path):
                    if sys.platform == 'win32':
                        os.startfile(exemplo_path)
                    else:
                        # Para Linux e Mac
                        webbrowser.open('file://' + exemplo_path)
                    self.log_info(f"Arquivo de exemplo aberto: {exemplo_path}")
                    return
                
            # Se nenhum arquivo existir, tenta criar um
            try:
                from criar_excel_exemplo import criar_excel_exemplo
                criar_excel_exemplo()
                if os.path.exists(exemplo_paths[0]):
                    if sys.platform == 'win32':
                        os.startfile(exemplo_paths[0])
                    else:
                        webbrowser.open('file://' + exemplo_paths[0])
                    self.log_info(f"Arquivo de exemplo criado e aberto: {exemplo_paths[0]}")
                    return
            except:
                pass
            
            # Se todas as tentativas falharem
            messagebox.showwarning("Aviso", "Arquivo de exemplo não encontrado. Verifique a pasta 'data'.")
        except Exception as e:
            self.log_error(f"Erro ao abrir arquivo de exemplo: {str(e)}")
    
    def reiniciar_aplicacao(self):
        """Reinicia a aplicação para o estado inicial."""
        self.limpar_dados()
        self.arquivo_path.set("")
        self.status_texto.set("Aguardando seleção de arquivo...")
        self.ano_selecionado.set("2024")
        self.versao_selecionada.set("V1")
        self.log_info("Aplicação reiniciada. Selecione um novo arquivo para começar.")
        messagebox.showinfo("Informação", "Aplicação reiniciada com sucesso!")
    
    def log_info(self, mensagem):
        """Adiciona uma mensagem de informação ao console."""
        self._adicionar_ao_console(mensagem, tag="info")
        logger.info(mensagem)
    
    def log_error(self, mensagem):
        """Adiciona uma mensagem de erro ao console."""
        self._adicionar_ao_console(mensagem, tag="error")
        logger.error(mensagem)
    
    def log_warning(self, mensagem):
        """Adiciona uma mensagem de aviso ao console."""
        self._adicionar_ao_console(mensagem, tag="warning")
        logger.warning(mensagem)
    
    def log_success(self, mensagem):
        """Adiciona uma mensagem de sucesso ao console."""
        self._adicionar_ao_console(mensagem, tag="success")
        logger.info(mensagem)
    
    def _adicionar_ao_console(self, mensagem, tag=None):
        """Adiciona texto ao console com formatação."""
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        texto = f"[{timestamp}] {mensagem}\n"
        
        # Insere o texto com a tag apropriada
        self.console.config(state="normal")
        self.console.insert(tk.END, texto, tag if tag else "info")
        self.console.see(tk.END)  # Rola para o final
        self.console.config(state="disabled")

    def carregar_arquivo_botao(self):
        """Função dedicada para o botão de carregar, com feedback visual."""
        arquivo = self.arquivo_path.get()
        if not arquivo:
            messagebox.showwarning("Aviso", "Selecione um arquivo Excel ou CSV primeiro.")
            return
            
        # Feedback visual
        try:
            self.root.config(cursor="watch")  # Muda o cursor para indicar processamento
        except:
            # Fallback para sistemas que não suportam "watch"
            pass
        self.status_texto.set(f"Carregando arquivo: {os.path.basename(arquivo)}...")
        self.root.update()  # Atualiza a interface para mostrar as mudanças
        
        try:
            # Chama a função de carregamento
            self.carregar_dados()
        except Exception as e:
            self.log_error(f"Erro ao carregar arquivo: {str(e)}")
            messagebox.showerror("Erro", f"Falha ao carregar o arquivo: {str(e)}")
        finally:
            # Restaura o cursor independente do resultado
            try:
                self.root.config(cursor="")
            except:
                pass
            # Forçar atualização da interface para garantir que o cursor seja restaurado
            self.root.update_idletasks()

    def enviar_para_bigquery(self):
        """Salva os dados processados em formatos Excel e XML."""
        try:
            if self.df is None or self.df.empty:
                messagebox.showerror("Erro", "Não há dados para exportar. Por favor, carregue e processe um arquivo primeiro.")
                self.console.insert(tk.END, "Erro: Não há dados para exportar.\n")
                return
            
            # Configura cursor de espera
            try:
                self.root.config(cursor="watch")
            except:
                pass
            self.root.update()
            
            # Habilita visualização no console
            self.console.config(state="normal")
            self.console.insert(tk.END, "Iniciando exportação para Excel e XML...\n")
            self.console.config(state="disabled")
            self.root.update()
            
            # Preparar o DataFrame
            df_exportar = self.df.copy()
            
            # Adiciona informações de versão e data de envio
            ano = self.ano_selecionado.get()
            versao = self.versao_selecionada.get()
            
            df_exportar['ANO'] = ano
            df_exportar['VERSAO'] = versao
            df_exportar['DATA_EXPORTACAO'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            df_exportar['USUARIO'] = os.environ.get('USERNAME', os.environ.get('USER', 'desconhecido'))
            
            # Pergunta o local para salvar os arquivos
            diretorio_salvar = filedialog.askdirectory(
                title="Selecione o diretório para salvar os arquivos",
                initialdir="data/processados"
            )
            
            if not diretorio_salvar:
                self.log_info("Exportação cancelada pelo usuário.")
                
                # Restaura o cursor
                try:
                    self.root.config(cursor="")
                except:
                    pass
                return
            
            # Gera nome de arquivo base com timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_base = f"dados_processados_{timestamp}"
            
            # Caminho para os arquivos
            caminho_excel = os.path.join(diretorio_salvar, f"{nome_base}.xlsx")
            caminho_xml = os.path.join(diretorio_salvar, f"{nome_base}.xml")
            
            # Salva em Excel
            self.log_info(f"Salvando arquivo Excel em: {caminho_excel}")
            df_exportar.to_excel(caminho_excel, index=False)
            
            # Salva em XML
            try:
                self.log_info(f"Salvando arquivo XML em: {caminho_xml}")
                # Converte para XML usando o método to_xml do pandas
                xml_data = df_exportar.to_xml(root_name="Dados", row_name="Registro")
                
                # Salva o XML em arquivo
                with open(caminho_xml, "w", encoding="utf-8") as f:
                    f.write(xml_data)
                
                self.log_success(f"Dados exportados com sucesso para Excel e XML!")
                self.console.config(state="normal")
                self.console.insert(tk.END, f"Dados exportados com sucesso!\n", "success")
                self.console.config(state="disabled")
                
                messagebox.showinfo("Sucesso", f"Dados exportados com sucesso!\n\n" +
                                   f"Excel: {caminho_excel}\n" +
                                   f"XML: {caminho_xml}")
                
            except Exception as e:
                # Se falhar ao gerar XML, tenta um método alternativo
                try:
                    self.log_warning(f"Método to_xml falhou, usando método alternativo: {str(e)}")
                    
                    # Método alternativo usando lxml se disponível
                    import xml.etree.ElementTree as ET
                    
                    # Cria a estrutura XML
                    root = ET.Element("Dados")
                    
                    # Adiciona cada linha como um elemento filho
                    for idx, row in df_exportar.iterrows():
                        registro = ET.SubElement(root, "Registro")
                        
                        # Adiciona cada coluna como um elemento filho do registro
                        for coluna, valor in row.items():
                            elem = ET.SubElement(registro, coluna)
                            elem.text = str(valor)
                    
                    # Cria a árvore XML
                    tree = ET.ElementTree(root)
                    
                    # Salva o XML em arquivo
                    tree.write(caminho_xml, encoding="utf-8", xml_declaration=True)
                    
                    self.log_success(f"Dados exportados com sucesso para Excel e XML!")
                    self.console.config(state="normal")
                    self.console.insert(tk.END, f"Dados exportados com sucesso!\n", "success")
                    self.console.config(state="disabled")
                    
                    messagebox.showinfo("Sucesso", f"Dados exportados com sucesso!\n\n" +
                                       f"Excel: {caminho_excel}\n" +
                                       f"XML: {caminho_xml}")
                    
                except Exception as e2:
                    self.log_error(f"Erro ao salvar arquivo XML: {str(e2)}")
                    self.console.config(state="normal")
                    self.console.insert(tk.END, f"Erro ao gerar XML: {str(e2)}\n", "error")
                    self.console.config(state="disabled")
                    
                    messagebox.showwarning("Atenção", 
                                         f"O arquivo Excel foi salvo com sucesso, mas houve um erro ao gerar o XML.\n\n" +
                                         f"Excel: {caminho_excel}\n\n" +
                                         f"Erro: {str(e2)}")
        
        except Exception as e:
            erro_msg = str(e)
            self.log_error(f"Erro ao exportar dados: {erro_msg}")
            self.console.config(state="normal")
            self.console.insert(tk.END, f"Erro ao exportar dados: {erro_msg}\n", "error")
            self.console.config(state="disabled")
            messagebox.showerror("Erro", f"Ocorreu um erro ao exportar os dados: {erro_msg}")
        
        finally:
            # Restaura o cursor
            try:
                self.root.config(cursor="")
            except:
                pass

def main():
    root = tk.Tk()
    app = ImportadorControladoriaApp(root)
    root.mainloop()

if __name__ == "__main__":
    main() 