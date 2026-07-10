"""
Hallucination guard and quote verification engine.

Why this approach:
Large Language Models are prone to hallucinating or misrepresenting conversational evidence.
To prevent false compliance flags, this module verifies that the LLM's 'quoted_line' exists 
as a literal substring inside the actual transcription text (case-insensitive and standardized).
If verified, we match the quote against individual transcription segments to resolve the exact
start timestamp. If unverified, the tag is rejected and dropped from database storage.
"""

import re
from typing import List, Dict, Optional

def standardize_text(text: str) -> str:
    """
    Normalizes a string by converting it to lowercase, stripping surrounding quotes,
    removing punctuation/special characters, and collapsing whitespace.
    
    Args:
        text (str): Raw string.
        
    Returns:
        str: Standardized alphanumeric string.
    """
    if not text:
        return ""
    text = text.lower().strip()
    # Strip enclosing quotes
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1]
    # Remove punctuation
    text = re.sub(r"[^\w\s]", "", text)
    # Collapse multiple whitespaces
    return " ".join(text.split())

def verify_tag_quote(quoted_line: str, full_transcript: str) -> bool:
    """
    Verifies if the standardized quoted line is a substring of the standardized full transcript.
    """
    standard_quote = standardize_text(quoted_line)
    standard_transcript = standardize_text(full_transcript)
    
    if not standard_quote:
        return False
        
    return standard_quote in standard_transcript

def resolve_tag_timestamp(quoted_line: str, segments: List[Dict]) -> float:
    """
    Scans transcription segments to find where the quoted line is located,
    returning the start timestamp of the matching segment.
    
    Args:
        quoted_line (str): The compliance violation quote.
        segments (List[Dict]): Transcription segments containing (speaker, start, end, text).
        
    Returns:
        float: Start timestamp in seconds. Defaults to 0.0 if not found.
    """
    standard_quote = standardize_text(quoted_line)
    if not standard_quote or not segments:
        return 0.0
        
    # 1. Search for matching quote inside a single segment
    for segment in segments:
        standard_segment_text = standardize_text(segment.get("text", ""))
        if standard_quote in standard_segment_text:
            return float(segment.get("start", 0.0))
            
    # 2. Fallback: if quote spans multiple segments, match on the first 3 words
    words = standard_quote.split()
    if len(words) >= 3:
        beginning_snippet = " ".join(words[:3])
        for segment in segments:
            standard_segment_text = standardize_text(segment.get("text", ""))
            if beginning_snippet in standard_segment_text:
                return float(segment.get("start", 0.0))
                
    # 3. Default fallback: return start of first segment or 0.0
    return float(segments[0].get("start", 0.0))

def verify_and_clean_tags(full_transcript: str, segments: List[Dict], raw_tags: List[Dict]) -> List[Dict]:
    """
    Filters raw LLM tags, dropping those that fail quote verification,
    and populating the correct start timestamps.
    
    Args:
        full_transcript (str): Full text of the call.
        segments (List[Dict]): Timestamps segments from transcription.
        raw_tags (List[Dict]): Raw tag dictionaries from the LLM.
        
    Returns:
        List[Dict]: Verified tags with resolved timestamps.
    """
    verified_tags = []
    
    for tag in raw_tags:
        quoted_line = tag.get("quoted_line", "")
        
        # Guard: check if the quote is found in the transcript
        if not verify_tag_quote(quoted_line, full_transcript):
            # Quote failed verification -> Drop tag to prevent false-positives
            continue
            
        # Quote verified -> Resolve its timestamp from segments
        timestamp = resolve_tag_timestamp(quoted_line, segments)
        
        verified_tag = {
            "type": tag.get("type"),
            "severity": tag.get("severity", "warning").lower(),
            "timestamp_sec": timestamp,
            "quoted_line": quoted_line,
            "reason": tag.get("reason", "")
        }
        verified_tags.append(verified_tag)
        
    return verified_tags
