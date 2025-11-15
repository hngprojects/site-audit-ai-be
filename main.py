from fastapi import FastAPI
from app.core.config import get_settings
from app.api.v1 import api_router


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
