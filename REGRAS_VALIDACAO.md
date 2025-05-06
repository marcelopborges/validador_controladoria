# Regras de Validação - Importador Controladoria

Este documento descreve todas as regras de validação e transformação aplicadas aos dados antes de serem importados para o BigQuery.

## Tipos de Importação

### Importação Completa
- Ocorre quando um arquivo contém todos os registros de uma versão
- Todos os registros existentes da versão são deletados antes da importação
- O sistema identifica automaticamente como importação completa quando:
  - Não existem registros da versão no banco
  - A tabela não existe (primeira importação)
- Nos metadados, é registrado como:
  - STATUS: "IMPORTACAO_COMPLETA"
  - ARQUIVO_ORIGEM: "IMPORTACAO_COMPLETA: nome_do_arquivo.xlsx"

### Atualização Parcial
- Ocorre quando um arquivo contém apenas alguns registros de uma versão
- Os registros existentes são atualizados e novos registros são inseridos
- O sistema identifica como atualização parcial quando:
  - Já existem registros da versão no banco
  - O arquivo contém apenas uma parte dos registros
- Nos metadados, é registrado como:
  - STATUS: "ATUALIZACAO_PARCIAL"
  - ARQUIVO_ORIGEM: "ATUALIZACAO_PARCIAL: nome_do_arquivo.xlsx"

## Regras Gerais

- Nenhuma coluna pode ter acento
- Não pode ter espaços desnecessários em nenhum campo
- Todos os textos são convertidos para letras maiúsculas

## Campos Obrigatórios
- N_CONTA
- N_CENTRO_CUSTO
- DESCRICAO
- VALOR
- DATA
- VERSAO
- FILIAL

## Campos Opcionais
- OPERACAO (máximo 10 caracteres)

## Validações por Campo

### FILIAL
- **Formato**: 4 dígitos, começando com "0" (ex: 0103, 0102, 0503)
- **Obrigatório**: Sim
- **Tipo**: String (texto)
- **Observação**: Se começar com números, será completado com zeros à esquerda

### DATA
- **Formato**: DD/MM/YYYY (ex: 01/01/2024)
- **Obrigatório**: Sim
- **Tipo**: Data
- **Observação**: Datas em outros formatos serão rejeitadas

### N_CONTA
- **Formato**: 8 dígitos numéricos
- **Obrigatório**: Sim
- **Tipo**: Número inteiro
- **Observação**: Não aceita valores nulos

### N_CENTRO_CUSTO
- **Formato**: 9 dígitos numéricos
- **Obrigatório**: Condicional - Obrigatório apenas quando N_CONTA não começa com 1
- **Tipo**: Número inteiro
- **Observação**: Pode ser nulo quando N_CONTA começa com 1

### OPERACAO
- **Formato**: Texto com no máximo 10 caracteres
- **Obrigatório**: Não
- **Tipo**: String (texto)
- **Observação**: Campo aceita valores nulos

### VALOR
- **Formato**: Número decimal (float)
- **Obrigatório**: Sim
- **Tipo**: Decimal
- **Observação**: Não aceita valores nulos, utilizar ponto ou vírgula como separador decimal

### DESCRICAO
- **Formato**: Texto livre
- **Obrigatório**: Sim
- **Tipo**: String (texto)
- **Observação**: Não aceita valores nulos

### TIPO
- **Formato**: Texto livre
- **Obrigatório**: Não
- **Tipo**: String (texto)
- **Observação**: Se estiver vazio, será preenchido automaticamente com "ORCADO"

### VERSAO
- **Formato**: Deve seguir o padrão "ANO - VERSAO" (ex: "2024 - V1", "2025 - V2")
- **Obrigatório**: Sim
- **Tipo**: String (texto)
- **Observação**: O ano deve ser um número de 4 dígitos, seguido de " - V" e o número da versão
- **Interface Gráfica**: Use os dropdowns de Ano e Versão para selecionar a versão a ser aplicada a todos os registros

## Regras por Campo

### N_CONTA
- Deve ser um número inteiro
- Não pode ser nulo
- Deve ter no máximo 10 dígitos

### N_CENTRO_CUSTO
- Deve ser um número inteiro
- Não pode ser nulo
- Deve ter exatamente 9 dígitos

### DESCRICAO
- Deve ser uma string
- Não pode ser nula
- Deve ter no máximo 100 caracteres

### VALOR
- Deve ser um número decimal
- Não pode ser nulo
- Deve ser maior que zero
- Deve ter no máximo 2 casas decimais

### DATA
- Deve ser uma data válida
- Não pode ser nula
- Formato: DD/MM/AAAA

### VERSAO
- Deve ser uma string
- Não pode ser nula
- Deve ter no máximo 10 caracteres

### OPERACAO
- Deve ser uma string
- Pode ser nula
- Deve ter no máximo 10 caracteres
- Se preenchida, deve conter apenas letras, números e caracteres especiais permitidos

## Exemplos de Valores Válidos

### N_CONTA
- 123456
- 7890123456

### N_CENTRO_CUSTO
- 123456789
- 987654321

### DESCRICAO
- "Material de Escritório"
- "Serviços de Manutenção"

### VALOR
- 100.50
- 1234.56

### DATA
- 01/01/2024
- 31/12/2024

### VERSAO
- "2024.1"
- "REV1"

### OPERACAO
- "INSERT"
- "UPDATE"
- "DELETE"
- "MERGE"

## Como Corrigir Erros Comuns

1. **Filial inválida**: Certifique-se que a filial possui 4 dígitos e começa com "0"
2. **Data inválida**: Use o formato DD/MM/YYYY (ex: 01/01/2024)
3. **N_Conta inválido**: Verifique se possui 8 dígitos numéricos
4. **N_Centro_Custo inválido**: Verifique se possui 9 dígitos numéricos
5. **Operação muito longa**: Reduza para no máximo 10 caracteres
6. **Valor nulo ou inválido**: Adicione um valor numérico válido
7. **Descrição vazia**: Adicione uma descrição
8. **Versão em formato inválido**: Use o formato "YYYY - VX", onde YYYY é o ano com 4 dígitos e X é o número da versão

## Nomes de Colunas

Os nomes das colunas devem seguir essas regras:

1. Todas as letras em maiúsculas
2. Sem acentos ou caracteres especiais
3. Usar underscore (_) em vez de espaços
   - Exemplo: "N CONTA" deve ser escrito como "N_CONTA"
   - Exemplo: "N CENTRO CUSTO" deve ser escrito como "N_CENTRO_CUSTO"
