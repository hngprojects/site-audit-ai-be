from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.referral.models.share_message_template import ShareMessageTemplate


class AdminShareMessageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_template(self, platform: str, message: str):
        existing_template = await self.get_template(platform)

        if existing_template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Template for {platform} already exists.",
            )

        template = ShareMessageTemplate(platform=platform, message=message)
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)

        return template

    async def update_template(self, platform: str, message: str):
        template = await self.get_template(platform)

        if template is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Template for {platform} not found."
            )

        template.message = message  # type: ignore
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def get_template(self, platform: str) -> Optional[ShareMessageTemplate]:
        result = await self.db.execute(
            select(ShareMessageTemplate).where(ShareMessageTemplate.platform == platform)
        )
        return result.unique().scalar_one_or_none()

    async def list_templates(self) -> list[ShareMessageTemplate]:
        """
        List all templates.
        """
        result = await self.db.execute(
            select(ShareMessageTemplate).order_by(ShareMessageTemplate.platform)
        )
        return list(result.unique().scalars().all())

    async def delete_template(self, platform: str) -> None:
        """
        Delete a share template.
        """
        result = await self.db.execute(
            select(ShareMessageTemplate).where(ShareMessageTemplate.platform == platform)
        )
        template = result.unique().scalar_one_or_none()

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template for platform '{platform}' not found",
            )

        await self.db.delete(template)
        await self.db.commit()
