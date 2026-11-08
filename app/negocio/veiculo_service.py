"""Regras de negócio de Veiculo"""
import re
from datetime import date
from typing import Optional

from app.excecoes import ErroNegocio
from app.modelo.entidades import Veiculo
from app.negocio import validacao as v


class VeiculoService:
    def __init__(self, banco, veiculo_dao, cliente_dao, os_dao=None):
        self._banco = banco
        self._veiculos = veiculo_dao
        self._clientes = cliente_dao
        self._os = os_dao

    def cadastrar(self, dados: dict) -> int:
        placa = v.texto(dados.get("placa"), "Placa").upper().replace("-", "")
        if not re.fullmatch(r"[A-Z0-9]{7}", placa):
            raise ErroNegocio("A placa deve ter 7 caracteres alfanuméricos (ex.: ABC1D23).")

        veiculo = Veiculo(
            placa=placa,
            marca=v.texto(dados.get("marca"), "Marca", max_len=50),
            modelo=v.texto(dados.get("modelo"), "Modelo", max_len=50),
            ano_fabricacao=v.inteiro(dados.get("ano_fabricacao"), "Ano de fabricação",
                                     minimo=1901, maximo=date.today().year + 1),
            cor=v.texto(dados.get("cor"), "Cor", obrigatorio=False, max_len=30),
            numero_chassi=v.texto(dados.get("numero_chassi"), "Número do chassi", max_len=30).upper(),
            quilometragem_atual=v.inteiro(dados.get("quilometragem_atual"), "Quilometragem atual", minimo=0),
            observacoes=v.texto(dados.get("observacoes"), "Observações", obrigatorio=False),
            id_cliente=v.inteiro(dados.get("id_cliente"), "Cliente", minimo=1),
        )
        with self._banco.cursor() as cur:
            if self._clientes.buscar_por_id(cur, veiculo.id_cliente) is None:
                raise ErroNegocio("Cliente não encontrado.")
            return self._veiculos.inserir(cur, veiculo)

    def listar(self, busca: Optional[str] = None) -> list[Veiculo]:
        with self._banco.cursor() as cur:
            return self._veiculos.listar(cur, busca)

    def clientes_para_selecao(self):
        with self._banco.cursor() as cur:
            return self._clientes.listar(cur)

    def detalhar(self, id_veiculo: int):
        """Retorna (veículo, histórico de OS do veículo)."""
        with self._banco.cursor() as cur:
            veiculo = self._veiculos.buscar_por_id(cur, id_veiculo)
            if veiculo is None:
                raise ErroNegocio("Veículo não encontrado.")
            return veiculo, self._os.listar_por_veiculo(cur, id_veiculo)
