"""Small, typed Fashion tools independent from any particular LLM provider."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError

from app.domain.schemas import LookPlanCreate, OutfitCreate, WardrobeItemCreate, WearEventCreate
from app.fashion.services import FashionService


class ToolInput(BaseModel):
    model_config = {"extra": "forbid"}


class GetWardrobeInput(ToolInput):
    category: str | None = Field(default=None, max_length=60)
    color: str | None = Field(default=None, max_length=80)
    style: str | None = Field(default=None, max_length=100)
    season: str | None = Field(default=None, max_length=30)
    occasion: str | None = Field(default=None, max_length=100)
    query: str | None = Field(default=None, max_length=180)
    limit: int = Field(default=12, ge=1, le=50)


class GetWardrobeItemInput(ToolInput):
    item_id: int = Field(gt=0)


class MixAndMatchInput(ToolInput):
    anchor_item_id: int = Field(gt=0)
    limit: int = Field(default=4, ge=1, le=6)


class ToolUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolResult:
    status: str
    data: dict[str, Any]
    facts: list[dict[str, Any]]
    source_refs: list[dict[str, Any]]
    ui_hints: list[dict[str, Any]]

    def as_model_content(self) -> dict[str, Any]:
        """Compact, factual object passed back to the LLM after execution."""
        return {
            "status": self.status,
            "data": self.data,
            "facts": self.facts,
            "source_refs": self.source_refs,
        }


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    input_model: type[BaseModel]
    execute: Callable[[FashionService, BaseModel], ToolResult]
    version: int = 1

    @property
    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.execute.__doc__ or self.name,
                "parameters": self.input_model.model_json_schema(),
            },
        }


def _get_wardrobe(service: FashionService, data: GetWardrobeInput) -> ToolResult:
    """Read only owned wardrobe items with optional filters."""
    items, total = service.list_items(**data.model_dump(exclude={"limit"}), limit=data.limit)
    payload = {"items": [item.model_dump(mode="json") for item in items], "total": total}
    return ToolResult(
        status="empty" if not items else "ok",
        data=payload,
        facts=[{"kind": "wardrobe_count", "value": total}],
        source_refs=[{"kind": "wardrobe", "ref_id": str(item.id)} for item in items],
        ui_hints=[{"type": "wardrobe_view"}],
    )


def _get_wardrobe_item(service: FashionService, data: GetWardrobeItemInput) -> ToolResult:
    """Read one owned wardrobe item and its usage facts."""
    item = service.item_view(service._item(data.item_id))
    return ToolResult(
        status="ok",
        data={"item": item.model_dump(mode="json")},
        facts=[{"kind": "wear_count", "item_id": item.id, "value": item.wear_count}],
        source_refs=[{"kind": "wardrobe", "ref_id": str(item.id)}],
        ui_hints=[{"type": "wardrobe_item"}],
    )


def _add_wardrobe_item(service: FashionService, data: WardrobeItemCreate) -> ToolResult:
    """Create a wardrobe item after server-side attribute validation."""
    item = service.create_item(data)
    return ToolResult(
        status="ok", data={"item": item.model_dump(mode="json")},
        facts=[{"kind": "wardrobe_item", "id": item.id, "owned": True}],
        source_refs=[{"kind": "wardrobe", "ref_id": str(item.id)}], ui_hints=[{"type": "wardrobe_item"}],
    )


def _get_style_profile(service: FashionService, _data: ToolInput) -> ToolResult:
    """Read explicit preferences and attributable inferred signals."""
    profile = service.profile()
    return ToolResult(
        status="ok", data={"profile": profile.model_dump(mode="json")}, facts=[],
        source_refs=[{"kind": "tool_run", "ref_id": "style_profile"}], ui_hints=[],
    )


def _save_outfit(service: FashionService, data: OutfitCreate) -> ToolResult:
    """Persist an outfit that references owned pieces or explicit external gaps."""
    outfit = service.create_outfit(data)
    refs = [{"kind": "outfit", "ref_id": str(outfit.id)}]
    refs.extend({"kind": "wardrobe", "ref_id": str(item.wardrobe_item_id)} for item in outfit.items if item.wardrobe_item_id)
    return ToolResult(
        status="ok", data={"outfit": outfit.model_dump(mode="json")}, facts=[], source_refs=refs,
        ui_hints=[{"type": "outfit_detail"}],
    )


def _record_wear(service: FashionService, data: WearEventCreate) -> ToolResult:
    """Record actual use of owned wardrobe items without inferring a purchase."""
    event = service.record_wear(data)
    return ToolResult(
        status="ok", data={"wear_event": event.model_dump(mode="json")},
        facts=[{"kind": "wear_event", "id": event.id}], source_refs=[], ui_hints=[],
    )


def _plan_outfit(service: FashionService, data: LookPlanCreate) -> ToolResult:
    """Place a saved outfit on a date in the user's declared timezone."""
    plan = service.create_plan(data)
    return ToolResult(
        status="ok", data={"plan": plan.model_dump(mode="json")}, facts=[],
        source_refs=[{"kind": "outfit", "ref_id": str(plan.outfit_id)}] if plan.outfit_id else [],
        ui_hints=[{"type": "look_calendar"}],
    )


