from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.domain.models import Conversation, ModelConfig, Persona
from app.domain.schemas import ConversationCreate, ConversationRead, ConversationUpdate, MessageRead, SendMessage
from app.repositories.settings import SettingsRepository
from app.services.chat import ChatService

router = APIRouter(prefix="/conversations", tags=["conversations"])


def load(db: Session, conversation_id: int) -> Conversation | None:
    return (
        db.query(Conversation)
        .options(
            joinedload(Conversation.persona),
            joinedload(Conversation.model_config).joinedload(ModelConfig.provider),
            joinedload(Conversation.messages),
        )
        .filter(Conversation.id == conversation_id)
        .one_or_none()
    )


def view(row: Conversation, include_messages: bool = True) -> ConversationRead:
    return ConversationRead(
        id=row.id,
        title=row.title,
        persona_id=row.persona_id,
        persona_name=row.persona.name,
        persona_emoji=row.persona.avatar_emoji,
        model_config_id=row.model_config_id,
        model_display_name=row.model_config.display_name,
        provider_kind=row.model_config.provider.kind,
        is_archived=row.is_archived,
        created_at=row.created_at,
        updated_at=row.updated_at,
        messages=[MessageRead.model_validate(message) for message in row.messages] if include_messages else [],
    )


@router.get("", response_model=list[ConversationRead])
def list_conversations(db: Session = Depends(get_db)):
    rows = (
        db.query(Conversation)
        .options(joinedload(Conversation.persona), joinedload(Conversation.model_config).joinedload(ModelConfig.provider))
        .filter(Conversation.is_archived.is_(False))
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [view(row, include_messages=False) for row in rows]


@router.post("", response_model=ConversationRead, status_code=201)
def create_conversation(payload: ConversationCreate, db: Session = Depends(get_db)):
    settings = SettingsRepository(db).get_all()
    persona_id = payload.persona_id or int(settings["active_persona_id"])
    model_config_id = payload.model_config_id or int(settings["active_model_config_id"])
    if not db.get(Persona, persona_id):
        raise HTTPException(404, "Persona not found")
    if not db.get(ModelConfig, model_config_id):
        raise HTTPException(404, "Model config not found")
    row = Conversation(title=payload.title, persona_id=persona_id, model_config_id=model_config_id)
    db.add(row)
    db.commit()
    return view(load(db, row.id))


@router.get("/{conversation_id}", response_model=ConversationRead)
def get_conversation(conversation_id: int, db: Session = Depends(get_db)):
    row = load(db, conversation_id)
    if not row:
        raise HTTPException(404, "Conversation not found")
    return view(row)


@router.patch("/{conversation_id}", response_model=ConversationRead)
def update_conversation(conversation_id: int, payload: ConversationUpdate, db: Session = Depends(get_db)):
    row = db.get(Conversation, conversation_id)
    if not row:
        raise HTTPException(404, "Conversation not found")
    data = payload.model_dump(exclude_none=True)
    if "persona_id" in data and not db.get(Persona, data["persona_id"]):
        raise HTTPException(404, "Persona not found")
    if "model_config_id" in data and not db.get(ModelConfig, data["model_config_id"]):
        raise HTTPException(404, "Model config not found")
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    return view(load(db, row.id))


@router.delete("/{conversation_id}", status_code=204)
def archive_conversation(conversation_id: int, db: Session = Depends(get_db)):
    row = db.get(Conversation, conversation_id)
    if not row:
        raise HTTPException(404, "Conversation not found")
    row.is_archived = True
    db.commit()


@router.post("/{conversation_id}/messages/stream")
async def stream_message(conversation_id: int, payload: SendMessage, db: Session = Depends(get_db)):
    if not db.get(Conversation, conversation_id):
        raise HTTPException(404, "Conversation not found")
    service = ChatService(db)
    return StreamingResponse(
        service.stream_message(conversation_id, payload.content),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
