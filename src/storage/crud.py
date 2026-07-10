"""
Database CRUD (Create, Read, Update, Delete) operations.

Why this approach:
We isolate all direct database operations using SQLAlchemy Session objects into this module. 
This ensures other system modules (API routers, ingestion adapters, orchestrator) remain decoupled 
from database query syntax and connection handling details.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from src.storage.models import Org, Team, Advisor, Call, Transcript, Scores, Tag, Contest
from src.ingestion.schemas import CallEvent
from typing import List, Optional

def get_or_create_org(db: Session, name: str) -> Org:
    """
    Retrieves an organization by name, or creates it if it does not exist.
    """
    org = db.query(Org).filter(Org.name == name).first()
    if not org:
        org = Org(name=name)
        db.add(org)
        db.commit()
        db.refresh(org)
    return org

def get_or_create_team(db: Session, name: str, org_id: int) -> Team:
    """
    Retrieves a team by name and organization ID, or creates it if it does not exist.
    """
    team = db.query(Team).filter(and_(Team.name == name, Team.org_id == org_id)).first()
    if not team:
        team = Team(name=name, org_id=org_id)
        db.add(team)
        db.commit()
        db.refresh(team)
    return team

def get_or_create_advisor(db: Session, name: str, team_id: int) -> Advisor:
    """
    Retrieves an advisor by name and team ID, or creates it if it does not exist.
    """
    advisor = db.query(Advisor).filter(and_(Advisor.name == name, Advisor.team_id == team_id)).first()
    if not advisor:
        advisor = Advisor(name=name, team_id=team_id)
        db.add(advisor)
        db.commit()
        db.refresh(advisor)
    return advisor

def get_call_by_source(db: Session, source_system: str, source_call_id: str) -> Optional[Call]:
    """
    Gets a call by its source system and source call identifier.
    """
    return db.query(Call).filter(
        and_(Call.source_system == source_system, Call.source_call_id == source_call_id)
    ).first()

def get_call(db: Session, call_id: int) -> Optional[Call]:
    """
    Gets a call by its unique database ID.
    """
    return db.query(Call).filter(Call.id == call_id).first()

def create_call_from_event(db: Session, event: CallEvent) -> Call:
    """
    Idempotently creates a pending call record in the database from an ingestion CallEvent.
    If the call already exists, it returns the existing record.
    """
    # 1. Idempotency Check
    existing_call = get_call_by_source(db, event.source_system, event.source_call_id)
    if existing_call:
        return existing_call
        
    # 2. Map advisor to Org & Team hierarchy
    org = get_or_create_org(db, "FitNova")
    
    # Deterministic team routing for mock advisors
    if event.advisor_name in ["Rohan", "Sneha"]:
        team = get_or_create_team(db, "Team Alpha", org.id)
    else:
        team = get_or_create_team(db, "Team Beta", org.id)
        
    advisor = None
    if event.advisor_name:
        advisor = get_or_create_advisor(db, event.advisor_name, team.id)
        
    # 3. Create Call Record
    db_call = Call(
        advisor_id=advisor.id if advisor else None,
        source_system=event.source_system,
        source_call_id=event.source_call_id,
        recording_path=event.recording_path,
        status="pending"
    )
    db.add(db_call)
    db.commit()
    db.refresh(db_call)
    return db_call

def update_call_status(db: Session, call_id: int, status: str) -> Optional[Call]:
    """
    Updates the processing status of a call.
    """
    db_call = get_call(db, call_id)
    if db_call:
        db_call.status = status
        db.commit()
        db.refresh(db_call)
    return db_call

def create_transcript(db: Session, call_id: int, full_text: str, segments_json: List[dict], diarisation_confidence: str) -> Transcript:
    """
    Creates or updates the transcript record for a call.
    """
    transcript = db.query(Transcript).filter(Transcript.call_id == call_id).first()
    if transcript:
        transcript.full_text = full_text
        transcript.segments_json = segments_json
        transcript.diarisation_confidence = diarisation_confidence
    else:
        transcript = Transcript(
            call_id=call_id,
            full_text=full_text,
            segments_json=segments_json,
            diarisation_confidence=diarisation_confidence
        )
        db.add(transcript)
    db.commit()
    db.refresh(transcript)
    return transcript

def create_scores(db: Session, call_id: int, scores_dict: dict) -> Scores:
    """
    Creates or updates the call evaluation scores.
    """
    scores = db.query(Scores).filter(Scores.call_id == call_id).first()
    if scores:
        for key, value in scores_dict.items():
            setattr(scores, key, value)
    else:
        scores = Scores(call_id=call_id, **scores_dict)
        db.add(scores)
    db.commit()
    db.refresh(scores)
    return scores

def create_tag(db: Session, call_id: int, tag_type: str, severity: str, timestamp_sec: float, quoted_line: str, reason: str) -> Tag:
    """
    Adds a new compliance tag to a call.
    """
    tag = Tag(
        call_id=call_id,
        type=tag_type,
        severity=severity,
        timestamp_sec=timestamp_sec,
        quoted_line=quoted_line,
        reason=reason,
        contest_status="none"
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag

def get_calls_filtered(db: Session, advisor_id: Optional[int] = None, team_id: Optional[int] = None, status: Optional[str] = None) -> List[Call]:
    """
    Queries calls filterable by advisor, team, or status.
    """
    query = db.query(Call)
    if advisor_id:
        query = query.filter(Call.advisor_id == advisor_id)
    elif team_id:
        # Join with Advisor table to filter by team
        query = query.join(Advisor).filter(Advisor.team_id == team_id)
        
    if status:
        query = query.filter(Call.status == status)
        
    return query.order_by(Call.created_at.desc()).all()
