"""Camada de apresentação: rotas Flask (controladores web).

Esta camada só conhece os services (camada de negócio). Nunca acessa DAO ou SQL
"""
from types import SimpleNamespace

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from app.excecoes import ErroAplicacao

bp = Blueprint("oficina", __name__)


def svc():
    return current_app.extensions["servicos"]


def _erro(e: ErroAplicacao) -> None:
    flash(str(e), "erro")


def _consultar(funcao, padrao):
    """Executa uma consulta; em caso de erro, avisa o usuário e devolve um valor padrão."""
    try:
        return funcao()
    except ErroAplicacao as e:
        _erro(e)
        return padrao


def _acao(destino_ok, acao, mensagem_ok):
    """Executa uma ação de escrita, avisa o resultado e redireciona."""
    try:
        acao()
        flash(mensagem_ok, "ok")
    except ErroAplicacao as e:
        _erro(e)
    return redirect(destino_ok)


# Painel
@bp.route("/")
def index():
    painel = _consultar(svc().painel.painel, None)
    return render_template("index.html", painel=painel)


# Clientes
@bp.route("/clientes")
def clientes():
    busca = request.args.get("busca", "").strip()
    return render_template("clientes.html", clientes=_consultar(lambda: svc().clientes.listar(busca), []),
                           busca=busca)


@bp.route("/clientes/novo", methods=["GET", "POST"])
def cliente_novo():
    if request.method == "POST":
        try:
            id_cliente = svc().clientes.cadastrar(request.form)
            flash("Cliente cadastrado com sucesso.", "ok")
            return redirect(url_for("oficina.cliente_detalhe", id_cliente=id_cliente))
        except ErroAplicacao as e:
            _erro(e)
    return render_template("cliente_form.html", form=request.form)


@bp.route("/clientes/<int:id_cliente>")
def cliente_detalhe(id_cliente):
    try:
        cliente, veiculos, ordens = svc().clientes.detalhar(id_cliente)
    except ErroAplicacao as e:
        _erro(e)
        return redirect(url_for("oficina.clientes"))
    return render_template("cliente_detalhe.html", cliente=cliente, veiculos=veiculos, ordens=ordens)


#  Veículos
@bp.route("/veiculos")
def veiculos():
    busca = request.args.get("busca", "").strip()
    return render_template("veiculos.html", veiculos=_consultar(lambda: svc().veiculos.listar(busca), []),
                           busca=busca)


@bp.route("/veiculos/novo", methods=["GET", "POST"])
def veiculo_novo():
    if request.method == "POST":
        try:
            id_veiculo = svc().veiculos.cadastrar(request.form)
            flash("Veículo cadastrado com sucesso.", "ok")
            return redirect(url_for("oficina.veiculo_detalhe", id_veiculo=id_veiculo))
        except ErroAplicacao as e:
            _erro(e)
    clientes_sel = _consultar(svc().veiculos.clientes_para_selecao, [])
    form = request.form if request.method == "POST" else {"id_cliente": request.args.get("id_cliente", "")}
    opcoes = [(c.id_cliente, f"{c.nome} ({c.documento})") for c in clientes_sel]
    return render_template("veiculo_form.html", form=form, clientes_opcoes=opcoes)


@bp.route("/veiculos/<int:id_veiculo>")
def veiculo_detalhe(id_veiculo):
    try:
        veiculo, ordens = svc().veiculos.detalhar(id_veiculo)
    except ErroAplicacao as e:
        _erro(e)
        return redirect(url_for("oficina.veiculos"))
    return render_template("veiculo_detalhe.html", v=veiculo, ordens=ordens)


# Mecânicos
@bp.route("/mecanicos")
def mecanicos():
    busca = request.args.get("busca", "").strip()
    return render_template("mecanicos.html", mecanicos=_consultar(lambda: svc().mecanicos.listar(busca), []),
                           busca=busca)


@bp.route("/mecanicos/novo", methods=["GET", "POST"])
def mecanico_novo():
    if request.method == "POST":
        try:
            id_mecanico = svc().mecanicos.cadastrar(request.form)
            flash("Mecânico cadastrado com sucesso.", "ok")
            return redirect(url_for("oficina.mecanico_detalhe", id_mecanico=id_mecanico))
        except ErroAplicacao as e:
            _erro(e)
    opcoes = [(e, e) for e in svc().mecanicos.ESPECIALIDADES]
    return render_template("mecanico_form.html", form=request.form, especialidades_opcoes=opcoes)


@bp.route("/mecanicos/<int:id_mecanico>")
def mecanico_detalhe(id_mecanico):
    try:
        d = svc().mecanicos.detalhar(id_mecanico)
    except ErroAplicacao as e:
        _erro(e)
        return redirect(url_for("oficina.mecanicos"))
    return render_template("mecanico_detalhe.html", d=d)


