from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class QualificationInput:
    established_business: bool = False
    existing_customers: bool = False
    good_product_or_service: bool = False
    active_business: bool = False
    active_social_presence: bool = False
    obvious_social_opportunity: bool = False
    ability_to_pay: bool = False
    growth_potential: bool = False


@dataclass(frozen=True)
class LeadScore:
    score: int
    priority: str
    reasons: list[str]


FACTOR_LABELS = {
    "established_business": "Established business history & presence",
    "existing_customers": "Visible customer base or social proof",
    "good_product_or_service": "Quality product or service offer",
    "active_business": "Currently active operations",
    "active_social_presence": "Existing social media activity",
    "obvious_social_opportunity": "Clear social media gap / content opportunity",
    "ability_to_pay": "Budget / ability to pay for marketing services",
    "growth_potential": "Demonstrated growth intent or scaling signals",
}


def score_lead(factors: QualificationInput) -> LeadScore:
    factor_dict = asdict(factors)
    matched = [FACTOR_LABELS[key] for key, val in factor_dict.items() if val]
    score = round(len(matched) * 12.5)
    if score >= 80:
        priority = "HOT"
    elif score >= 60:
        priority = "WARM"
    elif score >= 40:
        priority = "COLD"
    else:
        priority = "SKIP"
    return LeadScore(score=score, priority=priority, reasons=matched)


def evaluate_lead_factors(candidate: dict[str, object]) -> QualificationInput:
    """Extract qualification factors from lead evidence and observations."""
    obs = str(candidate.get("observation", "")).lower()
    opp = str(candidate.get("opportunity", "")).lower()
    text = f"{obs} {opp}".lower()

    has_web = bool(candidate.get("website"))
    has_social = bool(candidate.get("instagram") or candidate.get("linkedin") or candidate.get("facebook"))
    has_email = bool(candidate.get("email"))

    return QualificationInput(
        established_business=has_web or "established" in text or "years" in text,
        existing_customers="reviews" in text or "clients" in text or "customers" in text or has_web,
        good_product_or_service=True,
        active_business=has_web or has_social or has_email,
        active_social_presence=has_social,
        obvious_social_opportunity=bool(opp) or "opportunity" in text or "missing" in text or "outdated" in text or "gap" in text,
        ability_to_pay=has_web and (has_email or has_social),
        growth_potential="hiring" in text or "expanding" in text or "growth" in text or "launch" in text or True,
    )

