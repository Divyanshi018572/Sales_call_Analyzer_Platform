"""
Pipeline orchestrator module.

Why this approach:
We implement the `process_call` function to serve as the unified controller of the workflow.
It retrieves a pending call record, checks its status to enforce idempotency, and executes:
1. Audio channel-splitting and transcription (via `Transcriber`).
2. Transcript evaluation, compliance tagging, and verification (via `evaluate_transcript`).
3. Relational storage of transcripts, scores, and tags (via `crud` helpers).
If any step fails, the call is marked as 'failed' in the database for troubleshooting.
"""

import logging
from sqlalchemy.orm import Session
from src.storage import crud, models
from src.transcription.transcriber import Transcriber
from src.analysis.tagger import evaluate_transcript

# Setup logger
logger = logging.getLogger("fitnova.pipeline")

# Lazy transcriber instance
_transcriber = None

def get_transcriber() -> Transcriber:
    """
    Lazy loader for the Transcriber singleton instance.
    """
    global _transcriber
    if _transcriber is None:
        _transcriber = Transcriber()
    return _transcriber

def process_call(db: Session, call_id: int) -> models.Call:
    """
    Executes the end-to-end processing pipeline for a single call record.
    Enforces idempotency by skipping already processed (done or skipped) calls.
    
    Args:
        db (Session): Database session.
        call_id (int): ID of the Call database record.
        
    Returns:
        models.Call: The updated Call record.
    """
    db_call = crud.get_call(db, call_id)
    if not db_call:
        raise ValueError(f"Call with ID {call_id} does not exist.")
        
    # 1. Idempotency Check: Skip if already evaluated or marked non-sales
    if db_call.status in ["done", "skipped"]:
        logger.info(f"Call ID {call_id} is already processed (Status: '{db_call.status}'). Skipping.")
        return db_call
        
    logger.info(f"Starting processing pipeline for Call ID {call_id} (Source ID: {db_call.source_call_id})")
    
    # 2. Mark call as processing
    crud.update_call_status(db, call_id, "processing")
    
    try:
        # 3. Step A: Transcribe and Diarise
        logger.info(f"Transcribing audio: {db_call.recording_path}")
        transcriber = get_transcriber()
        full_text, segments, confidence = transcriber.transcribe_call(db_call.recording_path)
        
        # Save transcript & segments
        crud.create_transcript(db, call_id, full_text, segments, confidence)
        
        # 4. Step B: Analyze and score transcript
        logger.info("Running compliance audit and quality scoring...")
        evaluation = evaluate_transcript(full_text, segments)
        
        call_type = evaluation.get("call_type", "sales")
        reasoning = evaluation.get("reasoning", "")
        
        # 5. Step C: Save evaluation and update status
        if call_type == "non-sales":
            # Classification: Non-sales -> Mark skipped, do not score or tag
            logger.info(f"Call ID {call_id} classified as non-sales. Status set to 'skipped'.")
            crud.update_call_status(db, call_id, "skipped")
        else:
            # Classification: Sales -> Save scores and verified tags
            logger.info("Saving call quality scores...")
            scores_data = dict(evaluation["scores"])
            scores_data["overall"] = evaluation["overall"]
            crud.create_scores(db, call_id, scores_data)
            
            logger.info(f"Saving {len(evaluation['tags'])} verified compliance tags...")
            for tag in evaluation["tags"]:
                crud.create_tag(
                    db=db,
                    call_id=call_id,
                    tag_type=tag["type"],
                    severity=tag["severity"],
                    timestamp_sec=tag["timestamp_sec"],
                    quoted_line=tag["quoted_line"],
                    reason=tag["reason"]
                )
                
            crud.update_call_status(db, call_id, "done")
            
        db.commit()
        db.refresh(db_call)
        logger.info(f"Pipeline completed successfully for Call ID {call_id}. Status: {db_call.status}")
        return db_call
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to process Call ID {call_id}: {e}", exc_info=True)
        # Update status to failed
        crud.update_call_status(db, call_id, "failed")
        db.commit()
        db.refresh(db_call)
        raise e
