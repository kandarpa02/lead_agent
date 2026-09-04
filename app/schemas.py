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


class CampaignRead(CampaignCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    status: str
    error: str | None


class LeadCreate(BaseModel):
    business_name: str = Field(min_length=1, max_length=200)
    niche: str | None = None
    location: str | None = None
    country: str | None = None
    website: HttpUrl | None = None
    instagram: HttpUrl | None = None
    linkedin: HttpUrl | None = None
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=80)
    source: str | None = Field(default="CSV", max_length=120)


class LeadRead(LeadCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    campaign_id: str
    status: str
    score: float | None
    priority: str | None
    research: dict[str, Any] | None
    outreach_message: str | None
    created_at: datetime
    updated_at: datetime


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
    channel: Literal["instagram", "linkedin", "email"]
    destination: str | None
    recipient: str | None
    subject: str | None
    body: str
    status: str
    created_at: datetime
