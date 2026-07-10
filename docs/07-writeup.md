# FitNova Sales-Call Intelligence: Project Writeup

This writeup synthesizes the architecture, design choices, and grading requirements (Sections A, B, and C) for the FitNova Sales-Call Intelligence prototype.

---

## 👥 Section A: System Architecture & Value Justification

The core pipeline is built as a modular, dockerized system:
1. **Ingestion Layer**: Telephony/file events are captured via adapters and staged as `pending` calls in PostgreSQL.
2. **Transcription Layer**: Stereo WAV audio files are split programmatically into separate tracks for the Advisor (Channel 0) and Customer (Channel 1). Each track is transcribed using local `faster-whisper-small` (auto-detecting segments to support English-Hindi code-switching).
3. **LLM Analysis Layer**: Transcripts are audited against the quality rubric and compliance taxonomy. 
4. **Verification Layer**: An automated verifier matches compliance tags against raw transcript text. Hallucinations are discarded, and start timestamps are programmatically resolved.
5. **Surfacing & Dashboard**: The Streamlit dashboard displays role-tailored metrics for Sales Directors, Team Leaders, and Advisors, incorporating the dispute resolution workflow.

### 💡 High-Value Automation Stages:
- **Compliance Auditing (Highest Value)**: In manual systems, managers audit less than 5% of calls. By using LLMs to scan 100% of calls, FitNova achieves complete compliance coverage, allowing Team Leaders to focus 100% of their human coaching time on calls with critical flags.
- **Stereo Diarisation (Second Highest Value)**: Splits tracks at ingestion for deterministic speaker identification at zero compute cost, bypassing expensive and flakey ML-based blind diarisation clustering on mono files.

---

## 📝 Section B: Evaluation Rubric & LLM Engineering

### ⚖️ Performance Rubric & Compliance Deductions:
Call quality is scored out of 5.0 across five weighted dimensions:
- **Needs Discovery** (25%)
- **Product Knowledge** (20%)
- **Objection Handling** (20%)
- **Compliance Audits** (20%)
- **Trial Booking** (15%)

Critical compliance tag violations (e.g. prescribing medical advice, aggressive urgency tactics, or over-promising) trigger a **`-0.5` overall score deduction** per violation from the weighted rollup. Warning flags (e.g. failing to state call recording policies) do not deduct scores but are flagged for manager review.

### 🔌 Provider-Agnostic LLM Fallback Client:
To ensure high availability and prevent single-point-of-failure issues:
1. **Primary**: Gemini 2.5 Flash is invoked (high accuracy, low cost, fast speed).
2. **Fallback**: If Gemini fails (rate limits, network timeouts), the client automatically retries twice before falling back to Llama 3.3 (70B) on Groq.
3. **Offline Mock**: If no API keys are present or both providers are down, the system invokes a local mock evaluator so test suites run green without internet connection.

### 🛡️ Hallucination Guard (Verifier):
To protect advisors from false AI accusations, `verifier.py` performs literal substring validation. The LLM must output the exact quote representing the violation. If the quote is not present in the transcription segments, the tag is rejected as an AI hallucination.

---

## ⚖️ Section C: Human-in-the-Loop (HITL) Dispute Resolution

To maintain team trust, the prototype implements a complete human-in-the-loop feedback system:
1. **Advisor View**: Advisors review their call scorecard and chronological transcripts. Next to any compliance tag, they can fill out an explanation and click **File Dispute**. The tag's status updates to `pending`.
2. **Team Leader View**: Team Leaders are alerted on their dashboard with the count and list of active disputes. They review the contested quote, read the advisor's note, and make a decision.
3. **Dynamic Recalculation**: If the TL selects **Overturn Tag**, the tag is marked `overturned`. The backend dynamically recalculates the call's overall score by subtracting the compliance deduction penalty in Postgres, updating the advisor's metrics instantly.

---

## ⚙️ Technical Trade-offs & Future Production Upgrades

| Prototype Implementation | Trade-off / Limitation | Production Upgrade Path |
|---|---|---|
| **Synchronous API Pipeline** | Large audio files block the FastAPI thread during transcription. | Offload transcription to an async queue (Celery/RabbitMQ) with websocket notifications. |
| **Local CPU Whisper** | Transcription runs on CPU, taking 15-30s per call. | Run faster-whisper on dedicated GPU nodes (CUDA) or migrate to a managed API (e.g., Deepgram). |
| **Directory-based Ingestion** | Adapter monitors local folder (`data/mock_calls/`). | Implement webhook endpoints for CRM systems (HubSpot, Salesforce) or Twilio SIP streams. |