# Serviços
@bp.route("/servicos")
def servicos():
    busca = request.args.get("busca", "").strip()
    return render_template("servicos.html", servicos=_consultar(lambda: svc().servicos.listar(busca), []),
                           busca=busca)


@bp.route("/servicos/novo", methods=["GET", "POST"])
def servico_novo():
    if request.method == "POST":
        try:
            svc().servicos.cadastrar(request.form)
            flash("Serviço cadastrado com sucesso.", "ok")
            return redirect(url_for("oficina.servicos"))
        except ErroAplicacao as e:
            _erro(e)
    return render_template("servico_form.html", form=request.form)


# Peças
@bp.route("/pecas")
def pecas():
    busca = request.args.get("busca", "").strip()
    so_baixo = request.args.get("estoque_baixo") == "1"
    lista = _consultar(lambda: svc().pecas.listar(busca, so_baixo), [])
    return render_template("pecas.html", pecas=lista, busca=busca, so_baixo=so_baixo)


@bp.route("/pecas/novo", methods=["GET", "POST"])
def peca_nova():
    if request.method == "POST":
        try:
            id_peca = svc().pecas.cadastrar(request.form)
            flash("Peça cadastrada com sucesso.", "ok")
            return redirect(url_for("oficina.peca_detalhe", id_peca=id_peca))
        except ErroAplicacao as e:
            _erro(e)
    return render_template("peca_form.html", form=request.form)


@bp.route("/pecas/<int:id_peca>")
def peca_detalhe(id_peca):
    try:
        d = svc().pecas.detalhar(id_peca)
    except ErroAplicacao as e:
        _erro(e)
        return redirect(url_for("oficina.pecas"))
    return render_template("peca_detalhe.html", d=d)


@bp.route("/movimentacoes")
def movimentacoes():
    tipo = request.args.get("tipo", "").strip()
    busca = request.args.get("busca", "").strip()
    lista = _consultar(lambda: svc().pecas.movimentacoes(tipo or None, busca or None), [])
    return render_template("movimentacoes.html", movs=lista, tipo=tipo, busca=busca)


# Fornecedores
@bp.route("/fornecedores")
def fornecedores():
    busca = request.args.get("busca", "").strip()
    lista = _consultar(lambda: svc().fornecedores.listar(busca), [])
    return render_template("fornecedores.html", fornecedores=lista, busca=busca)


@bp.route("/fornecedores/novo", methods=["GET", "POST"])
def fornecedor_novo():
    if request.method == "POST":
        try:
            id_fornecedor = svc().fornecedores.cadastrar(request.form)
            flash("Fornecedor cadastrado com sucesso.", "ok")
            return redirect(url_for("oficina.fornecedor_detalhe", id_fornecedor=id_fornecedor))
        except ErroAplicacao as e:
            _erro(e)
    return render_template("fornecedor_form.html", form=request.form)


@bp.route("/fornecedores/<int:id_fornecedor>")
def fornecedor_detalhe(id_fornecedor):
    try:
        d = svc().fornecedores.detalhar(id_fornecedor)
    except ErroAplicacao as e:
        _erro(e)
        return redirect(url_for("oficina.fornecedores"))
    return render_template("fornecedor_detalhe.html", d=d)


@bp.post("/fornecedores/<int:id_fornecedor>/pecas")
def fornecedor_vincular_peca(id_fornecedor):
    return _acao(url_for("oficina.fornecedor_detalhe", id_fornecedor=id_fornecedor),
                 lambda: svc().fornecedores.vincular_peca(id_fornecedor, request.form),
                 "Peça vinculada ao fornecedor (preço e prazo salvos).")


# Pedidos
@bp.route("/pedidos")
def pedidos():
    status = request.args.get("status", "").strip()
    busca = request.args.get("busca", "").strip()
    lista = _consultar(lambda: svc().pedidos.listar(status or None, busca or None), [])
    contagem = _consultar(svc().pedidos.contagem_por_status, {})
    return render_template("pedidos.html", pedidos=lista, status=status, busca=busca, contagem=contagem,
                           total=sum(contagem.values()), status_validos=svc().pedidos.STATUS)


@bp.route("/pedidos/novo", methods=["GET", "POST"])
def pedido_novo():
    if request.method == "POST":
        try:
            id_pedido = svc().pedidos.criar(request.form)
            flash("Pedido registrado e enviado ao fornecedor.", "ok")
            return redirect(url_for("oficina.pedido_detalhe", id_pedido=id_pedido))
        except ErroAplicacao as e:
            _erro(e)
        origem = request.form
    else:
        origem = request.args
    id_fornecedor = origem.get("id_fornecedor", type=int)
    try:
        dados = svc().pedidos.dados_para_novo(id_fornecedor)
    except ErroAplicacao as e:
        _erro(e)
        return redirect(url_for("oficina.pedidos"))
    return render_template("pedido_form.html", d=dados, form=origem)


