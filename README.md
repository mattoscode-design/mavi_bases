# Mavi Bases

Sistema desktop para processamento e tratamento de bases Excel por varejista, com identificação automática de lojas via cruzamento com banco MySQL.

Construído com **Python 3.14 + Flet 0.84** (interface gráfica nativa).

---

## Estrutura do projeto

```
mavi_bases/
├── app.py                        ← ponto de entrada do app Flet
├── config.py                     ← variáveis de ambiente e paths
├── requirements.txt              ← dependências Python
├── .env                          ← credenciais (não versionado)
├── .env.example                  ← modelo de .env
├── .gitignore
│
├── engine/                       ← lógica de negócio / ETL
│   ├── conexao.py                ← pool de conexões MySQL (thread-safe)
│   ├── exportador.py             ← exportação para Excel
│   ├── grupos.py                 ← gerenciamento de grupos de varejistas
│   ├── logger.py                 ← logger centralizado (arquivo rotativo)
│   ├── mapeamento_loader.py      ← carregamento de mapeamentos do banco
│   ├── matcher.py                ← identificação de lojas (5 estratégias)
│   ├── pendencias_store.py       ← persistência de pendências por banco
│   ├── processador.py            ← orquestrador principal do pipeline ETL
│   └── transformador.py          ← todas as transformações de dados
│
├── models/
│   └── schemas.py                ← modelos Pydantic de entrada/saída
│
├── security/
│   ├── audit.py                  ← log de ações por usuário
│   ├── crypto.py                 ← criptografia de credenciais (Fernet)
│   ├── limpeza.py                ← exclusão segura de arquivos temporários
│   ├── sanitizacao.py            ← validação de paths e nomes de arquivo
│   └── usuarios.json             ← hashes de senha (não versionado)
│
├── ui/                           ← telas Flet
│   ├── tema.py                   ← design system (cores, botões, inputs)
│   ├── login.py                  ← autenticação
│   ├── banco.py                  ← seleção de banco de dados
│   ├── modulos.py                ← menu principal
│   ├── upload.py                 ← upload e processamento de bases
│   ├── mapeamento.py             ← configuração de mapeamentos por varejista
│   ├── resultado.py              ← exibição de resultados e download
│   └── validacao.py              ← vinculação manual de lojas pendentes
│
├── entradas/                     ← arquivos recebidos (gerada automaticamente)
└── saidas/                       ← arquivos processados (gerada automaticamente)
```

---

## Pré-requisitos

- Python 3.11+
- MySQL 8.0+ com o banco restaurado
- Tabelas que precisam existir no banco: `loja`, `varejista`
  - `aliases_loja`, `mapeamento_coluna`, `varejista_grupo` são criadas automaticamente pelo app

---

## Instalação

### 1. Clone o projeto

```bash
cd mavi_bases
```

### 2. Crie e ative o ambiente virtual

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure o `.env`

Copie o modelo e preencha com suas credenciais MySQL:

```bash
cp .env.example .env
```

```
DB_HOST=localhost
DB_PORT=3306
DB_NAME=nome_do_banco
DB_USER=root
DB_PASSWORD=sua_senha
```

### 5. Crie o primeiro usuário

Execute uma vez no terminal Python:

```python
from ui.login import adicionar_usuario
adicionar_usuario("seu_usuario", "sua_senha")
```

### 6. Rode o projeto

```bash
python app.py
```

> Arquivos processados são salvos em `saidas/` com o nome `<VAREJISTA>_<MÊS_ANO>.xlsx`.

---

## Fluxo de uso

```
Login → Selecionar banco → Menu principal
                               ├── Tratamento de Bases
                               │     ├── Selecionar varejista + arquivo Excel
                               │     ├── Pré-visualizar (dry-run 10 linhas)
                               │     └── Processar → Tela de resultado + download
                               ├── Configurar Mapeamento
                               ├── Lojas Pendentes (vinculação manual)
                               └── Grupos de Varejistas
```

---

## Funcionalidades principais

### Processamento de bases Excel

- Leitura robusta: detecta cabeçalho automaticamente + desunifica células mescladas
- Separação de data em MÊS / ANO (8+ formatos suportados)
- Cruzamento de lojas por 5 estratégias em cascata
- Cruzamento de EAN com setor de produto
- Cruzamento de varejistas em bases consolidadas
- Conversão automática de numéricos (formato brasileiro `1.234,56`)
- Colunas calculadas, renomeação, colunas novas com valor fixo
- Sinalização de pendências na coluna `PENDENCIA`
- Export para `.xlsx` com aba de lojas pendentes separada

