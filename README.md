# Importador Controladoria

Aplicação para importação, validação e processamento de dados orçamentários para a Controladoria.

## Funcionalidades

- Validação de dados seguindo regras específicas da controladoria
- Transformação e padronização de dados (remoção de acentos, conversão para maiúsculas)
- Interface gráfica moderna para visualização dos dados
- Suporte para arquivos Excel (.xlsx, .xls)
- Aplicação de versão para todos os registros via dropdown
- Rejeição completa de arquivos com erros, exibindo mensagens detalhadas para correção
- Logs de processamento para auditoria
- Separação de arquivos processados e rejeitados
- Compilação para executável Windows (.exe)

## Requisitos

- Python 3.8+
- uv (instalador de pacotes otimizado)
- Pandas
- Colorama
- Tkinter (geralmente já vem com o Python)
- OpenpyXL (para leitura/escrita de Excel)
- XLRD (para suporte a arquivos .xls)
- PyInstaller (apenas para compilação)
- Pillow (para elementos gráficos)

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

1. Selecione um arquivo Excel (.xlsx) ou CSV contendo os dados a serem importados
2. Carregue os dados clicando em "Carregar"
3. Valide e processe os dados clicando em "Validar e Processar"
4. Se a validação for bem-sucedida, salve os dados processados ou envie-os para o BigQuery

## Formato dos Dados

Consulte o arquivo `FORMATO_EXCEL.md` para detalhes sobre o formato esperado dos dados de entrada.

## Regras de Validação

Consulte o arquivo `REGRAS_VALIDACAO.md` para detalhes sobre as regras de validação aplicadas.

## Envio para BigQuery

A aplicação permite enviar os dados processados diretamente para o BigQuery. Para usar esta funcionalidade:

1. Configure as credenciais do BigQuery em variáveis de ambiente ou no arquivo de configuração
2. Certifique-se de que o dataset e a tabela já existam no BigQuery
3. Após processar os dados com sucesso, clique no botão "Enviar para BigQuery"

## Configuração das Credenciais

Para configurar as credenciais do BigQuery:

1. Copie o arquivo `config/bigquery-credentials.example.json` para `config/bigquery-credentials.json`
2. Substitua os valores no arquivo com suas credenciais do Google Cloud
3. **IMPORTANTE**: Nunca compartilhe ou comite suas credenciais reais

```bash
cp config/bigquery-credentials.example.json config/bigquery-credentials.json
# Edite o arquivo config/bigquery-credentials.json com suas credenciais
```

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
│       └── main.py         # Ponto de entrada principal
├── interface_grafica.py    # Interface gráfica da aplicação
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
