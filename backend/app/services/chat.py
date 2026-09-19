from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from starlette.concurrency import run_in_threadpool

from app.core.security import SecretCipher
from app.db.session import SessionLocal
from app.domain.models import (
    Conversation,
    Memory,
    MemoryScope,
    Message,
    MessageRole,
    MessageStatus,
    ModelConfig,
    utcnow,
)
from app.repositories.settings import SettingsRepository
from app.services.context import ContextMessage, build_messages
from app.services.persona import compose_system_prompt, traits_from_row
from app.services.llm.base import ChatRuntimeConfig, LLMAdapter
from app.services.llm.errors import LLMError, ProviderResponseError
from app.services.llm.factory import create_adapter
from app.services.llm.runtime import build_runtime_config

logger = logging.getLogger(__name__)

# Sinal de vida enquanto o provider não manda nada. Sem ele o navegador não tem
# como distinguir "modelo pensando" de "conexão morta", e uma conexão que morre
# em silêncio deixava a UI em "gerando" para sempre.
HEARTBEAT_SECONDS = 15.0
_PING = object()


class _ComBatimento:
    """Itera o stream do adapter e devolve `_PING` a cada `intervalo` de silêncio.

    Usa uma Task para a próxima leitura em vez de `asyncio.wait_for`: o wait_for
    cancelaria a leitura em andamento a cada timeout, o que derruba o stream
    HTTP do provider no meio.
    """

    def __init__(self, fonte, intervalo: float) -> None:
        self._it = fonte.__aiter__()
        self._intervalo = intervalo
        self._proxima: asyncio.Future | None = None

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._proxima is None:
            self._proxima = asyncio.ensure_future(self._it.__anext__())
        feito, _ = await asyncio.wait({self._proxima}, timeout=self._intervalo)
        if not feito:
            return _PING
        tarefa, self._proxima = self._proxima, None
        return tarefa.result()  # StopAsyncIteration encerra a iteração normalmente

    def cancelar(self) -> None:
        """Síncrono de propósito: é chamado num GeneratorExit, onde não há await.

        Cancelar a leitura pendente fecha o stream HTTP do provider — sem isto a
        geração continuaria rodando depois de a usuária ter desistido.
        """
        if self._proxima is not None and not self._proxima.done():
            self._proxima.cancel()


class ConversationNotFound(LookupError):
    pass


class ConversationUnavailable(ValueError):
    """Conversa arquivada ou provider desligado — não há o que streamar."""


@dataclass
class PreparedTurn:
    """Tudo que o stream precisa, já desligado da sessão do banco.

    Existe para cumprir F3.4: dentro do laço de tokens não pode haver nenhum
    acesso a `Session`, nem lazy-load de relacionamento.
    """

    conversation_id: int
    provider_kind: str
    config: ChatRuntimeConfig
    adapter: LLMAdapter
    messages: list[dict[str, str]]
    dropped_messages: int
    estimated_prompt_tokens: int


