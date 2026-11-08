"""DAO de Servico (catálogo de serviços oferecidos pela oficina)."""
from typing import Optional

from app.modelo.entidades import Servico


class ServicoDAO:
    def inserir(self, cur, s: Servico) -> int:
        cur.execute(
            """INSERT INTO Servico (codigo, descricao, tempo_medio_execucao, valor_mao_obra,
                                    categoria, periodo_garantia)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_servico""",
            (s.codigo, s.descricao, s.tempo_medio_execucao, s.valor_mao_obra,
             s.categoria, s.periodo_garantia),
        )
        return cur.fetchone()["id_servico"]

    def listar(self, cur, busca: Optional[str] = None) -> list[Servico]:
        sql, params = "SELECT * FROM Servico", []
        if busca:
            sql += " WHERE codigo ILIKE %s OR descricao ILIKE %s OR categoria ILIKE %s"
            params = [f"%{busca}%"] * 3
        cur.execute(sql + " ORDER BY codigo", params)
        return [Servico.de_linha(r) for r in cur.fetchall()]

    def buscar_por_id(self, cur, id_servico: int) -> Optional[Servico]:
        cur.execute("SELECT * FROM Servico WHERE id_servico = %s", (id_servico,))
        linha = cur.fetchone()
        return Servico.de_linha(linha) if linha else None
