"""add received documents and evidence source reference"""

from alembic import op
import sqlalchemy as sa


revision = "0003_received_documents_and_storage_metadata"
down_revision = "0002_file_content"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "received_documents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("submission_id", sa.Integer(), sa.ForeignKey("submissions.id"), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("plausibility_status", sa.String(length=30), nullable=False),
        sa.Column("plausibility_score", sa.Integer(), nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column("evidences", sa.Column("source_document_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_evidences_source_document_id",
        "evidences",
        "received_documents",
        ["source_document_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_evidences_source_document_id", "evidences", type_="foreignkey")
    op.drop_column("evidences", "source_document_id")
    op.drop_table("received_documents")
