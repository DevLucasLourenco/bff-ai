from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.llm.factory import PROVIDER_KINDS

# Derivado do registry de adapters: a lista de kinds válidos existe em um lugar só.
ProviderKind = Literal[PROVIDER_KINDS]


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: ProviderKind
    base_url: str = Field(min_length=4, max_length=500)
    api_key: str | None = None


class ProviderUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    clear_api_key: bool = False
    is_enabled: bool | None = None


class ProviderRead(OrmModel):
    id: int
    name: str
    kind: str
    base_url: str
    has_api_key: bool
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class ModelCreate(BaseModel):
    provider_id: int
    display_name: str
    model_id: str
    temperature: float = Field(default=0.75, ge=0, le=2)
    # None means that the provider chooses its own maximum.
    max_tokens: int | None = Field(default=None, ge=1)
    top_p: float = Field(default=0.95, gt=0, le=1)
    # 0 = janela desconhecida: sem orçamento, o histórico não é truncado.
    context_window: int = Field(default=0, ge=0)


class ModelUpdate(BaseModel):
    display_name: str | None = None
    model_id: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1)
    top_p: float | None = Field(default=None, gt=0, le=1)
    context_window: int | None = Field(default=None, ge=0)


class ModelRead(BaseModel):
    id: int
    provider_id: int
    provider_name: str
    provider_kind: str
    display_name: str
    model_id: str
    temperature: float
    max_tokens: int | None
    top_p: float
    context_window: int


class PersonaTraitFields(BaseModel):
    """Os campos que descrevem a personalidade (o que varia entre personas)."""

    personality: str = ""
    humor: str = ""
    tone: str = ""
    energy: str = ""
    objective: str = ""
    avoid: str = ""
    extra_instructions: str = ""


class PersonaCreate(PersonaTraitFields):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    greeting: str = ""
    avatar_emoji: str = "💗"


class PersonaUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    personality: str | None = None
    humor: str | None = None
    tone: str | None = None
    energy: str | None = None
    objective: str | None = None
    avoid: str | None = None
    extra_instructions: str | None = None
    greeting: str | None = None
    avatar_emoji: str | None = None


class PersonaRead(OrmModel):
    id: int
    name: str
    description: str
    personality: str
    humor: str
    tone: str
    energy: str
    objective: str
    avoid: str
    extra_instructions: str
    greeting: str
    avatar_emoji: str
    # Prompt final, montado a partir da regra global + campos + extras. A UI
    # mostra exatamente isto, para não haver mistério sobre o que foi enviado.
    composed_prompt: str
    created_at: datetime
    updated_at: datetime


class MessageRead(OrmModel):
    id: int
    role: str
    content: str
    # "complete" | "failed" | "cancelled": a UI marca resposta interrompida em
    # vez de descartá-la.
    status: str
    error_code: str | None
    error_message: str | None
    model_id: str | None
    provider_kind: str | None
    latency_ms: int | None
    prompt_tokens: int | None
    completion_tokens: int | None
    created_at: datetime


class ConversationCreate(BaseModel):
    title: str = "Nova conversa"
    persona_id: int | None = None
    model_config_id: int | None = None


class ConversationUpdate(BaseModel):
    title: str | None = None
    persona_id: int | None = None
    model_config_id: int | None = None
    is_archived: bool | None = None


class ConversationRead(BaseModel):
    id: int
    title: str
    persona_id: int
    persona_name: str
    persona_emoji: str
    model_config_id: int
    model_display_name: str
    provider_kind: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead] = []


class SendMessage(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)


MemoryScopeName = Literal["global", "persona", "conversation"]
ThemeName = Literal["system", "light", "dark"]


class MemoryCreate(BaseModel):
    category: str = Field(default="general", min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=5000)
    is_active: bool = True
    scope: MemoryScopeName = "global"
    persona_id: int | None = None
    conversation_id: int | None = None


class MemoryUpdate(BaseModel):
    category: str | None = Field(default=None, min_length=1, max_length=80)
    content: str | None = Field(default=None, min_length=1, max_length=5000)
    is_active: bool | None = None
    scope: MemoryScopeName | None = None
    persona_id: int | None = None
    conversation_id: int | None = None


class MemoryRead(OrmModel):
    id: int
    category: str
    content: str
    is_active: bool
    scope: str
    persona_id: int | None
    conversation_id: int | None
    created_at: datetime
    updated_at: datetime


class SettingsRead(BaseModel):
    app_name: str
    user_display_name: str
    theme: ThemeName
    active_persona_id: int
    active_model_config_id: int
    # Regra que toda persona obedece, antes de qualquer traço de personalidade.
    global_persona_rules: str


class SettingsUpdate(BaseModel):
    app_name: str | None = None
    user_display_name: str | None = None
    theme: ThemeName | None = None
    active_persona_id: int | None = None
    active_model_config_id: int | None = None
    global_persona_rules: str | None = None
