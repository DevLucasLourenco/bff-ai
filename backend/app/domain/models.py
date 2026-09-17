from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


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
    __tablename__ = "model_configs"
    __table_args__ = (UniqueConstraint("provider_id", "model_id", name="uq_provider_model"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("provider_configs.id", ondelete="CASCADE"), index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    model_id: Mapped[str] = mapped_column(String(240))
    temperature_milli: Mapped[int] = mapped_column(Integer, default=750)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2048)
    top_p_milli: Mapped[int] = mapped_column(Integer, default=950)
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
    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(String(400), default="")
    system_prompt: Mapped[str] = mapped_column(Text)
    greeting: Mapped[str] = mapped_column(Text, default="")
    avatar_emoji: Mapped[str] = mapped_column(String(24), default="💗")
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

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    model_id: Mapped[Optional[str]] = mapped_column(String(240), nullable=True)
    provider_kind: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(80), default="general", index=True)
    content: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
