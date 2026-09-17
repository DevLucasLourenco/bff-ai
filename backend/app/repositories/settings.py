from __future__ import annotations

from sqlalchemy.orm import Session
from app.domain.models import AppSetting

DEFAULT_SETTINGS = {
    "app_name": "BFF AI",
    "user_display_name": "Você",
    "assistant_display_name": "Bestie",
    "theme": "pink",
    "active_persona_id": "1",
    "active_model_config_id": "1",
}


class SettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def seed_defaults(self) -> None:
        for key, value in DEFAULT_SETTINGS.items():
            if self.db.get(AppSetting, key) is None:
                self.db.add(AppSetting(key=key, value=value))
        self.db.commit()

    def get(self, key: str) -> str:
        row = self.db.get(AppSetting, key)
        if not row:
            raise KeyError(key)
        return row.value

    def get_all(self) -> dict[str, str]:
        rows = self.db.query(AppSetting).all()
        return {row.key: row.value for row in rows}

    def set_many(self, values: dict[str, str]) -> None:
        for key, value in values.items():
            row = self.db.get(AppSetting, key)
            if row:
                row.value = value
            else:
                self.db.add(AppSetting(key=key, value=value))
        self.db.commit()
