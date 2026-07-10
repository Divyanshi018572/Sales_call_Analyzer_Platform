"""
Analysis orchestration engine (Tagger).

Why this approach:
We provide a unified `evaluate_transcript` function to manage the analysis workflow.
It calls our provider-agnostic `llm_client` to get scores and tags, verifies compliance
quotes literally against the transcription text (via `verifier`), filters out false-positives,
and calculates the overall weighted score (applying penalties for critical violations via `rubric`).
If a call is classified as a non-sales call, it skips scoring and tagging entirely.
"""

from typing import List, Dict, Any
from src.analysis.llm_client import analyze_call
from src.analysis.verifier import verify_and_clean_tags
from src.analysis.rubric import calculate_overall_score

def evaluate_transcript(transcript_text: str, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluates a transcript by classifying it, scoring it, and raising verified tags.
    
    Args:
        transcript_text (str): Full raw text of the transcription.
        segments (List[Dict[str, Any]]): Time-aligned segments from the transcriber.
        
    Returns:
        Dict[str, Any]: Consolidated evaluation dictionary containing:
            - call_type: 'sales' or 'non-sales'
            - reasoning: text explaining the evaluation
            - scores: dictionary of individual dimension scores (empty if non-sales)
            - overall: calculated overall quality score (0.0 if non-sales)
            - tags: list of verified compliance tags (empty if non-sales)
    """
    # 1. Fetch analysis from LLM client (Gemini -> Groq -> Mock fallback)
    raw_analysis = analyze_call(transcript_text)
    
    call_type = raw_analysis.get("call_type", "sales").lower()
    reasoning = raw_analysis.get("reasoning", "")
    
    # 2. Check if call is classified as non-sales (wrong number, disconnected, etc.)
    if call_type == "non-sales":
        return {
            "call_type": "non-sales",
            "reasoning": reasoning,
            "scores": {},
            "overall": 1.0,  # Minimum score boundary
            "tags": []
        }
        
    # 3. Process sales call
    raw_scores = raw_analysis.get("scores", {})
    raw_tags = raw_analysis.get("tags", [])
    
    # 4. Verify tags and resolve timestamps programmatically
    verified_tags = verify_and_clean_tags(transcript_text, segments, raw_tags)
    
    # 5. Count critical tags to apply penalty
    critical_count = sum(1 for tag in verified_tags if tag.get("severity") == "critical")
    
    # 6. Calculate overall score using weighted averages and penalties
    overall_score = calculate_overall_score(raw_scores, critical_count)
    
    # 7. Force standard scores structure
    final_scores = {
        "needs_discovery": float(raw_scores.get("needs_discovery", 1.0)),
        "product_knowledge": float(raw_scores.get("product_knowledge", 1.0)),
        "objection_handling": float(raw_scores.get("objection_handling", 1.0)),
        "compliance": float(raw_scores.get("compliance", 1.0)),
        "trial_booking": float(raw_scores.get("trial_booking", 1.0))
    }
    
    return {
        "call_type": "sales",
        "reasoning": reasoning,
        "scores": final_scores,
        "overall": overall_score,
        "tags": verified_tags
    }
