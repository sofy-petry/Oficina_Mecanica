"""Entidades de domínio (camada de modelo), compartilhadas pelas três camadas

Cada entidade é uma dataclass. Campos "de exibição" (ex.: nome_cliente) são
preenchidos apenas por consultas que fazem JOIN
"""
from dataclasses import dataclass, field, fields
from datetime import date, time
from decimal import Decimal
from typing import Optional


class Entidade:
    @classmethod
    def de_linha(cls, linha: dict):
        """Cria a entidade a partir de uma linha do banco (dict), ignorando colunas extras."""
        nomes = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in linha.items() if k in nomes})


@dataclass
class Cliente(Entidade):
    nome: str
    endereco: str
    tipo_cliente: str  # 'F' (pessoa física) ou 'J' (pessoa jurídica)
    documento: Optional[str] = None  # CPF ou CNPJ, conforme o tipo
    email: Optional[str] = None
    telefones: list = field(default_factory=list)
    qtd_veiculos: Optional[int] = None  # exibição
    id_cliente: Optional[int] = None

    @property
    def tipo_descricao(self) -> str:
        return "Pessoa Física" if self.tipo_cliente == "F" else "Pessoa Jurídica"

    @property
    def rotulo_documento(self) -> str:
        return "CPF" if self.tipo_cliente == "F" else "CNPJ"


@dataclass
class Veiculo(Entidade):
    placa: str
    marca: str
    modelo: str
    ano_fabricacao: int
    numero_chassi: str
    quilometragem_atual: int
    id_cliente: int
    cor: Optional[str] = None
    observacoes: Optional[str] = None
    id_veiculo: Optional[int] = None
    nome_cliente: Optional[str] = None  # exibição


@dataclass
class Mecanico(Entidade):
    nome: str
    cpf: str
    dta_admissao: date
    especialidade: str
    percentual_comissao: Decimal = Decimal("0")
    id_mecanico: Optional[int] = None
    os_abertas: Optional[int] = None  # exibição


@dataclass
class Servico(Entidade):
    codigo: str
    descricao: str
    tempo_medio_execucao: int  # minutos
    valor_mao_obra: Decimal
    categoria: str
    periodo_garantia: Optional[int] = 90  # dias
    id_servico: Optional[int] = None


@dataclass
class Peca(Entidade):
    codigo: str
    descricao: str
    fabricante: str
    qtd_estoque: int
    qtd_minimo: int
    preco_custo: Decimal
    preco_venda: Decimal
    cod_fabricante: Optional[str] = None
    periodo_garantia: Optional[int] = 90  # dias
    marcas: list = field(default_factory=list)
    modelos: list = field(default_factory=list)
    id_peca: Optional[int] = None

    @property
    def estoque_baixo(self) -> bool:
        return self.qtd_estoque <= self.qtd_minimo

    @property
    def pct_estoque(self) -> int:
        """Nível do estoque (0-100) tomando como cheio o triplo do mínimo."""
        return min(100, round(self.qtd_estoque / max(self.qtd_minimo * 3, 1) * 100))


@dataclass
class OrdemServico(Entidade):
    numero_sequencial: str
    quilometragem_entrada: int
    descricao_problema: str
    id_veiculo: int
    status: str = "aguardando peças"
    dta_entrada: Optional[date] = None
    hra_entrada: Optional[time] = None
    dta_previsao_conclusao: Optional[date] = None
    dta_saida: Optional[date] = None
    hra_saida: Optional[time] = None
    subtotal_pecas: Decimal = Decimal("0")
    subtotal_mao_obra: Decimal = Decimal("0")
    desconto: Decimal = Decimal("0")
    valor_total: Decimal = Decimal("0")
    id_mecanico_responsavel: Optional[int] = None
    id_ordem_servico: Optional[int] = None
    # exibição
    placa: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    nome_cliente: Optional[str] = None
    nome_mecanico: Optional[str] = None

    STATUS_VALIDOS = (
        "aguardando peças", "em execução", "aguardando aprovação",
        "concluída", "entregue", "cancelada",
    )
    STATUS_FECHADOS = ("concluída", "entregue", "cancelada")

    STATUS_ABERTOS = ("aguardando aprovação", "aguardando peças", "em execução")

    @property
    def fechada(self) -> bool:
        """OS fechada não aceita mais serviços/peças (regra também garantida por gatilho)."""
        return self.status in self.STATUS_FECHADOS

    @property
    def em_andamento(self) -> bool:
        return self.status in self.STATUS_ABERTOS


