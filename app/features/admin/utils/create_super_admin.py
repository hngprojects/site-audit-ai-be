"""
Script to create a super admin programmatically.

Usage:
    python -m app.features.admin.utils.create_super_admin

This script will create a super admin with the provided credentials.
"""

import asyncio
import sys

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.admin.utils.admin_creator import create_super_admin_programmatically
from app.platform.db.session import get_db


async def main():
    """Main function to create super admin."""

    print("=== Super Admin Creation Script ===")
    print("This will create a new super admin account.\n")

    # Get admin details
    email = input("Enter admin email: ").strip()
    if not email:
        print("Error: Email is required")
        sys.exit(1)

    password = input("Enter admin password: ").strip()
    if not password:
        print("Error: Password is required")
        sys.exit(1)

    confirm_password = input("Confirm password: ").strip()
    if password != confirm_password:
        print("Error: Passwords do not match")
        sys.exit(1)

    # Create admin
    async for db in get_db():
        try:
            admin = await create_super_admin_programmatically(db, email, password)
            print("\n✅ Super admin created successfully!")
            print(f"   Email: {admin.email}")
            print(f"   ID: {admin.id}")
            print(f"   Is Super Admin: {admin.is_super_admin}")
            print(f"   Created At: {admin.created_at}")
            print("\n⚠️  Please change the password immediately after first login.")

        except Exception as e:
            print(f"\n❌ Error creating super admin: {e}")
            sys.exit(1)

        break


if __name__ == "__main__":
    asyncio.run(main())
