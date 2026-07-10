# FitNova Sales-Call Intelligence — Build Plan

Source spec: `AI_ENGINEER_INTERN_SKILLOVILLa.pdf` (48h nominal window, working with a ~31h budget —
containerization and a deployed link are treated as mandatory, not optional, which adds ~1h over
the original 30h estimate). This file is the single source of truth for scope, stack, and
sequencing. Re-read it (and the original PDF) after finishing every component, before starting the
next one.

---

## 1. Tech stack — decided, with reasons

| Layer | Choice | Why this, not the alternative |
|---|---|---|
| Language | Python 3.11 | One language end to end (pipeline + API + dashboard) = less context-switching in 30h. |
| Transcription | `faster-whisper` (medium model, local) | Free, offline, handles Hindi-English code-switching decently. No per-minute API cost/rate-limit risk during a demo. |
| Diarisation | Dual-channel split first; `pyannote.audio` only if forced to handle mono | Channel-separated audio is deterministic and cheap. Blind diarisation is a real ML problem — don't burn hours tuning it; treat mono as an edge case with a documented fallback (see §5). |
| LLM (scoring/tagging) | **Google Gemini API** (`gemini-2.5-flash`), free tier — **fallback: Groq** (`llama-3.3-70b-versatile`), also free | Gemini free tier is the most generous + highest-quality free option available, supports structured/JSON output needed for reliable tagging. Groq is the fallback if Gemini's daily quota is hit or the call fails — wrap both behind a single `analyze_call()` function so the rest of the pipeline never knows which provider actually answered. |
| Database | PostgreSQL via `docker-compose`, `SQLAlchemy` ORM | Relational fits the org→team→advisor→call hierarchy and rollup aggregation queries. One `docker-compose up` = zero manual setup for the evaluator. |
| Backend API | FastAPI | Async-friendly, auto-generates OpenAPI docs (useful when they say "we may ask you to explain any part"), typed request/response models via Pydantic catch bugs early. |
| Frontend/dashboard | Streamlit | Pure Python, no separate frontend build step — fastest path to the 3 required views (org/team/advisor) inside a 30h budget. *(Stretch, only if time remains after core loop works: restyle with Next.js — do not attempt this before the core pipeline is proven end to end.)* |
| Orchestration | Plain Python function chain, called synchronously per call | Celery/queues add real value at scale but are not needed to prove the design in a prototype — mention them in the writeup as the production upgrade path instead of building them. |
| Testing | `pytest` | Standard, fast, works for both unit tests (per module) and one end-to-end pipeline test. |
| Containerization | Docker, multi-stage builds, `docker-compose` for local orchestration | Every service (DB, API, dashboard) runs identically on any machine — no "works on my machine" risk for the evaluator. Multi-stage keeps images small (builder stage installs deps, runtime stage copies only what's needed). |
| Deployment | Render (Web Services for API + dashboard, Managed Postgres) | Deploys directly from a Dockerfile with no extra config, free managed Postgres in the same project, gives a public URL per service — satisfies the assignment's "one clear command **or a deployed link**" directly. Considered Railway (similar, tighter free-tier caps) and AWS/GCP (too much setup overhead for this scope). |

**Decision rule for anything not listed above:** pick the option that gets one real call through
the full loop fastest, and write the trade-off down in the writeup. Do not swap a choice above
mid-build unless a component is provably blocking you for >1 hour.

---

## 2. Repository structure (modular, one responsibility per file)

```
fitnova-call-intelligence/
├── AGENTS.md
├── README.md
├── PLAN.md
├── docker-compose.yml            # 3 services: db, api, dashboard — `docker-compose up` runs everything
├── Dockerfile.api                # builds the FastAPI service image
├── Dockerfile.dashboard          # builds the Streamlit dashboard image
├── .dockerignore
├── render.yaml                   # Render Blueprint: db + api + dashboard services, one-step deploy
├── requirements.txt
├── .env.example
├── .gitignore
├── data/
│   └── mock_calls/              # sample audio + a few pre-written transcripts (edge cases)
├── docs/
│   ├── 01-ingestion.md
│   ├── 02-transcription.md
│   ├── 03-analysis-engine.md
│   ├── 04-storage.md
│   ├── 05-pipeline.md
│   ├── 06-api.md
│   ├── 07-dashboard.md
│   └── 08-feedback-loop.md      # one file per component, written when that component merges
├── src/
│   ├── config.py                # env vars, constants — nothing else
│   ├── ingestion/
│   │   ├── base_adapter.py      # abstract interface: fetch_new_calls(), normalize()
│   │   ├── folder_adapter.py    # concrete: mock "telephony" source = a folder
│   │   └── schemas.py           # normalized call-event shape
│   ├── transcription/
│   │   ├── transcriber.py       # faster-whisper wrapper only
│   │   └── diarizer.py          # channel-split / pyannote fallback only
│   ├── analysis/
│   │   ├── prompts.py           # the rubric + tag-taxonomy prompt text, nothing else
│   │   ├── rubric.py            # dimension weights, roll-up math
│   │   ├── llm_client.py        # provider-agnostic wrapper: try Gemini, fall back to Groq
│   │   ├── tagger.py            # calls llm_client, gets structured JSON back
│   │   └── verifier.py          # hallucination guard: quoted_line must exist in transcript
│   ├── storage/
│   │   ├── db.py                 # engine/session setup only
│   │   ├── models.py             # SQLAlchemy tables (see PLAN §4)
│   │   └── crud.py               # get/create functions, nothing else
│   ├── pipeline/
│   │   └── orchestrator.py       # process_call(call_id): ingest→transcribe→analyze→store,
│   │                              # idempotent (checks call.status before reprocessing)
│   └── api/
│       ├── main.py               # FastAPI app + router registration only
│       ├── schemas.py            # Pydantic request/response models
│       └── routers/
│           ├── calls.py
│           ├── summaries.py      # org/team/advisor rollups
│           └── contests.py       # feedback loop endpoints
├── dashboard/
│   └── app.py                    # Streamlit, reads from API or DB directly
├── tests/
│   ├── test_ingestion.py
│   ├── test_analysis_verifier.py # hallucination-guard test — evaluator will care about this one
│   ├── test_storage.py
│   └── test_pipeline_e2e.py      # the test that proves "one call, full loop"
└── scripts/
    └── run_demo.sh               # the ONE command the README promises
```

**Rule:** if a file is doing two jobs (e.g. fetching *and* transforming data), split it. Every file
should be explainable in one sentence — if it needs "and", split it.

---

## 2a. Test/mock audio source — `data/mock_calls/`

FitNova has no real call recordings to hand over, so `data/mock_calls/` is seeded with real
Hindi-English conversational audio pulled from a public dataset, purely to prove the
transcription/diarisation pipeline against genuine code-switched speech rather than synthetic or
silent test files.

- **Source:** `snorbyte/indic-audio-dialog-sample` (Hugging Face). Chosen over other candidates
  (`CallCenterEN` — transcripts only, no audio; `AxonData` sets — English-only, license unclear;
  `SwitchLingua` — requires a signed licensing agreement) because it ships actual multi-channel
  `.wav` audio, includes Hindi, and is designed for code-switching analysis with no license
  friction for this kind of non-commercial test use.
- **How it was obtained:** one shard (`data_shard_000_zstd.parquet`, ~380MB) downloaded manually
  from the dataset's Hugging Face page, opened with `pandas`/`pyarrow`, and the first ~5 rows'
  `audio.bytes` extracted and written out as individual `.wav` files. The parquet shard itself is
  **not** committed to the repo (too large, and not needed once the samples are extracted) — only
  the extracted `.wav` files under `data/mock_calls/` are.
- **What it is NOT:** these are not real FitNova sales calls, not fitness/coaching-domain
  conversations, and not guaranteed to be dual-channel (verify per-file; mono ones exercise the
  `pyannote` fallback path from §5). They exist solely to validate the pipeline mechanics
  (transcribe → diarise → score → tag → store) against real Hindi-English speech.
- **README requirement:** the "what is real vs mocked" table must state plainly that call audio is
  sourced from this public dataset, not FitNova, with a link to the dataset page — this is a
  non-negotiable per `AGENTS.md`.

---

## 2b. Containerization & deployment — required, not stretch

Every service runs in Docker from the start, not bolted on at the end. This is now a required
component, not an optional polish item.

- **`docker-compose.yml`** defines three services: `db` (Postgres, as before), `api` (built from
  `Dockerfile.api`, runs the FastAPI app), `dashboard` (built from `Dockerfile.dashboard`, runs
  Streamlit). `docker-compose up --build` brings up the entire system — nobody needs a local Python
  install to run this.
- **Dockerfiles are multi-stage:** a `builder` stage installs dependencies into a virtualenv, a slim
  `runtime` stage (`python:3.11-slim`) copies only that virtualenv + source code. Keeps image size
  down and avoids shipping build toolchains in the final image.
- **Ingestion/pipeline scripts are not separate services** — they stay plain function calls
  triggered through the API (`POST /calls/ingest`, `POST /calls/{id}/process`), consistent with the
  §1 decision not to introduce a queue/worker layer. Containerizing them as their own service would
  contradict that decision.
- **Local dev workflow:** `docker-compose up --build` replaces the old "pip install, then run"
  flow. `scripts/run_demo.sh` becomes a thin wrapper that calls `docker-compose up --build` and then
  hits the ingest/process endpoints.
- **Deployment target: Render.** A `render.yaml` Blueprint defines the same three services (Managed
  Postgres, API web service, dashboard web service) so the whole stack deploys from one Blueprint
  import — no manual dashboard clicking per service.
- **Secrets:** `GEMINI_API_KEY`, `GROQ_API_KEY`, and DB credentials are set as environment variables
  in Render's dashboard, never committed. `.env.example` remains the local-only template; it is not
  read in the deployed environment.
- **README gets two run paths**, not one: **(1) one command locally** — `docker-compose up --build`
  — and **(2) a deployed link** — both are explicitly permitted by the assignment ("must run, from
  one clear command **or** a deployed link"), and having both removes any single point of failure
  on demo day.

---

## 3. API endpoints (FastAPI) — 9 total, no more

| Method | Path | Purpose |
|---|---|---|
| POST | `/calls/ingest` | Pull new calls from the configured adapter into `calls` table (status=pending) |
| POST | `/calls/{call_id}/process` | Run the full pipeline for one call — idempotent, safe to retry |
| GET | `/calls` | List calls, filterable by advisor/team/status |
| GET | `/calls/{call_id}` | Full detail: transcript + scores + tags |
| GET | `/orgs/{org_id}/summary` | Org-wide rollup (Sales Director view) |
| GET | `/teams/{team_id}/summary` | Team rollup (Team Leader view) |
| GET | `/advisors/{advisor_id}/summary` | Advisor's own calls + trend (Advisor view) |
| POST | `/tags/{tag_id}/contest` | Advisor contests a flag |
| POST | `/contests/{contest_id}/resolve` | Team Leader marks upheld/overturned |

Keep this list fixed. Do not add endpoints mid-build without updating this table first.

---

## 4. Data model (Postgres tables)

```
orgs(id, name)
teams(id, org_id FK, name)
advisors(id, team_id FK, name)
calls(id, advisor_id FK, source_system, source_call_id, recording_path,
      status[pending|processing|done|failed], created_at)
      -- unique constraint on (source_system, source_call_id) = idempotency
transcripts(id, call_id FK, full_text, segments_json, diarisation_confidence)
scores(id, call_id FK, needs_discovery, product_knowledge, objection_handling,
       compliance, trial_booking, overall)
tags(id, call_id FK, type, severity, timestamp_sec, quoted_line, reason,
     contest_status[none|pending|upheld|overturned])
contests(id, tag_id FK, advisor_note, resolved_by, resolution_note, resolved_at)
```

New team/advisor = new row. No schema change ever required for growth — this directly satisfies
the "grows without manual reconfiguration" requirement.

---

## 5. Edge cases — explicit handling (don't skip, this is graded)

| Edge case | Handling |
|---|---|
| Mono / poor diarisation | Set `diarisation_confidence: low`, still process, flag in dashboard rather than silently guessing speaker turns. |
| Hindi-English code-switching | Whisper `language=None` (auto-detect per segment) rather than forcing one language. |
| Non-sales call (wrong number, internal) | First LLM pass classifies `call_type` before scoring; non-sales calls get `status=skipped`, not scored. |
| PII redaction | Regex pass (phone numbers, emails) over transcript before storage/LLM call for anything beyond what's operationally needed. |
| Hallucinated/false-positive tags | `verifier.py`: every `quoted_line` must literal-match a substring of the transcript or the tag is dropped, not stored. |
| Vendor API failure | Wrap external calls (Whisper/LLM) in retry-with-backoff; `calls.status` prevents double-processing (idempotency check before reprocessing). `llm_client.py` specifically: retry Gemini 2x, then fall back to Groq automatically before marking the call `failed`. |

**Note on test data:** don't assume the `data/mock_calls/` samples (see §2a) are stereo — check
each file first (`ffprobe` or a quick Python channel-count check). Whichever samples turn out mono
become the concrete test case for the "mono / poor diarisation" row above, instead of having to
fabricate one.

---

## 6. Git workflow

- `main` is always green — nothing merges in that hasn't passed its test.
- One branch per component, named `feature/<component>` (matches folder names above).
- Commit style: **Conventional Commits** — `feat(ingestion): add folder adapter`,
  `test(analysis): add hallucination guard test`, `docs: update README run instructions`.
- Commit at each working checkpoint within a branch, not just once at the end — small commits make
  debugging and video narration easier later.
- Before merging a branch: run its tests locally, update PLAN.md's checklist (§7) for that
  component, then merge to `main` (a self-reviewed PR if using GitHub, or `git merge --no-ff` locally
  to keep the history explicit even solo).
- Tag `main` after each merged milestone (`git tag milestone-3-analysis-engine`) — gives you clean
  rollback points if a later change breaks something.

---

## 7. Hour-by-hour roadmap (30h budget) — checklist

- [ ] **0:00–1:00** — Scaffold repo, `docker-compose.yml` (3 services: db/api/dashboard),
      `Dockerfile.api`, `Dockerfile.dashboard`, `.dockerignore`, `.env.example`, empty module
      folders, write `AGENTS.md` and this `PLAN.md`. Confirm `docker-compose up --build` starts
      (even with near-empty API/dashboard) before moving on — every later component builds and
      tests against this from now on, not a bare local Python install. Commit directly to `main`
      (chore, no logic yet).
- [x] **1:00–4:00** — `feature/ingestion-storage`: adapter interface + folder adapter, Postgres
      models, `db.py`. Before writing the test, populate `data/mock_calls/` per §2a (extract ~5
      `.wav` samples from the `snorbyte/indic-audio-dialog-sample` shard) so the folder adapter has
      something real to read. Test: insert a mock call, read it back. Merge.
- [x] **4:00–8:00** — `feature/transcription`: Whisper wrapper, dual-channel split. Test: one real
      recorded sample produces a transcript. Merge.
- [x] **8:00–14:00** — `feature/analysis-engine`: prompts.py, tagger.py, verifier.py, rubric.py.
      This is the highest-weight component for evaluation — do not rush it. Test: known transcript
      with a planted issue produces the expected tag; verifier rejects a fabricated quote. Merge.
- [x] **14:00–16:00** — `feature/pipeline`: orchestrator tying ingestion→transcription→analysis→
      storage, idempotency check. Test: `test_pipeline_e2e.py` — one call, full loop, asserted in DB.
      Merge. **(This is the "minimum expectation" bar — once this merges, you have a submittable
      project. Everything after this is upside.)**
- [x] **16:00–19:00** — `feature/api`: FastAPI routers per §3. Test: hit each endpoint against the
      seeded DB. Merge.
- [x] **19:00–24:00** — `feature/dashboard`: Streamlit, 3 views (org/team/advisor + call detail).
      Merge.
- [x] **24:00–26:00** — `feature/feedback-loop`: contest endpoints + dashboard "contest this flag"
      button. Merge.
- [x] **26:00–28:00** — `feature/edge-cases`: implement §5 table, add/adjust tests for each row.
      Merge.
- [x] **28:00–29:00** — `feature/deploy`: `render.yaml` Blueprint (db + api + dashboard), push,
      verify all three services come up on Render with real environment variables set, confirm the
      public API and dashboard URLs work end to end (not just locally). Merge.
- [x] **29:00–30:00** — README.md (setup — both `docker-compose up --build` locally and the
      deployed link, what is real versus mocked), writeup (A/B/C sections from the PDF, in your own
      words, concise).
- [x] **30:00–31:00** — Buffer + record 2-minute video (trade-offs, what you didn't build and why,
      where it would fail). Final check: fresh clone + `docker-compose up --build` works, **and**
      the deployed Render link works independently, in case the video walkthrough references either.

If you're behind schedule at any checkpoint, cut scope from **19:00 onward first** (dashboard
polish, feedback loop) — never cut the analysis engine, the e2e pipeline test, or the deployment
step. Those three are what "working prototype," "depth of understanding," and "a deployed link"
are graded on.

### Optional stretch — MCP wrapper (only if everything above is done, with time to spare)

Not required by the assignment; not graded by its rubric. Skip entirely unless §7 is fully complete
and merged. If there's spare time in the last hour: wrap 1–2 read endpoints (`GET /calls/{id}`,
`POST /tags/{id}/contest`) as MCP tools using `fastapi-mcp` (thin layer over the existing FastAPI
app — no new logic, just exposure) so an MCP-aware client (e.g. Claude Desktop) could query flagged
calls directly. If there's no spare time, just note the possibility in `docs/06-api.md` — the
awareness costs nothing, the implementation isn't worth risking the core loop for.

---

## 8. Definition of done, per component

A component is only "done" (mergeable) if: it has a passing test, it has a one-paragraph docstring
at the top of its main file explaining *why* it's built this way, its `docs/<NN>-<component>.md`
file exists (template below), and PLAN.md's checklist above is ticked. If any of these four is
missing, it's not done — don't move to the next component.

### `docs/<component>.md` template (keep each under ~20 lines — this feeds the writeup later)

```
# <Component name>

**What it does:** one or two sentences.

**Why built this way:** the key decision(s) and the alternative you didn't pick, and why.

**Inputs / outputs:** what goes in, what comes out (shapes, not full schemas — those are in code).

**Edge cases handled here:** bullet list, only the ones relevant to this component.

**Known gaps / what I'd do with more time:** honest, short.
```

Stitching all `docs/*.md` files together at hour 28 (§7) becomes ~80% of your final writeup —
that's the point of writing them as you go instead of reconstructing everything at the end.
