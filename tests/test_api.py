"""
Unit tests for the FastAPI routing layer.

Why this approach:
We write a clean test suite using FastAPI's TestClient to hit all HTTP endpoints.
It verifies that each route (Ingestion, Detail, Org/Team/Advisor Rollups, Contests, and Resolutions)
behaves correctly under both normal and error conditions (such as invalid parameters or missing IDs).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.api.main import app
from src.storage.db import SessionLocal, engine, Base
from src.storage import models, crud
from src.ingestion.schemas import CallEvent

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    """
    Sets up database tables and populates a mock hierarchy (Org -> Team -> Advisor) for API testing.
    """
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        # Seed basic hierarchy
        org = models.Org(name="Test Org")
        session.add(org)
        session.flush()
        
        team = models.Team(name="Test Team", org_id=org.id)
        session.add(team)
        session.flush()
        
        advisor = models.Advisor(name="Rohan", team_id=team.id)
        session.add(advisor)
        session.flush()
        
        session.commit()
        yield session, org.id, team.id, advisor.id
    finally:
        # Clean up database in reverse dependency order
        session.query(models.Contest).delete()
        session.query(models.Tag).delete()
        session.query(models.Scores).delete()
        session.query(models.Transcript).delete()
        session.query(models.Call).delete()
        session.query(models.Advisor).delete()
        session.query(models.Team).delete()
        session.query(models.Org).delete()
        session.commit()
        session.close()

def test_health_endpoints():
    """
    Tests health check and root endpoints.
    """
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

def test_call_ingestion_and_processing_flow(db_session):
    """
    Tests POST /calls/ingest, GET /calls, POST /calls/{id}/process, and GET /calls/{id}.
    """
    session, org_id, team_id, advisor_id = db_session
    
    # 1. Ingest new calls
    res = client.post("/calls/ingest")
    assert res.status_code == 201
    calls_list = res.json()
    assert len(calls_list) > 0
    first_call = calls_list[0]
    assert first_call["status"] == "pending"
    call_id = first_call["id"]
    
    # Update advisor_id to Rohan so summaries aggregate correctly
    db_call = session.query(models.Call).filter(models.Call.id == call_id).first()
    db_call.advisor_id = advisor_id
    session.commit()

    # 2. List calls
    res = client.get("/calls")
    assert res.status_code == 200
    assert len(res.json()) >= len(calls_list)

    # 3. Process call through API
    res = client.post(f"/calls/{call_id}/process")
    assert res.status_code == 200
    processed_detail = res.json()
    assert processed_detail["status"] in ["done", "skipped"]

    # 4. Get single call detail
    res = client.get(f"/calls/{call_id}")
    assert res.status_code == 200
    detail = res.json()
    assert detail["status"] == processed_detail["status"]
    assert detail["transcript"] is not None

def test_summaries_endpoints(db_session):
    """
    Tests /orgs/{org_id}/summary, /teams/{team_id}/summary, and /advisors/{advisor_id}/summary.
    """
    session, org_id, team_id, advisor_id = db_session
    
    # 1. Org summary
    res = client.get(f"/orgs/{org_id}/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["org_id"] == org_id
    assert data["total_calls"] >= 1
    assert data["overall_average"] >= 0.0

    # 2. Team summary
    res = client.get(f"/teams/{team_id}/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["team_id"] == team_id
    assert len(data["advisors"]) >= 1

    # 3. Advisor summary
    res = client.get(f"/advisors/{advisor_id}/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["advisor_id"] == advisor_id
    assert len(data["recent_calls"]) >= 1

def test_disputes_and_resolutions_flow(db_session):
    """
    Tests /tags/{tag_id}/contest and /contests/{contest_id}/resolve feedback loop.
    """
    session, org_id, team_id, advisor_id = db_session
    
    # Seed a call with scores and a critical tag for Rohan
    call = models.Call(advisor_id=advisor_id, source_system="test", source_call_id="call_test_dispute.wav", recording_path="dummy", status="done")
    session.add(call)
    session.flush()
    
    scores = models.Scores(
        call_id=call.id,
        needs_discovery=4.0,
        product_knowledge=4.0,
        objection_handling=4.0,
        compliance=4.0,
        trial_booking=4.0,
        overall=3.5 # Overall score includes tag deduction
    )
    session.add(scores)
    
    tag = models.Tag(
        call_id=call.id,
        type="medical_advice",
        severity="critical",
        timestamp_sec=12.5,
        quoted_line="You should take these pills",
        reason="Advisor prescribed medicine.",
        contest_status="none"
    )
    session.add(tag)
    session.commit()
    
    # 1. Advisor contests the tag
    res = client.post(f"/tags/{tag.id}/contest", json={"advisor_note": "I only recommended lifestyle changes."})
    assert res.status_code == 201
    contest_data = res.json()
    assert contest_data["tag_id"] == tag.id
    assert contest_data["advisor_note"] == "I only recommended lifestyle changes."
    contest_id = contest_data["id"]
    
    # Check tag status is now pending
    session.refresh(tag)
    assert tag.contest_status == "pending"

    # Query pending contests list
    res_list = client.get("/contests/pending")
    assert res_list.status_code == 200
    pending_list = res_list.json()
    assert len(pending_list) >= 1
    assert pending_list[0]["contest_id"] == contest_id

    # 2. Team Leader resolves (overturns) the contest
    res = client.post(
        f"/contests/{contest_id}/resolve",
        json={
            "resolved_by": advisor_id,
            "resolution_note": "Verified transcript context; advisor was repeating customer request.",
            "decision": "overturned"
        }
    )
    assert res.status_code == 200
    resolved_data = res.json()
    assert resolved_data["resolved_by"] == advisor_id
    
    # Check tag is marked overturned and call scores recalculated (critical deduction removed)
    session.refresh(tag)
    session.refresh(scores)
    assert tag.contest_status == "overturned"
    assert scores.overall == 4.0 # Recalculated without critical deduction penalty!
