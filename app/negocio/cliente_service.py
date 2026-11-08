"""Regras de negócio de Cliente"""
from typing import Optional

from app.excecoes import ErroNegocio
from app.modelo.entidades import Cliente
from app.negocio import validacao as v


class ClienteService:
    def __init__(self, banco, cliente_dao, veiculo_dao, os_dao):
        self._banco = banco
        self._clientes = cliente_dao
        self._veiculos = veiculo_dao
        self._os = os_dao

    def cadastrar(self, dados: dict) -> int:
        tipo = (dados.get("tipo_cliente") or "").upper()
        if tipo not in ("F", "J"):
            raise ErroNegocio("Selecione o tipo de cliente (pessoa física ou jurídica).")

        documento = (v.formatar_cpf(dados.get("documento")) if tipo == "F"
                     else v.formatar_cnpj(dados.get("documento")))
        email = v.texto(dados.get("email"), "E-mail", obrigatorio=False, max_len=100)
        if email and "@" not in email:
            raise ErroNegocio("Informe um e-mail válido.")

        cliente = Cliente(
            nome=v.texto(dados.get("nome"), "Nome", max_len=100),
            endereco=v.texto(dados.get("endereco"), "Endereço", max_len=200),
            tipo_cliente=tipo,
            documento=documento,
            email=email,
            telefones=v.lista_separada(dados.get("telefones")),
        )
        if any(len(t) > 20 for t in cliente.telefones):
            raise ErroNegocio("Cada telefone aceita no máximo 20 caracteres.")

        with self._banco.cursor() as cur:  # uma única transação (cliente + especialização + telefones)
            return self._clientes.inserir(cur, cliente)

    def listar(self, busca: Optional[str] = None) -> list[Cliente]:
        with self._banco.cursor() as cur:
            return self._clientes.listar(cur, busca)

    def detalhar(self, id_cliente: int):
        """Retorna (cliente, veículos do cliente, histórico de OS)."""
        with self._banco.cursor() as cur:
            cliente = self._clientes.buscar_por_id(cur, id_cliente)
            if cliente is None:
                raise ErroNegocio("Cliente não encontrado.")
            return (cliente, self._veiculos.listar_por_cliente(cur, id_cliente),
                    self._os.listar_por_cliente(cur, id_cliente))
