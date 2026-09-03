from dataclasses import dataclass


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


def score_lead(factors: QualificationInput) -> LeadScore:
    score = sum(bool(getattr(factors, field)) for field in factors.__dataclass_fields__) * 12.5
    score = round(score)
    if score >= 80:
        priority = "HOT"
    elif score >= 60:
        priority = "WARM"
    elif score >= 40:
        priority = "COLD"
    else:
        priority = "SKIP"
    return LeadScore(score=score, priority=priority)
