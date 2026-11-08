"""Configuração da conexão com o PostgreSQL

Ordem de prioridade: variáveis de ambiente > arquivo .env (na raiz do projeto) > padrões abaixo.
Para trocar host, porta, banco, usuário ou senha, edite o arquivo .env (copie de .env.example).
"""
import os
from pathlib import Path


def _carregar_env() -> None:
    arquivo = Path(__file__).resolve().parent.parent / ".env"
    if not arquivo.exists():
        return
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


_carregar_env()


class Config:
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", "5432"))
    DB_NAME = os.environ.get("DB_NAME", "oficina")
    DB_USER = os.environ.get("DB_USER", "postgres")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-oficina-mecanica")
