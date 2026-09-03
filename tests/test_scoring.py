from app.scoring import QualificationInput, score_lead


def test_all_factors_are_hot() -> None:
    result = score_lead(QualificationInput(*([True] * 8)))
    assert result.score == 100
    assert result.priority == "HOT"


def test_two_factors_are_cold() -> None:
    result = score_lead(QualificationInput(established_business=True, ability_to_pay=True))
    assert result.score == 25
    assert result.priority == "SKIP"


def test_five_factors_are_warm() -> None:
    result = score_lead(QualificationInput(*([True] * 5 + [False] * 3)))
    assert result.score == 62
    assert result.priority == "WARM"