@bp.route("/pedidos/<int:id_pedido>")
def pedido_detalhe(id_pedido):
    try:
        d = svc().pedidos.detalhar(id_pedido)
    except ErroAplicacao as e:
        _erro(e)
        return redirect(url_for("oficina.pedidos"))
    return render_template("pedido_detalhe.html", d=d)


@bp.post("/pedidos/<int:id_pedido>/status")
def pedido_status(id_pedido):
    novo = request.form.get("status", "")
    mensagem = ("Pedido recebido: as peças entraram no estoque." if novo == "entregue"
                else "Status do pedido atualizado.")
    return _acao(url_for("oficina.pedido_detalhe", id_pedido=id_pedido),
                 lambda: svc().pedidos.alterar_status(id_pedido, novo), mensagem)


# Ordens de serviço
@bp.route("/os")
def ordens():
    status = request.args.get("status", "").strip()
    busca = request.args.get("busca", "").strip()
    lista = _consultar(lambda: svc().ordens.listar(status or None, busca or None), [])
    contagem = _consultar(svc().ordens.contagem_por_status, {})
    return render_template("os_lista.html", ordens=lista, status=status, busca=busca, contagem=contagem,
                           total=sum(contagem.values()), status_validos=svc().ordens.STATUS)


@bp.route("/os/nova", methods=["GET", "POST"])
def os_nova():
    if request.method == "POST":
        try:
            id_os = svc().ordens.abrir(request.form)
            flash("Ordem de serviço aberta.", "ok")
            return redirect(url_for("oficina.os_detalhe", id_os=id_os))
        except ErroAplicacao as e:
            _erro(e)
    try:
        opcoes = svc().ordens.dados_para_abertura()
    except ErroAplicacao as e:
        _erro(e)
        return redirect(url_for("oficina.ordens"))
    form = request.form if request.method == "POST" else {"id_veiculo": request.args.get("id_veiculo", "")}
    return render_template(
        "os_form.html", form=form, veiculos=opcoes.veiculos,
        mecanicos_opcoes=[(m.id_mecanico, f"{m.nome} ({m.especialidade})") for m in opcoes.mecanicos],
    )


@bp.route("/os/<int:id_os>")
def os_detalhe(id_os):
    try:
        detalhe = svc().ordens.detalhar(id_os)
        opcoes = svc().ordens.dados_para_lancamento() if not detalhe.os.fechada else None
    except ErroAplicacao as e:
        _erro(e)
        return redirect(url_for("oficina.ordens"))
    return render_template("os_detalhe.html", d=detalhe, opcoes=opcoes,
                           status_validos=svc().ordens.STATUS, formas=svc().ordens.FORMAS_PAGAMENTO)


def _acao_os(id_os, acao, mensagem_ok):
    return _acao(url_for("oficina.os_detalhe", id_os=id_os), acao, mensagem_ok)


@bp.post("/os/<int:id_os>/servico")
def os_add_servico(id_os):
    return _acao_os(id_os, lambda: svc().ordens.adicionar_servico(id_os, request.form),
                    "Serviço lançado na OS.")


@bp.post("/os/<int:id_os>/peca")
def os_add_peca(id_os):
    return _acao_os(id_os, lambda: svc().ordens.adicionar_peca(id_os, request.form),
                    "Peça lançada na OS (estoque atualizado).")


@bp.post("/os/<int:id_os>/servico/<int:id_servico_os>/remover")
def os_del_servico(id_os, id_servico_os):
    return _acao_os(id_os, lambda: svc().ordens.remover_servico(id_os, id_servico_os),
                    "Serviço removido da OS.")


@bp.post("/os/<int:id_os>/peca/<int:id_item>/remover")
def os_del_peca(id_os, id_item):
    return _acao_os(id_os, lambda: svc().ordens.remover_peca(id_os, id_item),
                    "Peça removida da OS (devolvida ao estoque).")


@bp.post("/os/<int:id_os>/status")
def os_status(id_os):
    return _acao_os(id_os, lambda: svc().ordens.alterar_status(id_os, request.form.get("status", "")),
                    "Status atualizado.")


@bp.post("/os/<int:id_os>/desconto")
def os_desconto(id_os):
    return _acao_os(id_os, lambda: svc().ordens.aplicar_desconto(id_os, request.form),
                    "Desconto aplicado.")


@bp.post("/os/<int:id_os>/pagamento")
def os_pagamento(id_os):
    return _acao_os(id_os, lambda: svc().ordens.registrar_pagamento(id_os, request.form),
                    "Pagamento registrado e parcelas geradas.")


@bp.post("/os/<int:id_os>/parcela/<int:numero>/pagar")
def os_pagar_parcela(id_os, numero):
    return _acao_os(id_os, lambda: svc().ordens.pagar_parcela(id_os, numero),
                    f"Parcela {numero} marcada como paga.")
