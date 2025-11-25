from typing import Any, Optional

from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def api_response(
    *,
    data: Optional[Any] = None,
    message: str = "Operation successful",
    status_code: int = status.HTTP_200_OK,
) -> JSONResponse:
    """
    Single source of truth for ALL API responses.
    Automatically sets status = "success" if < 400 else "error"
    """
    status_str = "success" if status_code < 400 else "error"
    data = jsonable_encoder(data) if data is not None else {}

    return JSONResponse(
        status_code=status_code,
        content={
            "status_code": status_code,
            "status": status_str,
            "message": message,
            "data": data,
        },
    )
