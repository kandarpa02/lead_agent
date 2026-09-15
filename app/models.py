from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(160))
    niche: Mapped[str] = mapped_column(String(160))
    location: Mapped[str] = mapped_column(String(160))
    country: Mapped[str] = mapped_column(String(120))
    minimum_budget: Mapped[str | None] = mapped_column(String(80), nullable=True)
    primary_channel: Mapped[str] = mapped_column(String(40))
    secondary_channel: Mapped[str | None] = mapped_column(String(40), nullable=True)
    lead_count: Mapped[int] = mapped_column(Integer, default=20)
    operator_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    brief_status: Mapped[str] = mapped_column(String(40), default="Finalized")
    brief: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="Created", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    leads: Mapped[list["Lead"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    runs: Mapped[list["CampaignRun"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    messages: Mapped[list["CampaignMessage"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    briefs: Mapped[list["CampaignBrief"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")


class CampaignMessage(Base):
    __tablename__ = "campaign_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    campaign: Mapped[Campaign] = relationship(back_populates="messages")


class CampaignBrief(Base):
    __tablename__ = "campaign_briefs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    brief_data: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(30), default="Proposed")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    campaign: Mapped[Campaign] = relationship(back_populates="briefs")


class WorkspaceProfile(Base):
    __tablename__ = "workspace_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    person_name: Mapped[str] = mapped_column(String(160), default="")
    business_name: Mapped[str] = mapped_column(String(160), default="")
    service_offer: Mapped[str] = mapped_column(Text, default="")
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    positioning: Mapped[str] = mapped_column(Text, default="")
    tone: Mapped[str] = mapped_column(String(120), default="Warm and conversational")
    call_to_action: Mapped[str] = mapped_column(String(500), default="")
    instagram: Mapped[str | None] = mapped_column(String(500), nullable=True)
    linkedin: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"), index=True)
    business_name: Mapped[str] = mapped_column(String(200), index=True)
    niche: Mapped[str | None] = mapped_column(String(160), nullable=True)
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    website: Mapped[str | None] = mapped_column(String(500), nullable=True)
    instagram: Mapped[str | None] = mapped_column(String(500), nullable=True)
    linkedin: Mapped[str | None] = mapped_column(String(500), nullable=True)
    facebook: Mapped[str | None] = mapped_column(String(500), nullable=True)
    google_maps: Mapped[str | None] = mapped_column(String(500), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="To Research", index=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    recommended_channel: Mapped[str | None] = mapped_column(String(40), nullable=True)
    recommended_channel_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    operator_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    exclusion_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    research: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    outreach_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    contacted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_follow_up_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_contacted_channel: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("campaign_id", "email", name="uq_lead_campaign_email"),)

    campaign: Mapped[Campaign] = relationship(back_populates="leads")
    drafts: Mapped[list["EmailDraft"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    evidence: Mapped[list["ResearchEvidence"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    status_history: Mapped[list["LeadStatusHistory"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    qualifications: Mapped[list["LeadQualification"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    audits: Mapped[list["LeadAudit"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    activities: Mapped[list["LeadActivity"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    follow_ups: Mapped[list["FollowUpTask"]] = relationship(back_populates="lead", cascade="all, delete-orphan")


class DiscoveryQuery(Base):
    __tablename__ = "discovery_queries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(ForeignKey("campaign_runs.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    query: Mapped[str] = mapped_column(String(500))
    purpose: Mapped[str | None] = mapped_column(String(200), nullable=True)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class LeadQualification(Base):
    __tablename__ = "lead_qualifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), index=True)
    score: Mapped[float] = mapped_column(Float)
    priority: Mapped[str] = mapped_column(String(20))
    factors: Mapped[dict[str, Any]] = mapped_column(JSON)
    reasons: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    lead: Mapped[Lead] = relationship(back_populates="qualifications")


class LeadAudit(Base):
    __tablename__ = "lead_audits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), index=True)
    what_is_working: Mapped[str | None] = mapped_column(Text, nullable=True)
    what_is_missing: Mapped[str | None] = mapped_column(Text, nullable=True)
    social_opportunity: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_offer: Mapped[str | None] = mapped_column(Text, nullable=True)
    personalization_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    checklist_items: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    lead: Mapped[Lead] = relationship(back_populates="audits")


class LeadActivity(Base):
    __tablename__ = "lead_activities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), index=True)
    activity_type: Mapped[str] = mapped_column(String(60), index=True)
    channel: Mapped[str | None] = mapped_column(String(40), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    lead: Mapped[Lead] = relationship(back_populates="activities")


class FollowUpTask(Base):
    __tablename__ = "follow_up_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), index=True)
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"), index=True)
    channel: Mapped[str] = mapped_column(String(40))
    due_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(30), default="Pending", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    lead: Mapped[Lead] = relationship(back_populates="follow_ups")


class CampaignRun(Base):
    __tablename__ = "campaign_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    campaign_id: Mapped[str] = mapped_column(ForeignKey("campaigns.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="Queued", index=True)
    current_step: Mapped[str | None] = mapped_column(String(60), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    campaign: Mapped[Campaign] = relationship(back_populates="runs")
    steps: Mapped[list["WorkflowStep"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(ForeignKey("campaign_runs.id"), index=True)
    name: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(30), default="Pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    run: Mapped[CampaignRun] = relationship(back_populates="steps")


class ResearchEvidence(Base):
    __tablename__ = "research_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), index=True)
    url: Mapped[str] = mapped_column(String(1000))
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    text_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    lead: Mapped[Lead] = relationship(back_populates="evidence")


class LeadStatusHistory(Base):
    __tablename__ = "lead_status_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), index=True)
    from_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    to_status: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    lead: Mapped[Lead] = relationship(back_populates="status_history")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class EmailDraft(Base):
    __tablename__ = "email_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    channel: Mapped[str] = mapped_column(String(30), default="email", index=True)
    destination: Mapped[str | None] = mapped_column(String(500), nullable=True)
    recipient: Mapped[str | None] = mapped_column(String(320), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(250), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="Pending Approval", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    lead: Mapped[Lead] = relationship(back_populates="drafts")
    approval: Mapped["Approval | None"] = relationship(back_populates="draft", cascade="all, delete-orphan", uselist=False)
    send: Mapped["EmailSend | None"] = relationship(back_populates="draft", cascade="all, delete-orphan", uselist=False)


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    draft_id: Mapped[str] = mapped_column(ForeignKey("email_drafts.id"), index=True)
    action: Mapped[str] = mapped_column(String(20))
    edited_subject: Mapped[str | None] = mapped_column(String(250), nullable=True)
    edited_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    draft: Mapped[EmailDraft] = relationship(back_populates="approval")


class EmailSend(Base):
    __tablename__ = "email_sends"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    draft_id: Mapped[str] = mapped_column(ForeignKey("email_drafts.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True, index=True, default=lambda: str(uuid4()))
    provider_message_id: Mapped[str | None] = mapped_column(String(250), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="Pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    draft: Mapped[EmailDraft] = relationship(back_populates="send")
