
from app.features.support.routes.email_support import router as email_support_router
from app.features.support.routes.live_chat import router as live_chat_router
from app.features.support.routes.message import router as message_router
from app.features.support.routes.phone_support import router as phone_support_router
from app.features.support.routes.admin import router as admin_router

__all__ = [
    'email_support_router',
    'live_chat_router',
    'message_router',
    'phone_support_router',
    'admin_router'
]