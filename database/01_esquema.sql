-- Limpeza do esquema existente (ordem reversa de dependência)
DROP TABLE IF EXISTS Movimentacao_Estoque CASCADE;
DROP TABLE IF EXISTS Item_Peca_OS CASCADE;
DROP TABLE IF EXISTS Servico_OS CASCADE;
DROP TABLE IF EXISTS Item_Pedido CASCADE;
DROP TABLE IF EXISTS Pedido_Peca CASCADE;
DROP TABLE IF EXISTS Fornecimento CASCADE;
DROP TABLE IF EXISTS Fornecedor CASCADE;
DROP TABLE IF EXISTS Peca_Modelo CASCADE;
DROP TABLE IF EXISTS Peca_Marca CASCADE;
DROP TABLE IF EXISTS Peca CASCADE;
DROP TABLE IF EXISTS Parcela CASCADE;
DROP TABLE IF EXISTS Pagamento CASCADE;
DROP TABLE IF EXISTS Ordem_Servico CASCADE;
DROP TABLE IF EXISTS Servico CASCADE;
DROP TABLE IF EXISTS Mecanico CASCADE;
DROP TABLE IF EXISTS Veiculo CASCADE;
DROP TABLE IF EXISTS Telefone CASCADE;
DROP TABLE IF EXISTS Cliente_Juridico CASCADE;
DROP TABLE IF EXISTS Cliente_Fisico CASCADE;
DROP TABLE IF EXISTS Cliente CASCADE;


CREATE TABLE Cliente (
    id_cliente SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    endereco VARCHAR(200) NOT NULL,
    email VARCHAR(100),
    tipo_cliente CHAR(1) NOT NULL CHECK (tipo_cliente IN ('F', 'J'))
);

CREATE TABLE Cliente_Fisico (
    id_cliente INT PRIMARY KEY REFERENCES Cliente(id_cliente) ON DELETE CASCADE,
    cpf VARCHAR(14) UNIQUE NOT NULL
);

CREATE TABLE Cliente_Juridico (
    id_cliente INT PRIMARY KEY REFERENCES Cliente(id_cliente) ON DELETE CASCADE,
    cnpj VARCHAR(18) UNIQUE NOT NULL
);

CREATE TABLE Telefone (
    id_cliente INT REFERENCES Cliente(id_cliente) ON DELETE CASCADE,
    numero VARCHAR(20) NOT NULL,
    PRIMARY KEY (id_cliente, numero)
);


CREATE TABLE Veiculo (
    id_veiculo SERIAL PRIMARY KEY,
    placa VARCHAR(10) UNIQUE NOT NULL,
    marca VARCHAR(50) NOT NULL,
    modelo VARCHAR(50) NOT NULL,
    ano_fabricacao INT NOT NULL CHECK (ano_fabricacao > 1900),
    cor VARCHAR(30),
    numero_chassi VARCHAR(30) UNIQUE NOT NULL,
    quilometragem_atual INT NOT NULL CHECK (quilometragem_atual >= 0),
    observacoes TEXT,
    id_cliente INT NOT NULL REFERENCES Cliente(id_cliente) ON DELETE RESTRICT
);



CREATE TABLE Mecanico (
    id_mecanico SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    cpf VARCHAR(14) UNIQUE NOT NULL,
    dta_admissao DATE NOT NULL,
    especialidade VARCHAR(50) NOT NULL CHECK (especialidade IN ('mecânica geral', 'elétrica', 'funilaria', 'pintura', 'outros')),
    percentual_comissao DECIMAL(5,2) NOT NULL DEFAULT 0.00 CHECK (percentual_comissao >= 0 AND percentual_comissao <= 100)
);



CREATE TABLE Servico (
    id_servico SERIAL PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    descricao VARCHAR(150) NOT NULL,
    tempo_medio_execucao INT NOT NULL CHECK (tempo_medio_execucao > 0), -- em minutos
    valor_mao_obra DECIMAL(10,2) NOT NULL CHECK (valor_mao_obra >= 0),
    categoria VARCHAR(50) NOT NULL,
    periodo_garantia INT DEFAULT 90 -- em dias
);



