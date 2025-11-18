from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api_routers.v1 import api_router
from app.features.waitlist.routes.waitlist import router as waitlist_router
from app.features.health.routes.health import router as health_router
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

from app.features.auth import router as auth_router, ErrorResponse, ErrorCode

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('session_audit.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Session Timeout & Logout API",
    description="Backend session management with automatic logout",
    version="1.0.0"
)


# Exception Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom exception handler for consistent error responses"""
    
    # Log unauthorized access attempts
    if exc.status_code == 401:
        logger.warning(
            f"Unauthorized access attempt - Path: {request.url.path}, "
            f"IP: {request.client.host}, Detail: {exc.detail}"
        )
    
    # If detail is already a dict (our custom format), use it
    if isinstance(exc.detail, dict):
        error_response = ErrorResponse(
            error=exc.detail.get("error", "Unauthorized"),
            error_code=exc.detail.get("error_code", ErrorCode.UNAUTHORIZED),
            message=exc.detail.get("message", str(exc.detail)),
            path=str(request.url.path)
        )
    else:
        error_response = ErrorResponse(
            error="Unauthorized",
            error_code=ErrorCode.UNAUTHORIZED,
            message=str(exc.detail),
            path=str(request.url.path)
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict()
    )


# Include routers
app.include_router(auth_router, prefix="/api")


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint - no authentication required"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Session Timeout & Logout API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(waitlist_router)
app.include_router(health_router)
app.include_router(api_router, prefix="/api/v1")