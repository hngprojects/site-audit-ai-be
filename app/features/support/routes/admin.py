"""
Admin Routes
FastAPI endpoints for support team and admin operations
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.platform.db.session import get_db
from app.features.support.services import TicketService, ChatService

router = APIRouter(
    prefix="/api/admin/support",
    tags=["Admin"]
)


@router.get("/dashboard")
async def get_dashboard_stats(
    days: int = 30,
    db: Session = Depends(get_db)
):

    
    ticket_service = TicketService(db)
    chat_service = ChatService(db)
    
    # Get ticket statistics
    ticket_stats = ticket_service.get_ticket_statistics(days=days)
    
    # Get overdue tickets
    overdue_tickets = ticket_service.get_overdue_tickets()
    
    # Get waiting chat sessions
    waiting_chats = chat_service.get_waiting_sessions()
    
    return {
        "period": f"Last {days} days",
        "tickets": ticket_stats,
        "overdue_tickets": {
            "count": len(overdue_tickets),
            "tickets": [t.to_dict() for t in overdue_tickets[:10]]  # First 10
        },
        "live_chat": {
            "waiting_count": len(waiting_chats),
            "waiting_sessions": [s.to_dict() for s in waiting_chats]
        }
    }


@router.get("/tickets/overdue")
async def get_overdue_tickets(
    db: Session = Depends(get_db)
):

    ticket_service = TicketService(db)
    overdue_tickets = ticket_service.get_overdue_tickets()
    
    return {
        "success": True,
        "count": len(overdue_tickets),
        "tickets": [t.to_dict() for t in overdue_tickets]
    }


@router.get("/stats")
async def get_support_stats(
    days: int = 7,
    db: Session = Depends(get_db)
):

    
    ticket_service = TicketService(db)
    stats = ticket_service.get_ticket_statistics(days=days)
    
    return {
        "success": True,
        "period": f"Last {days} days",
        "stats": stats
    }


@router.post("/tickets/{ticket_id}/assign/{agent_id}")
async def assign_ticket_to_agent(
    ticket_id: str,
    agent_id: int,
    db: Session = Depends(get_db)
):

    
    ticket_service = TicketService(db)
    ticket = ticket_service.get_ticket_by_ticket_id(ticket_id)
    
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )
    
    success, error = ticket_service.assign_ticket(
        ticket_id=ticket.id,
        agent_id=agent_id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )
    
    return {
        "success": True,
        "message": f"Ticket {ticket_id} assigned to agent {agent_id}"
    }


@router.get("/agents/{agent_id}/tickets")
async def get_agent_tickets(
    agent_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):

    ticket_service = TicketService(db)
    
    # Search for tickets assigned to this agent
    tickets = ticket_service.search_tickets(
        assigned_to=agent_id,
        status=status,
        limit=100
    )
    
    return {
        "success": True,
        "agent_id": agent_id,
        "count": len(tickets),
        "tickets": [t.to_dict() for t in tickets]
    }


@router.get("/agents/{agent_id}/chats")
async def get_agent_chats(
    agent_id: int,
    db: Session = Depends(get_db)
):

    
    chat_service = ChatService(db)
    sessions = chat_service.get_agent_active_sessions(agent_id)
    
    return {
        "success": True,
        "agent_id": agent_id,
        "active_sessions": len(sessions),
        "sessions": [s.to_dict() for s in sessions]
    }


@router.post("/chats/timeout-check")
async def check_stale_sessions(
    db: Session = Depends(get_db)
):

    chat_service = ChatService(db)
    timeout_count = chat_service.check_and_timeout_stale_sessions()
    
    return {
        "success": True,
        "message": f"Checked stale sessions. {timeout_count} sessions timed out.",
        "timeout_count": timeout_count
    }


@router.get("/performance")
async def get_performance_metrics(
    days: int = 30,
    db: Session = Depends(get_db)
):

    ticket_service = TicketService(db)
    stats = ticket_service.get_ticket_statistics(days=days)
    
    # Calculate additional metrics
    overdue_tickets = ticket_service.get_overdue_tickets()
    
    return {
        "period": f"Last {days} days",
        "kpis": {
            "total_tickets": stats['total_tickets'],
            "resolution_rate": stats['resolution_rate'],
            "average_response_time_hours": stats['average_response_time_hours'],
            "overdue_tickets": len(overdue_tickets),
            "tickets_by_priority": stats['by_priority'],
            "tickets_by_status": stats['by_status']
        },
        "health_indicators": {
            "response_time_status": "good" if stats['average_response_time_hours'] < 12 else "needs_improvement",
            "resolution_rate_status": "good" if stats['resolution_rate'] > 80 else "needs_improvement",
            "overdue_status": "good" if len(overdue_tickets) == 0 else "attention_needed"
        }
    }


@router.get("/categories")
async def get_ticket_categories(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """
    Get ticket distribution by category
    
    - **days**: Number of days to analyze (default: 30)
    """
    
    ticket_service = TicketService(db)
    stats = ticket_service.get_ticket_statistics(days=days)
    
    return {
        "success": True,
        "period": f"Last {days} days",
        "categories": stats['by_category']
    }