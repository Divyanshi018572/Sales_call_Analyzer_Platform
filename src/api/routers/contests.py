"""
FastAPI router for compliance tag disputes (contests) and feedback loops.

Why this approach:
We implement routes for advisors to contest compliance tags and Team Leaders to resolve disputes.
When a dispute is resolved as 'overturned' (marking the AI tag as a false-positive), we update 
the database state. If the overturned tag was of 'critical' severity, we dynamically recalculate 
the call's overall score by subtracting the penalty weight, ensuring the advisor's scorecard 
updates in real-time. This completes the human-in-the-loop design.
"""

import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from src.storage import db, models
from src.api import schemas
from src.analysis.rubric import calculate_overall_score

router = APIRouter(tags=["Contests"])

@router.post("/tags/{tag_id}/contest", response_model=schemas.ContestResponse, status_code=status.HTTP_201_CREATED)
def contest_tag(tag_id: int, request: schemas.ContestRequest, db_session: Session = Depends(db.get_db)):
    """
    Submits a dispute for a specific compliance tag, setting its contest status to 'pending'.
    """
    tag = db_session.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance tag with ID {tag_id} not found."
        )
        
    if tag.contest_status != "none":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This compliance tag is already contested or resolved."
        )
        
    # Create contest dispute record
    contest = models.Contest(
        tag_id=tag_id,
        advisor_note=request.advisor_note
    )
    
    # Update tag status
    tag.contest_status = "pending"
    
    db_session.add(contest)
    db_session.commit()
    db_session.refresh(contest)
    return contest

@router.post("/contests/{contest_id}/resolve", response_model=schemas.ContestResponse)
def resolve_contest(contest_id: int, request: schemas.ContestResolveRequest, db_session: Session = Depends(db.get_db)):
    """
    Resolves a dispute as 'upheld' or 'overturned', automatically recalculating scores if a critical tag is overturned.
    """
    contest = db_session.query(models.Contest).filter(models.Contest.id == contest_id).first()
    if not contest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispute contest with ID {contest_id} not found."
        )
        
    if contest.resolved_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This dispute has already been resolved."
        )
        
    tag = contest.tag
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Associated compliance tag missing for this contest."
        )
        
    # Update contest resolution
    contest.resolved_by = request.resolved_by
    contest.resolution_note = request.resolution_note
    contest.resolved_at = datetime.datetime.utcnow()
    
    # Update tag contest status
    decision = request.decision.lower()
    tag.contest_status = decision
    
    # Human-in-the-loop adjustment: if a critical tag is overturned, recalculate the score
    if decision == "overturned" and tag.severity == "critical":
        call = tag.call
        if call and call.scores:
            # Count remaining active critical tags (excluding the current overturned one)
            remaining_critical_count = db_session.query(func.count(models.Tag.id)).filter(
                and_(
                    models.Tag.call_id == call.id,
                    models.Tag.severity == "critical",
                    models.Tag.id != tag.id,
                    models.Tag.contest_status != "overturned"
                )
            ).scalar() or 0
            
            # Recalculate
            scores_record = call.scores
            scores_dict = {
                "needs_discovery": scores_record.needs_discovery,
                "product_knowledge": scores_record.product_knowledge,
                "objection_handling": scores_record.objection_handling,
                "compliance": scores_record.compliance,
                "trial_booking": scores_record.trial_booking
            }
            
            new_overall = calculate_overall_score(scores_dict, remaining_critical_count)
            scores_record.overall = new_overall
            
    db_session.commit()
    db_session.refresh(contest)
    return contest

@router.get("/contests/pending", response_model=list[dict])
def get_pending_contests(db_session: Session = Depends(db.get_db)):
    """
    Retrieves all disputes that are pending resolution, along with context (advisor name, tag description).
    """
    from typing import List as PyList
    contests = db_session.query(models.Contest).join(models.Tag).filter(models.Tag.contest_status == "pending").all()
    results = []
    for c in contests:
        tag = c.tag
        call = tag.call
        advisor = call.advisor if call else None
        results.append({
            "contest_id": c.id,
            "tag_id": tag.id,
            "call_id": call.id if call else None,
            "advisor_name": advisor.name if advisor else "Unknown",
            "tag_type": tag.type,
            "quoted_line": tag.quoted_line,
            "reason": tag.reason,
            "advisor_note": c.advisor_note,
            "created_at": call.created_at if call else None
        })
    return results
