"""
Concrete folder ingestion adapter simulating telephony file exports.

Why this approach:
This adapter monitors a local folder for WAV files, implementing the BaseAdapter interface.
It parses files and maps them to CallEvent objects. To simulate realistic advisor assignments
without manual telemetry inputs, it maps each call deterministically to a mock advisor 
using the filename's hash.
"""

import os
from typing import List
from src.ingestion.base_adapter import BaseAdapter
from src.ingestion.schemas import CallEvent
from src.config import settings

class FolderAdapter(BaseAdapter):
    """
    Concrete adapter reading call records from a local folder directory.
    """
    
    def __init__(self, directory_path: str = None):
        """
        Initializes the adapter with a target directory.
        """
        self.directory_path = directory_path or settings.MOCK_CALLS_DIR
        # Fixed pool of mock advisors to map files to
        self.mock_advisors = ["Rohan", "Sneha", "Amit", "Priya"]
        
    def fetch_new_calls(self) -> List[CallEvent]:
        """
        Scans the configured directory for .wav files.
        
        Returns:
            List[CallEvent]: Staged call events ready for database processing.
        """
        events = []
        if not os.path.exists(self.directory_path):
            return events
            
        for filename in os.listdir(self.directory_path):
            if filename.endswith(".wav"):
                filepath = os.path.join(self.directory_path, filename)
                
                # Deterministic advisor assignment using hash
                advisor_index = abs(hash(filename)) % len(self.mock_advisors)
                advisor_name = self.mock_advisors[advisor_index]
                
                event = CallEvent(
                    source_system="folder",
                    source_call_id=filename,
                    recording_path=os.path.abspath(filepath),
                    advisor_name=advisor_name
                )
                events.append(event)
                
        return events
