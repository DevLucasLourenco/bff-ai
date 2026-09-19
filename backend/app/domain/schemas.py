from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

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
    supports_tools: bool = False


class ModelUpdate(BaseModel):
    display_name: str | None = None
    model_id: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1)
    top_p: float | None = Field(default=None, gt=0, le=1)
    context_window: int | None = Field(default=None, ge=0)
    supports_tools: bool | None = None


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
    supports_tools: bool


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
    attachment_asset_ids: list[int] = []
    created_at: datetime
    # Objetos são persistidos fora do texto da mensagem para que o frontend não
    # precise tentar extrair JSON do conteúdo produzido pelo modelo.
    ui_objects: list["ChatUiObjectRead"] = []


# Fashion Module -------------------------------------------------------------

FashionObjectType = Literal[
    "wardrobe_view", "wardrobe_item", "outfit_carousel", "outfit_detail",
    "product_carousel", "trend_board", "look_calendar", "wardrobe_suggestion",
]


class SourceRef(BaseModel):
    kind: Literal["wardrobe", "outfit", "product", "trend", "tool_run", "web"]
    ref_id: str = Field(min_length=1, max_length=120)
    observed_at: datetime | None = None
    url: str | None = Field(default=None, max_length=2048)


class ChatAction(BaseModel):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=1, max_length=120)
    target: dict[str, Any] = Field(default_factory=dict)


class ChatUiPayload(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    subtitle: str = Field(default="", max_length=300)
    data: dict[str, Any] = Field(default_factory=dict)
    actions: list[ChatAction] = Field(default_factory=list, max_length=12)
    metadata: dict[str, str] = Field(default_factory=dict)


class ChatUiObjectRead(OrmModel):
    id: int
    type: FashionObjectType = Field(validation_alias="object_type", serialization_alias="type")
    schema_version: int
    data: ChatUiPayload = Field(validation_alias="payload", serialization_alias="data")
    source: list[SourceRef] = Field(validation_alias="source_refs", serialization_alias="source")
    created_at: datetime


class FashionAssetRead(OrmModel):
    id: int
    mime_type: str
    width: int
    height: int
    byte_size: int
    created_at: datetime
    url: str


class WardrobeItemFields(BaseModel):
    name: str = Field(min_length=1, max_length=180)
    category: str = Field(min_length=1, max_length=60)
    subcategory: str | None = Field(default=None, max_length=80)
    color: str | None = Field(default=None, max_length=80)
    material: str | None = Field(default=None, max_length=100)
    brand: str | None = Field(default=None, max_length=120)
    size: str | None = Field(default=None, max_length=40)
    style: str | None = Field(default=None, max_length=100)
    seasons: list[str] = Field(default_factory=list, max_length=12)
    occasions: list[str] = Field(default_factory=list, max_length=20)
    formality: int | None = Field(default=None, ge=1, le=5)
    tags: list[str] = Field(default_factory=list, max_length=30)
    image_asset_id: int | None = Field(default=None, gt=0)
    collection_status: Literal["owned", "wanted", "inspiration", "retired"] = "owned"


class WardrobeItemCreate(WardrobeItemFields):
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=120)


class WardrobeItemUpdate(BaseModel):
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=180)
    category: str | None = Field(default=None, min_length=1, max_length=60)
    subcategory: str | None = Field(default=None, max_length=80)
    color: str | None = Field(default=None, max_length=80)
    material: str | None = Field(default=None, max_length=100)
    brand: str | None = Field(default=None, max_length=120)
    size: str | None = Field(default=None, max_length=40)
    style: str | None = Field(default=None, max_length=100)
    seasons: list[str] | None = Field(default=None, max_length=12)
    occasions: list[str] | None = Field(default=None, max_length=20)
    formality: int | None = Field(default=None, ge=1, le=5)
    tags: list[str] | None = Field(default=None, max_length=30)
    image_asset_id: int | None = Field(default=None, gt=0)
    collection_status: Literal["owned", "wanted", "inspiration", "retired"] | None = None


