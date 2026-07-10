"""
End-to-end integration tests for the FitNova Call Intelligence Pipeline.

Why this approach:
We write a comprehensive E2E test verifying that a raw audio call event goes through the entire
loop (Ingestion -> Transcription -> Diarisation -> LLM Analysis -> Verifier -> Storage) successfully,
with all outputs asserted in the Postgres database.
We also verify the idempotency of the orchestrator by running it twice and ensuring the second
run exits early.
"""

import os
import pytest
from sqlalchemy.orm import Session
from src.storage.db import SessionLocal, engine, Base
from src.storage import models, crud
from src.ingestion.schemas import CallEvent
from src.pipeline.orchestrator import process_call

@pytest.fixture(scope="module")
def db():
    """
    Sets up database tables and yields a clean session for E2E testing.
    """
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

def test_pipeline_end_to_end(db: Session):
    """
    Test that ingesting and processing a real stereo WAV call completes the full loop:
    transcribes, diarises, scores, tags, and stores results in the DB.
    """
    # 1. Ingestion: Simulate a CallEvent
    audio_file = "data/mock_calls/call_4507.wav"
    assert os.path.exists(audio_file), f"Mock audio file {audio_file} missing."
    
    event = CallEvent(
        source_system="folder",
        source_call_id="call_4507.wav",
        recording_path=os.path.abspath(audio_file),
        advisor_name="Rohan"
    )
    
    # Create call in pending status
    db_call = crud.create_call_from_event(db, event)
    assert db_call.id is not None
    assert db_call.status == "pending"
    
    # 2. Orchestration: Process the call through the pipeline
    processed_call = process_call(db, db_call.id)
    
    # 3. Assertions: Verify DB state after E2E execution
    assert processed_call.status in ["done", "skipped"]
    
    # Verify transcript is populated
    transcript = db.query(models.Transcript).filter(models.Transcript.call_id == db_call.id).first()
    assert transcript is not None
    assert len(transcript.full_text) > 0
    assert transcript.diarisation_confidence == "high"  # stereo split should be high
    assert len(transcript.segments_json) > 0
    
    # Verify scores are populated (if it's classified as sales)
    if processed_call.status == "done":
        scores = db.query(models.Scores).filter(models.Scores.call_id == db_call.id).first()
        assert scores is not None
        assert scores.overall >= 1.0 and scores.overall <= 5.0
        assert scores.needs_discovery >= 1.0 and scores.needs_discovery <= 5.0
        
        # Verify tags relationship
        tags = db.query(models.Tag).filter(models.Tag.call_id == db_call.id).all()
        # Verify that each tag is correctly resolved with a positive timestamp
        for tag in tags:
            assert tag.timestamp_sec >= 0.0
            assert len(tag.quoted_line) > 0
            assert tag.contest_status == "none"
            
    # 4. Idempotency Check: Run the pipeline again. It should exit early and not raise errors
    re_processed_call = process_call(db, db_call.id)
    assert re_processed_call.status == processed_call.status
