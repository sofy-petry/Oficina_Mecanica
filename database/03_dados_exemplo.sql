-- Dados de exemplo para demonstração do sistema.
-- Execute DEPOIS de 01_esquema.sql e 02_gatilhos.sql.
-- Tudo passa pelos gatilhos: nomes viram maiúsculas, itens de OS dão baixa no estoque,
-- totais das OS são recalculados, parcelas são geradas e pedidos entregues dão entrada no estoque.
-- As datas são relativas a CURRENT_DATE, então o painel sempre parece "vivo".


-- Funções auxiliares (temporárias: somem ao fim da sessão)

CREATE FUNCTION pg_temp.lancar_servico(p_os text, p_servico text, p_mecanico int, p_qtd int DEFAULT 1,
                                       p_garantia boolean DEFAULT FALSE) RETURNS void AS $$
    INSERT INTO Servico_OS (quantidade, valor_cobrado, em_garantia, id_ordem_servico, id_servico, id_mecanico)
    SELECT p_qtd, s.valor_mao_obra, p_garantia, o.id_ordem_servico, s.id_servico, p_mecanico
      FROM Servico s, Ordem_Servico o
     WHERE s.codigo = p_servico AND o.numero_sequencial = p_os;
$$ LANGUAGE sql;

CREATE FUNCTION pg_temp.lancar_peca(p_os text, p_peca text, p_qtd int,
                                    p_garantia boolean DEFAULT FALSE) RETURNS void AS $$
    INSERT INTO Item_Peca_OS (qtd_utilizada, valor_unitario, valor_total, em_garantia, id_ordem_servico, id_peca)
    SELECT p_qtd, p.preco_venda, p_qtd * p.preco_venda, p_garantia, o.id_ordem_servico, p.id_peca
      FROM Peca p, Ordem_Servico o
     WHERE p.codigo = p_peca AND o.numero_sequencial = p_os;
$$ LANGUAGE sql;

-- Registra o pagamento (o gatilho gera as parcelas) e reposiciona os vencimentos no passado
CREATE FUNCTION pg_temp.registrar_pagamento(p_os text, p_forma text, p_parcelas int,
                                            p_dias_1o_vencimento int) RETURNS void AS $$
    INSERT INTO Pagamento (codigo, forma_pagamento, valor_total, numero_parcelas, id_ordem_servico)
    SELECT 'PAG-' || o.numero_sequencial, p_forma, o.valor_total, p_parcelas, o.id_ordem_servico
      FROM Ordem_Servico o WHERE o.numero_sequencial = p_os;
    UPDATE Parcela pa
       SET dta_vencimento = CURRENT_DATE + p_dias_1o_vencimento + (pa.numero_parcela - 1) * 30
      FROM Pagamento pg, Ordem_Servico o
     WHERE pa.id_pagamento = pg.id_pagamento AND pg.id_ordem_servico = o.id_ordem_servico
       AND o.numero_sequencial = p_os;
$$ LANGUAGE sql;

CREATE FUNCTION pg_temp.baixar_parcela(p_os text, p_numero int, p_dias_atras int) RETURNS void AS $$
    UPDATE Parcela pa SET status = 'pago', dta_pagamento = CURRENT_DATE - p_dias_atras
      FROM Pagamento pg, Ordem_Servico o
     WHERE pa.id_pagamento = pg.id_pagamento AND pg.id_ordem_servico = o.id_ordem_servico
       AND o.numero_sequencial = p_os AND pa.numero_parcela = p_numero;
$$ LANGUAGE sql;


-- Clientes, telefones e veículos

INSERT INTO Cliente (nome, endereco, email, tipo_cliente) VALUES
    ('João da Silva',            'Rua das Flores, 120 - Joinville/SC',        'joao.silva@email.com',        'F'),  -- 1
    ('Maria Oliveira',           'Av. Beira Rio, 450 - Joinville/SC',         'maria.oliveira@email.com',    'F'),  -- 2
    ('Transportes Norte Ltda',   'Rua Industrial, 900 - Joinville/SC',        'contato@transnorte.com.br',   'J'),  -- 3
    ('Carla Mendes',             'Rua XV de Novembro, 77 - Blumenau/SC',      'carla.mendes@email.com',      'F'),  -- 4
    ('Pedro Henrique Costa',     'Rua Porto Alegre, 310 - Joinville/SC',      NULL,                          'F'),  -- 5
    ('Auto Locadora Veloz Ltda', 'Av. Santos Dumont, 2500 - Joinville/SC',    'frota@locadoraveloz.com.br',  'J'),  -- 6
    ('Fernanda Lima',            'Rua Dona Francisca, 1450 - Joinville/SC',   'fe.lima@email.com',           'F');  -- 7

