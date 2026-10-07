"""Add configurable OpenAI-compatible AI provider settings."""
import sqlalchemy as sa

from alembic import op

revision = "0004_ai_provider_configuration"
down_revision = "0003_pdf_prospecting_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("ai_provider_configuration"):
        op.create_table(
            "ai_provider_configuration",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("base_url", sa.String(length=1000), nullable=False),
            sa.Column("api_key", sa.Text(), nullable=False),
            sa.Column("selected_model", sa.String(length=500), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("ai_provider_configuration"):
        op.drop_table("ai_provider_configuration")
