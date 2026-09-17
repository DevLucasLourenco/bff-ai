from fastapi import APIRouter, HTTPException

from app.api.deps import Db
from app.domain.models import Conversation, Persona
from app.domain.schemas import PersonaCreate, PersonaRead, PersonaUpdate

router = APIRouter(prefix="/personas", tags=["personas"])


@router.get("", response_model=list[PersonaRead])
def list_personas(db: Db):
    return db.query(Persona).order_by(Persona.name.asc()).all()


@router.post("", response_model=PersonaRead, status_code=201)
def create_persona(payload: PersonaCreate, db: Db):
    persona = Persona(**payload.model_dump())
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return persona


@router.patch("/{persona_id}", response_model=PersonaRead)
def update_persona(persona_id: int, payload: PersonaUpdate, db: Db):
    persona = db.get(Persona, persona_id)
    if not persona:
        raise HTTPException(404, "Persona not found")
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(persona, key, value)
    db.commit()
    db.refresh(persona)
    return persona


@router.delete("/{persona_id}", status_code=204)
def delete_persona(persona_id: int, db: Db):
    persona = db.get(Persona, persona_id)
    if not persona:
        raise HTTPException(404, "Persona not found")
    if db.query(Conversation).filter(Conversation.persona_id == persona_id).count():
        raise HTTPException(409, "Persona is used by conversations")
    db.delete(persona)
    db.commit()
