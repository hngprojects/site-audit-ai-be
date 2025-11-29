from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

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

    async def get_user_details(self, user_id: str) -> str:
        result = await self.db.execute(select(User.email, User.username).where(User.id == user_id))
        user_details = result.mappings().one_or_none()
        if not user_details:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return user_details
    
    async def create_request(
        self,
        user_id: str,
        job_id: str,
        selected_category: list[str],
    ) -> RequestForm:
        if not selected_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one category must be selected.",
            )

        await self.get_user_details(user_id)  # validate user exists

        submission = RequestForm(
            user_id=user_id,
            job_id=job_id,
            selected_category=selected_category,
            status=RequestStatus.PENDING,
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

        return submission

    async def get_specific_request(self, request_id: str) -> RequestForm | None:
        result = await self.db.execute(select(RequestForm).where(RequestForm.request_id == request_id))
        return result.scalar_one_or_none()
      
    async def list_all_requests_for_user(self, user_id: str) -> list[RequestForm]:
        result = await self.db.execute(select(RequestForm).where(RequestForm.user_id == user_id))
        return result.scalars().all()
    
    async def update_request(self, request_id: str, selected_category: list[str]) -> RequestForm:
        if not selected_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one category must be selected.",
            )

        stmt = (
            update(RequestForm)
            .where(RequestForm.request_id == request_id)
            .values(selected_category=selected_category)
            .returning(RequestForm)
        )
        result = await self.db.execute(stmt)
        updated = result.scalars().first()
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
        await self.db.commit()
        return updated
    
    async def update_status(self, request_id: str, new_status: RequestStatus) -> RequestForm:
        stmt = (
            update(RequestForm)
            .where(RequestForm.request_id == request_id)
            .values(status=new_status)
            .returning(RequestForm)
        )
        result = await self.db.execute(stmt)
        updated = result.scalars().first()
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
        await self.db.commit()
        return updated
    
    async def delete_request(self, request_id: str) -> None:
        stmt = delete(RequestForm).where(RequestForm.request_id == request_id)
        result = await self.db.execute(stmt)
        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
        await self.db.commit()
    

    async def send_notification(self, website, user_email, username) -> None:
        support_templates = Path(__file__).resolve().parent.parent / "template"
        base_template = Path(__file__).resolve().parent.parent.parent / "auth" / "template"


        env = Environment(
        loader=ChoiceLoader([
            FileSystemLoader(str(support_templates)),
            FileSystemLoader(str(base_template)),
        ])
    )
        template = env.get_template("request_form_email.html")
        
        html_content = template.render({
            "website" : website,
            "username": username
            })  


        to_email = user_email
        send_email(user_email, f"New Ticket for {website}", html_content)