INSERT INTO Cliente_Fisico (id_cliente, cpf) VALUES
    (1, '123.456.789-09'), (2, '987.654.321-00'), (4, '222.333.444-55'), (5, '333.444.555-66'), (7, '444.555.666-77');
INSERT INTO Cliente_Juridico (id_cliente, cnpj) VALUES
    (3, '12.345.678/0001-90'), (6, '45.678.901/0001-23');

INSERT INTO Telefone (id_cliente, numero) VALUES
    (1, '(47) 99999-1111'), (1, '(47) 3422-1111'), (2, '(47) 98888-2222'), (3, '(47) 3433-3333'),
    (4, '(47) 99777-4444'), (5, '(47) 99666-5555'), (6, '(47) 3455-6666'), (6, '(47) 99555-6767'), (7, '(47) 99444-7777');

INSERT INTO Veiculo (placa, marca, modelo, ano_fabricacao, cor, numero_chassi, quilometragem_atual, observacoes, id_cliente) VALUES
    ('ABC1D23', 'Fiat',       'Uno',     2014, 'Prata',    '9BD195A12E0123456', 98500,  'Arranhão na porta traseira direita', 1),  -- 1
    ('DEF4G56', 'Volkswagen', 'Gol',     2018, 'Branco',   '9BWZZZ377VT004251', 54200,  NULL,                                 2),  -- 2
    ('GHI7J89', 'Ford',       'Ranger',  2020, 'Preta',    '8AFDZZFLAKJ123456', 120300, 'Veículo de frota',                   3),  -- 3
    ('JKL0M12', 'Chevrolet',  'Onix',    2019, 'Cinza',    '9BGKS48U0KG123789', 61000,  NULL,                                 4),  -- 4
    ('NOP3Q45', 'Honda',      'Civic',   2017, 'Preto',    '93HFC1670HZ456123', 88000,  'Cliente pede retorno do veículo lavado', 5),  -- 5
    ('RST6U78', 'Toyota',     'Corolla', 2021, 'Branco',   '9BR53ZEC4M4789456', 42000,  'Veículo de frota',                   6),  -- 6
    ('VWX9Y01', 'Hyundai',    'HB20',    2020, 'Vermelho', '9BHBG51CALP321654', 35000,  'Veículo de frota',                   6),  -- 7
    ('ZAB2C34', 'Fiat',       'Strada',  2022, 'Azul',     '9BD578A12NY654987', 27000,  NULL,                                 7);  -- 8


-- Equipe, catálogo de serviços e peças

INSERT INTO Mecanico (nome, cpf, dta_admissao, especialidade, percentual_comissao) VALUES
    ('Carlos Pereira', '111.222.333-44', '2019-03-10', 'mecânica geral', 5.00),   -- 1
    ('Ana Souza',      '555.666.777-88', '2021-07-01', 'elétrica',       6.50),   -- 2
    ('Roberto Alves',  '666.777.888-99', '2018-02-15', 'funilaria',      4.00),   -- 3
    ('Juliana Prado',  '777.888.999-00', '2022-09-05', 'mecânica geral', 5.50);   -- 4

INSERT INTO Servico (codigo, descricao, tempo_medio_execucao, valor_mao_obra, categoria, periodo_garantia) VALUES
    ('SRV-001', 'Troca de óleo e filtro',        40,  80.00,  'Manutenção preventiva', 90),
    ('SRV-002', 'Alinhamento e balanceamento',   60,  120.00, 'Suspensão',             90),
    ('SRV-003', 'Revisão de freios',             90,  150.00, 'Freios',                180),
    ('SRV-004', 'Revisão completa',              240, 450.00, 'Manutenção preventiva', 180),
    ('SRV-005', 'Diagnóstico elétrico',          60,  100.00, 'Elétrica',              30),
    ('SRV-006', 'Troca de correia dentada',      120, 320.00, 'Motor',                 180),
    ('SRV-007', 'Troca de bateria',              30,  60.00,  'Elétrica',              90),
    ('SRV-008', 'Troca de pneus (jogo)',         90,  160.00, 'Suspensão',             90),
    ('SRV-009', 'Limpeza de bicos injetores',    90,  180.00, 'Motor',                 90),
    ('SRV-010', 'Troca de amortecedores',        150, 280.00, 'Suspensão',             180);

