"""DAO de Cliente (inclui as especializações Cliente_Fisico/Cliente_Juridico e Telefone)."""
from typing import Optional

from app.modelo.entidades import Cliente

_SELECT = """
    SELECT c.id_cliente, c.nome, c.endereco, c.email, c.tipo_cliente,
           COALESCE(f.cpf, j.cnpj) AS documento,
           ARRAY(SELECT t.numero FROM Telefone t
                  WHERE t.id_cliente = c.id_cliente ORDER BY t.numero) AS telefones,
           (SELECT COUNT(*) FROM Veiculo v WHERE v.id_cliente = c.id_cliente) AS qtd_veiculos
      FROM Cliente c
      LEFT JOIN Cliente_Fisico f ON f.id_cliente = c.id_cliente
      LEFT JOIN Cliente_Juridico j ON j.id_cliente = c.id_cliente
"""


class ClienteDAO:
    def inserir(self, cur, cliente: Cliente) -> int:
        cur.execute(
            "INSERT INTO Cliente (nome, endereco, email, tipo_cliente) "
            "VALUES (%s, %s, %s, %s) RETURNING id_cliente",
            (cliente.nome, cliente.endereco, cliente.email, cliente.tipo_cliente),
        )
        id_cliente = cur.fetchone()["id_cliente"]

        if cliente.tipo_cliente == "F":
            cur.execute("INSERT INTO Cliente_Fisico (id_cliente, cpf) VALUES (%s, %s)",
                        (id_cliente, cliente.documento))
        else:
            cur.execute("INSERT INTO Cliente_Juridico (id_cliente, cnpj) VALUES (%s, %s)",
                        (id_cliente, cliente.documento))

        for numero in cliente.telefones:
            cur.execute("INSERT INTO Telefone (id_cliente, numero) VALUES (%s, %s) "
                        "ON CONFLICT DO NOTHING", (id_cliente, numero))
        return id_cliente

    def listar(self, cur, busca: Optional[str] = None) -> list[Cliente]:
        sql, params = _SELECT, []
        if busca:
            sql += " WHERE c.nome ILIKE %s OR COALESCE(f.cpf, j.cnpj) ILIKE %s"
            params = [f"%{busca}%", f"%{busca}%"]
        cur.execute(sql + " ORDER BY c.nome", params)
        return [Cliente.de_linha(r) for r in cur.fetchall()]

    def buscar_por_id(self, cur, id_cliente: int) -> Optional[Cliente]:
        cur.execute(_SELECT + " WHERE c.id_cliente = %s", (id_cliente,))
        linha = cur.fetchone()
        return Cliente.de_linha(linha) if linha else None
