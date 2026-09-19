from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import joinedload

from app.api.deps import Db, get_active
from app.domain.models import ModelConfig, ProviderConfig
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
        context_window=model.context_window,
    )


@router.get("", response_model=list[ModelRead])
def list_models(db: Db):
    rows = (
        db.query(ModelConfig)
        .options(joinedload(ModelConfig.provider))
        .filter(ModelConfig.is_archived.is_(False))
        .order_by(ModelConfig.id.asc())
        .all()
    )
    return [view(row) for row in rows]


@router.post("", response_model=ModelRead, status_code=201)
def create_model(payload: ModelCreate, db: Db):
    get_active(db, ProviderConfig, payload.provider_id, "Provider")
    existente = db.query(ModelConfig).filter_by(provider_id=payload.provider_id, model_id=payload.model_id).one_or_none()
    if existente and not existente.is_archived:
        # Antes estourava IntegrityError (500) ao clicar duas vezes no mesmo modelo.
        raise HTTPException(409, "Esse modelo já está configurado")

    # Modelo excluído (soft delete) volta em vez de criar linha nova: a UNIQUE
    # (provider, model_id) impediria, e conversas antigas continuam apontando
    # para a mesma linha.
    row = existente or ModelConfig(provider_id=payload.provider_id, model_id=payload.model_id)
    row.display_name = payload.display_name
    row.temperature_milli = round(payload.temperature * 1000)
    row.max_tokens = payload.max_tokens
    row.top_p_milli = round(payload.top_p * 1000)
    row.context_window = payload.context_window
    row.is_archived = False
    if not existente:
        db.add(row)
    db.commit()
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
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    row = db.query(ModelConfig).options(joinedload(ModelConfig.provider)).filter_by(id=row.id).one()
    return view(row)


@router.post("/{model_id}/activate", response_model=ModelRead)
def activate_model(model_id: int, db: Db):
    get_active(db, ModelConfig, model_id, "Modelo")
    row = db.query(ModelConfig).options(joinedload(ModelConfig.provider)).filter_by(id=model_id).one()
    SettingsRepository(db).set_many({"active_model_config_id": str(model_id)})
    return view(row)


@router.delete("/{model_id}", status_code=204)
def archive_model(model_id: int, db: Db):
    """Soft delete: some da lista, mas a linha fica.

    As conversas registram qual modelo usaram; apagar de verdade quebraria esse
    histórico ou exigiria recusar a exclusão para sempre.
    """
    row = db.get(ModelConfig, model_id)
    if not row:
        raise HTTPException(404, "Model config not found")

    ativo = SettingsRepository(db).get_all().get("active_model_config_id")
    if ativo and int(ativo) == model_id:
        substituto = (
            db.query(ModelConfig)
            .filter(ModelConfig.is_archived.is_(False), ModelConfig.id != model_id)
            .order_by(ModelConfig.id.asc())
            .first()
        )
        if not substituto:
            raise HTTPException(409, "Não dá para arquivar o único modelo disponível")
        SettingsRepository(db).set_many({"active_model_config_id": str(substituto.id)})

    row.is_archived = True
    db.commit()