INSERT INTO Peca (codigo, descricao, fabricante, cod_fabricante, qtd_estoque, qtd_minimo, preco_custo, preco_venda, periodo_garantia) VALUES
    ('PC-001', 'Óleo 5W30 sintético 1L',       'Mobil',   'MB-5W30',   40, 10,  28.00,  45.00, 0),     -- 1
    ('PC-002', 'Filtro de óleo universal',     'Tecfil',  'PSL-55',    25,  5,  12.00,  25.00, 90),    -- 2
    ('PC-003', 'Pastilha de freio dianteira',  'Cobreq',  'N-1033',     3,  4,  60.00, 110.00, 180),   -- 3
    ('PC-004', 'Bateria 60Ah',                 'Moura',   'M60AD',      6,  2, 320.00, 480.00, 365),   -- 4
    ('PC-005', 'Pneu aro 14 175/70',           'Pirelli', 'P-175-70',  12,  4, 280.00, 390.00, 365),   -- 5
    ('PC-006', 'Correia dentada',              'Gates',   'GT-5453',    8,  3,  90.00, 150.00, 180),   -- 6
    ('PC-007', 'Amortecedor dianteiro',        'Cofap',   'AMT-2210',   2,  4, 180.00, 290.00, 180),   -- 7
    ('PC-008', 'Filtro de ar',                 'Fram',    'CA-9482',   15,  5,  18.00,  35.00, 90),    -- 8
    ('PC-009', 'Vela de ignição',              'NGK',     'BKR6E',     30,  8,  14.00,  38.00, 90),    -- 9
    ('PC-010', 'Fluido de freio DOT4 500ml',   'Bosch',   'FD-4500',    4,  6,  16.00,  32.00, 0);     -- 10

-- Compatibilidade (peça sem linhas aqui serve para qualquer veículo)
INSERT INTO Peca_Marca (id_peca, nome_marca) VALUES (3, 'Fiat'), (3, 'Volkswagen');
INSERT INTO Peca_Modelo (id_peca, nome_modelo) VALUES (3, 'Uno'), (3, 'Gol'), (5, 'Uno'), (5, 'Gol'), (7, 'HB20'), (7, 'Onix');


-- Fornecedores e catálogo de fornecimento

INSERT INTO Fornecedor (cnpj, razao_social, telefone, email, endereco, condicao_pagamento) VALUES
    ('98.765.432/0001-10', 'Distribuidora AutoPeças Sul S/A',  '(47) 3030-4040', 'vendas@autopecassul.com.br',     'Rod. BR-101, km 55 - Joinville/SC',   '30/60 dias'),  -- 1
    ('11.222.333/0001-44', 'Pneus & Cia Distribuidora Ltda',   '(47) 3040-5050', 'pedidos@pneusecia.com.br',       'Av. Paulista, 1200 - Curitiba/PR',    'À vista com 5% de desconto'),  -- 2
    ('55.666.777/0001-88', 'Elétrica Brasil Componentes Ltda', '(11) 4004-8080', 'comercial@eletricabrasil.com.br', 'Rua do Comércio, 80 - São Paulo/SP', '28 dias');       -- 3

INSERT INTO Fornecimento (id_fornecedor, id_peca, preco_praticado, prazo_entrega) VALUES
    (1, 1, 26.00, 2),  (1, 2, 11.00, 2),  (1, 3, 55.00, 3),  (1, 6, 85.00, 3),  (1, 7, 170.00, 4),  (1, 8, 16.50, 2),  (1, 9, 13.00, 2),  (1, 10, 15.00, 2),
    (2, 5, 270.00, 5),
    (3, 4, 300.00, 5), (3, 9, 12.50, 6);


-- Ordens de serviço (de ~4 meses atrás até hoje)

-- OS-00001: em execução, aberta hoje (Uno do João)
INSERT INTO Ordem_Servico (numero_sequencial, quilometragem_entrada, descricao_problema, status, dta_previsao_conclusao, id_veiculo, id_mecanico_responsavel)
VALUES ('OS-2026-00001', 98800, 'Troca de óleo e barulho ao frear', 'em execução', CURRENT_DATE + 2, 1, 1);
SELECT pg_temp.lancar_servico('OS-2026-00001', 'SRV-001', 1);
SELECT pg_temp.lancar_peca('OS-2026-00001', 'PC-001', 4);
SELECT pg_temp.lancar_peca('OS-2026-00001', 'PC-002', 1);

