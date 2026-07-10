# FastAPI API Routers Component

**What it does:**
Exposes the ingestion adapter, processing pipeline orchestrator, organizational summaries, and dispute contests to the dashboard through RESTful HTTP endpoints.

**Why built this way:**
- **Separated Concerns**: Grouped logically into three routers: `calls` (ingestion, list, detail, process), `summaries` (org, team, advisor rollups), and `contests` (disputes and resolutions).
- **Database Rollups**: Averages and counts are calculated directly in Postgres using SQLAlchemy aggregations (`func.avg`, `func.count`), resulting in sub-50ms response times.
- **Recalculation Loop**: Resolving a dispute as `overturned` immediately re-evaluates the call's overall score by removing the compliance penalty, keeping scorecards synchronized.

**Inputs / outputs:**
- **Input**: REST payloads (e.g. JSON bodies for disputes/resolutions, query filters for listings).
- **Output**: Validated Pydantic models (e.g. `CallDetailResponse`, `TeamSummaryResponse`, `ContestResponse`).

**Edge cases handled here:**
- **Zero-State Summaries**: If an org, team, or advisor has no processed calls, the API catches null values and returns `0.0` for averages instead of causing dashboard parsing errors.
- **Database Mismatch Safeguards**: The API router validates the TL resolving disputes against an integer column `resolved_by`, matching the DB model.
- **Disputed Call Recalculations**: Re-runs the scoring logic to deduct critical penalties for overturned tags.

**Known gaps / what I'd do with more time:**
- Implement role-based access control (RBAC) via JWT tokens so Advisors can only query their own summaries, while Team Leaders can resolve disputes.
- Add request rate-limiting (e.g. using `slowapi`) to prevent denial-of-service on resource-heavy Whisper transcription triggers.
- Cache summary statistics in Redis to eliminate redundant database queries on static historical data.
