from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
from app.features.auth.models.verify_email import EmailVerification
from app.features.auth.utils.verify import api_success, api_error, is_expired, generate_temp_token

class EmailVerificationService:

    @staticmethod
    async def verify_code(db: AsyncSession, email: str, code: str):
        # Fetch the latest verification record
        result = await db.execute(
            select(EmailVerification)
            .filter(EmailVerification.email == email)
            .order_by(EmailVerification.created_at.desc())
        )
        record = result.scalars().first()

        if not record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_error("No verification request found for this email")
            )

        if record.verified:
            return api_success("Email already verified")

        if record.attempts >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=api_error("Too many invalid attempts. Request a new code.")
            )

        # Track attempts
        record.attempts += 1

        # Validate code first
        if record.code != code:
            await db.commit() 
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_error("Invalid verification code")
            )

        if is_expired(record.expires_at):
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_error("Verification code has expired")
            )

        # Mark as verified
        record.verified = True
        await db.commit()

        # Generate temporary token
        temp_token = generate_temp_token()
        return api_success("Email verified successfully", data={"temp_token": temp_token})
