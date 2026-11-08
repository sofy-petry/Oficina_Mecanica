drop trigger if exists tg_calcula_valor_total_item_os on item_peca_os;
drop trigger if exists tg_valida_compatibilidade_peca_os on item_peca_os;
drop trigger if exists tg_atualiza_estoque_item_os on item_peca_os;
drop trigger if exists tg_recalcula_totais_os_peca on item_peca_os;
drop trigger if exists tg_recalcula_totais_os_servico on servico_os;
drop trigger if exists tg_gerar_parcelas_pagamento on pagamento;
drop trigger if exists tg_processa_entrega_pedido_peca on pedido_peca;

-- adicionei os meus drops pq nao tinha
drop trigger if exists trg_atualiza_km on ordem_servico;
drop trigger if exists trg_bloquear_servico_os on servico_os;
drop trigger if exists trg_bloquear_peca_os on item_peca_os;
drop trigger if exists trg_padronizar_nome_cliente on cliente;
drop trigger if exists trg_proteger_peca_com_estoque on peca;
drop trigger if exists trg_limitar_desconto_os on ordem_servico;
drop trigger if exists trg_controle_status_os on ordem_servico;

drop function if exists fn_calcula_valor_total_item_os();
drop function if exists fn_valida_compatibilidade_peca_os();
drop function if exists fn_atualiza_estoque_item_os();
drop function if exists fn_recalcula_totais_os();
drop function if exists fn_recalcula_totais_os_id(int);
drop function if exists fn_gerar_parcelas_pagamento();
drop function if exists fn_processa_entrega_pedido_peca();

drop function if exists fn_atualiza_km_veiculo();
drop function if exists fn_bloquear_alteracao_os_fechada();
drop function if exists fn_padronizar_nome_cliente();
drop function if exists fn_proteger_peca_com_estoque();
drop function if exists fn_limitar_desconto_os();
drop function if exists fn_controle_status_os();

drop sequence if exists seq_codigo_movimentacao;

-- sequencia usada para gerar codigos unicos de movimentacao (sem colisao)
create sequence seq_codigo_movimentacao;


-- gatilho: calculo automatico do valor_total do item (qtd * valor unitario) (elane)
-- tabela: item_peca_os (before insert or update)
create or replace function fn_calcula_valor_total_item_os()
returns trigger as $$
begin
    new.valor_total := new.qtd_utilizada * new.valor_unitario;
    return new;
end;
$$ language plpgsql;

create trigger tg_calcula_valor_total_item_os
before insert or update on item_peca_os
for each row
execute function fn_calcula_valor_total_item_os();



-- gatilho: validacao de compatibilidade da peca com marca/modelo do veiculo (elane)
-- tabela: item_peca_os (before insert or update)
create or replace function fn_valida_compatibilidade_peca_os()
returns trigger as $$
declare
    v_marca_veiculo varchar(50);
    v_modelo_veiculo varchar(50);
    v_tem_restricao_marca boolean;
    v_tem_restricao_modelo boolean;
begin
    -- busca marca e modelo do veiculo associado a ordem de servico
    select v.marca, v.modelo
      into v_marca_veiculo, v_modelo_veiculo
      from ordem_servico os
      join veiculo v on os.id_veiculo = v.id_veiculo
     where os.id_ordem_servico = new.id_ordem_servico;

    -- verifica se a peca possui restricao de marca
    select exists (select 1 from peca_marca where id_peca = new.id_peca)
      into v_tem_restricao_marca;

    if v_tem_restricao_marca then
        if not exists (
            select 1 from peca_marca
             where id_peca = new.id_peca
               and lower(nome_marca) = lower(v_marca_veiculo)
        ) then
            raise exception 'Incompatibilidade de marca: a peca (id %) nao e compativel com a marca do veiculo (%)!',
                new.id_peca, v_marca_veiculo;
        end if;
    end if;

    -- verifica se a peca possui restricao de modelo
    select exists (select 1 from peca_modelo where id_peca = new.id_peca)
      into v_tem_restricao_modelo;

    if v_tem_restricao_modelo then
        if not exists (
            select 1 from peca_modelo
             where id_peca = new.id_peca
               and lower(nome_modelo) = lower(v_modelo_veiculo)
        ) then
            raise exception 'Incompatibilidade de modelo: a peca (id %) nao e compativel com o modelo do veiculo (%)!',
                new.id_peca, v_modelo_veiculo;
        end if;
    end if;

    return new;