CREATE TABLE Ordem_Servico (
    id_ordem_servico SERIAL PRIMARY KEY,
    numero_sequencial VARCHAR(20) UNIQUE NOT NULL,
    dta_entrada DATE NOT NULL DEFAULT CURRENT_DATE,
    hra_entrada TIME NOT NULL DEFAULT CURRENT_TIME,
    quilometragem_entrada INT NOT NULL CHECK (quilometragem_entrada >= 0),
    descricao_problema TEXT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'aguardando peças' 
        CHECK (status IN ('aguardando peças', 'em execução', 'aguardando aprovação', 'concluída', 'entregue', 'cancelada')),
    dta_previsao_conclusao DATE,
    dta_saida DATE,
    hra_saida TIME,
    
    -- Atributos do Orçamento (Fusão 1:1)
    subtotal_pecas DECIMAL(10,2) DEFAULT 0.00 CHECK (subtotal_pecas >= 0),
    subtotal_mao_obra DECIMAL(10,2) DEFAULT 0.00 CHECK (subtotal_mao_obra >= 0),
    desconto DECIMAL(10,2) DEFAULT 0.00 CHECK (desconto >= 0),
    valor_total DECIMAL(10,2) DEFAULT 0.00 CHECK (valor_total >= 0),
    
    id_veiculo INT NOT NULL REFERENCES Veiculo(id_veiculo) ON DELETE RESTRICT,
    id_mecanico_responsavel INT REFERENCES Mecanico(id_mecanico) ON DELETE SET NULL
);


CREATE TABLE Pagamento (
    id_pagamento SERIAL PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    forma_pagamento VARCHAR(30) NOT NULL CHECK (forma_pagamento IN ('dinheiro', 'cartão de crédito', 'cartão de débito', 'pix', 'boleto')),
    valor_total DECIMAL(10,2) NOT NULL CHECK (valor_total > 0),
    numero_parcelas INT NOT NULL DEFAULT 1 CHECK (numero_parcelas >= 1),
    id_ordem_servico INT UNIQUE NOT NULL REFERENCES Ordem_Servico(id_ordem_servico) ON DELETE RESTRICT
);

CREATE TABLE Parcela (
    id_pagamento INT REFERENCES Pagamento(id_pagamento) ON DELETE CASCADE,
    numero_parcela INT NOT NULL CHECK (numero_parcela >= 1),
    valor_parcela DECIMAL(10,2) NOT NULL CHECK (valor_parcela > 0),
    dta_vencimento DATE NOT NULL,
    dta_pagamento DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente', 'pago', 'atrasado')),
    PRIMARY KEY (id_pagamento, numero_parcela)
);



CREATE TABLE Peca (
    id_peca SERIAL PRIMARY KEY,
    codigo VARCHAR(30) UNIQUE NOT NULL,
    descricao VARCHAR(150) NOT NULL,
    fabricante VARCHAR(80) NOT NULL,
    cod_fabricante VARCHAR(50),
    qtd_estoque INT NOT NULL DEFAULT 0 CHECK (qtd_estoque >= 0),
    qtd_minimo INT NOT NULL DEFAULT 1 CHECK (qtd_minimo >= 0),
    preco_custo DECIMAL(10,2) NOT NULL CHECK (preco_custo >= 0),
    preco_venda DECIMAL(10,2) NOT NULL CHECK (preco_venda >= preco_custo),
    periodo_garantia INT DEFAULT 90 -- em dias
);

CREATE TABLE Peca_Marca (
    id_peca INT REFERENCES Peca(id_peca) ON DELETE CASCADE,
    nome_marca VARCHAR(50) NOT NULL,
    PRIMARY KEY (id_peca, nome_marca)
);

CREATE TABLE Peca_Modelo (
    id_peca INT REFERENCES Peca(id_peca) ON DELETE CASCADE,
    nome_modelo VARCHAR(50) NOT NULL,
    PRIMARY KEY (id_peca, nome_modelo)
);


CREATE TABLE Fornecedor (
    id_fornecedor SERIAL PRIMARY KEY,
    cnpj VARCHAR(18) UNIQUE NOT NULL,
    razao_social VARCHAR(120) NOT NULL,
    telefone VARCHAR(20) NOT NULL,
    email VARCHAR(100),
    endereco VARCHAR(200) NOT NULL,
    condicao_pagamento VARCHAR(100)
);

