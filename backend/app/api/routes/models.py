from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import joinedload

from app.api.deps import Db
from app.domain.models import Conversation, ModelConfig, ProviderConfig
from app.domain.schemas import ModelCreate, ModelRead, ModelUpdate
from app.repositories.settings import SettingsRepository
from app.services.llm.runtime import effective_max_tokens

router = APIRouter(prefix="/models", tags=["models"])


def view(model: ModelConfig) -> ModelRead:
    return ModelRead(
        id=model.id,
        provider_id=model.provider_id,
        provider_name=model.provider.name,
        provider_kind=model.provider.kind,
        display_name=model.display_name,
        model_id=model.model_id,
        temperature=model.temperature,
        # A regra de max_tokens vem das capacidades do adapter, não de um
        # `if kind == "nvidia_nim"` duplicado aqui.
        max_tokens=effective_max_tokens(model.provider.kind, model.max_tokens),
        top_p=model.top_p,
    )


@router.get("", response_model=list[ModelRead])
def list_models(db: Db):
    rows = db.query(ModelConfig).options(joinedload(ModelConfig.provider)).order_by(ModelConfig.id.asc()).all()
    return [view(row) for row in rows]


@router.post("", response_model=ModelRead, status_code=201)
def create_model(payload: ModelCreate, db: Db):
    if not db.get(ProviderConfig, payload.provider_id):
        raise HTTPException(404, "Provider not found")
    row = ModelConfig(
        provider_id=payload.provider_id,
        display_name=payload.display_name,
        model_id=payload.model_id,
        temperature_milli=round(payload.temperature * 1000),
        # SQLite keeps 0 as the internal sentinel for provider-managed limits.
        max_tokens=payload.max_tokens or 0,
        top_p_milli=round(payload.top_p * 1000),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    row = db.query(ModelConfig).options(joinedload(ModelConfig.provider)).filter_by(id=row.id).one()
    return view(row)


@router.patch("/{model_id}", response_model=ModelRead)
def update_model(model_id: int, payload: ModelUpdate, db: Db):
    row = db.get(ModelConfig, model_id)
    if not row:
        raise HTTPException(404, "Model config not found")
    data = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "max_tokens" in payload.model_fields_set and payload.max_tokens is None:
        data["max_tokens"] = None
    if "temperature" in data:
        row.temperature_milli = round(data.pop("temperature") * 1000)
    if "top_p" in data:
        row.top_p_milli = round(data.pop("top_p") * 1000)
    if "max_tokens" in data:
        data["max_tokens"] = data["max_tokens"] or 0
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    row = db.query(ModelConfig).options(joinedload(ModelConfig.provider)).filter_by(id=row.id).one()
    return view(row)


@router.post("/{model_id}/activate", response_model=ModelRead)
def activate_model(model_id: int, db: Db):
    row = db.query(ModelConfig).options(joinedload(ModelConfig.provider)).filter_by(id=model_id).one_or_none()
    if not row:
        raise HTTPException(404, "Model config not found")
    SettingsRepository(db).set_many({"active_model_config_id": str(model_id)})
    return view(row)


@router.delete("/{model_id}", status_code=204)
def delete_model(model_id: int, db: Db):
    row = db.get(ModelConfig, model_id)
    if not row:
        raise HTTPException(404, "Model config not found")
    if db.query(Conversation).filter(Conversation.model_config_id == model_id).count():
        raise HTTPException(409, "Model config is used by conversations")
    db.delete(row)
    db.commit()
