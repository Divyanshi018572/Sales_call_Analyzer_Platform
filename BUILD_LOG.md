# Build Log - FitNova Sales-Call Intelligence

This log documents the incremental fixes, improvements, and features added to the codebase.

## 2026-07-11 - PII Redaction Feature

### Changes
- **Pipeline Orchestrator**: Moved the PII redaction pass to `src/pipeline/orchestrator.py` before transcripts are saved to the database or evaluated by the LLM.
- **Transcription**: Removed PII redaction from `src/transcription/transcriber.py` to enforce clean separation of concerns.
- **Regex Robustness**: Updated `PHONE_PATTERN` in `src/transcription/redactor.py` to properly capture leading `+` signs and spaces (e.g. `+91 99999 88888`).
- **Testing**: Added integration test `test_pipeline_pii_redaction` in `tests/test_pipeline_e2e.py` verifying that phone numbers and email addresses are correctly redacted from transcripts in the database.

### Verification
- All tests in `tests/test_pipeline_e2e.py`, `tests/test_transcription.py`, and `tests/test_storage.py` passed successfully.
