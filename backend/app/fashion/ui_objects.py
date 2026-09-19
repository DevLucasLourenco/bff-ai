from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.domain.models import MessageUiObject
from app.domain.schemas import ChatUiObjectRead
from app.fashion.tools import ToolResult


def build_objects(result: ToolResult) -> list[dict[str, Any]]:
    """Convert factual tool output into server-owned visual snapshots."""
    objects: list[dict[str, Any]] = []
    for hint in result.ui_hints:
        object_type = hint.get("type")
        if object_type not in {
            "wardrobe_view", "wardrobe_item", "outfit_carousel", "outfit_detail",
            "product_carousel", "trend_board", "look_calendar",
        }:
            continue
        payload = {
            "title": {
                "wardrobe_view": "Meu guarda-roupa",
                "wardrobe_item": "Peça do guarda-roupa",
                "outfit_carousel": "Combinações",
                "outfit_detail": "Look salvo",
                "product_carousel": "Produtos encontrados",
                "trend_board": "Tendências",
                "look_calendar": "Agenda de looks",
            }[object_type],
            "subtitle": "Dados atualizados agora",
            "data": result.data,
            "actions": hint.get("actions", []),
            "metadata": {"state": "snapshot", "created_at": datetime.now(timezone.utc).isoformat()},
        }
        objects.append({"type": object_type, "payload": payload, "source_refs": result.source_refs})
    return objects


def persist_objects(db: Session, message_id: int, result: ToolResult) -> list[ChatUiObjectRead]:
    rows: list[MessageUiObject] = []
    next_position = db.query(MessageUiObject).filter_by(message_id=message_id).count()
    for position, item in enumerate(build_objects(result), start=next_position):
        row = MessageUiObject(
            message_id=message_id,
            position=position,
            object_type=item["type"],
            payload=item["payload"],
            source_refs=item["source_refs"],
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return [ChatUiObjectRead.model_validate(row) for row in rows]


def object_view(row: MessageUiObject) -> ChatUiObjectRead:
    return ChatUiObjectRead.model_validate(row)
