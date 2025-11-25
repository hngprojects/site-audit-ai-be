from fastapi import APIRouter

router = APIRouter(prefix="/contact", tags=["Contact Us"])


@router.post("/")
async def submit_contact_form():
    pass
