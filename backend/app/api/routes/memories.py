from fastapi import APIRouter, HTTPException

from app.api.deps import Db
from app.domain.models import Conversation, Memory, MemoryScope, Persona
from app.domain.schemas import MemoryCreate, MemoryRead, MemoryUpdate

router = APIRouter(prefix="/memories", tags=["memories"])


def validate_scope(db, scope: str, persona_id: int | None, conversation_id: int | None) -> None:
    """Memória com escopo precisa apontar para algo que existe (F4.3)."""
    if scope == MemoryScope.PERSONA.value:
        if persona_id is None or not db.get(Persona, persona_id):
            raise HTTPException(422, "Memória de persona exige um persona_id válido")
    elif scope == MemoryScope.CONVERSATION.value:
        if conversation_id is None or not db.get(Conversation, conversation_id):
            raise HTTPException(422, "Memória de conversa exige um conversation_id válido")


@router.get("", response_model=list[MemoryRead])
def list_memories(db: Db):
    return db.query(Memory).order_by(Memory.updated_at.desc()).all()


@router.post("", response_model=MemoryRead, status_code=201)
def create_memory(payload: MemoryCreate, db: Db):
    validate_scope(db, payload.scope, payload.persona_id, payload.conversation_id)
    row = Memory(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/{memory_id}", response_model=MemoryRead)
def update_memory(memory_id: int, payload: MemoryUpdate, db: Db):
    row = db.get(Memory, memory_id)
    if not row:
        raise HTTPException(404, "Memory not found")
    data = payload.model_dump(exclude_none=True)
    for key, value in data.items():
        setattr(row, key, value)
    # O alvo precisa acompanhar o escopo: voltar para "global" deixava o
    # persona_id antigo pendurado na memória.
    if row.scope != MemoryScope.PERSONA.value:
        row.persona_id = None
    if row.scope != MemoryScope.CONVERSATION.value:
        row.conversation_id = None
    validate_scope(db, row.scope, row.persona_id, row.conversation_id)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{memory_id}", status_code=204)
def delete_memory(memory_id: int, db: Db):
    row = db.get(Memory, memory_id)
    if not row:
        raise HTTPException(404, "Memory not found")
    db.delete(row)
    db.commit()
