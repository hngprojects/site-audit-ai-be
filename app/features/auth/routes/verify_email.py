from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.features.auth.schemas import VerifyOTPRequest, VerifyOTPResponse
from app.features.auth.services import validate_otp
from app.platform.db import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/auth/verify-reset-code", response_model=VerifyOTPResponse)
def verify_reset_code(payload: VerifyOTPRequest, db: Session = Depends(get_db)):
    temp_token = validate_otp(db, payload.email, payload.code)
    return VerifyOTPResponse(
        success=True,
        temp_token=temp_token,
        message="OTP verified successfully."
    )
