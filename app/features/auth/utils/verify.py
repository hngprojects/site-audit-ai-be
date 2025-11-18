from fastapi import status

def api_success(message: str, data: dict | None = None):
    resp = {"success": True, "message": message}
    if data:
        resp.update(data)
    return resp

def api_error(message: str):
    return {"success": False, "message": message}

def is_expired(expires_at):
    from datetime import datetime
    return datetime.utcnow() > expires_at

def generate_temp_token():
    import secrets
    return secrets.token_urlsafe(16)