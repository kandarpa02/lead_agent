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
    status: Mapped[str] = mapped_column(String(40), default="Created", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    leads: Mapped[list["Lead"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    runs: Mapped[list["CampaignRun"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")


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
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="To Research", index=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    research: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    outreach_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("campaign_id", "email", name="uq_lead_campaign_email"),)

    campaign: Mapped[Campaign] = relationship(back_populates="leads")
    drafts: Mapped[list["EmailDraft"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    evidence: Mapped[list["ResearchEvidence"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    status_history: Mapped[list["LeadStatusHistory"]] = relationship(back_populates="lead", cascade="all, delete-orphan")


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
    recipient: Mapped[str] = mapped_column(String(320))
    subject: Mapped[str] = mapped_column(String(250))
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