end;
$$ language plpgsql;

create trigger tg_valida_compatibilidade_peca_os
before insert or update on item_peca_os
for each row
execute function fn_valida_compatibilidade_peca_os();



-- gatilho: baixa/atualizacao automatica de estoque e registro de movimentacao (elane)
-- tabela: item_peca_os (after insert or update or delete)
create or replace function fn_atualiza_estoque_item_os()
returns trigger as $$
declare
    v_estoque_atual int;
    v_diferenca int;
    v_codigo_mov varchar(30);
begin
    if (tg_op = 'INSERT') then
        -- verifica disponibilidade em estoque
        select qtd_estoque into v_estoque_atual from peca where id_peca = new.id_peca;

        if v_estoque_atual < new.qtd_utilizada then
            raise exception 'Estoque insuficiente para a peca id %! estoque atual: %, solicitado: %',
                new.id_peca, v_estoque_atual, new.qtd_utilizada;
        end if;

        -- baixa no estoque da peca
        update peca
           set qtd_estoque = qtd_estoque - new.qtd_utilizada
         where id_peca = new.id_peca;

        -- registro na tabela de movimentacao_estoque
        v_codigo_mov := 'mov-os-' || nextval('seq_codigo_movimentacao')::text;
        insert into movimentacao_estoque (codigo, data_movimentacao, hora_movimentacao, tipo, quantidade, id_peca, id_item_peca_os)
        values (v_codigo_mov, current_date, current_time, 'SAIDA', new.qtd_utilizada, new.id_peca, new.id_item_peca_os);

        return new;

    elsif (tg_op = 'UPDATE') then
        -- nao permite trocar a peca de um item (exclua e insira novamente)
        if new.id_peca <> old.id_peca then
            raise exception 'Nao e permitido trocar a peca de um item; exclua e insira novamente.';
        end if;

        v_diferenca := new.qtd_utilizada - old.qtd_utilizada;

        if v_diferenca > 0 then
            select qtd_estoque into v_estoque_atual from peca where id_peca = new.id_peca;
            if v_estoque_atual < v_diferenca then
                raise exception 'Estoque insuficiente para alteracao da peca id %! estoque atual: %, adicional necessario: %',
                    new.id_peca, v_estoque_atual, v_diferenca;
            end if;

            update peca set qtd_estoque = qtd_estoque - v_diferenca where id_peca = new.id_peca;
            v_codigo_mov := 'mov-os-' || nextval('seq_codigo_movimentacao')::text;
            insert into movimentacao_estoque (codigo, data_movimentacao, hora_movimentacao, tipo, quantidade, id_peca, id_item_peca_os)
            values (v_codigo_mov, current_date, current_time, 'SAIDA', v_diferenca, new.id_peca, new.id_item_peca_os);

        elsif v_diferenca < 0 then
            update peca set qtd_estoque = qtd_estoque + abs(v_diferenca) where id_peca = new.id_peca;
            v_codigo_mov := 'mov-os-' || nextval('seq_codigo_movimentacao')::text;
            insert into movimentacao_estoque (codigo, data_movimentacao, hora_movimentacao, tipo, quantidade, id_peca, id_item_peca_os)
            values (v_codigo_mov, current_date, current_time, 'ENTRADA', abs(v_diferenca), new.id_peca, new.id_item_peca_os);
        end if;

        return new;

    elsif (tg_op = 'DELETE') then
        -- devolve pecas ao estoque em caso de exclusao do item
        update peca
           set qtd_estoque = qtd_estoque + old.qtd_utilizada
         where id_peca = old.id_peca;

        v_codigo_mov := 'mov-os-del-' || nextval('seq_codigo_movimentacao')::text;
        insert into movimentacao_estoque (codigo, data_movimentacao, hora_movimentacao, tipo, quantidade, id_peca, id_item_peca_os)
        values (v_codigo_mov, current_date, current_time, 'ENTRADA', old.qtd_utilizada, old.id_peca, null);

        return old;
    end if;

    return null;
