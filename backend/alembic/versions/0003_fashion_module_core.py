"""fashion module core persistence

Adds the local owner, wardrobe, outfit, profile, externally observed data and
the persistent UI-object contract. Existing chat data remains unchanged.
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_fashion_module_core"
down_revision = "0002_nome_persona_ativa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=120), server_default="Você", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.execute("INSERT INTO users (id, display_name, created_at) VALUES (1, 'Você', CURRENT_TIMESTAMP)")

    op.create_table(
        "fashion_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=80), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_fashion_assets_owner_id", "fashion_assets", ["owner_id"])
    op.create_index("ix_fashion_assets_owner_created", "fashion_assets", ["owner_id", "created_at"])
    op.create_index("ix_fashion_assets_sha256", "fashion_assets", ["sha256"])

    op.create_table(
        "wardrobe_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("subcategory", sa.String(length=80), nullable=True),
        sa.Column("color", sa.String(length=80), nullable=True),
        sa.Column("material", sa.String(length=100), nullable=True),
        sa.Column("brand", sa.String(length=120), nullable=True),
        sa.Column("size", sa.String(length=40), nullable=True),
        sa.Column("style", sa.String(length=100), nullable=True),
        sa.Column("seasons", sa.JSON(), nullable=False),
        sa.Column("occasions", sa.JSON(), nullable=False),
        sa.Column("formality", sa.Integer(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("image_asset_id", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=20), server_default="manual", nullable=False),
        sa.Column("attribute_confidence", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["image_asset_id"], ["fashion_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in (("ix_wardrobe_items_owner_id", ["owner_id"]), ("ix_wardrobe_items_category", ["category"]), ("ix_wardrobe_items_color", ["color"]), ("ix_wardrobe_items_style", ["style"]), ("ix_wardrobe_items_is_archived", ["is_archived"]), ("ix_wardrobe_items_owner_category", ["owner_id", "category"]), ("ix_wardrobe_items_owner_archived", ["owner_id", "is_archived"])):
        op.create_index(name, "wardrobe_items", columns)

    op.create_table(
        "style_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("explicit_preferences", sa.JSON(), nullable=False),
        sa.Column("inferred_preferences", sa.JSON(), nullable=False),
        sa.Column("restrictions", sa.JSON(), nullable=False),
        sa.Column("default_budget", sa.String(length=32), nullable=True),
        sa.Column("default_currency", sa.String(length=3), server_default="BRL", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_style_profiles_owner_id", "style_profiles", ["owner_id"], unique=True)

    op.create_table(
        "style_signals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("signal_type", sa.String(length=40), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("attribute", sa.String(length=120), nullable=True),
        sa.Column("value", sa.String(length=240), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in (("ix_style_signals_owner_id", ["owner_id"]), ("ix_style_signals_signal_type", ["signal_type"]), ("ix_style_signals_is_revoked", ["is_revoked"]), ("ix_style_signals_owner_created", ["owner_id", "created_at"])):
        op.create_index(name, "style_signals", columns)

    op.create_table(
        "outfits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("style", sa.String(length=100), nullable=True),
        sa.Column("occasion", sa.String(length=100), nullable=True),
        sa.Column("explanation", sa.Text(), server_default="", nullable=False),
        sa.Column("source", sa.String(length=20), server_default="manual", nullable=False),
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in (("ix_outfits_owner_id", ["owner_id"]), ("ix_outfits_is_archived", ["is_archived"]), ("ix_outfits_owner_archived", ["owner_id", "is_archived"])):
        op.create_index(name, "outfits", columns)

    op.create_table(
        "outfit_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("outfit_id", sa.Integer(), nullable=False),
        sa.Column("wardrobe_item_id", sa.Integer(), nullable=True),
        sa.Column("slot", sa.String(length=50), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("external_snapshot", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["outfit_id"], ["outfits.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["wardrobe_item_id"], ["wardrobe_items.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("outfit_id", "slot", name="uq_outfit_slot"),
    )
    op.create_index("ix_outfit_items_outfit_id", "outfit_items", ["outfit_id"])
    op.create_index("ix_outfit_items_wardrobe_item_id", "outfit_items", ["wardrobe_item_id"])

    op.create_table(
        "wear_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("outfit_id", sa.Integer(), nullable=True),
        sa.Column("item_ids", sa.JSON(), nullable=False),
        sa.Column("worn_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=True),
        sa.ForeignKeyConstraint(["outfit_id"], ["outfits.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_wear_events_owner_id", "wear_events", ["owner_id"])
    op.create_index("ix_wear_events_owner_worn", "wear_events", ["owner_id", "worn_at"])

    op.create_table(
        "look_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("outfit_id", sa.Integer(), nullable=True),
        sa.Column("planned_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(length=64), server_default="America/Sao_Paulo", nullable=False),
        sa.Column("event_name", sa.String(length=180), server_default="", nullable=False),
        sa.Column("occasion", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="planned", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["outfit_id"], ["outfits.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_look_plans_owner_id", "look_plans", ["owner_id"])
    op.create_index("ix_look_plans_planned_for", "look_plans", ["planned_for"])
    op.create_index("ix_look_plans_owner_date", "look_plans", ["owner_id", "planned_for"])

    op.create_table(
        "product_observations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=120), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("canonical_url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in (("ix_product_observations_owner_id", ["owner_id"]), ("ix_product_observations_canonical_url", ["canonical_url"]), ("ix_product_observations_owner_fetched", ["owner_id", "fetched_at"])):
        op.create_index(name, "product_observations", columns)

    op.create_table(
        "trend_observations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("source_name", sa.String(length=120), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trend_observations_owner_id", "trend_observations", ["owner_id"])
    op.create_index("ix_trend_observations_owner_fetched", "trend_observations", ["owner_id", "fetched_at"])

    op.create_table(
        "tool_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("tool_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="completed", nullable=False),
        sa.Column("arguments", sa.JSON(), nullable=False),
        sa.Column("result_refs", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_tool_runs_owner_id", "tool_runs", ["owner_id"])
    op.create_index("ix_tool_runs_conversation_created", "tool_runs", ["conversation_id", "created_at"])

    op.create_table(
        "message_ui_objects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("object_type", sa.String(length=80), nullable=False),
        sa.Column("schema_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("source_refs", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("message_id", "position", name="uq_message_ui_object_position"),
    )
    op.create_index("ix_message_ui_objects_message_id", "message_ui_objects", ["message_id"])
    op.create_index("ix_message_ui_objects_object_type", "message_ui_objects", ["object_type"])

    op.create_table(
        "external_service_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("service_kind", sa.String(length=80), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("secret_encrypted", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("service_kind"),
    )


def downgrade() -> None:
    for table in (
        "external_service_configs", "message_ui_objects", "tool_runs", "trend_observations",
        "product_observations", "look_plans", "wear_events", "outfit_items", "outfits",
        "style_signals", "style_profiles", "wardrobe_items", "fashion_assets", "users",
    ):
        op.drop_table(table)
