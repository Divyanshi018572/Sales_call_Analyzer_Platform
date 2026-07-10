"""
Pydantic schemas for the ingestion layer.

Why this approach:
We use Pydantic models to define a strict, source-agnostic interface for incoming call events.
This decouples the database layer and downstream pipeline from vendor-specific telemetry formats,
allowing different adapters to feed the same data structure into the system.
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional

class CallEvent(BaseModel):
    """
    Data model representing a normalized call event produced by any ingestion adapter.
    """
    model_config = ConfigDict(frozen=True)

    source_system: str
    source_call_id: str
    recording_path: str
    advisor_name: Optional[str] = None