end;
$$ language plpgsql;

create trigger tg_atualiza_estoque_item_os
after insert or update or delete on item_peca_os
for each row
execute function fn_atualiza_estoque_item_os();



-- gatilho: atualizacao da quilometragem do veiculo (sofia)
/*
ao abrir uma nova ordem de servico, atualiza automaticamente a quilometragem_atual do veiculo
caso a quilometragem_entrada informada na os seja maior que a registrada no cadastro.
*/
create or replace function fn_atualiza_km_veiculo() returns trigger as $$
begin
    update veiculo
    set quilometragem_atual = new.quilometragem_entrada
    where id_veiculo = new.id_veiculo
      and quilometragem_atual < new.quilometragem_entrada;
    return new;
end;
$$ language plpgsql;

create trigger trg_atualiza_km
after insert on ordem_servico
for each row execute function fn_atualiza_km_veiculo();



-- gatilho: recalculo automatico dos subtotais e valor total da ordem de servico (elane)
-- tabelas: item_peca_os e servico_os (after insert or update or delete)
-- itens/servicos em garantia nao sao cobrados do cliente
create or replace function fn_recalcula_totais_os_id(p_id_os int)
returns void as $$
declare
    v_subtotal_pecas decimal(10,2);
    v_subtotal_mo decimal(10,2);
    v_desconto decimal(10,2);
    v_valor_total decimal(10,2);
begin
    -- soma subtotal de pecas (exceto em garantia)
    select coalesce(sum(valor_total), 0.00)
      into v_subtotal_pecas
      from item_peca_os
     where id_ordem_servico = p_id_os
       and not em_garantia;

    -- soma subtotal de mao de obra (exceto em garantia)
    select coalesce(sum(valor_cobrado * quantidade), 0.00)
      into v_subtotal_mo
      from servico_os
     where id_ordem_servico = p_id_os
       and not em_garantia;

    -- obtem o desconto atual cadastrado na os
    select desconto
      into v_desconto
      from ordem_servico
     where id_ordem_servico = p_id_os;

    v_desconto := coalesce(v_desconto, 0.00);

    v_valor_total := greatest(0.00, (v_subtotal_pecas + v_subtotal_mo) - v_desconto);

    -- atualiza os totais na tabela ordem_servico
    update ordem_servico
       set subtotal_pecas = v_subtotal_pecas,
           subtotal_mao_obra = v_subtotal_mo,
           valor_total = v_valor_total
     where id_ordem_servico = p_id_os;
end;
$$ language plpgsql;

create or replace function fn_recalcula_totais_os()
returns trigger as $$
begin
    if (tg_op = 'DELETE') then
        perform fn_recalcula_totais_os_id(old.id_ordem_servico);
        return old;
    end if;

    perform fn_recalcula_totais_os_id(new.id_ordem_servico);

    -- se o item/servico mudou de os, recalcula tambem a os antiga
    if (tg_op = 'UPDATE' and old.id_ordem_servico <> new.id_ordem_servico) then
        perform fn_recalcula_totais_os_id(old.id_ordem_servico);
    end if;

    return new;
end;
$$ language plpgsql;

create trigger tg_recalcula_totais_os_peca
after insert or update or delete on item_peca_os
for each row
execute function fn_recalcula_totais_os();

create trigger tg_recalcula_totais_os_servico
after insert or update or delete on servico_os
for each row
execute function fn_recalcula_totais_os();



-- gatilho: geracao automatica das parcelas do pagamento (elane)
-- tabela: pagamento (after insert)
create or replace function fn_gerar_parcelas_pagamento()
returns trigger as $$
declare
    v_i int;
    v_valor_parcela decimal(10,2);
    v_valor_acumulado decimal(10,2) := 0.00;
    v_vencimento date;
