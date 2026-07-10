"""
Pydantic validation schemas for the FastAPI layer.

Why this approach:
We define structured request and response models to enforce type validation and output shape.
By separating external API contracts from internal SQLAlchemy models, we prevent exposing 
internal database details directly and simplify JSON serialization (like converting datetimes).
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ScoresResponse(BaseModel):
    """
    Response model for call evaluation scores.
    """
    needs_discovery: float
    product_knowledge: float
    objection_handling: float
    compliance: float
    trial_booking: float
    overall: float

    model_config = {"from_attributes": True}

class TagResponse(BaseModel):
    """
    Response model for call compliance tags.
    """
    id: int
    type: str
    severity: str
    timestamp_sec: float
    quoted_line: str
    reason: str
    contest_status: str

    model_config = {"from_attributes": True}

class TranscriptResponse(BaseModel):
    """
    Response model for call transcripts.
    """
    full_text: str
    segments_json: List[Dict[str, Any]]
    diarisation_confidence: str

    model_config = {"from_attributes": True}

class CallResponse(BaseModel):
    """
    Response model for list call endpoints.
    """
    id: int
    advisor_id: Optional[int] = None
    source_system: str
    source_call_id: str
    recording_path: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}

class CallDetailResponse(CallResponse):
    """
    Response model for detailed single call queries, embedding transcripts and evaluations.
    """
    transcript: Optional[TranscriptResponse] = None
    scores: Optional[ScoresResponse] = None
    tags: List[TagResponse] = []

class OrgSummaryResponse(BaseModel):
    """
    Response model representing org-wide rollup metrics.
    """
    org_id: int
    org_name: str
    total_calls: int
    overall_average: float
    dimension_averages: Dict[str, float]
    compliance_tag_count: int

class AdvisorScoreRow(BaseModel):
    """
    Inner schema representing a team's advisor rollup.
    """
    advisor_id: int
    advisor_name: str
    total_calls: int
    overall_average: float

class TeamSummaryResponse(BaseModel):
    """
    Response model representing team rollup metrics for Team Leaders.
    """
    team_id: int
    team_name: str
    total_calls: int
    overall_average: float
    dimension_averages: Dict[str, float]
    compliance_tag_count: int
    advisors: List[AdvisorScoreRow]
    pending_contests_count: int

class RecentCallRow(BaseModel):
    """
    Inner schema representing an advisor's call history.
    """
    call_id: int
    source_call_id: str
    created_at: datetime
    overall_score: Optional[float] = None
    status: str

class AdvisorSummaryResponse(BaseModel):
    """
    Response model representing advisor rollup metrics for individual dashboards.
    """
    advisor_id: int
    advisor_name: str
    team_name: str
    total_calls: int
    overall_average: float
    dimension_averages: Dict[str, float]
    recent_calls: List[RecentCallRow]

class ContestRequest(BaseModel):
    """
    Request model for an advisor to contest/dispute a tag.
    """
    advisor_note: str = Field(..., min_length=3, max_length=500, description="Reason for disputing this tag.")

class ContestResolveRequest(BaseModel):
    """
    Request model for a Team Leader to resolve a dispute.
    """
    resolved_by: int = Field(..., description="ID of the Advisor/Team Leader resolving the dispute.")
    resolution_note: str = Field(..., min_length=3, max_length=500, description="Notes on the decision.")
    decision: str = Field(..., pattern="^(upheld|overturned)$", description="Whether the dispute is upheld or overturned.")

class ContestResponse(BaseModel):
    """
    Response model representing a dispute record.
    """
    id: int
    tag_id: int
    advisor_note: str
    resolved_by: Optional[int] = None
    resolution_note: Optional[str] = None
    resolved_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
