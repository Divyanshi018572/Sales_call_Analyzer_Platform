# Ingestion and Storage Component

**What it does:**
Scans a target directory for new call audio files, normalizes the files and metadata into source-agnostic `CallEvent` schemas, and stores them transactionally in a relational PostgreSQL database.

**Why built this way:**
- **Decoupled Ingestion**: We introduced a Pydantic `CallEvent` layer as an intermediary. Ingestion adapters normalize metadata to this schema, meaning telephony or CRM changes won't break database logic.
- **Normalized Hierarchy**: Organized the database relations as `Orgs` -> `Teams` -> `Advisors` -> `Calls`. This models the actual company structure and allows easy rollup calculations.
- **Idempotency**: Set a unique constraint on `(source_system, source_call_id)` in the `calls` table, preventing the orchestrator from duplicate processing of the same call.
- **No Alembic Migration**: For the prototype's 30h timeline, we used `Base.metadata.create_all(bind=engine)` inside the API startup loop. This guarantees instant setup for the evaluator without manual script runs, though Alembic would be the production alternative.

**Inputs / outputs:**
- **Input**: Local WAV audio files stored under `data/mock_calls/`.
- **Output**: Relational records created or verified in `orgs`, `teams`, `advisors`, and `calls` tables (with status set to `pending`).

**Edge cases handled here:**
- **Duplicate Ingestion**: If the same file is processed again, the `uq_source_call` constraint catches the duplicate and returns the existing call ID instead of double-inserting.
- **Missing Advisor Details**: The database model permits `advisor_id` to be null, accommodating telephony systems where caller identification fails.

**Known gaps / what I'd do with more time:**
- Use **Alembic** migrations to support live production database changes.
- Replace the folder poller with a reactive **file system watcher** (`watchdog`) to instantly trigger ingestion when a telephony recording is saved.
