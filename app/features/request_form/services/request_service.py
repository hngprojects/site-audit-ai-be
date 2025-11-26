from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.features.request_form.models.request_form import RequestForm, RequestStatus
from app.platform.logger import get_logger
from app.platform.services.email import send_email
from jinja2 import Environment, FileSystemLoader, ChoiceLoader
from app.platform.config import settings
from pathlib import Path
from app.features.auth.models.user import User

logger = get_logger(__name__)


class RequestFormService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_email(self, user_id: str) -> str:
        result = await self.db.execute(select(User.email).where(User.id == user_id))
        email = result.scalar_one_or_none()
        if not email:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return email
    
    async def get_user_name(self, user_id: str) -> str:
        result = await self.db.execute(select(User.username).where(User.id == user_id))
        username = result.scalar_one_or_none()
        if not username:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return username

    async def create_request(
        self,
        user_id: str,
        job_id: str,
        website: str,
        selected_category: list[str],
    ) -> RequestForm:
        if not selected_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one category must be selected.",
            )

        await self.get_user_email(user_id)  # validate user exists

        submission = RequestForm(
            user_id=user_id,
            job_id=job_id,
            selected_category=selected_category,
            status=RequestStatus.RECEIVED,
        )
        self.db.add(submission)

        try:
            await self.db.commit()
            await self.db.refresh(submission)
        except Exception as exc:
            logger.exception("Failed to store request form submission", exc_info=exc)
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not submit request at this time.",
            )

        logger.info(
            "Request form stored",
            extra={
                "request_id": submission.request_id,
                "user_id": user_id,
                "job_id": job_id,
                "website": website,
                "selected_category": selected_category,
            },
        )
        return submission

    async def get_request(self, request_id: str) -> RequestForm | None:
        result = await self.db.execute(select(RequestForm).where(RequestForm.request_id == request_id))
        return result.scalar_one_or_none()
    

    async def send_notification(self, website, user_email, username) -> None:
        support_templates = Path(__file__).resolve().parent.parent / "template"
        base_template = Path(__file__).resolve().parent.parent.parent / "auth" / "template"


        env = Environment(
        loader=ChoiceLoader([
            FileSystemLoader(str(support_templates)),
            FileSystemLoader(str(base_template)),
        ])
    )
        template = env.get_template("admin_email.html")
        
        html_content = template.render({
            "website" : website,
            "username": username
            })  


        to_email = user_email
        send_email(user_email, f"New Ticket for {website}", html_content)
