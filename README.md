# Importador Controladoria

Aplicação para importação, validação e processamento de dados orçamentários para a Controladoria.

## Funcionalidades

- Validação de dados seguindo regras específicas da controladoria
- Transformação e padronização de dados (remoção de acentos, conversão para maiúsculas)
- Interface web moderna para visualização dos dados
- Suporte para arquivos Excel (.xlsx, .xls)
- Aplicação de versão para todos os registros via dropdown
- Rejeição completa de arquivos com erros, exibindo mensagens detalhadas para correção
- Logs de processamento para auditoria
- Separação de arquivos processados e rejeitados
- Compilação para executável Windows (.exe)
- Integração com BigQuery para armazenamento dos dados
- Deduplicação automática de registros
- Processamento em etapas com feedback visual
- Exportação para CSV e XML

## Requisitos

- Python 3.8+
- uv (instalador de pacotes otimizado)
- Pandas
- Flask (para interface web)
- OpenpyXL (para leitura/escrita de Excel)
- XLRD (para suporte a arquivos .xls)
- PyInstaller (apenas para compilação)
- Google Cloud BigQuery (para integração com BigQuery)

## Instalação

### Instalando o uv (caso ainda não tenha)

```bash
# Instalar uv usando o instalador oficial
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Instalando as dependências com uv

```bash
# Clonar o repositório
git clone [URL_DO_REPOSITORIO]
cd importador_controladoria

# Instalar todas as dependências usando uv
uv pip install -r requirements.txt
```

## Executando a aplicação

### Usando o script de execução

O script `run_importador.sh` automatiza a instalação das dependências e a execução da aplicação:

```bash
./run_importador.sh
```

### Executando manualmente

```bash
python interface_grafica.py
```

## Uso

1. Acesse a interface web em http://localhost:5000
2. Selecione um arquivo Excel (.xlsx) ou CSV contendo os dados a serem importados
3. Carregue os dados clicando em "Carregar"
4. Valide e processe os dados clicando em "Validar e Processar"
5. Acompanhe o progresso em tempo real através das etapas:
   - Carregamento de Dados
   - Validação
   - Upload para BigQuery
   - Metadados
6. Se a validação for bem-sucedida, os dados serão:
   - Salvos em CSV e XML na pasta de processados
   - Enviados para o BigQuery (se configurado)
   - Gerados metadados do processamento

## Formato dos Dados

Consulte o arquivo `FORMATO_EXCEL.md` para detalhes sobre o formato esperado dos dados de entrada.

## Regras de Validação

Consulte o arquivo `REGRAS_VALIDACAO.md` para detalhes sobre as regras de validação aplicadas, incluindo:

- Formato da filial (4 dígitos, começando com "0")
- Formato da data (DD/MM/YYYY)
- Validação de N_CONTA e N_CENTRO_CUSTO
- Regras para valores e descrições
- Formato da versão (YYYY - VX)

## Envio para BigQuery

A aplicação permite enviar os dados processados diretamente para o BigQuery. Para usar esta funcionalidade:

1. Configure as credenciais do BigQuery em variáveis de ambiente ou no arquivo de configuração
2. Certifique-se de que o dataset e a tabela já existam no BigQuery
3. Após processar os dados com sucesso, os dados serão enviados automaticamente

### Deduplicação no BigQuery

O sistema implementa deduplicação automática usando a seguinte lógica:
- Chave única: N_CONTA + N_CENTRO_CUSTO + DATA
- Em caso de duplicidade, mantém o registro mais recente
- Atualiza registros existentes com novos valores

## Configuração das Credenciais

Existem duas formas de configurar as credenciais do BigQuery:

### 1. Usando arquivo de credenciais (desenvolvimento local)

1. Copie o arquivo `config/bigquery-credentials.example.json` para `config/bigquery-credentials.json`
2. Substitua os valores no arquivo com suas credenciais do Google Cloud
3. **IMPORTANTE**: Nunca compartilhe ou comite suas credenciais reais

```bash
cp config/bigquery-credentials.example.json config/bigquery-credentials.json
# Edite o arquivo config/bigquery-credentials.json com suas credenciais
```

### 2. Usando variáveis de ambiente (recomendado para produção)

Configure as seguintes variáveis de ambiente:

```bash
# Configurações do BigQuery
export BIGQUERY_PROJECT_ID=seu-projeto-id
export BIGQUERY_DATASET_ID=seu-dataset-id
export BIGQUERY_TABLE_ID=sua-tabela-id
export BIGQUERY_METADATA_TABLE_ID=sua-tabela-metadata-id

# Credenciais do Service Account
export BIGQUERY_PRIVATE_KEY_ID=chave-privada-id
export BIGQUERY_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nSua chave privada aqui\n-----END PRIVATE KEY-----\n"
export BIGQUERY_CLIENT_EMAIL=seu-service-account@seu-projeto.iam.gserviceaccount.com
export BIGQUERY_CLIENT_ID=seu-client-id
export BIGQUERY_CLIENT_X509_CERT_URL=url-do-certificado
```

**Nota**: Para maior segurança em produção, considere usar um gerenciador de segredos como o Google Secret Manager ou GitHub Secrets.

## Licença

Este software é proprietário e confidencial.

## Estrutura do Projeto

```
importador_controladoria/
├── data/                   # Diretório para arquivos de dados
│   ├── processados/        # Arquivos processados com sucesso
│   └── rejeitados/         # Arquivos rejeitados com erros
├── logs/                   # Logs de processamento
├── src/                    # Código-fonte do projeto
│   └── importador_controladoria/
│       ├── __init__.py
│       ├── config.py       # Configurações do projeto
│       ├── transformacoes.py # Funções de validação e transformação
│       ├── interface.py    # Interface web e processamento
│       └── main.py         # Ponto de entrada principal
├── interface_grafica.py    # Interface web da aplicação
├── processar_arquivo.py    # Script para processamento de arquivos via CLI
├── setup.py                # Script para compilação do executável
├── criar_icone.py          # Script para criar o ícone da aplicação
├── REGRAS_VALIDACAO.md     # Documentação das regras de validação
└── README.md               # Este arquivo
```

## Contribuição

Para contribuir com este projeto, siga as etapas:

1. Faça um fork do repositório
2. Crie uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. Faça commit das suas alterações (`git commit -m 'Adiciona nova funcionalidade'`)
4. Faça push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo LICENSE para mais detalhes.
