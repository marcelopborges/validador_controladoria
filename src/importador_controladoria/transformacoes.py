import pandas as pd
import re
from typing import Tuple

def limpar_texto(texto: str) -> str:
    """Remove acentos, espaços extras e converte para maiúsculas."""
    if pd.isna(texto):
        return texto
    
    # Converte para string caso seja um número
    if isinstance(texto, (int, float)):
        texto = str(texto)
    
    # Remove acentos
    texto = texto.upper()
    texto = texto.replace('Á', 'A').replace('À', 'A').replace('Â', 'A').replace('Ã', 'A')
    texto = texto.replace('É', 'E').replace('È', 'E').replace('Ê', 'E')
    texto = texto.replace('Í', 'I').replace('Ì', 'I').replace('Î', 'I')
    texto = texto.replace('Ó', 'O').replace('Ò', 'O').replace('Ô', 'O').replace('Õ', 'O')
    texto = texto.replace('Ú', 'U').replace('Ù', 'U').replace('Û', 'U')
    texto = texto.replace('Ç', 'C')
    
    # Remove espaços extras
    texto = ' '.join(texto.split())
    
    return texto

def validar_filial(filial: str) -> Tuple[bool, str]:
    """Valida o formato da filial."""
    if pd.isna(filial):
        return False, "Filial não pode ser nula"
    
    # Padroniza a filial para string
    filial_str = str(filial).strip()
    
    # Verifica se parece ser um número de 4 dígitos ou menos
    if filial_str.isdigit() and len(filial_str) <= 4:
        # Preenche com zeros à esquerda até ter 4 dígitos
        filial_str = filial_str.zfill(4)
    else:
        # Extrai apenas os números
        filial_str = re.sub(r'\D', '', filial_str)
        if len(filial_str) != 4:
            return False, "Filial deve ter 4 dígitos"
    
    # Verifica se começa com 01
    if not filial_str.startswith('01'):
        return False, "Filial deve começar com 01"
    
    return True, filial_str

def formatar_data(data: str) -> Tuple[bool, str]:
    """Formata a data para DD/MM/YYYY."""
    if pd.isna(data):
        return False, "Data não pode ser nula"
    
    try:
        # Tenta converter para datetime com dayfirst=True para formato brasileiro (DD/MM/AAAA)
        data_dt = pd.to_datetime(data, dayfirst=True)
        return True, data_dt.strftime('%d/%m/%Y')
    except:
        return False, "Data inválida"

def validar_n_conta(n_conta: str) -> Tuple[bool, int]:
    """Valida o número da conta."""
    if pd.isna(n_conta):
        return False, "Número da conta não pode ser nulo"
    
    # Remove caracteres não numéricos
    numeros = re.sub(r'\D', '', str(n_conta))
    
    if len(numeros) != 8:
        return False, "Número da conta deve ter 8 dígitos"
    
    try:
        return True, int(numeros)
    except:
        return False, "Número da conta inválido"

def validar_centro_custo(centro_custo: str) -> Tuple[bool, int]:
    """Valida o centro de custo."""
    if pd.isna(centro_custo):
        return False, "Centro de custo não pode ser nulo"
    
    # Remove caracteres não numéricos
    numeros = re.sub(r'\D', '', str(centro_custo))
    
    if len(numeros) != 9:
        return False, "Centro de custo deve ter 9 dígitos"
    
    try:
        return True, int(numeros)
    except:
        return False, "Centro de custo inválido"

def validar_operacao(operacao: str) -> Tuple[bool, str]:
    """Valida a operação."""
    if pd.isna(operacao):
        return True, None  # Aceita nulo
    
    operacao = str(operacao).strip().upper()
    if len(operacao) > 10:
        return False, "Operação deve ter no máximo 10 caracteres"
    
    return True, operacao

def validar_valor(valor: str) -> Tuple[bool, float]:
    """Valida o valor."""
    if pd.isna(valor):
        return False, "Valor não pode ser nulo"
    
    try:
        # Remove caracteres não numéricos exceto ponto e vírgula
        valor_limpo = re.sub(r'[^\d.,]', '', str(valor))
        # Substitui vírgula por ponto
        valor_limpo = valor_limpo.replace(',', '.')
        return True, float(valor_limpo)
    except:
        return False, "Valor inválido"

def validar_descricao(descricao: str) -> Tuple[bool, str]:
    """Valida a descrição."""
    if pd.isna(descricao):
        return False, "Descrição não pode ser nula"
    
    return True, limpar_texto(descricao)

def validar_tipo(tipo: str) -> Tuple[bool, str]:
    """Valida o tipo."""
    if pd.isna(tipo):
        return True, "ORCADO"  # Preenche com ORCADO se nulo
    
    tipo = limpar_texto(tipo)
    return True, tipo

def validar_versao(versao: str) -> Tuple[bool, str]:
    """Valida a versão."""
    if pd.isna(versao):
        return False, "Versão não pode ser nula"
    
    versao = limpar_texto(versao)
    # Padrão atualizado para ANO - VERSAO (ex: 2025 - V2)
    if not re.match(r'^\d{4} - V\d+$', versao):
        return False, "Versão deve seguir o padrão 'YYYY - VX'"
    
    return True, versao

