import pandas as pd
import sys
import os
from pathlib import Path
import logging
from colorama import Fore, Style, init

# Inicializa o colorama para cores no terminal
init()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/processamento.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Adiciona o diretório src ao PYTHONPATH
sys.path.append(str(Path(__file__).parent))

# Importa as funções de transformação
from src.importador_controladoria.transformacoes import transformar_dados

def processar_arquivo(arquivo: str) -> bool:
    """
    Processa um arquivo CSV e valida os dados.
    Se encontrar erros, rejeita o arquivo inteiro e retorna False.
    Caso contrário, transforma os dados e retorna True.
    """
    try:
        # Cria diretórios se não existirem
        Path("logs").mkdir(exist_ok=True)
        Path("data/processados").mkdir(parents=True, exist_ok=True)
        Path("data/rejeitados").mkdir(parents=True, exist_ok=True)
        
        # Carrega o arquivo
        logger.info(f"Processando arquivo: {arquivo}")
        df = pd.read_csv(arquivo)
        
        # Aplica transformações e validações
        df_transformado, erros = transformar_dados(df)
        
        # Se houver erros, rejeita o arquivo
        if erros:
            logger.error(f"Arquivo rejeitado: {arquivo}")
            logger.error(f"Encontrado(s) {len(erros)} erro(s).")
            
            # Copia arquivo para pasta de rejeitados
            nome_arquivo = os.path.basename(arquivo)
            arquivo_rejeitado = f"data/rejeitados/{nome_arquivo}"
            df.to_csv(arquivo_rejeitado, index=False)
            
            # Exibe relatório detalhado dos erros
            print(f"\n{Fore.RED}ARQUIVO REJEITADO{Style.RESET_ALL}: {arquivo}")
            print(f"{Fore.RED}Encontrado(s) {len(erros)} erro(s). Corrija os problemas abaixo:{Style.RESET_ALL}\n")
            
            # Agrupa erros por tipo para melhor visualização
            erros_por_tipo = {}
            for erro in erros:
                tipo_erro = erro.split(':')[1].split('-')[0].strip()
                if tipo_erro not in erros_por_tipo:
                    erros_por_tipo[tipo_erro] = []
                erros_por_tipo[tipo_erro].append(erro)
            
            # Exibe erros por tipo
            for tipo, lista_erros in erros_por_tipo.items():
                print(f"{Fore.YELLOW}Problemas de {tipo}:{Style.RESET_ALL}")
                for erro in lista_erros:
                    print(f"  {erro}")
                print()
            
            print(f"\n{Fore.YELLOW}AÇÃO NECESSÁRIA:{Style.RESET_ALL} Corrija os erros e tente novamente.")
            print(f"Uma cópia do arquivo foi salva em: {arquivo_rejeitado}\n")
            
            return False
        
        # Se não houver erros, salva o arquivo processado
        logger.info(f"Arquivo processado com sucesso: {arquivo}")
        nome_arquivo = os.path.basename(arquivo)
        arquivo_processado = f"data/processados/{nome_arquivo}"
        df_transformado.to_csv(arquivo_processado, index=False)
        
        # Resumo do processamento
        print(f"\n{Fore.GREEN}ARQUIVO PROCESSADO COM SUCESSO{Style.RESET_ALL}: {arquivo}")
        print(f"Linhas processadas: {len(df)}")
        print(f"Arquivo transformado salvo em: {arquivo_processado}\n")
        
        return True
        
    except Exception as e:
        logger.error(f"Erro ao processar arquivo {arquivo}: {str(e)}")
        print(f"\n{Fore.RED}ERRO NO PROCESSAMENTO{Style.RESET_ALL}: {str(e)}")
        return False

def main():
    """Função principal"""
    # Verifica se foi passado um arquivo como argumento
    if len(sys.argv) < 2:
        print(f"\n{Fore.YELLOW}Uso:{Style.RESET_ALL} python processar_arquivo.py <caminho_do_arquivo>")
        print(f"Exemplo: python processar_arquivo.py data/dados_teste.csv\n")
        return
    
    # Processa o arquivo
    arquivo = sys.argv[1]
    if not os.path.exists(arquivo):
        print(f"\n{Fore.RED}ERRO:{Style.RESET_ALL} Arquivo não encontrado: {arquivo}\n")
        return
    
    processar_arquivo(arquivo)

if __name__ == "__main__":
    main() 