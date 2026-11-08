"""DAO de Veiculo."""
from typing import Optional

from app.modelo.entidades import Veiculo

_SELECT = """
    SELECT v.*, c.nome AS nome_cliente
      FROM Veiculo v
      JOIN Cliente c ON c.id_cliente = v.id_cliente
"""


class VeiculoDAO:
    def inserir(self, cur, v: Veiculo) -> int:
        cur.execute(
            """INSERT INTO Veiculo (placa, marca, modelo, ano_fabricacao, cor, numero_chassi,
                                    quilometragem_atual, observacoes, id_cliente)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id_veiculo""",
            (v.placa, v.marca, v.modelo, v.ano_fabricacao, v.cor, v.numero_chassi,
             v.quilometragem_atual, v.observacoes, v.id_cliente),
        )
        return cur.fetchone()["id_veiculo"]

    def listar(self, cur, busca: Optional[str] = None) -> list[Veiculo]:
        sql, params = _SELECT, []
        if busca:
            sql += (" WHERE v.placa ILIKE %s OR v.marca ILIKE %s OR v.modelo ILIKE %s"
                    " OR c.nome ILIKE %s")
            params = [f"%{busca}%"] * 4
        cur.execute(sql + " ORDER BY v.placa", params)
        return [Veiculo.de_linha(r) for r in cur.fetchall()]

    def listar_por_cliente(self, cur, id_cliente: int) -> list[Veiculo]:
        cur.execute(_SELECT + " WHERE v.id_cliente = %s ORDER BY v.placa", (id_cliente,))
        return [Veiculo.de_linha(r) for r in cur.fetchall()]

    def buscar_por_id(self, cur, id_veiculo: int) -> Optional[Veiculo]:
        cur.execute(_SELECT + " WHERE v.id_veiculo = %s", (id_veiculo,))
        linha = cur.fetchone()
        return Veiculo.de_linha(linha) if linha else None
