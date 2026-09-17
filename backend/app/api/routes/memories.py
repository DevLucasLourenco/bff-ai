from fastapi import APIRouter, HTTPException

from app.api.deps import Db
from app.domain.models import Memory
from app.domain.schemas import MemoryCreate, MemoryRead, MemoryUpdate

router = APIRouter(prefix="/memories", tags=["memories"])


@router.get("", response_model=list[MemoryRead])
def list_memories(db: Db):
    return db.query(Memory).order_by(Memory.updated_at.desc()).all()


@router.post("", response_model=MemoryRead, status_code=201)
def create_memory(payload: MemoryCreate, db: Db):
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
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(row, key, value)
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
