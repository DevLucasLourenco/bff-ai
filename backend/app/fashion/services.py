from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.domain.models import (
    FashionAsset,
    LookPlan,
    Outfit,
    OutfitFeedback,
    OutfitItem,
    StyleProfile,
    StyleSignal,
    ToolRun,
    WardrobeItem,
    WearEvent,
)
from app.domain.schemas import (
    ExternalImageImport,
    LookPlanCreate,
    LookPlanRead,
    OutfitCreate,
    OutfitRead,
    StyleProfileRead,
    StyleProfileUpdate,
    WardrobeItemCreate,
    WardrobeItemRead,
    WardrobeItemUpdate,
    WearEventCreate,
    WearEventRead,
)


class FashionNotFound(LookupError):
    pass


class FashionConflict(ValueError):
    pass


def _asset_view(asset: FashionAsset | None) -> dict[str, Any] | None:
    if asset is None:
        return None
    return {
        "id": asset.id,
        "mime_type": asset.mime_type,
        "width": asset.width,
        "height": asset.height,
        "byte_size": asset.byte_size,
        "created_at": asset.created_at,
        "url": f"/api/fashion/assets/{asset.id}",
    }


class FashionService:
    """Owner-scoped business operations shared by REST actions and LLM tools."""

    def __init__(self, db: Session, owner_id: int) -> None:
        self.db = db
        self.owner_id = owner_id

    def _asset(self, asset_id: int | None) -> FashionAsset | None:
        if asset_id is None:
            return None
        asset = self.db.get(FashionAsset, asset_id)
        if asset is None or asset.owner_id != self.owner_id:
            raise FashionNotFound("Imagem não encontrada")
        return asset

    def _item(self, item_id: int, *, include_archived: bool = False) -> WardrobeItem:
        item = self.db.get(WardrobeItem, item_id)
        if item is None or item.owner_id != self.owner_id or (item.is_archived and not include_archived):
            raise FashionNotFound("Peça não encontrada")
        return item

    def _outfit(self, outfit_id: int, *, include_archived: bool = False) -> Outfit:
        outfit = self.db.get(Outfit, outfit_id)
        if outfit is None or outfit.owner_id != self.owner_id or (outfit.is_archived and not include_archived):
            raise FashionNotFound("Look não encontrado")
        return outfit

    def _wear_stats(self, item_id: int) -> tuple[int, datetime | None]:
        events = self.db.query(WearEvent).filter(WearEvent.owner_id == self.owner_id).all()
        relevant = [event for event in events if item_id in (event.item_ids or [])]
        latest = max((event.worn_at for event in relevant), default=None)
        return len(relevant), latest

    def item_view(self, item: WardrobeItem) -> WardrobeItemRead:
        asset = self._asset(item.image_asset_id) if item.image_asset_id else None
        wear_count, last_worn_at = self._wear_stats(item.id)
        return WardrobeItemRead(
            id=item.id,
            name=item.name,
            category=item.category,
            subcategory=item.subcategory,
            color=item.color,
            material=item.material,
            brand=item.brand,
            size=item.size,
            style=item.style,
            seasons=item.seasons or [],
            occasions=item.occasions or [],
            formality=item.formality,
            tags=item.tags or [],
            image_asset_id=item.image_asset_id,
            source=item.source,
            collection_status=item.collection_status,
            external_url=item.external_url,
            external_domain=item.external_domain,
            external_captured_at=item.external_captured_at,
            attribute_confidence=item.attribute_confidence or {},
            revision=item.revision,
            is_archived=item.is_archived,
            created_at=item.created_at,
            updated_at=item.updated_at,
            image=_asset_view(asset),
            wear_count=wear_count,
            last_worn_at=last_worn_at,
        )

    def list_items(
        self,
        *,
        category: str | None = None,
        color: str | None = None,
        style: str | None = None,
        season: str | None = None,
        occasion: str | None = None,
        collection_status: str | None = None,
        query: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[WardrobeItemRead], int]:
        rows = self.db.query(WardrobeItem).filter(
            WardrobeItem.owner_id == self.owner_id,
            WardrobeItem.is_archived.is_(False),
        )
        if category:
            rows = rows.filter(WardrobeItem.category == category)
        if color:
            rows = rows.filter(WardrobeItem.color == color)
        if style:
            rows = rows.filter(WardrobeItem.style == style)
        if collection_status:
            rows = rows.filter(WardrobeItem.collection_status == collection_status)
        candidates = rows.order_by(WardrobeItem.updated_at.desc(), WardrobeItem.id.desc()).all()
        normalized_query = (query or "").strip().casefold()

        def matches(item: WardrobeItem) -> bool:
            if season and season not in (item.seasons or []):
                return False
            if occasion and occasion not in (item.occasions or []):
                return False
            if normalized_query:
                haystack = " ".join(
                    str(value or "") for value in (
                        item.name, item.category, item.subcategory, item.color, item.brand, item.style, *(item.tags or []),
                    )
                ).casefold()
                return normalized_query in haystack
            return True

        filtered = [item for item in candidates if matches(item)]
        return [self.item_view(item) for item in filtered[offset:offset + limit]], len(filtered)

    def create_item(self, payload: WardrobeItemCreate) -> WardrobeItemRead:
        if payload.idempotency_key:
            prior = self.db.query(ToolRun).filter_by(idempotency_key=payload.idempotency_key).one_or_none()
            if prior and prior.tool_name == "add_wardrobe_item" and prior.result_refs:
                return self.item_view(self._item(int(prior.result_refs[0]["id"])))
        asset = self._asset(payload.image_asset_id)
        if asset and asset.source_url:
            existing = self.external_item_for_url(asset.source_url)
            if existing:
                return existing
        values = payload.model_dump(exclude={"idempotency_key"})
        if asset and asset.source_url:
            values.update(
                source="external", external_url=asset.source_url,
                external_domain=asset.source_domain, external_captured_at=asset.created_at,
            )
        values["seasons"] = [value.strip() for value in payload.seasons if value.strip()]
        values["occasions"] = [value.strip() for value in payload.occasions if value.strip()]
        values["tags"] = [value.strip() for value in payload.tags if value.strip()]
        item = WardrobeItem(owner_id=self.owner_id, **values)
        self.db.add(item)
        self.db.flush()
        if payload.idempotency_key:
            self.db.add(ToolRun(
                owner_id=self.owner_id,
                tool_name="add_wardrobe_item",
                arguments={"name": payload.name, "category": payload.category},
                result_refs=[{"kind": "wardrobe", "id": item.id}],
                idempotency_key=payload.idempotency_key,
            ))
        self.db.commit()
        self.db.refresh(item)
        return self.item_view(item)

    def imported_external_item(self, idempotency_key: str | None) -> WardrobeItemRead | None:
        if not idempotency_key:
            return None
        prior = self.db.query(ToolRun).filter_by(idempotency_key=idempotency_key).one_or_none()
        if prior and prior.tool_name == "import_external_image" and prior.result_refs:
            return self.item_view(self._item(int(prior.result_refs[0]["id"])))
        return None

    def external_item_for_url(self, canonical_url: str) -> WardrobeItemRead | None:
        item = self.db.query(WardrobeItem).filter_by(
            owner_id=self.owner_id, source="external", external_url=canonical_url,
        ).one_or_none()
        return self.item_view(item) if item else None

    def create_external_image_item(
        self, payload: ExternalImageImport, *, image_asset_id: int, canonical_url: str, domain: str, captured_at: datetime,
    ) -> WardrobeItemRead:
        prior = self.imported_external_item(payload.idempotency_key)
        if prior:
            return prior
        self._asset(image_asset_id)
        item = WardrobeItem(
            owner_id=self.owner_id, name=payload.name, category=payload.category, color=payload.color,
            style=payload.style, brand=payload.brand, tags=[tag.strip() for tag in payload.tags if tag.strip()],
            image_asset_id=image_asset_id, source="external", collection_status=payload.collection_status,
            external_url=canonical_url, external_domain=domain, external_captured_at=captured_at,
        )
        self.db.add(item)
        self.db.flush()
        if payload.idempotency_key:
            self.db.add(ToolRun(
                owner_id=self.owner_id, tool_name="import_external_image",
                arguments={"url": canonical_url, "name": payload.name},
                result_refs=[{"kind": "wardrobe", "id": item.id}], idempotency_key=payload.idempotency_key,
            ))
        self.db.commit()
        self.db.refresh(item)
        return self.item_view(item)

    def update_item(self, item_id: int, payload: WardrobeItemUpdate) -> WardrobeItemRead:
        item = self._item(item_id)
        if item.revision != payload.expected_revision:
            raise FashionConflict("Esta peça foi alterada em outra tela. Recarregue antes de salvar.")
        data = payload.model_dump(exclude_unset=True, exclude={"expected_revision"})
        if "image_asset_id" in data:
            self._asset(data["image_asset_id"])
        for key, value in data.items():
            if key in {"seasons", "occasions", "tags"} and value is not None:
                value = [entry.strip() for entry in value if entry.strip()]
            setattr(item, key, value)
        item.revision += 1
        self.db.commit()
        self.db.refresh(item)
        return self.item_view(item)

    def archive_item(self, item_id: int, expected_revision: int) -> WardrobeItemRead:
        item = self._item(item_id)
        if item.revision != expected_revision:
            raise FashionConflict("Esta peça foi alterada em outra tela. Recarregue antes de arquivar.")
        item.is_archived = True
        item.revision += 1
        self.db.commit()
        self.db.refresh(item)
        return self.item_view(item)

    def profile(self) -> StyleProfileRead:
        profile = self.db.query(StyleProfile).filter_by(owner_id=self.owner_id).one_or_none()
        if profile is None:
            profile = StyleProfile(owner_id=self.owner_id)
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
        signals = self.db.query(StyleSignal).filter_by(owner_id=self.owner_id).order_by(StyleSignal.created_at.desc()).limit(30).all()
        return StyleProfileRead(
            id=profile.id,
            explicit_preferences=profile.explicit_preferences or {},
            inferred_preferences=profile.inferred_preferences or {},
            restrictions=profile.restrictions or {},
            default_budget=profile.default_budget,
            default_currency=profile.default_currency,
            revision=profile.revision,
            updated_at=profile.updated_at,
            signals=signals,
        )

    def update_profile(self, payload: StyleProfileUpdate) -> StyleProfileRead:
        profile = self.db.query(StyleProfile).filter_by(owner_id=self.owner_id).one_or_none()
        if profile is None:
            profile = StyleProfile(owner_id=self.owner_id)
            self.db.add(profile)
            self.db.flush()
        if payload.expected_revision is not None and profile.revision != payload.expected_revision:
            raise FashionConflict("Seu perfil foi alterado em outra tela. Recarregue antes de salvar.")
        for key, value in payload.model_dump(exclude_unset=True, exclude={"expected_revision"}).items():
            setattr(profile, key, value)
        profile.revision += 1
        self.db.commit()
        return self.profile()

    def create_outfit(self, payload: OutfitCreate) -> OutfitRead:
        if len({entry.slot for entry in payload.items}) != len(payload.items):
            raise FashionConflict("Cada slot do look só pode aparecer uma vez")
        if payload.idempotency_key:
            prior = self.db.query(ToolRun).filter_by(idempotency_key=payload.idempotency_key).one_or_none()
            if prior and prior.tool_name == "save_outfit" and prior.result_refs:
                return self.outfit_view(self._outfit(int(prior.result_refs[0]["id"])))
        outfit = Outfit(
            owner_id=self.owner_id,
            title=payload.title,
            style=payload.style,
            occasion=payload.occasion,
            explanation=payload.explanation,
        )
        self.db.add(outfit)
        self.db.flush()
        for position, entry in enumerate(payload.items):
            if entry.wardrobe_item_id:
                item = self._item(entry.wardrobe_item_id)
                if item.collection_status != "owned":
                    raise FashionConflict("Só peças marcadas como possuídas entram em um look salvo.")
            if entry.wardrobe_item_id is None and entry.external_snapshot is None:
                raise FashionConflict("Cada slot precisa de uma peça ou de uma lacuna externa")
            self.db.add(OutfitItem(
                outfit_id=outfit.id,
                slot=entry.slot,
                position=position,
                wardrobe_item_id=entry.wardrobe_item_id,
                external_snapshot=entry.external_snapshot,
            ))
        if payload.idempotency_key:
            self.db.add(ToolRun(
                owner_id=self.owner_id,
                tool_name="save_outfit",
                arguments={"title": payload.title},
                result_refs=[{"kind": "outfit", "id": outfit.id}],
                idempotency_key=payload.idempotency_key,
            ))
        self.db.commit()
        return self.outfit_view(outfit)

    def outfit_view(self, outfit: Outfit) -> OutfitRead:
        entries = self.db.query(OutfitItem).filter_by(outfit_id=outfit.id).order_by(OutfitItem.position).all()
        items = []
        for entry in entries:
            wardrobe_item = self._item(entry.wardrobe_item_id, include_archived=True) if entry.wardrobe_item_id else None
            items.append({
                "id": entry.id,
                "slot": entry.slot,
                "wardrobe_item_id": entry.wardrobe_item_id,
                "external_snapshot": entry.external_snapshot,
                "position": entry.position,
                "wardrobe_item": self.item_view(wardrobe_item) if wardrobe_item else None,
            })
        return OutfitRead(
            id=outfit.id, title=outfit.title, style=outfit.style, occasion=outfit.occasion,
            explanation=outfit.explanation, source=outfit.source, revision=outfit.revision,
            is_archived=outfit.is_archived, created_at=outfit.created_at, updated_at=outfit.updated_at, items=items,
        )

    def feedback(self, outfit_id: int, *, liked: bool, reason: str | None) -> None:
        self._outfit(outfit_id)
        self.db.add(OutfitFeedback(owner_id=self.owner_id, outfit_id=outfit_id, liked=liked, reason=reason))
        self.db.add(StyleSignal(
            owner_id=self.owner_id,
            signal_type="saved" if liked else "rejected",
            entity_type="outfit",
            entity_id=outfit_id,
            attribute="feedback",
            value=reason,
            weight=1 if liked else -1,
        ))
        self.db.commit()

    def record_wear(self, payload: WearEventCreate) -> WearEventRead:
        if not payload.item_ids and payload.outfit_id is None:
            raise FashionConflict("Informe pelo menos uma peça ou um look")
        if payload.idempotency_key:
            existing = self.db.query(WearEvent).filter_by(idempotency_key=payload.idempotency_key).one_or_none()
            if existing:
                return WearEventRead.model_validate(existing)
        item_ids = list(dict.fromkeys(payload.item_ids))
        if payload.outfit_id:
            outfit = self._outfit(payload.outfit_id)
            outfit_ids = [entry.wardrobe_item_id for entry in self.db.query(OutfitItem).filter_by(outfit_id=outfit.id) if entry.wardrobe_item_id]
            item_ids = list(dict.fromkeys([*item_ids, *outfit_ids]))
        for item_id in item_ids:
            self._item(item_id)
        event = WearEvent(
            owner_id=self.owner_id,
            outfit_id=payload.outfit_id,
            item_ids=item_ids,
            worn_at=payload.worn_at or datetime.now().astimezone(),
            idempotency_key=payload.idempotency_key,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return WearEventRead.model_validate(event)

    def create_plan(self, payload: LookPlanCreate) -> LookPlanRead:
        if payload.outfit_id:
            self._outfit(payload.outfit_id)
        plan = LookPlan(owner_id=self.owner_id, **payload.model_dump())
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return LookPlanRead.model_validate(plan)

    def list_plans(self, starts_at: datetime, ends_at: datetime) -> list[LookPlanRead]:
        rows = self.db.query(LookPlan).filter(
            LookPlan.owner_id == self.owner_id,
            LookPlan.planned_for >= starts_at,
            LookPlan.planned_for <= ends_at,
        ).order_by(LookPlan.planned_for).all()
        return [LookPlanRead.model_validate(row) for row in rows]
