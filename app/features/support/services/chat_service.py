from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.features.support.models import LiveChatSession, Message
from app.features.support.models.live_chat_session import ChatStatus
from app.features.support.models.message import MessageType, SenderType, MessageStatus


class ChatService:
    """Service for managing live chat sessions"""
    
    # Configuration
    MAX_WAIT_TIME_MINUTES = 10
    SESSION_TIMEOUT_MINUTES = 30
    MAX_ACTIVE_SESSIONS_PER_AGENT = 5
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_session(
        self,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        user_id: Optional[int] = None,
        subject: Optional[str] = None,
        source: str = "web"
    ) -> LiveChatSession:
        session = LiveChatSession(
            session_id=LiveChatSession.generate_session_id(),
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            subject=subject,
            status=ChatStatus.WAITING,
            source=source,
            started_at=datetime.utcnow(),
            last_activity_at=datetime.utcnow()
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        # Calculate queue position
        queue_position = self._calculate_queue_position()
        session.queue_position = queue_position
        self.db.commit()
        
        # Send welcome message
        self._send_system_message(
            session.id,
            f"Hello! You're currently number {queue_position} in queue. An agent will be with you shortly."
        )
        
        return session
    
    def assign_agent(
        self,
        session_id: int,
        agent_id: int,
        agent_name: str
    ) -> Tuple[bool, Optional[str]]:
        session = self.db.query(LiveChatSession).filter(
            LiveChatSession.id == session_id
        ).first()
        
        if not session:
            return False, "Session not found"
        
        if session.status != ChatStatus.WAITING:
            return False, "Session is not waiting for agent"
        
        # Check agent's active session count
        active_count = self.db.query(LiveChatSession).filter(
            LiveChatSession.agent_id == agent_id,
            LiveChatSession.status == ChatStatus.ACTIVE,
            LiveChatSession.is_active == True
        ).count()
        
        if active_count >= self.MAX_ACTIVE_SESSIONS_PER_AGENT:
            return False, f"Agent has reached maximum active sessions ({self.MAX_ACTIVE_SESSIONS_PER_AGENT})"
        
        # Assign agent
        session.agent_id = agent_id
        session.agent_name = agent_name
        session.status = ChatStatus.ACTIVE
        session.agent_joined_at = datetime.utcnow()
        session.wait_time_seconds = int((datetime.utcnow() - session.started_at).total_seconds())
        session.last_activity_at = datetime.utcnow()
        
        self.db.commit()
        
        # Send agent joined message
        self._send_system_message(
            session.id,
            f"{agent_name} has joined the chat. How can I help you today?"
        )
        
        return True, None
    
    def send_message(
        self,
        session_id: int,
        content: str,
        sender_type: str,
        sender_id: Optional[int] = None,
        sender_name: Optional[str] = None,
        message_type: str = "text"
    ) -> Tuple[Optional[Message], Optional[str]]:
        session = self.db.query(LiveChatSession).filter(
            LiveChatSession.id == session_id
        ).first()
        
        if not session:
            return None, "Session not found"
        
        if not session.is_active:
            return None, "Session is not active"
        
        # Create message
        message = Message(
            message_id=Message.generate_message_id(),
            chat_session_id=session_id,
            content=content,
            message_type=MessageType(message_type),
            sender_type=SenderType(sender_type),
            sender_id=sender_id,
            sender_name=sender_name,
            status=MessageStatus.SENT,
            sent_at=datetime.utcnow()
        )
        
        self.db.add(message)
        
        # Update session statistics
        session.message_count += 1
        session.last_activity_at = datetime.utcnow()
        
        if sender_type == "user":
            session.user_message_count += 1
        elif sender_type == "agent":
            session.agent_message_count += 1
        
        self.db.commit()
        self.db.refresh(message)
        
        return message, None
    
    def end_session(
        self,
        session_id: int,
        end_reason: str,
        ended_by: str = "user"
    ) -> Tuple[bool, Optional[str]]:
        session = self.db.query(LiveChatSession).filter(
            LiveChatSession.id == session_id
        ).first()
        
        if not session:
            return False, "Session not found"
        
        if not session.is_active:
            return False, "Session already ended"
        
        # Update session
        session.status = ChatStatus.ENDED
        session.is_active = False
        session.ended_at = datetime.utcnow()
        session.end_reason = end_reason
        
        self.db.commit()
        
        # Send closing message
        if ended_by == "agent":
            self._send_system_message(
                session.id,
                "The agent has ended this chat session. Thank you for contacting support!"
            )
        
        return True, None
    
    def transfer_session(
        self,
        session_id: int,
        new_agent_id: int,
        new_agent_name: str,
        transfer_reason: str
    ) -> Tuple[bool, Optional[str]]:
        session = self.db.query(LiveChatSession).filter(
            LiveChatSession.id == session_id
        ).first()
        
        if not session:
            return False, "Session not found"
        
        if session.status != ChatStatus.ACTIVE:
            return False, "Can only transfer active sessions"
        
        old_agent_name = session.agent_name
        
        # Update session
        session.agent_id = new_agent_id
        session.agent_name = new_agent_name
        session.is_transferred = True
        session.transfer_reason = transfer_reason
        session.status = ChatStatus.TRANSFERRED
        session.last_activity_at = datetime.utcnow()
        
        self.db.commit()
        
        # Send transfer message
        self._send_system_message(
            session.id,
            f"You've been transferred from {old_agent_name} to {new_agent_name}. {transfer_reason}"
        )
        
        # Set back to active
        session.status = ChatStatus.ACTIVE
        self.db.commit()
        
        return True, None
    
    def get_session(self, session_id: int) -> Optional[LiveChatSession]:
        return self.db.query(LiveChatSession).filter(
            LiveChatSession.id == session_id
        ).first()
    
    def get_session_by_session_id(self, session_id_str: str) -> Optional[LiveChatSession]:
        return self.db.query(LiveChatSession).filter(
            LiveChatSession.session_id == session_id_str
        ).first()
    
    def get_session_messages(
        self,
        session_id: int,
        limit: int = 100,
        offset: int = 0
    ) -> List[Message]:
        return self.db.query(Message).filter(
            Message.chat_session_id == session_id,
            Message.is_deleted == False
        ).order_by(Message.sent_at.asc()).offset(offset).limit(limit).all()
    
    def get_waiting_sessions(self) -> List[LiveChatSession]:

        return self.db.query(LiveChatSession).filter(
            LiveChatSession.status == ChatStatus.WAITING,
            LiveChatSession.is_active == True
        ).order_by(LiveChatSession.started_at.asc()).all()
    
    def get_agent_active_sessions(self, agent_id: int) -> List[LiveChatSession]:
        return self.db.query(LiveChatSession).filter(
            LiveChatSession.agent_id == agent_id,
            LiveChatSession.status == ChatStatus.ACTIVE,
            LiveChatSession.is_active == True
        ).all()
    
    def check_and_timeout_stale_sessions(self) -> int:

        timeout_threshold = datetime.utcnow() - timedelta(minutes=self.SESSION_TIMEOUT_MINUTES)
        
        stale_sessions = self.db.query(LiveChatSession).filter(
            LiveChatSession.is_active == True,
            LiveChatSession.last_activity_at < timeout_threshold
        ).all()
        
        count = 0
        for session in stale_sessions:
            session.status = ChatStatus.TIMEOUT
            session.is_active = False
            session.ended_at = datetime.utcnow()
            session.end_reason = "timeout"
            count += 1
        
        self.db.commit()
        return count
    
    def rate_session(
        self,
        session_id: int,
        rating: int,
        feedback: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:

        if rating < 1 or rating > 5:
            return False, "Rating must be between 1 and 5"
        
        session = self.db.query(LiveChatSession).filter(
            LiveChatSession.id == session_id
        ).first()
        
        if not session:
            return False, "Session not found"
        
        session.rating = rating
        session.feedback = feedback
        
        self.db.commit()
        return True, None
    
    def _send_system_message(self, session_id: int, content: str) -> Message:
        message = Message(
            message_id=Message.generate_message_id(),
            chat_session_id=session_id,
            content=content,
            message_type=MessageType.SYSTEM,
            sender_type=SenderType.SYSTEM,
            status=MessageStatus.SENT,
            sent_at=datetime.utcnow(),
            is_automated=True
        )
        
        self.db.add(message)
        self.db.commit()
        return message
    
    def _calculate_queue_position(self) -> int:

        waiting_count = self.db.query(LiveChatSession).filter(
            LiveChatSession.status == ChatStatus.WAITING,
            LiveChatSession.is_active == True
        ).count()
        
        return waiting_count + 1