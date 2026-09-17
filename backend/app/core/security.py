from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from app.core.config import APP_MASTER_KEY


class MasterKeyError(RuntimeError):
    """APP_MASTER_KEY ausente ou incapaz de decifrar o que está no banco.

    Tipada para virar uma resposta explicável em vez de um 500 opaco: antes, uma
    chave trocada só falhava na hora de enviar a primeira mensagem.
    """

    code = "master_key"


class SecretCipher:
    def __init__(self, key: str | None = None) -> None:
        raw = (key or APP_MASTER_KEY).strip()
        self._fernet = Fernet(raw.encode()) if raw else None

    @property
    def enabled(self) -> bool:
        return self._fernet is not None

    def encrypt(self, value: str | None) -> str | None:
        if not value:
            return None
        if not self._fernet:
            raise MasterKeyError("APP_MASTER_KEY é obrigatória para salvar segredos de provider.")
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str | None) -> str | None:
        if not value:
            return None
        if not self._fernet:
            raise MasterKeyError("APP_MASTER_KEY é obrigatória para ler segredos de provider.")
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise MasterKeyError("A APP_MASTER_KEY configurada não decifra os segredos guardados no banco.") from exc
