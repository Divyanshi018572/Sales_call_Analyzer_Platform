# Pipeline Orchestrator Component

**What it does:**
Binds the ingestion call records, local Whisper transcription, LLM-based quality analysis, and SQL storage together into a single transaction-wrapped processing sequence.

**Why built this way:**
- **Centralized Pipeline**: Avoids scattered execution logic by wrapping all steps inside `process_call(db, call_id)`.
- **Idempotency Gate**: First checks if a call's status is already `done` or `skipped`. If so, it returns immediately without invoking the transcriber or LLM, preventing duplicate CPU processing or double API billing.
- **State Control**: Transitions status from `pending` -> `processing` -> `done` (or `skipped` for non-sales calls), and handles transaction rollbacks on failures to prevent partial writes.

**Inputs / outputs:**
- **Input**:
  - `call_id` (int): Unique database ID of the ingested Call record.
- **Output**:
  - `models.Call`: The updated Call database object, with related transcript, scores, and tag records persisted in Postgres.

**Edge cases handled here:**
- **Reprocessing Prevention**: Ensured by the idempotency gate, making the pipeline safe to retry.
- **Transactional Rollback**: Uses `db.rollback()` in the `except` block to abort all partial inserts (e.g. transcript written but scores failed) and updates the call status to `failed` for visibility.

**Known gaps / what I'd do with more time:**
- Implement an **asynchronous task queue** (such as Celery or RQ) to move transcription and analysis workloads to background workers instead of blocking the FastAPI thread.
- Configure a **processing timeout watchdog** to automatically release and mark as `failed` any calls stuck in `processing` state for more than 15 minutes.
