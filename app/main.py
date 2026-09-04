from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.agents_workflow import draft_outreach
from app.database import get_db
from app.gmail import GmailError, send_approved_email
from app.models import Approval, Campaign, CampaignRun, EmailDraft, EmailSend, Lead, WorkspaceProfile
from app.schemas import (
    ApprovalUpdate,
    CampaignCreate,
    CampaignRead,
    DraftRead,
    DraftRevisionRequest,
    DraftUpdate,
    LeadCreate,
    LeadRead,
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


@app.delete("/api/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(campaign_id: str, db: Session = Depends(get_db)) -> Response:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status in {"Researching", "Drafting"}:
        raise HTTPException(status_code=409, detail="Cannot delete a campaign while it is running")
    db.delete(campaign)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@app.post("/api/campaigns/{campaign_id}/run", response_model=CampaignRead, status_code=status.HTTP_202_ACCEPTED)
def run_campaign(campaign_id: str, db: Session = Depends(get_db)) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status not in {"Created", "Failed"}:
        raise HTTPException(status_code=409, detail="Campaign is already running or completed")
    run = CampaignRun(campaign_id=campaign.id, idempotency_key=f"campaign:{campaign.id}", status="Queued")
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
    if draft.channel not in {"instagram", "linkedin"}:
        raise HTTPException(status_code=409, detail="Only social drafts support guided revisions")
    lead = db.get(Lead, draft.lead_id)
    profile = db.get(WorkspaceProfile, 1)
    if lead is None or profile is None:
        raise HTTPException(status_code=409, detail="Workspace or lead context is missing")
    revised = await draft_outreach(
        get_settings(),
        {
            "business_name": lead.business_name, "niche": lead.niche, "location": lead.location,
            "website": lead.website, "instagram": lead.instagram, "linkedin": lead.linkedin,
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
        from datetime import datetime

        lead.status = "Contacted"
        lead.contacted_at = datetime.utcnow()
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
    else:
        draft.status = "Rejected"
        db.add(Approval(draft_id=draft.id, action="reject"))
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
    except GmailError as exc:
        send_record.status = "Failed"
        send_record.error = str(exc)
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    db.commit()
    db.refresh(draft)
    return draft
