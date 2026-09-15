import asyncio
import logging
from datetime import datetime
from typing import Any
from sqlalchemy import select

from app.agents_workflow import draft_outreach, research_campaign
from app.config import get_settings
from app.constants import LeadStatus, PriorityTier
from app.database import SessionLocal
from app.models import (
    AuditEvent,
    Campaign,
    CampaignRun,
    EmailDraft,
    Lead,
    LeadActivity,
    LeadAudit,
    LeadQualification,
    LeadStatusHistory,
    ResearchEvidence,
    WorkflowStep,
    WorkspaceProfile,
)
from app.scoring import evaluate_lead_factors, score_lead

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def claim_run() -> CampaignRun | None:
    with SessionLocal() as db:
        run = db.scalar(select(CampaignRun).where(CampaignRun.status == "Queued").order_by(CampaignRun.created_at).limit(1))
        if run is None:
            return None
        run.status = "Running"
        run.attempts += 1
        run.current_step = "research"
        campaign = db.get(Campaign, run.campaign_id)
        if campaign:
            campaign.status = "Researching"
        db.commit()
        return run


def _determine_recommended_channel(lead_data: dict[str, Any], campaign_channels: list[str]) -> tuple[str, str]:
    avail = []
    if lead_data.get("instagram"):
        avail.append("instagram")
    if lead_data.get("linkedin"):
        avail.append("linkedin")
    if lead_data.get("facebook"):
        avail.append("facebook")
    if lead_data.get("email"):
        avail.append("email")

    for preferred in campaign_channels:
        if preferred.lower() in avail:
            return preferred.lower(), f"Matches campaign channel preference ({preferred}) and profile link is available."

    if avail:
        first = avail[0]
        return first, f"Selected {first} as available contact destination."
    return "email", "Default channel recommendation (no profile links verified yet)."


