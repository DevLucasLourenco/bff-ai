from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator

from sqlalchemy.orm import Session, joinedload

from app.core.security import SecretCipher
from app.domain.models import Conversation, Memory, Message, ModelConfig, ProviderConfig, utcnow
from app.services.llm.base import ChatRuntimeConfig
from app.services.llm.factory import create_adapter


class ChatService:
    def __init__(self, db: Session, cipher: SecretCipher | None = None) -> None:
        self.db = db
        self.cipher = cipher or SecretCipher()

    def _load_conversation(self, conversation_id: int) -> Conversation:
        conversation = (
            self.db.query(Conversation)
            .options(
                joinedload(Conversation.messages),
                joinedload(Conversation.persona),
                joinedload(Conversation.model_config).joinedload(ModelConfig.provider),
            )
            .filter(Conversation.id == conversation_id)
            .one_or_none()
        )
        if not conversation:
            raise LookupError("Conversation not found")
        if conversation.is_archived:
            raise ValueError("Conversation is archived")
        return conversation

    @staticmethod
    def _sse(event: str, payload: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    async def stream_message(self, conversation_id: int, user_content: str) -> AsyncIterator[str]:
        conversation = self._load_conversation(conversation_id)
        provider: ProviderConfig = conversation.model_config.provider
        if not provider.is_enabled:
            raise ValueError("The selected provider is disabled")

        user_message = Message(conversation_id=conversation.id, role="user", content=user_content)
        self.db.add(user_message)
        conversation.updated_at = utcnow()
        if len(conversation.messages) == 0 and conversation.title == "Nova conversa":
            conversation.title = user_content.strip().replace("\n", " ")[:70] or "Nova conversa"
        self.db.commit()

        history = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.id.asc())
            .all()
        )
        llm_messages = [{"role": "system", "content": conversation.persona.system_prompt}]
        memories = self.db.query(Memory).filter(Memory.is_active.is_(True)).order_by(Memory.id.asc()).all()
        if memories:
            memory_text = "\n".join(f"- [{item.category}] {item.content}" for item in memories)
            llm_messages.append({
                "role": "system",
                "content": "Memórias persistentes fornecidas explicitamente pela usuária. Use-as apenas quando forem relevantes e não invente detalhes além delas:\n" + memory_text,
            })
        llm_messages.extend({"role": msg.role, "content": msg.content} for msg in history if msg.role in {"user", "assistant"})

        config = ChatRuntimeConfig(
            base_url=provider.base_url,
            model_id=conversation.model_config.model_id,
            api_key=self.cipher.decrypt(provider.api_key_encrypted),
            temperature=conversation.model_config.temperature,
            # NVIDIA reasoning models share their token budget between thinking
            # and the visible answer. Let NVIDIA choose its provider default
            # instead of forcing the legacy 2048-token cap.
            max_tokens=None if provider.kind == "nvidia_nim" or conversation.model_config.max_tokens <= 0 else conversation.model_config.max_tokens,
            top_p=conversation.model_config.top_p,
            reasoning_effort="none" if provider.kind == "nvidia_nim" else None,
        )
        adapter = create_adapter(provider.kind)

        yield self._sse("meta", {"conversation_id": conversation.id, "model": config.model_id, "provider": provider.kind})
        started = time.perf_counter()
        chunks: list[str] = []
        try:
            async for chunk in adapter.stream(llm_messages, config):
                chunks.append(chunk)
                yield self._sse("token", {"text": chunk})
        except Exception as exc:
            # Important: no fallback attempt is made here.
            yield self._sse("error", {"message": str(exc)})
            return

        content = "".join(chunks).strip()
        latency_ms = round((time.perf_counter() - started) * 1000)
        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=content,
            model_id=config.model_id,
            provider_kind=provider.kind,
            latency_ms=latency_ms,
        )
        self.db.add(assistant_message)
        conversation.updated_at = utcnow()
        self.db.commit()
        self.db.refresh(assistant_message)
        yield self._sse("done", {"message_id": assistant_message.id, "latency_ms": latency_ms})
