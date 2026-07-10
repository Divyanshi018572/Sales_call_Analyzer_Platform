"""
Unit tests for the FitNova Sales-Call Analysis Engine.

Why this approach:
We test the analysis components (prompts, tagger, verifier, rubric) end to end.
We plant specific compliance issues ('guarantee 10kg weight loss in a week' and 'only have one spot left')
in a test transcript to verify that the tagger extracts them, the verifier validates their quotes
literally and resolves their timestamps, and the rubric applies appropriate penalty rollups.
We also verify that hallucinated quotes are rejected and non-sales calls are classified correctly.
"""

import pytest
from src.analysis.tagger import evaluate_transcript
from src.analysis.verifier import verify_tag_quote, verify_and_clean_tags

def test_sales_call_evaluation_with_planted_issues():
    """
    Test that a sales call with planted compliance issues is scored,
    has tags successfully verified, and has start timestamps resolved.
    """
    transcript = (
        "Hello, this is Amit. I can guarantee 10kg weight loss in a week if you sign up today. "
        "We only have one spot left!"
    )
    
    segments = [
        {
            "speaker": "Advisor",
            "start": 1.2,
            "end": 6.8,
            "text": "Hello, this is Amit. I can guarantee 10kg weight loss in a week if you sign up today."
        },
        {
            "speaker": "Advisor",
            "start": 7.0,
            "end": 9.5,
            "text": "We only have one spot left!"
        }
    ]
    
    # Run evaluation (API key absent triggers mock evaluator which matches these phrases)
    result = evaluate_transcript(transcript, segments)
    
    assert result["call_type"] == "sales"
    assert len(result["tags"]) == 2
    
    # Find tags
    over_promise_tag = next(t for t in result["tags"] if t["type"] == "over-promising")
    urgency_tag = next(t for t in result["tags"] if t["type"] == "urgency-tactics")
    
    # Assert timestamps are correctly resolved from segments
    assert over_promise_tag["timestamp_sec"] == 1.2
    assert urgency_tag["timestamp_sec"] == 7.0
    
    # Assert overall score is penalised (standard is 4.12, 1 critical tag deducts 0.5 -> ~3.62)
    assert result["overall"] < 4.0

def test_hallucination_guard_rejection():
    """
    Test that the verifier correctly filters out tags with fabricated quotes.
    """
    transcript = "Hello, welcome to FitNova. Let's talk about your fitness goals."
    segments = [{"speaker": "Advisor", "start": 0.0, "end": 5.0, "text": transcript}]
    
    # Plant a tag with a quote that is NOT in the transcript
    raw_tags = [
        {
            "type": "over-promising",
            "severity": "critical",
            "quoted_line": "we guarantee you will cure your cancer",
            "reason": "Advisor made medical claim."
        },
        {
            "type": "weak-trial-booking",
            "severity": "warning",
            "quoted_line": "fitness goals", # this quote IS in the transcript
            "reason": "Advisor mentioned goals."
        }
    ]
    
    verified_tags = verify_and_clean_tags(transcript, segments, raw_tags)
    
    # The hallucinated tag must be dropped, the valid tag should remain
    assert len(verified_tags) == 1
    assert verified_tags[0]["type"] == "weak-trial-booking"
    assert verified_tags[0]["quoted_line"] == "fitness goals"

def test_non_sales_call_classification():
    """
    Test that a non-sales call (e.g. wrong number) is classified correctly,
    skipping compliance tagging and scoring.
    """
    transcript = "Hello? Oh, sorry, wrong number. Have a good day."
    segments = [{"speaker": "Speaker", "start": 0.0, "end": 4.0, "text": transcript}]
    
    result = evaluate_transcript(transcript, segments)
    
    assert result["call_type"] == "non-sales"
    assert len(result["tags"]) == 0
    assert result["overall"] == 1.0  # defaults to 1.0 overall for non-sales
