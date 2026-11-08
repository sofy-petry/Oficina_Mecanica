"""Regras de negócio da Ordem de Serviço (serviços, peças, status, desconto e pagamento)

Boa parte das regras de integridade (estoque, compatibilidade, totais, bloqueio de OS
fechada, limite de desconto, geração de parcelas) já é garantida por gatilhos no banco.
Esta camada valida a entrada, aplica regras de fluxo e devolve os dados já montados.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from typing import Optional

from app.excecoes import ErroNegocio
from app.modelo.entidades import ItemPecaOS, OrdemServico, Pagamento, ServicoOS
from app.negocio import validacao as v

FORMAS_PAGAMENTO = ("dinheiro", "cartão de crédito", "cartão de débito", "pix", "boleto")
FORMAS_PARCELAVEIS = ("cartão de crédito", "boleto")
MAX_PARCELAS = 12


@dataclass
class DetalheOS:
    os: OrdemServico
    servicos: list = field(default_factory=list)
    pecas: list = field(default_factory=list)
    pagamento: Optional[Pagamento] = None
    pedidos: list = field(default_factory=list)

    @property
    def pode_pagar(self) -> bool:
        return self.os.status in ("concluída", "entregue") and self.pagamento is None \
            and self.os.valor_total > 0


class OrdemServicoService:
    STATUS = OrdemServico.STATUS_VALIDOS
    FORMAS_PAGAMENTO = FORMAS_PAGAMENTO

    def __init__(self, banco, os_dao, veiculo_dao, mecanico_dao, servico_dao, peca_dao, pagamento_dao,
                 pedido_dao):
        self._banco = banco
        self._os = os_dao
        self._veiculos = veiculo_dao
        self._mecanicos = mecanico_dao
        self._servicos = servico_dao
        self._pecas = peca_dao
        self._pagamentos = pagamento_dao
        self._pedidos = pedido_dao

    # Abertura e consulta ----------------------------------------------
    def abrir(self, dados: dict) -> int:
        id_veiculo = v.inteiro(dados.get("id_veiculo"), "Veículo", minimo=1)
        km = v.inteiro(dados.get("quilometragem_entrada"), "Quilometragem de entrada", minimo=0)
        previsao = v.data(dados.get("dta_previsao_conclusao"), "Previsão de conclusão", obrigatorio=False)
        if previsao and previsao < date.today():
            raise ErroNegocio("A previsão de conclusão não pode ser anterior a hoje.")
        id_mecanico = v.inteiro(dados.get("id_mecanico_responsavel"), "Mecânico responsável",
                                minimo=1, obrigatorio=False)
        problema = v.texto(dados.get("descricao_problema"), "Descrição do problema")

        with self._banco.cursor() as cur:
            veiculo = self._veiculos.buscar_por_id(cur, id_veiculo)
            if veiculo is None:
                raise ErroNegocio("Veículo não encontrado.")
            if km < veiculo.quilometragem_atual:
                raise ErroNegocio(
                    f"A quilometragem de entrada ({km}) não pode ser menor que a atual do "
                    f"veículo ({veiculo.quilometragem_atual})."
                )
            if id_mecanico and self._mecanicos.buscar_por_id(cur, id_mecanico) is None:
                raise ErroNegocio("Mecânico não encontrado.")

            id_os = self._os.proximo_id(cur)
            os = OrdemServico(
                id_ordem_servico=id_os,
                numero_sequencial=f"OS-{date.today().year}-{id_os:05d}",
                quilometragem_entrada=km,
                descricao_problema=problema,
                id_veiculo=id_veiculo,
                status="aguardando aprovação",
                dta_previsao_conclusao=previsao,
                id_mecanico_responsavel=id_mecanico,
            )
            return self._os.inserir(cur, os)  # gatilho atualiza a km do veículo

    def listar(self, status: Optional[str] = None, busca: Optional[str] = None) -> list[OrdemServico]:
        if status and status not in self.STATUS:
            raise ErroNegocio("Status inválido.")
        with self._banco.cursor() as cur:
            return self._os.listar(cur, status, busca)

    def detalhar(self, id_os: int) -> DetalheOS:
        with self._banco.cursor() as cur:
            os = self._os.buscar_por_id(cur, id_os)
            if os is None:
                raise ErroNegocio("Ordem de serviço não encontrada.")
            return DetalheOS(
                os=os,
                servicos=self._os.listar_servicos(cur, id_os),
                pecas=self._os.listar_pecas(cur, id_os),
                pagamento=self._pagamentos.buscar_por_os(cur, id_os),
                pedidos=self._pedidos.listar(cur, id_os=id_os),
            )

    def dados_para_abertura(self) -> SimpleNamespace:
        with self._banco.cursor() as cur:
            return SimpleNamespace(veiculos=self._veiculos.listar(cur),
                                   mecanicos=self._mecanicos.listar(cur))

    def dados_para_lancamento(self) -> SimpleNamespace:
        with self._banco.cursor() as cur:
            return SimpleNamespace(servicos=self._servicos.listar(cur),
                                   pecas=self._pecas.listar(cur),
                                   mecanicos=self._mecanicos.listar(cur))

    def contagem_por_status(self) -> dict:
        with self._banco.cursor() as cur:
            return self._os.contar_por_status(cur)

    # Lançamentos 
    def adicionar_servico(self, id_os: int, dados: dict) -> None:
        id_servico = v.inteiro(dados.get("id_servico"), "Serviço", minimo=1)
        quantidade = v.inteiro(dados.get("quantidade") or "1", "Quantidade", minimo=1)
        id_mecanico = v.inteiro(dados.get("id_mecanico"), "Mecânico", minimo=1, obrigatorio=False)
        valor = v.decimal(dados.get("valor_cobrado"), "Valor cobrado", minimo=Decimal("0"),
                          obrigatorio=False)

        with self._banco.cursor() as cur:
            os = self._exigir_os_aberta(cur, id_os)
            servico = self._servicos.buscar_por_id(cur, id_servico)
            if servico is None:
                raise ErroNegocio("Serviço não encontrado.")
            if id_mecanico is None:
                id_mecanico = os.id_mecanico_responsavel
            self._os.inserir_servico(cur, ServicoOS(
                quantidade=quantidade,
                valor_cobrado=valor if valor is not None else servico.valor_mao_obra,
                em_garantia=v.marcado(dados.get("em_garantia")),
                id_ordem_servico=id_os,
                id_servico=id_servico,
                id_mecanico=id_mecanico,
            ))

    def adicionar_peca(self, id_os: int, dados: dict) -> None:
        id_peca = v.inteiro(dados.get("id_peca"), "Peça", minimo=1)
        quantidade = v.inteiro(dados.get("qtd_utilizada") or "1", "Quantidade", minimo=1)
        valor = v.decimal(dados.get("valor_unitario"), "Valor unitário", minimo=Decimal("0"),
                          obrigatorio=False)

        with self._banco.cursor() as cur:
            self._exigir_os_aberta(cur, id_os)
            peca = self._pecas.buscar_por_id(cur, id_peca)
            if peca is None:
                raise ErroNegocio("Peça não encontrada.")
            if peca.qtd_estoque < quantidade:
                raise ErroNegocio(
                    f"Estoque insuficiente de '{peca.descricao}': disponível {peca.qtd_estoque}, "
                    f"solicitado {quantidade}. Registre um pedido ao fornecedor."
                )
            # compatibilidade com marca/modelo e baixa de estoque: gatilhos do banco
            self._os.inserir_item_peca(cur, ItemPecaOS(
                qtd_utilizada=quantidade,
                valor_unitario=valor if valor is not None else peca.preco_venda,
                em_garantia=v.marcado(dados.get("em_garantia")),
                id_ordem_servico=id_os,
                id_peca=id_peca,
            ))

    def remover_servico(self, id_os: int, id_servico_os: int) -> None:
        with self._banco.cursor() as cur:
            self._exigir_os_aberta(cur, id_os)
            self._os.remover_servico(cur, id_servico_os, id_os)

    def remover_peca(self, id_os: int, id_item: int) -> None:
        with self._banco.cursor() as cur:
            self._exigir_os_aberta(cur, id_os)
            self._os.remover_item_peca(cur, id_item, id_os)  # gatilho devolve ao estoque

    # Status e desconto 
    def alterar_status(self, id_os: int, novo_status: str) -> None:
        if novo_status not in self.STATUS:
            raise ErroNegocio("Status inválido.")
        with self._banco.cursor() as cur:
            os = self._os.buscar_por_id(cur, id_os)
            if os is None:
                raise ErroNegocio("Ordem de serviço não encontrada.")
            if os.status == novo_status:
                return
            self._os.atualizar_status(cur, id_os, novo_status)  # gatilho valida a transição

    def aplicar_desconto(self, id_os: int, dados: dict) -> None:
        desconto = v.decimal(dados.get("desconto") or "0", "Desconto", minimo=Decimal("0"))
        with self._banco.cursor() as cur:
            self._exigir_os_aberta(cur, id_os)
            self._os.atualizar_desconto(cur, id_os, desconto)  # gatilho limita a 20%

    # Pagamento 
    def registrar_pagamento(self, id_os: int, dados: dict) -> None:
        forma = (dados.get("forma_pagamento") or "").strip()
        if forma not in FORMAS_PAGAMENTO:
            raise ErroNegocio("Selecione uma forma de pagamento válida.")
        parcelas = v.inteiro(dados.get("numero_parcelas") or "1", "Número de parcelas",
                             minimo=1, maximo=MAX_PARCELAS)
        if parcelas > 1 and forma not in FORMAS_PARCELAVEIS:
            raise ErroNegocio("Só é possível parcelar no cartão de crédito ou boleto.")

        with self._banco.cursor() as cur:
            os = self._os.buscar_por_id(cur, id_os)
            if os is None:
                raise ErroNegocio("Ordem de serviço não encontrada.")
            if os.status not in ("concluída", "entregue"):
                raise ErroNegocio("O pagamento só pode ser registrado após a conclusão da OS.")
            if os.valor_total <= 0:
                raise ErroNegocio("A OS não possui valor a ser cobrado.")
            self._pagamentos.inserir(cur, Pagamento(  # gatilho gera as parcelas
                codigo=f"PAG-{os.numero_sequencial}",
                forma_pagamento=forma,
                valor_total=os.valor_total,
                numero_parcelas=parcelas,
                id_ordem_servico=id_os,
            ))

    def pagar_parcela(self, id_os: int, numero_parcela: int) -> None:
        with self._banco.cursor() as cur:
            pagamento = self._pagamentos.buscar_por_os(cur, id_os)
            if pagamento is None:
                raise ErroNegocio("Esta OS não possui pagamento registrado.")
            parcela = next((p for p in pagamento.parcelas if p.numero_parcela == numero_parcela), None)
            if parcela is None:
                raise ErroNegocio("Parcela não encontrada.")
            if parcela.status == "pago":
                raise ErroNegocio("Esta parcela já foi paga.")
            self._pagamentos.marcar_parcela_paga(cur, pagamento.id_pagamento, numero_parcela, date.today())

    # Auxiliares 
    def _exigir_os_aberta(self, cur, id_os: int) -> OrdemServico:
        os = self._os.buscar_por_id(cur, id_os)
        if os is None:
            raise ErroNegocio("Ordem de serviço não encontrada.")
        if os.fechada:
            raise ErroNegocio(f"A OS está {os.status} e não aceita alterações.")
        return os
