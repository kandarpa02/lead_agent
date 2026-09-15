"""Add PDF prospecting methodology tables and columns."""
from alembic import op
import sqlalchemy as sa


revision = "0003_pdf_prospecting_workflow"
down_revision = "0002_manual_outreach"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("campaign_messages"):
        op.create_table(
            "campaign_messages",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("campaign_id", sa.String(length=36), sa.ForeignKey("campaigns.id"), index=True, nullable=False),
            sa.Column("role", sa.String(length=20), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if not inspector.has_table("campaign_briefs"):
        op.create_table(
            "campaign_briefs",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("campaign_id", sa.String(length=36), sa.ForeignKey("campaigns.id"), index=True, nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("brief_data", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="Proposed"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if not inspector.has_table("discovery_queries"):
        op.create_table(
            "discovery_queries",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("run_id", sa.String(length=36), sa.ForeignKey("campaign_runs.id"), index=True, nullable=False),
            sa.Column("provider", sa.String(length=40), nullable=False),
            sa.Column("query", sa.String(length=500), nullable=False),
            sa.Column("purpose", sa.String(length=200), nullable=True),
            sa.Column("result_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if not inspector.has_table("lead_qualifications"):
        op.create_table(
            "lead_qualifications",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("lead_id", sa.String(length=36), sa.ForeignKey("leads.id"), index=True, nullable=False),
            sa.Column("score", sa.Float(), nullable=False),
            sa.Column("priority", sa.String(length=20), nullable=False),
            sa.Column("factors", sa.JSON(), nullable=False),
            sa.Column("reasons", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if not inspector.has_table("lead_audits"):
        op.create_table(
            "lead_audits",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("lead_id", sa.String(length=36), sa.ForeignKey("leads.id"), index=True, nullable=False),
            sa.Column("what_is_working", sa.Text(), nullable=True),
            sa.Column("what_is_missing", sa.Text(), nullable=True),
            sa.Column("social_opportunity", sa.Text(), nullable=True),
            sa.Column("recommended_offer", sa.Text(), nullable=True),
            sa.Column("personalization_note", sa.Text(), nullable=True),
            sa.Column("checklist_items", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if not inspector.has_table("lead_activities"):
        op.create_table(
            "lead_activities",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("lead_id", sa.String(length=36), sa.ForeignKey("leads.id"), index=True, nullable=False),
            sa.Column("activity_type", sa.String(length=60), index=True, nullable=False),
            sa.Column("channel", sa.String(length=40), nullable=True),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        )

    if not inspector.has_table("follow_up_tasks"):
        op.create_table(
            "follow_up_tasks",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("lead_id", sa.String(length=36), sa.ForeignKey("leads.id"), index=True, nullable=False),
            sa.Column("campaign_id", sa.String(length=36), sa.ForeignKey("campaigns.id"), index=True, nullable=False),
            sa.Column("channel", sa.String(length=40), nullable=False),
            sa.Column("due_at", sa.DateTime(), index=True, nullable=False),
            sa.Column("status", sa.String(length=30), index=True, nullable=False, server_default="Pending"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
        )

    campaign_cols = {col["name"] for col in inspector.get_columns("campaigns")}
    with op.batch_alter_table("campaigns") as batch:
        if "operator_instructions" not in campaign_cols:
            batch.add_column(sa.Column("operator_instructions", sa.Text(), nullable=True))
        if "brief_status" not in campaign_cols:
            batch.add_column(sa.Column("brief_status", sa.String(length=40), nullable=False, server_default="Finalized"))
        if "brief" not in campaign_cols:
            batch.add_column(sa.Column("brief", sa.JSON(), nullable=True))

    lead_cols = {col["name"] for col in inspector.get_columns("leads")}
    with op.batch_alter_table("leads") as batch:
        if "facebook" not in lead_cols:
            batch.add_column(sa.Column("facebook", sa.String(length=500), nullable=True))
        if "google_maps" not in lead_cols:
            batch.add_column(sa.Column("google_maps", sa.String(length=500), nullable=True))
        if "recommended_channel" not in lead_cols:
            batch.add_column(sa.Column("recommended_channel", sa.String(length=40), nullable=True))
        if "recommended_channel_reason" not in lead_cols:
            batch.add_column(sa.Column("recommended_channel_reason", sa.String(length=500), nullable=True))
        if "operator_notes" not in lead_cols:
            batch.add_column(sa.Column("operator_notes", sa.Text(), nullable=True))
        if "exclusion_reason" not in lead_cols:
            batch.add_column(sa.Column("exclusion_reason", sa.String(length=500), nullable=True))
        if "next_follow_up_at" not in lead_cols:
            batch.add_column(sa.Column("next_follow_up_at", sa.DateTime(), nullable=True))
        if "last_activity_at" not in lead_cols:
            batch.add_column(sa.Column("last_activity_at", sa.DateTime(), nullable=True))
        if "last_contacted_channel" not in lead_cols:
            batch.add_column(sa.Column("last_contacted_channel", sa.String(length=40), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("leads") as batch:
        batch.drop_column("last_contacted_channel")
        batch.drop_column("last_activity_at")
        batch.drop_column("next_follow_up_at")
        batch.drop_column("exclusion_reason")
        batch.drop_column("operator_notes")
        batch.drop_column("recommended_channel_reason")
        batch.drop_column("recommended_channel")
        batch.drop_column("google_maps")
        batch.drop_column("facebook")

    with op.batch_alter_table("campaigns") as batch:
        batch.drop_column("brief")
        batch.drop_column("brief_status")
        batch.drop_column("operator_instructions")

    op.drop_table("follow_up_tasks")
    op.drop_table("lead_activities")
    op.drop_table("lead_audits")
    op.drop_table("lead_qualifications")
    op.drop_table("discovery_queries")
    op.drop_table("campaign_briefs")
    op.drop_table("campaign_messages")
