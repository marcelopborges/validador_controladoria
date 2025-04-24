# Regras de Validação - Importador Controladoria

Este documento descreve todas as regras de validação e transformação aplicadas aos dados antes de serem importados para o BigQuery.

## Regras Gerais

- Nenhuma coluna pode ter acento
- Não pode ter espaços desnecessários em nenhum campo
- Todos os textos são convertidos para letras maiúsculas

## Validações por Campo

### FILIAL
- **Formato**: 4 dígitos, começando com "0" (ex: 0101, 0102, 0503)
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
