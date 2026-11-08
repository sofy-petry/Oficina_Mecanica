"""DAO de Pagamento e Parcela. As parcelas são geradas por gatilho ao inserir o pagamento"""
from datetime import date
from typing import Optional

from app.modelo.entidades import Pagamento, Parcela


class PagamentoDAO:
    def inserir(self, cur, p: Pagamento) -> int:
        cur.execute(
            """INSERT INTO Pagamento (codigo, forma_pagamento, valor_total, numero_parcelas,
                                      id_ordem_servico)
               VALUES (%s, %s, %s, %s, %s) RETURNING id_pagamento""",
            (p.codigo, p.forma_pagamento, p.valor_total, p.numero_parcelas, p.id_ordem_servico),
        )
        return cur.fetchone()["id_pagamento"]

    def buscar_por_os(self, cur, id_os: int) -> Optional[Pagamento]:
        cur.execute("SELECT * FROM Pagamento WHERE id_ordem_servico = %s", (id_os,))
        linha = cur.fetchone()
        if not linha:
            return None
        pagamento = Pagamento.de_linha(linha)
        cur.execute("SELECT * FROM Parcela WHERE id_pagamento = %s ORDER BY numero_parcela",
                    (pagamento.id_pagamento,))
        pagamento.parcelas = [Parcela.de_linha(r) for r in cur.fetchall()]
        return pagamento

    def marcar_parcela_paga(self, cur, id_pagamento: int, numero_parcela: int, data: date) -> None:
        cur.execute(
            """UPDATE Parcela SET status = 'pago', dta_pagamento = %s
                WHERE id_pagamento = %s AND numero_parcela = %s""",
            (data, id_pagamento, numero_parcela),
        )
