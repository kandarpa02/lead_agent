from enum import Enum


class CampaignStatus(str, Enum):
    DRAFT = "Draft"
    CREATED = "Created"
    QUEUED = "Queued"
    RESEARCHING = "Researching"
    QUALIFYING = "Qualifying"
    AUDITING = "Auditing"
    DRAFTING = "Drafting"
    AWAITING_APPROVAL = "Awaiting Approval"
    COMPLETED = "Completed"
    FAILED = "Failed"


class CampaignRunStatus(str, Enum):
    QUEUED = "Queued"
    RUNNING = "Running"
    AWAITING_APPROVAL = "Awaiting Approval"
    COMPLETED = "Completed"
    FAILED = "Failed"


class LeadStatus(str, Enum):
    TO_RESEARCH = "To Research"
    DISCOVERED = "Discovered"
    RESEARCHING = "Researching"
    RESEARCH_COMPLETE = "Research Complete"
    QUALIFIED = "Qualified"
    NEEDS_REVIEW = "Needs Review"
    READY_FOR_OUTREACH = "Ready for Outreach"
    CONTACTED = "Contacted"
    FOLLOW_UP_DUE = "Follow-up Due"
    REPLIED = "Replied"
    MEETING_BOOKED = "Meeting Booked"
    WON = "Won"
    NOT_A_FIT = "Not a Fit"
    DO_NOT_CONTACT = "Do Not Contact"
    ARCHIVED = "Archived"


class PriorityTier(str, Enum):
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"
    SKIP = "SKIP"


class OutreachChannel(str, Enum):
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    EMAIL = "email"


class DraftStatus(str, Enum):
    DRAFTING = "Drafting"
    PENDING_APPROVAL = "Pending Approval"
    APPROVED = "Approved"
    CONTACTED = "Contacted"
    SENT = "Sent"
    REJECTED = "Rejected"
    SUPERSEDED = "Superseded"


class SourceProvider(str, Enum):
    DUCKDUCKGO = "duckduckgo"
    WEBSITE = "website"
    INSTAGRAM = "instagram"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    GOOGLE_MAPS = "google_maps"
    MANUAL = "manual"


VALID_LEAD_TRANSITIONS: dict[str, set[str]] = {
    LeadStatus.TO_RESEARCH.value: {LeadStatus.DISCOVERED.value, LeadStatus.RESEARCHING.value, LeadStatus.NOT_A_FIT.value},
    LeadStatus.DISCOVERED.value: {LeadStatus.RESEARCHING.value, LeadStatus.QUALIFIED.value, LeadStatus.NOT_A_FIT.value, LeadStatus.DO_NOT_CONTACT.value},
    LeadStatus.RESEARCHING.value: {LeadStatus.RESEARCH_COMPLETE.value, LeadStatus.QUALIFIED.value, LeadStatus.NOT_A_FIT.value},
    LeadStatus.RESEARCH_COMPLETE.value: {LeadStatus.QUALIFIED.value, LeadStatus.NEEDS_REVIEW.value, LeadStatus.READY_FOR_OUTREACH.value, LeadStatus.NOT_A_FIT.value},
    LeadStatus.QUALIFIED.value: {LeadStatus.NEEDS_REVIEW.value, LeadStatus.READY_FOR_OUTREACH.value, LeadStatus.NOT_A_FIT.value, LeadStatus.DO_NOT_CONTACT.value},
    LeadStatus.NEEDS_REVIEW.value: {LeadStatus.READY_FOR_OUTREACH.value, LeadStatus.NOT_A_FIT.value, LeadStatus.DO_NOT_CONTACT.value},
    LeadStatus.READY_FOR_OUTREACH.value: {LeadStatus.CONTACTED.value, LeadStatus.NOT_A_FIT.value, LeadStatus.DO_NOT_CONTACT.value},
    LeadStatus.CONTACTED.value: {LeadStatus.FOLLOW_UP_DUE.value, LeadStatus.REPLIED.value, LeadStatus.MEETING_BOOKED.value, LeadStatus.WON.value, LeadStatus.NOT_A_FIT.value},
    LeadStatus.FOLLOW_UP_DUE.value: {LeadStatus.CONTACTED.value, LeadStatus.REPLIED.value, LeadStatus.MEETING_BOOKED.value, LeadStatus.WON.value, LeadStatus.NOT_A_FIT.value},
    LeadStatus.REPLIED.value: {LeadStatus.MEETING_BOOKED.value, LeadStatus.WON.value, LeadStatus.NOT_A_FIT.value},
    LeadStatus.MEETING_BOOKED.value: {LeadStatus.WON.value, LeadStatus.NOT_A_FIT.value},
    LeadStatus.WON.value: {LeadStatus.ARCHIVED.value},
    LeadStatus.NOT_A_FIT.value: {LeadStatus.QUALIFIED.value, LeadStatus.ARCHIVED.value},
    LeadStatus.DO_NOT_CONTACT.value: {LeadStatus.QUALIFIED.value, LeadStatus.ARCHIVED.value},
    LeadStatus.ARCHIVED.value: {LeadStatus.QUALIFIED.value},
}
