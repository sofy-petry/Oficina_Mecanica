# 🔧 Sistema de Controle de Oficina Mecânica

Projeto da disciplina de **Banco de Dados**: modelagem, banco relacional em **PostgreSQL**, gatilhos (triggers) e uma
**aplicação web em Python (Flask)** que usa o banco para cadastrar e consultar clientes, veículos, ordens de serviço,
peças, estoque, fornecedores e pagamentos.

> **Autoras:** _Sofia Soares e Elane Souza_ · **Disciplina:** Banco de Dados

---

## 📑 Sumário

1. [Visão geral das etapas](#-visão-geral-das-etapas)
2. [Parte 1 – Modelagem conceitual (DER)](#-parte-1--modelagem-conceitual-der)
3. [Parte 2 – Modelo relacional e esquema SQL](#-parte-2--modelo-relacional-e-esquema-sql)
4. [Parte 3 – Gatilhos (triggers)](#-parte-3--gatilhos-triggers)
5. [Parte 4 – Aplicação web](#-parte-4--aplicação-web)
6. [Como o Python se conecta ao PostgreSQL](#-como-o-python-se-conecta-ao-postgresql)
7. [Como o front-end foi feito](#-como-o-front-end-foi-feito)
8. [Como executar o projeto](#-como-executar-o-projeto)
9. [Estrutura de pastas](#-estrutura-de-pastas)
---

## 🧭 Visão geral das etapas

| Etapa | O que foi feito | Onde está |
|------|-----------------|-----------|
| **Parte 1** | Diagrama Entidade-Relacionamento (DER) do sistema | `docs/` (PDF) |
| **Parte 2** | Modelo relacional (notação textual) e script SQL de criação das tabelas | `docs/` e `database/01_esquema.sql` |
| **Parte 3** | Funções e gatilhos em PL/pgSQL que aplicam regras de negócio dentro do banco | `database/02_gatilhos.sql` |
| **Parte 4** | Aplicação web Flask em três camadas, ligada ao PostgreSQL | `app/`, `run.py` |

---

## 🗺️ Parte 1 – Modelagem conceitual (DER)

O sistema controla o dia a dia de uma oficina: quem são os clientes e seus veículos, quais serviços e peças entram em
cada ordem de serviço (OS), como o estoque é reposto com fornecedores e como o cliente paga.

**Principais entidades:** Cliente (Físico / Jurídico), Veículo, Mecânico, Serviço, Ordem de Serviço (com Orçamento),
Pagamento, Parcela, Peça, Fornecedor, Pedido de Peça e Movimentação de Estoque.

**Decisões de modelagem importantes**

- **Especialização de Cliente:** todo cliente é pessoa física (CPF) **ou** jurídica (CNPJ). O campo `tipo_cliente`
  (`'F'` ou `'J'`) indica qual.
- **Atributo multivalorado:** um cliente pode ter vários telefones; uma peça pode servir para várias marcas e modelos.
- **Orçamento fundido na OS (1:1):** como cada OS tem exatamente um orçamento, os campos do orçamento
  (`subtotal_pecas`, `subtotal_mao_obra`, `desconto`, `valor_total`) ficam dentro da própria `Ordem_Servico`.
- **Relacionamentos N:M com atributos:** uma OS tem vários serviços e várias peças, e o relacionamento guarda
  quantidade, valor cobrado e se está em garantia.
- **Fornecimento (N:M):** cada fornecedor vende várias peças, com **preço praticado** e **prazo de entrega** próprios.

---

## 🗄️ Parte 2 – Modelo relacional e esquema SQL

O modelo relacional resultante tem **20 tabelas**. Notação: `#` chave primária, `&` chave estrangeira, `[ ]` atributo opcional.

```text
Cliente(#id_cliente, nome, endereco, [email], tipo_cliente)
Cliente_Fisico(#&id_cliente, cpf)
Cliente_Juridico(#&id_cliente, cnpj)
Telefone(#&id_cliente, #numero)
Veiculo(#id_veiculo, placa, marca, modelo, ano_fabricacao, cor, numero_chassi, quilometragem_atual, [observacoes], &id_cliente)
Mecanico(#id_mecanico, nome, cpf, dta_admissao, especialidade, percentual_comissao)
Servico(#id_servico, codigo, descricao, tempo_medio_execucao, valor_mao_obra, categoria, [periodo_garantia])
Ordem_Servico(#id_ordem_servico, numero_sequencial, dta_entrada, hra_entrada, quilometragem_entrada, descricao_problema, status, ..., &id_veiculo, [&id_mecanico_responsavel])
Pagamento(#id_pagamento, codigo, forma_pagamento, valor_total, numero_parcelas, &id_ordem_servico)
Parcela(#&id_pagamento, #numero_parcela, valor_parcela, dta_vencimento, [dta_pagamento], status)
Peca(#id_peca, codigo, descricao, fabricante, [cod_fabricante], qtd_estoque, qtd_minimo, preco_custo, preco_venda, [periodo_garantia])
Peca_Marca(#&id_peca, #nome_marca)
Peca_Modelo(#&id_peca, #nome_modelo)
Fornecedor(#id_fornecedor, cnpj, razao_social, telefone, [email], endereco, [condicao_pagamento])
Fornecimento(#&id_fornecedor, #&id_peca, preco_praticado, prazo_entrega)
Pedido_Peca(#id_pedido_peca, codigo_pedido, data_pedido, [previsao_entrega], status, valor_total, &id_fornecedor, [&id_ordem_servico])
Item_Pedido(#id_item_pedido, quantidade, valor_unitario, valor_total, &id_pedido_peca, &id_peca)
Servico_OS(#id_servico_os, quantidade, valor_cobrado, em_garantia, &id_ordem_servico, &id_servico, [&id_mecanico])
Item_Peca_OS(#id_item_peca_os, qtd_utilizada, valor_unitario, valor_total, em_garantia, &id_ordem_servico, &id_peca)
Movimentacao_Estoque(#id_movimentacao_estoque, codigo, data_movimentacao, hora_movimentacao, tipo, quantidade, &id_peca, [&id_item_pedido], [&id_item_peca_os])
```

### Pontos importantes do script SQL (`database/01_esquema.sql`)

- **Chaves primárias `SERIAL`:** o PostgreSQL gera o `id` automaticamente (1, 2, 3…).
- **Especialização:** `Cliente_Fisico` e `Cliente_Juridico` usam como chave primária o próprio `id_cliente`
  (que também é chave estrangeira para `Cliente`) com `ON DELETE CASCADE`.
- **Chaves compostas:** `Telefone`, `Parcela`, `Peca_Marca`, `Peca_Modelo` e `Fornecimento` identificam cada linha pela
  combinação de duas colunas.
- **Restrições `CHECK`** garantem dados válidos já no banco, por exemplo:
  - `status` da OS só aceita `aguardando peças`, `em execução`, `aguardando aprovação`, `concluída`, `entregue`, `cancelada`;
  - `quilometragem_atual >= 0`, `ano_fabricacao > 1900`;
  - `preco_venda >= preco_custo`;
  - `percentual_comissao` entre 0 e 100;
  - `forma_pagamento` limitada a dinheiro, cartão de crédito/débito, pix e boleto.
- **`UNIQUE`:** placa, chassi, CPF, CNPJ e códigos não se repetem.
- **Políticas de exclusão (`ON DELETE`):**
  - `RESTRICT` impede apagar algo que ainda é usado (ex.: um cliente que tem veículos);
  - `CASCADE` apaga os dependentes junto (ex.: telefones de um cliente apagado);
  - `SET NULL` mantém o registro e limpa a referência (ex.: mecânico responsável).
- **Rastreabilidade do estoque:** `Movimentacao_Estoque` aponta para o item de pedido (entrada) **ou** para o item usado
  na OS (saída), então dá para saber a origem de cada movimento.
- O início do script faz `DROP TABLE IF EXISTS ... CASCADE`, então ele pode ser executado de novo para **reiniciar o banco**.

---

## ⚙️ Parte 3 – Gatilhos (triggers)

Regras de negócio importantes foram colocadas **dentro do banco**, com funções PL/pgSQL e gatilhos
(`database/02_gatilhos.sql`). Assim, valem para qualquer aplicação que use o banco, não só para o site.
Cada gatilho é composto por uma **função** (`fn_...`, onde está a lógica) e um **gatilho** (`tg_...`/`trg_...`, que diz
em qual tabela e momento ela dispara: `BEFORE` antes de gravar, `AFTER` depois).

| Gatilho | Tabela / momento | O que faz |
|---------|------------------|-----------|
| `tg_calcula_valor_total_item_os` | `item_peca_os` · before insert/update | Calcula `valor_total = qtd_utilizada × valor_unitario`. |
| `tg_valida_compatibilidade_peca_os` | `item_peca_os` · before insert/update | Se a peça tem marcas/modelos cadastrados (`Peca_Marca`, `Peca_Modelo`), só aceita veículo compatível. Peça sem restrição serve para qualquer veículo. |
| `tg_atualiza_estoque_item_os` | `item_peca_os` · after insert/update/delete | **Insert:** verifica estoque, dá baixa e registra `SAIDA`. **Update:** ajusta pela diferença de quantidade (não permite trocar a peça). **Delete:** devolve ao estoque e registra `ENTRADA`. Estoque insuficiente gera erro. |
| `tg_recalcula_totais_os_peca` / `_servico` | `item_peca_os` e `servico_os` · after insert/update/delete | Recalcula `subtotal_pecas`, `subtotal_mao_obra` e `valor_total` da OS. **Itens em garantia não são cobrados.** |
| `trg_limitar_desconto_os` | `ordem_servico` · before insert/update | O desconto não pode passar de **20%** da soma de peças + mão de obra; mantém `valor_total` coerente com o desconto. |
| `trg_controle_status_os` | `ordem_servico` · before update | OS `cancelada` ou `entregue` não muda mais de status; não deixa **concluir/entregar OS vazia** (sem serviço e sem peça); ao entregar, preenche `dta_saida` e `hra_saida`. |
| `trg_bloquear_servico_os` / `trg_bloquear_peca_os` | `servico_os` e `item_peca_os` · before insert/update/delete | OS `concluída`, `entregue` ou `cancelada` não aceita mais incluir, alterar ou remover itens. |
| `trg_atualiza_km` | `ordem_servico` · after insert | Ao abrir a OS, atualiza a `quilometragem_atual` do veículo se a km de entrada for maior. |
| `tg_gerar_parcelas_pagamento` | `pagamento` · after insert | Gera as parcelas automaticamente, com vencimentos mensais (primeira em 1 mês). A **última parcela absorve a diferença de centavos** do arredondamento. |
| `tg_processa_entrega_pedido_peca` | `pedido_peca` · after update of status | Ao marcar o pedido como `entregue`, soma os itens ao estoque e registra `ENTRADA`. Pedido entregue não pode voltar atrás (evita entrada duplicada). |
| `trg_padronizar_nome_cliente` | `cliente` · before insert/update | Grava o nome do cliente em letras **maiúsculas**. |
| `trg_proteger_peca_com_estoque` | `peca` · before delete | Impede apagar peça que ainda tem unidades em estoque. |

Os códigos das movimentações de estoque (`mov-os-...`, `mov-ped-...`) são gerados pela sequência `seq_codigo_movimentacao`,
o que evita códigos repetidos.

As mensagens de erro dos gatilhos (`RAISE EXCEPTION`) são capturadas pelo Python e **mostradas na tela** para o usuário.

---

## 🖥️ Parte 4 – Aplicação web

Aplicação em **Python + Flask** sobre o PostgreSQL, organizada em **três camadas**:

```text
 Navegador ──► apresentação ──► negócio ──► dados ──► PostgreSQL
              (rotas+HTML)     (services)    (DAOs)
                     └────── modelo (entidades) ──────┘
```

| Camada | Pasta | Responsabilidade |
|--------|-------|------------------|
| **Apresentação** | `app/apresentacao/` | Rotas Flask, templates HTML, CSS e JavaScript. Só conversa com os *services*; não conhece SQL. |
| **Negócio** | `app/negocio/` | *Services*: validam os dados digitados, aplicam regras de fluxo e controlam as transações. |
| **Dados** | `app/dados/` | *DAOs* e conexão. É o **único lugar com SQL**. Traduz erros do PostgreSQL em mensagens amigáveis. |
| **Modelo** | `app/modelo/` | Entidades de domínio (`dataclasses`) usadas pelas três camadas. |

Fluxo de uma requisição: `rota → service → DAO → PostgreSQL`, e o resultado volta como entidades até o template.

### Funcionalidades

| Tela | Inserir | Consultar |
|------|:------:|:---------:|
| Painel | | 4 indicadores e lista das OS abertas |
| Clientes (PF/PJ, telefones) | ✔ | ✔ busca, ficha com veículos e histórico de OS |
| Veículos | ✔ | ✔ ficha com histórico de manutenção |
| Mecânicos | ✔ | ✔ OS atendidas, produção e comissão estimada |
| Serviços (catálogo) | ✔ | ✔ |
| Peças e estoque | ✔ | ✔ |
| Movimentações de estoque | automáticas | ✔ |
| Fornecedores | ✔ e vínculo de peças com preço e prazo | ✔ |
| Pedidos de peças | ✔ total ao vivo | ✔ filtro por status |
| Ordens de serviço | ✔ abrir OS | ✔ filtro por status, detalhe com barra de andamento |
| Itens da OS (serviços e peças) | ✔ lançar / remover | ✔ |
| Orçamento da OS | ✔ desconto e totais | ✔ |
| Pagamento parcelado | ✔ registrar / dar baixa | ✔ |

---

## 🔌 Como o Python se conecta ao PostgreSQL

### 1. Biblioteca usada

A conexão é feita com o **driver `psycopg2`** (adaptador PostgreSQL para Python), instalado pelo pacote
`psycopg2-binary`. O `requirements.txt` do projeto tem apenas duas dependências:

```text
Flask>=3.0
psycopg2-binary>=2.9
```

O `psycopg2` é quem "fala" o protocolo do PostgreSQL: abre a conexão, envia os comandos SQL e devolve as linhas.
A versão `-binary` já vem compilada, então não precisa instalar compilador nem as bibliotecas do PostgreSQL.

> O Flask cuida apenas da parte web. **Não** usamos ORM (como SQLAlchemy): todo o SQL é escrito à mão nos DAOs, para
> aplicar na prática o que foi estudado na disciplina.

### 2. Onde ficam os dados de conexão (`.env`)

Usuário e senha **não ficam dentro do código**. Eles ficam no arquivo `.env`, na raiz do projeto:

```dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=Oficina
DB_USER=postgres
DB_PASSWORD=sua_senha_aqui
```

### 3. `config.py` lê o `.env`

O arquivo `app/config.py` lê o `.env` e monta a classe `Config`. A ordem de prioridade é:

> **variáveis de ambiente do sistema › arquivo `.env` › valores padrão do código**

```python
class Config:
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", "5432"))
    DB_NAME = os.environ.get("DB_NAME", "oficina")
    DB_USER = os.environ.get("DB_USER", "postgres")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-oficina-mecanica")
```

### 4. A classe `Banco` (`app/dados/conexao.py`)

A classe `Banco` guarda os parâmetros da `Config` (host, porta, banco, usuário e senha) e oferece o método `cursor()`.
Um **cursor** é o objeto que executa SQL e lê o resultado. O método funciona como um bloco `with`, e **cada bloco é uma transação**:

```python
with banco.cursor() as cur:
    cur.execute("SELECT * FROM Veiculo WHERE id_veiculo = %s", (3,))
    linha = cur.fetchone()
```

O que acontece por baixo, passo a passo:

1. `psycopg2.connect(host, port, dbname, user, password)` abre a conexão com o PostgreSQL;
2. `conn.set_client_encoding("UTF8")` garante os acentos corretos;
3. o bloco `with conn:` faz **`COMMIT`** automático se tudo terminar bem e **`ROLLBACK`** se ocorrer qualquer erro
   (nada é gravado pela metade);
4. o cursor é criado com **`RealDictCursor`**, então cada linha volta como **dicionário**
   (`{"id_veiculo": 3, "placa": "ABC1D23", ...}`) em vez de tupla. Esse dicionário é convertido em objeto das entidades
   (`Veiculo.de_linha(linha)`);
5. no `finally`, a conexão é sempre fechada.

Se o PostgreSQL estiver desligado ou os dados do `.env` estiverem errados (`psycopg2.OperationalError`), a aplicação
mostra uma mensagem pedindo para verificar o servidor e as variáveis `DB_*`.

### 5. Quem usa a conexão: services e DAOs

A conexão é criada uma vez em `create_app()` (`app/__init__.py`) e **injetada** nos *services*, que a repassam aos DAOs
(injeção de dependência):

```python
# app/__init__.py
banco = Banco(config)
app.extensions["servicos"] = montar_servicos(banco)
```

O *service* abre a transação e chama o DAO; o DAO executa o SQL. Exemplo real (`app/dados/veiculo_dao.py`):

```python
def inserir(self, cur, v: Veiculo) -> int:
    cur.execute(
        """INSERT INTO Veiculo (placa, marca, modelo, ano_fabricacao, cor, numero_chassi,
                                quilometragem_atual, observacoes, id_cliente)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id_veiculo""",
        (v.placa, v.marca, v.modelo, v.ano_fabricacao, v.cor, v.numero_chassi,
         v.quilometragem_atual, v.observacoes, v.id_cliente),
    )
    return cur.fetchone()["id_veiculo"]
```

Pontos importantes desse trecho:

- **`%s` + tupla de valores = consulta parametrizada.** O driver envia os valores separados do comando SQL, o que
  **evita SQL Injection**. Nunca concatenamos texto digitado pelo usuário dentro do SQL.
- **`RETURNING id_veiculo`** devolve o `id` que o `SERIAL` acabou de gerar, sem precisar de outra consulta.
- O DAO **não decide** quando dar `COMMIT`: quem controla a transação é o *service*, por isso vários passos (ex.: lançar
  peça + atualizar totais + baixar estoque) acontecem juntos ou não acontecem.

### 6. Erros do banco chegam amigáveis na tela

Quando o banco recusa uma operação, o `psycopg2` levanta uma exceção. A função `traduzir_erro()` (em `conexao.py`)
a transforma em uma mensagem legível, que vira um `ErroBanco` (`app/excecoes.py`) e é exibida pela rota:

| Exceção do psycopg2 | Quando acontece | O que o usuário vê |
|---|---|---|
| `UniqueViolation` | CPF, CNPJ, placa, chassi ou código repetido | "Já existe um veículo com esta placa." (mensagem escolhida pelo nome da constraint) |
| `RaiseException` | Um **gatilho** executou `RAISE EXCEPTION` | O texto escrito no próprio gatilho (ex.: "Estoque insuficiente...") |
| `CheckViolation` | Valor fora de um `CHECK` (ex.: km negativa) | "Valor inválido (restrição '...' violada)." |
| `ForeignKeyViolation` | Registro relacionado inexistente ou em uso | "Operação não permitida: registro relacionado inexistente ou em uso." |
| `NotNullViolation` | Campo obrigatório vazio | "Campo obrigatório não informado: ..." |

Assim, as regras da **Parte 3** (gatilhos) e as restrições da **Parte 2** aparecem diretamente no site.

### Resumo do caminho completo

```text
.env  ──►  config.py (Config)  ──►  Banco (psycopg2)  ──►  Service  ──►  DAO  ──►  SQL no PostgreSQL
```

---

## 🎨 Como o front-end foi feito

O visual do site **não foi feito em Python puro**: o Flask apenas gera páginas HTML no servidor
(*server-side rendering*). O front usa as tecnologias padrão da web:

| Tecnologia | Para quê | Onde |
|-----------|----------|------|
| **HTML + Jinja2** | Estrutura das páginas. O Jinja2 (já vem com o Flask) permite colocar dados do Python dentro do HTML (`{{ os.numero_sequencial }}`, `{% for ... %}`) e reaproveitar um layout base (menu lateral). | `app/apresentacao/templates/` |
| **CSS** | Cores, cartões, tabelas, menu lateral, etiquetas de status. | `app/apresentacao/static/style.css` |
| **JavaScript** | Pequenos comportamentos no navegador (ex.: total do pedido calculado ao vivo). | `app/apresentacao/static/app.js` |
| **Filtros Jinja** | Funções Python para formatar dinheiro (`R$ 426,67`), datas etc. nos templates. | `app/apresentacao/filtros.py` |

Funcionamento: o navegador pede uma URL → a **rota** (`rotas.py`) chama o *service* → recebe os dados →
`render_template("pagina.html", dados=...)` → o Jinja2 monta o HTML final → o navegador exibe, carregando
`style.css` e `app.js` de `/static/`. É por isso que, olhando só as pastas de Python, parece que "só tem Python".

---

## ▶️ Como executar o projeto

### Pré-requisitos

- [Python 3.10+](https://www.python.org/downloads/)
- [PostgreSQL](https://www.postgresql.org/download/) e pgAdmin
- VS Code (ou outro editor) e Git

### A) Preparar o banco no pgAdmin (uma única vez)

1. Conecte-se ao servidor PostgreSQL.
2. Botão direito em *Databases > Create > Database…* e crie o banco (ex.: **`Oficina`**).
3. Selecione o banco e abra *Tools > Query Tool*.
4. Abra cada arquivo da pasta `database/` e execute com ▶, **nesta ordem**:
   1. `01_esquema.sql` – cria as tabelas (apaga e recria se já existirem);
   2. `02_gatilhos.sql` – cria as funções e gatilhos;
   3. `03_dados_exemplo.sql` – dados de demonstração.
5. Atualize (*Refresh*) *Schemas > public > Tables*: as tabelas devem aparecer.

> O projeto **não cria** o banco nem as tabelas: ele só se conecta a um banco que já existe.

### B) Rodar a aplicação

```bash
# 1. clonar o repositório
git clone https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git
cd NOME_DO_REPOSITORIO

# 2. criar o ambiente virtual
python3 -m venv .venv

# 3. ativar o ambiente virtual
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 4. instalar as dependências
pip install -r requirements.txt

# 5. criar o .env a partir do modelo e editar com seus dados
cp .env.example .env               # Windows: copy .env.example .env

# 6. executar
python3 run.py                     # abre em http://localhost:5000
```

**O que é o ambiente virtual (`.venv`)?** É uma pasta com uma cópia isolada do Python e das bibliotecas deste projeto
(Flask, psycopg2…), instaladas a partir do `requirements.txt`. Assim o projeto não interfere em outros. Ela é grande e
específica de cada computador, por isso **não vai para o GitHub**: cada pessoa recria com os comandos acima.
(Já a pasta `__pycache__` é gerada automaticamente pelo Python com código compilado e também não é versionada.)

---

## 📁 Estrutura de pastas

```text
.
├── app/
│   ├── apresentacao/     rotas.py, filtros.py, templates/, static/ (style.css, app.js)
│   ├── negocio/          cliente_service.py, ordem_servico_service.py, mecanico_service.py, validacao.py ...
│   ├── dados/            conexao.py (Banco), cliente_dao.py, veiculo_dao.py, peca_dao.py ...
│   ├── modelo/           entidades.py (dataclasses)
│   ├── config.py         lê o .env e monta a Config
│   ├── excecoes.py       ErroNegocio / ErroBanco
│   └── __init__.py       create_app() e montagem dos objetos (injeção de dependência)
├── database/             01_esquema.sql, 02_gatilhos.sql, 03_dados_exemplo.sql
├── Modelo Lógico.txt
├── Modelo Conceitual.pdf             
├── .env                  modelo das variáveis de conexão (sem senha real)
├── requirements.txt
├── run.py                ponto de entrada
└── README.md
```
---


## 🛠️ Tecnologias

Python · Flask · Jinja2 · HTML · CSS · JavaScript · PostgreSQL · PL/pgSQL · psycopg2 · pgAdmin · Git/GitHub