def transformar_dados(df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
    """
    Aplica todas as transformações e validações nos dados.
    Se encontrar erros, rejeita o arquivo inteiro e retorna mensagens detalhadas.
    Retorna o DataFrame transformado e uma lista de erros encontrados.
    """
    erros = []
    df_transformado = df.copy()
    
    # Primeiro, converte todos os nomes de colunas para maiúsculas e remove acentos
    df_transformado.columns = [limpar_texto(col) for col in df_transformado.columns]
    
    # Renomeia colunas se necessário, substituindo espaços por underscores
    colunas_padrao = {
        "N CONTA": "N_CONTA",
        "N CENTRO CUSTO": "N_CENTRO_CUSTO"
    }
    
    colunas_a_renomear = {}
    for col_original, col_nova in colunas_padrao.items():
        if col_original in df_transformado.columns:
            colunas_a_renomear[col_original] = col_nova
    
    if colunas_a_renomear:
        df_transformado = df_transformado.rename(columns=colunas_a_renomear)
    
    # Mapeamento de nomes de colunas (suporta tanto com espaço quanto com underscore)
    col_n_conta = "N_CONTA" if "N_CONTA" in df_transformado.columns else "N CONTA"
    col_n_centro_custo = "N_CENTRO_CUSTO" if "N_CENTRO_CUSTO" in df_transformado.columns else "N CENTRO CUSTO"
    
    # Verifica se as colunas necessárias existem
    colunas_necessarias = ['FILIAL', 'DATA', 'VALOR', 'DESCRICAO', 'OPERACAO']
    
    # Adiciona os nomes alternativos das colunas
    if col_n_conta not in colunas_necessarias:
        colunas_necessarias.append(col_n_conta)
    if col_n_centro_custo not in colunas_necessarias:
        colunas_necessarias.append(col_n_centro_custo)
    
    # Verifica se todas as colunas necessárias estão presentes
    colunas_faltantes = [col for col in colunas_necessarias if col not in df_transformado.columns]
    if colunas_faltantes:
        erros.append(f"Colunas obrigatórias faltando: {', '.join(colunas_faltantes)}")
        return df_transformado, erros
    
    # Converte colunas para os tipos corretos
    # Isso evita avisos de tipos incompatíveis durante as atribuições
    df_transformado['FILIAL'] = df_transformado['FILIAL'].astype(str)
    df_transformado['DATA'] = df_transformado['DATA'].astype(str)
    if 'OPERACAO' in df_transformado.columns:
        df_transformado['OPERACAO'] = df_transformado['OPERACAO'].astype(str)
    if 'DESCRICAO' in df_transformado.columns:
        df_transformado['DESCRICAO'] = df_transformado['DESCRICAO'].astype(str)
    
    # Aplica as transformações e validações
    for idx, row in df_transformado.iterrows():
        # FILIAL
        valido, resultado = validar_filial(row['FILIAL'])
        if not valido:
            erros.append(f"Linha {idx+1}: {resultado} - Valor encontrado: '{row['FILIAL']}'. A filial deve ter 4 dígitos iniciando com '01'.")
        else:
            df_transformado.at[idx, 'FILIAL'] = resultado
            
        # DATA
        valido, resultado = formatar_data(row['DATA'])
        if not valido:
            erros.append(f"Linha {idx+1}: {resultado} - Valor encontrado: '{row['DATA']}'. Use o formato DD/MM/YYYY.")
        else:
            df_transformado.at[idx, 'DATA'] = resultado
            
        # N CONTA
        try:
            valor_n_conta = row[col_n_conta]
            valido, resultado = validar_n_conta(valor_n_conta)
            if not valido:
                erros.append(f"Linha {idx+1}: {resultado} - Valor encontrado: '{valor_n_conta}'. O número da conta deve ter 8 dígitos.")
            else:
                df_transformado.at[idx, 'N_CONTA'] = resultado
        except KeyError:
            erros.append(f"Linha {idx+1}: Coluna de número de conta não encontrada - Verifique o nome da coluna (esperado: N_CONTA ou 'N CONTA').")
            
        # N CENTRO CUSTO
        try:
            valor_centro_custo = row[col_n_centro_custo]
            valido, resultado = validar_centro_custo(valor_centro_custo)
            if not valido:
                erros.append(f"Linha {idx+1}: {resultado} - Valor encontrado: '{valor_centro_custo}'. O centro de custo deve ter 9 dígitos.")
            else:
                df_transformado.at[idx, 'N_CENTRO_CUSTO'] = resultado
        except KeyError:
            erros.append(f"Linha {idx+1}: Coluna de centro de custo não encontrada - Verifique o nome da coluna (esperado: N_CENTRO_CUSTO ou 'N CENTRO CUSTO').")
            
        # OPERACAO
        valido, resultado = validar_operacao(row['OPERACAO'])
        if not valido:
            erros.append(f"Linha {idx+1}: {resultado} - Valor encontrado: '{row['OPERACAO']}'. A operação deve ter no máximo 10 caracteres.")
        else:
            df_transformado.at[idx, 'OPERACAO'] = resultado
            
        # VALOR
        valido, resultado = validar_valor(row['VALOR'])
        if not valido:
            erros.append(f"Linha {idx+1}: {resultado} - Valor encontrado: '{row['VALOR']}'. O valor deve ser um número válido.")
        else:
            df_transformado.at[idx, 'VALOR'] = resultado
            
        # DESCRICAO
        if pd.isna(row['DESCRICAO']):
            erros.append(f"Linha {idx+1}: Descrição não pode ser nula")
        else:
            # Garante que seja string e trata a descrição
            if isinstance(row['DESCRICAO'], (int, float)):
                descricao = str(row['DESCRICAO'])
            else:
                descricao = row['DESCRICAO']
                
            # Limita a 100 caracteres
            descricao = limpar_texto(descricao)[:100]
            df_transformado.at[idx, 'DESCRICAO'] = descricao
            
        # Adiciona colunas TIPO e VERSAO se não existirem
        if 'TIPO' not in df_transformado.columns:
            df_transformado.at[idx, 'TIPO'] = 'NORMAL'
            
        if 'VERSAO' not in df_transformado.columns:
            df_transformado.at[idx, 'VERSAO'] = 'V1'
        
    return df_transformado, erros 