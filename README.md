# Mavi Bases

Sistema desktop para tratamento de bases Excel por varejista, com identificação automática de lojas, cruzamento com banco MySQL e exportação final por base completa ou por varejista.

Stack principal: Python 3.14, Flet 0.84, MySQL, pandas 3.x, openpyxl, Pydantic v2.

---

## Visão geral

O app é desktop, sem servidor web. O fluxo principal é:

`Login -> Seleção de banco -> Menu -> Upload -> Processamento -> Resultado -> Pendências`

Principais recursos:

- Leitura robusta de Excel com detecção automática de cabeçalho
- Tratamento de células mescladas
- Mapeamento configurável por varejista
- Cruzamento de lojas por múltiplas estratégias
- Cruzamento de EAN e varejista
- Pré-visualização antes do processamento
- Persistência de pendências por banco
- Vinculação manual de lojas com reaproveitamento automático via alias
- Exportação da base completa e exportação separada por varejista

---

## Estrutura do projeto

```text
mavi_bases/
├── app.py
├── config.py
├── README.md
├── requirements.txt
├── .env.example
├── assets/
│   ├── mavi_logo.png
│   └── minimavi_logo.png
├── engine/
├── models/
├── security/
├── ui/
├── entradas/
└── saidas/
```

Pastas principais:

- `engine/`: regras de negócio, ETL, exportação, conexões, logs
- `ui/`: telas Flet
- `security/`: autenticação, sanitização, limpeza, auditoria
- `models/`: schemas Pydantic
- `assets/`: logos e imagens do app
- `entradas/`: arquivos recebidos para processamento
- `saidas/`: arquivos finais gerados

---

## Pré-requisitos

- Python 3.14 recomendado
- MySQL 8+
- Banco com as tabelas `loja` e `varejista`
- As tabelas `aliases_loja`, `mapeamento_colunas`, `varejista_grupo` e `varejista_grupo_item` podem ser criadas/geridas pelo próprio app

---

## Instalação

### 1. Criar ambiente virtual

```powershell
python -m venv .venv
.venv\Scripts\Activate
```

Se o PowerShell bloquear scripts:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.venv\Scripts\Activate
```

### 2. Instalar dependências

```powershell
pip install -r requirements.txt
```

### 3. Configurar `.env`

Use o `.env.example` como base:

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=nome_do_banco
DB_USER=root
DB_PASSWORD=sua_senha
```

### 4. Criar primeiro usuário

```python
from ui.login import adicionar_usuario
adicionar_usuario("seu_usuario", "sua_senha")
```

### 5. Rodar o app

```powershell
python app.py
```

---

## Dependências compatíveis

Dependências ajustadas para Python 3.14:

- `flet==0.84.0`
- `pandas>=3.0.0,<3.1.0`
- `openpyxl>=3.1.5,<3.2.0`
- `mysql-connector-python>=9.0.0`
- `pydantic>=2.13.0,<3.0.0`

---

## Fluxo de uso

### Tratamento de bases

1. Escolher o banco
2. Selecionar o varejista
3. Selecionar a base Excel
4. Pré-visualizar, se necessário
5. Processar
6. Salvar a base completa ou baixar por varejista

### Configurar mapeamento

Para cada coluna da base é possível definir:

- `id_loja`
- `matricula_loja`
- `nome_loja`
- `renomear`
- `cruzar_ean`
- `separar_mes_ano`
- `calcular_quantidade`
- `manter`
- `ignorar`
- `cruzar_varejista`

Também é possível:

- criar novas colunas
- calcular quantidade por fórmula
- restringir cruzamento de varejista por grupos
- salvar e reabrir o mapeamento já preenchido

### Lojas pendentes

A tela de pendências permite:

- pesquisar loja por id ou nome
- vincular manualmente uma loja
- persistir a vinculação via alias
- ver pendências agrupadas por varejista
- consultar aliases já cadastrados

---

## Arquitetura técnica

```text
app.py
  -> ui/
  -> engine/
  -> security/
  -> models/
```

### app.py

Responsável por:

- inicialização da janela Flet
- navegação entre telas
- estado de sessão
- carregamento e mescla de pendências
- registro de auditoria

Estado de sessão principal:

```python
sessao = {
    "usuario": "",
    "banco": "",
    "cod_varejista": None,
    "resultado": None,
    "nome_varejista": "",
    "pendencias": [],
}
```

### engine/

#### `conexao.py`

- troca de banco com segurança via `configurar_banco()`
- pool de conexões MySQL
- controle por lock para evitar inconsistência

