# Documentação Técnica — Mavi Bases

**Versão:** 1.0  
**Stack:** Python 3.14 · Flet 0.84 · MySQL · pandas 3.x · openpyxl · Pydantic v2

---

## Índice

1. [Visão geral da arquitetura](#1-visão-geral-da-arquitetura)
2. [Configuração e inicialização](#2-configuração-e-inicialização)
3. [Camada de dados — engine/](#3-camada-de-dados--engine)
   - 3.1 [conexao.py](#31-conexaopy)
   - 3.2 [logger.py](#32-loggerpy)
   - 3.3 [matcher.py](#33-matcherpy)
   - 3.4 [transformador.py](#34-transformadorpy)
   - 3.5 [processador.py](#35-processadorpy)
   - 3.6 [mapeamento_loader.py](#36-mapeamento_loaderpy)
   - 3.7 [exportador.py](#37-exportadorpy)
   - 3.8 [grupos.py](#38-grupospy)
   - 3.9 [pendencias_store.py](#39-pendencias_storepy)
4. [Camada de segurança — security/](#4-camada-de-segurança--security)
5. [Camada de interface — ui/](#5-camada-de-interface--ui)
6. [Models — Pydantic](#6-models--pydantic)
7. [Pipeline ETL completo](#7-pipeline-etl-completo)
8. [Banco de dados — estrutura de tabelas](#8-banco-de-dados--estrutura-de-tabelas)
9. [Fluxo de autenticação](#9-fluxo-de-autenticação)
10. [Persistência local de dados](#10-persistência-local-de-dados)
11. [Convenções e padrões adotados](#11-convenções-e-padrões-adotados)

---

## 1. Visão geral da arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                      app.py (Flet)                      │
│   Gerencia sessão, navegação entre telas e callbacks    │
└────────────────────────┬────────────────────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │           ui/                   │
        │  login · banco · modulos        │
        │  upload · mapeamento            │
        │  resultado · validacao          │
        └────────────────┬────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │           engine/               │
        │  processador (orquestrador)     │
        │  transformador · matcher        │
        │  mapeamento_loader              │
        │  exportador · grupos            │
        │  conexao · logger               │
        │  pendencias_store               │
        └────────────────┬────────────────┘
                         │
        ┌────────────────▼────────────────┐
        │           MySQL                 │
        │  loja · varejista               │
        │  aliases_loja · mapeamento      │
        │  varejista_grupo                │
        └─────────────────────────────────┘
```

O app **não tem servidor HTTP** — é 100% desktop via Flet. Toda comunicação com o banco é direta via pool MySQL.

---

## 2. Configuração e inicialização

### config.py

Carrega `.env` da raiz do projeto e expõe:

| Símbolo           | Tipo   | Descrição                                             |
| ----------------- | ------ | ----------------------------------------------------- |
| `DB_CONFIG`       | `dict` | Parâmetros de conexão MySQL                           |
| `ENV_CONFIGURADO` | `bool` | `True` se `DB_USER` e `DB_PASSWORD` estão definidos   |
| `ENV_AUSENTE`     | `bool` | `True` se o arquivo `.env` não existe                 |
| `PASTA_ENTRADA`   | `str`  | Path absoluto de `entradas/` (criado automaticamente) |
| `PASTA_SAIDA`     | `str`  | Path absoluto de `saidas/` (criado automaticamente)   |

### app.py

Ponto de entrada (`ft.run(main)`). Responsabilidades:

- Inicializa a janela Flet (800×650, tema dark)
- Mantém o objeto `sessao` com estado da sessão atual:
  ```python
  sessao = {
      "usuario": str,
      "banco": str,
      "cod_varejista": int | None,
      "resultado": dict | None,
      "nome_varejista": str,
      "pendencias": list,
  }
  ```
- Ao selecionar banco, carrega pendências persistidas via `pendencias_store.carregar()`
- Ao receber resultado de processamento, mescla pendências via `pendencias_store.mesclar()`
- Registra ações de auditoria (`audit.registrar`) em login, seleção de banco e processamentos
- Limpa arquivos de entrada com mais de 24h na inicialização

---

## 3. Camada de dados — engine/

### 3.1 conexao.py

Pool de conexões MySQL com controle de concorrência.

```python
configurar_banco(nome_banco: str)  # troca banco de forma thread-safe
get_conexao() -> Connection        # retorna conexão do pool
testar_conexao() -> dict           # {"ok": bool, "versao": str}
```

**Detalhes:**

- Pool de 5 conexões com `connection_timeout=10s`
- `threading.Lock` protege a criação/reset do pool
- `configurar_banco()` atualiza `os.environ["DB_NAME"]` e zera o pool
- Toda mudança de banco passa por esta função — nunca setar `os.environ` diretamente

---

### 3.2 logger.py

Logger centralizado. Uso em qualquer módulo:

```python
from engine.logger import get_logger
_log = get_logger(__name__)
_log.info("mensagem")
_log.error("erro %s", ex, exc_info=True)
```

- **Arquivo:** `~/.mavi_bases/logs/app.log` (rotativo 5 MB × 3 backups)
- **Console:** apenas nível ERROR+ no stderr
- **Formato:** `2026-04-17 10:30:00 [INFO    ] processador: mensagem`

---

### 3.3 matcher.py

Identificação de lojas pela base de dados em cache.

#### Carregamento de cache

```python
carregar_cache(cod_varejista: int) -> dict
```

Retorna:

```python
{
    "id_loja":   {"123": (123, "NOME LOJA"), ...},
    "cluster_9": {"456": (123, "NOME LOJA"), ...},
    "alias":     {"SUPERMERCADO X": (123, "NOME LOJA"), ...},
}
```

#### Identificação — 5 estratégias em cascata

```python
identificar_loja(matricula, nome_loja, cod_varejista, id_direto, cache) -> dict
```

| #   | Estratégia       | Fonte                                       |
| --- | ---------------- | ------------------------------------------- |
| 0   | ID direto        | `coluna_id_direto` → `cache["id_loja"]`     |
| 1   | Matrícula direta | `col_matricula` → `cache["id_loja"]`        |
| 2   | Cluster 9        | `col_matricula` → `cache["cluster_9"]`      |
| 3   | Número no nome   | extrai dígitos do nome → `cache["id_loja"]` |
| 4   | Alias            | nome normalizado → `cache["alias"]`         |

Quando cluster_9 ou número-no-nome acham match, o nome é salvo automaticamente como alias:

```python
salvar_aliases(cod_varejista, [(cod, nome_norm, id_loja), ...])
```

#### Vinculação manual

```python
vincular_loja_manualmente(cod_varejista, nome_alias, id_loja)
```

Insere diretamente em `aliases_loja`. Próxima execução já reconhece a loja.

---

### 3.4 transformador.py

Todas as transformações do pipeline. Todas recebem e retornam `pd.DataFrame`.

#### `_ler_excel_robusto(caminho)` ← ver processador.py

#### `separar_mes_ano(df, cfg)`

```python
cfg = {"COLUNA_DATA": ("MÊS", "ANO")}
```

Suporta 8+ formatos: `dez./25`, `dez/2025`, `01-01-2025`, `01/01/2025`, `2025-01-01`, `01/2025`, `2025-01`, timestamp.

#### `cruzar_loja(df, cfg, cod_varejista) -> (df, pendencias, saida_id)`

**Totalmente vetorizado** — usa `pd.Series.map()` em cascata pelas 5 estratégias sem loop Python.

Colunas produzidas:

- `LOJA` (ou `saida_id`): valor original da base
- `COD_LOJA` (ou `saida_cod`): `id_loja` do banco, ou id original se não encontrou
- `BANCO` (ou `saida_nome`): nome da loja no banco, ou nome PDV se não encontrou
- `_LOJA_OK_`: flag booleana temporária consumida por `sinalizar_pendencias`

#### `cruzar_ean(df, cfg)`

Cruza a coluna EAN com `produto_ean` no banco e cria coluna `SETOR_PRODUTO`. Nunca sobrescreve a coluna EAN original.

#### `cruzar_varejista(df, cfg) -> (df, novos)`

**Vetorizado.** Cria coluna `VAREJISTA_BANCO` e coluna temporária `_COD_VAR_` (cod_varejista por linha para bases consolidadas).

#### `renomear_colunas(df, cfg)`

```python
cfg = {"NOME_ORIGINAL": "NOME_NOVO", ...}
```

#### `converter_numericos(df, colunas_protegidas)`

Tenta converter cada coluna para numérico. Threshold: 80% dos valores não-nulos convertíveis. Suporta `1.234,56` (BR) e `1,234.56` (US).

#### `calcular_colunas(df, cfg)`

```python
cfg = {"QUANTIDADE": ("VALOR", "/", "PRECO")}
# operadores: / * + -
```

#### `adicionar_colunas_novas(df, novas, rename_map)`

Suporta valor fixo, ano atual, fórmulas de cálculo entre colunas. `rename_map` resolve nomes pré-renomeação.

#### `sinalizar_pendencias(df, pendencias, saida_nome)`

Usa a flag `_LOJA_OK_` para marcar coluna `PENDENCIA` como `"SIM"` / `""`. Remove a flag após uso.

---

### 3.5 processador.py

Orquestrador do pipeline ETL completo.

#### `_ler_excel_robusto(caminho) -> pd.DataFrame`

Leitura inteligente com `openpyxl`:

1. **Desunifica células mescladas** — preenche o valor âncora em toda a região
2. **Detecta linha de cabeçalho** — varre as primeiras 15 linhas, escolhe a com mais células preenchidas com texto real
3. **Remove colunas e linhas vazias** de layout
4. **Garante nomes únicos** para colunas sem cabeçalho

Isso garante leitura correta em bases com:

- Título/logo acima da tabela
- Colunas agrupadas com células mescladas
- Cabeçalho em linha 2, 3, etc.

#### `preview_base(caminho, cod_varejista, n_linhas=10) -> dict`

Executa todo o pipeline nas primeiras `n_linhas` **sem exportar**. Retorna:

```python
{"ok": bool, "colunas": list, "linhas": list[list], "erro": str | None}
```

#### `processar_base(caminho, cod_varejista, nome_varejista, on_status) -> dict`

Pipeline completo. Etapas com pesos de progresso:

| Etapa                     | Peso acumulado |
| ------------------------- | -------------- |
| Carregar mapeamento       | 5%             |
| Ler Excel                 | 15%            |
| Remover colunas ignoradas | 17%            |
| Separar data              | 20%            |
| Identificar lojas         | 58%            |
| Cruzar varejistas         | 64%            |
| Cruzar EANs               | 70%            |
| Renomear colunas          | 72%            |
| Converter numéricos       | 78%            |
| Calcular colunas          | 82%            |
| Adicionar novas colunas   | 85%            |
| Sinalizar pendências      | 88%            |
| Exportar Excel            | 100%           |

Ao concluir, loga um resumo completo com timings de cada etapa:

```
Processamento 'VAREJISTA X' concluído em 4.32s | linhas=12500 lojas_ok=11800 pendencias=23 | etapas: read_excel=1.2s | cruzar_loja=0.8s | ...
```

Retorna `ResultadoProcessamento.model_dump()` (ver seção 6).

---

### 3.6 mapeamento_loader.py

Carrega configuração de mapeamento do banco para um `cod_varejista`.

```python
carregar(cod_varejista: int) -> dict
```

Retorna:

```python
{
    "separar":          {"COL_DATA": ("MÊS", "ANO")},
    "cruzar_loja":      {"coluna_matricula": ..., "saida_id": ..., ...},
    "cruzar_ean":       {"coluna_ean": ..., "saida_setor": ...},
    "cruzar_varejista": {"coluna_entrada": ..., "saida": ..., "permitidos": set()},
    "renomear":         {"ORIG": "DEST", ...},
    "calcular":         {"SAIDA": ("COL_A", "/", "COL_B")},
    "novas":            [{"coluna_saida": ..., "tipo": ..., "valor": ...}],
    "ignorar":          ["COL1", "COL2"],
}
```

Mantém compatibilidade com formatos legados (`separar_mes` + `separar_ano` antigos).

---

### 3.7 exportador.py

```python
salvar_excel(df, pendencias, nome_varejista) -> str  # caminho do arquivo temp
```

- Tenta `xlsxwriter` primeiro (mais rápido), fallback para `openpyxl`
- Arquivo temporário com `delete=False` — caller responsável por mover/deletar
- Em caso de falha, remove o temp antes de relançar a exceção
- Cria aba `BASE_TRATADA` + aba `LOJAS NOVAS` se houver pendências

---

### 3.8 grupos.py

Gerencia grupos de varejistas (conjunto nomeado para uso em `cruzar_varejista`).

```python
carregar_grupos() -> list[dict]
salvar_grupo(nome_grupo, cod_varejistas) -> int   # id_grupo
excluir_grupo(id_grupo)
```

- Tabelas criadas automaticamente na primeira chamada (flag `_tabelas_garantidas` evita re-execução)
- Tabelas: `varejista_grupo` + `varejista_grupo_item` (com CASCADE)

---

### 3.9 pendencias_store.py

Persistência de pendências por banco em JSON local.

```
~/.mavi_bases/pendencias/<nome_banco>.json
```

```python
carregar(banco: str) -> list
salvar(banco: str, pendencias: list)
mesclar(banco: str, novas: list) -> list   # merge sem duplicatas por "chave"
limpar(banco: str)
```

- `chave` é `f"{id_original}|{nome_pdv}"` — identificador único por loja não encontrada
- Ao vincular uma loja em `validacao.py`, a pendência é removida imediatamente do arquivo

---

## 4. Camada de segurança — security/

### audit.py

Log de ações por usuário em JSON mensal:

```
~/.mavi_bases/logs/audit_YYYY_MM.json
```

```python
registrar(usuario, acao, **kwargs)
listar_logs(ano, mes) -> list
```

### crypto.py

Criptografia de credenciais com Fernet (AES-128-CBC). Chave derivada de:

- Nome do computador
- Usuário do sistema
- Salt fixo `"mavi_salt_2026"`

> Adequado para uso single-machine. Chave muda se o usuário/hostname mudar.

### limpeza.py

```python
limpar_entradas_antigas(pasta, horas=24)  # remove arquivos de entrada antigos
excluir_seguro(caminho)                   # sobrescreve com zeros antes de deletar
```

### sanitizacao.py

```python
caminho_seguro(caminho, base_permitida) -> bool   # bloqueia path traversal
sanitizar_nome_arquivo(nome) -> str               # basename + sanitização
validar_extensao_excel(caminho) -> bool           # whitelist: .xlsx, .xls
```

### login.py — autenticação

- **Algoritmo:** PBKDF2-SHA256, 100.000 iterações, salt `"mavi_salt_2026"`
- **Comparação:** `hmac.compare_digest` (timing-constant, evita timing attack)
- **Hashes:** `security/usuarios.json` (fora do versionamento)
- **Rate limiting:** 5 tentativas por usuário em 60 segundos (contador em memória)

```python
adicionar_usuario(usuario, senha)   # gera hash e salva
```

---

## 5. Camada de interface — ui/

### tema.py

Design system centralizado. Todas as telas usam exclusivamente funções e constantes daqui.

| Símbolo      | Tipo | Valor     |
| ------------ | ---- | --------- |
| `BG`         | cor  | `#1a1a1a` |
| `BG2`        | cor  | `#232323` |
| `BG3`        | cor  | `#2a2a2a` |
| `TEAL`       | cor  | `#00d4b4` |
| `TEXT`       | cor  | `#e8e8e8` |
| `TEXT_MUTED` | cor  | `#888888` |
| `DANGER`     | cor  | `#ff4d4d` |
| `BORDER`     | cor  | `#333333` |

Funções principais:

```python
btn_primario(texto, largura, on_click)
btn_outline(texto, largura, on_click)
campo_texto(label, senha=False)
dropdown_estilo(label, opcoes)
navbar(titulo, banco, on_voltar)
snackbar_erro(page, msg)
snackbar_sucesso(page, msg)
titulo_logo()
tela_centralizada(controles)
```

### login.py

Tela de login com PBKDF2 + rate limiting. Campos de usuário e senha com submit no Enter.

### banco.py

Lista bancos MySQL disponíveis (filtra `information_schema`, `mysql`, `performance_schema`, `sys`). Ao selecionar, chama `configurar_banco()` de forma thread-safe.

Exibe tela de erro amigável se `.env` estiver ausente ou incompleto.

### modulos.py

Menu principal com 4 botões:

- Tratamento de Bases
- Configurar Mapeamento
- Lojas Pendentes
- Grupos de Varejistas

### upload.py

Tela de seleção de varejista + arquivo Excel.

- Seletor de arquivo via `tkinter.filedialog`
- Validação de extensão (`.xlsx`, `.xls`)
- Processamento em thread separada (não bloqueia UI)
- Barra de progresso com mensagem de etapa atual
- Botão **"Pré-visualizar"**: executa `preview_base()` e exibe resultado em tabela numa dialog

### mapeamento.py

Configuração de mapeamento por varejista. Permite configurar para cada coluna da base:

- Tipo de ação: separar data, cruzar loja, cruzar EAN, cruzar varejista, renomear, calcular quantidade, ignorar
- Campos de entrada/saída específicos por tipo
- Adicionar "novas colunas" com valor fixo, ano atual ou cálculo
- Gerenciar grupos de varejistas inline

Ao reabrir, carrega o mapeamento salvo e pré-popula todos os campos.

### resultado.py

Exibe estatísticas do processamento:

- Total de linhas, lojas identificadas, lojas pendentes
- Total de valor e quantidade (quando disponíveis)
- Setores únicos encontrados
- Botão download do arquivo completo
- Botão download por varejista (para bases consolidadas)
- Botão ir para Lojas Pendentes

### validacao.py

Lista lojas não encontradas com campo de busca pesquisável (com autocomplete em tempo real, máx 15 resultados, filtra por id ou nome).

Ao vincular:

1. Salva alias em `aliases_loja` via `vincular_loja_manualmente()`
2. Remove a pendência do `pendencias_store`
3. Marca o card como "✅ Vinculado" visualmente

---

## 6. Models — Pydantic

### VincularLojaRequest

```python
cod_varejista: int
nome_alias:    str
id_loja:       int
```

### ProcessarRequest

```python
cod_varejista:  int
nome_varejista: str
nome_arquivo:   str
```

### ResultadoProcessamento

```python
ok:                     bool
arquivo_saida:          str | None
total_linhas:           int | None
lojas_unicas:           int | None
lojas_ok:               int | None
lojas_novas:            int | None
total_valor:            float | None
total_quantidade:       float | None
setores:                list
pendencias:             list
varejistas_novos:       list
mes_ref:                str             # ex: "MAR_2026"
coluna_varejista_saida: str
erro:                   str | None
timings:                dict            # tempo por etapa em segundos
```

---

## 7. Pipeline ETL completo

```
Excel bruto
    │
    ▼
_ler_excel_robusto()
  ├─ Desunifica células mescladas
  ├─ Detecta linha de cabeçalho (15 primeiras linhas)
  └─ Remove linhas/colunas vazias
    │
    ▼
Remover colunas ignoradas
    │
    ▼
separar_mes_ano()  ──► MÊS, ANO
    │
    ▼
cruzar_varejista()  ──► VAREJISTA_BANCO, _COD_VAR_ (temp)
    │
    ▼
cruzar_loja()  ──► LOJA, COD_LOJA, BANCO, _LOJA_OK_ (temp)
    │
    ▼
cruzar_ean()  ──► SETOR_PRODUTO
    │
    ▼
renomear_colunas()
    │
    ▼
converter_numericos()
    │
    ▼
calcular_colunas()  ──► ex: QUANTIDADE = VALOR / PRECO
    │
    ▼
adicionar_colunas_novas()  ──► colunas fixas / fórmulas
    │
    ▼
sinalizar_pendencias()  ──► PENDENCIA = "SIM" onde _LOJA_OK_ = False
    │
    ▼
salvar_excel()  ──► aba BASE_TRATADA + aba LOJAS NOVAS
```

---

## 8. Banco de dados — estrutura de tabelas

### loja

| Coluna      | Tipo    | Descrição                         |
| ----------- | ------- | --------------------------------- |
| `id_loja`   | INT PK  | Identificador principal           |
| `nome_loja` | VARCHAR | Nome oficial                      |
| `cluster_9` | VARCHAR | Código alternativo (estratégia 2) |

### varejista

| Coluna           | Tipo    | Descrição           |
| ---------------- | ------- | ------------------- |
| `cod_varejista`  | INT PK  | Código do varejista |
| `nome_varejista` | VARCHAR | Nome do varejista   |

### aliases_loja

| Coluna          | Tipo    | Descrição                                |
| --------------- | ------- | ---------------------------------------- |
| `cod_varejista` | INT     | FK varejista                             |
| `nome_alias`    | VARCHAR | Nome normalizado (uppercase, sem acento) |
| `id_loja`       | INT     | FK loja                                  |

PK composta `(cod_varejista, nome_alias)`. `INSERT IGNORE` para evitar duplicatas.

### mapeamento_coluna

Gerenciada pela tela de mapeamento. Armazena as configurações de transformação por varejista.

### varejista_grupo + varejista_grupo_item

| Tabela                 | Colunas principais                |
| ---------------------- | --------------------------------- |
| `varejista_grupo`      | `id_grupo`, `nome_grupo` (UNIQUE) |
| `varejista_grupo_item` | `id_grupo` FK, `cod_varejista`    |

Criadas automaticamente pelo app na primeira execução.

---

## 9. Fluxo de autenticação

```
Usuario digita login/senha
    │
    ▼
_bloqueado(usuario)?  ──► SIM → "Aguarde 1 minuto" (máx 5 tentativas/60s)
    │ NÃO
    ▼
_verificar_senha(usuario, senha)
  └─ PBKDF2-SHA256(senha, salt, 100_000).hex()
  └─ hmac.compare_digest(hash_tentativa, hash_salvo)
    │
    ▼
on_sucesso(usuario) → audit.registrar("LOGIN") → tela_banco
```

Hashes ficam em `security/usuarios.json`:

```json
{
  "gabriel": "05b5f386...",
  "admin": "a1b2c3d4..."
}
```

Para adicionar usuário:

```python
from ui.login import adicionar_usuario
adicionar_usuario("novo_usuario", "senha_forte")
```

---

## 10. Persistência local de dados

Todos os dados locais ficam em `~/.mavi_bases/`:

```
~/.mavi_bases/
├── logs/
│   ├── app.log           ← log técnico (rotativo 5MB × 3)
│   ├── audit_2026_04.json  ← auditoria mensal
│   └── audit_2026_03.json
└── pendencias/
    ├── banco_producao.json
    └── banco_homolog.json
```

### Formato das pendências

```json
[
  {
    "chave": "042|SUPERMERCADO NOVO",
    "id_original": "042",
    "matricula": "042",
    "nome_pdv": "SUPERMERCADO NOVO",
    "id_loja": null
  }
]
```

---

## 11. Convenções e padrões adotados

### Colunas temporárias internas

| Coluna      | Origem             | Consumida por          |
| ----------- | ------------------ | ---------------------- |
| `_LOJA_OK_` | `cruzar_loja`      | `sinalizar_pendencias` |
| `_COD_VAR_` | `cruzar_varejista` | `cruzar_loja`          |

Ambas são sempre removidas ao final do pipeline — nunca aparecem no arquivo de saída.

### Normalização de texto

Todos os cruzamentos por nome usam `normalizar()` do `matcher.py`:

- Strip + UPPER
- Remove acentos (NFKD decomposition)

Garante que `"São Paulo"`, `"SAO PAULO"`, `"são paulo"` são equivalentes.

### `mes_ref`

Formato `"MMM_YYYY"` derivado das colunas `MÊS` e `ANO` após transformação. Ex.: `"MAR_2026"`. Usado para nomear arquivos de saída.

### Threading na UI

Processamento e preview rodam em `threading.Thread(daemon=True)`. A UI é atualizada via `page.update()` chamado da thread worker — thread-safe no Flet.

### Overlays e dialogs

Todos os dialogs e overlays usam `page.overlay.append(dlg)` + `dlg.open = True` + `page.update()`. Fechamento via `page.close(dlg)`.
