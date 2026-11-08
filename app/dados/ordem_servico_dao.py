"""DAO de Ordem_Servico e de seus itens (Servico_OS e Item_Peca_OS)"""
from decimal import Decimal
from typing import Optional

from app.modelo.entidades import ItemPecaOS, OrdemServico, ServicoOS

_SELECT = """
    SELECT os.*, v.placa, v.marca, v.modelo, c.nome AS nome_cliente,
           m.nome AS nome_mecanico
      FROM Ordem_Servico os
      JOIN Veiculo v ON v.id_veiculo = os.id_veiculo
      JOIN Cliente c ON c.id_cliente = v.id_cliente
      LEFT JOIN Mecanico m ON m.id_mecanico = os.id_mecanico_responsavel
"""


class OrdemServicoDAO:
    # Ordem de serviço 
    def proximo_id(self, cur) -> int:
        """Reserva o próximo id da sequência (usado para compor o número sequencial da OS)."""
        cur.execute("SELECT nextval(pg_get_serial_sequence('ordem_servico', 'id_ordem_servico')) AS id")
        return cur.fetchone()["id"]

    def inserir(self, cur, os: OrdemServico) -> int:
        cur.execute(
            """INSERT INTO Ordem_Servico (id_ordem_servico, numero_sequencial, quilometragem_entrada,
                                          descricao_problema, status, dta_previsao_conclusao,
                                          id_veiculo, id_mecanico_responsavel)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id_ordem_servico""",
            (os.id_ordem_servico, os.numero_sequencial, os.quilometragem_entrada,
             os.descricao_problema, os.status, os.dta_previsao_conclusao,
             os.id_veiculo, os.id_mecanico_responsavel),
        )
        return cur.fetchone()["id_ordem_servico"]

    def listar(self, cur, status: Optional[str] = None, busca: Optional[str] = None,
               limite: Optional[int] = None) -> list[OrdemServico]:
        condicoes, params = [], []
        if status:
            condicoes.append("os.status = %s")
            params.append(status)
        if busca:
            condicoes.append("(os.numero_sequencial ILIKE %s OR v.placa ILIKE %s OR c.nome ILIKE %s)")
            params += [f"%{busca}%"] * 3
        sql = _SELECT + (" WHERE " + " AND ".join(condicoes) if condicoes else "")
        sql += " ORDER BY os.id_ordem_servico DESC"
        if limite:
            sql += " LIMIT %s"
            params.append(limite)
        cur.execute(sql, params)
        return [OrdemServico.de_linha(r) for r in cur.fetchall()]

    def buscar_por_id(self, cur, id_os: int) -> Optional[OrdemServico]:
        cur.execute(_SELECT + " WHERE os.id_ordem_servico = %s", (id_os,))
        linha = cur.fetchone()
        return OrdemServico.de_linha(linha) if linha else None

    def listar_por_veiculo(self, cur, id_veiculo: int) -> list[OrdemServico]:
        cur.execute(_SELECT + " WHERE os.id_veiculo = %s ORDER BY os.id_ordem_servico DESC", (id_veiculo,))
        return [OrdemServico.de_linha(r) for r in cur.fetchall()]

    def listar_por_cliente(self, cur, id_cliente: int) -> list[OrdemServico]:
        cur.execute(_SELECT + " WHERE v.id_cliente = %s ORDER BY os.id_ordem_servico DESC", (id_cliente,))
        return [OrdemServico.de_linha(r) for r in cur.fetchall()]

    def listar_por_mecanico(self, cur, id_mecanico: int) -> list[OrdemServico]:
        """OS em que o mecânico é o responsável ou executou algum serviço."""
        cur.execute(
            _SELECT + """ WHERE os.id_mecanico_responsavel = %s
                             OR EXISTS (SELECT 1 FROM Servico_OS so
                                         WHERE so.id_ordem_servico = os.id_ordem_servico
                                           AND so.id_mecanico = %s)
                          ORDER BY os.id_ordem_servico DESC""", (id_mecanico, id_mecanico))
        return [OrdemServico.de_linha(r) for r in cur.fetchall()]

    def listar_prazos(self, cur, limite: int = 6) -> list[OrdemServico]:
        """OS em andamento com previsão de conclusão, da mais urgente para a menos."""
        cur.execute(
            _SELECT + """ WHERE os.status IN ('aguardando aprovação', 'aguardando peças', 'em execução')
                            AND os.dta_previsao_conclusao IS NOT NULL
                          ORDER BY os.dta_previsao_conclusao, os.id_ordem_servico LIMIT %s""", (limite,))
        return [OrdemServico.de_linha(r) for r in cur.fetchall()]

    def atualizar_status(self, cur, id_os: int, status: str) -> None:
        cur.execute("UPDATE Ordem_Servico SET status = %s WHERE id_ordem_servico = %s",
                    (status, id_os))

    def atualizar_desconto(self, cur, id_os: int, desconto: Decimal) -> None:
        cur.execute("UPDATE Ordem_Servico SET desconto = %s WHERE id_ordem_servico = %s",
                    (desconto, id_os))

    # ---- Serviços executados na OS ----------------------------------------
    def listar_servicos(self, cur, id_os: int) -> list[ServicoOS]:
        cur.execute(
            """SELECT so.*, s.codigo, s.descricao, m.nome AS nome_mecanico
                 FROM Servico_OS so
                 JOIN Servico s ON s.id_servico = so.id_servico
                 LEFT JOIN Mecanico m ON m.id_mecanico = so.id_mecanico
                WHERE so.id_ordem_servico = %s
                ORDER BY so.id_servico_os""", (id_os,))
        return [ServicoOS.de_linha(r) for r in cur.fetchall()]

    def inserir_servico(self, cur, s: ServicoOS) -> int:
        cur.execute(
            """INSERT INTO Servico_OS (quantidade, valor_cobrado, em_garantia, id_ordem_servico,
                                       id_servico, id_mecanico)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_servico_os""",
            (s.quantidade, s.valor_cobrado, s.em_garantia, s.id_ordem_servico,
             s.id_servico, s.id_mecanico),
        )
        return cur.fetchone()["id_servico_os"]

    def remover_servico(self, cur, id_servico_os: int, id_os: int) -> None:
        cur.execute("DELETE FROM Servico_OS WHERE id_servico_os = %s AND id_ordem_servico = %s",
                    (id_servico_os, id_os))

    # ---- Peças utilizadas na OS -------------------------------------------
    def listar_pecas(self, cur, id_os: int) -> list[ItemPecaOS]:
        cur.execute(
            """SELECT i.*, p.codigo, p.descricao
                 FROM Item_Peca_OS i
                 JOIN Peca p ON p.id_peca = i.id_peca
                WHERE i.id_ordem_servico = %s
                ORDER BY i.id_item_peca_os""", (id_os,))
        return [ItemPecaOS.de_linha(r) for r in cur.fetchall()]

    def inserir_item_peca(self, cur, i: ItemPecaOS) -> int:
        # valor_total é recalculado pelo gatilho; enviamos o valor coerente por clareza
        cur.execute(
            """INSERT INTO Item_Peca_OS (qtd_utilizada, valor_unitario, valor_total, em_garantia,
                                         id_ordem_servico, id_peca)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_item_peca_os""",
            (i.qtd_utilizada, i.valor_unitario, i.qtd_utilizada * i.valor_unitario,
             i.em_garantia, i.id_ordem_servico, i.id_peca),
        )
        return cur.fetchone()["id_item_peca_os"]

    def remover_item_peca(self, cur, id_item: int, id_os: int) -> None:
        cur.execute("DELETE FROM Item_Peca_OS WHERE id_item_peca_os = %s AND id_ordem_servico = %s",
                    (id_item, id_os))

    # ---- Indicadores do painel inicial ------------------------------------
    def contar_por_status(self, cur) -> dict:
        cur.execute("SELECT status, COUNT(*) AS total FROM Ordem_Servico GROUP BY status")
        return {r["status"]: r["total"] for r in cur.fetchall()}