class ChatService:
    def __init__(self, db: Session, cipher: SecretCipher | None = None) -> None:
        self.db = db
        self.cipher = cipher or SecretCipher()

    # ------------------------------------------------------------------ leitura

    def _load_conversation(self, conversation_id: int) -> Conversation:
        conversation = (
            self.db.query(Conversation)
            .options(
                joinedload(Conversation.persona),
                joinedload(Conversation.model_config).joinedload(ModelConfig.provider),
            )
            .filter(Conversation.id == conversation_id)
            .one_or_none()
        )
        if not conversation:
            raise ConversationNotFound("Conversa não encontrada")
        if conversation.is_archived:
            raise ConversationUnavailable("Conversa arquivada")
        return conversation

    def _memories_for(self, conversation: Conversation) -> list[tuple[str, str]]:
        """Só memórias no escopo desta conversa (F4.3).

        Antes, toda memória ativa entrava em toda requisição — de qualquer
        persona e de qualquer conversa.
        """
        rows = (
            self.db.query(Memory)
            .filter(Memory.is_active.is_(True))
            .filter(
                or_(
                    Memory.scope == MemoryScope.GLOBAL.value,
                    (Memory.scope == MemoryScope.PERSONA.value) & (Memory.persona_id == conversation.persona_id),
                    (Memory.scope == MemoryScope.CONVERSATION.value) & (Memory.conversation_id == conversation.id),
                )
            )
            .order_by(Memory.id.asc())
            .all()
        )
        return [(row.category, row.content) for row in rows]

    def _history_for(self, conversation_id: int) -> list[ContextMessage]:
        rows = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.id.asc())
            .all()
        )
        # Mensagem falhada/cancelada não volta como contexto: é ruído, e o
        # conteúdo parcial pode terminar no meio de uma frase.
        return [
            ContextMessage(row.role, row.content)
            for row in rows
            if row.status == MessageStatus.COMPLETE.value and row.content
        ]

    # ----------------------------------------------------------------- preparo

    def prepare(self, conversation_id: int, user_content: str) -> PreparedTurn:
        """Etapa síncrona: valida, persiste o turno da usuária e monta o prompt.

        Roda **antes** de a resposta de streaming começar, para que erros virem
        status HTTP de verdade em vez de um 200 com evento de erro no corpo.
        """
        conversation = self._load_conversation(conversation_id)
        provider = conversation.model_config.provider
        if not provider.is_enabled:
            raise ConversationUnavailable("O provider selecionado está desativado")

        existing = self.db.query(Message).filter(Message.conversation_id == conversation.id).count()
        self.db.add(
            Message(
                conversation_id=conversation.id,
                role=MessageRole.USER.value,
                content=user_content,
                status=MessageStatus.COMPLETE.value,
            )
        )
        conversation.updated_at = utcnow()
        if existing == 0 and conversation.title == "Nova conversa":
            conversation.title = user_content.strip().replace("\n", " ")[:70] or "Nova conversa"
        self.db.commit()

        return self._build_turn(conversation)

    def prepare_regeneration(self, conversation_id: int, message_id: int) -> PreparedTurn:
        """Descarta a última resposta do assistente e prepara outra (F3.5).

        Sem isto, refazer uma resposta ruim só era possível mandando outra
        mensagem, o que polui o histórico que volta ao modelo a cada turno.
        """
        conversation = self._load_conversation(conversation_id)
        if not conversation.model_config.provider.is_enabled:
            raise ConversationUnavailable("O provider selecionado está desativado")

        target = self.db.get(Message, message_id)
        if not target or target.conversation_id != conversation.id:
            raise ConversationNotFound("Mensagem não encontrada nesta conversa")
        if target.role != MessageRole.ASSISTANT.value:
            raise ConversationUnavailable("Só respostas do assistente podem ser regeneradas")
        # Só a última resposta. Regenerar uma antiga apagava tudo depois dela —
        # inclusive mensagens da usuária — sem confirmação e sem volta.
        depois = self.db.query(Message).filter(
            Message.conversation_id == conversation.id, Message.id > message_id
        ).count()
        if depois:
            raise ConversationUnavailable("Só a última resposta pode ser regenerada")

        self.db.query(Message).filter(
            Message.conversation_id == conversation.id, Message.id >= message_id
        ).delete(synchronize_session=False)
        conversation.updated_at = utcnow()
        self.db.commit()

        remaining = self.db.query(Message).filter(Message.conversation_id == conversation.id).count()
        if remaining == 0:
            raise ConversationUnavailable("Não sobrou nenhuma mensagem para responder")
        return self._build_turn(conversation)

    def _build_turn(self, conversation: Conversation) -> PreparedTurn:
        provider = conversation.model_config.provider
        # O prompt é composto: regra global (uma só, obedecida por todas) +
        # campos da persona + instruções extras.
        ajustes = SettingsRepository(self.db).get_all()
        context = build_messages(
            system_prompt=compose_system_prompt(
                traits_from_row(conversation.persona),
                ajustes.get("global_persona_rules", ""),
                user_name=ajustes.get("user_display_name", ""),
            ),
            memories=self._memories_for(conversation),
            history=self._history_for(conversation.id),
            context_window=conversation.model_config.context_window,
        )
        config = build_runtime_config(
            provider_kind=provider.kind,
            base_url=provider.base_url,
            api_key=self.cipher.decrypt(provider.api_key_encrypted),
            model_id=conversation.model_config.model_id,
            stored_max_tokens=conversation.model_config.max_tokens,
            temperature=conversation.model_config.temperature,
            top_p=conversation.model_config.top_p,
        )
        return PreparedTurn(
            conversation_id=conversation.id,
            provider_kind=provider.kind,
            config=config,
            adapter=create_adapter(provider.kind),
            messages=context.messages,
            dropped_messages=context.dropped_messages,
            estimated_prompt_tokens=context.estimated_prompt_tokens,
        )

    # --------------------------------------------------------------- streaming

    @staticmethod
    def _sse(event: str, payload: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    @staticmethod
    def _persist(
        turn: PreparedTurn,
        *,
        chunks: list[str],
        latency_ms: int,
        status: MessageStatus,
        error: LLMError | None = None,
        usage: dict[str, int | None] | None = None,
    ) -> int | None:
        """Grava a resposta do assistente numa sessão própria e curta.

        Sessão nova de propósito: a sessão da requisição morre junto com o
        response, e o stream pode durar minutos. Nada aqui roda dentro do laço
        de tokens.
        """
        content = "".join(chunks).strip()
        if not content and status is MessageStatus.COMPLETE:
            content = ""
        usage = usage or {}
        with SessionLocal() as db:
            message = Message(
                conversation_id=turn.conversation_id,
                role=MessageRole.ASSISTANT.value,
                content=content,
                status=status.value,
                error_code=error.code if error else None,
                error_message=error.message if error else None,
                model_id=turn.config.model_id,
                provider_kind=turn.provider_kind,
                latency_ms=latency_ms,
                prompt_tokens=usage.get("prompt_tokens"),
                completion_tokens=usage.get("completion_tokens"),
            )
            db.add(message)
            conversation = db.get(Conversation, turn.conversation_id)
            if conversation:
                conversation.updated_at = utcnow()
            db.commit()
            return message.id

    async def run(self, turn: PreparedTurn) -> AsyncIterator[str]:
        yield self._sse(
            "meta",
            {
                "conversation_id": turn.conversation_id,
                "model": turn.config.model_id,
                "provider": turn.provider_kind,
                "context_trimmed": turn.dropped_messages,
                "estimated_prompt_tokens": turn.estimated_prompt_tokens,
            },
        )
        started = time.perf_counter()
        chunks: list[str] = []

        def elapsed() -> int:
            return round((time.perf_counter() - started) * 1000)

        fluxo = _ComBatimento(turn.adapter.stream(turn.messages, turn.config), HEARTBEAT_SECONDS)
        try:
            async for chunk in fluxo:
                if chunk is _PING:
                    # Comentário SSE: o cliente ignora, mas conta como sinal de vida.
                    yield ": ping\n\n"
                    continue
                chunks.append(chunk)
                yield self._sse("token", {"text": chunk})
        except (asyncio.CancelledError, GeneratorExit):
            fluxo.cancelar()
            # Cliente desistiu. A gravação aqui é síncrona de propósito: num
            # GeneratorExit não existe await possível, e perder o texto parcial
            # é exatamente o defeito que o F3.1 conserta.
            self._persist(turn, chunks=chunks, latency_ms=elapsed(), status=MessageStatus.CANCELLED)
            logger.info("chat cancelado conversation=%s chars=%s", turn.conversation_id, len("".join(chunks)))
            raise
        except LLMError as exc:
            self._persist(turn, chunks=chunks, latency_ms=elapsed(), status=MessageStatus.FAILED, error=exc)
            logger.error(
                "chat falhou conversation=%s provider=%s code=%s detail=%s",
                turn.conversation_id, turn.provider_kind, exc.code, exc.provider_detail,
            )
            # Sem segunda tentativa e sem outro provider: a regra 1 é terminal.
            yield self._sse("error", {**exc.as_payload(), "partial_chars": len("".join(chunks))})
            return
        except Exception as exc:  # pragma: no cover - rede de segurança
            wrapped = ProviderResponseError("Falha inesperada ao falar com o provider.", provider_detail=str(exc))
            self._persist(turn, chunks=chunks, latency_ms=elapsed(), status=MessageStatus.FAILED, error=wrapped)
            logger.exception("chat falhou de forma inesperada conversation=%s", turn.conversation_id)
            yield self._sse("error", {**wrapped.as_payload(), "partial_chars": len("".join(chunks))})
            return

        latency_ms = elapsed()
        usage = getattr(turn.adapter, "last_usage", None)
        message_id = await run_in_threadpool(
            self._persist,
            turn,
            chunks=chunks,
            latency_ms=latency_ms,
            status=MessageStatus.COMPLETE,
            usage=usage,
        )
        logger.info(
            "chat ok conversation=%s provider=%s model=%s latency_ms=%s usage=%s",
            turn.conversation_id, turn.provider_kind, turn.config.model_id, latency_ms, usage,
        )
        yield self._sse("done", {"message_id": message_id, "latency_ms": latency_ms, "usage": usage})