@dataclass
class ServicoOS(Entidade):
    quantidade: int
    valor_cobrado: Decimal
    id_ordem_servico: int
    id_servico: int
    em_garantia: bool = False
    id_mecanico: Optional[int] = None
    id_servico_os: Optional[int] = None
    # exibição
    codigo: Optional[str] = None
    descricao: Optional[str] = None
    nome_mecanico: Optional[str] = None

    @property
    def total(self) -> Decimal:
        return Decimal("0") if self.em_garantia else self.valor_cobrado * self.quantidade


@dataclass
class ItemPecaOS(Entidade):
    qtd_utilizada: int
    valor_unitario: Decimal
    id_ordem_servico: int
    id_peca: int
    em_garantia: bool = False
    valor_total: Decimal = Decimal("0")
    id_item_peca_os: Optional[int] = None
    # exibição
    codigo: Optional[str] = None
    descricao: Optional[str] = None


@dataclass
class Parcela(Entidade):
    id_pagamento: int
    numero_parcela: int
    valor_parcela: Decimal
    dta_vencimento: date
    status: str
    dta_pagamento: Optional[date] = None


@dataclass
class Pagamento(Entidade):
    codigo: str
    forma_pagamento: str
    valor_total: Decimal
    numero_parcelas: int
    id_ordem_servico: int
    id_pagamento: Optional[int] = None
    parcelas: list = field(default_factory=list)


@dataclass
class Fornecedor(Entidade):
    cnpj: str
    razao_social: str
    telefone: str
    endereco: str
    email: Optional[str] = None
    condicao_pagamento: Optional[str] = None
    id_fornecedor: Optional[int] = None


@dataclass
class Fornecimento(Entidade):
    """Peça que um fornecedor vende (Fornecimento: preço praticado e prazo)."""
    id_fornecedor: int
    id_peca: int
    preco_praticado: Decimal
    prazo_entrega: int  # dias
    razao_social: Optional[str] = None  # exibição
    codigo: Optional[str] = None
    descricao: Optional[str] = None
    qtd_estoque: Optional[int] = None


@dataclass
class PedidoPeca(Entidade):
    codigo_pedido: str
    data_pedido: date
    status: str
    valor_total: Decimal
    id_fornecedor: int
    previsao_entrega: Optional[date] = None
    id_ordem_servico: Optional[int] = None
    id_pedido_peca: Optional[int] = None
    razao_social: Optional[str] = None  # exibição
    numero_os: Optional[str] = None
    qtd_itens: Optional[int] = None

    STATUS_VALIDOS = ("pendente", "em trânsito", "entregue", "cancelado")
    # transições permitidas (entregue e cancelado são finais)
    TRANSICOES = {
        "pendente": ("em trânsito", "entregue", "cancelado"),
        "em trânsito": ("entregue", "cancelado"),
        "entregue": (),
        "cancelado": (),
    }

    @property
    def em_aberto(self) -> bool:
        return self.status in ("pendente", "em trânsito")


@dataclass
class ItemPedido(Entidade):
    quantidade: int
    valor_unitario: Decimal
    valor_total: Decimal
    id_pedido_peca: int
    id_peca: int
    id_item_pedido: Optional[int] = None
    codigo: Optional[str] = None  # exibição
    descricao: Optional[str] = None


@dataclass
class Movimentacao(Entidade):
    codigo: str
    data_movimentacao: date
    hora_movimentacao: time
    tipo: str  # ENTRADA / SAIDA
    quantidade: int
    id_peca: int
    id_movimentacao_estoque: Optional[int] = None
    peca_codigo: Optional[str] = None  # exibição
    peca_descricao: Optional[str] = None
    origem: Optional[str] = None
    id_pedido_origem: Optional[int] = None
    id_os_origem: Optional[int] = None
