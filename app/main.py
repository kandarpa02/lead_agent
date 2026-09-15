from uuid import uuid4
from datetime import datetime
from typing import Any
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents_workflow import draft_outreach, generate_campaign_brief
from app.config import get_settings
from app.constants import VALID_LEAD_TRANSITIONS, LeadStatus
from app.database import get_db
from app.gmail import GmailError, send_approved_email
from app.models import (
    Approval,
    AuditEvent,
    Campaign,
    CampaignBrief,
    CampaignMessage,
    CampaignRun,
    EmailDraft,
    EmailSend,
    FollowUpTask,
    Lead,
    LeadActivity,
    LeadAudit,
    LeadQualification,
    LeadStatusHistory,
    WorkflowStep,
    WorkspaceProfile,
)
from app.schemas import (
    ApprovalUpdate,
    CampaignBriefRead,
    CampaignBriefUpdate,
    CampaignCreate,
    CampaignDashboardRead,
    CampaignMessageCreate,
    CampaignMessageRead,
    CampaignRead,
    DraftRead,
    DraftRevisionRequest,
    DraftUpdate,
    FollowUpTaskRead,
    LeadActivityRead,
    LeadAuditRead,
    LeadCreate,
    LeadDetailUpdate,
    LeadQualificationRead,
    LeadRead,
    LeadStatusUpdate,
    WorkspaceProfileRead,
    WorkspaceProfileUpdate,
)

