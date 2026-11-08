"""Filtros Jinja e variáveis globais de template (formatação em pt-BR)"""
import unicodedata
from datetime import date
from decimal import Decimal

DIAS_SEMANA = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]


def moeda(valor) -> str:
    if valor is None:
        return "—"
    texto = f"{Decimal(valor):,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def numero(valor) -> str:
    """1234567 -> '1.234.567' (usado em quilometragem e quantidades grandes)."""
    return "—" if valor is None else f"{int(valor):,}".replace(",", ".")


def data_br(valor) -> str:
    return valor.strftime("%d/%m/%Y") if valor else "—"


def hora_br(valor) -> str:
    return valor.strftime("%H:%M") if valor else "—"


def data_extenso(valor) -> str:
    return f"{DIAS_SEMANA[valor.weekday()]}, {valor.day} de {MESES[valor.month - 1]} de {valor.year}"


def relativo(valor) -> str:
    """Data como texto relativo a hoje: 'hoje', 'amanhã', 'em 3 dias', 'há 2 dias'."""
    if not valor:
        return ""
    d = (valor - date.today()).days
    if d == 0:
        return "hoje"
    if d == 1:
        return "amanhã"
    if d == -1:
        return "ontem"
    return f"em {d} dias" if d > 0 else f"há {-d} dias"


def iniciais(nome) -> str:
    partes = [p for p in str(nome or "").split() if p[:1].isalpha()]
    if not partes:
        return "?"
    return (partes[0][0] + (partes[-1][0] if len(partes) > 1 else "")).upper()


def slug(valor) -> str:
    """'aguardando peças' -> 'aguardando-pecas' (usado em classes CSS)."""
    sem_acento = unicodedata.normalize("NFKD", str(valor or "")).encode("ascii", "ignore").decode()
    return sem_acento.lower().replace(" ", "-")


def registrar_filtros(app) -> None:
    app.jinja_env.filters.update(moeda=moeda, numero=numero, data_br=data_br, hora_br=hora_br,
                                 data_extenso=data_extenso, relativo=relativo, iniciais=iniciais, slug=slug)

    # global (e não só variável de contexto) para ficar visível dentro dos macros
    app.jinja_env.globals["hoje"] = date.today()

    @app.context_processor
    def globais():
        return {"hoje": date.today()}
