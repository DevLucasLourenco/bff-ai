from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class MessageStatus(str, Enum):
    """Estado de uma resposta do assistente.

    Antes não existia: uma resposta interrompida no meio era descartada e a
    conversa ficava com um turno do usuário pendurado, sem nada que explicasse.
    """

    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProviderConfig(Base):
    __tablename__ = "provider_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)  # ollama | nvidia_nim
    base_url: Mapped[str] = mapped_column(String(500))
    api_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    models: Mapped[list["ModelConfig"]] = relationship(back_populates="provider", cascade="all, delete-orphan")


class ModelConfig(Base):
    """Um modelo configurado. Arquivar some da lista sem quebrar as conversas
    que registraram esse modelo — a linha continua existindo."""

    __tablename__ = "model_configs"
    __table_args__ = (UniqueConstraint("provider_id", "model_id", name="uq_provider_model"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("provider_configs.id", ondelete="CASCADE"), index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    model_id: Mapped[str] = mapped_column(String(240))
    temperature_milli: Mapped[int] = mapped_column(Integer, default=750)
    # NULL = o provider escolhe o próprio limite. Era um sentinela 0, que obrigava
    # cada leitor a saber da convenção.
    max_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    top_p_milli: Mapped[int] = mapped_column(Integer, default=950)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    # Janela de contexto do modelo. 0 = desconhecida: sem orçamento não há
    # truncamento, e o histórico vai inteiro como antes.
    context_window: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    # Explicit model confirmation. Adapter capability alone is insufficient:
    # deployments often expose models with different tool-call support.
    supports_tools: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    provider: Mapped[ProviderConfig] = relationship(back_populates="models")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="model_config")

    @property
    def temperature(self) -> float:
        return self.temperature_milli / 1000

    @property
    def top_p(self) -> float:
        return self.top_p_milli / 1000


class Persona(Base):
    """Personalidade como campos, não como um bloco de texto solto.

    As salvaguardas (não fingir sentimentos, admitir o que não sabe) saíram
    daqui para a regra global em `app_settings`: não são personalidade, e uma
    edição descuidada de persona apagava a salvaguarda sem ninguém notar.
    """

    __tablename__ = "personas"
    # Nome único só entre as ativas. Com UNIQUE simples, uma persona excluída
    # (soft delete) continuava dona do nome e ninguém conseguia criar outra igual.
    __table_args__ = (
        Index("uq_personas_nome_ativa", "name", unique=True, sqlite_where=text("is_archived = 0")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(400), default="")
    personality: Mapped[str] = mapped_column(Text, default="", server_default="")
    humor: Mapped[str] = mapped_column(Text, default="", server_default="")
    tone: Mapped[str] = mapped_column(Text, default="", server_default="")
    energy: Mapped[str] = mapped_column(Text, default="", server_default="")
    objective: Mapped[str] = mapped_column(Text, default="", server_default="")
    avoid: Mapped[str] = mapped_column(Text, default="", server_default="")
    # Válvula de escape para o que não cabe nos campos acima.
    extra_instructions: Mapped[str] = mapped_column(Text, default="", server_default="")
    greeting: Mapped[str] = mapped_column(Text, default="")
    avatar_emoji: Mapped[str] = mapped_column(String(24), default="💗")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="persona")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180), default="Nova conversa")
    persona_id: Mapped[int] = mapped_column(ForeignKey("personas.id", ondelete="RESTRICT"), index=True)
    model_config_id: Mapped[int] = mapped_column(ForeignKey("model_configs.id", ondelete="RESTRICT"), index=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    persona: Mapped[Persona] = relationship(back_populates="conversations")
    model_config: Mapped[ModelConfig] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role in ('user', 'assistant')", name="ck_messages_role"),
        CheckConstraint("status in ('complete', 'failed', 'cancelled')", name="ck_messages_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=MessageStatus.COMPLETE.value, server_default="complete")
    error_code: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_id: Mapped[Optional[str]] = mapped_column(String(240), nullable=True)
    provider_kind: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    attachment_asset_ids: Mapped[list[int]] = mapped_column(JSON, default=list, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class MemoryScope(str, Enum):
    GLOBAL = "global"
    PERSONA = "persona"
    CONVERSATION = "conversation"


class Memory(Base):
    __tablename__ = "memories"
    __table_args__ = (
        CheckConstraint("scope in ('global', 'persona', 'conversation')", name="ck_memories_scope"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(80), default="general", index=True)
    content: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    # Escopo: antes toda memória ativa entrava em toda requisição, de qualquer
    # persona e de qualquer conversa.
    scope: Mapped[str] = mapped_column(String(20), default=MemoryScope.GLOBAL.value, server_default="global", index=True)
    persona_id: Mapped[Optional[int]] = mapped_column(ForeignKey("personas.id", ondelete="CASCADE"), nullable=True, index=True)
    conversation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


# Fashion Module -------------------------------------------------------------
#
# O produto ainda é local e tem uma única pessoa usuária. A tabela existe desde
# já para que dados pessoais não precisem de uma migração estrutural quando o
# app ganhar autenticação. Nenhuma rota permite escolher outro owner_id.
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), default="Você", server_default="Você")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FashionAsset(Base):
    __tablename__ = "fashion_assets"
    __table_args__ = (Index("ix_fashion_assets_owner_created", "owner_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True)
    mime_type: Mapped[str] = mapped_column(String(80))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    byte_size: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), index=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    source_image_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    source_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WardrobeItem(Base):
    __tablename__ = "wardrobe_items"
    __table_args__ = (
        Index("ix_wardrobe_items_owner_category", "owner_id", "category"),
        Index("ix_wardrobe_items_owner_archived", "owner_id", "is_archived"),
        Index("ix_wardrobe_items_owner_collection_status", "owner_id", "collection_status"),
        Index("ix_wardrobe_items_owner_external_url", "owner_id", "external_url"),
        UniqueConstraint("owner_id", "external_url", name="uq_wardrobe_items_owner_external_url"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(60), index=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    material: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    brand: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    size: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    style: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    seasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    occasions: Mapped[list[str]] = mapped_column(JSON, default=list)
    formality: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    image_asset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("fashion_assets.id", ondelete="SET NULL"), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="manual", server_default="manual")
    collection_status: Mapped[str] = mapped_column(String(20), default="owned", server_default="owned")
    external_url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    external_domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    external_captured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    attribute_confidence: Mapped[dict] = mapped_column(JSON, default=dict)
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class StyleProfile(Base):
    __tablename__ = "style_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    explicit_preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    inferred_preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    restrictions: Mapped[dict] = mapped_column(JSON, default=dict)
    default_budget: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    default_currency: Mapped[str] = mapped_column(String(3), default="BRL", server_default="BRL")
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class StyleSignal(Base):
    __tablename__ = "style_signals"
    __table_args__ = (Index("ix_style_signals_owner_created", "owner_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    signal_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    attribute: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    value: Mapped[Optional[str]] = mapped_column(String(240), nullable=True)
    weight: Mapped[int] = mapped_column(Integer, default=1)
    confidence: Mapped[int] = mapped_column(Integer, default=100)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Outfit(Base):
    __tablename__ = "outfits"
    __table_args__ = (Index("ix_outfits_owner_archived", "owner_id", "is_archived"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    style: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    occasion: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    explanation: Mapped[str] = mapped_column(Text, default="", server_default="")
    source: Mapped[str] = mapped_column(String(20), default="manual", server_default="manual")
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class OutfitItem(Base):
    __tablename__ = "outfit_items"
    __table_args__ = (UniqueConstraint("outfit_id", "slot", name="uq_outfit_slot"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    outfit_id: Mapped[int] = mapped_column(ForeignKey("outfits.id", ondelete="CASCADE"), index=True)
    wardrobe_item_id: Mapped[Optional[int]] = mapped_column(ForeignKey("wardrobe_items.id", ondelete="SET NULL"), nullable=True, index=True)
    slot: Mapped[str] = mapped_column(String(50))
    position: Mapped[int] = mapped_column(Integer, default=0)
    external_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class OutfitFeedback(Base):
    __tablename__ = "outfit_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    outfit_id: Mapped[int] = mapped_column(ForeignKey("outfits.id", ondelete="CASCADE"), index=True)
    liked: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WearEvent(Base):
    __tablename__ = "wear_events"
    __table_args__ = (Index("ix_wear_events_owner_worn", "owner_id", "worn_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    outfit_id: Mapped[Optional[int]] = mapped_column(ForeignKey("outfits.id", ondelete="SET NULL"), nullable=True)
    item_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    worn_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, unique=True)


class LookPlan(Base):
    __tablename__ = "look_plans"
    __table_args__ = (Index("ix_look_plans_owner_date", "owner_id", "planned_for"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    outfit_id: Mapped[Optional[int]] = mapped_column(ForeignKey("outfits.id", ondelete="SET NULL"), nullable=True)
    planned_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    timezone: Mapped[str] = mapped_column(String(64), default="America/Sao_Paulo", server_default="America/Sao_Paulo")
    event_name: Mapped[str] = mapped_column(String(180), default="", server_default="")
    occasion: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="planned", server_default="planned")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ProductObservation(Base):
    __tablename__ = "product_observations"
    __table_args__ = (Index("ix_product_observations_owner_fetched", "owner_id", "fetched_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_name: Mapped[str] = mapped_column(String(120))
    source_url: Mapped[str] = mapped_column(String(2048))
    canonical_url: Mapped[str] = mapped_column(String(2048), index=True)
    title: Mapped[str] = mapped_column(String(300))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class TrendObservation(Base):
    __tablename__ = "trend_observations"
    __table_args__ = (Index("ix_trend_observations_owner_fetched", "owner_id", "fetched_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_name: Mapped[str] = mapped_column(String(120))
    source_url: Mapped[str] = mapped_column(String(2048))
    title: Mapped[str] = mapped_column(String(300))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ToolRun(Base):
    __tablename__ = "tool_runs"
    __table_args__ = (Index("ix_tool_runs_conversation_created", "conversation_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    conversation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    tool_name: Mapped[str] = mapped_column(String(100))
    tool_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    status: Mapped[str] = mapped_column(String(30), default="completed", server_default="completed")
    arguments: Mapped[dict] = mapped_column(JSON, default=dict)
    result_refs: Mapped[list] = mapped_column(JSON, default=list)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(160), nullable=True, unique=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MessageUiObject(Base):
    __tablename__ = "message_ui_objects"
    __table_args__ = (UniqueConstraint("message_id", "position", name="uq_message_ui_object_position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    object_type: Mapped[str] = mapped_column(String(80), index=True)
    schema_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    source_refs: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExternalServiceConfig(Base):
    __tablename__ = "external_service_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    service_kind: Mapped[str] = mapped_column(String(80), unique=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    secret_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