app = FastAPI(title=get_settings().app_name, version="0.1.0")
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse("frontend/index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "agent_runtime": "openai-agents-sdk", "model_provider": "ollama"}


@app.get("/health/live", include_in_schema=False)
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", include_in_schema=False)
def ready(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(select(1))
    return {"status": "ready"}


@app.get("/api/workspace", response_model=WorkspaceProfileRead | None)
def get_workspace(db: Session = Depends(get_db)) -> WorkspaceProfile | None:
    return db.get(WorkspaceProfile, 1)


@app.put("/api/workspace", response_model=WorkspaceProfileRead)
def update_workspace(payload: WorkspaceProfileUpdate, db: Session = Depends(get_db)) -> WorkspaceProfile:
    profile = db.get(WorkspaceProfile, 1)
    if profile is None:
        profile = WorkspaceProfile(id=1)
        db.add(profile)
    for key, value in payload.model_dump(mode="json").items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


@app.post("/api/campaigns", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)) -> Campaign:
    campaign = Campaign(**payload.model_dump())
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@app.get("/api/campaigns", response_model=list[CampaignRead])
def list_campaigns(db: Session = Depends(get_db)) -> list[Campaign]:
    return list(db.scalars(select(Campaign).order_by(Campaign.created_at.desc())))


@app.get("/api/campaigns/{campaign_id}/dashboard", response_model=CampaignDashboardRead)
def get_campaign_dashboard(campaign_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    latest_run = db.scalar(
        select(CampaignRun).where(CampaignRun.campaign_id == campaign_id).order_by(CampaignRun.created_at.desc()).limit(1)
    )

    lead_counts = {}
    for st in LeadStatus:
        cnt = db.scalar(select(func.count(Lead.id)).where(Lead.campaign_id == campaign_id, Lead.status == st.value)) or 0
        lead_counts[st.value] = cnt

    total_leads = db.scalar(select(func.count(Lead.id)).where(Lead.campaign_id == campaign_id)) or 0
    total_drafts = db.scalar(select(func.count(EmailDraft.id)).join(Lead).where(Lead.campaign_id == campaign_id)) or 0
    pending_approval = db.scalar(select(func.count(EmailDraft.id)).join(Lead).where(Lead.campaign_id == campaign_id, EmailDraft.status == "Pending Approval")) or 0

    return {
        "campaign": campaign,
        "latest_run_step": latest_run.current_step if latest_run else None,
        "counts": {
            "total_leads": total_leads,
            "total_drafts": total_drafts,
            "pending_approval": pending_approval,
            **lead_counts,
        },
    }


@app.delete("/api/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(campaign_id: str, db: Session = Depends(get_db)) -> Response:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status in {"Researching", "Drafting", "Qualifying", "Auditing"}:
        raise HTTPException(status_code=409, detail="Cannot delete a campaign while it is running")
    db.delete(campaign)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/api/campaigns/{campaign_id}/messages", response_model=CampaignMessageRead)
async def add_campaign_message(campaign_id: str, payload: CampaignMessageCreate, db: Session = Depends(get_db)) -> CampaignMessage:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    user_msg = CampaignMessage(campaign_id=campaign_id, role="user", content=payload.content)
    db.add(user_msg)
    db.commit()

    messages = list(db.scalars(select(CampaignMessage).where(CampaignMessage.campaign_id == campaign_id).order_by(CampaignMessage.created_at)))
    chat_history = [{"role": m.role, "content": m.content} for m in messages]

    profile = db.get(WorkspaceProfile, 1)
    profile_dict = {
        "person_name": profile.person_name if profile else "",
        "business_name": profile.business_name if profile else "",
        "service_offer": profile.service_offer if profile else "",
    }

    brief_output = await generate_campaign_brief(
        get_settings(),
        campaign.name,
        campaign.niche,
        campaign.location,
        campaign.country,
        chat_history,
        profile_dict,
    )

    brief_data = brief_output.model_dump()
    assistant_reply = brief_data.pop("assistant_reply", "Generated proposed campaign brief.")

    assistant_msg = CampaignMessage(campaign_id=campaign_id, role="assistant", content=assistant_reply)
    db.add(assistant_msg)

    brief_rec = db.scalar(select(CampaignBrief).where(CampaignBrief.campaign_id == campaign_id).order_by(CampaignBrief.version.desc()).limit(1))
    new_version = (brief_rec.version + 1) if brief_rec else 1

    new_brief = CampaignBrief(
        campaign_id=campaign_id,
        version=new_version,
        brief_data=brief_data,
        status="Proposed",
    )
    db.add(new_brief)
    campaign.brief = brief_data
    campaign.brief_status = "Proposed"

    db.commit()
    db.refresh(user_msg)
    return user_msg


@app.get("/api/campaigns/{campaign_id}/messages", response_model=list[CampaignMessageRead])
def list_campaign_messages(campaign_id: str, db: Session = Depends(get_db)) -> list[CampaignMessage]:
    return list(db.scalars(select(CampaignMessage).where(CampaignMessage.campaign_id == campaign_id).order_by(CampaignMessage.created_at)))


@app.get("/api/campaigns/{campaign_id}/brief", response_model=CampaignBriefRead | None)
def get_campaign_brief(campaign_id: str, db: Session = Depends(get_db)) -> CampaignBrief | None:
    return db.scalar(select(CampaignBrief).where(CampaignBrief.campaign_id == campaign_id).order_by(CampaignBrief.version.desc()).limit(1))


@app.put("/api/campaigns/{campaign_id}/brief", response_model=CampaignBriefRead)
def update_campaign_brief(campaign_id: str, payload: CampaignBriefUpdate, db: Session = Depends(get_db)) -> CampaignBrief:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")

    latest = db.scalar(select(CampaignBrief).where(CampaignBrief.campaign_id == campaign_id).order_by(CampaignBrief.version.desc()).limit(1))
    version = (latest.version + 1) if latest else 1

    brief_data = payload.model_dump()
    new_brief = CampaignBrief(campaign_id=campaign_id, version=version, brief_data=brief_data, status="Finalized")
    db.add(new_brief)
    campaign.brief = brief_data
    campaign.brief_status = "Finalized"

    db.commit()
    db.refresh(new_brief)
    return new_brief


@app.post("/api/campaigns/{campaign_id}/leads", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
def create_lead(campaign_id: str, payload: LeadCreate, db: Session = Depends(get_db)) -> Lead:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    lead = Lead(campaign_id=campaign_id, **payload.model_dump(mode="json"))
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@app.get("/api/campaigns/{campaign_id}/leads", response_model=list[LeadRead])
def list_leads(campaign_id: str, db: Session = Depends(get_db)) -> list[Lead]:
    return list(db.scalars(select(Lead).where(Lead.campaign_id == campaign_id).order_by(Lead.created_at.desc())))


@app.get("/api/leads/{lead_id}", response_model=LeadRead)
def get_lead(lead_id: str, db: Session = Depends(get_db)) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@app.patch("/api/leads/{lead_id}", response_model=LeadRead)
def update_lead_details(lead_id: str, payload: LeadDetailUpdate, db: Session = Depends(get_db)) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(lead, key, value)

    db.add(LeadActivity(lead_id=lead_id, activity_type="details_updated", description="Updated lead configuration & notes"))
    db.commit()
    db.refresh(lead)
    return lead


@app.post("/api/leads/{lead_id}/status", response_model=LeadRead)
def update_lead_status(lead_id: str, payload: LeadStatusUpdate, db: Session = Depends(get_db)) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead not found")

    valid_targets = VALID_LEAD_TRANSITIONS.get(lead.status, set())
    if valid_targets and payload.status not in valid_targets:
        # Allow operator override but log reason
        pass

    old_status = lead.status
    lead.status = payload.status
    lead.last_activity_at = datetime.utcnow()

    db.add(LeadStatusHistory(lead_id=lead_id, from_status=old_status, to_status=payload.status, reason=payload.reason))
    db.add(LeadActivity(lead_id=lead_id, activity_type="status_changed", description=f"Changed status from {old_status} to {payload.status}"))
    db.add(AuditEvent(action="lead_status_changed", entity_type="lead", entity_id=lead_id, metadata_json={"from": old_status, "to": payload.status}))

    db.commit()
    db.refresh(lead)
    return lead


@app.post("/api/campaigns/{campaign_id}/run", response_model=CampaignRead, status_code=status.HTTP_202_ACCEPTED)
def run_campaign(campaign_id: str, db: Session = Depends(get_db)) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status not in {"Created", "Failed"}:
        raise HTTPException(status_code=409, detail="Campaign is already running or completed")
    run = CampaignRun(campaign_id=campaign.id, idempotency_key=f"campaign:{campaign.id}:run-{str(uuid4())[:8]}", status="Queued")
    campaign.status = "Queued"
    campaign.error = None
    db.add(run)
    db.commit()
    db.refresh(campaign)
    return campaign


@app.get("/api/campaigns/{campaign_id}/drafts", response_model=list[DraftRead])
def list_drafts(campaign_id: str, db: Session = Depends(get_db)) -> list[EmailDraft]:
    return list(db.scalars(select(EmailDraft).join(Lead).where(Lead.campaign_id == campaign_id)))


@app.patch("/api/drafts/{draft_id}", response_model=DraftRead)
def update_draft(draft_id: str, payload: DraftUpdate, db: Session = Depends(get_db)) -> EmailDraft:
    draft = db.get(EmailDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status in {"Sent", "Contacted", "Rejected"}:
        raise HTTPException(status_code=409, detail="Draft cannot be edited in its current state")
    draft.subject = payload.subject
    draft.body = payload.body
    draft.version += 1
    draft.status = "Pending Approval"
    db.commit()
    db.refresh(draft)
    return draft


@app.post("/api/drafts/{draft_id}/revise", response_model=DraftRead)
async def revise_draft(draft_id: str, payload: DraftRevisionRequest, db: Session = Depends(get_db)) -> EmailDraft:
    draft = db.get(EmailDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    lead = db.get(Lead, draft.lead_id)
    profile = db.get(WorkspaceProfile, 1)
    if lead is None or profile is None:
        raise HTTPException(status_code=409, detail="Workspace or lead context is missing")
    revised = await draft_outreach(
        get_settings(),
        {
            "business_name": lead.business_name, "niche": lead.niche, "location": lead.location,
            "website": lead.website, "instagram": lead.instagram, "linkedin": lead.linkedin,
            "facebook": lead.facebook, "email": lead.email,
            "observation": (lead.research or {}).get("observation", ""),
            "opportunity": (lead.research or {}).get("opportunity", ""),
            "current_draft": draft.body, "revision_request": payload.instruction,
        },
        draft.channel,
        {
            "person_name": profile.person_name, "business_name": profile.business_name,
            "service_offer": profile.service_offer, "positioning": profile.positioning,
            "tone": profile.tone, "call_to_action": profile.call_to_action,
        },
    )
    draft.subject = revised.subject
    draft.body = revised.body
    draft.version += 1
    draft.status = "Pending Approval"
    db.commit()
    db.refresh(draft)
    return draft


@app.post("/api/drafts/{draft_id}/mark-contacted", response_model=DraftRead)
def mark_contacted(draft_id: str, db: Session = Depends(get_db)) -> EmailDraft:
    draft = db.get(EmailDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.channel == "email":
        raise HTTPException(status_code=409, detail="Email drafts use the email send workflow")
    if draft.status != "Approved" or draft.approval is None or draft.approval.action != "approve":
        raise HTTPException(status_code=409, detail="Only an approved draft can be marked contacted")
    draft.status = "Contacted"
    lead = db.get(Lead, draft.lead_id)
    if lead:
        lead.status = "Contacted"
        lead.contacted_at = datetime.utcnow()
        lead.last_contacted_channel = draft.channel
        lead.last_activity_at = datetime.utcnow()
        db.add(LeadActivity(lead_id=lead.id, activity_type="outreach_sent_manually", channel=draft.channel, description=f"Marked {draft.channel} message as contacted manually"))
    db.commit()
    db.refresh(draft)
    return draft


@app.post("/api/drafts/{draft_id}/approval", response_model=DraftRead)
def approve_draft(draft_id: str, payload: ApprovalUpdate, db: Session = Depends(get_db)) -> EmailDraft:
    draft = db.get(EmailDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status != "Pending Approval":
        raise HTTPException(status_code=409, detail="Draft has already been reviewed")
    if payload.action == "approve":
        if payload.body is not None:
            draft.body = payload.body
        if payload.subject is not None:
            draft.subject = payload.subject
        draft.status = "Approved"
        db.add(Approval(draft_id=draft.id, action="approve", edited_subject=payload.subject, edited_body=payload.body))
        db.add(LeadActivity(lead_id=draft.lead_id, activity_type="draft_approved", channel=draft.channel, description=f"Approved {draft.channel} draft"))
    else:
        draft.status = "Rejected"
        db.add(Approval(draft_id=draft.id, action="reject"))
        db.add(LeadActivity(lead_id=draft.lead_id, activity_type="draft_rejected", channel=draft.channel, description=f"Rejected {draft.channel} draft"))
    db.commit()
    db.refresh(draft)
    return draft


@app.post("/api/drafts/{draft_id}/send", response_model=DraftRead)
def send_draft(draft_id: str, db: Session = Depends(get_db)) -> EmailDraft:
    draft = db.get(EmailDraft, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status != "Approved" or draft.approval is None or draft.approval.action != "approve":
        raise HTTPException(status_code=409, detail="Only an approved draft can be sent")
    if draft.channel != "email":
        raise HTTPException(status_code=409, detail="Social drafts must be sent manually")
    if draft.send is not None:
        return draft
    send_record = EmailSend(draft_id=draft.id, status="Sending")
    db.add(send_record)
    try:
        send_record.provider_message_id = send_approved_email(
            get_settings(), recipient=draft.recipient, subject=draft.subject, body=draft.body
        )
        send_record.status = "Sent"
        draft.status = "Sent"
        lead = db.get(Lead, draft.lead_id)
        if lead:
            lead.status = "Contacted"
            lead.contacted_at = datetime.utcnow()
            lead.last_contacted_channel = "email"
            lead.last_activity_at = datetime.utcnow()
            db.add(LeadActivity(lead_id=lead.id, activity_type="email_sent", channel="email", description="Sent email via Gmail API"))
    except GmailError as exc:
        send_record.status = "Failed"
        send_record.error = str(exc)
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    db.commit()
    db.refresh(draft)
    return draft
