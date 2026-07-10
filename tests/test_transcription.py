"""
Tests for the audio transcription and diarisation component.

Why this approach:
We test the Transcriber wrapper directly against a real extracted WAV sample (call_4507.wav).
This verifies that faster-whisper loads, transcribes Indic-audio speech, performs stereo-channel
splitting, chronologically merges segments, and successfully deletes temporary tracks.
"""

import os
import pytest
from src.transcription.transcriber import Transcriber

def test_transcription_on_stereo_sample():
    """
    Test that transcribing a real stereo WAV file produces a structured transcript,
    diarises the conversation, and cleans up the temporary files.
    """
    sample_file = "data/mock_calls/call_4507.wav"
    assert os.path.exists(sample_file), f"Test WAV file not found: {sample_file}"
    
    # Initialize transcriber with 'tiny' model for fast test execution on CPU
    transcriber = Transcriber(model_size="tiny", device="cpu", compute_type="int8")
    
    full_text, segments, confidence = transcriber.transcribe_call(sample_file)
    
    # Assertions on transcription results
    assert len(full_text) > 0, "Transcript is empty."
    assert len(segments) > 0, "No transcription segments were found."
    assert confidence == "high", "Diarisation confidence should be high for stereo sample."
    
    # Check segment structure
    for segment in segments:
        assert "speaker" in segment
        assert segment["speaker"] in ["Advisor", "Customer"]
        assert "start" in segment
        assert "end" in segment
        assert "text" in segment
        assert isinstance(segment["start"], (int, float))
        assert isinstance(segment["end"], (int, float))
        assert len(segment["text"]) > 0
        
    # Check that segments are sorted chronologically
    for i in range(len(segments) - 1):
        assert segments[i]["start"] <= segments[i + 1]["start"], "Segments are not sorted chronologically."
        
    # Verify cleanup of temporary split files
    base_dir = os.path.dirname(sample_file)
    base_name = os.path.splitext(os.path.basename(sample_file))[0]
    left_temp = os.path.join(base_dir, f"{base_name}_advisor_mono.wav")
    right_temp = os.path.join(base_dir, f"{base_name}_customer_mono.wav")
    
    assert not os.path.exists(left_temp), "Advisor temporary mono file was not cleaned up."
    assert not os.path.exists(right_temp), "Customer temporary mono file was not cleaned up."
