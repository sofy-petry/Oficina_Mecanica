"""Consultas agregadas para o painel inicial (indicadores e gráfico de faturamento)"""


class PainelDAO:
    def indicadores(self, cur) -> dict:
        cur.execute(
            """SELECT
                 (SELECT COUNT(*) FROM Ordem_Servico
                   WHERE status IN ('aguardando aprovação', 'aguardando peças', 'em execução')) AS os_em_andamento,
                 (SELECT COUNT(*) FROM Ordem_Servico WHERE status = 'concluída') AS prontas_retirada,
                 (SELECT COALESCE(SUM(valor_total), 0) FROM Ordem_Servico
                   WHERE status IN ('concluída', 'entregue')
                     AND date_trunc('month', COALESCE(dta_saida, dta_entrada)) = date_trunc('month', CURRENT_DATE)
                 ) AS faturamento_mes,
                 (SELECT COALESCE(SUM(valor_parcela), 0) FROM Parcela
                   WHERE status = 'pago'
                     AND date_trunc('month', dta_pagamento) = date_trunc('month', CURRENT_DATE)
                 ) AS recebido_mes,
                 (SELECT COALESCE(SUM(valor_parcela), 0) FROM Parcela WHERE status <> 'pago') AS a_receber,
                 (SELECT COUNT(*) FROM Parcela
                   WHERE status <> 'pago' AND dta_vencimento < CURRENT_DATE) AS parcelas_vencidas,
                 (SELECT COUNT(*) FROM Peca WHERE qtd_estoque <= qtd_minimo) AS estoque_baixo,
                 (SELECT COUNT(*) FROM Pedido_Peca WHERE status IN ('pendente', 'em trânsito')) AS pedidos_abertos,
                 (SELECT COUNT(*) FROM Ordem_Servico
                   WHERE status IN ('aguardando aprovação', 'aguardando peças', 'em execução')
                     AND dta_previsao_conclusao < CURRENT_DATE) AS os_atrasadas"""
        )
        return cur.fetchone()

    def faturamento_mensal(self, cur, meses: int = 6) -> list[dict]:
        """Total das OS concluídas/entregues por mês (inclui meses sem movimento)."""
        cur.execute(
            """SELECT m::date AS mes, COALESCE(SUM(os.valor_total), 0) AS total
                 FROM generate_series(date_trunc('month', CURRENT_DATE) - (%s * interval '1 month'),
                                      date_trunc('month', CURRENT_DATE), interval '1 month') AS m
                 LEFT JOIN Ordem_Servico os
                        ON os.status IN ('concluída', 'entregue')
                       AND date_trunc('month', COALESCE(os.dta_saida, os.dta_entrada)) = m
                GROUP BY m ORDER BY m""",
            (meses - 1,),
        )
        return cur.fetchall()

    def parcelas_vencidas(self, cur, limite: int = 5) -> list[dict]:
        cur.execute(
            """SELECT pa.numero_parcela, pa.valor_parcela, pa.dta_vencimento,
                      pg.numero_parcelas, os.id_ordem_servico, os.numero_sequencial, c.nome AS nome_cliente
                 FROM Parcela pa
                 JOIN Pagamento pg ON pg.id_pagamento = pa.id_pagamento
                 JOIN Ordem_Servico os ON os.id_ordem_servico = pg.id_ordem_servico
                 JOIN Veiculo v ON v.id_veiculo = os.id_veiculo
                 JOIN Cliente c ON c.id_cliente = v.id_cliente
                WHERE pa.status <> 'pago' AND pa.dta_vencimento < CURRENT_DATE
                ORDER BY pa.dta_vencimento LIMIT %s""",
            (limite,),
        )
        return cur.fetchall()
