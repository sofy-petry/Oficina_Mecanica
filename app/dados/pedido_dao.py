"""DAO de Pedido_Peca e Item_Pedido. A entrada no estoque ao entregar é feita por gatilho."""
from typing import Optional

from app.modelo.entidades import ItemPedido, PedidoPeca

_SELECT = """
    SELECT pp.*, f.razao_social, os.numero_sequencial AS numero_os,
           (SELECT COUNT(*) FROM Item_Pedido ip WHERE ip.id_pedido_peca = pp.id_pedido_peca) AS qtd_itens
      FROM Pedido_Peca pp
      JOIN Fornecedor f ON f.id_fornecedor = pp.id_fornecedor
      LEFT JOIN Ordem_Servico os ON os.id_ordem_servico = pp.id_ordem_servico
"""


class PedidoDAO:
    def proximo_id(self, cur) -> int:
        cur.execute("SELECT nextval(pg_get_serial_sequence('pedido_peca', 'id_pedido_peca')) AS id")
        return cur.fetchone()["id"]

    def inserir(self, cur, p: PedidoPeca) -> int:
        cur.execute(
            """INSERT INTO Pedido_Peca (id_pedido_peca, codigo_pedido, previsao_entrega, status,
                                        valor_total, id_fornecedor, id_ordem_servico)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id_pedido_peca""",
            (p.id_pedido_peca, p.codigo_pedido, p.previsao_entrega, p.status, p.valor_total,
             p.id_fornecedor, p.id_ordem_servico),
        )
        return cur.fetchone()["id_pedido_peca"]

    def inserir_item(self, cur, i: ItemPedido) -> int:
        cur.execute(
            """INSERT INTO Item_Pedido (quantidade, valor_unitario, valor_total, id_pedido_peca, id_peca)
               VALUES (%s, %s, %s, %s, %s) RETURNING id_item_pedido""",
            (i.quantidade, i.valor_unitario, i.valor_total, i.id_pedido_peca, i.id_peca),
        )
        return cur.fetchone()["id_item_pedido"]

    def listar(self, cur, status: Optional[str] = None, busca: Optional[str] = None,
               apenas_abertos: bool = False, id_fornecedor: Optional[int] = None,
               id_os: Optional[int] = None, limite: Optional[int] = None) -> list[PedidoPeca]:
        condicoes, params = [], []
        if status:
            condicoes.append("pp.status = %s"); params.append(status)
        if apenas_abertos:
            condicoes.append("pp.status IN ('pendente', 'em trânsito')")
        if id_fornecedor:
            condicoes.append("pp.id_fornecedor = %s"); params.append(id_fornecedor)
        if id_os:
            condicoes.append("pp.id_ordem_servico = %s"); params.append(id_os)
        if busca:
            condicoes.append("(pp.codigo_pedido ILIKE %s OR f.razao_social ILIKE %s)")
            params += [f"%{busca}%"] * 2
        sql = _SELECT + (" WHERE " + " AND ".join(condicoes) if condicoes else "")
        sql += " ORDER BY pp.id_pedido_peca DESC"
        if limite:
            sql += " LIMIT %s"; params.append(limite)
        cur.execute(sql, params)
        return [PedidoPeca.de_linha(r) for r in cur.fetchall()]

    def buscar_por_id(self, cur, id_pedido: int) -> Optional[PedidoPeca]:
        cur.execute(_SELECT + " WHERE pp.id_pedido_peca = %s", (id_pedido,))
        linha = cur.fetchone()
        return PedidoPeca.de_linha(linha) if linha else None

    def listar_itens(self, cur, id_pedido: int) -> list[ItemPedido]:
        cur.execute(
            """SELECT ip.*, p.codigo, p.descricao
                 FROM Item_Pedido ip JOIN Peca p ON p.id_peca = ip.id_peca
                WHERE ip.id_pedido_peca = %s ORDER BY ip.id_item_pedido""", (id_pedido,))
        return [ItemPedido.de_linha(r) for r in cur.fetchall()]

    def atualizar_status(self, cur, id_pedido: int, status: str) -> None:
        cur.execute("UPDATE Pedido_Peca SET status = %s WHERE id_pedido_peca = %s", (status, id_pedido))

    def contar_por_status(self, cur) -> dict:
        cur.execute("SELECT status, COUNT(*) AS total FROM Pedido_Peca GROUP BY status")
        return {r["status"]: r["total"] for r in cur.fetchall()}
