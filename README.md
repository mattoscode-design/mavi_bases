# Agente de Bases

Sistema de processamento e tratamento de bases Excel por varejista, com identificação automática de lojas via cruzamento com banco MySQL.

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
