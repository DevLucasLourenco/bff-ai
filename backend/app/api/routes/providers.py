from fastapi import APIRouter, HTTPException

from app.core.security import SecretCipher
from app.api.deps import Db
from app.domain.models import ProviderConfig
from app.domain.schemas import ProviderCreate, ProviderRead, ProviderUpdate
from app.services.llm.factory import create_adapter

router = APIRouter(prefix="/providers", tags=["providers"])


def view(provider: ProviderConfig) -> ProviderRead:
    return ProviderRead(
        id=provider.id,
        name=provider.name,
        kind=provider.kind,
        base_url=provider.base_url,
        has_api_key=bool(provider.api_key_encrypted),
        is_enabled=provider.is_enabled,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


@router.get("", response_model=list[ProviderRead])
def list_providers(db: Db):
    return [view(p) for p in db.query(ProviderConfig).order_by(ProviderConfig.id.asc()).all()]


@router.post("", response_model=ProviderRead, status_code=201)
def create_provider(payload: ProviderCreate, db: Db):
    cipher = SecretCipher()
    provider = ProviderConfig(
        name=payload.name,
        kind=payload.kind,
        base_url=payload.base_url.rstrip("/"),
        api_key_encrypted=cipher.encrypt(payload.api_key),
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return view(provider)


@router.patch("/{provider_id}", response_model=ProviderRead)
def update_provider(provider_id: int, payload: ProviderUpdate, db: Db):
    provider = db.get(ProviderConfig, provider_id)
    if not provider:
        raise HTTPException(404, "Provider not found")
    data = payload.model_dump(exclude_none=True)
    cipher = SecretCipher()
    if data.pop("clear_api_key", False):
        provider.api_key_encrypted = None
    if "api_key" in data:
        provider.api_key_encrypted = cipher.encrypt(data.pop("api_key"))
    for key, value in data.items():
        if key == "base_url":
            value = value.rstrip("/")
        setattr(provider, key, value)
    db.commit()
    db.refresh(provider)
    return view(provider)


@router.get("/{provider_id}/remote-models", response_model=list[str])
async def remote_models(provider_id: int, db: Db):
    provider = db.get(ProviderConfig, provider_id)
    if not provider:
        raise HTTPException(404, "Provider not found")
    adapter = create_adapter(provider.kind)
    try:
        key = SecretCipher().decrypt(provider.api_key_encrypted)
        return await adapter.list_models(provider.base_url, key)
    except Exception as exc:
        raise HTTPException(502, str(exc)) from exc
