import uuid
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, UploadFile, status

# Configuration
UPLOAD_DIR = Path("static/uploads/profile-pictures")
MAX_FILE_SIZE = 3 * 1024 * 1024  # 3MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def validate_image_file(file: UploadFile) -> None:
    """
    Validate uploaded image file for size and type.

    Args:
        file: The uploaded file to validate

    Raises:
        HTTPException: If validation fails
    """
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Check content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid content type. Must be an image file.",
        )


async def save_profile_picture(file: UploadFile, user_id: str) -> str:
    """
    Save uploaded profile picture to disk.

    Args:
        file: The uploaded image file
        user_id: The ID of the user uploading the picture

    Returns:
        str: The relative path to the saved file

    Raises:
        HTTPException: If file validation or save fails
    """
    # Validate file
    validate_image_file(file)

    # Create upload directory if it doesn't exist
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # Generate unique filename
    file_ext = Path(file.filename).suffix.lower()
    unique_filename = f"{user_id}_{uuid.uuid4().hex}{file_ext}"
    file_path = UPLOAD_DIR / unique_filename

    # Read and validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # Save file to disk
    try:
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        )

    # Return relative path
    return f"/static/uploads/profile-pictures/{unique_filename}"


def delete_profile_picture(file_url: Optional[str]) -> None:
    """
    Delete a profile picture from disk.

    Args:
        file_url: The URL/path of the file to delete
    """
    if not file_url:
        return

    try:
        # Extract filename from URL
        filename = Path(file_url).name
        file_path = UPLOAD_DIR / filename

        # Delete file if it exists
        if file_path.exists():
            file_path.unlink()
    except Exception:
        # Silently fail - file might already be deleted
        pass
