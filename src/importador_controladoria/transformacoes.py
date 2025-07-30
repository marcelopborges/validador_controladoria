import pandas as pd
import re
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

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
    """
    Valida e transforma a filial.
    
    Args:
        filial: String com a filial a ser validada
        
    Returns:
        Tuple contendo:
        - bool: True se a filial é válida, False caso contrário
        - str: Filial transformada ou mensagem de erro
    """
    if pd.isna(filial) or filial == '':
        return False, "Filial não pode ser vazia"
    
    # Converte para string e remove espaços extras
    filial = str(filial).strip()
    
    # Se for número, converte para string com zeros à esquerda
    if filial.isdigit():
        filial = filial.zfill(4)
    
    # Verifica se tem 4 dígitos
    if not filial.isdigit() or len(filial) != 4:
        return False, "Filial deve ter 4 dígitos"
    
    return True, filial

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

def validar_centro_custo(centro_custo: str, n_conta: str) -> Tuple[bool, int]:
    """Valida o centro de custo."""
    # Se n_conta começa com 1, centro_custo pode ser nulo
    if str(n_conta).startswith('1') and pd.isna(centro_custo):
        return True, None
    
    if pd.isna(centro_custo):
        return False, "Centro de custo não pode ser nulo quando N_CONTA não começa com 1"
    
    # Remove caracteres não numéricos
    numeros = re.sub(r'\D', '', str(centro_custo))
    
    if len(numeros) != 9:
        return False, "Centro de custo deve ter 9 dígitos"
    
    try:
        return True, int(numeros)
    except:
        return False, "Centro de custo inválido"

def validar_operacao(operacao: str) -> Tuple[bool, str]:
    """
    Valida e transforma a operação.
    
    Args:
        operacao: String com a operação a ser validada
        
    Returns:
        Tuple contendo:
        - bool: True se a operação é válida, False caso contrário
        - str: Operação transformada ou mensagem de erro
    """
    if pd.isna(operacao) or operacao == '':
        return True, ''
    
    # Remove espaços extras
    operacao = ' '.join(operacao.split())
    # Converte para maiúsculo
    operacao = operacao.upper()
    
    # Verifica se tem mais de 10 caracteres
    if len(operacao) > 10:
        return False, "Operação não pode ter mais de 10 caracteres"
    
    return True, operacao


def validar_rateio(rateio: str) -> Tuple[bool, str]:
    """
    Valida e transforma o campo rateio.
    
    Args:
        rateio: String com o rateio a ser validado
        
    Returns:
        Tuple contendo:
        - bool: True se o rateio é válido, False caso contrário
        - str: Rateio transformado ou mensagem de erro
    """
    if pd.isna(rateio) or rateio == '':
        return True, ''
    
    # Remove espaços extras e converte para maiúsculo
    rateio = ' '.join(str(rateio).split()).upper()
    
    # Verifica se é SIM ou NÃO
    if rateio not in ['SIM', 'NAO', 'NÃO']:
        return False, "Rateio deve ser 'SIM' ou 'NÃO'"
    
    # Normaliza NÃO para NAO (sem acento)
    if rateio == 'NÃO':
        rateio = 'NAO'
    
    return True, rateio


def validar_origem(origem: str) -> Tuple[bool, str]:
    """
    Valida e transforma o campo origem.
    
    Args:
        origem: String com a origem a ser validada
        
    Returns:
        Tuple contendo:
        - bool: True se a origem é válida, False caso contrário
        - str: Origem transformada ou mensagem de erro
    """
    if pd.isna(origem) or origem == '':
        return True, ''
    
    # Remove espaços extras e converte para maiúsculo
    origem = limpar_texto(str(origem))
    
    # Verifica o tamanho máximo
    if len(origem) > 60:
        return False, "Origem não pode ter mais de 60 caracteres"
    
    return True, origem

def validar_valor(valor: float) -> Tuple[bool, float]:
    """
    Valida e transforma o valor.
    
    Args:
        valor: Valor a ser validado
        
    Returns:
        Tuple contendo:
        - bool: True se o valor é válido, False caso contrário
        - float: Valor transformado ou mensagem de erro
    """
    try:
        # Converte para float
        valor_float = float(valor)
        return True, valor_float
    except:
        return False, "Valor inválido"

def validar_descricao(descricao: str) -> Tuple[bool, str]:
    """
    Valida e transforma a descrição.
    
    Args:
        descricao: String com a descrição a ser validada
        
    Returns:
        Tuple contendo:
        - bool: True se a descrição é válida, False caso contrário
        - str: Descrição transformada ou mensagem de erro
    """
    if pd.isna(descricao) or descricao == '':
        return False, "Descrição não pode ser vazia"
    
    # Remove espaços extras
    descricao = ' '.join(descricao.split())
    # Converte para maiúsculo
    descricao = descricao.upper()
    
    return True, descricao

def validar_tipo(tipo: str) -> Tuple[bool, str]:
    """
    Valida e transforma o tipo.
    
    Args:
        tipo: String com o tipo a ser validado
        
    Returns:
        Tuple contendo:
        - bool: True se o tipo é válido, False caso contrário
        - str: Tipo transformado ou mensagem de erro
    """
    if pd.isna(tipo) or tipo == '':
        return True, "ORCADO"
    
    # Remove espaços extras
    tipo = ' '.join(tipo.split())
    # Converte para maiúsculo
    tipo = tipo.upper()
    
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

