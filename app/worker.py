import asyncio
import logging

from sqlalchemy import select

from app.agents_workflow import draft_outreach, research_campaign
from app.config import get_settings
from app.database import SessionLocal
from app.models import Campaign, CampaignRun, EmailDraft, Lead, WorkflowStep, WorkspaceProfile

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


async def execute_run(run_id: str) -> None:
    settings = get_settings()
    with SessionLocal() as db:
        run = db.get(CampaignRun, run_id)
        campaign = db.get(Campaign, run.campaign_id) if run else None
        if run is None or campaign is None:
            return
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
            step = WorkflowStep(run_id=run.id, name="research", status="Running", attempts=1)
            db.add(step)
            db.commit()
            research = await research_campaign(settings, {
                "name": campaign.name, "niche": campaign.niche, "location": campaign.location,
                "country": campaign.country, "minimum_budget": campaign.minimum_budget,
                "lead_count": campaign.lead_count, "primary_channel": campaign.primary_channel,
                "secondary_channel": campaign.secondary_channel,
            }, profile)
            step.status = "Completed"
            step.output = {"lead_count": len(research.leads)}
            run.current_step = "drafting"
            campaign.status = "Drafting"
            db.commit()
            for discovered in research.leads[: campaign.lead_count]:
                lead = Lead(
                    campaign_id=campaign.id, business_name=discovered.business_name,
                    niche=discovered.niche or campaign.niche, location=discovered.location or campaign.location,
                    country=campaign.country, website=discovered.website, instagram=discovered.instagram,
                    linkedin=discovered.linkedin,
                    email=discovered.email, source="Agents SDK web research",
                    research={"source_urls": discovered.source_urls, "observation": discovered.observation, "opportunity": discovered.opportunity},
                    status="Qualified" if any((discovered.email, discovered.instagram, discovered.linkedin)) else "Research Complete",
                )
                db.add(lead)
                db.flush()
                lead_data = {
                    "business_name": lead.business_name, "niche": lead.niche, "location": lead.location,
                    "website": lead.website, "instagram": lead.instagram, "linkedin": lead.linkedin,
                    "observation": discovered.observation, "opportunity": discovered.opportunity,
                    "source_urls": discovered.source_urls,
                }
                channels = [campaign.primary_channel.lower()]
                if campaign.secondary_channel:
                    channels.append(campaign.secondary_channel.lower())
                for channel in dict.fromkeys(channels):
                    destination = {"instagram": lead.instagram, "linkedin": lead.linkedin}.get(channel)
                    if not destination or db.scalar(select(EmailDraft).where(
                        EmailDraft.lead_id == lead.id, EmailDraft.channel == channel
                    )):
                        continue
                    draft = await draft_outreach(settings, lead_data, channel, profile)
                    db.add(EmailDraft(
                        lead_id=lead.id, channel=channel, destination=destination,
                        recipient=None, subject=draft.subject, body=draft.body,
                    ))
                db.commit()
            run.status = "Awaiting Approval"
            run.current_step = "approval"
            campaign.status = "Awaiting Approval"
            db.commit()
        except Exception as exc:
            logger.exception("Campaign run %s failed", run_id)
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