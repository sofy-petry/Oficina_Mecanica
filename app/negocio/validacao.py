"""Funções de validação e conversão de dados de entrada (strings vindas do formulário)"""
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.excecoes import ErroNegocio


def texto(valor, campo: str, obrigatorio: bool = True, max_len: Optional[int] = None) -> Optional[str]:
    valor = (valor or "").strip()
    if not valor:
        if obrigatorio:
            raise ErroNegocio(f"O campo '{campo}' é obrigatório.")
        return None
    if max_len and len(valor) > max_len:
        raise ErroNegocio(f"O campo '{campo}' aceita no máximo {max_len} caracteres.")
    return valor


def inteiro(valor, campo: str, minimo: Optional[int] = None, maximo: Optional[int] = None,
            obrigatorio: bool = True) -> Optional[int]:
    valor = str(valor or "").strip()
    if not valor:
        if obrigatorio:
            raise ErroNegocio(f"O campo '{campo}' é obrigatório.")
        return None
    try:
        numero = int(valor)
    except ValueError:
        raise ErroNegocio(f"O campo '{campo}' deve ser um número inteiro.") from None
    if minimo is not None and numero < minimo:
        raise ErroNegocio(f"O campo '{campo}' deve ser no mínimo {minimo}.")
    if maximo is not None and numero > maximo:
        raise ErroNegocio(f"O campo '{campo}' deve ser no máximo {maximo}.")
    return numero


def decimal(valor, campo: str, minimo: Optional[Decimal] = None, maximo: Optional[Decimal] = None,
            obrigatorio: bool = True) -> Optional[Decimal]:
    """Aceita '1234.56', '1234,56' e '1.234,56'."""
    valor = str(valor or "").strip()
    if not valor:
        if obrigatorio:
            raise ErroNegocio(f"O campo '{campo}' é obrigatório.")
        return None
    if "," in valor:
        valor = valor.replace(".", "").replace(",", ".")
    try:
        numero = Decimal(valor).quantize(Decimal("0.01"))
    except InvalidOperation:
        raise ErroNegocio(f"O campo '{campo}' deve ser um valor numérico.") from None
    if minimo is not None and numero < minimo:
        raise ErroNegocio(f"O campo '{campo}' deve ser no mínimo {minimo}.")
    if maximo is not None and numero > maximo:
        raise ErroNegocio(f"O campo '{campo}' deve ser no máximo {maximo}.")
    return numero


def data(valor, campo: str, obrigatorio: bool = True) -> Optional[date]:
    """Converte 'AAAA-MM-DD' (formato de <input type="date">)."""
    valor = (valor or "").strip()
    if not valor:
        if obrigatorio:
            raise ErroNegocio(f"O campo '{campo}' é obrigatório.")
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        raise ErroNegocio(f"O campo '{campo}' deve ser uma data válida.") from None


def marcado(valor) -> bool:
    """Interpreta o valor de um checkbox HTML."""
    return str(valor or "").lower() in ("on", "1", "true", "sim")


def somente_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def formatar_cpf(valor: str) -> str:
    d = somente_digitos(valor)
    if len(d) != 11:
        raise ErroNegocio("CPF deve conter 11 dígitos.")
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


def formatar_cnpj(valor: str) -> str:
    d = somente_digitos(valor)
    if len(d) != 14:
        raise ErroNegocio("CNPJ deve conter 14 dígitos.")
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"


def lista_separada(valor: str) -> list[str]:
    """Quebra um texto separado por vírgula, ponto e vírgula ou quebra de linha, sem repetidos."""
    itens = [i.strip() for i in re.split(r"[,;\n]", valor or "") if i.strip()]
    return list(dict.fromkeys(itens))
