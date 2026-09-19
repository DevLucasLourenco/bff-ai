from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
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
