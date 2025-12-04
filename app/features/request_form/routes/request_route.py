from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.request_form.schemas.request_schema import (
    RequestFormCreate,
    RequestFormUpdate,
    RequestFormResponse,
    RequestFormStatusResponse,
    RequestFormStatusUpdate,
)
from app.features.request_form.services.request_service import RequestFormService
from app.platform.db.session import get_db
from app.platform.response import api_response
from app.platform.logger import get_logger

router = APIRouter(prefix="/request-form", tags=["Request Form"])
logger = get_logger(__name__)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def submit_request_form(
    background_tasks: BackgroundTasks,
    payload: RequestFormCreate,
    db: AsyncSession = Depends(get_db),
):
    service = RequestFormService(db)
    user_details = await service.get_user_details(payload.user_id) 
    user_email = user_details["email"]
    user_name = user_details["username"]

    submission = await service.create_request(
        user_id=payload.user_id,
        job_id=payload.job_id,
        issues=payload.issues,
        additional_notes=payload.additional_notes,
    )

    logger.info(
        "Request form accepted",
        extra={
            "request_id": submission.request_id,
            "user_id": submission.user_id,
            "job_id": submission.job_id,
            "issues": payload.issues,
        },
    )

    background_tasks.add_task(service.send_notification, submission.request_id, user_email, user_name)

    return api_response(
        message="Request submitted successfully",
        data={
            "request_id": submission.request_id,
            "submission": RequestFormResponse.model_validate(submission),
        },
        status_code=status.HTTP_201_CREATED,
    )


@router.get("/user/{user_id}", status_code=status.HTTP_200_OK)
async def list_requests_for_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = RequestFormService(db)
    requests = await service.list_all_requests_for_user(user_id)
    return api_response(
        message="Requests retrieved",
        data=[RequestFormResponse.model_validate(req) for req in requests],
        status_code=status.HTTP_200_OK
    )


@router.patch("/{request_id}", status_code=status.HTTP_200_OK)
async def update_request(
    request_id: str,
    payload: RequestFormUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = RequestFormService(db)
    updated = await service.update_request(
        request_id,
        payload.model_dump(exclude_none=True),
    )

    return api_response(
        message="Request updated",
        data=RequestFormResponse.model_validate(updated),
        status_code=status.HTTP_200_OK
    )


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_request(
    request_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = RequestFormService(db)
    await service.delete_request(request_id)
    return api_response(
        message="Request form deleted",
        data={},
        status_code=status.HTTP_204_NO_CONTENT,
    )


@router.get("/{request_id}", status_code=status.HTTP_200_OK)
async def get_request_form(
    request_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = RequestFormService(db)
    submission = await service.get_specific_request(request_id)

    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Request not found"
                            )

    logger.info("Request form fetched", extra={"request_id": request_id})
    return api_response(
        message="Request retrieved",
        data=RequestFormResponse.model_validate(submission),
        status_code=status.HTTP_200_OK,
    )


@router.get("/{request_id}/status", status_code=status.HTTP_200_OK)
async def get_request_status(
    request_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = RequestFormService(db)
    submission = await service.get_specific_request(request_id)

    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Request not found"
            )

    logger.info("Request form status fetched", extra={"request_id": request_id, "status": submission.status})
    return api_response(
        message="Request status retrieved",
        data=RequestFormStatusResponse.model_validate(submission),
        status_code=status.HTTP_200_OK,
    )


@router.patch("/{request_id}/status", status_code=status.HTTP_200_OK)
async def update_request_status(
    request_id: str,
    payload: RequestFormStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    service = RequestFormService(db)
    updated = await service.update_status(request_id, payload.status)
    return api_response(
        message="Request status updated",
        data=RequestFormStatusResponse.model_validate(updated),
        status_code=status.HTTP_200_OK
    )