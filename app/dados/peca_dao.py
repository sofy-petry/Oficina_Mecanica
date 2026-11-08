"""DAO de Peca (inclui compatibilidade por marca/modelo)."""
from typing import Optional

from app.modelo.entidades import Peca

_SELECT = """
    SELECT p.*,
           ARRAY(SELECT m.nome_marca FROM Peca_Marca m
                  WHERE m.id_peca = p.id_peca ORDER BY m.nome_marca) AS marcas,
           ARRAY(SELECT o.nome_modelo FROM Peca_Modelo o
                  WHERE o.id_peca = p.id_peca ORDER BY o.nome_modelo) AS modelos
      FROM Peca p
"""


class PecaDAO:
    def inserir(self, cur, p: Peca) -> int:
        cur.execute(
            """INSERT INTO Peca (codigo, descricao, fabricante, cod_fabricante, qtd_estoque,
                                 qtd_minimo, preco_custo, preco_venda, periodo_garantia)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id_peca""",
            (p.codigo, p.descricao, p.fabricante, p.cod_fabricante, p.qtd_estoque,
             p.qtd_minimo, p.preco_custo, p.preco_venda, p.periodo_garantia),
        )
        id_peca = cur.fetchone()["id_peca"]
        for marca in p.marcas:
            cur.execute("INSERT INTO Peca_Marca (id_peca, nome_marca) VALUES (%s, %s) "
                        "ON CONFLICT DO NOTHING", (id_peca, marca))
        for modelo in p.modelos:
            cur.execute("INSERT INTO Peca_Modelo (id_peca, nome_modelo) VALUES (%s, %s) "
                        "ON CONFLICT DO NOTHING", (id_peca, modelo))
        return id_peca

    def listar(self, cur, busca: Optional[str] = None, apenas_estoque_baixo: bool = False) -> list[Peca]:
        condicoes, params = [], []
        if busca:
            condicoes.append("(p.codigo ILIKE %s OR p.descricao ILIKE %s OR p.fabricante ILIKE %s)")
            params += [f"%{busca}%"] * 3
        if apenas_estoque_baixo:
            condicoes.append("p.qtd_estoque <= p.qtd_minimo")
        sql = _SELECT + (" WHERE " + " AND ".join(condicoes) if condicoes else "")
        cur.execute(sql + " ORDER BY p.codigo", params)
        return [Peca.de_linha(r) for r in cur.fetchall()]

    def buscar_por_id(self, cur, id_peca: int) -> Optional[Peca]:
        cur.execute(_SELECT + " WHERE p.id_peca = %s", (id_peca,))
        linha = cur.fetchone()
        return Peca.de_linha(linha) if linha else None
