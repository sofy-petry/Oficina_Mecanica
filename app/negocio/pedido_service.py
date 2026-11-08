"""Regras de negócio dos pedidos de peças a fornecedores

Ao marcar um pedido como 'entregue', o gatilho do banco dá entrada no estoque e registra
as movimentações. Aqui validamos o fluxo de status e montamos o pedido a partir do
catálogo de fornecimento (preço e prazo praticados pelo fornecedor)
"""
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Optional

from app.excecoes import ErroNegocio
from app.modelo.entidades import ItemPedido, PedidoPeca
from app.negocio import validacao as v


class PedidoService:
    STATUS = PedidoPeca.STATUS_VALIDOS
    TRANSICOES = PedidoPeca.TRANSICOES

    def __init__(self, banco, pedido_dao, fornecedor_dao, os_dao):
        self._banco = banco
        self._pedidos = pedido_dao
        self._fornecedores = fornecedor_dao
        self._os = os_dao

    def listar(self, status: Optional[str] = None, busca: Optional[str] = None) -> list[PedidoPeca]:
        if status and status not in self.STATUS:
            raise ErroNegocio("Status inválido.")
        with self._banco.cursor() as cur:
            return self._pedidos.listar(cur, status=status, busca=busca)

    def contagem_por_status(self) -> dict:
        with self._banco.cursor() as cur:
            return self._pedidos.contar_por_status(cur)

    def detalhar(self, id_pedido: int) -> SimpleNamespace:
        with self._banco.cursor() as cur:
            pedido = self._pedidos.buscar_por_id(cur, id_pedido)
            if pedido is None:
                raise ErroNegocio("Pedido não encontrado.")
            return SimpleNamespace(pedido=pedido, itens=self._pedidos.listar_itens(cur, id_pedido),
                                   proximos=self.TRANSICOES[pedido.status])

    def dados_para_novo(self, id_fornecedor: Optional[int] = None) -> SimpleNamespace:
        """Etapa 1: escolher o fornecedor. Etapa 2: informar as quantidades das peças dele."""
        with self._banco.cursor() as cur:
            fornecedor, fornecimentos = None, []
            if id_fornecedor:
                fornecedor = self._fornecedores.buscar_por_id(cur, id_fornecedor)
                if fornecedor is None:
                    raise ErroNegocio("Fornecedor não encontrado.")
                fornecimentos = self._fornecedores.listar_fornecimentos(cur, id_fornecedor)
            return SimpleNamespace(
                fornecedores=self._fornecedores.listar(cur),
                fornecedor=fornecedor,
                fornecimentos=fornecimentos,
                ordens=[o for o in self._os.listar(cur) if o.em_andamento],  # OS que podem receber o pedido
            )

    def criar(self, dados) -> int:
        id_fornecedor = v.inteiro(dados.get("id_fornecedor"), "Fornecedor", minimo=1)
        id_os = v.inteiro(dados.get("id_ordem_servico"), "Ordem de serviço", minimo=1, obrigatorio=False)
        previsao = v.data(dados.get("previsao_entrega"), "Previsão de entrega", obrigatorio=False)
        hoje = date.today()
        if previsao and previsao < hoje:
            raise ErroNegocio("A previsão de entrega não pode ser anterior a hoje.")

        with self._banco.cursor() as cur:
            if self._fornecedores.buscar_por_id(cur, id_fornecedor) is None:
                raise ErroNegocio("Fornecedor não encontrado.")
            if id_os and self._os.buscar_por_id(cur, id_os) is None:
                raise ErroNegocio("Ordem de serviço não encontrada.")

            itens, prazo_max = [], 0
            for f in self._fornecedores.listar_fornecimentos(cur, id_fornecedor):
                qtd = v.inteiro(dados.get(f"qtd_{f.id_peca}") or "0", f"Quantidade de {f.codigo}", minimo=0)
                if qtd > 0:
                    itens.append((f, qtd))
                    prazo_max = max(prazo_max, f.prazo_entrega)
            if not itens:
                raise ErroNegocio("Informe a quantidade de pelo menos uma peça.")

            id_pedido = self._pedidos.proximo_id(cur)
            total = sum((f.preco_praticado * qtd for f, qtd in itens), Decimal("0"))
            self._pedidos.inserir(cur, PedidoPeca(
                id_pedido_peca=id_pedido,
                codigo_pedido=f"PED-{hoje.year}-{id_pedido:05d}",
                data_pedido=hoje,
                previsao_entrega=previsao or hoje + timedelta(days=prazo_max),
                status="pendente",
                valor_total=total,
                id_fornecedor=id_fornecedor,
                id_ordem_servico=id_os,
            ))
            for f, qtd in itens:
                self._pedidos.inserir_item(cur, ItemPedido(
                    quantidade=qtd, valor_unitario=f.preco_praticado,
                    valor_total=f.preco_praticado * qtd,
                    id_pedido_peca=id_pedido, id_peca=f.id_peca))
            return id_pedido

    def alterar_status(self, id_pedido: int, novo_status: str) -> None:
        if novo_status not in self.STATUS:
            raise ErroNegocio("Status inválido.")
        with self._banco.cursor() as cur:
            pedido = self._pedidos.buscar_por_id(cur, id_pedido)
            if pedido is None:
                raise ErroNegocio("Pedido não encontrado.")
            if novo_status not in self.TRANSICOES[pedido.status]:
                raise ErroNegocio(f"Um pedido '{pedido.status}' não pode passar para '{novo_status}'.")
            self._pedidos.atualizar_status(cur, id_pedido, novo_status)  # gatilho: entrada no estoque
