"""Acesso ao PostgreSQL: conexão, transação e tradução de erros do banco."""
from contextlib import contextmanager

import psycopg2
from psycopg2 import errors
from psycopg2.extras import RealDictCursor

from app.excecoes import ErroBanco

# Mensagens amigáveis para restrições UNIQUE (nome da constraint -> mensagem)
_MSG_UNICO = {
    "cliente_fisico_cpf_key": "Já existe um cliente com este CPF.",
    "cliente_juridico_cnpj_key": "Já existe um cliente com este CNPJ.",
    "veiculo_placa_key": "Já existe um veículo com esta placa.",
    "veiculo_numero_chassi_key": "Já existe um veículo com este número de chassi.",
    "mecanico_cpf_key": "Já existe um mecânico com este CPF.",
    "servico_codigo_key": "Já existe um serviço com este código.",
    "peca_codigo_key": "Já existe uma peça com este código.",
    "uk_os_peca": "Esta peça já foi lançada nesta OS. Remova o lançamento atual para alterar a quantidade.",
    "pagamento_id_ordem_servico_key": "Esta OS já possui um pagamento registrado.",
    "pagamento_codigo_key": "Já existe um pagamento com este código.",
}


def traduzir_erro(e: psycopg2.Error) -> str:
    """Converte uma exceção do psycopg2 em mensagem legível para o usuário."""
    diag = e.diag
    if isinstance(e, errors.UniqueViolation):
        return _MSG_UNICO.get(diag.constraint_name, "Registro duplicado.")
    if isinstance(e, errors.RaiseException):
        # mensagens lançadas pelos gatilhos (RAISE EXCEPTION)
        return diag.message_primary
    if isinstance(e, errors.CheckViolation):
        return f"Valor inválido (restrição '{diag.constraint_name}' violada)."
    if isinstance(e, errors.ForeignKeyViolation):
        return "Operação não permitida: registro relacionado inexistente ou em uso."
    if isinstance(e, errors.NotNullViolation):
        return f"Campo obrigatório não informado: {diag.column_name}."
    return diag.message_primary or str(e)


class Banco:
    """Fornece cursores transacionais. Cada bloco `with banco.cursor()` é uma transação:
    commit ao sair normalmente, rollback se ocorrer qualquer exceção."""

    def __init__(self, config):
        self._params = dict(
            host=config.DB_HOST, port=config.DB_PORT, dbname=config.DB_NAME,
            user=config.DB_USER, password=config.DB_PASSWORD,
        )

    @contextmanager
    def cursor(self):
        conn = None
        try:
            conn = psycopg2.connect(**self._params)
            conn.set_client_encoding("UTF8")
            with conn:  # commit / rollback automático
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    yield cur
        except psycopg2.OperationalError as e:
            raise ErroBanco(
                "Não foi possível acessar o banco de dados. Verifique se o PostgreSQL "
                "está em execução e as variáveis DB_* estão corretas."
            ) from e
        except psycopg2.Error as e:
            raise ErroBanco(traduzir_erro(e)) from e
        finally:
            if conn is not None:
                conn.close()
