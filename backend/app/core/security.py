from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
from app.core.config import APP_MASTER_KEY


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
            raise RuntimeError("APP_MASTER_KEY is required before saving provider secrets.")
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str | None) -> str | None:
        if not value:
            return None
        if not self._fernet:
            raise RuntimeError("APP_MASTER_KEY is required before reading provider secrets.")
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            raise RuntimeError("The configured APP_MASTER_KEY cannot decrypt stored secrets.") from exc
