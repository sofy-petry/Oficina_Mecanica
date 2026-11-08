"""Regras de negócio de Fornecedor e do vínculo Fornecimento (peça x fornecedor)"""
from decimal import Decimal
from types import SimpleNamespace
from typing import Optional

from app.excecoes import ErroNegocio
from app.modelo.entidades import Fornecedor
from app.negocio import validacao as v


class FornecedorService:
    def __init__(self, banco, fornecedor_dao, peca_dao, pedido_dao):
        self._banco = banco
        self._fornecedores = fornecedor_dao
        self._pecas = peca_dao
        self._pedidos = pedido_dao

    def cadastrar(self, dados: dict) -> int:
        email = v.texto(dados.get("email"), "E-mail", obrigatorio=False, max_len=100)
        if email and "@" not in email:
            raise ErroNegocio("Informe um e-mail válido.")
        fornecedor = Fornecedor(
            cnpj=v.formatar_cnpj(dados.get("cnpj")),
            razao_social=v.texto(dados.get("razao_social"), "Razão social", max_len=120),
            telefone=v.texto(dados.get("telefone"), "Telefone", max_len=20),
            email=email,
            endereco=v.texto(dados.get("endereco"), "Endereço", max_len=200),
            condicao_pagamento=v.texto(dados.get("condicao_pagamento"), "Condição de pagamento",
                                       obrigatorio=False, max_len=100),
        )
        with self._banco.cursor() as cur:
            return self._fornecedores.inserir(cur, fornecedor)

    def listar(self, busca: Optional[str] = None) -> list[Fornecedor]:
        with self._banco.cursor() as cur:
            return self._fornecedores.listar(cur, busca)

    def detalhar(self, id_fornecedor: int) -> SimpleNamespace:
        with self._banco.cursor() as cur:
            fornecedor = self._fornecedores.buscar_por_id(cur, id_fornecedor)
            if fornecedor is None:
                raise ErroNegocio("Fornecedor não encontrado.")
            return SimpleNamespace(
                fornecedor=fornecedor,
                fornecimentos=self._fornecedores.listar_fornecimentos(cur, id_fornecedor),
                pedidos=self._pedidos.listar(cur, id_fornecedor=id_fornecedor),
                pecas=self._pecas.listar(cur),  # para o formulário de vínculo
            )

    def vincular_peca(self, id_fornecedor: int, dados: dict) -> None:
        id_peca = v.inteiro(dados.get("id_peca"), "Peça", minimo=1)
        preco = v.decimal(dados.get("preco_praticado"), "Preço praticado", minimo=Decimal("0"))
        prazo = v.inteiro(dados.get("prazo_entrega"), "Prazo de entrega (dias)", minimo=0)
        with self._banco.cursor() as cur:
            if self._fornecedores.buscar_por_id(cur, id_fornecedor) is None:
                raise ErroNegocio("Fornecedor não encontrado.")
            if self._pecas.buscar_por_id(cur, id_peca) is None:
                raise ErroNegocio("Peça não encontrada.")
            self._fornecedores.vincular_peca(cur, id_fornecedor, id_peca, preco, prazo)
