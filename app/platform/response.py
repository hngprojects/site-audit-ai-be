from fastapi.responses import JSONResponse

def api_response(
    data=None,
    message: str = "Operation successful",
    status_code: int = 200,
    success: bool = True
):
    return JSONResponse(
        status_code=status_code,
        content={
            "status_code": status_code,
            "success": success,
            "message": message,
            "data": data,
        }
    )