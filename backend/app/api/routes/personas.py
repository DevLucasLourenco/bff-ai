from fastapi import APIRouter, HTTPException

from app.api.deps import Db
from app.domain.models import Conversation, Persona
from app.domain.schemas import PersonaCreate, PersonaRead, PersonaUpdate
from app.repositories.settings import SettingsRepository
from app.services.persona import compose_system_prompt, traits_from_row

router = APIRouter(prefix="/personas", tags=["personas"])


def view(persona: Persona, global_rules: str) -> PersonaRead:
    return PersonaRead(
        **{campo: getattr(persona, campo) for campo in (
            "id", "name", "description", "personality", "humor", "tone",
            "energy", "objective", "avoid", "extra_instructions",
            "greeting", "avatar_emoji", "created_at", "updated_at",
        )},
        # Montado aqui para a UI poder mostrar exatamente o que será enviado ao
        # modelo, em vez de a usuária ter que imaginar o resultado dos campos.
        composed_prompt=compose_system_prompt(traits_from_row(persona), global_rules),
    )


def regras_globais(db) -> str:
    return SettingsRepository(db).get_all().get("global_persona_rules", "")


@router.get("", response_model=list[PersonaRead])
def list_personas(db: Db):
    regras = regras_globais(db)
    return [view(p, regras) for p in db.query(Persona).order_by(Persona.name.asc()).all()]


@router.post("", response_model=PersonaRead, status_code=201)
def create_persona(payload: PersonaCreate, db: Db):
    if db.query(Persona).filter(Persona.name == payload.name).count():
        raise HTTPException(409, "Já existe uma persona com esse nome")
    persona = Persona(**payload.model_dump())
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return view(persona, regras_globais(db))


@router.patch("/{persona_id}", response_model=PersonaRead)
def update_persona(persona_id: int, payload: PersonaUpdate, db: Db):
    persona = db.get(Persona, persona_id)
    if not persona:
        raise HTTPException(404, "Persona not found")
    data = payload.model_dump(exclude_none=True)
    if "name" in data and db.query(Persona).filter(
        Persona.name == data["name"], Persona.id != persona_id
    ).count():
        raise HTTPException(409, "Já existe uma persona com esse nome")
    for key, value in data.items():
        setattr(persona, key, value)
    db.commit()
    db.refresh(persona)
    return view(persona, regras_globais(db))


@router.delete("/{persona_id}", status_code=204)
def delete_persona(persona_id: int, db: Db):
    persona = db.get(Persona, persona_id)
    if not persona:
        raise HTTPException(404, "Persona not found")
    if db.query(Conversation).filter(Conversation.persona_id == persona_id).count():
        raise HTTPException(409, "Persona is used by conversations")
    db.delete(persona)
    db.commit()
