# Transcription and Diarisation Component

**What it does:**
Splits stereo audio recordings into separate mono files for Advisor and Customer, transcribes each track independently using local `faster-whisper` (handling code-switched Hindi-English), merges segments chronologically, and cleans up temporary files.

**Why built this way:**
- **Deterministic Diarisation**: Speaker diarisation is solved deterministically by splitting stereo channels: Channel 0 is the Advisor, Channel 1 is the Customer. This provides 100% speaker assignment accuracy at zero runtime machine learning compute cost.
- **Multilingual Support**: Runs transcription with `language=None` (auto-detect per segment) rather than forcing English or Hindi. This allows Whisper to seamlessly transcribe Hindi-English code-switched speech segment-by-segment.
- **Lazy Loading**: Initializes the Whisper model only when the first transcription is requested. This reduces application startup time and resource footprint.

**Inputs / outputs:**
- **Input**: Local WAV audio file (stereo or mono).
- **Output**: 
  - `full_text` (str): Full transcribed call text.
  - `segments` (List[dict]): List of segments containing `speaker`, `start` timestamp, `end` timestamp, and `text`.
  - `diarisation_confidence` (str): `high` for stereo, `low` for mono.

**Edge cases handled here:**
- **Mono Fallback**: If a call recording is mono, channel splitting is skipped. The adapter transcribes it as a single track, assigns segments to a generic `Speaker` label, and flags the diarisation confidence as `low` to alert downstream views.
- **Resource Leakage**: Uses Python's `try...finally` block to guarantee that temporary mono split WAV files are deleted from the disk after transcription, even if the Whisper run fails or is interrupted.

**Known gaps / what I'd do with more time:**
- Integrate `pyannote.audio` for speaker diarisation on mono calls to resolve speaker identities when channel-split is not available.
- Transcribe the split channels in parallel threads to double processing speed on multi-core CPU/GPU systems.