begin
    for v_i in 1..new.numero_parcelas loop
        -- trata arredondamento de centavos na ultima parcela
        if v_i = new.numero_parcelas then
            v_valor_parcela := new.valor_total - v_valor_acumulado;
        else
            v_valor_parcela := round(new.valor_total / new.numero_parcelas, 2);
            v_valor_acumulado := v_valor_acumulado + v_valor_parcela;
        end if;

        -- vencimentos mensais sucessivos (primeira parcela em 1 mes)
        v_vencimento := (current_date + (v_i * interval '1 month'))::date;

        insert into parcela (id_pagamento, numero_parcela, valor_parcela, dta_vencimento, status)
        values (new.id_pagamento, v_i, v_valor_parcela, v_vencimento, 'pendente');
    end loop;

    return new;
end;
$$ language plpgsql;

create trigger tg_gerar_parcelas_pagamento
after insert on pagamento
for each row
execute function fn_gerar_parcelas_pagamento();



-- gatilho: entrada de estoque ao confirmar entrega do pedido de pecas (elane)
-- tabela: pedido_peca (after update of status)
create or replace function fn_processa_entrega_pedido_peca()
returns trigger as $$
declare
    r_item record;
    v_codigo_mov varchar(30);
begin
    -- impede reverter um pedido ja entregue (evita entrada duplicada no estoque)
    if (old.status = 'entregue' and new.status <> 'entregue') then
        raise exception 'Nao e permitido alterar o status de um pedido ja entregue (pedido id %)!',
            old.id_pedido_peca;
    end if;

    -- dispara apenas quando o status muda para 'entregue'
    if (old.status <> 'entregue' and new.status = 'entregue') then
        for r_item in
            select id_item_pedido, id_peca, quantidade
              from item_pedido
             where id_pedido_peca = new.id_pedido_peca
        loop
            -- incrementa o estoque da peca recebida
            update peca
               set qtd_estoque = qtd_estoque + r_item.quantidade
             where id_peca = r_item.id_peca;

            -- registra a movimentacao de entrada no estoque
            v_codigo_mov := 'mov-ped-' || nextval('seq_codigo_movimentacao')::text;
            insert into movimentacao_estoque (codigo, data_movimentacao, hora_movimentacao, tipo, quantidade, id_peca, id_item_pedido)
            values (v_codigo_mov, current_date, current_time, 'ENTRADA', r_item.quantidade, r_item.id_peca, r_item.id_item_pedido);
        end loop;
    end if;

    return new;
end;
$$ language plpgsql;

create trigger tg_processa_entrega_pedido_peca
after update of status on pedido_peca
for each row
execute function fn_processa_entrega_pedido_peca();



-- gatilho: bloqueio de alteracoes em os fechada (sofia)
/*
restricao de integridade que impede a adicao, alteracao ou exclusao de servicos ou pecas
em uma ordem_servico que ja esteja finalizada (status 'concluída', 'entregue' ou 'cancelada').
*/
create or replace function fn_bloquear_alteracao_os_fechada() returns trigger as $$
declare
    v_id_os int;
    v_status varchar;
begin
    -- no delete so existe old; nos demais casos usa new
    if tg_op = 'DELETE' then
        v_id_os := old.id_ordem_servico;
    else
        v_id_os := new.id_ordem_servico;
    end if;

    select status into v_status from ordem_servico where id_ordem_servico = v_id_os;

    if v_status in ('concluída', 'entregue', 'cancelada') then
        raise exception 'Não é permitido alterar itens. A OS já está %', v_status;
    end if;

    if tg_op = 'DELETE' then
        return old;
    end if;
    return new;
end;
$$ language plpgsql;

create trigger trg_bloquear_servico_os
before insert or update or delete on servico_os
for each row execute function fn_bloquear_alteracao_os_fechada();

create trigger trg_bloquear_peca_os
before insert or update or delete on item_peca_os
for each row execute function fn_bloquear_alteracao_os_fechada();



-- gatilho: padronizacao de nomes - formatacao (sofia)
/*
sempre que um utilizador inserir ou atualizar um cliente,
o banco de dados converte automaticamente o nome para letras maiusculas.
*/
create or replace function fn_padronizar_nome_cliente() returns trigger as $$
begin
    -- converte o nome digitado para maiusculas antes de guardar
    new.nome := upper(new.nome);
    return new;
end;
$$ language plpgsql;

create trigger trg_padronizar_nome_cliente
before insert or update on cliente
for each row execute function fn_padronizar_nome_cliente();



