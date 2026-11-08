"""Regras de negócio do catálogo de Servico"""
from decimal import Decimal
from typing import Optional

from app.modelo.entidades import Servico
from app.negocio import validacao as v


class ServicoService:
    def __init__(self, banco, servico_dao):
        self._banco = banco
        self._servicos = servico_dao

    def cadastrar(self, dados: dict) -> int:
        servico = Servico(
            codigo=v.texto(dados.get("codigo"), "Código", max_len=20).upper(),
            descricao=v.texto(dados.get("descricao"), "Descrição", max_len=150),
            tempo_medio_execucao=v.inteiro(dados.get("tempo_medio_execucao"),
                                           "Tempo médio de execução (min)", minimo=1),
            valor_mao_obra=v.decimal(dados.get("valor_mao_obra"), "Valor da mão de obra",
                                     minimo=Decimal("0")),
            categoria=v.texto(dados.get("categoria"), "Categoria", max_len=50),
            periodo_garantia=v.inteiro(dados.get("periodo_garantia") or "0", "Período de garantia (dias)",
                                       minimo=0),
        )
        with self._banco.cursor() as cur:
            return self._servicos.inserir(cur, servico)

    def listar(self, busca: Optional[str] = None) -> list[Servico]:
        with self._banco.cursor() as cur:
            return self._servicos.listar(cur, busca)