async def execute_run(run_id: str) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        run = db.get(CampaignRun, run_id)
        campaign = db.get(Campaign, run.campaign_id) if run else None
        if run is None or campaign is None:
            return

        current_step_obj: WorkflowStep | None = None
        try:
            profile_record = db.get(WorkspaceProfile, 1)
            if profile_record is None:
                raise RuntimeError("Complete workspace setup before running a campaign")
            profile = {
                "person_name": profile_record.person_name,
                "business_name": profile_record.business_name,
                "service_offer": profile_record.service_offer,
                "website": profile_record.website,
                "positioning": profile_record.positioning,
                "tone": profile_record.tone,
                "call_to_action": profile_record.call_to_action,
                "instagram": profile_record.instagram,
                "linkedin": profile_record.linkedin,
            }

            # 1. Research Step
            current_step_obj = WorkflowStep(run_id=run.id, name="research", status="Running", attempts=1)
            db.add(current_step_obj)
            db.commit()

            campaign_payload = {
                "name": campaign.name,
                "niche": campaign.niche,
                "location": campaign.location,
                "country": campaign.country,
                "minimum_budget": campaign.minimum_budget,
                "lead_count": campaign.lead_count,
                "primary_channel": campaign.primary_channel,
                "secondary_channel": campaign.secondary_channel,
                "operator_instructions": campaign.operator_instructions,
                "brief": campaign.brief,
            }

            research = await research_campaign(settings, campaign_payload, profile)
            current_step_obj.status = "Completed"
            current_step_obj.output = {"lead_count": len(research.leads)}
            db.commit()

            # 2. Qualification & Audit Step
            current_step_obj = WorkflowStep(run_id=run.id, name="qualification_and_audit", status="Running", attempts=1)
            run.current_step = "qualification_and_audit"
            campaign.status = "Qualifying"
            db.add(current_step_obj)
            db.commit()

            processed_leads = []
            for discovered in research.leads[: campaign.lead_count]:
                lead_data = {
                    "business_name": discovered.business_name,
                    "niche": discovered.niche or campaign.niche,
                    "location": discovered.location or campaign.location,
                    "website": discovered.website,
                    "instagram": discovered.instagram,
                    "linkedin": discovered.linkedin,
                    "email": discovered.email,
                    "observation": discovered.observation,
                    "opportunity": discovered.opportunity,
                    "source_urls": discovered.source_urls,
                }

                # Evaluate qualification & score
                factors = evaluate_lead_factors(lead_data)
                score_res = score_lead(factors)

                # Channel recommendation
                pref_channels = [campaign.primary_channel]
                if campaign.secondary_channel:
                    pref_channels.append(campaign.secondary_channel)
                rec_chan, rec_reason = _determine_recommended_channel(lead_data, pref_channels)

                # Status determination
                if score_res.priority == PriorityTier.SKIP.value:
                    initial_status = LeadStatus.NOT_A_FIT.value
                    excl_reason = "Score below qualification threshold"
                else:
                    initial_status = LeadStatus.QUALIFIED.value
                    excl_reason = None

                lead = Lead(
                    campaign_id=campaign.id,
                    business_name=discovered.business_name,
                    niche=discovered.niche or campaign.niche,
                    location=discovered.location or campaign.location,
                    country=campaign.country,
                    website=discovered.website,
                    instagram=discovered.instagram,
                    linkedin=discovered.linkedin,
                    email=discovered.email,
                    source="Agents SDK web research",
                    status=initial_status,
                    score=float(score_res.score),
                    priority=score_res.priority,
                    recommended_channel=rec_chan,
                    recommended_channel_reason=rec_reason,
                    exclusion_reason=excl_reason,
                    research={"source_urls": discovered.source_urls, "observation": discovered.observation, "opportunity": discovered.opportunity},
                )
                db.add(lead)
                db.flush()

                # Persist Evidence
                for url in discovered.source_urls:
                    db.add(ResearchEvidence(
                        lead_id=lead.id,
                        url=url,
                        title=discovered.business_name,
                        http_status=200,
                        content=discovered.observation,
                    ))
                if discovered.website and discovered.website not in discovered.source_urls:
                    db.add(ResearchEvidence(
                        lead_id=lead.id,
                        url=discovered.website,
                        title=f"{discovered.business_name} Official Website",
                        http_status=200,
                        content=discovered.opportunity,
                    ))

                # Persist Qualification
                from dataclasses import asdict
                db.add(LeadQualification(
                    lead_id=lead.id,
                    score=float(score_res.score),
                    priority=score_res.priority,
                    factors=asdict(factors),
                    reasons=score_res.reasons,
                ))

                # Persist Audit
                db.add(LeadAudit(
                    lead_id=lead.id,
                    what_is_working="Active web or search presence detected",
                    what_is_missing=discovered.observation,
                    social_opportunity=discovered.opportunity,
                    recommended_offer=profile_record.service_offer[:200] if profile_record else "Social Media Management & Growth",
                    personalization_note=f"Observed: {discovered.observation[:150]}",
                    checklist_items={
                        "has_website": bool(discovered.website),
                        "has_instagram": bool(discovered.instagram),
                        "has_linkedin": bool(discovered.linkedin),
                        "has_email": bool(discovered.email),
                    },
                ))

                # History & Audit Event
                db.add(LeadStatusHistory(lead_id=lead.id, from_status=None, to_status=initial_status, reason="Automated campaign discovery & qualification"))
                db.add(AuditEvent(action="lead_discovered", entity_type="lead", entity_id=lead.id, metadata_json={"score": score_res.score, "priority": score_res.priority}))
                db.add(LeadActivity(lead_id=lead.id, activity_type="lead_qualified", description=f"Lead qualified with score {score_res.score} ({score_res.priority})"))

                processed_leads.append(lead)

            current_step_obj.status = "Completed"
            current_step_obj.output = {"qualified_count": len([l for l in processed_leads if l.status != LeadStatus.NOT_A_FIT.value])}
            db.commit()

            # 3. Drafting Step
            current_step_obj = WorkflowStep(run_id=run.id, name="drafting", status="Running", attempts=1)
            run.current_step = "drafting"
            campaign.status = "Drafting"
            db.add(current_step_obj)
            db.commit()

            draft_count = 0
            for lead in processed_leads:
                if lead.status == LeadStatus.NOT_A_FIT.value:
                    continue

                channels = [campaign.primary_channel.lower()]
                if campaign.secondary_channel:
                    channels.append(campaign.secondary_channel.lower())

                lead_data = {
                    "business_name": lead.business_name,
                    "niche": lead.niche,
                    "location": lead.location,
                    "website": lead.website,
                    "instagram": lead.instagram,
                    "linkedin": lead.linkedin,
                    "facebook": lead.facebook,
                    "email": lead.email,
                    "observation": (lead.research or {}).get("observation", ""),
                    "opportunity": (lead.research or {}).get("opportunity", ""),
                    "source_urls": (lead.research or {}).get("source_urls", []),
                }

                for channel in dict.fromkeys(channels):
                    dest_map = {
                        "instagram": lead.instagram,
                        "linkedin": lead.linkedin,
                        "facebook": lead.facebook,
                        "email": lead.email,
                    }
                    destination = dest_map.get(channel)
                    if not destination:
                        continue

                    # Check for existing draft
                    existing = db.scalar(select(EmailDraft).where(
                        EmailDraft.lead_id == lead.id, EmailDraft.channel == channel
                    ))
                    if existing:
                        continue

                    draft_out = await draft_outreach(settings, lead_data, channel, profile)
                    db.add(EmailDraft(
                        lead_id=lead.id,
                        channel=channel,
                        destination=destination,
                        recipient=lead.email if channel == "email" else None,
                        subject=draft_out.subject,
                        body=draft_out.body,
                        status="Pending Approval",
                    ))
                    draft_count += 1
                    db.add(LeadActivity(lead_id=lead.id, activity_type="draft_created", channel=channel, description=f"Generated {channel} draft outreach message"))

            current_step_obj.status = "Completed"
            current_step_obj.output = {"draft_count": draft_count}

            run.status = "Awaiting Approval"
            run.current_step = "approval"
            campaign.status = "Awaiting Approval"
            db.commit()

        except Exception as exc:
            logger.exception("Campaign run %s failed", run_id)
            if current_step_obj:
                current_step_obj.status = "Failed"
                current_step_obj.error = str(exc)[:2000]
            run.status = "Failed"
            run.error = str(exc)[:2000]
            campaign.status = "Failed"
            campaign.error = str(exc)[:2000]
            db.commit()


async def main() -> None:
    while True:
        run = claim_run()
        if run:
            await execute_run(run.id)
        else:
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())


async def main() -> None:
    while True:
        run = claim_run()
        if run:
            await execute_run(run.id)
        else:
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())