-- gatilho: impedir exclusao de pecas com estoque (sofia)
/*
se alguem tentar apagar um registo da tabela peca,
o gatilho bloqueia a acao caso a peca ainda tenha unidades no estoque.
*/
create or replace function fn_proteger_peca_com_estoque() returns trigger as $$
begin
    -- old representa os dados da linha antes de ser apagada
    if old.qtd_estoque > 0 then
        raise exception 'Operação cancelada: Não pode apagar uma peça que ainda tem % unidades em estoque!', old.qtd_estoque;
    end if;
    return old;
end;
$$ language plpgsql;

create trigger trg_proteger_peca_com_estoque
before delete on peca
for each row execute function fn_proteger_peca_com_estoque();



-- gatilho: limite de desconto na ordem de servico (autora: sofia)
/*
verifica o valor que esta a ser inserido no campo desconto.
se o desconto for superior a 20% da soma das pecas e mao de obra, ele aborta
a operacao e exibe um erro. a validacao so ocorre quando o desconto e informado
ou alterado, para nao bloquear o recalculo automatico dos subtotais.
tambem mantem o valor_total coerente com o desconto.
*/
create or replace function fn_limitar_desconto_os() returns trigger as $$
declare
    v_limite_desconto decimal(10,2);
begin
    -- valida apenas quando o desconto e informado ou alterado
    if tg_op = 'INSERT' or new.desconto is distinct from old.desconto then
        -- calcula o maximo permitido (20% do valor dos itens + servicos)
        v_limite_desconto := (coalesce(new.subtotal_pecas, 0) + coalesce(new.subtotal_mao_obra, 0)) * 0.20;

        -- se o desconto concedido for maior que o limite, lanca um erro
        if coalesce(new.desconto, 0) > v_limite_desconto then
            raise exception 'O desconto de % excede o limite máximo permitido de 20%%.', new.desconto;
        end if;
    end if;

    -- mantem o valor_total coerente com o desconto
    new.valor_total := greatest(0.00,
        coalesce(new.subtotal_pecas, 0) + coalesce(new.subtotal_mao_obra, 0) - coalesce(new.desconto, 0));

    return new;
end;
$$ language plpgsql;

create trigger trg_limitar_desconto_os
before insert or update on ordem_servico
for each row execute function fn_limitar_desconto_os();



-- gatilho: controle rigoroso do status da ordem de servico (sofia)
/*
se a oficina tentar finalizar ou entregar a os, ele verifica se existem servicos
cadastrados (para nao fechar uma os vazia). alem disso, se o status mudar para 'entregue',
ele preenche automaticamente a data e hora de saida, poupando trabalho do usuario
*/
create or replace function fn_controle_status_os() returns trigger as $$
declare
    v_total_itens_servico int;
    v_total_itens_peca int;
begin
    -- so executa as verificacoes se o status estiver sendo alterado
    if old.status is distinct from new.status then

        -- impedir reabertura de os ja cancelada ou entregue
        if old.status in ('cancelada', 'entregue') then
            raise exception 'Não é permitido alterar o status de uma Ordem de Serviço que já foi %.', old.status;
        end if;

        -- para concluir ou entregar, a os nao pode estar vazia
        if new.status in ('concluída', 'entregue') then
            -- conta quantos servicos e pecas a os tem
            select count(*) into v_total_itens_servico from servico_os where id_ordem_servico = new.id_ordem_servico;
            select count(*) into v_total_itens_peca from item_peca_os where id_ordem_servico = new.id_ordem_servico;

            if v_total_itens_servico = 0 and v_total_itens_peca = 0 then
                raise exception 'Ação bloqueada: Não é possível concluir ou entregar uma Ordem de Serviço sem nenhum serviço ou peça lançada.';
            end if;
        end if;

        if new.status = 'entregue' then
            if new.dta_saida is null then
                new.dta_saida := current_date;
            end if;
            if new.hra_saida is null then
                new.hra_saida := current_time;
            end if;
        end if;

    end if;

    return new;
end;
$$ language plpgsql;

create trigger trg_controle_status_os
before update on ordem_servico
for each row execute function fn_controle_status_os();