from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.features.leads.models.lead_model import Lead
from app.platform.services.email import send_email
from app.platform.config import settings
from jinja2 import Environment, FileSystemLoader, ChoiceLoader
from pathlib import Path

class LeadService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_lead(self, email: str) -> Lead:
        existing = await self.db.execute(select(Lead).where(Lead.email == email))
        if existing.scalars().first():
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already submitted")

        lead = Lead(email=email)
        self.db.add(lead)
        await self.db.commit()
        await self.db.refresh(lead)
        return lead

    @staticmethod
    def _env() -> Environment:
        lead_templates = Path(__file__).resolve().parent.parent / "template"
        base_template = Path(__file__).resolve().parents[2] / "auth" / "template"
        return Environment(loader=ChoiceLoader([FileSystemLoader(str(lead_templates)),
                                               FileSystemLoader(str(base_template))]))

    @classmethod
    async def send_lead_confirmation(cls, lead: Lead) -> None:
        env = cls._env()
        template = env.get_template("lead_confirmation.html")
        html = template.render(lead=lead)
        send_email(lead.email, "We got your request - Sitelytics", html)

    @classmethod
    async def send_admin_notification(cls, lead: Lead) -> None:
        env = cls._env()
        template = env.get_template("lead_admin_notification.html")
        html = template.render(lead=lead)
        send_email(settings.MAIL_ADMIN_EMAIL, f"New Lead: {lead.email}", html)
