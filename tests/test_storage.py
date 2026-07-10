"""
Tests for database storage, models, and ingestion folder adapter.

Why this approach:
We write integration tests that run against the active database session. They verify that
the FolderAdapter scans directories correctly, the CRUD helper functions process CallEvents
idempotently, and we can save transcripts, scores, and compliance tags with relational integrity.
"""

import os
import pytest
from sqlalchemy.orm import Session
from src.storage.db import SessionLocal, engine, Base
from src.storage import models, crud
from src.ingestion.folder_adapter import FolderAdapter

@pytest.fixture(scope="module")
def db_session():
    """
    Sets up a database session for testing, clearing records after run.
    """
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        # Clean up database records in reverse dependency order
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

def test_folder_adapter_scanning():
    """
    Verify that the FolderAdapter scans the mock directory and normalizes WAV files correctly.
    """
    adapter = FolderAdapter()
    events = adapter.fetch_new_calls()
    assert len(events) > 0, "Folder adapter did not find any WAV files in the mock_calls directory."
    for event in events:
        assert event.source_system == "folder"
        assert event.source_call_id.endswith(".wav")
        assert os.path.exists(event.recording_path)
        assert event.advisor_name in ["Rohan", "Sneha", "Amit", "Priya"]

def test_ingestion_and_crud(db_session: Session):
    """
    Verify CRUD transactions, relationship creations, and database constraints.
    """
    adapter = FolderAdapter()
    events = adapter.fetch_new_calls()
    assert len(events) > 0
    
    # Ingest the first event
    event = events[0]
    db_call = crud.create_call_from_event(db_session, event)
    
    # Assert call record is created with 'pending' status
    assert db_call.id is not None
    assert db_call.source_call_id == event.source_call_id
    assert db_call.status == "pending"
    
    # Verify relations (Advisor, Team, Org are created automatically)
    assert db_call.advisor_id is not None
    advisor = db_call.advisor
    assert advisor.name == event.advisor_name
    assert advisor.team is not None
    assert advisor.team.org is not None
    assert advisor.team.org.name == "FitNova"
    
    # Test Idempotency: creating call from same event should return the existing call
    db_call_duplicate = crud.create_call_from_event(db_session, event)
    assert db_call_duplicate.id == db_call.id
    
    # Test update status
    crud.update_call_status(db_session, db_call.id, "processing")
    db_session.refresh(db_call)
    assert db_call.status == "processing"
    
    # Test create transcript
    segments = [
        {"speaker": "Advisor", "start": 0.0, "end": 2.5, "text": "Hello, welcome to FitNova."},
        {"speaker": "Customer", "start": 3.0, "end": 5.0, "text": "Hi, I want to join."}
    ]
    db_transcript = crud.create_transcript(
        db_session, 
        db_call.id, 
        full_text="Hello, welcome to FitNova. Hi, I want to join.",
        segments_json=segments,
        diarisation_confidence="high"
    )
    assert db_transcript.call_id == db_call.id
    assert db_transcript.diarisation_confidence == "high"
    
    # Test create scores
    scores_dict = {
        "needs_discovery": 4.5,
        "product_knowledge": 5.0,
        "objection_handling": 3.5,
        "compliance": 5.0,
        "trial_booking": 4.0,
        "overall": 4.4
    }
    db_scores = crud.create_scores(db_session, db_call.id, scores_dict)
    assert db_scores.overall == 4.4
    
    # Test create compliance tag
    db_tag = crud.create_tag(
        db_session,
        db_call.id,
        tag_type="over-promising",
        severity="critical",
        timestamp_sec=12.5,
        quoted_line="guaranteed 10kg weight loss in a week",
        reason="Advisor guaranteed results which is against policy."
    )
    assert db_tag.id is not None
    assert db_tag.contest_status == "none"
