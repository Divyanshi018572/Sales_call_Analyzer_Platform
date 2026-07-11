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

from src.api import auth_utils
from src.storage import models

router = APIRouter(prefix="/calls", tags=["Calls"])

@router.post("/ingest", response_model=List[schemas.CallResponse], status_code=status.HTTP_201_CREATED)
def ingest_calls(
    db_session: Session = Depends(db.get_db),
    current_user: models.User = Depends(auth_utils.RoleChecker(["team_leader", "director"]))
):
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
def process_single_call(
    call_id: int, 
    db_session: Session = Depends(db.get_db),
    current_user: models.User = Depends(auth_utils.RoleChecker(["team_leader", "director"]))
):
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
    limit: Optional[int] = None,
    offset: int = 0,
    db_session: Session = Depends(db.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user)
):
    """
    Retrieves call records filterable by advisor ID, team ID, or processing status, with pagination.
    """
    # Enforce row-level filtering based on user role
    if current_user.role == "advisor":
        advisor_id = current_user.advisor_id
        team_id = None
    elif current_user.role == "team_leader":
        if advisor_id:
            advisor = db_session.query(models.Advisor).filter(models.Advisor.id == advisor_id).first()
            if not advisor or advisor.team_id != current_user.team_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this advisor's calls"
                )
        else:
            team_id = current_user.team_id

    return crud.get_calls_filtered(
        db=db_session, 
        advisor_id=advisor_id, 
        team_id=team_id, 
        status=status,
        limit=limit,
        offset=offset
    )

@router.get("/{call_id}", response_model=schemas.CallDetailResponse)
def get_call_detail(
    call_id: int, 
    db_session: Session = Depends(db.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user)
):
    """
    Retrieves the complete detail of a single call, including transcripts and compliance scores.
    """
    db_call = crud.get_call(db_session, call_id)
    if not db_call:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call with ID {call_id} not found."
        )
        
    # Enforce row-level access checks
    if current_user.role == "advisor" and db_call.advisor_id != current_user.advisor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this call details"
        )
    elif current_user.role == "team_leader":
        if db_call.advisor and db_call.advisor.team_id != current_user.team_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this call details"
            )
            
    return db_call
