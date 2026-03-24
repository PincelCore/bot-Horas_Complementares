"""initial schema"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


submission_status = sa.Enum("DRAFT", "SUBMITTED", "NEEDS_REVIEW", "APPROVED_ESTIMATE", "REJECTED_ESTIMATE", name="submissionstatus")
rule_type = sa.Enum("PER_UNIT", "DECLARED_HOURS", "FIXED_HOURS", "PERCENTAGE_OF_DECLARED", name="ruletype")
quantity_unit = sa.Enum("MONTH", "EVENT", "PRESENTATION", "STAGE", "AWARD", "DAY", "SEMESTER", "COURSE", name="quantityunit")


def upgrade() -> None:
    submission_status.create(op.get_bind(), checkfirst=True)
    rule_type.create(op.get_bind(), checkfirst=True)
    quantity_unit.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("telegram_username", sa.String(length=255), nullable=True),
        sa.Column("bot_state", sa.String(length=50), nullable=False),
        sa.Column("active_submission_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("telegram_chat_id"),
    )
    op.create_table(
        "activity_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("max_hours", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("activity_categories.id"), nullable=False),
        sa.Column("short_description", sa.String(length=255), nullable=False),
        sa.Column("rule_type", rule_type, nullable=False),
        sa.Column("quantity_unit", quantity_unit, nullable=True),
        sa.Column("minimum_quantity", sa.Float(), nullable=True),
        sa.Column("hours_per_unit", sa.Float(), nullable=True),
        sa.Column("fixed_hours", sa.Float(), nullable=True),
        sa.Column("percentage_multiplier", sa.Float(), nullable=True),
        sa.Column("max_hours_per_item", sa.Float(), nullable=True),
        sa.Column("max_hours_per_category", sa.Float(), nullable=True),
        sa.Column("requires_evidence", sa.Boolean(), nullable=False),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False),
        sa.Column("accepted_mime_types", sa.String(length=255), nullable=True),
        sa.Column("documentation_required", sa.Text(), nullable=True),
        sa.Column("special_conditions", sa.Text(), nullable=True),
        sa.Column("source_reference", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("activity_categories.id"), nullable=True),
        sa.Column("rule_id", sa.Integer(), sa.ForeignKey("rules.id"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("declared_quantity", sa.Float(), nullable=True),
        sa.Column("declared_hours", sa.Float(), nullable=True),
        sa.Column("estimated_hours", sa.Float(), nullable=True),
        sa.Column("status", submission_status, nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "evidences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("file_hash"),
        sa.UniqueConstraint("stored_filename"),
    )
    op.create_table(
        "submission_evidences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("submission_id", sa.Integer(), sa.ForeignKey("submissions.id"), nullable=False),
        sa.Column("evidence_id", sa.Integer(), sa.ForeignKey("evidences.id"), nullable=False),
        sa.UniqueConstraint("submission_id", "evidence_id", name="uq_submission_evidence"),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("submission_id", sa.Integer(), sa.ForeignKey("submissions.id"), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("submission_evidences")
    op.drop_table("evidences")
    op.drop_table("submissions")
    op.drop_table("rules")
    op.drop_table("activity_categories")
    op.drop_table("users")
    quantity_unit.drop(op.get_bind(), checkfirst=True)
    rule_type.drop(op.get_bind(), checkfirst=True)
    submission_status.drop(op.get_bind(), checkfirst=True)
