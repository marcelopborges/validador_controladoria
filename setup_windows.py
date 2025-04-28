"""
Script para compilar o Importador Controladoria em um executável para Windows.
Utiliza o PyInstaller para gerar o arquivo .exe.

Para executar:
python setup_windows.py

Requisitos:
- PyInstaller: pip install pyinstaller
- Pillow: pip install pillow
- pywin32: pip install pywin32 (opcional, para criar atalho)
- winshell: pip install winshell (opcional, para criar atalho)
"""

import os
import sys
import shutil
import time
from pathlib import Path
from PIL import Image

def verificar_ambiente_windows():
    """Verifica se o ambiente é Windows."""
    if sys.platform != 'win32':
        print("ERRO: Este script deve ser executado em um ambiente Windows!")
        sys.exit(1)

def criar_pastas_necessarias():
    """Cria as pastas necessárias para o funcionamento da aplicação."""
    pastas = [
        "data",
        "data/processados",
        "data/rejeitados",
        "logs",
        "config"
    ]
    
    for pasta in pastas:
        Path(pasta).mkdir(parents=True, exist_ok=True)
        print(f"Pasta criada/verificada: {pasta}")

def limpar_diretorio(caminho):
    """Limpa um diretório com tratamento de erros."""
    try:
        if os.path.exists(caminho):
            print(f"Limpando {caminho}...")
            if os.path.isdir(caminho):
                # Tenta remover arquivos individualmente primeiro
                for item in os.listdir(caminho):
                    item_path = os.path.join(caminho, item)
                    try:
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                    except Exception as e:
                        print(f"Aviso: Não foi possível remover {item_path}: {str(e)}")
                        # Aguarda um pouco e tenta novamente
                        time.sleep(1)
                        try:
                            if os.path.isfile(item_path):
                                os.remove(item_path)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                        except:
                            pass
                
                # Tenta remover o diretório
                try:
                    shutil.rmtree(caminho)
                except:
                    pass
            else:
                os.remove(caminho)
    except Exception as e:
        print(f"Aviso: Não foi possível limpar {caminho}: {str(e)}")

def converter_png_para_ico(png_path, ico_path):
    """Converte um arquivo PNG para ICO."""
    try:
        # Abre a imagem PNG
        img = Image.open(png_path)
        # Converte para modo RGBA se não estiver
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        # Redimensiona para tamanhos comuns de ícone
        icon_sizes = [(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)]
        img.save(ico_path, format='ICO', sizes=icon_sizes)
        return True
    except Exception as e:
        print(f"Erro ao converter ícone: {str(e)}")
        return False

