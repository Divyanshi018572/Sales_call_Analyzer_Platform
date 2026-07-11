"""
Unit and integration tests for authentication (JWT logins) and row-level access control.

Why this approach:
We construct a TestClient hitting the `/auth/login` and `/auth/me` endpoints and verifying
the behavior of RoleChecker and row-level checks on calls router. We assert that:
1. Incorrect login credentials return HTTP 401.
2. Advisors are blocked from accessing other advisors' call detail records (HTTP 403).
3. Team leaders are blocked from accessing call details of advisors outside their team (HTTP 403).
4. Directors can query any call record across all teams (HTTP 200).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.api.main import app
from src.storage.db import SessionLocal, engine, Base
from src.storage import models
from src.api import auth_utils

client = TestClient(app)

@pytest.fixture(scope="module")
def auth_db_session():
    """
    Sets up database tables and populates users, teams, advisors, and calls to test auth security.
    """
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        # Seed test database hierarchy
        org = models.Org(name="Auth Test Org")
        session.add(org)
        session.flush()
        
        team_1 = models.Team(name="Auth Team 1", org_id=org.id)
        team_2 = models.Team(name="Auth Team 2", org_id=org.id)
        session.add_all([team_1, team_2])
        session.flush()
        
        adv_1 = models.Advisor(name="Advisor 1", team_id=team_1.id)
        adv_2 = models.Advisor(name="Advisor 2", team_id=team_2.id)
        session.add_all([adv_1, adv_2])
        session.flush()
        
        # Seed Users
        user_dir = models.User(
            email="dir@test.com",
            hashed_password=auth_utils.hash_password("dir_pass"),
            role="director"
        )
        user_tl = models.User(
            email="tl@test.com",
            hashed_password=auth_utils.hash_password("tl_pass"),
            role="team_leader",
            team_id=team_1.id
        )
        user_adv1 = models.User(
            email="adv1@test.com",
            hashed_password=auth_utils.hash_password("adv1_pass"),
            role="advisor",
            advisor_id=adv_1.id,
            team_id=team_1.id
        )
        user_adv2 = models.User(
            email="adv2@test.com",
            hashed_password=auth_utils.hash_password("adv2_pass"),
            role="advisor",
            advisor_id=adv_2.id,
            team_id=team_2.id
        )
        session.add_all([user_dir, user_tl, user_adv1, user_adv2])
        session.commit()
        
        yield session, user_dir, user_tl, user_adv1, user_adv2, adv_1.id, adv_2.id, team_1.id, team_2.id
    finally:
        # Cleanup
        session.query(models.User).delete()
        session.query(models.Advisor).delete()
        session.query(models.Team).delete()
        session.query(models.Org).delete()
        session.commit()
        session.close()

def test_login_flow(auth_db_session):
    """
    Tests POST /auth/login with correct and incorrect credentials.
    """
    # Test successful login
    res = client.post("/auth/login", json={"email": "adv1@test.com", "password": "adv1_pass"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["role"] == "advisor"
    assert data["email"] == "adv1@test.com"
    
    # Test failed login
    res = client.post("/auth/login", json={"email": "adv1@test.com", "password": "wrong_password"})
    assert res.status_code == 401

def test_profile_flow(auth_db_session):
    """
    Tests GET /auth/me with and without Bearer credentials.
    """
    # Try to access without token
    res = client.get("/auth/me")
    assert res.status_code in [401, 403]
    
    # Login to get token
    res = client.post("/auth/login", json={"email": "adv1@test.com", "password": "adv1_pass"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    res = client.get("/auth/me", headers=headers)
    assert res.status_code == 200
    profile = res.json()
    assert profile["email"] == "adv1@test.com"
    assert profile["role"] == "advisor"

def test_role_authorization_and_row_level_filters(auth_db_session):
    """
    Enforces row-level query limitations for advisors, team leaders, and directors.
    """
    session, user_dir, user_tl, user_adv1, user_adv2, adv1_id, adv2_id, team1_id, team2_id = auth_db_session
    
    # 1. Get tokens
    dir_token = client.post("/auth/login", json={"email": "dir@test.com", "password": "dir_pass"}).json()["access_token"]
    tl_token = client.post("/auth/login", json={"email": "tl@test.com", "password": "tl_pass"}).json()["access_token"]
    adv1_token = client.post("/auth/login", json={"email": "adv1@test.com", "password": "adv1_pass"}).json()["access_token"]
    
    # Seed a call for Advisor 1 and a call for Advisor 2
    call_1 = models.Call(advisor_id=adv1_id, source_system="test", source_call_id="call1.wav", recording_path="dummy", status="done")
    call_2 = models.Call(advisor_id=adv2_id, source_system="test", source_call_id="call2.wav", recording_path="dummy", status="done")
    session.add_all([call_1, call_2])
    session.commit()
    
    # 2. Advisor 1 queries Advisor 2's call detail -> 403 Forbidden
    res = client.get(f"/calls/{call_2.id}", headers={"Authorization": f"Bearer {adv1_token}"})
    assert res.status_code == 403
    
    # 3. Advisor 1 queries Advisor 1's call detail -> 200 OK
    res = client.get(f"/calls/{call_1.id}", headers={"Authorization": f"Bearer {adv1_token}"})
    assert res.status_code == 200
    
    # 4. Team Leader 1 queries Advisor 2's call (who is on Team 2) -> 403 Forbidden
    res = client.get(f"/calls/{call_2.id}", headers={"Authorization": f"Bearer {tl_token}"})
    assert res.status_code == 403
    
    # 5. Team Leader 1 queries Advisor 1's call -> 200 OK
    res = client.get(f"/calls/{call_1.id}", headers={"Authorization": f"Bearer {tl_token}"})
    assert res.status_code == 200
    
    # 6. Director queries Advisor 2's call -> 200 OK
    res = client.get(f"/calls/{call_2.id}", headers={"Authorization": f"Bearer {dir_token}"})
    assert res.status_code == 200

    # Clean up calls manually to prevent dependencies on teardown
    session.delete(call_1)
    session.delete(call_2)
    session.commit()
