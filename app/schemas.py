from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    niche: str = Field(min_length=1, max_length=160)
    location: str = Field(min_length=1, max_length=160)
    country: str = Field(min_length=1, max_length=120)
    minimum_budget: str | None = Field(default=None, max_length=80)
    primary_channel: str = Field(default="Instagram", max_length=40)
    secondary_channel: str | None = Field(default=None, max_length=40)
    lead_count: int = Field(default=20, ge=1, le=1000)
    operator_instructions: str | None = Field(default=None, max_length=4000)


class CampaignRead(CampaignCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    status: str
    brief_status: str
    brief: dict[str, Any] | None
    error: str | None


class CampaignMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class CampaignMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    role: str
    content: str
    created_at: datetime


class CampaignBriefUpdate(BaseModel):
    ideal_customer_profile: str
    industry_tiers: list[str] = Field(default_factory=list)
    buying_signals: list[str] = Field(default_factory=list)
    excluded_business_types: list[str] = Field(default_factory=list)
    priority_locations: list[str] = Field(default_factory=list)
    offer_angles: list[str] = Field(default_factory=list)
    proof_points: list[str] = Field(default_factory=list)
    prohibited_claims: list[str] = Field(default_factory=list)
    channel_preferences: list[str] = Field(default_factory=list)
    operator_notes: str | None = None


class CampaignBriefRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    version: int
    brief_data: dict[str, Any]
    status: str
    created_at: datetime


class LeadCreate(BaseModel):
    business_name: str = Field(min_length=1, max_length=200)
    niche: str | None = None
    location: str | None = None
    country: str | None = None
    website: HttpUrl | None = None
    instagram: HttpUrl | None = None
    linkedin: HttpUrl | None = None
    facebook: HttpUrl | None = None
    google_maps: HttpUrl | None = None
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=80)
    source: str | None = Field(default="CSV", max_length=120)


class LeadQualificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lead_id: str
    score: float
    priority: str
    factors: dict[str, Any]
    reasons: list[str] | None
    created_at: datetime


class LeadAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lead_id: str
    what_is_working: str | None
    what_is_missing: str | None
    social_opportunity: str | None
    recommended_offer: str | None
    personalization_note: str | None
    checklist_items: dict[str, Any] | None
    created_at: datetime


class LeadActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lead_id: str
    activity_type: str
    channel: str | None
    description: str
    metadata_json: dict[str, Any] | None
    created_at: datetime


class FollowUpTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lead_id: str
    campaign_id: str
    channel: str
    due_at: datetime
    status: str
    notes: str | None
    created_at: datetime
    completed_at: datetime | None


class LeadRead(LeadCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    status: str
    score: float | None
    priority: str | None
    recommended_channel: str | None
    recommended_channel_reason: str | None
    operator_notes: str | None
    exclusion_reason: str | None
    research: dict[str, Any] | None
    outreach_message: str | None
    contacted_at: datetime | None
    next_follow_up_at: datetime | None
    last_activity_at: datetime | None
    last_contacted_channel: str | None
    created_at: datetime
    updated_at: datetime


class LeadStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=40)
    reason: str | None = Field(default=None, max_length=500)


class LeadDetailUpdate(BaseModel):
    recommended_channel: str | None = None
    priority: str | None = None
    operator_notes: str | None = None
    exclusion_reason: str | None = None
    next_follow_up_at: datetime | None = None


class ApprovalUpdate(BaseModel):
    action: str = Field(pattern="^(approve|reject)$")
    subject: str | None = Field(default=None, max_length=250)
    body: str | None = None


class WorkspaceProfileUpdate(BaseModel):
    person_name: str = Field(min_length=1, max_length=160)
    business_name: str = Field(min_length=1, max_length=160)
    service_offer: str = Field(min_length=1, max_length=4000)
    website: HttpUrl | None = None
    positioning: str = Field(default="", max_length=4000)
    tone: str = Field(default="Warm and conversational", max_length=120)
    call_to_action: str = Field(default="", max_length=500)
    instagram: HttpUrl | None = None
    linkedin: HttpUrl | None = None


class WorkspaceProfileRead(WorkspaceProfileUpdate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    updated_at: datetime


class DraftUpdate(BaseModel):
    subject: str | None = Field(default=None, max_length=250)
    body: str = Field(min_length=1, max_length=10000)


class DraftRevisionRequest(BaseModel):
    instruction: str = Field(min_length=3, max_length=500)


class DraftRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lead_id: str
    version: int
    channel: Literal["instagram", "linkedin", "facebook", "email"]
    destination: str | None
    recipient: str | None
    subject: str | None
    body: str
    status: str
    created_at: datetime


class CampaignDashboardRead(BaseModel):
    campaign: CampaignRead
    latest_run_step: str | None
    counts: dict[str, int]