-- OS-00002: entregue há ~5 semanas, paga à vista no pix (Onix da Carla)
INSERT INTO Ordem_Servico (numero_sequencial, dta_entrada, quilometragem_entrada, descricao_problema, status, dta_previsao_conclusao, id_veiculo, id_mecanico_responsavel)
VALUES ('OS-2026-00002', CURRENT_DATE - 40, 60800, 'Revisão dos 60 mil km', 'em execução', CURRENT_DATE - 38, 4, 4);
SELECT pg_temp.lancar_servico('OS-2026-00002', 'SRV-004', 4);
SELECT pg_temp.lancar_peca('OS-2026-00002', 'PC-001', 4);
SELECT pg_temp.lancar_peca('OS-2026-00002', 'PC-002', 1);
SELECT pg_temp.lancar_peca('OS-2026-00002', 'PC-008', 1);
UPDATE Ordem_Servico SET status = 'concluída' WHERE numero_sequencial = 'OS-2026-00002';
UPDATE Ordem_Servico SET status = 'entregue', dta_saida = CURRENT_DATE - 37 WHERE numero_sequencial = 'OS-2026-00002';
SELECT pg_temp.registrar_pagamento('OS-2026-00002', 'pix', 1, -37);
SELECT pg_temp.baixar_parcela('OS-2026-00002', 1, 37);

-- OS-00003: concluída, pronta para retirada, ainda sem pagamento (Civic do Pedro)
INSERT INTO Ordem_Servico (numero_sequencial, dta_entrada, quilometragem_entrada, descricao_problema, status, dta_previsao_conclusao, id_veiculo, id_mecanico_responsavel)
VALUES ('OS-2026-00003', CURRENT_DATE - 4, 88400, 'Pedal do freio baixo e ruído nas rodas', 'em execução', CURRENT_DATE - 1, 5, 1);
SELECT pg_temp.lancar_servico('OS-2026-00003', 'SRV-003', 1);
SELECT pg_temp.lancar_peca('OS-2026-00003', 'PC-009', 4);
SELECT pg_temp.lancar_peca('OS-2026-00003', 'PC-010', 1);
UPDATE Ordem_Servico SET desconto = 30.00 WHERE numero_sequencial = 'OS-2026-00003';
UPDATE Ordem_Servico SET status = 'concluída' WHERE numero_sequencial = 'OS-2026-00003';

-- OS-00004: em execução, revisão da frota (Corolla da locadora)
INSERT INTO Ordem_Servico (numero_sequencial, dta_entrada, quilometragem_entrada, descricao_problema, status, dta_previsao_conclusao, id_veiculo, id_mecanico_responsavel)
VALUES ('OS-2026-00004', CURRENT_DATE - 2, 42300, 'Revisão preventiva da frota e troca de óleo', 'em execução', CURRENT_DATE + 1, 6, 4);
SELECT pg_temp.lancar_servico('OS-2026-00004', 'SRV-004', 4);
SELECT pg_temp.lancar_servico('OS-2026-00004', 'SRV-002', 1);
SELECT pg_temp.lancar_peca('OS-2026-00004', 'PC-001', 4);
SELECT pg_temp.lancar_peca('OS-2026-00004', 'PC-002', 1);
SELECT pg_temp.lancar_peca('OS-2026-00004', 'PC-008', 1);

-- OS-00005: aguardando peças (HB20 da locadora; amortecedores pedidos ao fornecedor)
INSERT INTO Ordem_Servico (numero_sequencial, dta_entrada, quilometragem_entrada, descricao_problema, status, dta_previsao_conclusao, id_veiculo, id_mecanico_responsavel)
VALUES ('OS-2026-00005', CURRENT_DATE - 1, 35100, 'Barulho na suspensão dianteira em lombadas', 'aguardando peças', CURRENT_DATE + 4, 7, 1);
SELECT pg_temp.lancar_servico('OS-2026-00005', 'SRV-010', 1);

-- OS-00006: aguardando aprovação do orçamento, aberta hoje (Strada da Fernanda)
INSERT INTO Ordem_Servico (numero_sequencial, quilometragem_entrada, descricao_problema, status, dta_previsao_conclusao, id_veiculo, id_mecanico_responsavel)
VALUES ('OS-2026-00006', 27200, 'Luz da injeção acesa e perda de potência', 'aguardando aprovação', CURRENT_DATE + 3, 8, 2);
SELECT pg_temp.lancar_servico('OS-2026-00006', 'SRV-005', 2);

