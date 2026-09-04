"""Add workspace profile and manual social outreach fields."""
from alembic import op
import sqlalchemy as sa


revision = "0002_manual_outreach"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("workspace_profiles"):
        op.create_table(
            "workspace_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("person_name", sa.String(length=160), nullable=False, server_default=""),
            sa.Column("business_name", sa.String(length=160), nullable=False, server_default=""),
            sa.Column("service_offer", sa.Text(), nullable=False, server_default=""),
            sa.Column("website", sa.String(length=500), nullable=True),
            sa.Column("positioning", sa.Text(), nullable=False, server_default=""),
            sa.Column("tone", sa.String(length=120), nullable=False, server_default="Warm and conversational"),
            sa.Column("call_to_action", sa.String(length=500), nullable=False, server_default=""),
            sa.Column("instagram", sa.String(length=500), nullable=True),
            sa.Column("linkedin", sa.String(length=500), nullable=True),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )
    lead_columns = {column["name"] for column in inspector.get_columns("leads")}
    with op.batch_alter_table("leads") as batch:
        if "linkedin" not in lead_columns:
            batch.add_column(sa.Column("linkedin", sa.String(length=500), nullable=True))
        if "contacted_at" not in lead_columns:
            batch.add_column(sa.Column("contacted_at", sa.DateTime(), nullable=True))
    draft_columns = {column["name"]: column for column in inspector.get_columns("email_drafts")}
    with op.batch_alter_table("email_drafts") as batch:
        if "channel" not in draft_columns:
            batch.add_column(sa.Column("channel", sa.String(length=30), nullable=False, server_default="email"))
        if "destination" not in draft_columns:
            batch.add_column(sa.Column("destination", sa.String(length=500), nullable=True))
        if draft_columns.get("recipient", {}).get("nullable") is False:
            batch.alter_column("recipient", existing_type=sa.String(length=320), nullable=True)
        if draft_columns.get("subject", {}).get("nullable") is False:
            batch.alter_column("subject", existing_type=sa.String(length=250), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("email_drafts") as batch:
        batch.alter_column("subject", existing_type=sa.String(length=250), nullable=False)
        batch.alter_column("recipient", existing_type=sa.String(length=320), nullable=False)
        batch.drop_column("destination")
        batch.drop_column("channel")
    with op.batch_alter_table("leads") as batch:
        batch.drop_column("contacted_at")
        batch.drop_column("linkedin")
    op.drop_table("workspace_profiles")