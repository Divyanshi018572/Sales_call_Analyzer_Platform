"""
SQLAlchemy ORM models representing the database schema.

Why this approach:
We define explicit SQLAlchemy schema mappings to match the Postgres tables specified in PLAN.md §4.
By building relational constraints (ForeignKeys, UniqueConstraints) and relationships, we enforce
referential integrity (e.g. cascading deletes for a call's scores and transcripts) and allow clean
object-based querying. A UniqueConstraint is declared on (source_system, source_call_id) to guarantee
idempotent call ingestion.
"""

import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, JSON
from sqlalchemy.orm import relationship
from src.storage.db import Base

class Org(Base):
    """
    Represents an Organization (highest level in hierarchy).
    """
    __tablename__ = "orgs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    
    # Relationships
    teams = relationship("Team", back_populates="org", cascade="all, delete-orphan")

class Team(Base):
    """
    Represents a Pod/Team within an organization, managed by a Team Leader.
    """
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    
    # Relationships
    org = relationship("Org", back_populates="teams")
    advisors = relationship("Advisor", back_populates="team", cascade="all, delete-orphan")

class Advisor(Base):
    """
    Represents a Tele-advisor who makes sales calls.
    """
    __tablename__ = "advisors"
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    
    # Relationships
    team = relationship("Team", back_populates="advisors")
    calls = relationship("Call", back_populates="advisor")

class Call(Base):
    """
    Represents an ingested sales call recording and its metadata.
    """
    __tablename__ = "calls"
    id = Column(Integer, primary_key=True, index=True)
    advisor_id = Column(Integer, ForeignKey("advisors.id", ondelete="SET NULL"), nullable=True)
    source_system = Column(String, nullable=False) # e.g. 'folder', 'telephony_api'
    source_call_id = Column(String, nullable=False) # unique call ID inside the source system
    recording_path = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False) # pending, processing, done, failed, skipped
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    # Idempotency constraint: cannot ingest the same call twice from the same telephony source
    __table_args__ = (
        UniqueConstraint("source_system", "source_call_id", name="uq_source_call"),
    )
    
    # Relationships
    advisor = relationship("Advisor", back_populates="calls")
    transcript = relationship("Transcript", back_populates="call", uselist=False, cascade="all, delete-orphan")
    scores = relationship("Scores", back_populates="call", uselist=False, cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="call", cascade="all, delete-orphan")

class Transcript(Base):
    """
    Represents the transcription and diarisation output of a call.
    """
    __tablename__ = "transcripts"
    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, unique=True)
    full_text = Column(String, nullable=False)
    segments_json = Column(JSON, nullable=False) # Stores timestamped speaker utterances
    diarisation_confidence = Column(String, nullable=False) # 'high' (stereo split), 'low' (mono fallback)
    
    # Relationships
    call = relationship("Call", back_populates="transcript")

class Scores(Base):
    """
    Represents the evaluation scores of a call along the sales rubric.
    """
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, unique=True)
    needs_discovery = Column(Float, nullable=False)
    product_knowledge = Column(Float, nullable=False)
    objection_handling = Column(Float, nullable=False)
    compliance = Column(Float, nullable=False)
    trial_booking = Column(Float, nullable=False)
    overall = Column(Float, nullable=False)
    
    # Relationships
    call = relationship("Call", back_populates="scores")

class Tag(Base):
    """
    Represents compliance issue flags raised by the analysis engine.
    """
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id", ondelete="CASCADE"), nullable=False)
    type = Column(String, nullable=False) # e.g. 'over-promising', 'urgency-tactics'
    severity = Column(String, nullable=False) # critical, warning
    timestamp_sec = Column(Float, nullable=False)
    quoted_line = Column(String, nullable=False) # Verified transcript excerpt
    reason = Column(String, nullable=False)
    contest_status = Column(String, default="none", nullable=False) # none, pending, upheld, overturned
    
    # Relationships
    call = relationship("Call", back_populates="tags")
    contest = relationship("Contest", back_populates="tag", uselist=False, cascade="all, delete-orphan")

class Contest(Base):
    """
    Represents an advisor's dispute of a specific compliance tag.
    """
    __tablename__ = "contests"
    id = Column(Integer, primary_key=True, index=True)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, unique=True)
    advisor_note = Column(String, nullable=False)
    resolved_by = Column(Integer, nullable=True) # Advisor/TL who resolved it
    resolution_note = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    tag = relationship("Tag", back_populates="contest")