class WardrobeItemRead(WardrobeItemFields, OrmModel):
    id: int
    source: str
    external_url: str | None = None
    external_domain: str | None = None
    external_captured_at: datetime | None = None
    attribute_confidence: dict[str, Any]
    revision: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    image: FashionAssetRead | None = None
    wear_count: int = 0
    last_worn_at: datetime | None = None


class WardrobePage(BaseModel):
    items: list[WardrobeItemRead]
    total: int
    next_cursor: str | None = None


class ExternalImageImport(BaseModel):
    image_url: str = Field(min_length=8, max_length=2048)
    name: str = Field(min_length=1, max_length=180)
    category: str = Field(min_length=1, max_length=60)
    color: str | None = Field(default=None, max_length=80)
    style: str | None = Field(default=None, max_length=100)
    brand: str | None = Field(default=None, max_length=120)
    collection_status: Literal["owned", "wanted", "inspiration"] = "wanted"
    tags: list[str] = Field(default_factory=list, max_length=30)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=120)


class StyleProfileUpdate(BaseModel):
    expected_revision: int | None = Field(default=None, ge=1)
    explicit_preferences: dict[str, Any] | None = None
    restrictions: dict[str, Any] | None = None
    default_budget: str | None = Field(default=None, max_length=32)
    default_currency: str | None = Field(default=None, min_length=3, max_length=3)


class StyleSignalRead(OrmModel):
    id: int
    signal_type: str
    entity_type: str
    entity_id: int | None
    attribute: str | None
    value: str | None
    weight: int
    confidence: int
    is_revoked: bool
    created_at: datetime


class StyleProfileRead(OrmModel):
    id: int
    explicit_preferences: dict[str, Any]
    inferred_preferences: dict[str, Any]
    restrictions: dict[str, Any]
    default_budget: str | None
    default_currency: str
    revision: int
    updated_at: datetime
    signals: list[StyleSignalRead] = []


class OutfitItemInput(BaseModel):
    slot: str = Field(min_length=1, max_length=50)
    wardrobe_item_id: int | None = Field(default=None, gt=0)
    external_snapshot: dict[str, Any] | None = None


class OutfitCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    style: str | None = Field(default=None, max_length=100)
    occasion: str | None = Field(default=None, max_length=100)
    explanation: str = Field(default="", max_length=5000)
    items: list[OutfitItemInput] = Field(min_length=1, max_length=12)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=120)


class OutfitItemRead(OutfitItemInput, OrmModel):
    id: int
    position: int
    wardrobe_item: WardrobeItemRead | None = None


class OutfitRead(OrmModel):
    id: int
    title: str
    style: str | None
    occasion: str | None
    explanation: str
    source: str
    revision: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    items: list[OutfitItemRead]


class OutfitFeedbackCreate(BaseModel):
    liked: bool
    reason: str | None = Field(default=None, max_length=500)


class WearEventCreate(BaseModel):
    item_ids: list[int] = Field(default_factory=list, max_length=12)
    outfit_id: int | None = Field(default=None, gt=0)
    worn_at: datetime | None = None
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=120)


class WearEventRead(OrmModel):
    id: int
    outfit_id: int | None
    item_ids: list[int]
    worn_at: datetime


class LookPlanCreate(BaseModel):
    planned_for: datetime
    timezone: str = Field(default="America/Sao_Paulo", min_length=1, max_length=64)
    event_name: str = Field(default="", max_length=180)
    occasion: str | None = Field(default=None, max_length=100)
    outfit_id: int | None = Field(default=None, gt=0)


class LookPlanRead(OrmModel):
    id: int
    outfit_id: int | None
    planned_for: datetime
    timezone: str
    event_name: str
    occasion: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class ChatActionRequest(BaseModel):
    object_id: int = Field(gt=0)
    action_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    target: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1, max_length=160)


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
    # Saudação da persona, mostrada na conversa vazia. Era editável e nunca aparecia.
    persona_greeting: str
    model_config_id: int
    model_display_name: str
    provider_kind: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead] = []


class SendMessage(BaseModel):
    content: str = Field(min_length=1, max_length=100_000)
    attachment_asset_ids: list[int] = Field(default_factory=list, max_length=4)


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


MessageRead.model_rebuild()