def validar_data(data: str) -> Tuple[bool, str]:
    """
    Valida e transforma a data para o formato correto.
    
    Args:
        data: String com a data a ser validada
        
    Returns:
        Tuple contendo:
        - bool: True se a data é válida, False caso contrário
        - str: Data transformada ou mensagem de erro
    """
    if pd.isna(data) or data == '':
        return False, "Data não pode ser vazia"
    
    try:
        # Tenta converter a data para datetime com dayfirst=True para formato brasileiro (DD/MM/AAAA)
        data_dt = pd.to_datetime(data, dayfirst=True)
        # Retorna a data no formato correto
        return True, data_dt.strftime('%d/%m/%Y')
    except:
        return False, "Data inválida. Use o formato DD/MM/AAAA"

def transformar_dados(df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
    """
    Transforma os dados do DataFrame conforme as regras de negócio.
    
    Args:
        df: DataFrame com os dados a serem transformados
        
    Returns:
        Tuple contendo o DataFrame transformado e uma lista de erros encontrados
    """
    erros = []
    df_transformado = df.copy()
    
    # Lista de colunas necessárias
    colunas_necessarias = [
        'N_CONTA',
        'N_CENTRO_CUSTO',
        'DESCRICAO',
        'VALOR',
        'DATA',
        'VERSAO',
        'FILIAL'
    ]
    
    # Verifica se todas as colunas necessárias estão presentes
    colunas_faltantes = [col for col in colunas_necessarias if col not in df_transformado.columns]
    if colunas_faltantes:
        erros.append(f"Colunas obrigatórias faltando: {', '.join(colunas_faltantes)}")
        return df_transformado, erros
    
    logger.info(f"Colunas necessárias encontradas: {colunas_necessarias}")
    
    # Converte colunas para os tipos corretos
    # Isso evita avisos de tipos incompatíveis durante as atribuições
    df_transformado['FILIAL'] = df_transformado['FILIAL'].astype(str)
    df_transformado['DATA'] = df_transformado['DATA'].astype(str)
    if 'OPERACAO' in df_transformado.columns:
        df_transformado['OPERACAO'] = df_transformado['OPERACAO'].astype(str)
    if 'DESCRICAO' in df_transformado.columns:
        df_transformado['DESCRICAO'] = df_transformado['DESCRICAO'].astype(str)
    if 'VERSAO' in df_transformado.columns:
        df_transformado['VERSAO'] = df_transformado['VERSAO'].astype(str)
    if 'TIPO' in df_transformado.columns:
        df_transformado['TIPO'] = df_transformado['TIPO'].astype(str)
    if 'RATEIO' in df_transformado.columns:
        df_transformado['RATEIO'] = df_transformado['RATEIO'].astype(str)
    if 'ORIGEM' in df_transformado.columns:
        df_transformado['ORIGEM'] = df_transformado['ORIGEM'].astype(str)
    
    # Aplica as transformações
    for idx, row in df_transformado.iterrows():
        # Valida e transforma a filial
        filial_valida, filial_transformada = validar_filial(row['FILIAL'])
        if not filial_valida:
            erros.append(f"Linha {idx + 2}: {filial_transformada}")
        df_transformado.at[idx, 'FILIAL'] = filial_transformada
        
        # Valida e transforma o tipo
        tipo_valido, tipo_transformado = validar_tipo(row.get('TIPO', ''))
        if not tipo_valido:
            erros.append(f"Linha {idx + 2}: {tipo_transformado}")
        df_transformado.at[idx, 'TIPO'] = tipo_transformado
        
        # Valida e transforma a data
        data_valida, data_transformada = validar_data(row['DATA'])
        if not data_valida:
            erros.append(f"Linha {idx + 2}: {data_transformada}")
        df_transformado.at[idx, 'DATA'] = data_transformada
        
        # Valida e transforma o valor
        valor_valido, valor_transformado = validar_valor(row['VALOR'])
        if not valor_valido:
            erros.append(f"Linha {idx + 2}: {valor_transformado}")
        df_transformado.at[idx, 'VALOR'] = valor_transformado
        
        # Valida e transforma a descrição
        descricao_valida, descricao_transformada = validar_descricao(row['DESCRICAO'])
        if not descricao_valida:
            erros.append(f"Linha {idx + 2}: {descricao_transformada}")
        df_transformado.at[idx, 'DESCRICAO'] = descricao_transformada
        
        # Valida e transforma a operação
        if 'OPERACAO' in df_transformado.columns:
            operacao_valida, operacao_transformada = validar_operacao(row['OPERACAO'])
            if not operacao_valida:
                erros.append(f"Linha {idx + 2}: {operacao_transformada}")
            df_transformado.at[idx, 'OPERACAO'] = operacao_transformada
        
        # Valida e transforma o rateio
        if 'RATEIO' in df_transformado.columns:
            rateio_valido, rateio_transformado = validar_rateio(row['RATEIO'])
            if not rateio_valido:
                erros.append(f"Linha {idx + 2}: {rateio_transformado}")
            df_transformado.at[idx, 'RATEIO'] = rateio_transformado
        
        # Valida e transforma a origem
        if 'ORIGEM' in df_transformado.columns:
            origem_valida, origem_transformada = validar_origem(row['ORIGEM'])
            if not origem_valida:
                erros.append(f"Linha {idx + 2}: {origem_transformada}")
            df_transformado.at[idx, 'ORIGEM'] = origem_transformada
    
    return df_transformado, erros 