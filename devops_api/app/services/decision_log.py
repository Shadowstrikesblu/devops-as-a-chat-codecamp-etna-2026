# app/services/decision_log.py
"""
Helper de journalisation des décisions utilisateur (Challenge 2, Piste 4).
"""
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app import models

logger = logging.getLogger(__name__)


def log_decision(
    db: Session,
    user_id: int,
    decision: str,                 # "confirmed" | "rejected"
    action_summary: str,
    command: Optional[str] = None,
    safety_level: str = "sensitive",
    session_id: Optional[int] = None,
    chat_id: Optional[int] = None,
    mode: Optional[str] = "real",
) -> None:
    """
    Enregistre une décision utilisateur. Ne lève jamais : la journalisation ne doit
    pas casser le flux fonctionnel.
    """
    try:
        rec = models.ActionDecision(
            user_id=user_id,
            session_id=session_id,
            chat_id=chat_id,
            action_summary=action_summary[:300] if action_summary else "",
            command=(command or "")[:2000],
            safety_level=safety_level,
            decision=decision,
            mode=mode,
        )
        db.add(rec)
        db.commit()
        logger.info("[decision_log] user=%s decision=%s action=%s", user_id, decision, action_summary[:60])
    except Exception as e:
        db.rollback()
        logger.warning("[decision_log] échec journalisation: %s", e)
