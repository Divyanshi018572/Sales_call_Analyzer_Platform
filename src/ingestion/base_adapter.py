"""
Abstract base class for ingestion adapters.

Why this approach:
We define a formal interface using python's built-in abc module. Any telephony, CRM, or file source
must implement this class to scan and normalize its records into CallEvent objects. This design
enforces the non-negotiable rule that no vendor-specific code resides outside this adaptation layer.
"""

from abc import ABC, abstractmethod
from typing import List
from src.ingestion.schemas import CallEvent

class BaseAdapter(ABC):
    """
    Abstract interface for all telephony, file system, or CRM call recording adapters.
    """
    
    @abstractmethod
    def fetch_new_calls(self) -> List[CallEvent]:
        """
        Fetch new, unprocessed call events from the source.
        
        Returns:
            List[CallEvent]: A list of normalized call events.
        """
        pass
