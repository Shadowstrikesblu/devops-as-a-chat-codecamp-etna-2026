# app/models/action_decision.py
"""
Journalisation des décisions utilisateur (Challenge 2, Piste 4).

Trace chaque décision (confirmé / refusé) sur une action proposée par DAC,
pour répondre au critère « les actions confirmées et refusées sont tracées ».
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class ActionDecision(Base):
    __tablename__ = "action_decisions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(Integer, nullable=True, index=True)
    chat_id = Column(Integer, nullable=True)

    action_summary = Column(String, nullable=False)      # ex: "redémarrage de service nginx"
    command = Column(Text, nullable=True)                # commande exacte (sans secrets)
    safety_level = Column(String, nullable=False, default="sensitive")  # safe|sensitive|dangerous
    decision = Column(String, nullable=False)            # confirmed|rejected
    mode = Column(String, nullable=True)                 # dry_run|real

    created_at = Column(DateTime(timezone=True), server_default=func.now())
