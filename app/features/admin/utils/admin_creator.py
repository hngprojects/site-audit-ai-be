from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.admin.models.admin import Admin
from app.features.admin.services.auth import AdminAuthService


async def create_super_admin_programmatically(db: AsyncSession, email: str, password: str) -> Admin:
    """
    Create a super admin programmatically.
    This bypasses the normal authentication flow and should only be used
    for initial setup or emergency admin creation.

    Args:
        db: Database session
        email: Admin email
        password: Admin password

    Returns:
        Created admin object
    """
    auth_service = AdminAuthService(db)

    existing_admin = await auth_service.get_admin_by_email(email)
    if existing_admin:
        raise ValueError(f"Admin with email {email} already exists")

    admin = Admin(
        email=email.lower(),
        password_hash=auth_service.get_password_hash(password),
        is_super_admin=True,
        is_active=True,
        created_by=None,
    )

    db.add(admin)
    await db.commit()
    await db.refresh(admin)

    return admin


async def create_first_super_admin_if_none_exists(db: AsyncSession) -> bool:
    """
    Create a first super admin if none exists.
    This is useful for initial application setup.

    Args:
        db: Database session

    Returns:
        True if admin was created, False if admin already exists
    """
    admin_count = await db.scalar(select(func.count(Admin.id)))

    if admin_count and admin_count > 0:
        return False

    # Create default super admin
    default_email = "admin@sitelytics.com"
    default_password = "Admin123!@#"  # Should be changed immediately

    await create_super_admin_programmatically(db, default_email, default_password)

    return True
