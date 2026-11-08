"""Sistema de Controle de Oficina Mecânica - aplicação em três camadas

    apresentacao  ->  negocio  ->  dados  ->  PostgreSQL
                         \\______ modelo (entidades) ______/
"""
from types import SimpleNamespace

from flask import Flask

from app.config import Config
from app.dados.conexao import Banco
from app.dados.cliente_dao import ClienteDAO
from app.dados.veiculo_dao import VeiculoDAO
from app.dados.mecanico_dao import MecanicoDAO
from app.dados.servico_dao import ServicoDAO
from app.dados.peca_dao import PecaDAO
from app.dados.ordem_servico_dao import OrdemServicoDAO
from app.dados.pagamento_dao import PagamentoDAO
from app.dados.fornecedor_dao import FornecedorDAO
from app.dados.pedido_dao import PedidoDAO
from app.dados.movimentacao_dao import MovimentacaoDAO
from app.dados.painel_dao import PainelDAO
from app.negocio.cliente_service import ClienteService
from app.negocio.veiculo_service import VeiculoService
from app.negocio.mecanico_service import MecanicoService
from app.negocio.servico_service import ServicoService
from app.negocio.peca_service import PecaService
from app.negocio.ordem_servico_service import OrdemServicoService
from app.negocio.fornecedor_service import FornecedorService
from app.negocio.pedido_service import PedidoService
from app.negocio.painel_service import PainelService


def montar_servicos(banco: Banco) -> SimpleNamespace:
    """Composition root: instancia DAOs e injeta nos services"""
    cliente_dao = ClienteDAO()
    veiculo_dao = VeiculoDAO()
    mecanico_dao = MecanicoDAO()
    servico_dao = ServicoDAO()
    peca_dao = PecaDAO()
    os_dao = OrdemServicoDAO()
    pagamento_dao = PagamentoDAO()
    fornecedor_dao = FornecedorDAO()
    pedido_dao = PedidoDAO()
    movimentacao_dao = MovimentacaoDAO()
    painel_dao = PainelDAO()

    return SimpleNamespace(
        clientes=ClienteService(banco, cliente_dao, veiculo_dao, os_dao),
        veiculos=VeiculoService(banco, veiculo_dao, cliente_dao, os_dao),
        mecanicos=MecanicoService(banco, mecanico_dao, os_dao),
        servicos=ServicoService(banco, servico_dao),
        pecas=PecaService(banco, peca_dao, fornecedor_dao, movimentacao_dao),
        fornecedores=FornecedorService(banco, fornecedor_dao, peca_dao, pedido_dao),
        pedidos=PedidoService(banco, pedido_dao, fornecedor_dao, os_dao),
        ordens=OrdemServicoService(
            banco, os_dao, veiculo_dao, mecanico_dao, servico_dao, peca_dao, pagamento_dao, pedido_dao
        ),
        painel=PainelService(banco, painel_dao, os_dao, peca_dao, pedido_dao),
    )


def create_app(config: Config | None = None) -> Flask:
    config = config or Config()
    app = Flask(__name__, template_folder="apresentacao/templates",
                static_folder="apresentacao/static")
    app.config["SECRET_KEY"] = config.SECRET_KEY

    banco = Banco(config)
    app.extensions["servicos"] = montar_servicos(banco)

    from app.apresentacao.rotas import bp
    from app.apresentacao.filtros import registrar_filtros

    app.register_blueprint(bp)
    registrar_filtros(app)
    return app
