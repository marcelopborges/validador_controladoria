"""
Script para compilar o Importador Controladoria em um executável para Windows.
Utiliza o PyInstaller para gerar o arquivo .exe.

Para executar:
python setup_windows.py

Requisitos:
- PyInstaller: pip install pyinstaller
- Pillow: pip install pillow
"""

import os
import sys
import shutil
from pathlib import Path
from PIL import Image

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
        png_path = "@icone.png"
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
            if os.path.exists(dir_to_clean):
                print(f"Limpando {dir_to_clean}...")
                if os.path.isdir(dir_to_clean):
                    shutil.rmtree(dir_to_clean)
                else:
                    os.remove(dir_to_clean)
        
        # Comando para o PyInstaller
        cmd = f"""
        pyinstaller --name="{nome_app}" 
                   --onefile 
                   --windowed 
                   --noconfirm 
                   --clean 
                   --add-data="src:src" 
                   --add-data="REGRAS_VALIDACAO.md:." 
                   --add-data="README.md:." 
                   --hidden-import="openpyxl"
                   --hidden-import="xlrd"
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
            
            # Copia arquivo de exemplo
            if os.path.exists("data/modelo_importacao.xlsx"):
                shutil.copy2("data/modelo_importacao.xlsx", dist_package)
            
            # Cria arquivo README_INSTALACAO.txt
            with open(os.path.join(dist_package, "README_INSTALACAO.txt"), "w", encoding="utf-8") as f:
                f.write("""
IMPORTADOR CONTROLADORIA
========================

INSTRUÇÕES DE INSTALAÇÃO
------------------------

1. Extraia este pacote para qualquer pasta do seu computador.
2. Execute o arquivo ImportadorControladoria.exe para iniciar o programa.
3. As pastas data, logs, data/processados e data/rejeitados são necessárias para o funcionamento.
   Não remova essas pastas.

UTILIZAÇÃO
----------

1. Clique em "Procurar..." para selecionar um arquivo Excel (.xlsx, .xls, .csv).
2. Clique em "Carregar" para visualizar o conteúdo do arquivo.
3. Selecione o Ano e a Versão desejados nos dropdowns do painel lateral.
4. Clique em "Validar e Processar" para aplicar as validações.
5. Se não houver erros, clique em "Salvar Processado" para salvar o arquivo processado.

ARQUIVOS IMPORTANTES
-------------------

- modelo_importacao.xlsx: Exemplo de arquivo Excel no formato correto
- REGRAS_VALIDACAO.md: Documentação sobre as regras de validação aplicadas

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