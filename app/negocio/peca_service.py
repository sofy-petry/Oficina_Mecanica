"""Regras de negócio de Peca (estoque e compatibilidade)"""
from decimal import Decimal
from types import SimpleNamespace
from typing import Optional

from app.excecoes import ErroNegocio
from app.modelo.entidades import Peca
from app.negocio import validacao as v


class PecaService:
    def __init__(self, banco, peca_dao, fornecedor_dao=None, movimentacao_dao=None):
        self._banco = banco
        self._pecas = peca_dao
        self._fornecedores = fornecedor_dao
        self._movimentacoes = movimentacao_dao

    def cadastrar(self, dados: dict) -> int:
        custo = v.decimal(dados.get("preco_custo"), "Preço de custo", minimo=Decimal("0"))
        venda = v.decimal(dados.get("preco_venda"), "Preço de venda", minimo=Decimal("0"))
        if venda < custo:
            raise ErroNegocio("O preço de venda não pode ser menor que o preço de custo.")

        peca = Peca(
            codigo=v.texto(dados.get("codigo"), "Código", max_len=30).upper(),
            descricao=v.texto(dados.get("descricao"), "Descrição", max_len=150),
            fabricante=v.texto(dados.get("fabricante"), "Fabricante", max_len=80),
            cod_fabricante=v.texto(dados.get("cod_fabricante"), "Código do fabricante",
                                   obrigatorio=False, max_len=50),
            qtd_estoque=v.inteiro(dados.get("qtd_estoque") or "0", "Quantidade em estoque", minimo=0),
            qtd_minimo=v.inteiro(dados.get("qtd_minimo") or "1", "Estoque mínimo", minimo=0),
            preco_custo=custo,
            preco_venda=venda,
            periodo_garantia=v.inteiro(dados.get("periodo_garantia") or "0", "Período de garantia (dias)",
                                       minimo=0),
            marcas=v.lista_separada(dados.get("marcas")),
            modelos=v.lista_separada(dados.get("modelos")),
        )
        with self._banco.cursor() as cur:
            return self._pecas.inserir(cur, peca)

    def listar(self, busca: Optional[str] = None, apenas_estoque_baixo: bool = False) -> list[Peca]:
        with self._banco.cursor() as cur:
            return self._pecas.listar(cur, busca, apenas_estoque_baixo)

    def detalhar(self, id_peca: int) -> SimpleNamespace:
        with self._banco.cursor() as cur:
            peca = self._pecas.buscar_por_id(cur, id_peca)
            if peca is None:
                raise ErroNegocio("Peça não encontrada.")
            return SimpleNamespace(
                peca=peca,
                fornecimentos=self._fornecedores.listar_fornecimentos_da_peca(cur, id_peca),
                movimentacoes=self._movimentacoes.listar(cur, id_peca=id_peca, limite=30),
            )

    def movimentacoes(self, tipo: Optional[str] = None, busca: Optional[str] = None):
        if tipo and tipo not in ("ENTRADA", "SAIDA"):
            raise ErroNegocio("Tipo de movimentação inválido.")
        with self._banco.cursor() as cur:
            return self._movimentacoes.listar(cur, tipo=tipo, busca=busca)
