import asyncio
import pytest
from app.web_tools import _fetch_candidate, build_discovery_queries


def test_build_discovery_queries():
    queries = build_discovery_queries("Fitness Coaching", "Kolkata", "India")
    assert len(queries) == 4
    assert any("official website" in q["query"] for q in queries)
    assert any("instagram linkedin facebook" in q["query"] for q in queries)


def test_fetch_candidate_social_extraction(monkeypatch):
    async def mock_fetch(url):
        return (
            "Welcome to Apex Coaching! Check our Instagram https://instagram.com/apexcoach "
            "LinkedIn https://linkedin.com/in/apexcoach and Facebook https://facebook.com/apexcoach. "
            "Email us at hello@apexcoach.com"
        )

    from app import web_tools
    monkeypatch.setattr(web_tools, "fetch_public_website", type("Mock", (), {"__wrapped__": mock_fetch}))

    candidate = {"name": "Apex Coaching", "url": "https://apexcoach.com"}
    res = asyncio.run(_fetch_candidate(candidate))

    assert res["email"] == "hello@apexcoach.com"
    assert res["instagram"] == "https://instagram.com/apexcoach"
    assert res["linkedin"] == "https://linkedin.com/in/apexcoach"
    assert res["facebook"] == "https://facebook.com/apexcoach"
