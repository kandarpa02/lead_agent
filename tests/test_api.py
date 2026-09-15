from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=Base, sqlite_engine=True) if hasattr(Base, "sqlite_engine") else sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_workspace_profile_crud():
    resp = client.put("/api/workspace", json={
        "person_name": "Jane Doe",
        "business_name": "The Social Girl",
        "service_offer": "Social Media Management & Strategy",
        "website": "https://thesocialgirl.com",
        "positioning": "Helping premium coaches grow",
        "tone": "Warm and conversational",
        "call_to_action": "Book a 15-minute call",
    })
    assert resp.status_code == 200
    assert resp.json()["person_name"] == "Jane Doe"


def test_campaign_lifecycle():
    # 1. Create campaign
    resp = client.post("/api/campaigns", json={
        "name": "Kolkata Fitness Coaches",
        "niche": "Fitness Coaching",
        "location": "Kolkata",
        "country": "India",
        "minimum_budget": "$1000",
        "primary_channel": "Instagram",
        "secondary_channel": "LinkedIn",
        "lead_count": 5,
        "operator_instructions": "Focus on independent coaches with over 10k followers",
    })
    assert resp.status_code == 201
    campaign = resp.json()
    campaign_id = campaign["id"]

    # 2. Get Dashboard
    dash_resp = client.get(f"/api/campaigns/{campaign_id}/dashboard")
    assert dash_resp.status_code == 200
    assert dash_resp.json()["counts"]["total_leads"] == 0

    # 3. Add Lead
    lead_resp = client.post(f"/api/campaigns/{campaign_id}/leads", json={
        "business_name": "Pulse Fitness Studio",
        "niche": "Fitness",
        "location": "Kolkata",
        "country": "India",
        "website": "https://pulsefitness.in",
        "instagram": "https://instagram.com/pulsefitness",
        "email": "contact@pulsefitness.in",
    })
    assert lead_resp.status_code == 201
    lead_id = lead_resp.json()["id"]

    # 4. Update Lead Status
    status_resp = client.post(f"/api/leads/{lead_id}/status", json={
        "status": "Qualified",
        "reason": "Verified high engagement and active business",
    })
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "Qualified"

    # 5. Run Campaign (Queued)
    run_resp = client.post(f"/api/campaigns/{campaign_id}/run")
    assert run_resp.status_code == 202
    assert run_resp.json()["status"] == "Queued"
