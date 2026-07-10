"""
Audio transcription module using faster-whisper.

Why this approach:
We wrap the faster-whisper library to run multilingual transcription (auto-detecting segments 
to support Hindi-English code-switching). To achieve zero-compute speaker diarisation, we split 
stereo audio, transcribe the Advisor and Customer channels independently, tag their segments 
with the appropriate speaker name, merge them, sort them chronologically, and clean up temporary 
audio files.
"""

import os
from typing import Tuple, List, Dict
from faster_whisper import WhisperModel
from src.transcription.diarizer import split_stereo_audio
from src.config import settings

class Transcriber:
    """
    Service class wrapping the faster-whisper model and handling dual-channel chronological merging.
    """
    
    def __init__(self, model_size: str = None, device: str = "cpu", compute_type: str = "int8"):
        """
        Initializes transcriber configurations. Lazy loads the model on demand.
        """
        self.model_size = model_size or settings.WHISPER_MODEL_NAME
        self.device = device
        self.compute_type = compute_type
        self._model = None
        
    @property
    def model(self) -> WhisperModel:
        """
        Lazy loader for the WhisperModel to avoid overhead at import time.
        """
        if self._model is None:
            self._model = WhisperModel(
                self.model_size, 
                device=self.device, 
                compute_type=self.compute_type
            )
        return self._model
        
    def _transcribe_channel(self, audio_path: str, speaker_name: str) -> List[dict]:
        """
        Transcribes a single audio channel and tags segments with the speaker's identity.
        """
        segments, _ = self.model.transcribe(audio_path, beam_size=5, language=None)
        result = []
        for segment in segments:
            result.append({
                "speaker": speaker_name,
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip()
            })
        return result
        
    def transcribe_call(self, filepath: str) -> Tuple[str, List[dict], str]:
        """
        Orchestrates channel splitting, individual channel transcriptions, 
        chronological segment sorting, and cleanup.
        
        Args:
            filepath (str): Path to the source WAV file.
            
        Returns:
            Tuple[str, List[dict], str]: 
                - full_text: The concatenated text of the whole call.
                - segments: List of dictionaries with keys (speaker, start, end, text).
                - diarisation_confidence: 'high' (stereo split) or 'low' (mono fallback).
        """
        # 1. Split stereo into separate files if stereo, or return source if mono
        advisor_path, customer_path, confidence = split_stereo_audio(filepath)
        
        segments = []
        try:
            if customer_path:
                # Stereo recording: transcribe channels separately
                advisor_segments = self._transcribe_channel(advisor_path, "Advisor")
                customer_segments = self._transcribe_channel(customer_path, "Customer")
                segments = advisor_segments + customer_segments
            else:
                # Mono recording: transcribe single channel as Advisor/Speaker fallback
                segments = self._transcribe_channel(advisor_path, "Speaker")
                
            # 2. Sort all segments chronologically by start timestamp
            segments.sort(key=lambda x: x["start"])
            
            # 3. Join all segments into a single full text string
            full_text = " ".join([seg["text"] for seg in segments])
            
            return full_text, segments, confidence
            
        finally:
            # 4. Clean up temporary split files if they were created
            if customer_path:
                if os.path.exists(advisor_path):
                    try:
                        os.remove(advisor_path)
                    except Exception:
                        pass
                if os.path.exists(customer_path):
                    try:
                        os.remove(customer_path)
                    except Exception:
                        pass