def main():
    try:
        # Verifica se está no Windows
        verificar_ambiente_windows()
        
        # Cria pastas necessárias
        criar_pastas_necessarias()
        
        # Verifica se o PyInstaller está instalado
        try:
            import PyInstaller
        except ImportError:
            print("PyInstaller não encontrado. Instalando...")
            os.system("pip install pyinstaller")
            import PyInstaller
        
        # Verifica se o Pillow está instalado
        try:
            import PIL
        except ImportError:
            print("Pillow não encontrado. Instalando...")
            os.system("pip install pillow")
            import PIL
        
        # Converte o ícone PNG para ICO
        png_path = "icone.png"
        ico_path = "icon.ico"
        if os.path.exists(png_path):
            print("\nConvertendo ícone PNG para ICO...")
            if not converter_png_para_ico(png_path, ico_path):
                print("Erro ao converter ícone. Continuando sem ícone...")
                ico_path = None
        else:
            print(f"Arquivo de ícone {png_path} não encontrado. Continuando sem ícone...")
            ico_path = None

        # Cria pasta dist se não existir
        dist_dir = Path("dist")
        dist_dir.mkdir(exist_ok=True)
        
        # Cria arquivo de exemplo Excel
        print("\nCriando arquivo Excel de exemplo...")
        try:
            from criar_excel_exemplo import criar_excel_exemplo
            criar_excel_exemplo()
        except Exception as e:
            print(f"Erro ao criar arquivo Excel de exemplo: {str(e)}")
        
        # Define nome do arquivo executável
        nome_app = "ImportadorControladoria"
        
        # Limpa diretórios anteriores se existirem
        for dir_to_clean in ["build", "dist", f"{nome_app}.spec"]:
            limpar_diretorio(dir_to_clean)
        
        # Comando para o PyInstaller
        cmd = f"""
        pyinstaller --name="{nome_app}" 
                   --onefile 
                   --windowed 
                   --noconfirm 
                   --clean 
                   --add-data="src;src" 
                   --add-data="REGRAS_VALIDACAO.md;." 
                   --add-data="README.md;." 
                   --add-data="data/modelo_importacao.xlsx;data" 
                   --add-data="data/modelo_importacao.csv;data" 
                   --add-data="config;config"
                   --hidden-import="openpyxl"
                   --hidden-import="xlrd"
                   --hidden-import="pandas"
                   --hidden-import="numpy"
                   --hidden-import="flask"
                   --hidden-import="werkzeug"
                   --hidden-import="jinja2"
                   --hidden-import="markdown"
                   --hidden-import="google.cloud.bigquery"
                   --hidden-import="google.oauth2.service_account"
                   {f'--icon="{ico_path}"' if ico_path else ''}
                   interface_grafica.py
        """
        
        # Remover quebras de linha para o sistema operacional
        cmd = " ".join(line.strip() for line in cmd.splitlines())
        
        print("Iniciando compilação com PyInstaller...")
        print(cmd)
        
        # Executa o comando
        os.system(cmd)
        
        # Verifica se o arquivo foi criado
        exe_path = os.path.join("dist", f"{nome_app}.exe")
        if os.path.exists(exe_path):
            print("\nCompilação concluída com sucesso!")
            print(f"Arquivo executável gerado: {exe_path}")
            
            # Cria pasta de distribuição
            dist_package = Path("dist_package")
            dist_package.mkdir(exist_ok=True)
            
            # Copia o executável
            shutil.copy2(exe_path, dist_package)
            
            # Copia arquivos de documentação
            for doc_file in ["REGRAS_VALIDACAO.md", "README.md"]:
                if os.path.exists(doc_file):
                    shutil.copy2(doc_file, dist_package)
            
            # Cria estrutura de pastas
            for pasta in ["data", "logs", "config"]:
                (dist_package / pasta).mkdir(exist_ok=True)
            
            # Cria subpastas de data
            (dist_package / "data" / "processados").mkdir(exist_ok=True)
            (dist_package / "data" / "rejeitados").mkdir(exist_ok=True)
            
            # Copia arquivos de exemplo para a pasta data
            data_dir = Path("data")
            if data_dir.exists():
                for file in data_dir.glob("*"):
                    if file.is_file():
                        shutil.copy2(file, dist_package / "data")
            
            # Copia arquivo de credenciais se existir
            cred_path = Path("config/bigquery-credentials.json")
            if cred_path.exists():
                shutil.copy2(cred_path, dist_package / "config")
            
            print("Estrutura de pastas e arquivos copiados para o pacote de distribuição")
            
            # Cria arquivo README_INSTALACAO.txt
            with open(os.path.join(dist_package, "README_INSTALACAO.txt"), "w", encoding="utf-8") as f:
                f.write("""
IMPORTADOR CONTROLADORIA
========================

INSTRUÇÕES DE INSTALAÇÃO
------------------------

1. Extraia este pacote para qualquer pasta do seu computador.
2. Execute o arquivo ImportadorControladoria.exe para iniciar o programa.
3. A estrutura de pastas deve ser mantida:
   - data/
     - processados/
     - rejeitados/
   - logs/
   - config/

UTILIZAÇÃO
----------

1. Clique em "Procurar..." para selecionar um arquivo Excel (.xlsx, .xls, .csv).
2. Clique em "Carregar" para visualizar o conteúdo do arquivo.
3. Selecione o Ano e a Versão desejados nos dropdowns do painel lateral.
4. Clique em "Validar e Processar" para aplicar as validações.
5. Se não houver erros, clique em "Salvar Processado" para salvar o arquivo processado.

ARQUIVOS IMPORTANTES
-------------------

- data/modelo_importacao.xlsx: Exemplo de arquivo Excel no formato correto
- REGRAS_VALIDACAO.md: Documentação sobre as regras de validação aplicadas
- config/bigquery-credentials.json: Credenciais do BigQuery (se configurado)

Para mais informações, consulte os arquivos de documentação incluídos.
                """.strip())
            
            print("\nCompilação concluída com sucesso!")
            print(f"Arquivo executável gerado: {dist_package / exe_path.name}")
            print(f"Pacote de distribuição criado em: {dist_package}")
            print("\nCopie o conteúdo da pasta dist_package para distribuir a aplicação.")
            
            # Cria atalho no desktop (apenas no Windows)
            if sys.platform == 'win32':
                try:
                    import winshell
                    from win32com.client import Dispatch
                    
                    desktop = winshell.desktop()
                    path = os.path.join(desktop, f"{nome_app}.lnk")
                    
                    shell = Dispatch('WScript.Shell')
                    shortcut = shell.CreateShortCut(path)
                    shortcut.Targetpath = os.path.abspath(os.path.join(dist_package, os.path.basename(exe_path)))
                    shortcut.WorkingDirectory = os.path.abspath(dist_package)
                    shortcut.IconLocation = os.path.abspath("icon.ico")
                    shortcut.save()
                    
                    print(f"\nAtalho criado no desktop: {path}")
                except ImportError:
                    print("\nPara criar o atalho, instale as dependências:")
                    print("pip install pywin32 winshell")
                except Exception as e:
                    print(f"\nErro ao criar atalho: {str(e)}")
            
        else:
            print(f"Erro: Arquivo {exe_path} não foi gerado.")
            
    except Exception as e:
        print(f"Erro durante a compilação: {str(e)}")

if __name__ == "__main__":
    main() 