-- OS-00007: cancelada (cliente desistiu do orçamento)
INSERT INTO Ordem_Servico (numero_sequencial, dta_entrada, quilometragem_entrada, descricao_problema, status, id_veiculo, id_mecanico_responsavel)
VALUES ('OS-2026-00007', CURRENT_DATE - 20, 54500, 'Orçamento de funilaria na porta dianteira', 'aguardando aprovação', 2, 3);
UPDATE Ordem_Servico SET status = 'cancelada' WHERE numero_sequencial = 'OS-2026-00007';

-- OS-00008: entregue, frota Ranger, pago em 3x no cartão com parcela 2 em atraso
INSERT INTO Ordem_Servico (numero_sequencial, dta_entrada, quilometragem_entrada, descricao_problema, status, dta_previsao_conclusao, id_veiculo, id_mecanico_responsavel)
VALUES ('OS-2026-00008', CURRENT_DATE - 50, 120000, 'Veículo não pega pela manhã', 'em execução', CURRENT_DATE - 48, 3, 2);
SELECT pg_temp.lancar_servico('OS-2026-00008', 'SRV-005', 2);
SELECT pg_temp.lancar_servico('OS-2026-00008', 'SRV-007', 2);
SELECT pg_temp.lancar_peca('OS-2026-00008', 'PC-004', 1);
SELECT pg_temp.lancar_peca('OS-2026-00008', 'PC-001', 4, TRUE);   -- óleo lançado em garantia (não cobrado)
UPDATE Ordem_Servico SET status = 'concluída' WHERE numero_sequencial = 'OS-2026-00008';
UPDATE Ordem_Servico SET status = 'entregue', dta_saida = CURRENT_DATE - 47 WHERE numero_sequencial = 'OS-2026-00008';
SELECT pg_temp.registrar_pagamento('OS-2026-00008', 'cartão de crédito', 3, -45 + 30 - 30);
UPDATE Parcela pa SET dta_vencimento = CURRENT_DATE - 45 + (pa.numero_parcela - 1) * 30
  FROM Pagamento pg, Ordem_Servico o
 WHERE pa.id_pagamento = pg.id_pagamento AND pg.id_ordem_servico = o.id_ordem_servico AND o.numero_sequencial = 'OS-2026-00008';
SELECT pg_temp.baixar_parcela('OS-2026-00008', 1, 44);
UPDATE Parcela pa SET status = 'atrasado'
  FROM Pagamento pg, Ordem_Servico o
 WHERE pa.id_pagamento = pg.id_pagamento AND pg.id_ordem_servico = o.id_ordem_servico
   AND o.numero_sequencial = 'OS-2026-00008' AND pa.numero_parcela = 2;

-- OS-00009 a 00012: histórico mais antigo (alimenta o gráfico de faturamento)
INSERT INTO Ordem_Servico (numero_sequencial, dta_entrada, quilometragem_entrada, descricao_problema, status, dta_previsao_conclusao, id_veiculo, id_mecanico_responsavel) VALUES
    ('OS-2026-00009', CURRENT_DATE - 75,  97000, 'Freios com ruído', 'em execução', CURRENT_DATE - 73, 1, 1),
    ('OS-2026-00010', CURRENT_DATE - 100, 59000, 'Correia dentada no prazo de troca', 'em execução', CURRENT_DATE - 98, 4, 4),
    ('OS-2026-00011', CURRENT_DATE - 128, 86500, 'Troca de óleo', 'em execução', CURRENT_DATE - 127, 5, 4),
    ('OS-2026-00012', CURRENT_DATE - 30,  53000, 'Alinhamento e balanceamento', 'em execução', CURRENT_DATE - 29, 2, 1);

SELECT pg_temp.lancar_servico('OS-2026-00009', 'SRV-003', 1);
SELECT pg_temp.lancar_peca('OS-2026-00009', 'PC-003', 2);
SELECT pg_temp.lancar_servico('OS-2026-00010', 'SRV-006', 4);
SELECT pg_temp.lancar_peca('OS-2026-00010', 'PC-006', 1);
SELECT pg_temp.lancar_servico('OS-2026-00011', 'SRV-001', 4);
SELECT pg_temp.lancar_peca('OS-2026-00011', 'PC-001', 3);
SELECT pg_temp.lancar_peca('OS-2026-00011', 'PC-002', 1);
SELECT pg_temp.lancar_servico('OS-2026-00012', 'SRV-002', 1);

