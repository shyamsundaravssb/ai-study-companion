import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.ai.graphs.tutor_graph import tutor_app

class TutorService:
    @staticmethod
    def create_conversation(db: Session, project_id: uuid.UUID, title: Optional[str] = None) -> Conversation:
        conv = Conversation(project_id=project_id, title=title)
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return conv
        
    @staticmethod
    def get_conversation(db: Session, project_id: uuid.UUID, conv_id: uuid.UUID) -> Conversation:
        conv = db.query(Conversation).filter(
            Conversation.id == conv_id,
            Conversation.project_id == project_id
        ).first()
        
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conv

    @staticmethod
    async def chat_in_conversation(
        db: Session, 
        project_id: uuid.UUID, 
        conv_id: uuid.UUID, 
        user_message: str
    ) -> Message:
        # Verify conversation exists and belongs to project
        conv = TutorService.get_conversation(db, project_id, conv_id)
        
        # Save user message
        user_msg = Message(
            conversation_id=conv.id,
            role=MessageRole.user,
            content=user_message,
        )
        db.add(user_msg)
        db.commit()
        
        # Fetch last 4 messages for sliding window context (including the one just added)
        recent_db_msgs = db.query(Message).filter(
            Message.conversation_id == conv.id
        ).order_by(Message.created_at.desc()).limit(4).all()
        
        recent_db_msgs.reverse() # chronological order
        
        recent_messages = []
        for msg in recent_db_msgs:
            # Skip the newly added message from history since it's the current_question
            if msg.id == user_msg.id:
                continue
            role_str = "user" if msg.role == MessageRole.user else "assistant"
            recent_messages.append({"role": role_str, "content": msg.content})

        # Run graph
        initial_state = {
            "project_id": project_id,
            "recent_messages": recent_messages,
            "current_question": user_message,
            "context_chunks": [],
            "is_sufficient": False,
            "final_answer": "",
            "citations": []
        }
        
        final_state = await tutor_app.ainvoke(initial_state)
        
        # Save assistant response
        assistant_msg = Message(
            conversation_id=conv.id,
            role=MessageRole.assistant,
            content=final_state["final_answer"],
            citations=final_state["citations"]
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)
        
        return assistant_msg
