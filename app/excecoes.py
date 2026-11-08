"""Exceções compartilhadas pelas três camadas"""


class ErroAplicacao(Exception):
    """Base de todos os erros esperados da aplicação (mostrados ao usuário)."""


class ErroNegocio(ErroAplicacao):
    """Violação de regra de negócio ou dado inválido detectado na camada de negócio."""


class ErroBanco(ErroAplicacao):
    """Erro vindo do banco (restrições, gatilhos). A mensagem já vem traduzida."""
