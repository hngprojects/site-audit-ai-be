from fastapi import Request, status
from fastapi.exceptions import RequestValidationError, HTTPException
from app.platform.response import api_response
import logging

def add_exception_handlers(app):
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return api_response(message=str(exc.detail) or "Error", status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return api_response(
            message="Validation failed",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            data={"errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logging.exception(f"Unhandled exception: {exc}")
        return api_response(
            message="Internal server error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )