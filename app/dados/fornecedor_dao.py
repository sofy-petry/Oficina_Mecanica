"""DAO de Fornecedor e Fornecimento (peças vendidas por cada fornecedor)."""
from typing import Optional

from app.modelo.entidades import Fornecedor, Fornecimento

_SELECT_FORNECIMENTO = """
    SELECT fo.*, f.razao_social, p.codigo, p.descricao, p.qtd_estoque
      FROM Fornecimento fo
      JOIN Fornecedor f ON f.id_fornecedor = fo.id_fornecedor
      JOIN Peca p ON p.id_peca = fo.id_peca
"""


class FornecedorDAO:
    def inserir(self, cur, f: Fornecedor) -> int:
        cur.execute(
            """INSERT INTO Fornecedor (cnpj, razao_social, telefone, email, endereco, condicao_pagamento)
               VALUES (%s, %s, %s, %s, %s, %s) RETURNING id_fornecedor""",
            (f.cnpj, f.razao_social, f.telefone, f.email, f.endereco, f.condicao_pagamento),
        )
        return cur.fetchone()["id_fornecedor"]

    def listar(self, cur, busca: Optional[str] = None) -> list[Fornecedor]:
        sql, params = "SELECT * FROM Fornecedor", []
        if busca:
            sql += " WHERE razao_social ILIKE %s OR cnpj ILIKE %s OR email ILIKE %s"
            params = [f"%{busca}%"] * 3
        cur.execute(sql + " ORDER BY razao_social", params)
        return [Fornecedor.de_linha(r) for r in cur.fetchall()]

    def buscar_por_id(self, cur, id_fornecedor: int) -> Optional[Fornecedor]:
        cur.execute("SELECT * FROM Fornecedor WHERE id_fornecedor = %s", (id_fornecedor,))
        linha = cur.fetchone()
        return Fornecedor.de_linha(linha) if linha else None

    def listar_fornecimentos(self, cur, id_fornecedor: int) -> list[Fornecimento]:
        cur.execute(_SELECT_FORNECIMENTO + " WHERE fo.id_fornecedor = %s ORDER BY p.codigo", (id_fornecedor,))
        return [Fornecimento.de_linha(r) for r in cur.fetchall()]

    def listar_fornecimentos_da_peca(self, cur, id_peca: int) -> list[Fornecimento]:
        cur.execute(_SELECT_FORNECIMENTO + " WHERE fo.id_peca = %s ORDER BY fo.preco_praticado", (id_peca,))
        return [Fornecimento.de_linha(r) for r in cur.fetchall()]

    def vincular_peca(self, cur, id_fornecedor: int, id_peca: int, preco, prazo: int) -> None:
        """Cadastra (ou atualiza) o preço e prazo de uma peça para o fornecedor."""
        cur.execute(
            """INSERT INTO Fornecimento (id_fornecedor, id_peca, preco_praticado, prazo_entrega)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (id_fornecedor, id_peca)
               DO UPDATE SET preco_praticado = EXCLUDED.preco_praticado,
                             prazo_entrega = EXCLUDED.prazo_entrega""",
            (id_fornecedor, id_peca, preco, prazo),
        )
