from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Body, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import CurrentOwner, Db
from app.domain.models import Conversation, FashionAsset, Message, MessageUiObject
from app.domain.schemas import (
    ChatActionRequest,
    ChatUiObjectRead,
    FashionAssetRead,
    LookPlanCreate,
    LookPlanRead,
    OutfitCreate,
    OutfitFeedbackCreate,
    OutfitRead,
    StyleProfileRead,
    StyleProfileUpdate,
    WardrobeItemCreate,
    WardrobeItemRead,
    WardrobeItemUpdate,
    WardrobePage,
    WearEventCreate,
    WearEventRead,
)
from app.fashion.media import InvalidFashionImage, MAX_UPLOAD_BYTES, _safe_path, remove_asset, resolve_asset, store_image
from app.fashion.services import FashionConflict, FashionNotFound, FashionService
from app.fashion.tools import ToolUnavailable, fashion_tools
from app.fashion.ui_objects import persist_objects


router = APIRouter(prefix="/fashion", tags=["fashion"])


def service(db: Session, owner_id: int) -> FashionService:
    return FashionService(db, owner_id)


def http_error(error: Exception) -> HTTPException:
    if isinstance(error, FashionNotFound):
        return HTTPException(404, str(error))
    if isinstance(error, FashionConflict):
        return HTTPException(409, str(error))
    if isinstance(error, InvalidFashionImage):
        return HTTPException(422, str(error))
    raise error


def asset_view(asset: FashionAsset) -> FashionAssetRead:
    return FashionAssetRead(
        id=asset.id, mime_type=asset.mime_type, width=asset.width, height=asset.height,
        byte_size=asset.byte_size, created_at=asset.created_at, url=f"/api/fashion/assets/{asset.id}",
    )


@router.post("/assets", response_model=FashionAssetRead, status_code=201)
async def upload_asset(db: Db, owner_id: CurrentOwner, file: UploadFile = File(...)):
    # `read(limit + 1)` impede que um upload enorme vire alocação sem teto no
    # processo antes de a validação de mídia rodar.
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    try:
        return asset_view(store_image(db, owner_id, content, file.content_type))
    except Exception as exc:
        raise http_error(exc) from exc


@router.get("/assets/{asset_id}")
def get_asset(asset_id: int, db: Db, owner_id: CurrentOwner, thumbnail: bool = Query(default=False)):
    try:
        asset = resolve_asset(db, owner_id, asset_id)
        path = _safe_path(asset.storage_key, thumbnail=thumbnail)
        if not path.is_file():
            raise FashionNotFound("Imagem não encontrada")
        return FileResponse(path, media_type=asset.mime_type, headers={"Cache-Control": "private, max-age=86400"})
    except Exception as exc:
        raise http_error(exc) from exc


@router.delete("/assets/{asset_id}", status_code=204)
def delete_asset(asset_id: int, db: Db, owner_id: CurrentOwner):
    try:
        remove_asset(db, owner_id, asset_id)
    except Exception as exc:
        raise http_error(exc) from exc


@router.get("/wardrobe", response_model=WardrobePage)
def list_wardrobe(
    db: Db,
    owner_id: CurrentOwner,
    category: str | None = None,
    color: str | None = None,
    style: str | None = None,
    season: str | None = None,
    occasion: str | None = None,
    query: str | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=30, ge=1, le=50),
):
    items, total = service(db, owner_id).list_items(
        category=category, color=color, style=style, season=season, occasion=occasion,
        query=query, offset=offset, limit=limit,
    )
    next_cursor = str(offset + limit) if offset + limit < total else None
    return WardrobePage(items=items, total=total, next_cursor=next_cursor)


@router.post("/wardrobe", response_model=WardrobeItemRead, status_code=201)
def create_wardrobe_item(payload: WardrobeItemCreate, db: Db, owner_id: CurrentOwner):
    try:
        return service(db, owner_id).create_item(payload)
    except Exception as exc:
        raise http_error(exc) from exc


@router.get("/wardrobe/{item_id}", response_model=WardrobeItemRead)
def get_wardrobe_item(item_id: int, db: Db, owner_id: CurrentOwner):
    try:
        return service(db, owner_id).item_view(service(db, owner_id)._item(item_id))
    except Exception as exc:
        raise http_error(exc) from exc


@router.patch("/wardrobe/{item_id}", response_model=WardrobeItemRead)
def update_wardrobe_item(item_id: int, payload: WardrobeItemUpdate, db: Db, owner_id: CurrentOwner):
    try:
        return service(db, owner_id).update_item(item_id, payload)
    except Exception as exc:
        raise http_error(exc) from exc


@router.delete("/wardrobe/{item_id}", response_model=WardrobeItemRead)
def archive_wardrobe_item(item_id: int, db: Db, owner_id: CurrentOwner, expected_revision: int = Query(ge=1)):
    try:
        return service(db, owner_id).archive_item(item_id, expected_revision)
    except Exception as exc:
        raise http_error(exc) from exc


@router.get("/style-profile", response_model=StyleProfileRead)
def get_style_profile(db: Db, owner_id: CurrentOwner):
    return service(db, owner_id).profile()


@router.patch("/style-profile", response_model=StyleProfileRead)
def update_style_profile(payload: StyleProfileUpdate, db: Db, owner_id: CurrentOwner):
    try:
        return service(db, owner_id).update_profile(payload)
    except Exception as exc:
        raise http_error(exc) from exc