### Identificação de lojas — 5 estratégias

1. ID direto (`coluna_id_direto`)
2. Matrícula direta em `id_loja`
3. `cluster_9`
4. Número extraído do nome do PDV
5. Alias salvo anteriormente

### Mapeamento por varejista

Configurado via interface, salvo no banco. Suporta:

- Separar data, cruzar loja, cruzar EAN, cruzar varejista
- Renomear colunas, calcular colunas, adicionar colunas novas
- Ignorar colunas, colunas com valor fixo / ano atual

### Pré-visualização (dry-run)

Antes de processar, o botão **"Pré-visualizar"** executa todas as transformações nas primeiras 10 linhas e exibe o resultado em tabela — sem salvar nada.

### Pendências persistidas

Lojas não encontradas são salvas em `~/.mavi_bases/pendencias/<banco>.json` e sobrevivem a reinicializações. Ao vincular manualmente uma loja, ela é removida do arquivo.

---

## Segurança

| Item           | Implementação                                        |
| -------------- | ---------------------------------------------------- |
| Senhas         | PBKDF2-SHA256, 100k iterações, `hmac.compare_digest` |
| Credenciais DB | Arquivo `.env` fora do versionamento                 |
| Rate limiting  | 5 tentativas de login por 60s por usuário            |
| SQL injection  | Queries parametrizadas em todo o código              |
| Path traversal | `sanitizacao.py` com validação de caminho            |
| Arquivos temp  | Exclusão segura com sobrescrita de zeros             |
| Audit log      | JSON mensal em `~/.mavi_bases/logs/`                 |

---

## Logs

| Arquivo              | Localização           | Descrição                                 |
| -------------------- | --------------------- | ----------------------------------------- |
| `app.log`            | `~/.mavi_bases/logs/` | Log técnico rotativo (5 MB × 3 backups)   |
| `audit_YYYY_MM.json` | `~/.mavi_bases/logs/` | Ações por usuário (login, processamentos) |

---

## Estrutura do projeto

```
agente_bases/
├── main.py                   ← FastAPI — ponto de entrada
├── config.py                 ← configurações e mapeamentos por varejista
├── requirements.txt          ← dependências Python
├── .env.example              ← modelo de variáveis de ambiente
├── engine/
│   ├── conexao.py            ← pool de conexões MySQL
│   ├── matcher.py            ← identificação de lojas (4 estratégias)
│   └── processador.py        ← engine de transformação do Excel
├── routers/
│   ├── upload.py             ← rota de upload e processamento
│   ├── validacao.py          ← rota de vinculação manual de lojas
│   └── resultado.py          ← rota de download e histórico
├── models/
│   └── schemas.py            ← modelos Pydantic
├── templates/
│   ├── base.html             ← layout base
│   ├── upload.html           ← tela de upload
│   ├── resultado.html        ← tela de resultado
│   └── validacao.html        ← tela de lojas pendentes
├── static/
│   └── style.css             ← estilos do app
├── entradas/                 ← bases recebidas (gerada automaticamente)
└── saidas/                   ← bases tratadas (gerada automaticamente)
```

---

## Pré-requisitos

- Python 3.11+
- MySQL rodando localmente com o backup do banco restaurado
- Tabelas necessárias no banco:
  - `loja` — com as colunas `id_loja`, `nome_loja`, `cluster_9`
  - `varejista` — com `cod_varejista`, `nome_varejista`
  - `aliases_loja` — criada pelo script abaixo (nova tabela do projeto)

---

## Instalação

### 1. Clone ou copie a pasta do projeto

```bash
cd agente_bases
```

### 2. Crie o ambiente virtual

```bash
python -m venv venv
```

Ative o ambiente:

