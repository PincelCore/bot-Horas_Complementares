"""add file content to evidences"""

from alembic import op
import sqlalchemy as sa


revision = "0002_add_file_content_to_evidences"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("evidences", sa.Column("file_content", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("evidences", "file_content")