def _mix_and_match(service: FashionService, data: MixAndMatchInput) -> ToolResult:
    """Create deterministic draft combinations anchored to one owned item."""
    anchor = service.item_view(service._item(data.anchor_item_id))
    candidates, _ = service.list_items(limit=50)
    candidates = [item for item in candidates if item.id != anchor.id]
    drafts = []
    for candidate in candidates[:data.limit]:
        drafts.append({
            "title": f"{anchor.name} + {candidate.name}",
            "style": anchor.style or candidate.style,
            "occasion": (anchor.occasions or candidate.occasions or [None])[0],
            "items": [
                {"slot": "base", "wardrobe_item_id": anchor.id},
                {"slot": "combination", "wardrobe_item_id": candidate.id},
            ],
            "reason": "Combinação baseada em peças cadastradas no seu guarda-roupa.",
        })
    return ToolResult(
        status="empty" if not drafts else "ok", data={"outfits": drafts}, facts=[],
        source_refs=[{"kind": "wardrobe", "ref_id": str(anchor.id)}] + [{"kind": "wardrobe", "ref_id": str(candidate.id)} for candidate in candidates[:data.limit]],
        ui_hints=[{"type": "outfit_carousel"}],
    )


def _unavailable(_service: FashionService, _data: ToolInput) -> ToolResult:
    """Return an honest unavailable state until a real external integration exists."""
    return ToolResult(status="unavailable", data={}, facts=[], source_refs=[], ui_hints=[])


class FashionToolRegistry:
    def __init__(self) -> None:
        self._definitions = {
            "get_wardrobe": ToolDefinition("get_wardrobe", GetWardrobeInput, _get_wardrobe),
            "get_wardrobe_item": ToolDefinition("get_wardrobe_item", GetWardrobeItemInput, _get_wardrobe_item),
            "add_wardrobe_item": ToolDefinition("add_wardrobe_item", WardrobeItemCreate, _add_wardrobe_item),
            "get_style_profile": ToolDefinition("get_style_profile", ToolInput, _get_style_profile),
            "mix_and_match": ToolDefinition("mix_and_match", MixAndMatchInput, _mix_and_match),
            "save_outfit": ToolDefinition("save_outfit", OutfitCreate, _save_outfit),
            "record_wear": ToolDefinition("record_wear", WearEventCreate, _record_wear),
            "plan_outfit": ToolDefinition("plan_outfit", LookPlanCreate, _plan_outfit),
            # Declared but unavailable until a real provider is configured.
            "search_fashion_web": ToolDefinition("search_fashion_web", ToolInput, _unavailable),
            "search_products": ToolDefinition("search_products", ToolInput, _unavailable),
            "get_fashion_trends": ToolDefinition("get_fashion_trends", ToolInput, _unavailable),
            "analyze_clothing_image": ToolDefinition("analyze_clothing_image", ToolInput, _unavailable),
        }

    def schemas(self) -> list[dict[str, Any]]:
        return [definition.openai_schema for definition in self._definitions.values()]

    def execute(self, name: str, raw_arguments: dict[str, Any], service: FashionService) -> ToolResult:
        try:
            definition = self._definitions[name]
        except KeyError as exc:
            raise ToolUnavailable(f"Tool Fashion desconhecida: {name}") from exc
        try:
            arguments = definition.input_model.model_validate(raw_arguments)
        except ValidationError as exc:
            raise ToolUnavailable(f"Argumentos inválidos para {name}: {exc.errors()[0]['msg']}") from exc
        return definition.execute(service, arguments)


fashion_tools = FashionToolRegistry()