UPDATE Ordem_Servico SET status = 'concluída' WHERE numero_sequencial IN ('OS-2026-00009', 'OS-2026-00010', 'OS-2026-00011', 'OS-2026-00012');
UPDATE Ordem_Servico SET status = 'entregue', dta_saida = dta_entrada + 2 WHERE numero_sequencial IN ('OS-2026-00009', 'OS-2026-00010', 'OS-2026-00011', 'OS-2026-00012');

SELECT pg_temp.registrar_pagamento('OS-2026-00009', 'cartão de débito', 1, -73);
SELECT pg_temp.baixar_parcela('OS-2026-00009', 1, 73);
SELECT pg_temp.registrar_pagamento('OS-2026-00010', 'cartão de crédito', 2, -98);
UPDATE Parcela pa SET dta_vencimento = CURRENT_DATE - 98 + (pa.numero_parcela - 1) * 30
  FROM Pagamento pg, Ordem_Servico o WHERE pa.id_pagamento = pg.id_pagamento AND pg.id_ordem_servico = o.id_ordem_servico AND o.numero_sequencial = 'OS-2026-00010';
SELECT pg_temp.baixar_parcela('OS-2026-00010', 1, 97);
SELECT pg_temp.baixar_parcela('OS-2026-00010', 2, 66);
SELECT pg_temp.registrar_pagamento('OS-2026-00011', 'dinheiro', 1, -127);
SELECT pg_temp.baixar_parcela('OS-2026-00011', 1, 127);
SELECT pg_temp.registrar_pagamento('OS-2026-00012', 'pix', 1, -29);
SELECT pg_temp.baixar_parcela('OS-2026-00012', 1, 29);


-- Pedidos de peças

-- PED-00001: reposição de estoque, já entregue (o gatilho dá entrada no estoque)
INSERT INTO Pedido_Peca (codigo_pedido, data_pedido, previsao_entrega, status, valor_total, id_fornecedor)
VALUES ('PED-2026-00001', CURRENT_DATE - 33, CURRENT_DATE - 30, 'pendente', 20 * 26.00 + 6 * 55.00, 1);
INSERT INTO Item_Pedido (quantidade, valor_unitario, valor_total, id_pedido_peca, id_peca) VALUES
    (20, 26.00, 520.00, 1, 1), (6, 55.00, 330.00, 1, 3);
UPDATE Pedido_Peca SET status = 'entregue' WHERE codigo_pedido = 'PED-2026-00001';

-- PED-00002: baterias e velas, em trânsito
INSERT INTO Pedido_Peca (codigo_pedido, data_pedido, previsao_entrega, status, valor_total, id_fornecedor)
VALUES ('PED-2026-00002', CURRENT_DATE - 3, CURRENT_DATE + 2, 'em trânsito', 4 * 300.00 + 20 * 12.50, 3);
INSERT INTO Item_Pedido (quantidade, valor_unitario, valor_total, id_pedido_peca, id_peca) VALUES
    (4, 300.00, 1200.00, 2, 4), (20, 12.50, 250.00, 2, 9);

-- PED-00003: amortecedores para a OS-00005, pendente
INSERT INTO Pedido_Peca (codigo_pedido, data_pedido, previsao_entrega, status, valor_total, id_fornecedor, id_ordem_servico)
VALUES ('PED-2026-00003', CURRENT_DATE, CURRENT_DATE + 4, 'pendente', 6 * 170.00 + 4 * 15.00, 1,
        (SELECT id_ordem_servico FROM Ordem_Servico WHERE numero_sequencial = 'OS-2026-00005'));
INSERT INTO Item_Pedido (quantidade, valor_unitario, valor_total, id_pedido_peca, id_peca) VALUES
    (6, 170.00, 1020.00, 3, 7), (4, 15.00, 60.00, 3, 10);

-- Mantém a sequência do id da OS coerente com os registros acima
SELECT setval(pg_get_serial_sequence('ordem_servico', 'id_ordem_servico'), (SELECT MAX(id_ordem_servico) FROM Ordem_Servico));
SELECT setval(pg_get_serial_sequence('pedido_peca', 'id_pedido_peca'), (SELECT MAX(id_pedido_peca) FROM Pedido_Peca));
