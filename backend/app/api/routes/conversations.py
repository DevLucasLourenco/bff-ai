from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from starlette.concurrency import run_in_threadpool

from app.api.deps import CurrentOwner, Db, get_active
from app.domain.models import Conversation, MessageUiObject, ModelConfig, Persona
from app.domain.schemas import ChatUiObjectRead, ConversationCreate, ConversationRead, ConversationUpdate, MessageRead, SendMessage
from app.repositories.settings import SettingsRepository
from app.services.chat import ChatService, ConversationNotFound, ConversationUnavailable
from app.fashion.external_collection import ExternalImageError
from app.fashion.media import InvalidFashionImage

router = APIRouter(prefix="/conversations", tags=["conversations"])


def load(db: Session, conversation_id: int, owner_id: int) -> Conversation | None:
    return (
        db.query(Conversation)
        .options(
            joinedload(Conversation.persona),
            joinedload(Conversation.model_config).joinedload(ModelConfig.provider),
            joinedload(Conversation.messages),
        )
        .filter(Conversation.id == conversation_id, Conversation.owner_id == owner_id)
        .one_or_none()
    )


def message_view(db: Session, message) -> MessageRead:
    data = MessageRead.model_validate(message).model_dump()
    objects = db.query(MessageUiObject).filter_by(message_id=message.id).order_by(MessageUiObject.position).all()
    # Passamos modelos tipados, sem serialização intermediária. Neste projeto o
    # `model_dump()` já usa os aliases de saída (`type`, `data`, `source`), mas
    # `MessageRead` recebe os nomes internos de ChatUiObjectRead.
    data["ui_objects"] = [ChatUiObjectRead.model_validate(item) for item in objects]
    return MessageRead.model_validate(data)


def view(row: Conversation, include_messages: bool = True, db: Session | None = None) -> ConversationRead:
    return ConversationRead(
        id=row.id,
        title=row.title,
        persona_id=row.persona_id,
        persona_name=row.persona.name,
        persona_emoji=row.persona.avatar_emoji,
        persona_greeting=row.persona.greeting,
        model_config_id=row.model_config_id,
        model_display_name=row.model_config.display_name,
        provider_kind=row.model_config.provider.kind,
        is_archived=row.is_archived,
        created_at=row.created_at,
        updated_at=row.updated_at,
        messages=[message_view(db, message) for message in row.messages] if include_messages and db is not None else [],
    )


@router.get("", response_model=list[ConversationRead])
def list_conversations(db: Db, owner_id: CurrentOwner):
    rows = (
        db.query(Conversation)
        .options(joinedload(Conversation.persona), joinedload(Conversation.model_config).joinedload(ModelConfig.provider))
        .filter(Conversation.is_archived.is_(False), Conversation.owner_id == owner_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [view(row, include_messages=False) for row in rows]


@router.post("", response_model=ConversationRead, status_code=201)
def create_conversation(payload: ConversationCreate, db: Db, owner_id: CurrentOwner):
    settings = SettingsRepository(db).get_all()
    persona_id = payload.persona_id or int(settings["active_persona_id"])
    model_config_id = payload.model_config_id or int(settings["active_model_config_id"])
    get_active(db, Persona, persona_id, "Persona")
    get_active(db, ModelConfig, model_config_id, "Modelo")
    row = Conversation(owner_id=owner_id, title=payload.title, persona_id=persona_id, model_config_id=model_config_id)
    db.add(row)
    db.commit()
    return view(load(db, row.id, owner_id), db=db)


@router.get("/{conversation_id}", response_model=ConversationRead)
def get_conversation(conversation_id: int, db: Db, owner_id: CurrentOwner):
    row = load(db, conversation_id, owner_id)
    if not row:
        raise HTTPException(404, "Conversation not found")
    return view(row, db=db)


@router.patch("/{conversation_id}", response_model=ConversationRead)
def update_conversation(conversation_id: int, payload: ConversationUpdate, db: Db, owner_id: CurrentOwner):
    row = load(db, conversation_id, owner_id)
    if not row:
        raise HTTPException(404, "Conversation not found")
    data = payload.model_dump(exclude_none=True)
    if "persona_id" in data:
        get_active(db, Persona, data["persona_id"], "Persona")
    if "model_config_id" in data:
        get_active(db, ModelConfig, data["model_config_id"], "Modelo")
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    return view(load(db, row.id, owner_id), db=db)


@router.delete("/{conversation_id}", status_code=204)
def archive_conversation(conversation_id: int, db: Db, owner_id: CurrentOwner):
    row = load(db, conversation_id, owner_id)
    if not row:
        raise HTTPException(404, "Conversation not found")
    row.is_archived = True
    db.commit()


SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"}


def _streaming(service: ChatService, turn) -> StreamingResponse:
    return StreamingResponse(service.run(turn), media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/{conversation_id}/messages/stream")
async def stream_message(conversation_id: int, payload: SendMessage, db: Db, owner_id: CurrentOwner):
    service = ChatService(db, owner_id=owner_id)
    try:
        # O preparo roda em threadpool: é I/O de banco síncrono e não pode
        # bloquear o event loop (F3.4). Falhar aqui vira status HTTP de verdade,
        # em vez de um 200 com evento de erro no corpo.
        turn = await run_in_threadpool(service.prepare, conversation_id, payload.content, payload.attachment_asset_ids)
    except ConversationNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except ConversationUnavailable as exc:
        raise HTTPException(409, str(exc)) from exc
    except (ExternalImageError, InvalidFashionImage) as exc:
        raise HTTPException(422, str(exc)) from exc
    return _streaming(service, turn)


@router.post("/{conversation_id}/messages/{message_id}/regenerate")
async def regenerate_message(conversation_id: int, message_id: int, db: Db, owner_id: CurrentOwner):
    """Refaz a última resposta do assistente (F3.5). Respostas antigas: 409."""
    service = ChatService(db, owner_id=owner_id)
    try:
        turn = await run_in_threadpool(service.prepare_regeneration, conversation_id, message_id)
    except ConversationNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except ConversationUnavailable as exc:
        raise HTTPException(409, str(exc)) from exc
    return _streaming(service, turn)
