from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BASE_DIR.parent
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# BFF_DATABASE_URL existe para apontar testes e migrações para um banco
# descartável. NÃO é configuração de produto: modelo, persona e parâmetros
# continuam vivendo no SQLite, e o .env segue guardando só a chave-mestra.
DATABASE_URL = os.getenv("BFF_DATABASE_URL") or f"sqlite:///{(DATA_DIR / 'bff_ai.db').as_posix()}"
APP_MASTER_KEY = os.getenv("APP_MASTER_KEY", "")