#### `logger.py`

- log técnico centralizado
- arquivo em `~/.mavi_bases/logs/app.log`
- rotação de 5 MB com 3 backups

#### `matcher.py`

Estratégias de identificação de loja:

1. id direto
2. matrícula direta
3. `cluster_9`
4. número extraído do nome
5. alias salvo anteriormente

#### `transformador.py`

Responsável por:

- separar mês/ano
- cruzar loja
- cruzar EAN
- cruzar varejista
- renomear colunas
- converter numéricos
- calcular colunas
- adicionar colunas novas
- sinalizar pendências

#### `processador.py`

Orquestra o pipeline ETL:

1. carregar mapeamento
2. ler Excel com robustez
3. remover colunas ignoradas
4. separar data
5. cruzar varejista
6. cruzar lojas
7. cruzar EAN
8. renomear colunas
9. converter numéricos
10. calcular colunas
11. adicionar colunas novas
12. sinalizar pendências
13. exportar Excel final

Também expõe:

- `preview_base()`
- `processar_base()`

#### `exportador.py`

- gera arquivo Excel final
- usa `xlsxwriter` quando disponível
- fallback para `openpyxl`
- cria aba `BASE_TRATADA`
- cria aba `LOJAS NOVAS` quando há pendências

#### `grupos.py`

- cria, lista e remove grupos de varejistas
- usado na configuração de mapeamento

#### `pendencias_store.py`

Armazena pendências em:

```text
~/.mavi_bases/pendencias/<banco>.json
```

---

## Interface

### `ui/login.py`

- login com PBKDF2-SHA256
- rate limiting por usuário

### `ui/banco.py`

- seleção do banco
- teste de conexão

### `ui/modulos.py`

- menu principal
- acesso a tratamento, mapeamento, pendências e grupos

### `ui/upload.py`

- seleção de varejista
- seleção de arquivo Excel
- aviso se não houver mapeamento
- processamento em thread
- pré-visualização
- cancelamento de processamento

### `ui/mapeamento.py`

- leitura das colunas da base
- configuração de ação por coluna
- criação de novas colunas
- gerenciamento de grupos
- preenchimento inicial automático dos nomes de saída

### `ui/resultado.py`

- resumo do processamento
- indicadores principais
- setores encontrados
- avisos de pendência
- salvar base completa
- baixar por varejista
- gerar também arquivo de não registrados

### `ui/validacao.py`

- agrupamento de pendências por varejista
- pesquisa de lojas em tempo real
- vinculação manual
- histórico de aliases

---

## Models

### `VincularLojaRequest`

```python
cod_varejista: int
nome_alias: str
id_loja: int
```

### `ProcessarRequest`

```python
cod_varejista: int
nome_varejista: str
nome_arquivo: str
```

### `ResultadoProcessamento`

```python
ok: bool
arquivo_saida: str | None
total_linhas: int | None
lojas_unicas: int | None
lojas_ok: int | None
lojas_novas: int | None
total_valor: float | None
total_quantidade: float | None
setores: list
pendencias: list
varejistas_novos: list
mes_ref: str
coluna_varejista_saida: str
erro: str | None
timings: dict
```

---

## Banco de dados

### Tabelas principais

#### `loja`

- `id_loja`
- `nome_loja`
- `cluster_9`

#### `varejista`

- `cod_varejista`
- `nome_varejista`

#### `aliases_loja`

- `cod_varejista`
- `nome_alias`
- `id_loja`

#### `mapeamento_colunas`

- configuração da transformação por varejista

#### `varejista_grupo`

- definição do grupo

#### `varejista_grupo_item`

- relação entre grupo e varejistas

---

## Segurança

- senhas com `PBKDF2-SHA256`
- comparação com `hmac.compare_digest`
- rate limiting de login
- queries parametrizadas
- sanitização de nome de arquivo e caminho
- limpeza segura de arquivos
- auditoria mensal em JSON

Arquivos locais importantes:

```text
~/.mavi_bases/logs/app.log
~/.mavi_bases/logs/audit_YYYY_MM.json
~/.mavi_bases/pendencias/<banco>.json
```

---

## Convenções internas

Colunas temporárias usadas no pipeline:

- `_LOJA_OK_`
- `_COD_VAR_`

Essas colunas são removidas antes da exportação.

Formato de `mes_ref`:

- `MMM_YYYY`
- exemplo: `MAR_2026`

---

## Observações de manutenção

