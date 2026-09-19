from fastapi import APIRouter

from app.api.deps import Db, get_active
from app.domain.models import ModelConfig, Persona
from app.domain.schemas import SettingsRead, SettingsUpdate
from app.repositories.settings import SettingsRepository

router = APIRouter(prefix="/settings", tags=["settings"])


def serialize(repo: SettingsRepository) -> SettingsRead:
    values = repo.get_all()
    return SettingsRead(
        app_name=values["app_name"],
        user_display_name=values["user_display_name"],
        theme=values["theme"],
        active_persona_id=int(values["active_persona_id"]),
        active_model_config_id=int(values["active_model_config_id"]),
        global_persona_rules=values["global_persona_rules"],
        fashion_enabled=values.get("fashion_enabled", "false").lower() == "true",
    )


@router.get("", response_model=SettingsRead)
def get_settings(db: Db):
    repo = SettingsRepository(db)
    repo.seed_defaults()
    return serialize(repo)


@router.patch("", response_model=SettingsRead)
def update_settings(payload: SettingsUpdate, db: Db):
    data = payload.model_dump(exclude_none=True)
    if "active_persona_id" in data:
        get_active(db, Persona, data["active_persona_id"], "Persona")
    if "active_model_config_id" in data:
        get_active(db, ModelConfig, data["active_model_config_id"], "Modelo")
    repo = SettingsRepository(db)
    repo.set_many({key: str(value) for key, value in data.items()})
    return serialize(repo)
