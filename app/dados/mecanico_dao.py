"""DAO de Mecanico."""
from typing import Optional

from app.modelo.entidades import Mecanico


class MecanicoDAO:
    def inserir(self, cur, m: Mecanico) -> int:
        cur.execute(
            """INSERT INTO Mecanico (nome, cpf, dta_admissao, especialidade, percentual_comissao)
               VALUES (%s, %s, %s, %s, %s) RETURNING id_mecanico""",
            (m.nome, m.cpf, m.dta_admissao, m.especialidade, m.percentual_comissao),
        )
        return cur.fetchone()["id_mecanico"]

    _SELECT = """
        SELECT m.*,
               (SELECT COUNT(*) FROM Ordem_Servico os
                 WHERE os.id_mecanico_responsavel = m.id_mecanico
                   AND os.status IN ('aguardando aprovação', 'aguardando peças', 'em execução')) AS os_abertas
          FROM Mecanico m
    """

    def listar(self, cur, busca: Optional[str] = None) -> list[Mecanico]:
        sql, params = self._SELECT, []
        if busca:
            sql += " WHERE m.nome ILIKE %s OR m.cpf ILIKE %s OR m.especialidade ILIKE %s"
            params = [f"%{busca}%"] * 3
        cur.execute(sql + " ORDER BY m.nome", params)
        return [Mecanico.de_linha(r) for r in cur.fetchall()]

    def buscar_por_id(self, cur, id_mecanico: int) -> Optional[Mecanico]:
        cur.execute(self._SELECT + " WHERE m.id_mecanico = %s", (id_mecanico,))
        linha = cur.fetchone()
        return Mecanico.de_linha(linha) if linha else None

    def estatisticas(self, cur, id_mecanico: int) -> dict:
        """Produção em serviços de OS concluídas/entregues (itens em garantia não contam)."""
        cur.execute(
            """SELECT COUNT(DISTINCT so.id_ordem_servico) AS os_atendidas,
                      COALESCE(SUM(CASE WHEN so.em_garantia THEN 0
                                        ELSE so.valor_cobrado * so.quantidade END), 0) AS producao
                 FROM Servico_OS so
                 JOIN Ordem_Servico os ON os.id_ordem_servico = so.id_ordem_servico
                WHERE so.id_mecanico = %s AND os.status IN ('concluída', 'entregue')""",
            (id_mecanico,))
        return cur.fetchone()
