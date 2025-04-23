"""
Script para compilar o Importador Controladoria em um executável para Windows.
Utiliza o PyInstaller para gerar o arquivo .exe.

Para executar:
python setup.py

Requisitos:
- PyInstaller: pip install pyinstaller
"""

import os
import sys
import shutil
from pathlib import Path

def main():
    try:
        # Verifica se o PyInstaller está instalado
        try:
            import PyInstaller
        except ImportError:
            print("PyInstaller não encontrado. Instalando...")
            os.system("uv pip install pyinstaller")
            # Tenta importar novamente para verificar se foi instalado
            import PyInstaller
        
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
                   --add-data="src;src" 
                   --add-data="REGRAS_VALIDACAO.md;." 
                   --add-data="FORMATO_EXCEL.md;." 
                   --add-data="README.md;." 
                   --hidden-import="openpyxl"
                   --hidden-import="xlrd"
                   --icon=icon.ico 
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
            # Cria diretórios para o pacote final
            dist_package = Path("dist_package")
            dist_package.mkdir(exist_ok=True)
            
            # Copia o executável para a pasta do pacote
            shutil.copy(exe_path, dist_package)
            
            # Cria diretórios necessários para funcionamento
            for dir_name in ["data", "data/processados", "data/rejeitados", "logs"]:
                Path(os.path.join(dist_package, dir_name)).mkdir(exist_ok=True)
            
            # Copia alguns arquivos de exemplo para facilitar o uso
            if os.path.exists("data/modelo_importacao.xlsx"):
                shutil.copy("data/modelo_importacao.xlsx", os.path.join(dist_package, "data"))
            
            if os.path.exists("FORMATO_EXCEL.md"):
                shutil.copy("FORMATO_EXCEL.md", dist_package)
            
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

1. Clique em "Procurar..." para selecionar um arquivo Excel (.xlsx, .xls).
2. Clique em "Carregar" para visualizar o conteúdo do arquivo.
3. Selecione o Ano e a Versão desejados nos dropdowns do painel lateral.
4. Clique em "Validar e Processar" para aplicar as validações.
5. Se não houver erros, clique em "Salvar Processado" para salvar o arquivo processado.

ARQUIVOS IMPORTANTES
-------------------

- modelo_importacao.xlsx: Exemplo de arquivo Excel no formato correto
- FORMATO_EXCEL.md: Documentação detalhada sobre o formato esperado dos arquivos
- REGRAS_VALIDACAO.md: Documentação sobre as regras de validação aplicadas

Para mais informações, consulte os arquivos de documentação incluídos.
                """.strip())
            
            print("\nCompilação concluída com sucesso!")
            print(f"Arquivo executável gerado: {dist_package / exe_path.name}")
            print(f"Pacote de distribuição criado em: {dist_package}")
            print("\nCopie o conteúdo da pasta dist_package para distribuir a aplicação.")
            
        else:
            print(f"Erro: Arquivo {exe_path} não foi gerado.")
            
    except Exception as e:
        print(f"Erro durante a compilação: {str(e)}")
        
if __name__ == "__main__":
    main() 