CREATE TABLE Fornecimento (
    id_fornecedor INT REFERENCES Fornecedor(id_fornecedor) ON DELETE CASCADE,
    id_peca INT REFERENCES Peca(id_peca) ON DELETE CASCADE,
    preco_praticado DECIMAL(10,2) NOT NULL CHECK (preco_praticado >= 0),
    prazo_entrega INT NOT NULL CHECK (prazo_entrega >= 0), -- em dias
    PRIMARY KEY (id_fornecedor, id_peca)
);



CREATE TABLE Pedido_Peca (
    id_pedido_peca SERIAL PRIMARY KEY,
    codigo_pedido VARCHAR(30) UNIQUE NOT NULL,
    data_pedido DATE NOT NULL DEFAULT CURRENT_DATE,
    previsao_entrega DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'pendente' CHECK (status IN ('pendente', 'em trânsito', 'entregue', 'cancelado')),
    valor_total DECIMAL(10,2) DEFAULT 0.00 CHECK (valor_total >= 0),
    id_fornecedor INT NOT NULL REFERENCES Fornecedor(id_fornecedor) ON DELETE RESTRICT,
    id_ordem_servico INT REFERENCES Ordem_Servico(id_ordem_servico) ON DELETE SET NULL
);

CREATE TABLE Item_Pedido (
    id_item_pedido SERIAL PRIMARY KEY,
    quantidade INT NOT NULL CHECK (quantidade > 0),
    valor_unitario DECIMAL(10,2) NOT NULL CHECK (valor_unitario >= 0),
    valor_total DECIMAL(10,2) NOT NULL CHECK (valor_total >= 0),
    id_pedido_peca INT NOT NULL REFERENCES Pedido_Peca(id_pedido_peca) ON DELETE CASCADE,
    id_peca INT NOT NULL REFERENCES Peca(id_peca) ON DELETE RESTRICT,
    CONSTRAINT uk_pedido_peca UNIQUE (id_pedido_peca, id_peca)
);

-- vincular Serviços e Ordem de Serviço (N:M)
CREATE TABLE Servico_OS (
    id_servico_os SERIAL PRIMARY KEY,
    quantidade INT NOT NULL DEFAULT 1 CHECK (quantidade > 0),
    valor_cobrado DECIMAL(10,2) NOT NULL CHECK (valor_cobrado >= 0),
    em_garantia BOOLEAN NOT NULL DEFAULT FALSE,
    id_ordem_servico INT NOT NULL REFERENCES Ordem_Servico(id_ordem_servico) ON DELETE CASCADE,
    id_servico INT NOT NULL REFERENCES Servico(id_servico) ON DELETE RESTRICT,
    id_mecanico INT REFERENCES Mecanico(id_mecanico) ON DELETE SET NULL
);

-- vincular Peças utilizadas na Ordem de Serviço (N:M)
CREATE TABLE Item_Peca_OS (
    id_item_peca_os SERIAL PRIMARY KEY,
    qtd_utilizada INT NOT NULL CHECK (qtd_utilizada > 0),
    valor_unitario DECIMAL(10,2) NOT NULL CHECK (valor_unitario >= 0),
    valor_total DECIMAL(10,2) NOT NULL CHECK (valor_total >= 0),
    em_garantia BOOLEAN NOT NULL DEFAULT FALSE,
    id_ordem_servico INT NOT NULL REFERENCES Ordem_Servico(id_ordem_servico) ON DELETE CASCADE,
    id_peca INT NOT NULL REFERENCES Peca(id_peca) ON DELETE RESTRICT,
    CONSTRAINT uk_os_peca UNIQUE (id_ordem_servico, id_peca)
);

CREATE TABLE Movimentacao_Estoque (
    id_movimentacao_estoque SERIAL PRIMARY KEY,
    codigo VARCHAR(30) UNIQUE NOT NULL,
    data_movimentacao DATE NOT NULL DEFAULT CURRENT_DATE,
    hora_movimentacao TIME NOT NULL DEFAULT CURRENT_TIME,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('ENTRADA', 'SAIDA')),
    quantidade INT NOT NULL CHECK (quantidade > 0),
    id_peca INT NOT NULL REFERENCES Peca(id_peca) ON DELETE RESTRICT,
    id_item_pedido INT REFERENCES Item_Pedido(id_item_pedido) ON DELETE SET NULL,
    id_item_peca_os INT REFERENCES Item_Peca_OS(id_item_peca_os) ON DELETE SET NULL
);