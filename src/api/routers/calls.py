"""
FastAPI router for call ingestion, listing, detail, and pipeline execution.

Why this approach:
We isolate call operations into a dedicated router. This links incoming REST requests to
the FolderAdapter scanner, database queries, and the end-to-end processing pipeline orchestrator.
All endpoints leverage request-scoped database sessions and enforce standardized schema outputs.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.storage import crud, db
from src.api import schemas
from src.ingestion.folder_adapter import FolderAdapter
from src.pipeline.orchestrator import process_call
from typing import List, Optional

router = APIRouter(prefix="/calls", tags=["Calls"])

@router.post("/ingest", response_model=List[schemas.CallResponse], status_code=status.HTTP_201_CREATED)
def ingest_calls(db_session: Session = Depends(db.get_db)):
    """
    Scans the local mock folder adapter to discover and stage new calls as 'pending' in the database.
    """
    adapter = FolderAdapter()
    try:
        events = adapter.fetch_new_calls()
        calls = []
        for event in events:
            db_call = crud.create_call_from_event(db_session, event)
            calls.append(db_call)
        return calls
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {e}"
        )

@router.post("/{call_id}/process", response_model=schemas.CallDetailResponse)
def process_single_call(call_id: int, db_session: Session = Depends(db.get_db)):
    """
    Triggers the end-to-end transcription, diarisation, and compliance scoring pipeline for a pending call.
    """
    db_call = crud.get_call(db_session, call_id)
    if not db_call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call with ID {call_id} not found."
        )
        
    try:
        processed_call = process_call(db_session, call_id)
        return processed_call
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {e}"
        )

@router.get("", response_model=List[schemas.CallResponse])
def list_calls(
    advisor_id: Optional[int] = None,
    team_id: Optional[int] = None,
    status: Optional[str] = None,
    db_session: Session = Depends(db.get_db)
):
    """
    Retrieves call records filterable by advisor ID, team ID, or processing status.
    """
    return crud.get_calls_filtered(
        db=db_session, 
        advisor_id=advisor_id, 
        team_id=team_id, 
        status=status
    )

@router.get("/{call_id}", response_model=schemas.CallDetailResponse)
def get_call_detail(call_id: int, db_session: Session = Depends(db.get_db)):
    """
    Retrieves the complete detail of a single call, including transcripts and compliance scores.
    """
    db_call = crud.get_call(db_session, call_id)
    if not db_call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call with ID {call_id} not found."
        )
    return db_call
