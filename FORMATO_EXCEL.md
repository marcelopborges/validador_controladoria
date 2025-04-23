# Formato de Arquivo Excel

Este documento descreve o formato esperado para os arquivos Excel (.xlsx ou .xls) a serem importados pelo sistema.

## Estrutura Básica

O arquivo Excel deve conter uma planilha com as seguintes colunas:

| FILIAL | DATA | N_CONTA | N_CENTRO_CUSTO | OPERACAO | VALOR | DESCRICAO | TIPO | VERSAO |
|--------|------|---------|----------------|---------|-------|-----------|------|--------|
| 0101   | 01/01/2024 | 12345678 | 123456789 | OP1234567 | 1000.50 | DESCRIÇÃO DO LANÇAMENTO | ORCADO | 2024 - V1 |

## Descrição das Colunas

### FILIAL
- Deve ter 4 dígitos numéricos
- Deve começar com "01" (ex: 0101, 0102, 0103)
- Exemplo válido: 0101, 0102
- Exemplo inválido: 1234, ABC, 01

### DATA
- Formato DD/MM/YYYY (dia/mês/ano)
- Exemplo válido: 01/01/2024, 31/12/2024
- Exemplo inválido: 2024-01-01, 01-01-2024

### N_CONTA
- Deve ter exatamente 8 dígitos numéricos
- Exemplo válido: 12345678, 00000123
- Exemplo inválido: 123456, 123456789

### N_CENTRO_CUSTO
- Deve ter exatamente 9 dígitos numéricos
- Exemplo válido: 123456789, 000123456
- Exemplo inválido: 12345678, 1234567890

### OPERACAO
- Campo opcional (pode ficar em branco)
- Máximo 10 caracteres
- Exemplo válido: OP1234567, OPERACAO1, [vazio]
- Exemplo inválido: OPERACAO MUITO LONGA

### VALOR
- Valor numérico (pode conter decimais)
- Use ponto ou vírgula como separador decimal
- Não pode ficar em branco
- Exemplo válido: 1000.50, 1000,50, 1000
- Exemplo inválido: [vazio], ABC

### DESCRICAO
- Campo de texto livre
- Não pode ficar em branco
- Exemplo válido: PAGAMENTO DE FORNECEDOR
- Exemplo inválido: [vazio]

### TIPO
- Campo de texto
- Se estiver em branco, será preenchido automaticamente com "ORCADO"
- Exemplo válido: ORCADO, EXECUTADO, [vazio]

### VERSAO
- Deve seguir o formato "AAAA - Vx" onde AAAA é o ano com 4 dígitos e x é o número da versão
- Não precisa preencher manualmente, pois pode selecionar na interface
- Exemplo válido: 2024 - V1, 2025 - V2
- Exemplo inválido: V1, 2024V1, 2024-V1

## Importando via Excel

1. Certifique-se que seu arquivo Excel contém todas as colunas necessárias
2. Os nomes das colunas devem ser **EXATAMENTE** como listados acima (sem acentos e sem espaços)
3. O arquivo pode conter linhas em branco, elas serão ignoradas
4. Veja exemplos abaixo para uma importação correta

## Exemplos

### Exemplo Válido

| FILIAL | DATA       | N_CONTA  | N_CENTRO_CUSTO | OPERACAO  | VALOR    | DESCRICAO              | TIPO    | VERSAO    |
|--------|------------|----------|----------------|-----------|----------|------------------------|---------|-----------|
| 0101   | 01/01/2024 | 12345678 | 123456789      | OP1234567 | 1000.50  | CONTA DE LUZ           | ORCADO  | 2024 - V1 |
| 0102   | 02/01/2024 | 87654321 | 987654321      | OP7654321 | 2500.75  | FOLHA DE PAGAMENTO     | ORCADO  | 2024 - V1 |
| 0103   | 03/01/2024 | 11223344 | 112233445      |           | 3750.25  | ALUGUEL                | ORCADO  | 2024 - V1 |

### Exemplos com Erros

| FILIAL | DATA       | N_CONTA  | N_CENTRO_CUSTO | OPERACAO  | VALOR    | DESCRICAO              | TIPO    | VERSAO    | PROBLEMA                        |
|--------|------------|----------|----------------|-----------|----------|------------------------|---------|-----------|--------------------------------|
| 1234   | 01/01/2024 | 12345678 | 123456789      | OP1234567 | 1000.50  | TESTE                  | ORCADO  | 2024 - V1 | FILIAL não começa com "01"     |
| 0102   | 32/01/2024 | 87654321 | 987654321      | OP7654321 | 2500.75  | TESTE                  | ORCADO  | 2024 - V1 | DATA inválida                   |
| 0103   | 03/01/2024 | 1122334  | 112233445      |           | 3750.25  | TESTE                  | ORCADO  | 2024 - V1 | N_CONTA tem menos de 8 dígitos  |
| 0104   | 04/01/2024 | 12345678 | 12345          |           | 3750.25  | TESTE                  | ORCADO  | 2024 - V1 | N_CENTRO_CUSTO < 9 dígitos      |
| 0105   | 05/01/2024 | 12345678 | 123456789      | OPERACAO MUITO LONGA | 100 | TESTE           | ORCADO  | 2024 - V1 | OPERACAO > 10 caracteres        |
| 0106   | 06/01/2024 | 12345678 | 123456789      | OP1234567 |          | TESTE                  | ORCADO  | 2024 - V1 | VALOR vazio                     |
| 0107   | 07/01/2024 | 12345678 | 123456789      | OP1234567 | 1000.50  |                        | ORCADO  | 2024 - V1 | DESCRICAO vazia                 |
| 0108   | 08/01/2024 | 12345678 | 123456789      | OP1234567 | 1000.50  | TESTE                  | ORCADO  | 2024V1    | VERSAO formato incorreto        |

## Dicas para Preparação do Arquivo

1. **Formato das células**: Certifique-se de formatar corretamente cada coluna:
   - DATA: formato texto (DD/MM/YYYY)
   - N_CONTA e N_CENTRO_CUSTO: formato texto para preservar zeros à esquerda
   - VALOR: formato número com precisão de 2 casas decimais

2. **Verificação prévia**: Antes de importar, faça uma verificação básica:
   - FILIAL começa com "01" e tem 4 dígitos
   - DATA está no formato correto
   - Valores obrigatórios estão preenchidos

3. **Nomes das Colunas**: Atenção especial para os nomes das colunas:
   - Use apenas letras maiúsculas
   - Substitua espaços por underscores (_)
   - Não use acentos ou caracteres especiais

4. **Utilização da interface**: A interface ajuda a validar e corrigir erros:
   - Selecione Ano e Versão antes de processar
   - Verifique os erros no console caso a validação falhe 