@router.post("/outfits", response_model=OutfitRead, status_code=201)
def create_outfit(payload: OutfitCreate, db: Db, owner_id: CurrentOwner):
    try:
        return service(db, owner_id).create_outfit(payload)
    except Exception as exc:
        raise http_error(exc) from exc


@router.get("/outfits/{outfit_id}", response_model=OutfitRead)
def get_outfit(outfit_id: int, db: Db, owner_id: CurrentOwner):
    try:
        fashion = service(db, owner_id)
        return fashion.outfit_view(fashion._outfit(outfit_id))
    except Exception as exc:
        raise http_error(exc) from exc


@router.post("/outfits/{outfit_id}/feedback", status_code=204)
def feedback_outfit(outfit_id: int, payload: OutfitFeedbackCreate, db: Db, owner_id: CurrentOwner):
    try:
        service(db, owner_id).feedback(outfit_id, liked=payload.liked, reason=payload.reason)
    except Exception as exc:
        raise http_error(exc) from exc


@router.post("/wear-events", response_model=WearEventRead, status_code=201)
def create_wear_event(payload: WearEventCreate, db: Db, owner_id: CurrentOwner):
    try:
        return service(db, owner_id).record_wear(payload)
    except Exception as exc:
        raise http_error(exc) from exc


@router.post("/look-plans", response_model=LookPlanRead, status_code=201)
def create_look_plan(payload: LookPlanCreate, db: Db, owner_id: CurrentOwner):
    try:
        return service(db, owner_id).create_plan(payload)
    except Exception as exc:
        raise http_error(exc) from exc


@router.get("/look-plans", response_model=list[LookPlanRead])
def list_look_plans(starts_at: datetime, ends_at: datetime, db: Db, owner_id: CurrentOwner):
    return service(db, owner_id).list_plans(starts_at, ends_at)


@router.post("/actions")
def run_chat_action(payload: ChatActionRequest, db: Db, owner_id: CurrentOwner):
    """Execute only actions registered by the server for a persisted object.

    The model never sends arbitrary URLs or executable instructions to the UI.
    v1 intentionally supports a small action surface; new actions are added with
    their domain validation here and in the frontend registry.
    """
    row = db.get(MessageUiObject, payload.object_id)
    if row is None:
        raise HTTPException(404, "Objeto do chat não encontrado")
    message = db.get(Message, row.message_id)
    conversation = db.get(Conversation, message.conversation_id) if message else None
    if conversation is None or conversation.owner_id != owner_id:
        raise HTTPException(404, "Objeto do chat não encontrado")
    refs = row.source_refs or []

    def has_ref(kind: str, value: int) -> bool:
        return any(ref.get("kind") == kind and ref.get("ref_id") == str(value) for ref in refs)

    if payload.action_id == "open_item":
        try:
            item_id = int(payload.target.get("item_id", 0))
        except (TypeError, ValueError) as exc:
            raise HTTPException(422, "item_id inválido") from exc
        if not has_ref("wardrobe", item_id):
            raise HTTPException(422, "A peça não pertence a este objeto do chat")
        try:
            item = service(db, owner_id)._item(item_id)
            return {"item": service(db, owner_id).item_view(item).model_dump(mode="json")}
        except Exception as exc:
            raise http_error(exc) from exc
    if payload.action_id == "record_wear":
        item_ids = payload.target.get("item_ids", [])
        outfit_id = payload.target.get("outfit_id")
        if not isinstance(item_ids, list):
            raise HTTPException(422, "item_ids inválido")
        try:
            valid_items = all(has_ref("wardrobe", int(item_id)) for item_id in item_ids)
            valid_outfit = not outfit_id or has_ref("outfit", int(outfit_id))
        except (TypeError, ValueError) as exc:
            raise HTTPException(422, "Alvo inválido") from exc
        if not valid_items or not valid_outfit:
            raise HTTPException(422, "O alvo não pertence a este objeto do chat")
        try:
            event = service(db, owner_id).record_wear(WearEventCreate(
                item_ids=item_ids,
                outfit_id=outfit_id,
                idempotency_key=payload.idempotency_key,
            ))
            return {"wear_event": event.model_dump(mode="json")}
        except Exception as exc:
            raise http_error(exc) from exc
    raise HTTPException(422, "Ação Fashion não suportada por este objeto")


@router.get("/tools")
def list_fashion_tools():
    """Expose schemas for configured orchestration, never executable UI code."""
    return {"tools": fashion_tools.schemas()}


@router.post("/tools/{tool_name}")
def execute_fashion_tool(
    tool_name: str,
    db: Db,
    owner_id: CurrentOwner,
    message_id: int | None = Query(default=None, gt=0),
    arguments: dict = Body(default={}),
):
    """Internal-friendly seam for adapters and deterministic integration tests."""
    try:
        result = fashion_tools.execute(tool_name, arguments, service(db, owner_id))
        objects = []
        if message_id is not None:
            message = db.get(Message, message_id)
            conversation = db.get(Conversation, message.conversation_id) if message else None
            if conversation is None or conversation.owner_id != owner_id:
                raise FashionNotFound("Mensagem não encontrada")
            objects = [item.model_dump(by_alias=True, mode="json") for item in persist_objects(db, message_id, result)]
            db.commit()
        return result.as_model_content() | {"ui_hints": result.ui_hints, "ui_objects": objects}
    except ToolUnavailable as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise http_error(exc) from exc
