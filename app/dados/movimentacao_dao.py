"""DAO (somente consulta) de Movimentacao_Estoque. Os registros são criados pelos gatilhos."""
from typing import Optional

from app.modelo.entidades import Movimentacao

_SELECT = """
    SELECT m.*, p.codigo AS peca_codigo, p.descricao AS peca_descricao,
           CASE WHEN ip.id_item_pedido IS NOT NULL THEN 'Pedido ' || pp.codigo_pedido
                WHEN io.id_item_peca_os IS NOT NULL THEN 'OS ' || os.numero_sequencial
                WHEN left(m.codigo, 11) = 'mov-os-del-' THEN 'Item removido de uma OS'
                WHEN left(m.codigo, 7) = 'mov-os-' THEN 'OS (item removido depois)'
                ELSE 'Ajuste' END AS origem,
           pp.id_pedido_peca AS id_pedido_origem,
           os.id_ordem_servico AS id_os_origem
      FROM Movimentacao_Estoque m
      JOIN Peca p ON p.id_peca = m.id_peca
      LEFT JOIN Item_Pedido ip ON ip.id_item_pedido = m.id_item_pedido
      LEFT JOIN Pedido_Peca pp ON pp.id_pedido_peca = ip.id_pedido_peca
      LEFT JOIN Item_Peca_OS io ON io.id_item_peca_os = m.id_item_peca_os
      LEFT JOIN Ordem_Servico os ON os.id_ordem_servico = io.id_ordem_servico
"""


class MovimentacaoDAO:
    def listar(self, cur, tipo: Optional[str] = None, busca: Optional[str] = None,
               id_peca: Optional[int] = None, limite: int = 200) -> list[Movimentacao]:
        condicoes, params = [], []
        if tipo:
            condicoes.append("m.tipo = %s"); params.append(tipo)
        if id_peca:
            condicoes.append("m.id_peca = %s"); params.append(id_peca)
        if busca:
            condicoes.append("(p.codigo ILIKE %s OR p.descricao ILIKE %s OR m.codigo ILIKE %s)")
            params += [f"%{busca}%"] * 3
        sql = _SELECT + (" WHERE " + " AND ".join(condicoes) if condicoes else "")
        sql += (" ORDER BY m.data_movimentacao DESC, m.hora_movimentacao DESC, "
                "m.id_movimentacao_estoque DESC LIMIT %s")
        params.append(limite)
        cur.execute(sql, params)
        return [Movimentacao.de_linha(r) for r in cur.fetchall()]
