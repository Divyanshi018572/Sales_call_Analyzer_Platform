# Analysis Engine Component

**What it does:**
Classifies calls as sales/non-sales, scores advisors against a 5-dimension sales rubric, flags policy violations from a compliance taxonomy, and filters out hallucinated flags using literal transcript quote verification.

**Why built this way:**
- **Provider-Agnostic with Fallback**: Implemented a unified `analyze_call` interface that tries Gemini 2.5 Flash first, retries up to 2 times on failures with backoff, and automatically falls back to Groq (Llama 3.3 70B) before defaulting to a mock handler.
- **Hallucination Guard**: Matches LLM-extracted `quoted_line` evidence literally against the transcription text (standardized for case, quotes, and punctuation). If unverified, the tag is dropped.
- **Timestamp Resolution**: Rather than asking the LLM to guess timestamps (which is inaccurate), we match the verified quote against the transcription segments to resolve the exact start timestamp programmatically.
- **Compliance Deductions**: Rubric scores are weighted (Discovery 25%, Product 20%, Objections 20%, Compliance 20%, Booking 15%). We apply a `-0.5` overall score deduction per critical tag to reflect real sales auditing standards.

**Inputs / outputs:**
- **Input**:
  - `transcript_text` (str): Raw text of the transcription.
  - `segments` (List[dict]): List of dictionaries with keys (`speaker`, `start`, `end`, `text`).
- **Output**:
  - `call_type` (str): 'sales' or 'non-sales'.
  - `reasoning` (str): Step-by-step evaluation context.
  - `scores` (dict): Dictionary containing `needs_discovery`, `product_knowledge`, `objection_handling`, `compliance`, `trial_booking`.
  - `overall` (float): The final weighted and penalized call score.
  - `tags` (List[dict]): List of verified compliance tags, each with timestamp, type, severity, and reason.

**Edge cases handled here:**
- **Non-Sales Classification**: Automatically flags non-sales calls (wrong numbers, voicemails) and skips scoring/tagging, setting status to `skipped`.
- **API Failures / Missing Keys**: Retries and falls back automatically. If no API keys are configured, it invokes a local mock evaluator that matches key phrases, ensuring tests remain green.
- **Spanning Quotes**: If a compliance quote spans multiple segments, it resolves the timestamp using the first 3 words of the quote.

**Known gaps / what I'd do with more time:**
- Move prompt texts and rubric weights into the database, allowing team leaders to modify rubrics and taxonomy definitions without code changes.
- Add advanced regex and Named Entity Recognition (NER) passes to redact PII (credit cards, addresses) before sending transcripts to external APIs.