- O app usa as imagens em `assets/`
- O ícone da janela desktop usa `assets/minimavi_logo.png`
- A logo principal das telas usa `assets/mavi_logo.png`
- Se trocar os arquivos de imagem, mantenha os mesmos nomes para evitar ajustes no código

---

## Logs

| Arquivo              | Local                 | Uso         |
| -------------------- | --------------------- | ----------- |
| `app.log`            | `~/.mavi_bases/logs/` | log técnico |
| `audit_YYYY_MM.json` | `~/.mavi_bases/logs/` | auditoria   |

---

## Status atual do app

O sistema já cobre o fluxo principal de operação:

- autenticação
- seleção de banco
- configuração de mapeamento
- processamento de base
- validação de pendências
- exportação final
- exportação por varejista
- exportação de não registrados

# Mavi Bases

Sistema desktop para processamento, padronizacao e exportacao de bases Excel por varejista, com interface Flet e integracao direta com MySQL.

## Visao geral

- App desktop em Python com Flet
- Processamento de planilhas Excel com pandas e openpyxl
- Cruzamento automatico de lojas, EANs e varejistas
- Mapeamento configuravel por varejista
- Persistencia de pendencias e aliases para melhorar os proximos processamentos

## Estrutura do projeto

```text
mavi_bases/
├── app.py
├── config.py
├── requirements.txt
├── README.md
├── .env
├── .env.example
├── assets/
│   ├── mavi_logo.png
│   └── minimavi_logo.png
├── engine/
│   ├── conexao.py
│   ├── exportador.py
│   ├── grupos.py
│   ├── logger.py
│   ├── mapeamento_loader.py
│   ├── matcher.py
│   ├── pendencias_store.py
│   ├── processador.py
│   └── transformador.py
├── models/
│   └── schemas.py
├── security/
│   ├── audit.py
│   ├── crypto.py
│   ├── limpeza.py
│   ├── sanitizacao.py
│   └── usuarios.json
├── ui/
│   ├── banco.py
│   ├── login.py
│   ├── mapeamento.py
│   ├── modulos.py
│   ├── resultado.py
│   ├── tema.py
│   ├── upload.py
│   └── validacao.py
├── entradas/
└── saidas/
```

## Requisitos

- Python 3.14
- MySQL 8.0+
- Banco com as tabelas base `loja` e `varejista`
- As tabelas `aliases_loja`, `mapeamento_colunas`, `varejista_grupo` e `varejista_grupo_item` sao criadas/gerenciadas pelo app

## Instalacao

### 1. Criar e ativar o ambiente virtual

```powershell
python -m venv .venv
.venv\Scripts\Activate
```

Se o PowerShell bloquear a ativacao:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.venv\Scripts\Activate
```

### 2. Instalar as dependencias

```powershell
pip install -r requirements.txt
```

### 3. Configurar o `.env`

Use o `.env.example` como modelo:

```env
DB_HOST=localhost
DB_PORT=3306
DB_NAME=nome_do_banco
DB_USER=root
DB_PASSWORD=sua_senha
```

### 4. Criar o primeiro usuario

```python
from ui.login import adicionar_usuario
adicionar_usuario("seu_usuario", "sua_senha")
```

### 5. Executar o app

```powershell
python app.py
```

## Fluxo de uso

```text
Login
  -> Selecionar banco
  -> Menu principal
      -> Tratamento de Bases
      -> Configurar Mapeamento
      -> Lojas Pendentes
      -> Grupos de Varejistas
```

## Funcionalidades

### Tratamento de bases

- Leitura robusta de Excel com deteccao automatica do cabecalho
- Tratamento de celulas mescladas
- Conversao numerica automatica
- Separacao de mes e ano
- Colunas calculadas
- Colunas novas com valor fixo, ano atual ou formula
- Exportacao final em Excel
- Pre-visualizacao das primeiras linhas antes do processamento

### Cruzamentos

- Lojas por ID direto
- Lojas por matricula
- Lojas por `cluster_9`
- Lojas por numero extraido do nome
- Lojas por alias salvo
- EAN com setor de produto
- Varejista em bases consolidadas

### Operacao

- Persistencia local de pendencias por banco
- Vinculacao manual de lojas pendentes
- Historico de aliases por varejista
- Agrupamento de varejistas
- Download da base completa
- Download separado por varejista
- Download separado de varejistas nao registrados

## Arquivos gerados pelo app

### Saidas do processamento

- Bases tratadas sao exportadas em `saidas/`
- Na tela de resultado tambem e possivel salvar manualmente para outra pasta
- O download por varejista gera:
  - um arquivo para cada varejista identificado
  - um arquivo `NAO_REGISTRADO_<MES_REF>.xlsx` quando houver registros sem varejista reconhecido

### Dados locais da aplicacao

```text
~/.mavi_bases/
├── logs/
│   ├── app.log
│   └── audit_YYYY_MM.json
└── pendencias/
    └── <banco>.json
