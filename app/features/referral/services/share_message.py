from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.referral.models.share_message_template import ShareMessageTemplate
from app.features.referral.services.referral_link import ReferralLinkService


class ShareMessageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_template(self, platform: str) -> ShareMessageTemplate | None:
        """
        Get a specific share message template.
        """
        result = await self.db.execute(
            select(ShareMessageTemplate).where(ShareMessageTemplate.platform == platform)
        )
        return result.unique().scalar_one_or_none()

    async def get_share_message(self, user_data, platform: str):
        referral_service = ReferralLinkService(self.db)
        referral_link = await referral_service.generate_referral_link(str(user_data.id))
        template = await self.get_template(platform.lower())

        # If no template for platform, try default
        if not template:
            template = await self.get_template("default")

        # If still no template, return empty message
        if not template:
            return {"message": "", "referralLink": referral_link}

        message = self._replace_placeholders(template.message, user_data, referral_link)  # type: ignore

        return {"message": message, "referralLink": referral_link}

    def _replace_placeholders(self, template: str, user_data, referral_link: str) -> str:
        """
        Replace placeholders in template with actual user data.
        """
        # username = user_data.get("username") or user_data.get("first_name", "")
        username = user_data.username or user_data.first_name or ""

        replacements = {
            "{referral_link}": referral_link,
            "{first_name}": user_data.first_name,
            "{last_name}": user_data.last_name,
            "{email}": user_data.email,
            "{username}": username,
            "{site_name}": "Sitelytics",
        }

        message = template
        for placeholder, value in replacements.items():
            if value is not None:
                message = message.replace(placeholder, value)

        return message
