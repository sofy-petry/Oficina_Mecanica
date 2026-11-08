"""Regras de negócio de Mecanico"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Optional

from app.excecoes import ErroNegocio
from app.modelo.entidades import Mecanico
from app.negocio import validacao as v

ESPECIALIDADES = ("mecânica geral", "elétrica", "funilaria", "pintura", "outros")


class MecanicoService:
    ESPECIALIDADES = ESPECIALIDADES

    def __init__(self, banco, mecanico_dao, os_dao=None):
        self._banco = banco
        self._mecanicos = mecanico_dao
        self._os = os_dao

    def cadastrar(self, dados: dict) -> int:
        especialidade = (dados.get("especialidade") or "").strip()
        if especialidade not in ESPECIALIDADES:
            raise ErroNegocio("Selecione uma especialidade válida.")

        admissao = v.data(dados.get("dta_admissao"), "Data de admissão")
        if admissao > date.today():
            raise ErroNegocio("A data de admissão não pode ser futura.")

        mecanico = Mecanico(
            nome=v.texto(dados.get("nome"), "Nome", max_len=100),
            cpf=v.formatar_cpf(dados.get("cpf")),
            dta_admissao=admissao,
            especialidade=especialidade,
            percentual_comissao=v.decimal(dados.get("percentual_comissao") or "0", "Percentual de comissão",
                                          minimo=Decimal("0"), maximo=Decimal("100")),
        )
        with self._banco.cursor() as cur:
            return self._mecanicos.inserir(cur, mecanico)

    def listar(self, busca: Optional[str] = None) -> list[Mecanico]:
        with self._banco.cursor() as cur:
            return self._mecanicos.listar(cur, busca)

    def detalhar(self, id_mecanico: int) -> SimpleNamespace:
        """Dados do mecânico, produção em serviços concluídos e comissão estimada."""
        with self._banco.cursor() as cur:
            mecanico = self._mecanicos.buscar_por_id(cur, id_mecanico)
            if mecanico is None:
                raise ErroNegocio("Mecânico não encontrado.")
            est = self._mecanicos.estatisticas(cur, id_mecanico)
            comissao = (est["producao"] * mecanico.percentual_comissao / 100).quantize(Decimal("0.01"))
            return SimpleNamespace(mecanico=mecanico, os_atendidas=est["os_atendidas"],
                                   producao=est["producao"], comissao=comissao,
                                   ordens=self._os.listar_por_mecanico(cur, id_mecanico))
