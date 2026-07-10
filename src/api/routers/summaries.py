"""
FastAPI router for organizational, team, and advisor metrics rollup.

Why this approach:
We define route handlers that perform SQL aggregations using SQLAlchemy's func functions.
This moves rollup calculations (averages, counts, trends) directly to the database engine,
which is highly performant. Averages are capped or rounded, and empty database states
(e.g., zero processed calls) are handled gracefully by returning default scores (0.0),
preventing frontend crashes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from src.storage import db, models
from src.api import schemas
from typing import Dict

router = APIRouter(tags=["Summaries"])

@router.get("/orgs/{org_id}/summary", response_model=schemas.OrgSummaryResponse)
def get_org_summary(org_id: int, db_session: Session = Depends(db.get_db)):
    """
    Computes organization-wide averages and aggregates compliance tag counts (Sales Director view).
    """
    org = db_session.query(models.Org).filter(models.Org.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization with ID {org_id} not found."
        )
        
    # Get all team IDs in this org
    teams = db_session.query(models.Team).filter(models.Team.org_id == org_id).all()
    team_ids = [t.id for t in teams]
    
    # Get all advisor IDs in these teams
    advisors = db_session.query(models.Advisor).filter(models.Advisor.team_id.in_(team_ids)).all() if team_ids else []
    advisor_ids = [a.id for a in advisors]
    
    if not advisor_ids:
        return schemas.OrgSummaryResponse(
            org_id=org_id,
            org_name=org.name,
            total_calls=0,
            overall_average=0.0,
            dimension_averages={
                "needs_discovery": 0.0,
                "product_knowledge": 0.0,
                "objection_handling": 0.0,
                "compliance": 0.0,
                "trial_booking": 0.0
            },
            compliance_tag_count=0
        )
        
    # Query averages
    stats = db_session.query(
        func.count(models.Call.id).label("total"),
        func.avg(models.Scores.overall).label("avg_overall"),
        func.avg(models.Scores.needs_discovery).label("avg_discovery"),
        func.avg(models.Scores.product_knowledge).label("avg_product"),
        func.avg(models.Scores.objection_handling).label("avg_objection"),
        func.avg(models.Scores.compliance).label("avg_compliance"),
        func.avg(models.Scores.trial_booking).label("avg_booking")
    ).join(models.Scores, models.Call.id == models.Scores.call_id)\
     .filter(models.Call.advisor_id.in_(advisor_ids))\
     .filter(models.Call.status == "done").first()
     
    # Query tag count (excluding overturned disputes)
    tag_count = db_session.query(func.count(models.Tag.id))\
        .join(models.Call, models.Tag.call_id == models.Call.id)\
        .filter(models.Call.advisor_id.in_(advisor_ids))\
        .filter(models.Tag.contest_status != "overturned").scalar() or 0
        
    total_calls = stats.total if stats and stats.total is not None else 0
    overall_avg = round(stats.avg_overall, 2) if stats and stats.avg_overall is not None else 0.0
    
    dimension_averages = {
        "needs_discovery": round(stats.avg_discovery, 2) if stats and stats.avg_discovery is not None else 0.0,
        "product_knowledge": round(stats.avg_product, 2) if stats and stats.avg_product is not None else 0.0,
        "objection_handling": round(stats.avg_objection, 2) if stats and stats.avg_objection is not None else 0.0,
        "compliance": round(stats.avg_compliance, 2) if stats and stats.avg_compliance is not None else 0.0,
        "trial_booking": round(stats.avg_booking, 2) if stats and stats.avg_booking is not None else 0.0,
    }
    
    return schemas.OrgSummaryResponse(
        org_id=org_id,
        org_name=org.name,
        total_calls=total_calls,
        overall_average=overall_avg,
        dimension_averages=dimension_averages,
        compliance_tag_count=tag_count
    )

@router.get("/teams/{team_id}/summary", response_model=schemas.TeamSummaryResponse)
def get_team_summary(team_id: int, db_session: Session = Depends(db.get_db)):
    """
    Computes team rollups, pending tag disputes count, and individual advisor lists (Team Leader view).
    """
    team = db_session.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID {team_id} not found."
        )
        
    advisors = db_session.query(models.Advisor).filter(models.Advisor.team_id == team_id).all()
    advisor_ids = [a.id for a in advisors]
    
    if not advisor_ids:
        return schemas.TeamSummaryResponse(
            team_id=team_id,
            team_name=team.name,
            total_calls=0,
            overall_average=0.0,
            dimension_averages={
                "needs_discovery": 0.0,
                "product_knowledge": 0.0,
                "objection_handling": 0.0,
                "compliance": 0.0,
                "trial_booking": 0.0
            },
            compliance_tag_count=0,
            advisors=[],
            pending_contests_count=0
        )
        
    # Team averages
    stats = db_session.query(
        func.count(models.Call.id).label("total"),
        func.avg(models.Scores.overall).label("avg_overall"),
        func.avg(models.Scores.needs_discovery).label("avg_discovery"),
        func.avg(models.Scores.product_knowledge).label("avg_product"),
        func.avg(models.Scores.objection_handling).label("avg_objection"),
        func.avg(models.Scores.compliance).label("avg_compliance"),
        func.avg(models.Scores.trial_booking).label("avg_booking")
    ).join(models.Scores, models.Call.id == models.Scores.call_id)\
     .filter(models.Call.advisor_id.in_(advisor_ids))\
     .filter(models.Call.status == "done").first()
     
    tag_count = db_session.query(func.count(models.Tag.id))\
        .join(models.Call, models.Tag.call_id == models.Call.id)\
        .filter(models.Call.advisor_id.in_(advisor_ids))\
        .filter(models.Tag.contest_status != "overturned").scalar() or 0
        
    # Pending disputes count
    pending_contests = db_session.query(func.count(models.Contest.id))\
        .join(models.Tag, models.Contest.tag_id == models.Tag.id)\
        .join(models.Call, models.Tag.call_id == models.Call.id)\
        .filter(models.Call.advisor_id.in_(advisor_ids))\
        .filter(models.Tag.contest_status == "pending").scalar() or 0
        
    # Advisors score list
    advisors_list = []
    for advisor in advisors:
        adv_stats = db_session.query(
            func.count(models.Call.id).label("total"),
            func.avg(models.Scores.overall).label("avg_overall")
        ).join(models.Scores, models.Call.id == models.Scores.call_id)\
         .filter(models.Call.advisor_id == advisor.id)\
         .filter(models.Call.status == "done").first()
         
        total_adv_calls = adv_stats.total if adv_stats and adv_stats.total is not None else 0
        avg_adv_overall = round(adv_stats.avg_overall, 2) if adv_stats and adv_stats.avg_overall is not None else 0.0
        
        advisors_list.append(schemas.AdvisorScoreRow(
            advisor_id=advisor.id,
            advisor_name=advisor.name,
            total_calls=total_adv_calls,
            overall_average=avg_adv_overall
        ))
        
    total_calls = stats.total if stats and stats.total is not None else 0
    overall_avg = round(stats.avg_overall, 2) if stats and stats.avg_overall is not None else 0.0
    
    dimension_averages = {
        "needs_discovery": round(stats.avg_discovery, 2) if stats and stats.avg_discovery is not None else 0.0,
        "product_knowledge": round(stats.avg_product, 2) if stats and stats.avg_product is not None else 0.0,
        "objection_handling": round(stats.avg_objection, 2) if stats and stats.avg_objection is not None else 0.0,
        "compliance": round(stats.avg_compliance, 2) if stats and stats.avg_compliance is not None else 0.0,
        "trial_booking": round(stats.avg_booking, 2) if stats and stats.avg_booking is not None else 0.0,
    }
    
    return schemas.TeamSummaryResponse(
        team_id=team_id,
        team_name=team.name,
        total_calls=total_calls,
        overall_average=overall_avg,
        dimension_averages=dimension_averages,
        compliance_tag_count=tag_count,
        advisors=advisors_list,
        pending_contests_count=pending_contests
    )

@router.get("/advisors/{advisor_id}/summary", response_model=schemas.AdvisorSummaryResponse)
def get_advisor_summary(advisor_id: int, db_session: Session = Depends(db.get_db)):
    """
    Computes individual advisor quality dimensions, overall average, and recent call list (Advisor view).
    """
    advisor = db_session.query(models.Advisor).filter(models.Advisor.id == advisor_id).first()
    if not advisor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Advisor with ID {advisor_id} not found."
        )
        
    team = db_session.query(models.Team).filter(models.Team.id == advisor.team_id).first()
    team_name = team.name if team else "Unknown Team"
    
    # Advisor averages
    stats = db_session.query(
        func.count(models.Call.id).label("total"),
        func.avg(models.Scores.overall).label("avg_overall"),
        func.avg(models.Scores.needs_discovery).label("avg_discovery"),
        func.avg(models.Scores.product_knowledge).label("avg_product"),
        func.avg(models.Scores.objection_handling).label("avg_objection"),
        func.avg(models.Scores.compliance).label("avg_compliance"),
        func.avg(models.Scores.trial_booking).label("avg_booking")
    ).join(models.Scores, models.Call.id == models.Scores.call_id)\
     .filter(models.Call.advisor_id == advisor_id)\
     .filter(models.Call.status == "done").first()
     
    # List recent 10 calls
    recent_calls_db = db_session.query(models.Call)\
        .filter(models.Call.advisor_id == advisor_id)\
        .order_by(models.Call.created_at.desc())\
        .limit(10).all()
        
    recent_calls = []
    for call in recent_calls_db:
        score = call.scores.overall if call.scores else None
        recent_calls.append(schemas.RecentCallRow(
            call_id=call.id,
            source_call_id=call.source_call_id,
            created_at=call.created_at,
            overall_score=score,
            status=call.status
        ))
        
    total_calls = stats.total if stats and stats.total is not None else 0
    overall_avg = round(stats.avg_overall, 2) if stats and stats.avg_overall is not None else 0.0
    
    dimension_averages = {
        "needs_discovery": round(stats.avg_discovery, 2) if stats and stats.avg_discovery is not None else 0.0,
        "product_knowledge": round(stats.avg_product, 2) if stats and stats.avg_product is not None else 0.0,
        "objection_handling": round(stats.avg_objection, 2) if stats and stats.avg_objection is not None else 0.0,
        "compliance": round(stats.avg_compliance, 2) if stats and stats.avg_compliance is not None else 0.0,
        "trial_booking": round(stats.avg_booking, 2) if stats and stats.avg_booking is not None else 0.0,
    }
    
    return schemas.AdvisorSummaryResponse(
        advisor_id=advisor_id,
        advisor_name=advisor.name,
        team_name=team_name,
        total_calls=total_calls,
        overall_average=overall_avg,
        dimension_averages=dimension_averages,
        recent_calls=recent_calls
    )
