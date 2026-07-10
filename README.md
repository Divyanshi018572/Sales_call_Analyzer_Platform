# FitNova Sales-Call Intelligence

This repository contains the prototype for the **FitNova Sales-Call Intelligence** system. The system automatically ingests, transcribes, diarises, scores, and audits sales calls for FitNova wellness and fitness coaching programs, featuring an interactive human-in-the-loop feedback loop.

---

## 🏗️ System Architecture Overview

The system runs as three dockerized services:
1. **Database (`db`)**: PostgreSQL 15 alpine database storing organizations, teams, advisors, calls, transcripts, scores, compliance tags, and contest records.
2. **API Backend (`api`)**: FastAPI service running the orchestration pipeline (Ingestion -> Stereo splitting -> Whisper Transcription -> Gemini LLM Scoring -> Hallucination Verifier -> PostgreSQL Storage) and serving rollup metrics.
3. **Dashboard (`dashboard`)**: Streamlit application providing custom views for the Sales Director, Team Leaders, and Advisors.

---

## 💻 Local Setup & Run

### Prerequisites
- Docker & Docker Compose installed.
- (Optional) A Gemini API key. If absent, the system falls back to a mock evaluator.

### Steps
1. Create a local `.env` file in the root directory (based on `.env.example`):
   ```bash
   cp .env.example .env
   ```
   Add your API keys in the `.env` file:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   ```
2. Build and launch all services locally:
   ```bash
   docker-compose up --build
   ```
3. Access the interfaces:
   - **FastAPI Base API URL**: [http://localhost:8000](http://localhost:8000)
   - **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Streamlit Dashboard Web App**: [http://localhost:8501](http://localhost:8501)

4. Run all unit and E2E integration tests:
   ```bash
   docker exec fitnova_api python -m pytest
   ```

---

## 🚀 One-Click Deployment to Render

This repository includes a [render.yaml](file:///d:/DATA%20SCIENCE/saas%20APPs/fake_call_detect/render.yaml) Blueprint configuration that automatically configures and deploys the PostgreSQL database, the FastAPI backend, and the Streamlit dashboard on Render.

### Steps to Deploy:
1. Log in to the [Render Dashboard](https://dashboard.render.com).
2. Click **New** (top right) -> **Blueprint**.
3. Connect your GitHub repository: `https://github.com/Divyanshi018572/Fitnova-sales-call-analyzer.git`.
4. Render will automatically read the `render.yaml` blueprint. Enter values for the required environment variables:
   - `GEMINI_API_KEY` (Your Gemini API key)
   - `GROQ_API_KEY` (Your Groq API key, optional)
5. Click **Apply**. Render will spin up the services:
   - A private database (`fitnova-db`)
   - The FastAPI web service (`fitnova-api`)
   - The Streamlit web dashboard (`fitnova-dashboard`)
6. Once deployment completes, your services will be live at:
   - **API URL**: `https://fitnova-api.onrender.com` (or your custom Render URL)
   - **Dashboard URL**: `https://fitnova-dashboard.onrender.com` (or your custom Render URL)

---

## ⚖️ Real vs. Mocked Systems

| Component | Status | Description |
|---|---|---|
| Ingestion Source | Mocked | Ingests calls from a local directory (`data/mock_calls/`) rather than live telephony webhooks. |
| Transcription / Diarisation | Real | Runs locally using `faster-whisper` and split-channel stereo audio diarisation. |
| Call Scoring / Tagging | Real | Integrates with Gemini 2.5 Flash API with automated fallback to Groq Llama 3.3. |
| Database Storage | Real | Persists all call records, transcripts, scores, and tags to a PostgreSQL database. |
| Organization Rollups | Real | Computes live averages and trends per team and advisor on database records. |
| Feedback Loop / Contests | Real | Allows advisors to contest tags and team leaders to resolve contests via DB updates. |
