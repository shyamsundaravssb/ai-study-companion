import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.event import Event
from app.models.mastery import Mastery
from app.models.mastery_history import MasteryHistory

logger = logging.getLogger(__name__)

def process_assessment_completed_event_inline(db: Session, event_id: uuid.UUID) -> None:
    """
    Process an assessment completed event to update mastery scores.
    
    Update formula: new_score = old_score * 0.7 + performance * 0.3
    Reasoning: Alpha=0.3 provides a balance between historical performance and recent performance. 
    It ensures that a single bad (or good) performance doesn't drastically swing the score, 
    but consecutive performances will quickly converge to the new true understanding level.
    If no prior mastery exists, the performance score itself seeds the initial mastery.
    
    Idempotency: Locks the event row and checks `processed_at`. If processed, skips.
    """
    event = db.query(Event).filter(Event.id == event_id).with_for_update().first()
    
    if not event:
        logger.error(f"Event {event_id} not found for mastery processing.")
        return
        
    if event.processed_at is not None:
        logger.info(f"Event {event_id} already processed. Skipping mastery update.")
        return
        
    payload = event.payload
    project_id = uuid.UUID(payload["project_id"])
    concept_results = payload.get("concept_results", {})
    
    for concept_id_str, performance in concept_results.items():
        concept_id = uuid.UUID(concept_id_str)
        
        mastery = db.query(Mastery).filter(
            Mastery.project_id == project_id,
            Mastery.concept_id == concept_id
        ).first()
        
        if mastery:
            old_score = mastery.score
            new_score = old_score * 0.7 + performance * 0.3
            mastery.score = new_score
            mastery.last_updated = datetime.now(timezone.utc)
        else:
            new_score = performance
            mastery = Mastery(
                project_id=project_id,
                concept_id=concept_id,
                score=new_score
            )
            db.add(mastery)
            
        history = MasteryHistory(
            project_id=project_id,
            concept_id=concept_id,
            score=new_score
        )
        db.add(history)
        
    event.processed_at = datetime.now(timezone.utc)
    db.commit()
