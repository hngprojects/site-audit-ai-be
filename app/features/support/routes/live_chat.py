

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
import json

from app.platform.db.session import get_db
from app.features.support.schemas.chat_message import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionEnd,
    ChatSessionAssign,
    ChatSessionTransfer,
    ChatSessionRate,
    MessageListResponse,
    ChatSessionListResponse
)
from services import ChatService, ValidationService

router = APIRouter(
    prefix="/api/support/chat",
    tags=["Live Chat"]
)


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    request: ChatSessionCreate,
    db: Session = Depends(get_db)
):
    # Validate email if provided
    if request.user_email:
        is_valid, error = ValidationService.validate_email(request.user_email)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error
            )
    
    # Create session
    chat_service = ChatService(db)
    session = chat_service.create_session(
        user_name=request.user_name,
        user_email=request.user_email,
        subject=request.subject,
        source=request.source
    )
    
    return ChatSessionResponse.from_orm(session)


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    # Validate session ID format
    if not ValidationService.validate_session_id(session_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID format"
        )
    
    chat_service = ChatService(db)
    session = chat_service.get_session_by_session_id(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found"
        )
    
    return ChatSessionResponse.from_orm(session)


@router.post("/messages", response_model=ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_chat_message(
    request: ChatMessageRequest,
    db: Session = Depends(get_db)
):
    chat_service = ChatService(db)
    
    # Get session
    session = chat_service.get_session_by_session_id(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {request.session_id} not found"
        )
    
    # Sanitize content
    sanitized_content = ValidationService.sanitize_text(request.content)
    
    # Send message
    message, error = chat_service.send_message(
        session_id=session.id,
        content=sanitized_content,
        sender_type=request.sender_type,
        sender_name=request.sender_name
    )
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return ChatMessageResponse.from_orm(message)


@router.get("/sessions/{session_id}/messages", response_model=MessageListResponse)
async def get_session_messages(
    session_id: str,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    chat_service = ChatService(db)
    
    # Get session
    session = chat_service.get_session_by_session_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found"
        )
    
    # Get messages
    messages = chat_service.get_session_messages(
        session_id=session.id,
        limit=limit,
        offset=offset
    )
    
    return MessageListResponse(
        success=True,
        total=len(messages),
        messages=[ChatMessageResponse.from_orm(msg) for msg in messages]
    )


@router.post("/sessions/assign", response_model=dict)
async def assign_agent_to_session(
    request: ChatSessionAssign,
    db: Session = Depends(get_db)
):
    chat_service = ChatService(db)
    
    # Get session
    session = chat_service.get_session_by_session_id(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {request.session_id} not found"
        )
    
    # Assign agent
    success, error = chat_service.assign_agent(
        session_id=session.id,
        agent_id=request.agent_id,
        agent_name=request.agent_name
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {
        "success": True,
        "message": f"Agent {request.agent_name} assigned to session",
        "session_id": request.session_id
    }


@router.post("/sessions/end", response_model=dict)
async def end_chat_session(
    request: ChatSessionEnd,
    db: Session = Depends(get_db)
):
    chat_service = ChatService(db)
    
    # Get session
    session = chat_service.get_session_by_session_id(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {request.session_id} not found"
        )
    
    # End session
    success, error = chat_service.end_session(
        session_id=session.id,
        end_reason=request.end_reason,
        ended_by=request.ended_by
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {
        "success": True,
        "message": "Chat session ended successfully",
        "session_id": request.session_id
    }


@router.post("/sessions/transfer", response_model=dict)
async def transfer_chat_session(
    request: ChatSessionTransfer,
    db: Session = Depends(get_db)
):
    chat_service = ChatService(db)
    
    # Get session
    session = chat_service.get_session_by_session_id(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {request.session_id} not found"
        )
    
    # Transfer session
    success, error = chat_service.transfer_session(
        session_id=session.id,
        new_agent_id=request.new_agent_id,
        new_agent_name=request.new_agent_name,
        transfer_reason=request.transfer_reason
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {
        "success": True,
        "message": f"Session transferred to {request.new_agent_name}",
        "session_id": request.session_id
    }


@router.post("/sessions/rate", response_model=dict)
async def rate_chat_session(
    request: ChatSessionRate,
    db: Session = Depends(get_db)
):
    
    chat_service = ChatService(db)
    
    # Get session
    session = chat_service.get_session_by_session_id(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {request.session_id} not found"
        )
    
    # Rate session
    success, error = chat_service.rate_session(
        session_id=session.id,
        rating=request.rating,
        feedback=request.feedback
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {
        "success": True,
        "message": "Thank you for your feedback!",
        "session_id": request.session_id
    }


@router.get("/sessions/waiting", response_model=ChatSessionListResponse)
async def get_waiting_sessions(
    db: Session = Depends(get_db)
):
    """
    Get all chat sessions waiting for an agent
    """
    
    chat_service = ChatService(db)
    sessions = chat_service.get_waiting_sessions()
    
    return ChatSessionListResponse(
        success=True,
        total=len(sessions),
        sessions=[ChatSessionResponse.from_orm(s) for s in sessions]
    )


@router.get("/agents/{agent_id}/sessions", response_model=ChatSessionListResponse)
async def get_agent_sessions(
    agent_id: int,
    db: Session = Depends(get_db)
):
    chat_service = ChatService(db)
    sessions = chat_service.get_agent_active_sessions(agent_id)
    
    return ChatSessionListResponse(
        success=True,
        total=len(sessions),
        sessions=[ChatSessionResponse.from_orm(s) for s in sessions]
    )


# WebSocket endpoint for real-time chat (optional)
@router.websocket("/ws/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: str,
    db: Session = Depends(get_db)
):
    await websocket.accept()
    
    try:
        chat_service = ChatService(db)
        session = chat_service.get_session_by_session_id(session_id)
        
        if not session:
            await websocket.send_json({
                "error": "Session not found"
            })
            await websocket.close()
            return
        
        # Keep connection alive and handle messages
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Send message
            message, error = chat_service.send_message(
                session_id=session.id,
                content=message_data.get('content'),
                sender_type=message_data.get('sender_type', 'user'),
                sender_name=message_data.get('sender_name')
            )
            
            if message:
                await websocket.send_json(message.to_dict())
            else:
                await websocket.send_json({"error": error})
    
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
        await websocket.close()