```

## Seguranca

- Senhas com PBKDF2-SHA256
- Comparacao com `hmac.compare_digest`
- Rate limit de login: 5 tentativas em 60 segundos
- Queries parametrizadas
- Validacao de extensao e sanitizacao de nomes de arquivo
- Auditoria de acoes por usuario

## Arquitetura tecnica

### app.py

Responsavel por:

- iniciar a janela Flet
- controlar a sessao do usuario
- navegar entre as telas
- carregar e mesclar pendencias
- registrar auditoria

### engine/

#### conexao.py

- gerencia o pool MySQL
- troca de banco com seguranca entre threads

#### logger.py

- logger centralizado
- arquivo rotativo em `~/.mavi_bases/logs/app.log`

#### matcher.py

- carrega cache de lojas e aliases
- identifica lojas pelas estrategias configuradas
- grava aliases automaticamente e manualmente

#### transformador.py

- aplica separacao de data
- cruza loja, EAN e varejista
- renomeia colunas
- converte numericos
- calcula colunas derivadas
- sinaliza pendencias

#### processador.py

Orquestra o pipeline:

1. carrega mapeamento
2. le o Excel de forma robusta
3. remove colunas ignoradas
4. separa mes e ano
5. cruza lojas
6. cruza varejistas
7. cruza EAN
8. renomeia colunas
9. converte numericos
10. calcula colunas
11. adiciona colunas novas
12. sinaliza pendencias
13. exporta o Excel final

Tambem oferece `preview_base()` para pre-visualizacao sem exportacao.

#### exportador.py

- exporta `BASE_TRATADA`
- cria aba `LOJAS NOVAS` quando houver pendencias
- usa `xlsxwriter` com fallback para `openpyxl`

#### grupos.py

- salva e exclui grupos de varejistas
- mantem tabelas auxiliares do agrupamento

#### pendencias_store.py

- salva pendencias localmente em JSON
- mescla pendencias sem duplicar por chave

### ui/

#### login.py

- autenticacao local
- bloqueio temporario por excesso de tentativas

#### banco.py

- selecao do banco
- teste visual de conexao

#### modulos.py

- menu principal

#### upload.py

- selecao de arquivo
- selecao de varejista
- processamento em thread
- pre-visualizacao da base
- validacao de extensao

#### mapeamento.py

- configuracao das colunas por varejista
- renomeacao e transformacoes
- configuracao de cruzamento de varejistas
- adicao de novas colunas
- gerenciamento de grupos

#### resultado.py

- resumo do processamento
- avisos de pendencia
- download da base completa
- download por varejista

#### validacao.py

- busca de lojas por id ou nome
- vinculacao manual de pendencias
- remocao de pendencia persistida
- historico de aliases

### models/schemas.py

Principais modelos:

- `VincularLojaRequest`
- `ProcessarRequest`
- `ResultadoProcessamento`

`ResultadoProcessamento` concentra estatisticas como:

- total de linhas
- lojas identificadas
- lojas novas
- valor total
- quantidade total
- setores encontrados
- pendencias
- varejistas novos
- mes de referencia
- timings das etapas

## Banco de dados

### Tabelas principais

- `loja`
- `varejista`
- `aliases_loja`
- `mapeamento_colunas`
- `varejista_grupo`
- `varejista_grupo_item`

### Persistencia de aliases

Quando uma loja e vinculada manualmente, o alias fica salvo e passa a ser reconhecido nas proximas execucoes.

## Observacoes de compatibilidade

- O projeto esta ajustado para Python 3.14
- `pandas` esta na faixa `>=3.0.0,<3.1.0`
- `openpyxl` esta na faixa `>=3.1.5,<3.2.0`

## Logs

| Arquivo              | Localizacao           | Descricao            |
| -------------------- | --------------------- | -------------------- |
| `app.log`            | `~/.mavi_bases/logs/` | Log tecnico rotativo |
| `audit_YYYY_MM.json` | `~/.mavi_bases/logs/` | Auditoria mensal     |

## Proximos cuidados

- manter o `.env` fora do versionamento
- manter `usuarios.json` fora do Git
