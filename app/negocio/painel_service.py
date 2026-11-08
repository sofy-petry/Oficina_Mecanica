"""Monta os dados do painel inicial (indicadores, quadro de OS, gráfico e alertas)"""
from decimal import Decimal
from types import SimpleNamespace

from app.modelo.entidades import OrdemServico

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
COLUNAS_QUADRO = ("aguardando aprovação", "aguardando peças", "em execução", "concluída")


class PainelService:
    def __init__(self, banco, painel_dao, os_dao, peca_dao, pedido_dao):
        self._banco = banco
        self._painel = painel_dao
        self._os = os_dao
        self._pecas = peca_dao
        self._pedidos = pedido_dao

    def painel(self) -> SimpleNamespace:
        with self._banco.cursor() as cur:
            meses = self._painel.faturamento_mensal(cur, 6)
            maior = max((m["total"] for m in meses), default=Decimal("0")) or Decimal("1")
            grafico = [
                {"rotulo": MESES[m["mes"].month - 1], "total": m["total"],
                 "pct": max(3, round(m["total"] / maior * 100)) if m["total"] else 0}
                for m in meses
            ]
            return SimpleNamespace(
                kpis=SimpleNamespace(**self._painel.indicadores(cur)),
                por_status=self._os.contar_por_status(cur),
                quadro=[(s, self._os.listar(cur, status=s, limite=5)) for s in COLUNAS_QUADRO],
                faturamento=grafico,
                prazos=self._os.listar_prazos(cur, 6),
                estoque_baixo=self._pecas.listar(cur, apenas_estoque_baixo=True),
                pedidos_abertos=self._pedidos.listar(cur, apenas_abertos=True, limite=5),
                parcelas_vencidas=self._painel.parcelas_vencidas(cur, 5),
            )