```bash
# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Configure as variáveis de ambiente

Copie o arquivo de exemplo e preencha com suas credenciais:

```bash
cp .env.example .env
```

Abra o `.env` e preencha:

```
DB_HOST=localhost
DB_PORT=3306
DB_NAME=nome_do_seu_banco
DB_USER=root
DB_PASSWORD=sua_senha
```

### 5. Crie a tabela de aliases no banco

Execute este SQL no seu MySQL (via MySQL Workbench ou linha de comando):

```sql
CREATE TABLE IF NOT EXISTS aliases_loja (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    cod_varejista   INT          NOT NULL,
    nome_alias      VARCHAR(130) NOT NULL,
    id_loja         BIGINT       NOT NULL,
    criado_em       DATETIME     DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_alias (cod_varejista, nome_alias),
    FOREIGN KEY (cod_varejista) REFERENCES varejista(cod_varejista),
    FOREIGN KEY (id_loja)       REFERENCES loja(id_loja)
);
```

### 6. Teste a conexão com o banco

```bash
python engine/conexao.py
```

Saída esperada:

```
✅ Conectado ao MySQL 8.x.x
```

---

## Rodando o projeto

```bash
python main.py
```

Ou diretamente com uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Acesse no navegador: [http://localhost:8000](http://localhost:8000)

---

## Telas do app

| Rota                               | Descrição                                |
| ---------------------------------- | ---------------------------------------- |
| `/`                                | Upload da base e seleção do varejista    |
| `/resultado/download/{arquivo}`    | Download do Excel tratado                |
| `/validacao/lojas?cod_varejista=1` | Vinculação manual de lojas pendentes     |
| `/resultado/historico`             | Lista todos os arquivos gerados          |
| `/docs`                            | Documentação automática da API (Swagger) |
| `/health`                          | Status do servidor e conexão com banco   |

---

## Como o processamento funciona

### Transformações aplicadas (base Scantech)

| Coluna de entrada        | Ação                        | Coluna de saída                        |
| ------------------------ | --------------------------- | -------------------------------------- |
| `Mes de Data`            | Separada em duas colunas    | `MÊS` + `DATA`                         |
| `Matrícula` + `Nome PDV` | Cruzamento com banco        | `LOJA` (id_loja) + `BANCO` (nome_loja) |
| `Código Barra`           | Renomeada                   | `EAN`                                  |
| `Nome SKU`               | Renomeada                   | `PRODUTO`                              |
| `Vendas em valor`        | Renomeada                   | `VALOR`                                |
| _(nova)_                 | `VALOR ÷ Preço por Unidade` | `QUANTIDADE`                           |

### Estratégias de identificação de loja

O sistema tenta identificar cada loja em 4 etapas, em ordem:

```
1. Matrícula == loja.id_loja           (match direto)
2. Matrícula == loja.cluster_9         (match por cluster)
3. Número extraído do nome == id_loja  (ex: "carrefour lj11" → 11)
4. Nome do PDV == aliases_loja         (alias salvo anteriormente)
   ↓ não achou em nenhuma?
   Sinaliza como ⚠️ PENDENTE para revisão manual
```

Matches encontrados pelas estratégias 2 e 3 são salvos automaticamente como alias para uso futuro.

### Lojas pendentes

Quando uma loja não é identificada automaticamente:

- A linha recebe a marcação `⚠️ LOJA NÃO IDENTIFICADA` na coluna `PENDENCIA`
- Uma aba separada `PENDENCIAS` é criada no Excel de saída
- A tela `/validacao/lojas` permite vincular manualmente cada loja ao registro correto
- Após vincular, o sistema salva o alias e não precisará fazer isso de novo

---

## Adicionando um novo varejista

Abra o `config.py` e adicione uma entrada no dicionário `MAPEAMENTOS`:

```python
MAPEAMENTOS = {
    "scantech": { ... },  # já existe

    "novo_cliente": {
        "renomear": {
            "Coluna Original": "COLUNA_SAIDA",
        },
        "separar": {
            "Data Ref": ["MÊS", "DATA"]
        },
        "cruzar_loja": {
            "coluna_matricula": "Cod Loja",
            "coluna_nome":      "Nome Loja",
            "saida_id":         "LOJA",
            "saida_nome":       "BANCO",
        },
        "calcular": {
            "QUANTIDADE": ("VALOR", "/", "Preco Unit")
        },
    }
}
```

O nome da chave (`"novo_cliente"`) precisa aparecer no nome do arquivo Excel enviado para detecção automática.

---

## Dependências principais

| Pacote                 | Versão  | Uso                              |
| ---------------------- | ------- | -------------------------------- |
| fastapi                | 0.111.0 | Framework web                    |
| uvicorn                | 0.29.0  | Servidor ASGI                    |
| mysql-connector-python | 8.3.0   | Conexão MySQL                    |
| pandas                 | 2.2.0   | Leitura e transformação do Excel |
| openpyxl               | 3.1.2   | Escrita do Excel de saída        |
| python-dotenv          | 1.0.0   | Variáveis de ambiente            |
| pydantic               | 2.7.0   | Validação de dados               |
| unidecode              | 1.3.7   | Normalização de texto            |

---

## Próximos passos sugeridos

- [ ] Tela de cadastro de varejistas direto pelo app
- [ ] Suporte a bases consolidadas (separação automática por varejista)
- [ ] Dashboard com histórico de processamentos
- [ ] Autenticação de usuário
- [ ] Suporte a múltiplas abas no Excel de entradas
